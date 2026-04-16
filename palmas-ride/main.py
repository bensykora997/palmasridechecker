#!/usr/bin/env python3
"""Palmas Ride Advisor — Should I bike Palmas (Medellín) tomorrow morning?"""

import json
import sys
from fetch_siata import fetch_pluviometrica, fetch_radar, fetch_wrf_forecast
from fetch_openmeteo import fetch_openmeteo
from analyze import analyze_radar, analyze_stations, analyze_wrf, get_time_window, analyze_road_conditions, compute_score


def fetch_all_siata():
    pluvio = fetch_pluviometrica()
    radar = fetch_radar()
    wrf = fetch_wrf_forecast()
    return pluvio, radar, wrf


def run():
    print("🚴 Palmas Ride Advisor — fetching data...\n")

    pluvio, radar, wrf = fetch_all_siata()
    open_meteo = fetch_openmeteo()

    # Analyze
    radar_analysis = analyze_radar(radar)
    station_analysis = analyze_stations(pluvio)
    wrf_analysis = analyze_wrf(wrf)
    time_window = get_time_window(open_meteo)
    road = analyze_road_conditions(open_meteo, station_analysis)

    # Score
    result = compute_score(open_meteo, station_analysis, radar_analysis, wrf_analysis, time_window, road)

    output = {
        "decision": result["decision"],
        "score": result["score"],
        "confidence": result["confidence"],
        "best_window": {"start": time_window["start"], "end": time_window["end"]} if time_window.get("found") else None,
        "road_conditions": road["condition"],
        "reasons": result["reasons"],
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
            "wrf_forecast": {
                "available": wrf_analysis.get("available", False),
            },
            "open_meteo": {
                "available": open_meteo["available"],
            },
        },
    }

    if "--cli" in sys.argv:
        print_cli(output)
    else:
        print(json.dumps(output, indent=2, ensure_ascii=False))

    return output


def _cli_banner(score):
    if score >= 90: return "🚴‍♂️💨 KIT UP AND CLIP IN!"
    if score >= 75: return "🔥 SEND IT, PARCERO!"
    if score >= 60: return "🦺 RIDEABLE — pack a gilet"
    if score >= 50: return "🎲 ROLL THE DICE, ROLL THE WHEELS"
    if score >= 35: return "🪨 ZWIFT AND CHILL, BRO"
    if score >= 20: return "🌧️ NOT TODAY, PARCERO"
    return                  "🛋️ REST DAY — ZERO GUILT"

def print_cli(output):
    banner = _cli_banner(output["score"])

    sep = "═" * 48
    print(sep)
    print(f"  {banner}")
    print(sep)
    print(f"  Score:       {output['score']}/100 ({output['confidence']} confidence)")

    if output["best_window"]:
        print(f"  Best window: {output['best_window']['start']} – {output['best_window']['end']}")
    else:
        print("  Best window: No dry window found")

    print()
    print("  Reasons:")
    for r in output["reasons"]:
        print(f"    • {r}")

    print()
    ds = output["data_sources"]
    print("  Data sources:")
    print(f"    SIATA stations: {ds['siata_stations']['count']} nearby ({ds['siata_stations']['offline']} offline)")
    print(f"    Radar:          {'last scan ' + ds['radar']['last_scan'] if ds['radar']['last_scan'] else 'unavailable'}")
    print(f"    WRF forecast:   {'available' if ds['wrf_forecast']['available'] else 'unavailable'}")
    print(f"    Open-Meteo:     {'available' if ds['open_meteo']['available'] else 'unavailable'}")
    print(sep)


if __name__ == "__main__":
    run()
