# Source Map — Business Question → Data → System

| Business question | Information needed | Source system | Owner | Grain | Known gaps |
|---|---|---|---|---|---|
| How many trips happen, and when? | pickup/dropoff timestamps, counts | TLC Yellow Trip Records (Parquet) | TLC, sourced from TPEP vendors (Verifone/CMT) — TLC does not create this data itself | 1 row = 1 trip | TLC explicitly disclaims accuracy; vendor-submitted, so per-vendor quality varies and is not visible to us in the file itself |
| Which trips are unusually slow for their distance? | pickup/dropoff datetime, trip_distance, PULocationID | Same file | Same | Same | No ground-truth "expected duration" field exists — we must derive a baseline ourselves (see WORKFLOW_MODEL.md); this is a judgement call, not a given fact |
| Where geographically is delay concentrated? | LocationID → Borough/Zone mapping | TLC Taxi Zone Lookup (CSV) | TLC | 1 row = 1 of 265 zones | Zone 264/265 ("Unknown", "N/A") exist and must be handled, not silently joined away |
| Is weather a plausible cause of delay? | Hourly precipitation/snow for NYC | Open-Meteo Historical Weather API | Open-Meteo (aggregates NOAA/ECMWF reanalysis) | 1 row = 1 hour | Reanalysis weather is NYC-wide (JFK-area coordinate), not per-borough — a real limitation when attributing borough-level delay to weather |
| How much revenue is generated per unit of operational effort? | fare/total_amount, trip_distance | Same trip file | Same | Same | `total_amount` includes tolls/surcharges that vary by trip type (airport vs street-hail), which can distort revenue-per-mile if not segmented — flagged as an assumption, not fixed silently |

## Ownership note
None of these three systems are owned by "the business" in this project — they're all public data
substituting for what would, in a real engagement, be: (1) the dispatch/telematics system, (2) a
GIS/zones master table, (3) an external weather feed. The pipeline is written so swapping (1) or (3)
for a real internal system only requires changing `ingest.py`, not the validation/model/metrics layers.