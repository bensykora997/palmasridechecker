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


def _fetch_json(url, label):
    cached = get_cached(url)
    if cached is not None:
        return cached
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PalmasRide/1.0"})
        with urllib.request.urlopen(req, timeout=10, context=_ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        set_cache(url, data)
        return data
    except Exception as e:
        print(f"[SIATA] Failed to fetch {label}: {e}")
        return None


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

    return {
        "stations": [normalize(s) for s in nearby],
        "available": True,
        "expanded": expanded,
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
