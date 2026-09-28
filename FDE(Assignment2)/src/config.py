"""Central configuration — single source of truth for paths, URLs, and thresholds."""
from pathlib import Path

# ---- Paths -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_REJECTED = ROOT / "data" / "rejected"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_OUTPUT = ROOT / "data" / "output"
LOG_DIR = ROOT / "logs"

for d in (DATA_RAW, DATA_REJECTED, DATA_PROCESSED, DATA_OUTPUT, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---- Source URLs (verified live on the TLC site before shipping this) ------
TLC_BASE = "https://d37ci6vzurychx.cloudfront.net/trip-data"
ZONE_LOOKUP_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
WEATHER_API = "https://archive-api.open-meteo.com/v1/archive"
NYC_LAT, NYC_LON = 40.7128, -74.0060

def yellow_trip_url(month: str) -> str:
    """month format: 'YYYY-MM'"""
    return f"{TLC_BASE}/yellow_tripdata_{month}.parquet"

# ---- Business thresholds (documented, not buried in code) -----------------
MAX_PLAUSIBLE_SPEED_MPH = 65        # above this: treated as GPS/meter data error
MIN_TRIP_DURATION_SEC = 60          # below this: not a real trip (likely cancel/glitch)
MAX_TRIP_DURATION_SEC = 6 * 3600    # above this: data error, driver forgot to close meter
MAX_TRIP_DISTANCE_MI = 100          # above this: data error for an in-city taxi trip
DELAY_THRESHOLD_MULT = 1.5          # actual duration > 1.5x expected => delayed
RUSH_HOURS = {7, 8, 9, 16, 17, 18}  # local hour-of-day