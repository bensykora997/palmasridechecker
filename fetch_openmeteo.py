import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from config import PALMAS_CENTER, OPEN_METEO_URL, RIDE_EARLIEST, RIDE_LATEST
from cache import get_cached, set_cache


def fetch_openmeteo():
    """Fetches hourly forecast from Open-Meteo for Palmas coordinates."""
    cache_key = "open-meteo-hourly"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    params = urllib.parse.urlencode({
        "latitude": PALMAS_CENTER["lat"],
        "longitude": PALMAS_CENTER["lon"],
        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation_probability",
            "precipitation",
            "wind_speed_10m",
            "weather_code",
        ]),
        "timezone": "America/Bogota",
        "forecast_days": "2",
        "past_days": "1",
    })

    url = f"{OPEN_METEO_URL}?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PalmasRide/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        hourly = data["hourly"]
        hours = []
        for i, t in enumerate(hourly["time"]):
            # time format: "2026-04-14T05:00"
            hour = int(t[11:13])
            hours.append({
                "time": t,
                "date": t[:10],
                "hour": hour,
                "temp": hourly["temperature_2m"][i],
                "humidity": hourly["relative_humidity_2m"][i],
                "precip_prob": hourly["precipitation_probability"][i],
                "precip": hourly["precipitation"][i],
                "wind_speed": hourly["wind_speed_10m"][i],
                "weather_code": hourly["weather_code"][i],
            })

        result = {"hours": hours, "available": True}
        set_cache(cache_key, result)
        return result

    except Exception as e:
        print(f"[Open-Meteo] Failed: {e}")
        return {"hours": [], "available": False}


def fetch_actuals_for_date(target_date_str):
    """Fetch observed weather for the ride window on a past date.

    Returns dict with precip_mm, max_wind, rained, or None if unavailable.
    Uses Open-Meteo's archived/forecast endpoint with past_days. Reliable
    for dates within the past ~7 days.
    """
    target = datetime.strptime(target_date_str, "%Y-%m-%d")
    days_ago = (datetime.now().date() - target.date()).days
    if days_ago < 1:
        return None  # not in the past
    past_days = max(min(days_ago + 1, 14), 2)

    params = urllib.parse.urlencode({
        "latitude": PALMAS_CENTER["lat"],
        "longitude": PALMAS_CENTER["lon"],
        "hourly": ",".join(["precipitation", "wind_speed_10m"]),
        "timezone": "America/Bogota",
        "forecast_days": "1",
        "past_days": str(past_days),
    })
    url = f"{OPEN_METEO_URL}?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PalmasRide/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        hourly = data["hourly"]
        precip_total = 0.0
        max_wind = 0.0
        hits = 0
        for i, t in enumerate(hourly["time"]):
            if t[:10] != target_date_str:
                continue
            hour = int(t[11:13])
            if RIDE_EARLIEST <= hour <= RIDE_LATEST:
                precip_total += hourly["precipitation"][i] or 0
                max_wind = max(max_wind, hourly["wind_speed_10m"][i] or 0)
                hits += 1
        if hits == 0:
            return None
        return {
            "precip_mm": round(precip_total, 2),
            "max_wind": round(max_wind, 1),
            "rained": precip_total > 0.1,
        }
    except Exception as e:
        print(f"[Open-Meteo actuals] Failed for {target_date_str}: {e}")
        return None
