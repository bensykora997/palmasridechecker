"""Air quality from Open-Meteo Air Quality API (free, no key)."""

import json
import urllib.request
import urllib.parse
from config import PALMAS_CENTER
from cache import get_cached, set_cache

OPEN_METEO_AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def _aqi_label(us_aqi):
    """US EPA AQI category label and color tier."""
    if us_aqi is None:
        return "unknown", "unknown"
    if us_aqi <= 50:   return "Good", "good"
    if us_aqi <= 100:  return "Moderate", "moderate"
    if us_aqi <= 150:  return "Unhealthy (sensitive)", "usg"
    if us_aqi <= 200:  return "Unhealthy", "unhealthy"
    if us_aqi <= 300:  return "Very Unhealthy", "very_unhealthy"
    return "Hazardous", "hazardous"


def fetch_air_quality():
    """Returns current AQI + PM2.5 / PM10 for Palmas."""
    cache_key = "open-meteo-air"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    params = urllib.parse.urlencode({
        "latitude": PALMAS_CENTER["lat"],
        "longitude": PALMAS_CENTER["lon"],
        "current": "pm10,pm2_5,us_aqi,european_aqi",
        "timezone": "America/Bogota",
    })
    url = f"{OPEN_METEO_AIR_URL}?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PalmasRide/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        cur = data.get("current", {}) or {}
        us = cur.get("us_aqi")
        label, tier = _aqi_label(us)
        result = {
            "available": True,
            "pm2_5": cur.get("pm2_5"),
            "pm10": cur.get("pm10"),
            "us_aqi": us,
            "european_aqi": cur.get("european_aqi"),
            "label": label,
            "tier": tier,
            "time": cur.get("time"),
        }
        set_cache(cache_key, result)
        return result
    except Exception as e:
        print(f"[Open-Meteo Air] Failed: {e}")
        return {"available": False}
