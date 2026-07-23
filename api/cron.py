"""Cron-only endpoint. Vercel Cron Jobs hit this on a schedule to:
  1. Log tomorrow's prediction to blob storage.
  2. Backfill observed weather for any past predictions still pending.

Protected by CRON_SECRET — Vercel automatically sends
`Authorization: Bearer ${CRON_SECRET}` with cron requests when the
env var is set. If CRON_SECRET is not set in the environment, the
endpoint refuses all requests (fail-closed) since this endpoint
writes to the blob store.

User-facing UI continues to use /api/check and /api/history without
auth — those endpoints also log/backfill opportunistically.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from http.server import BaseHTTPRequestHandler

from fetch_siata import fetch_pluviometrica, fetch_radar, fetch_wrf_forecast
from fetch_openmeteo import fetch_openmeteo
from analyze import (
    analyze_radar, analyze_stations, analyze_wrf,
    get_time_window, analyze_road_conditions, compute_score,
    get_target_date,
)
from config import RIDE_EARLIEST, RIDE_LATEST
from timeutil import today_str, evening_before, framing as get_framing
import db
import calibrate
import backfill


def _summarize_forecast(open_meteo):
    if not open_meteo.get("available") or not open_meteo.get("hours"):
        return None, None, None, None
    target = get_target_date()
    morning = [
        h for h in open_meteo["hours"]
        if h["date"] == target and RIDE_EARLIEST <= h["hour"] <= RIDE_LATEST
    ]
    if not morning:
        return None, None, None, None
    avg_prob = sum(h["precip_prob"] for h in morning) / len(morning)
    max_wind = max(h["wind_speed"] for h in morning)
    avg_hum = sum(h["humidity"] for h in morning) / len(morning)
    prev_evening = evening_before(target)
    pre_ride = [
        h for h in open_meteo["hours"]
        if (h["date"] == prev_evening and h["hour"] >= 20)
        or (h["date"] == target and h["hour"] < RIDE_EARLIEST)
    ]
    overnight = sum(h["precip"] for h in pre_ride) if pre_ride else 0
    return round(avg_prob, 1), round(max_wind, 1), round(avg_hum, 1), round(overnight, 2)


def run_cron():
    """Do both jobs: log tomorrow's prediction, then backfill actuals."""
    result = {"logged": None, "backfilled": [], "skipped_backfill": [], "errors": []}

    if not db.is_enabled():
        result["errors"].append("blob storage not configured")
        return result

    db.init_schema()

    # 1) Log tomorrow's prediction
    try:
        pluvio = fetch_pluviometrica()
        radar = fetch_radar()
        wrf = fetch_wrf_forecast()
        open_meteo = fetch_openmeteo()

        radar_analysis = analyze_radar(radar)
        station_analysis = analyze_stations(pluvio)
        wrf_analysis = analyze_wrf(wrf)
        time_window = get_time_window(open_meteo)
        road = analyze_road_conditions(open_meteo, station_analysis)
        scored = compute_score(open_meteo, station_analysis, radar_analysis,
                               wrf_analysis, time_window, road)

        avg_prob, max_wind, avg_hum, overnight = _summarize_forecast(open_meteo)
        ride_date = get_target_date()
        # The 20:00 run targets tomorrow (canonical). The 07:00 run targets
        # today (framing "this morning") → logged as an observation only, so
        # it can't clobber the night-before canonical prediction.
        is_morning = get_framing() == "this_morning"

        # Champion model prediction: what the learned champion (as trained on
        # prior nights) says for this same forecast. Recorded so the model
        # accrues its own real-time track record.
        snaps = backfill.station_snapshots(pluvio)
        _p24h = [s.get("p24h") for s in snaps if isinstance(s.get("p24h"), (int, float))]
        feature_map = {
            "avg_precip_prob": avg_prob,
            "max_wind": max_wind,
            "avg_humidity": avg_hum,
            "overnight_precip_mm": overnight,
            "p24h": max(_p24h) if _p24h else None,
        }
        shadow = None
        try:
            cal_state = db.read_calibration()
            shadow = calibrate.apply_calibration(cal_state, scored["score"], feature_map)
        except Exception as e:
            result["errors"].append(f"shadow: {e}")

        db.save_prediction(
            ride_date=ride_date,
            score=scored["score"],
            decision=scored["decision"],
            confidence=scored["confidence"],
            reasons=scored["reasons"],
            forecast_avg_precip_prob=avg_prob,
            forecast_max_wind=max_wind,
            forecast_avg_humidity=avg_hum,
            forecast_overnight_precip_mm=overnight,
            station_snapshots=snaps,
            shadow=shadow,
            morning=is_morning,
        )
        result["logged"] = {
            "ride_date": ride_date,
            "morning_observation": is_morning,
            "decision": scored["decision"],
            "score": scored["score"],
            "shadow": shadow,
        }
    except Exception as e:
        result["errors"].append(f"log_prediction: {e}")

    # 2) Backfill any pending actuals. Shared dual-source logic lives in
    # backfill.py (used by /api/check and /api/history too) so all three
    # entry points label days identically. SIATA's p24h is only applied to
    # today's window in the morning; older dates use Open-Meteo only.
    try:
        # `pluvio` may not be defined if step 1 errored — refetch defensively.
        try:
            pluvio_for_backfill = pluvio
        except NameError:
            pluvio_for_backfill = fetch_pluviometrica()

        outcomes = backfill.backfill_pending(pluvio=pluvio_for_backfill)
        result["backfilled"] = [o for o in outcomes if not o.get("skipped")]
        result["skipped_backfill"] = [o["ride_date"] for o in outcomes if o.get("skipped")]
    except Exception as e:
        result["errors"].append(f"backfill: {e}")

    # 3) Retrain the shadow calibration model on the full (now-updated) log.
    try:
        from timeutil import now_bogota
        entries = db._read_all().get("predictions", [])
        cal = calibrate.train_calibration(
            entries, trained_at=now_bogota().isoformat(timespec="seconds"))
        db.write_calibration(cal)
        result["calibration"] = {"stage": cal.get("stage"),
                                 "n_evaluated": cal.get("n_evaluated"),
                                 "n_rained": cal.get("n_rained")}
    except Exception as e:
        result["errors"].append(f"calibration: {e}")

    return result


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        secret = os.environ.get("CRON_SECRET")
        if not secret:
            self._respond(500, {"error": "CRON_SECRET not configured"})
            return

        auth = self.headers.get("Authorization", "")
        if auth != f"Bearer {secret}":
            self._respond(401, {"error": "unauthorized"})
            return

        try:
            result = run_cron()
            self._respond(200, {"ok": True, **result})
        except Exception as e:
            self._respond(500, {"ok": False, "error": str(e)})

    def _respond(self, status, body):
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(payload)
