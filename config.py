# Waypoints along the Las Palmas climb, from the lower section near
# Las Palmas neighborhood up to Alto de Palmas. Stations are filtered
# by distance to the nearest waypoint (see CORRIDOR_RADIUS_KM).
PALMAS_ROUTE = [
    (6.2242, -75.5371),  # Seminario Redemptoris area (Las Palmas, start)
    (6.2200, -75.5350),
    (6.2150, -75.5300),
    (6.2100, -75.5230),
    (6.2050, -75.5150),
    (6.1980, -75.5070),
    (6.1900, -75.4980),
    (6.1820, -75.4900),
    (6.1750, -75.4820),  # Alto de Palmas (summit)
]

# Maximum distance (km) from any waypoint for a SIATA station to be
# considered "on Palmas". 2.5 km includes all stations directly on or
# adjacent to the road and excludes obvious off-route ones like Pan de
# Azucar and Guarne.
CORRIDOR_RADIUS_KM = 2.5

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
