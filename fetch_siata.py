import json
import math
import time
import urllib.request
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def _fetch_station_detail(station_code, timeout=3):
    """Fetch and parse a station's detail file `{code}.json`.

    Returns a dict with normalized rainfall fields (None where -999 / missing):
      {
        "p10m": float or None,
        "p1h":  float or None,
        "p24h": float or None,
        "date": float or None,    # Unix timestamp the station last reported
        "age_seconds": float or None,
        "available": bool,
      }

    Network errors → {"available": False, ...}. Cached by URL via cache.py.
    """
    blank = {"p10m": None, "p1h": None, "p24h": None,
             "date": None, "age_seconds": None, "available": False}
    if not station_code:
        return blank
    detail = _fetch_json(
        f"https://siata.gov.co/data/siata_app/{station_code}.json",
        f"station detail {station_code}",
        timeout=timeout,
    )
    if not detail:
        return blank

    def f(key):
        v = detail.get(key)
        try:
            fv = float(v)
            if fv == -999:
                return None
            return fv
        except (TypeError, ValueError):
            return None

    date_val = f("date")
    age = (time.time() - date_val) if date_val else None
    return {
        "p10m": f("p10m"),
        "p1h":  f("p1h"),
        "p24h": f("p24h"),
        "date": date_val,
        "age_seconds": age,
        "available": True,
    }


def _is_rainfall_sensor_live(detail):
    """Given a normalized detail dict (from _fetch_station_detail), does the
    rainfall sensor have any real reading?

    Falls back to True if the detail file was unreachable (conservative — we'd
    rather keep the summary `valor` on a network blip than drop possibly-real
    data).
    """
    if not detail or not detail.get("available"):
        return True
    return any(detail.get(k) is not None for k in ("p10m", "p1h", "p24h"))


def _enrich_stations(stations):
    """Fetch each station's detail file in parallel and merge p10m/p1h/p24h
    into the station dicts. Bounded by ThreadPoolExecutor to keep latency
    under ~4s even with 15+ stations.
    """
    if not stations:
        return

    def task(s):
        return s, _fetch_station_detail(s.get("code"))

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(task, s) for s in stations]
        for fut in as_completed(futures):
            try:
                s, detail = fut.result()
            except Exception as e:
                print(f"[SIATA] station enrich failed: {e}")
                continue
            s["p10m"] = detail.get("p10m")
            s["p1h"] = detail.get("p1h")
            s["p24h"] = detail.get("p24h")
            s["detail_age_seconds"] = detail.get("age_seconds")
            s["detail_available"] = detail.get("available", False)
            s["sensor_live"] = _is_rainfall_sensor_live(detail)


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

    # Enrich every corridor station with its detail file (p10m/p1h/p24h).
    # This is what lets us detect rain that the summary `valor` snapshot
    # misses (e.g. rain in the last hour that has since stopped, or a
    # microclimate event captured by the rolling totals but not by the
    # current-instant value). Cross-check for dead sensors at the same time.
    _enrich_stations(stations)

    verified_offline = []
    for s in stations:
        # A station with valor >= 0.1 but all detail-file rainfall fields
        # reporting None (-999) has a dead rain sensor — drop its value.
        if s.get("value", -999) >= 0.1 and s.get("value") != -999 and not s.get("sensor_live", True):
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
