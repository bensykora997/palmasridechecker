import json
import urllib.request
import ssl
from config import SIATA_URLS, PALMAS_BOUNDS
from cache import get_cached, set_cache

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

    def in_bounds(s, expand=0):
        lat = float(s.get("latitud", 0))
        lon = float(s.get("longitud", 0))
        return (
            PALMAS_BOUNDS["lat_min"] - expand <= lat <= PALMAS_BOUNDS["lat_max"] + expand
            and PALMAS_BOUNDS["lon_min"] - expand <= lon <= PALMAS_BOUNDS["lon_max"] + expand
        )

    def normalize(s):
        return {
            "name": s.get("nombre", ""),
            "code": s.get("codigo"),
            "lat": float(s.get("latitud", 0)),
            "lon": float(s.get("longitud", 0)),
            "value": float(s.get("valor", -999)),
            "neighborhood": s.get("barrio", ""),
            "city": s.get("ciudad", ""),
        }

    nearby = [s for s in data["estaciones"] if in_bounds(s)]
    expanded = False
    if not nearby:
        nearby = [s for s in data["estaciones"] if in_bounds(s, expand=0.05)]
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
