# Known / Unknown / Assumption / Limitation

## Known
- TLC trip files have no trip ID; VendorID + timestamps + PULocationID is the best available
  natural key, and duplicates on that key are logged, not silently deduplicated.
- TLC explicitly states it does not guarantee the accuracy of vendor-submitted data.
- The most recent 1–2 months on the TLC site are subject to later revision (vendor submission lag).

## Unknown
- Real reason for any individual "delayed" trip (traffic, driver detour, meter/GPS error,
  passenger request) — the data has no cause field, only timestamps and distance.
- Whether Open-Meteo's single NYC-area coordinate accurately represents borough-specific weather
  (e.g., a Staten Island trip during a Manhattan downpour would be mis-tagged as "rain hour").

## Assumptions (explicit, not silently baked in)
- **Expected duration baseline**: computed as distance / borough-median speed *from the same
  month's data*, not from an external standard. This is the single biggest FDE judgement call in
  this project — see the note below.
- Trips with average speed > 65 mph are treated as **data errors** (GPS/meter fault), not as
  "fast/efficient" trips, and are excluded from the delay calculation (but reported separately in
  the validation report, not deleted from the raw data).
- Trips with 0 passengers are kept (some TLC vendors report 0 as a default/sensor value) but flagged,
  not dropped — dropping them would silently bias volume metrics downward.

## The one judgement call worth defending on camera
**Why compute the "expected duration" baseline from the data itself (per-borough median speed)
rather than a fixed assumption like "20 mph in Manhattan"?** A fixed external assumption is easy to
justify but brittle — it doesn't adapt month to month, and it hides the fact that "normal" already
varies structurally by borough (Staten Island trips are legitimately faster than Manhattan trips).
Deriving the baseline from the same month's own median makes Delay Rate a *relative*, self-correcting
signal ("slower than usual for this borough this month") rather than an arbitrary absolute threshold
that would flag all of Manhattan as "delayed" every day. The trade-off: it can't detect a borough that
is *chronically* slow across every month, only anomalies within a month — a real limitation, disclosed
here rather than fixed.

## Limitations
- Single month analyzed by default; seasonal effects (e.g., snow in January vs none in June) are not
  visible unless `--month` is re-run across several months and outputs are compared manually.
- Weather join is at hour granularity across the whole city — coarse, as noted above.
- No ground truth to validate the delay flag against (no independent "this trip was actually stuck
  in traffic" label exists) — this is a proxy metric, and the README/KPI description says so.