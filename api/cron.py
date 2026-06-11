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
from fetch_openmeteo import fetch_openmeteo, fetch_actuals_for_date
from analyze import (
    analyze_radar, analyze_stations, analyze_wrf,
    get_time_window, analyze_road_conditions, compute_score,
    get_tomorrow_date,
)
from config import RIDE_EARLIEST, RIDE_LATEST
from timeutil import today_str
import db


def _summarize_forecast(open_meteo):
    if not open_meteo.get("available") or not open_meteo.get("hours"):
        return None, None, None, None
    tomorrow = get_tomorrow_date()
    morning = [
        h for h in open_meteo["hours"]
        if h["date"] == tomorrow and RIDE_EARLIEST <= h["hour"] <= RIDE_LATEST
    ]
    if not morning:
        return None, None, None, None
    avg_prob = sum(h["precip_prob"] for h in morning) / len(morning)
    max_wind = max(h["wind_speed"] for h in morning)
    avg_hum = sum(h["humidity"] for h in morning) / len(morning)
    today = today_str()
    pre_ride = [
        h for h in open_meteo["hours"]
        if (h["date"] == today and h["hour"] >= 20)
        or (h["date"] == tomorrow and h["hour"] < RIDE_EARLIEST)
    ]
    overnight = sum(h["precip"] for h in pre_ride) if pre_ride else 0
    return round(avg_prob, 1), round(max_wind, 1), round(avg_hum, 1), round(overnight, 2)


def _station_snapshots(pluvio):
    """Capture each corridor station's full rain readings for the audit trail."""
    return [
        {
            "name": s.get("name"),
            "code": s.get("code"),
            "distance_km": s.get("distance_km"),
            "valor": s.get("value"),
            "p10m": s.get("p10m"),
            "p1h": s.get("p1h"),
            "p24h": s.get("p24h"),
        }
        for s in pluvio.get("stations", [])
    ]


def _siata_p24h_stats(pluvio):
    """Compute average / max p24h across corridor stations.

    Returns (avg, max, [station snapshots]). p24h values that are None
    (sensor offline / no reading) are excluded from the aggregates.
    """
    vals = [s.get("p24h") for s in pluvio.get("stations", []) if s.get("p24h") is not None]
    if not vals:
        return None, None
    return round(sum(vals) / len(vals), 2), round(max(vals), 2)


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
        ride_date = get_tomorrow_date()
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
            station_snapshots=_station_snapshots(pluvio),
        )
        result["logged"] = {
            "ride_date": ride_date,
            "decision": scored["decision"],
            "score": scored["score"],
        }
    except Exception as e:
        result["errors"].append(f"log_prediction: {e}")

    # 2) Backfill any pending actuals
    # Capture SIATA's p24h totals NOW (07:00 cron run) — at this point
    # p24h covers yesterday afternoon → this morning, i.e. the ride
    # window we want to evaluate. We reuse the same pluvio fetch from
    # step 1 since it's seconds old.
    try:
        # `pluvio` may not be defined if step 1 errored — refetch defensively
        try:
            pluvio_for_backfill = pluvio
        except NameError:
            pluvio_for_backfill = fetch_pluviometrica()

        siata_avg, siata_max = _siata_p24h_stats(pluvio_for_backfill)
        station_snaps = _station_snapshots(pluvio_for_backfill)

        for past_date in db.pending_actuals():
            om = fetch_actuals_for_date(past_date)
            om_precip = om["precip_mm"] if om else None
            om_max_wind = om["max_wind"] if om else None

            # Pick the higher of the two precipitation sources. We never
            # want to underreport rain; over-reporting would push a NO
            # decision toward being marked correct, which is the safer
            # direction (better to call a wet day wet than miss it).
            candidates = [v for v in (om_precip, siata_avg) if v is not None]
            if not candidates:
                # Both sources failed — skip this date so we retry next run.
                result["skipped_backfill"].append(past_date)
                continue
            precip_final = round(max(candidates), 2)
            rained_final = precip_final > 0.1

            # Decide source label + disagreement
            if om_precip is None:
                source = "siata_p24h"
                disagreement = None
            elif siata_avg is None:
                source = "open_meteo"
                disagreement = None
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
                actual_rained=rained_final,
                open_meteo_precip_mm=om_precip,
                siata_p24h_avg_mm=siata_avg,
                siata_p24h_max_mm=siata_max,
                source=source,
                disagreement_mm=disagreement,
                station_snapshots=station_snaps,
            )
            result["backfilled"].append({
                "ride_date": past_date,
                "precip_mm": precip_final,
                "rained": rained_final,
                "source": source,
                "open_meteo_precip_mm": om_precip,
                "siata_p24h_avg_mm": siata_avg,
            })
    except Exception as e:
        result["errors"].append(f"backfill: {e}")

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
