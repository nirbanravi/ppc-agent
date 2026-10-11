# Apple Ads (App Store, Apple Maps)

Registry key: `apple` — check `../platform-registry.json` for API version, deadlines and when this was last verified. Anything not in the registry or past `stale_after_days` must be looked up on the official docs before you rely on it.

## Exports to request
- Campaign/ad group/keyword report by day with spend, impressions, taps, installs (tap-through/view-through), CPA/CPT
- Search terms report

## Read-only access
Apple Ads Platform API 1.0 (released Aug 2026). Campaign Management API v5 stops working 2027-01-26 — flag any tooling still on it.

## Analyst checklist (beyond the computed checks)
Each item becomes a finding only with evidence from loaded data; otherwise it becomes a question or a data gap.
- Brand vs generic vs competitor vs discovery campaign split.
- Search match on/off and negatives.
- Install quality: reconcile with MMP/in-app events, not installs alone.
- Lifetime budgets were deprecated; check daily budgets.

## Verify online before advising
- Platform API metric names (renamed vs v5)
- Apple Maps ads availability by country
