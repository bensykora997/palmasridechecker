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
    get_tomorrow_date,
)


def build_result():
    pluvio = fetch_pluviometrica()
    radar = fetch_radar()
    wrf = fetch_wrf_forecast()
    open_meteo = fetch_openmeteo()

    radar_analysis = analyze_radar(radar)
    station_analysis = analyze_stations(pluvio)
    wrf_analysis = analyze_wrf(wrf)
    time_window = get_time_window(open_meteo)
    road = analyze_road_conditions(open_meteo, station_analysis)
    result = compute_score(open_meteo, station_analysis, radar_analysis, wrf_analysis, time_window, road)

    return {
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
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = build_result()
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
