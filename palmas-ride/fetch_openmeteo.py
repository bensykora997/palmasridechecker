import json
import urllib.request
import urllib.parse
from config import PALMAS_CENTER, OPEN_METEO_URL
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
