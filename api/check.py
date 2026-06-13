import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from http.server import BaseHTTPRequestHandler
from fetch_siata import fetch_pluviometrica, fetch_radar, fetch_wrf_forecast
from fetch_openmeteo import fetch_openmeteo
from fetch_air import fetch_air_quality
from analyze import (
    analyze_radar, analyze_stations, analyze_wrf,
    get_time_window, analyze_road_conditions, compute_score,
    get_target_date,
)
from config import RIDE_EARLIEST, RIDE_LATEST, PALMAS_ROUTE_SEGMENTS
from timeutil import today_str, evening_before, framing as get_framing
import db
import calibrate
import backfill


def _summarize_forecast(open_meteo):
    """Pull the headline forecast inputs the model used."""
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
        "target_date": get_target_date(),
        "framing": get_framing(),
        # Alias kept for one release so a cached older frontend still renders.
        "tomorrow_date": get_target_date(),
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
        # Live SIATA aggregates across the corridor — shows which signal (if any)
        # flipped the raining flag. Useful both for the UI "more details" view
        # and for understanding why the road condition came out the way it did.
        "live_signals": station_analysis.get("live_signals", {}),
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
                    "p10m": s.get("p10m"),
                    "p1h": s.get("p1h"),
                    "p24h": s.get("p24h"),
                    "raining": (
                        (s.get("value") is not None and s.get("value") != -999 and s.get("value", 0) >= 0.1)
                        or (s.get("p10m") is not None and s.get("p10m", 0) >= 0.1)
                        or (s.get("p1h") is not None and s.get("p1h", 0) >= 0.5)
                    ),
                    "offline": s.get("value") == -999 or not s.get("sensor_live", True),
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
            station_snapshots = backfill.station_snapshots(pluvio)

            # Shadow prediction from the stored calibration model (read-only
            # here; the cron retrains nightly). Surfaced in the response and
            # recorded on the entry for the shadow model's own track record.
            shadow = None
            try:
                cal_state = db.read_calibration()
                feats = [avg_prob, max_wind, avg_hum, overnight]
                if any(f is None for f in feats):
                    feats = None
                shadow = calibrate.apply_calibration(cal_state, result["score"], feats)
            except Exception as e:
                print(f"[calibration] shadow skipped: {e}")
            response["calibration_shadow"] = shadow

            # A pre-dawn ("this morning") view re-scores today's ride; log it
            # as an observation only — the night-before canonical prediction
            # stays frozen and is what calibration grades.
            is_morning = get_framing() == "this_morning"
            db.save_prediction(
                ride_date=get_target_date(),
                score=result["score"],
                decision=result["decision"],
                confidence=result["confidence"],
                reasons=result["reasons"],
                forecast_avg_precip_prob=avg_prob,
                forecast_max_wind=max_wind,
                forecast_avg_humidity=avg_hum,
                forecast_overnight_precip_mm=overnight,
                station_snapshots=station_snapshots,
                shadow=shadow,
                morning=is_morning,
            )
            # Backfill any past predictions with observed weather (shared
            # dual-source logic in backfill.py, used by cron + history too).
            backfill.backfill_pending(pluvio=pluvio)
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
