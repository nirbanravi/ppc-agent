# Google Ads

Registry key: `google` — check `../platform-registry.json` for API version, deadlines and when this was last verified. Anything not in the registry or past `stale_after_days` must be looked up on the official docs before you rely on it.

## Exports to request
- Campaign report by day (incl. Search impr. share, Lost IS budget/rank)
- Search terms report
- Conversion actions list (name, category, primary/secondary, count, status)
- Change history for the audit window (if diagnosing a drop)

## Read-only access
Official Google Ads MCP server (read-only; GAQL search). A read-only user or a read-only OAuth scope in your own client also works.

## Analyst checklist (beyond the computed checks)
Each item becomes a finding only with evidence from loaded data; otherwise it becomes a question or a data gap.
- Conversion setup: which actions are Primary vs Secondary, duplicates (GA4 import + Ads tag counting the same purchase), enhanced conversions status, consent mode status.
- Bidding vs data volume: value/CPA bidding on campaigns with very few conversions in 30 days; tROAS/tCPA targets far from actual.
- Brand vs non-brand mixed in one campaign; brand cannibalisation inside PMax (needs search term / placement insight data).
- Search terms: irrelevant intent, competitor terms without a strategy, missing negative lists.
- Budget-limited campaigns with good CPA (BUD001) vs rank-limited (RNK001): different fixes.
- PMax / Demand Gen: asset group coverage, feed issues, final URL expansion settings, audience signals present.
- Location targeting option (presence vs presence-or-interest), language, network settings (Search partners / Display expansion on Search).

## Verify online before advising
- Current API version and sunset dates
- PMax and AI Max feature availability and reporting fields
- Policy categories affecting the client's vertical
