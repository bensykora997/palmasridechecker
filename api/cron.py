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
        )
        result["logged"] = {
            "ride_date": ride_date,
            "decision": scored["decision"],
            "score": scored["score"],
        }
    except Exception as e:
        result["errors"].append(f"log_prediction: {e}")

    # 2) Backfill any pending actuals
    try:
        for past_date in db.pending_actuals():
            actuals = fetch_actuals_for_date(past_date)
            if actuals:
                db.save_actuals(
                    ride_date=past_date,
                    actual_precip_mm=actuals["precip_mm"],
                    actual_max_wind=actuals["max_wind"],
                    actual_rained=actuals["rained"],
                )
                result["backfilled"].append({
                    "ride_date": past_date,
                    "precip_mm": actuals["precip_mm"],
                    "rained": actuals["rained"],
                })
            else:
                result["skipped_backfill"].append(past_date)
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
