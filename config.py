# Geometry of Avenida de Las Palmas pulled from OpenStreetMap
# (way ref=56). PALMAS_ROUTE_SEGMENTS is a list of ordered segments
# suitable for drawing on a map. PALMAS_ROUTE is the flattened set of
# waypoints used for corridor-distance filtering.
from palmas_route_data import ROUTE_SEGMENTS as PALMAS_ROUTE_SEGMENTS

PALMAS_ROUTE = [pt for seg in PALMAS_ROUTE_SEGMENTS for pt in seg]

# Maximum distance (km) from any waypoint for a SIATA station to be
# considered "on Palmas". With dense OSM waypoints this can be much
# tighter than the original 2.5 km — 1.5 km cleanly captures stations
# directly on the road or in adjacent neighborhoods, and excludes
# nearby-but-different microclimate areas.
CORRIDOR_RADIUS_KM = 1.5

# Palmas center for Open-Meteo queries (no change in behavior)
PALMAS_CENTER = {"lat": 6.20, "lon": -75.50}

# SIATA endpoints
SIATA_URLS = {
    "pluviometrica": "https://siata.gov.co/data/siata_app/Pluviometrica.json",
    "radar": "https://siata.gov.co/data/siata_app/animacion_radar.json",
    "wrf_centro": "https://siata.gov.co/data/siata_app/wrfmedCentro.json",
    "wrf_envigado": "https://siata.gov.co/data/siata_app/wrfenvigado.json",
}

# Open-Meteo (free, no key needed)
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Scoring
SCORING = {
    "rain_prob_high_threshold": 60,
    "rain_prob_high_penalty": -40,
    "active_rainfall_penalty": -50,
    "radar_precip_penalty": -40,
    "high_wind_threshold": 20,
    "high_wind_penalty": -15,
    "high_humidity_threshold": 90,
    "high_humidity_penalty": -10,
    "dry_window_bonus": 25,
    "no_recent_rain_bonus": 10,
    "wet_road_penalty": -15,
}

# Analysis window
RIDE_EARLIEST = 5    # 5:00 AM
RIDE_LATEST = 7      # covers up to 7:30 AM (hour 7 slot = 7:00–7:59)
RIDE_WINDOW_LABEL = "05:00 – 07:30"

CACHE_TTL_SECONDS = 300  # 5 minutes
