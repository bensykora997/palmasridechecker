import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from fetch_openmeteo import fetch_actuals_for_date
from fetch_siata import fetch_pluviometrica
from timeutil import now_bogota
import db
import calibrate

CALIBRATION_STALE_SECONDS = 24 * 3600


def _maybe_retrain_calibration():
    """Retrain the shadow model if the stored calibration is missing or older
    than 24h. Mirrors the opportunistic-backfill pattern so the panel stays
    fresh even between nightly cron runs. Returns the (possibly new) state."""
    cal = db.read_calibration()
    stale = True
    ts = (cal or {}).get("trained_at")
    if ts:
        try:
            # trained_at is an ISO string with tz offset (Bogota). Compare in UTC.
            parsed = datetime.fromisoformat(ts)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            age = (now_bogota() - parsed).total_seconds()
            stale = age > CALIBRATION_STALE_SECONDS
        except Exception:
            stale = True
    if stale:
        entries = db._read_all().get("predictions", [])
        cal = calibrate.train_calibration(
            entries, trained_at=now_bogota().isoformat(timespec="seconds"))
        db.write_calibration(cal)
    return cal


def _backfill_pending():
    """Best-effort dual-source backfill. Mirrors the logic in api/cron.py
    and the opportunistic path in api/check.py so all three entry points
    write the same audit fields."""
    pending = db.pending_actuals()
    if not pending:
        return

    # Only fetch SIATA pluvio once if there's something to backfill
    pluvio = fetch_pluviometrica()
    p24h_vals = [s.get("p24h") for s in pluvio.get("stations", []) if s.get("p24h") is not None]
    siata_avg = round(sum(p24h_vals) / len(p24h_vals), 2) if p24h_vals else None
    siata_max = round(max(p24h_vals), 2) if p24h_vals else None
    snaps = [
        {"name": s.get("name"), "code": s.get("code"),
         "distance_km": s.get("distance_km"),
         "valor": s.get("value"), "p10m": s.get("p10m"),
         "p1h": s.get("p1h"), "p24h": s.get("p24h")}
        for s in pluvio.get("stations", [])
    ]

    for past_date in pending:
        om = fetch_actuals_for_date(past_date)
        om_precip = om["precip_mm"] if om else None
        om_max_wind = om["max_wind"] if om else None
        candidates = [v for v in (om_precip, siata_avg) if v is not None]
        if not candidates:
            continue
        precip_final = round(max(candidates), 2)
        if om_precip is None:
            source, disagreement = "siata_p24h", None
        elif siata_avg is None:
            source, disagreement = "open_meteo", None
        else:
            disagreement = round(abs(om_precip - siata_avg), 2)
            if disagreement < 0.5:
                source = "agreed"
            elif siata_avg > om_precip:
                source = "siata_p24h"
            else:
                source = "open_meteo"
        db.save_actuals(
            ride_date=past_date,
            actual_precip_mm=precip_final,
            actual_max_wind=om_max_wind if om_max_wind is not None else 0,
            actual_rained=precip_final > 0.1,
            open_meteo_precip_mm=om_precip,
            siata_p24h_avg_mm=siata_avg,
            siata_p24h_max_mm=siata_max,
            source=source,
            disagreement_mm=disagreement,
            station_snapshots=snaps,
        )


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if db.is_enabled():
                db.init_schema()
                _backfill_pending()
            data = db.fetch_history(limit=60)
            if db.is_enabled():
                try:
                    data["calibration"] = _maybe_retrain_calibration()
                except Exception as e:
                    data["calibration"] = {"error": str(e)}
        except Exception as e:
            data = {"enabled": False, "error": str(e), "predictions": [], "stats": None}

        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
