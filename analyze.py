from datetime import datetime, timedelta
from config import SCORING, RIDE_EARLIEST, RIDE_LATEST, RIDE_WINDOW_LABEL
from timeutil import now_bogota, today_str, tomorrow_str, target_date_str, evening_before


def get_target_date():
    """The date being predicted for — time-aware: today's morning before the
    08:00 cutoff, tomorrow's after. See timeutil.target_date_str()."""
    return target_date_str()


# Backwards-compatible alias (older call sites / external refs).
def get_tomorrow_date():
    return get_target_date()


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


# SIATA pluvio stations often report sub-millimeter "noise" values
# (e.g. 0.02 mm) that don't correspond to actual rainfall. Use the same
# 0.1 mm threshold we use for Open-Meteo precipitation elsewhere.
RAIN_THRESHOLD_MM = 0.1
# Rain in the last hour: slightly higher threshold to avoid trace 24h
# spillover (a brief shower yesterday should not still register as "raining now").
P1H_RAIN_THRESHOLD_MM = 0.5


def _val(s, key):
    """Return s[key] as a non-None positive number, else None."""
    v = s.get(key)
    if v is None or (isinstance(v, (int, float)) and v == -999):
        return None
    return v


def analyze_stations(pluvio):
    """Decide if Palmas-area stations are reporting active rainfall.

    Considers four signals per station (any one above its threshold flips
    the station to "raining"):
      - valor   ≥ 0.1   (current snapshot from the summary file)
      - p10m    ≥ 0.1   (rain in the last 10 minutes, from detail file)
      - p1h     ≥ 0.5   (rain in the last hour, from detail file)
    `p24h` is surfaced for downstream use (road conditions) but doesn't
    by itself flag "currently raining" — yesterday's shower may have
    already evaporated by now.
    """
    if not pluvio["available"] or not pluvio["stations"]:
        return {
            "raining": False, "station_count": 0, "offline_count": 0,
            "active_stations": [], "trace_stations": [],
            "reason": "No nearby stations",
            "live_signals": {},
        }

    stations = pluvio["stations"]

    def is_raining(s):
        valor = _val(s, "value")
        p10m  = _val(s, "p10m")
        p1h   = _val(s, "p1h")
        if valor is not None and valor >= RAIN_THRESHOLD_MM:
            return True, "valor"
        if p10m is not None and p10m >= RAIN_THRESHOLD_MM:
            return True, "p10m"
        if p1h is not None and p1h >= P1H_RAIN_THRESHOLD_MM:
            return True, "p1h"
        return False, None

    active = []
    raining_via = None
    for s in stations:
        flag, source = is_raining(s)
        if flag:
            active.append(s)
            raining_via = raining_via or source

    # A station is "offline" if either: its summary value is -999, OR its
    # detail-file rainfall sensors are all -999 (zombie sensor reporting a
    # stale residual `valor` while the real sensor is dead). This matches
    # the per-station `offline` flag the map UI uses, so the count in
    # data_sources.siata_stations.offline agrees with what users see on
    # the map.
    def _offline(s):
        if s.get("value") == -999:
            return True
        # detail_available=False means we never got a detail file; conservative
        # default — don't count as offline if we can't tell.
        if s.get("detail_available") is False:
            return False
        return s.get("sensor_live") is False

    offline = [s for s in stations if _offline(s)]
    trace = [s for s in stations
             if 0 < (s.get("value") or 0) < RAIN_THRESHOLD_MM and s.get("value") != -999
             and not any(_val(s, k) is not None and _val(s, k) >= RAIN_THRESHOLD_MM for k in ("p10m", "p1h"))]

    if active:
        reason = f"{len(active)} station(s) reporting rain (via {raining_via})"
    elif trace:
        reason = f"No meaningful rain ({len(trace)} station(s) with trace amounts)"
    else:
        reason = "No stations reporting rain"

    # Aggregate live signals across the corridor for the response payload
    def safe_max(xs):
        vals = [x for x in xs if x is not None]
        return round(max(vals), 2) if vals else 0.0

    def safe_avg(xs):
        vals = [x for x in xs if x is not None]
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    valor_vals = [_val(s, "value") for s in stations]
    p10m_vals = [_val(s, "p10m") for s in stations]
    p1h_vals  = [_val(s, "p1h")  for s in stations]
    p24h_vals = [_val(s, "p24h") for s in stations]

    live_signals = {
        "valor_max": safe_max(valor_vals),
        "p10m_max":  safe_max(p10m_vals),
        "p1h_max":   safe_max(p1h_vals),
        "p24h_max":  safe_max(p24h_vals),
        "p24h_avg":  safe_avg(p24h_vals),
        "raining_via": raining_via,
    }

    return {
        "raining": len(active) > 0,
        "active_stations": [{"name": s["name"], "rainfall": s.get("value"),
                             "p10m": s.get("p10m"), "p1h": s.get("p1h"), "p24h": s.get("p24h")}
                            for s in active],
        "trace_stations": [{"name": s["name"], "rainfall": s["value"]} for s in trace],
        "station_count": len(stations),
        "offline_count": len(offline),
        "reason": reason,
        "live_signals": live_signals,
        "p24h_avg": live_signals["p24h_avg"],   # convenience for road analysis
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
        target = get_target_date()
        # Hours leading up to the target ride: the evening before (20:00+) through
        # the overnight hours of the ride day (before RIDE_EARLIEST). Relative to
        # the target date so it shifts correctly for the "this morning" view.
        prev_evening = evening_before(target)
        pre_ride = [
            h for h in open_meteo["hours"]
            if (h["date"] == prev_evening and h["hour"] >= 20)
            or (h["date"] == target and h["hour"] < RIDE_EARLIEST)
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

    # SIATA p24h: average rainfall in the last 24h across the corridor.
    # This captures microclimate rain that Open-Meteo's interpolated grid
    # may have missed (the Palmas microclimate vs Medellín valley problem).
    siata_p24h = station_analysis.get("p24h_avg", 0.0) or 0.0
    if siata_p24h > 0.2:
        result["factors"].append(f"SIATA stations recorded {siata_p24h:.1f} mm avg in last 24h")
    result["siata_p24h_avg_mm"] = siata_p24h

    # Determine condition: take the worst-case of Open-Meteo overnight
    # precip vs SIATA p24h average. If either source says it rained,
    # treat the road accordingly.
    precip = result["recent_precip_mm"]
    is_raining = station_analysis.get("raining", False)
    worst = max(precip, siata_p24h)

    if is_raining:
        result["condition"] = "wet"
        result["detail"] = "Roads are wet — active rainfall"
    elif worst > 5:
        result["condition"] = "wet"
        if siata_p24h > precip:
            result["detail"] = f"Roads likely wet — SIATA recorded {siata_p24h:.1f} mm at Palmas in last 24h"
        else:
            result["detail"] = "Roads likely wet — heavy recent rain"
    elif worst > 1:
        result["condition"] = "damp"
        if siata_p24h > precip:
            result["detail"] = f"Roads may be damp — SIATA recorded {siata_p24h:.1f} mm at Palmas in last 24h"
        else:
            result["detail"] = "Roads may be damp — light recent rain"
    elif worst > 0.2:
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
