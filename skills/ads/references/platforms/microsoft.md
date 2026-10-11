# Microsoft Advertising

Registry key: `microsoft` — check `../platform-registry.json` for API version, deadlines and when this was last verified. Anything not in the registry or past `stale_after_days` must be looked up on the official docs before you rely on it.

## Exports to request
- Campaign report by day with spend, impressions, clicks, conversions, revenue, impression share columns
- Search terms report

## Read-only access
Microsoft Advertising API v13 (moving SOAP → REST; SOAP fully deprecated 2027-01-31) with a read-only user.

## Analyst checklist (beyond the computed checks)
Each item becomes a finding only with evidence from loaded data; otherwise it becomes a question or a data gap.
- Google Ads imports: settings that differ after import (bids, budgets, targeting, ad extensions), auto-import overwriting local changes.
- Audience network / partner network settings and their performance.
- Same search-term and budget/rank checks as Google.

## Verify online before advising
- REST migration status of any tool you use
- Current campaign types (e.g. PMax availability)
