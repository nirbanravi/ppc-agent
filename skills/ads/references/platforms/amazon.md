# Amazon Ads

Registry key: `amazon` — check `../platform-registry.json` for API version, deadlines and when this was last verified. Anything not in the registry or past `stale_after_days` must be looked up on the official docs before you rely on it.

## Exports to request
- Sponsored Products/Brands/Display campaign reports by day with spend, impressions, clicks, attributed orders and sales (note the attribution window in the column name)
- Search term report
- Targeting report

## Read-only access
Amazon Ads API (Login with Amazon) or the Amazon Ads MCP Server (open beta since 2026-02-02; it can write — gated by the guard).

## Analyst checklist (beyond the computed checks)
Each item becomes a finding only with evidence from loaded data; otherwise it becomes a question or a data gap.
- ACoS/TACoS: platform sales vs total sales (needs Seller/Vendor Central data for TACoS).
- Search term harvesting: converting auto/broad terms to exact; negatives for wasted terms.
- Branded vs non-branded split; defending brand terms vs cannibalising organic.
- Budget out-of-stock days; inventory status of advertised ASINs.

## Verify online before advising
- API version and report types
- Attribution window per ad type
