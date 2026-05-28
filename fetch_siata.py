import json
import math
import urllib.request
import ssl
from config import SIATA_URLS, PALMAS_ROUTE, CORRIDOR_RADIUS_KM
from cache import get_cached, set_cache


def _haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two lat/lon points, in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def _distance_to_route_km(lat, lon):
    """Min distance from a point to any waypoint along the Palmas route."""
    return min(_haversine_km(lat, lon, wlat, wlon) for wlat, wlon in PALMAS_ROUTE)

# Relaxed SSL context for SIATA endpoints
_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE


def _fetch_json(url, label, timeout=10):
    cached = get_cached(url)
    if cached is not None:
        return cached
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PalmasRide/1.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        set_cache(url, data)
        return data
    except Exception as e:
        print(f"[SIATA] Failed to fetch {label}: {e}")
        return None


def _is_rainfall_sensor_live(station_code):
    """Cross-check a station's rainfall sensor by hitting its detail file.

    SIATA's summary Pluviometrica.json sometimes serves a stale residual
    value (e.g. 0.02 mm) from a station whose rainfall sensor has actually
    gone offline. The per-station detail file `{code}.json` exposes the
    real-time state via p10m / p1h / p24h. If all three report -999, the
    rainfall sensor is offline and the summary value should be ignored.

    Returns True if at least one rainfall timescale has a real reading.
    Falls back to True if the detail file is unreachable — better to trust
    the summary than discard a possibly-real reading on a network blip.
    """
    if not station_code:
        return True
    detail = _fetch_json(
        f"https://siata.gov.co/data/siata_app/{station_code}.json",
        f"station detail {station_code}",
        timeout=5,
    )
    if not detail:
        return True
    for key in ("p10m", "p1h", "p24h"):
        v = detail.get(key)
        try:
            if float(v) != -999:
                return True
        except (TypeError, ValueError):
            continue
    return False


def fetch_pluviometrica():
    """Returns pluviometric stations near Palmas with current rainfall values."""
    data = _fetch_json(SIATA_URLS["pluviometrica"], "Pluviometrica")
    if not data or "estaciones" not in data:
        return {"stations": [], "available": False}

    def near_route(s, radius_km):
        try:
            lat = float(s.get("latitud", 0))
            lon = float(s.get("longitud", 0))
        except (TypeError, ValueError):
            return False
        return _distance_to_route_km(lat, lon) <= radius_km

    def normalize(s):
        lat = float(s.get("latitud", 0))
        lon = float(s.get("longitud", 0))
        return {
            "name": s.get("nombre", ""),
            "code": s.get("codigo"),
            "lat": lat,
            "lon": lon,
            "value": float(s.get("valor", -999)),
            "neighborhood": s.get("barrio", ""),
            "city": s.get("ciudad", ""),
            "distance_km": round(_distance_to_route_km(lat, lon), 2),
        }

    nearby = [s for s in data["estaciones"] if near_route(s, CORRIDOR_RADIUS_KM)]
    expanded = False
    # Fallback: if nothing within the corridor, widen to 2x radius rather
    # than silently returning zero stations.
    if not nearby:
        nearby = [s for s in data["estaciones"] if near_route(s, CORRIDOR_RADIUS_KM * 2)]
        expanded = True

    stations = [normalize(s) for s in nearby]

    # Cross-check: for any station whose summary value would count as
    # "raining" (>= 0.1 mm), verify the rainfall sensor is actually live
    # by hitting the detail file. If all rainfall timescales report -999
    # we treat the station as offline (-999) so the score isn't anchored
    # to a stale residual reading from a dead sensor.
    verified_offline = []
    for s in stations:
        if s["value"] >= 0.1 and s["value"] != -999:
            if not _is_rainfall_sensor_live(s["code"]):
                verified_offline.append(s["name"])
                s["value"] = -999

    return {
        "stations": stations,
        "available": True,
        "expanded": expanded,
        "verified_offline": verified_offline,
    }


def fetch_radar():
    """Returns radar animation metadata."""
    data = _fetch_json(SIATA_URLS["radar"], "Radar")
    if not data or "urls" not in data:
        return {"frames": [], "available": False}

    return {
        "bounds": {
            "north": data.get("north"),
            "south": data.get("south"),
            "east": data.get("east"),
            "west": data.get("west"),
        },
        "frames": [{"time": u["time"], "image": u["image"]} for u in data["urls"]],
        "available": True,
    }


def fetch_wrf_forecast():
    """Returns WRF forecast for Centro and Envigado zones."""
    centro = _fetch_json(SIATA_URLS["wrf_centro"], "WRF Centro")
    envigado = _fetch_json(SIATA_URLS["wrf_envigado"], "WRF Envigado")

    def parse(data, zone):
        if not data or "pronostico" not in data:
            return []
        return [
            {
                "zone": zone,
                "date": d.get("fecha", ""),
                "temp_max": _int_or(d.get("temperatura_maxima"), 0),
                "temp_min": _int_or(d.get("temperatura_minima"), 0),
                "rain_early_morning": d.get("lluvia_madrugada", ""),
                "rain_morning": d.get("lluvia_mannana", ""),
                "rain_afternoon": d.get("lluvia_tarde", ""),
                "rain_night": d.get("lluvia_noche", ""),
            }
            for d in data["pronostico"]
        ]

    return {
        "centro": parse(centro, "Centro"),
        "envigado": parse(envigado, "Envigado"),
        "available": bool(centro or envigado),
    }


def _int_or(val, default):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default
