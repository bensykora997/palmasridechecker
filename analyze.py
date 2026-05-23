from datetime import datetime, timedelta
from config import SCORING, RIDE_EARLIEST, RIDE_LATEST, RIDE_WINDOW_LABEL
from timeutil import now_bogota, today_str, tomorrow_str


def get_tomorrow_date():
    return tomorrow_str()


def fmt_hour(h):
    return f"{h:02d}:00"


def analyze_radar(radar):
    """Check radar recency / availability."""
    if not radar["available"] or not radar["frames"]:
        return {"active": False, "last_scan": None, "reason": "Radar data unavailable"}

    last = radar["frames"][-1]
    try:
        # SIATA timestamps are local Bogota time, so compare in Bogota.
        last_time = datetime.strptime(last["time"], "%Y-%m-%d %H:%M")
        age_min = (now_bogota().replace(tzinfo=None) - last_time).total_seconds() / 60
    except Exception:
        age_min = 999

    return {
        "active": True,
        "last_scan": last["time"],
        "age_minutes": round(age_min),
        "reason": "Recent radar data available" if age_min < 30 else "Radar data is stale (>30 min)",
    }


def analyze_stations(pluvio):
    """Check if any nearby SIATA stations show active rainfall."""
    if not pluvio["available"] or not pluvio["stations"]:
        return {"raining": False, "station_count": 0, "offline_count": 0, "active_stations": [], "reason": "No nearby stations"}

    active = [s for s in pluvio["stations"] if s["value"] > 0 and s["value"] != -999]
    offline = [s for s in pluvio["stations"] if s["value"] == -999]

    return {
        "raining": len(active) > 0,
        "active_stations": [{"name": s["name"], "rainfall": s["value"]} for s in active],
        "station_count": len(pluvio["stations"]),
        "offline_count": len(offline),
        "reason": f"{len(active)} station(s) reporting rain" if active else "No stations reporting rain",
    }


def analyze_wrf(wrf):
    """Analyze WRF forecast for tomorrow morning."""
    if not wrf["available"]:
        return {"available": False, "reason": "WRF forecast unavailable"}

    tomorrow = get_tomorrow_date()
    all_fc = wrf["centro"] + wrf["envigado"]
    tomorrow_fc = [f for f in all_fc if f["date"] == tomorrow]

    if not tomorrow_fc:
        return {"available": False, "reason": "No WRF forecast for tomorrow"}

    rain_levels = []
    for f in tomorrow_fc:
        rain_levels.extend([f["rain_early_morning"], f["rain_morning"]])

    high_rain = any(l in ("ALTA", "MUY ALTA") for l in rain_levels)
    med_rain = any(l == "MEDIA" for l in rain_levels)

    if high_rain:
        reason = "WRF predicts HIGH rain tomorrow morning"
    elif med_rain:
        reason = "WRF predicts MEDIUM rain tomorrow morning"
    else:
        reason = "WRF predicts LOW rain tomorrow morning"

    return {"available": True, "date": tomorrow, "forecasts": tomorrow_fc, "high_rain": high_rain, "med_rain": med_rain, "reason": reason}


def get_time_window(open_meteo):
    """Check the fixed 05:00–07:30 riding window for dry conditions."""
    if not open_meteo["available"] or not open_meteo["hours"]:
        return {"found": False, "dry": False, "reason": "No hourly forecast available"}

    tomorrow = get_tomorrow_date()
    window_hours = [
        h for h in open_meteo["hours"]
        if h["date"] == tomorrow and RIDE_EARLIEST <= h["hour"] <= RIDE_LATEST
    ]

    if not window_hours:
        return {"found": False, "dry": False, "reason": "No forecast data for tomorrow morning"}

    # Check if the whole window is dry
    dry_hours = [h for h in window_hours if h["precip"] < 0.1 and h["precip_prob"] < 50]
    all_dry = len(dry_hours) == len(window_hours)
    avg_prob = sum(h["precip_prob"] for h in window_hours) / len(window_hours)

    return {
        "found": True,
        "start": "05:00",
        "end": "07:30",
        "label": RIDE_WINDOW_LABEL,
        "dry": all_dry,
        "dry_hours": len(dry_hours),
        "total_hours": len(window_hours),
        "avg_precip_prob": round(avg_prob),
        "reason": f"Window {RIDE_WINDOW_LABEL}: {'fully dry' if all_dry else f'{len(dry_hours)}/{len(window_hours)} hours dry'}",
    }


