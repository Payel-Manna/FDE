"""
Stage 2: VALIDATE
Profiles the raw trip data and applies business-oriented validation rules.
Invalid rows are QUARANTINED (written to data/rejected/ with a reason code) rather than silently
dropped or silently fixed — the pipeline records what it did not trust, not just what it kept.
"""
import json
import logging
from pathlib import Path

import pandas as pd

import config

log = logging.getLogger("validate")

REQUIRED_COLS = [
    "tpep_pickup_datetime", "tpep_dropoff_datetime", "passenger_count",
    "trip_distance", "PULocationID", "DOLocationID", "fare_amount", "total_amount",
]


def profile(df: pd.DataFrame) -> dict:
    """Simple data profile — null rates, ranges, duplicate key rate. Logged, not acted on silently."""
    dupe_key = ["VendorID", "tpep_pickup_datetime", "PULocationID"]
    dupes = df.duplicated(subset=[c for c in dupe_key if c in df.columns]).sum()
    return {
        "n_rows": len(df),
        "null_rate": df[REQUIRED_COLS].isna().mean().round(4).to_dict(),
        "trip_distance_p50_p99": df["trip_distance"].quantile([0.5, 0.99]).round(2).to_dict(),
        "fare_amount_min_max": [float(df["fare_amount"].min()), float(df["fare_amount"].max())],
        "duplicate_key_rows": int(dupes),
    }


def validate(month: str) -> pd.DataFrame:
    trip_path = config.DATA_RAW / f"yellow_tripdata_{month}.parquet"
    df = pd.read_parquet(trip_path)

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise RuntimeError(f"Schema drift: missing required columns {missing}")

    report = {"month": month, "n_rows": len(df), "profile_before": profile(df)}

    df = df.copy()
    df["duration_sec"] = (df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]).dt.total_seconds()

    reasons = pd.Series([None] * len(df), index=df.index, dtype="object")

    def flag(mask, reason):
        nonlocal reasons
        reasons = reasons.mask(mask & reasons.isna(), reason)

    flag(df["tpep_dropoff_datetime"] <= df["tpep_pickup_datetime"], "dropoff_before_or_equal_pickup")
    flag(df["duration_sec"] < config.MIN_TRIP_DURATION_SEC, "duration_too_short")
    flag(df["duration_sec"] > config.MAX_TRIP_DURATION_SEC, "duration_too_long")
    flag(df["trip_distance"] <= 0, "zero_or_negative_distance")
    flag(df["trip_distance"] > config.MAX_TRIP_DISTANCE_MI, "distance_implausible")
    flag(df["fare_amount"] < 0, "negative_fare")
    flag(df["total_amount"] < 0, "negative_total")
    flag(~df["tpep_pickup_datetime"].dt.strftime("%Y-%m").eq(month), "pickup_outside_reporting_month")

    valid_mask = reasons.isna()
    df_valid = df[valid_mask].copy()
    df_rejected = df[~valid_mask].copy()
    df_rejected["reject_reason"] = reasons[~valid_mask]

    reject_path = config.DATA_REJECTED / f"rejected_{month}.csv"
    df_rejected.to_csv(reject_path, index=False)

    report["n_valid"] = int(valid_mask.sum())
    report["n_rejected"] = int((~valid_mask).sum())
    report["reject_reason_counts"] = df_rejected["reject_reason"].value_counts().to_dict()
    report["pct_rejected"] = round(100 * report["n_rejected"] / report["n_rows"], 3)

    report_path = config.DATA_OUTPUT / f"validation_report_{month}.json"
    report_path.write_text(json.dumps(report, indent=2, default=str))

    log.info(
        f"validated {report['n_rows']:,} rows -> {report['n_valid']:,} valid, "
        f"{report['n_rejected']:,} rejected ({report['pct_rejected']}%) — see {report_path.name}"
    )
    if report["pct_rejected"] > 15:
        # Business rule: >15% rejection means something structural changed upstream — stop, don't
        # silently continue on a possibly broken source file.
        raise RuntimeError(
            f"Rejection rate {report['pct_rejected']}% exceeds 15% threshold — "
            "halting rather than modeling on a likely-corrupt source file."
        )

    valid_path = config.DATA_PROCESSED / f"valid_trips_{month}.parquet"
    df_valid.to_parquet(valid_path, index=False)
    return df_valid


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    validate(sys.argv[1] if len(sys.argv) > 1 else "2025-01")