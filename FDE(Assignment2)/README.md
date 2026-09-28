# NYC TLC Trip Reliability & Efficiency Pipeline

## Problem
NYC taxi trips are the closest public analogue to a delivery workflow: a request (hail/dispatch),
a pickup, a transit period, and a dropoff, with a fare settled at the end. Leadership-style question:
**"How much of our trip time is being lost to unpredictable delay, where is it concentrated, and does
weather explain it?"** This mirrors the FlashEats late-delivery problem — instead of "late delivery
rate," the operational KPI here is **Delay Rate**: the share of trips whose actual duration is
implausibly long relative to the distance travelled, after removing trips that are broken data
rather than genuine slow trips.

## Users / stakeholders
- **TLC operations analyst** — wants to know which boroughs/hours produce the most unreliable trips.
- **Fleet/dispatch planning** — wants revenue efficiency (revenue per mile) to plan vehicle deployment.
- **A city policy team** — wants to know whether weather is a meaningful driver of delay, or whether
  delay is structural (congestion, time-of-day) regardless of weather.

## Project KPI
**Delay Rate (%)** — share of valid trips where actual duration exceeds 1.5x the expected duration
for that trip's distance and pickup borough (expected duration is derived from that borough's own
median speed, not an external assumption). Supporting metrics explain *why* the KPI moves.

## Source overview (see `docs/SOURCE_MAP.md` for full detail)
| # | Source | Type | Retrieval mode | Grain |
|---|--------|------|-----------------|-------|
| 1 | TLC Yellow Taxi Trip Records | Parquet file, monthly | File download (HTTPS) | 1 row = 1 trip |
| 2 | TLC Taxi Zone Lookup Table | CSV file | File download (HTTPS) | 1 row = 1 zone |
| 3 | Open-Meteo Historical Weather API | JSON API | REST API call | 1 row = 1 hour, NYC |

Two distinct retrieval modes are used: **file-based** (Parquet + CSV, TLC's own systems) and
**API-based** (Open-Meteo, a third-party system) — satisfying the "at least two retrieval modes"
requirement without inventing a fake SQL source.

## What the pipeline produces
`data/output/metrics_<month>.csv` and `data/output/metrics_<month>.md` — a 5-metric evidence table
(trip volume, average speed, delay rate, revenue per mile, weather-adjusted delay rate) plus a
validation report (`data/output/validation_report_<month>.json`) showing what was rejected and why.

## What decision this supports
Whether the Delay Rate metric moves meaningfully with weather (supporting a "surge/weather-based
dispatch buffer" intervention) or stays flat (pointing instead at structural congestion, e.g.
time-of-day or specific boroughs) — i.e., whether the client should invest in weather-responsive
routing/staffing or in congestion-specific interventions (e.g. Manhattan CBD dispatch caps).

## Setup
\`\`\`bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
\`\`\`

## Run
\`\`\`bash
python src/pipeline.py --month 2025-01
\`\`\`
Re-running is safe: each stage checks for existing outputs and skips re-downloading/re-validating
unless `--force` is passed. Logs go to `logs/pipeline_<month>.log` and stdout.

## Repo layout
\`\`\`
data/
  raw/            # untouched originals — never edited, kept for auditability
  rejected/       # rows that failed validation, with reason codes
  processed/      # modeled/joined trip-level table
  output/         # final metrics + validation report
docs/
  SOURCE_MAP.md
  WORKFLOW_MODEL.md
  KNOWN_UNKNOWN_ASSUMPTIONS.md
src/
  config.py
  ingest.py
  validate.py
  transform.py
  metrics.py
  pipeline.py
logs/
requirements.txt
README.md
\`\`\`