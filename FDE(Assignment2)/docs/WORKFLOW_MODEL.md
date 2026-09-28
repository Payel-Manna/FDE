# Workflow Model

## Entities
- **Trip** (fact): one taxi trip, keyed by (VendorID, pickup_datetime, PULocationID) — TLC trip
  files have no natural trip ID, which is itself a data-quality note (see Known/Unknown doc).
- **Zone** (dimension): LocationID → Borough, Zone name, service_zone.
- **WeatherHour** (dimension): date + hour → precipitation_mm, snowfall_cm, temperature_c.

## Events / states per trip
1. **Pickup** — `tpep_pickup_datetime`, `PULocationID` (trip begins).
2. **Dropoff** — `tpep_dropoff_datetime`, `DOLocationID` (trip ends, fare settles).
3. Derived state: **duration_sec**, **distance_mi**, **avg_speed_mph** = distance / (duration/3600).
4. Derived state: **expected_duration_sec** = distance_mi / borough_median_speed_mph(pickup borough) × 3600.
5. Derived outcome: **delay_flag** = 1 if duration_sec > 1.5 × expected_duration_sec AND duration_sec
   is itself plausible (see validation rules — this guards against flagging broken GPS data as "delay").

## Interventions / external factors modeled
- **Weather** (WeatherHour join on pickup date+hour): rain/snow hour vs dry hour.
- **Time-of-day bucket** (rush hour 7–10am & 4–7pm vs off-peak) — a structural, non-weather factor,
  included specifically so weather's effect can be judged *relative to* a known structural cause.

## Relational model (simplified)
\`\`\`mermaid
erDiagram
    TRIP }o--|| ZONE : "PULocationID -> pickup zone"
    TRIP }o--|| ZONE : "DOLocationID -> dropoff zone"
    TRIP }o--|| WEATHER_HOUR : "pickup date+hour"
    ZONE {
        int LocationID PK
        string Borough
        string Zone
        string service_zone
    }
    WEATHER_HOUR {
        datetime hour PK
        float precipitation_mm
        float snowfall_cm
        float temperature_c
    }
    TRIP {
        datetime pickup_datetime
        datetime dropoff_datetime
        int PULocationID FK
        int DOLocationID FK
        float trip_distance
        float fare_amount
        float total_amount
        int passenger_count
        float duration_sec
        float expected_duration_sec
        bool delay_flag
    }
\`\`\`

## Event flow (per trip)
\`\`\`mermaid
flowchart LR
    A[Pickup event\ntpep_pickup_datetime] --> B[In-transit\nduration_sec elapses]
    B --> C[Dropoff event\ntpep_dropoff_datetime]
    C --> D{duration_sec vs\nexpected_duration_sec}
    D -->|"<= 1.5x expected"| E[On-pace trip]
    D -->|"> 1.5x expected"| F[Delayed trip\ndelay_flag = 1]
    G[Weather hour: rain/snow?] -.influences.-> D
    H[Time-of-day: rush hour?] -.influences.-> D
\`\`\`

## Metrics linked to the KPI
1. **Trip Volume** (daily) — denominator for everything else; also a sanity/completeness check.
2. **Average Speed (mph)** — the direct efficiency signal underlying delay.
3. **Delay Rate (%)** — the project KPI itself.
4. **Revenue per Mile ($/mi)** — ties delay to a business cost (a delayed trip earns less per minute
   of driver time even if the fare itself is undamaged).
5. **Weather-Adjusted Delay Rate** — Delay Rate split by rain/snow-hour vs dry-hour, and by rush-hour
   vs off-peak — this is what lets leadership tell "weather problem" apart from "congestion problem."