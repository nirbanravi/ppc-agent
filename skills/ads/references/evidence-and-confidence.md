# Evidence and confidence

## Evidence item
```json
{"source_id": "src1-google-campaigns-dai", "selector": "campaign='Generic - Phrase', 2026-09-11..2026-10-10",
 "detail": "spend / conversions vs account", "values": {"spend": 324000, "conversions": 184, "cpa": 1761}}
```
- `source_id` must be a data source in the run, `doc:<url>` for documentation, or `run:<run_id>` for a carried-over finding.
- `values` are copied from the data, not rounded into new claims. Any derived number names its formula in `detail`.

## Kinds
- `observed` — read directly or computed arithmetically from the loaded data.
- `estimated` — a projection or impact range; must state `impact.method` and a low–high range.
- `recommendation` — judgment; still needs evidence for why.

## Confidence score (0–1)
Start at 0.9 for computed findings; analysts state their own and give reasons. Multipliers (scripts/adslib/confidence.py):

| Condition | Multiplier |
|---|---|
| Needed columns missing (share c present) | 0.6 + 0.4c |
| Conversions < 5 / < 20 / < 50 | 0.6 / 0.8 / 0.92 |
| Clicks < 100 | 0.8 |
| Freshness aging / stale / unknown | 0.9 / 0.75 / 0.85 |
| Window < 7 days / < 14 days | 0.7 / 0.85 |
| Check-specific caveats (stated in reasons) | 0.8–0.9 |

Caps applied at finalize: cites stale data → ≤0.74; relies on platform docs not verified in 45 days → ≤0.49; documentation-only evidence → ≤0.60; same source shows a recent tracking break → conversion-based findings ≤0.60.

Levels: high ≥ 0.75, medium ≥ 0.50, low < 0.50.

## Overall confidence and health score
- Overall confidence = severity-weighted mean of finding scores × 0.95 per major gap × 0.75 per blocking gap × 0.8 if any errors.
- Health score (audit/monitor) = 100·e^(−P/100), where P = Σ severity weight × confidence (critical 25, high 12, medium 5, low 2). It is a triage signal, not a benchmark; never compare it across clients.

## Run status
- `failed`: a data command ran with no data.
- `partial`: any error, any blocking gap, or stale/undated data for monitor/optimize.
- `complete`: otherwise. Gaps still appear in the report.
