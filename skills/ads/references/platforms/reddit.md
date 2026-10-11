# Reddit Ads

Registry key: `reddit` — check `../platform-registry.json` for API version, deadlines and when this was last verified. Anything not in the registry or past `stale_after_days` must be looked up on the official docs before you rely on it.

## Exports to request
- Campaign/ad group report by day with spend, impressions, clicks, conversions
- Community/interest targeting breakdown

## Read-only access
Reddit Ads API v3 (allow-listed access) or exports from Ads Manager.

## Analyst checklist (beyond the computed checks)
Each item becomes a finding only with evidence from loaded data; otherwise it becomes a question or a data gap.
- Conversion API/pixel setup; small conversion volumes make CPA noisy — widen windows.
- Community targeting relevance; comments enabled and brand risk.
- Creative fit to subreddit norms.

## Verify online before advising
- API access requirements and reporting fields