def analyze_road_conditions(open_meteo, station_analysis):
    """Determine if roads are likely wet or dry based on recent precipitation."""
    result = {
        "condition": "unknown",
        "detail": "",
        "recent_precip_mm": 0,
        "factors": [],
    }

    # Check recent hours from Open-Meteo (last 6 hours before ride)
    if open_meteo["available"] and open_meteo["hours"]:
        tomorrow = get_tomorrow_date()
        # Hours leading up to ride: previous evening + overnight (23:00 today through 04:00 tomorrow)
        today = today_str()
        pre_ride = [
            h for h in open_meteo["hours"]
            if (h["date"] == today and h["hour"] >= 20)
            or (h["date"] == tomorrow and h["hour"] < RIDE_EARLIEST)
        ]

        if pre_ride:
            recent_mm = sum(h["precip"] for h in pre_ride)
            result["recent_precip_mm"] = round(recent_mm, 1)

            if recent_mm > 5:
                result["factors"].append(f"Heavy overnight rain ({recent_mm:.1f} mm)")
            elif recent_mm > 1:
                result["factors"].append(f"Light overnight rain ({recent_mm:.1f} mm)")
            else:
                result["factors"].append("No significant overnight rain")

            # Check humidity as proxy for drying
            avg_hum = sum(h["humidity"] for h in pre_ride) / len(pre_ride)
            if avg_hum > 90:
                result["factors"].append(f"Very high humidity ({avg_hum:.0f}%) — slow drying")
            elif avg_hum > 75:
                result["factors"].append(f"Moderate humidity ({avg_hum:.0f}%)")

    # Check SIATA current readings
    if station_analysis["raining"]:
        result["factors"].append("Active rain at nearby stations")
    elif station_analysis["station_count"] > 0:
        # All online stations at 0 = currently dry
        online = station_analysis["station_count"] - station_analysis["offline_count"]
        if online > 0:
            result["factors"].append(f"All {online} stations currently dry")

    # Determine condition
    precip = result["recent_precip_mm"]
    is_raining = station_analysis.get("raining", False)

    if is_raining:
        result["condition"] = "wet"
        result["detail"] = "Roads are wet — active rainfall"
    elif precip > 5:
        result["condition"] = "wet"
        result["detail"] = "Roads likely wet — heavy recent rain"
    elif precip > 1:
        result["condition"] = "damp"
        result["detail"] = "Roads may be damp — light recent rain"
    elif precip > 0.2:
        result["condition"] = "mostly_dry"
        result["detail"] = "Roads mostly dry — trace precipitation"
    else:
        result["condition"] = "dry"
        result["detail"] = "Roads should be dry"

    return result


def compute_score(open_meteo, station_analysis, radar_analysis, wrf_analysis, time_window, road_conditions):
    """Compute the Palmas Ride Score (0–100)."""
    score = 100
    reasons = []

    tomorrow = get_tomorrow_date()
    morning = [
        h for h in open_meteo.get("hours", [])
        if h["date"] == tomorrow and RIDE_EARLIEST <= h["hour"] <= RIDE_LATEST
    ] if open_meteo["available"] else []

    # Rain probability
    if morning:
        avg_prob = sum(h["precip_prob"] for h in morning) / len(morning)
        if avg_prob > SCORING["rain_prob_high_threshold"]:
            score += SCORING["rain_prob_high_penalty"]
            reasons.append(f"High rain probability ({avg_prob:.0f}%) for {RIDE_WINDOW_LABEL}")
        else:
            reasons.append(f"Moderate/low rain probability ({avg_prob:.0f}%)")

        # Wind
        max_wind = max(h["wind_speed"] for h in morning)
        if max_wind > SCORING["high_wind_threshold"]:
            score += SCORING["high_wind_penalty"]
            reasons.append(f"Strong wind up to {max_wind:.0f} km/h")
        else:
            reasons.append(f"Low wind conditions (max {max_wind:.0f} km/h)")

        # Humidity
        avg_hum = sum(h["humidity"] for h in morning) / len(morning)
        if avg_hum > SCORING["high_humidity_threshold"]:
            score += SCORING["high_humidity_penalty"]
            reasons.append(f"Very high humidity ({avg_hum:.0f}%)")

    # Active rainfall from SIATA
    if station_analysis["raining"]:
        score += SCORING["active_rainfall_penalty"]
        reasons.append(station_analysis["reason"])
    elif station_analysis["station_count"] > 0:
        score += SCORING["no_recent_rain_bonus"]
        reasons.append("No current rainfall at nearby stations")

    # WRF
    if wrf_analysis.get("available") and wrf_analysis.get("high_rain"):
        reasons.append(wrf_analysis["reason"])

    # Dry window bonus
    if time_window.get("found") and time_window.get("dry"):
        score += SCORING["dry_window_bonus"]
        reasons.append(f"Dry forecast for full {RIDE_WINDOW_LABEL} window")
    elif time_window.get("found"):
        reasons.append(time_window["reason"])

    # Road conditions penalty
    if road_conditions["condition"] == "wet":
        score += SCORING["wet_road_penalty"]
        reasons.append(f"Wet roads — {road_conditions['detail']}")
    elif road_conditions["condition"] == "damp":
        score += SCORING["wet_road_penalty"] // 2
        reasons.append(f"Damp roads — {road_conditions['detail']}")
    else:
        reasons.append(f"Dry roads — {road_conditions['detail']}")

    score = max(0, min(100, score))
    confidence = "high" if score >= 70 else ("medium" if score >= 40 else "low")
    decision = "YES" if score >= 50 else "NO"

    return {"decision": decision, "score": score, "confidence": confidence, "reasons": reasons}
