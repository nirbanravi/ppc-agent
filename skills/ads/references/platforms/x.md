# X Ads

Registry key: `x` — check `../platform-registry.json` for API version, deadlines and when this was last verified. Anything not in the registry or past `stale_after_days` must be looked up on the official docs before you rely on it.

## Exports to request
- Campaign/ad group report by day with spend (billed charge), impressions, engagements, link clicks, conversions

## Read-only access
X Ads API (versioned path) with read access, or exports from Ads Manager.

## Analyst checklist (beyond the computed checks)
Each item becomes a finding only with evidence from loaded data; otherwise it becomes a question or a data gap.
- Brand safety / adjacency settings.
- Conversion tracking coverage (X Pixel / Conversion API).
- Engagement vs outcome objectives.

## Verify online before advising
- Current API version (registry lists 12 from secondary verification)
- Ad policies for the vertical
