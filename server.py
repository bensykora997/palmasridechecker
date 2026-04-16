#!/usr/bin/env python3
"""Palmas Ride Engine — HTTP server for API + static UI."""

import json
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from fetch_siata import fetch_pluviometrica, fetch_radar, fetch_wrf_forecast
from fetch_openmeteo import fetch_openmeteo
from analyze import (
    analyze_radar, analyze_stations, analyze_wrf,
    get_time_window, analyze_road_conditions, compute_score,
    get_tomorrow_date,
)

PORT = int(os.environ.get("PORT", 3000))
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


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


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        if self.path == "/api/check":
            self._json_response(build_result())
        elif self.path == "/api/health":
            self._json_response({"status": "ok"})
        else:
            super().do_GET()

    def _json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[server] {args[0]}\n")


def main():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"🚴 Palmas Ride Engine running on http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
