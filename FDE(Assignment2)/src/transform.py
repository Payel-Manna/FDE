"""
Stage 3: TRANSFORM / MODEL
Joins validated trips against the zone dimension and the weather dimension, then computes the
derived workflow fields described in docs/WORKFLOW_MODEL.md (duration, speed, expected duration,
delay flag, rush-hour flag, revenue per mile).
"""
import json
import logging

import pandas as pd

import config

log = logging.getLogger("transform")


def load_zones() -> pd.DataFrame:
    z = pd.read_csv(config.DATA_RAW / "taxi_zone_lookup.csv")
    return z[["LocationID", "Borough", "Zone"]]


def load_weather(month: str) -> pd.DataFrame:
    payload = json.loads((config.DATA_RAW / f"weather_{month}.json").read_text())
    hourly = payload["hourly"]
    w = pd.DataFrame({
        "hour_ts": pd.to_datetime(hourly["time"]),
        "precipitation_mm": hourly["precipitation"],
        "snowfall_cm": hourly["snowfall"],
        "temperature_c": hourly["temperature_2m"],
    })
    w["is_wet_hour"] = (w["precipitation_mm"] > 0.1) | (w["snowfall_cm"] > 0.1)
    return w


def transform(month: str) -> pd.DataFrame:
    df = pd.read_parquet(config.DATA_PROCESSED / f"valid_trips_{month}.parquet")
    zones = load_zones()
    weather = load_weather(month)

    # Join pickup borough
    df = df.merge(
        zones.rename(columns={"LocationID": "PULocationID", "Borough": "pickup_borough", "Zone": "pickup_zone"}),
        on="PULocationID", how="left",
    )
    unmapped = df["pickup_borough"].isna().sum()
    if unmapped:
        log.warning(f"{unmapped} trips have a PULocationID not in the zone lookup (Unknown/N/A zones) — kept, tagged 'Unknown'")
    df["pickup_borough"] = df["pickup_borough"].fillna("Unknown")

    # Derived fields
    df["duration_sec"] = (df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]).dt.total_seconds()
    df["avg_speed_mph"] = df["trip_distance"] / (df["duration_sec"] / 3600)

    # Data-error guard: implausible speed is a GPS/meter fault, not a genuine (fast) trip.
    df["speed_is_plausible"] = df["avg_speed_mph"] <= config.MAX_PLAUSIBLE_SPEED_MPH

    # Expected duration baseline: per-borough median speed, computed from this month's plausible trips.
    plausible = df[df["speed_is_plausible"]]
    borough_median_speed = plausible.groupby("pickup_borough")["avg_speed_mph"].median()
    df["borough_median_speed_mph"] = df["pickup_borough"].map(borough_median_speed).fillna(
        plausible["avg_speed_mph"].median()
    )
    df["expected_duration_sec"] = (df["trip_distance"] / df["borough_median_speed_mph"]) * 3600

    df["delay_flag"] = (
        df["speed_is_plausible"]
        & (df["duration_sec"] > config.DELAY_THRESHOLD_MULT * df["expected_duration_sec"])
    )

    # Weather join on pickup hour
    df["pickup_hour_ts"] = df["tpep_pickup_datetime"].dt.floor("h")
    df = df.merge(weather, left_on="pickup_hour_ts", right_on="hour_ts", how="left")
    df["is_wet_hour"] = df["is_wet_hour"].fillna(False)

    # Rush hour flag
    df["is_rush_hour"] = df["tpep_pickup_datetime"].dt.hour.isin(config.RUSH_HOURS)

    # Revenue efficiency
    df["revenue_per_mile"] = df["total_amount"] / df["trip_distance"]

    out_path = config.DATA_PROCESSED / f"modeled_trips_{month}.parquet"
    df.to_parquet(out_path, index=False)
    log.info(f"modeled {len(df):,} trips -> {out_path.name}")
    return df


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    transform(sys.argv[1] if len(sys.argv) > 1 else "2025-01")