"""
Stage 4: METRICS
Aggregates the modeled trip table into the final 5-metric evidence table for the KPI.
"""
import logging

import pandas as pd

import config

log = logging.getLogger("metrics")


def compute_metrics(month: str) -> pd.DataFrame:
    df = pd.read_parquet(config.DATA_PROCESSED / f"modeled_trips_{month}.parquet")
    plausible = df[df["speed_is_plausible"]]

    rows = []
    rows.append({"metric": "Trip Volume", "value": len(df), "unit": "trips",
                 "note": "all validated trips this month"})
    rows.append({"metric": "Average Trip Speed", "value": round(plausible["avg_speed_mph"].mean(), 2),
                 "unit": "mph", "note": "excludes speed-implausible (GPS/meter fault) trips"})
    rows.append({"metric": "Delay Rate", "value": round(100 * df["delay_flag"].mean(), 2),
                 "unit": "%", "note": "share of trips > 1.5x expected duration for distance & borough"})
    # Revenue-per-mile is a right-skewed ratio: very short trips with flat/minimum fares (e.g.
    # 0.1mi + tolls) produce extreme values that blow up a mean. Median is the honest central
    # tendency here; mean is reported alongside so the skew itself is visible, not hidden.
    rpm = df["revenue_per_mile"].replace([float("inf"), float("-inf")], None).dropna()
    short_trip_pct = round(100 * (df["trip_distance"] < 0.3).mean(), 2)
    rows.append({"metric": "Revenue per Mile", "value": round(rpm.median(), 2),
                 "unit": "$/mi",
                 "note": f"median (mean=${rpm.mean():.2f}, skewed by short trips; "
                         f"{short_trip_pct}% of trips are under 0.3mi)"})

    wet_rate = 100 * df.loc[df["is_wet_hour"], "delay_flag"].mean() if df["is_wet_hour"].any() else float("nan")
    dry_rate = 100 * df.loc[~df["is_wet_hour"], "delay_flag"].mean()
    rush_rate = 100 * df.loc[df["is_rush_hour"], "delay_flag"].mean()
    offpeak_rate = 100 * df.loc[~df["is_rush_hour"], "delay_flag"].mean()
    rows.append({
        "metric": "Weather/Rush-Adjusted Delay Rate",
        "value": f"wet={wet_rate:.2f}% / dry={dry_rate:.2f}% / rush={rush_rate:.2f}% / off-peak={offpeak_rate:.2f}%",
        "unit": "%", "note": "isolates whether weather or time-of-day better explains delay",
    })

    metrics_df = pd.DataFrame(rows)
    csv_path = config.DATA_OUTPUT / f"metrics_{month}.csv"
    md_path = config.DATA_OUTPUT / f"metrics_{month}.md"
    metrics_df.to_csv(csv_path, index=False)
    md_path.write_text(metrics_df.to_markdown(index=False))
    log.info(f"metrics written -> {csv_path.name}, {md_path.name}")
    return metrics_df


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    print(compute_metrics(sys.argv[1] if len(sys.argv) > 1 else "2025-01"))