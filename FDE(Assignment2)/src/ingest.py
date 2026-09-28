"""
Stage 1: INGEST
Retrieval mode A: file download (HTTPS) for TLC Parquet trip file + CSV zone lookup.
Retrieval mode B: REST API call (JSON) for Open-Meteo historical weather.
Raw inputs are preserved untouched in data/raw/ for auditability; nothing here mutates them.
"""
import calendar
import logging
import sys
from pathlib import Path

import pandas as pd
import requests

import config

log = logging.getLogger("ingest")


def _download_file(url: str, dest: Path, force: bool = False) -> Path:
    if dest.exists() and not force:
        log.info(f"[skip] {dest.name} already present ({dest.stat().st_size:,} bytes)")
        return dest
    log.info(f"downloading {url}")
    r = requests.get(url, stream=True, timeout=120)
    r.raise_for_status()
    tmp = dest.with_suffix(dest.suffix + ".part")
    total = 0
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 20):
            f.write(chunk)
            total += len(chunk)
    tmp.rename(dest)
    log.info(f"[ok] saved {dest.name} ({total:,} bytes)")
    return dest


def ingest_trips(month: str, force: bool = False) -> Path:
    dest = config.DATA_RAW / f"yellow_tripdata_{month}.parquet"
    url = config.yellow_trip_url(month)
    _download_file(url, dest, force)

    # Completeness check: can we actually read it, and does row count look sane?
    df = pd.read_parquet(dest, columns=["tpep_pickup_datetime"])
    n = len(df)
    if n < 10_000:
        raise RuntimeError(
            f"Retrieval looks incomplete: only {n} rows in {dest.name}. "
            "Expected hundreds of thousands for a full monthly file."
        )
    log.info(f"[verified] {dest.name}: {n:,} rows retrieved")
    return dest


def ingest_zone_lookup(force: bool = False) -> Path:
    dest = config.DATA_RAW / "taxi_zone_lookup.csv"
    _download_file(config.ZONE_LOOKUP_URL, dest, force)
    df = pd.read_csv(dest)
    expected_cols = {"LocationID", "Borough", "Zone", "service_zone"}
    if not expected_cols.issubset(df.columns):
        raise RuntimeError(f"Zone lookup schema drifted: got columns {list(df.columns)}")
    if len(df) < 250:
        raise RuntimeError(f"Zone lookup looks incomplete: only {len(df)} zones (expected ~265).")
    log.info(f"[verified] zone lookup: {len(df)} zones")
    return dest


def ingest_weather(month: str, force: bool = False) -> Path:
    """API retrieval mode: Open-Meteo historical archive, hourly, for NYC."""
    dest = config.DATA_RAW / f"weather_{month}.json"
    if dest.exists() and not force:
        log.info(f"[skip] {dest.name} already present")
        return dest

    year, mon = map(int, month.split("-"))
    last_day = calendar.monthrange(year, mon)[1]
    start_date, end_date = f"{month}-01", f"{month}-{last_day:02d}"

    params = {
        "latitude": config.NYC_LAT,
        "longitude": config.NYC_LON,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "precipitation,snowfall,temperature_2m",
        "timezone": "America/New_York",
    }
    log.info(f"calling Open-Meteo API for {start_date}..{end_date}")
    r = requests.get(config.WEATHER_API, params=params, timeout=60)
    r.raise_for_status()
    payload = r.json()
    hourly = payload.get("hourly", {})
    n_hours = len(hourly.get("time", []))
    expected_hours = last_day * 24
    if n_hours < expected_hours * 0.95:
        raise RuntimeError(
            f"Weather retrieval incomplete: got {n_hours} hourly records, "
            f"expected ~{expected_hours}."
        )
    dest.write_text(r.text)
    log.info(f"[verified] weather: {n_hours} hourly records saved to {dest.name}")
    return dest


def run(month: str, force: bool = False):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    trip_path = ingest_trips(month, force)
    zone_path = ingest_zone_lookup(force)
    weather_path = ingest_weather(month, force)
    return trip_path, zone_path, weather_path


if __name__ == "__main__":
    month = sys.argv[1] if len(sys.argv) > 1 else "2025-01"
    run(month)