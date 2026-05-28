import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from http.server import BaseHTTPRequestHandler
from fetch_siata import fetch_pluviometrica, fetch_radar, fetch_wrf_forecast
from fetch_openmeteo import fetch_openmeteo, fetch_actuals_for_date
from fetch_air import fetch_air_quality
from analyze import (
    analyze_radar, analyze_stations, analyze_wrf,
    get_time_window, analyze_road_conditions, compute_score,
    get_tomorrow_date,
)
from config import RIDE_EARLIEST, RIDE_LATEST, PALMAS_ROUTE_SEGMENTS
from timeutil import today_str
import db


def _summarize_forecast(open_meteo):
    """Pull the headline forecast inputs the model used."""
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


def build_result():
    pluvio = fetch_pluviometrica()
    radar = fetch_radar()
    wrf = fetch_wrf_forecast()
    open_meteo = fetch_openmeteo()
    air = fetch_air_quality()

    radar_analysis = analyze_radar(radar)
    station_analysis = analyze_stations(pluvio)
    wrf_analysis = analyze_wrf(wrf)
    time_window = get_time_window(open_meteo)
    road = analyze_road_conditions(open_meteo, station_analysis)
    result = compute_score(open_meteo, station_analysis, radar_analysis, wrf_analysis, time_window, road)

    response = {
        "decision": result["decision"],
        "score": result["score"],
        "confidence": result["confidence"],
        "best_window": (
            {"start": time_window["start"], "end": time_window["end"]}
            if time_window.get("found") else None
        ),
        "road_conditions": {
            "condition": road["condition"],
            "detail": road["detail"],
            "recent_precip_mm": road["recent_precip_mm"],
            "factors": road["factors"],
        },
        "reasons": result["reasons"],
        "tomorrow_date": get_tomorrow_date(),
        "data_sources": {
            "siata_stations": {
                "count": station_analysis["station_count"],
                "offline": station_analysis["offline_count"],
                "raining": station_analysis["raining"],
            },
            "radar": {
                "available": radar["available"],
                "last_scan": radar_analysis.get("last_scan"),
            },
            "wrf_forecast": {"available": wrf_analysis.get("available", False)},
            "open_meteo": {"available": open_meteo["available"]},
        },
        # Extra data shown only in the "More details" view — not factored into the score.
        "details": {
            "radar": {
                "frames": radar.get("frames", [])[-12:],   # last ~12 frames is plenty for the loop
                "bounds": radar.get("bounds"),
                "available": radar.get("available", False),
            },
            "stations": [
                {
                    "name": s["name"],
                    "lat": s["lat"],
                    "lon": s["lon"],
                    "value": s["value"],
                    "neighborhood": s.get("neighborhood", ""),
                    "distance_km": s.get("distance_km"),
                    "raining": s["value"] > 0 and s["value"] != -999,
                    "offline": s["value"] == -999,
                }
                for s in pluvio.get("stations", [])
            ],
            "route_segments": [[[lat, lon] for lat, lon in seg] for seg in PALMAS_ROUTE_SEGMENTS],
            "air_quality": air,
        },
    }

    # Best-effort logging: never block the response on a DB failure.
    try:
        if db.is_enabled():
            db.init_schema()
            avg_prob, max_wind, avg_hum, overnight = _summarize_forecast(open_meteo)
            db.save_prediction(
                ride_date=get_tomorrow_date(),
                score=result["score"],
                decision=result["decision"],
                confidence=result["confidence"],
                reasons=result["reasons"],
                forecast_avg_precip_prob=avg_prob,
                forecast_max_wind=max_wind,
                forecast_avg_humidity=avg_hum,
                forecast_overnight_precip_mm=overnight,
            )
            # Backfill any past predictions with observed weather
            for past_date in db.pending_actuals():
                actuals = fetch_actuals_for_date(past_date)
                if actuals:
                    db.save_actuals(
                        ride_date=past_date,
                        actual_precip_mm=actuals["precip_mm"],
                        actual_max_wind=actuals["max_wind"],
                        actual_rained=actuals["rained"],
                    )
            response["logging"] = {"enabled": True}
        else:
            response["logging"] = {"enabled": False}
    except Exception as e:
        print(f"[logging] Skipped due to error: {e}")
        response["logging"] = {"enabled": False, "error": str(e)}

    return response


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # If the caller asks for fresh data, drop the in-memory cache so the
        # next fetchers go straight to the source instead of replaying a
        # cached response from a warm function instance.
        if "fresh=1" in (self.path or ""):
            from cache import clear_cache
            clear_cache()
        data = build_result()
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        # Belt-and-braces: tell intermediaries never to cache this response
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)
