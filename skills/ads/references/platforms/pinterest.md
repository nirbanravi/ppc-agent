# Pinterest Ads

Registry key: `pinterest` — check `../platform-registry.json` for API version, deadlines and when this was last verified. Anything not in the registry or past `stale_after_days` must be looked up on the official docs before you rely on it.

## Exports to request
- Campaign/ad group report by day with spend, impressions, clicks (outbound), conversions, value
- Product group report (shopping)

## Read-only access
Pinterest API v5 with ads:read scope. Registry entry is unverified — check docs before relying on version details.

## Analyst checklist (beyond the computed checks)
Each item becomes a finding only with evidence from loaded data; otherwise it becomes a question or a data gap.
- Pinterest tag + Conversions API coverage.
- Catalog/shopping feed health.
- Seasonal planning: Pinterest users plan early; compare YoY windows.

## Verify online before advising
- Current API version and conversion reporting fields (unverified in registry)
