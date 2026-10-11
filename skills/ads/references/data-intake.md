# Data intake

## Two ways in
1. **Exports** (works for every platform, no credentials): CSV/TSV/XLSX downloaded from the platform UI. UTF-16 TSV (Google Ads UI default), report title rows and "Total" rows are handled automatically.
2. **Read-only access**: an MCP server or API connection with read scopes. Pull the report, **save it to a file** (CSV or JSON rows), then `ads.py ingest --kind mcp_pull --pulled-at <ISO>` so the evidence is on disk and hashed. Never analyse data that exists only in the conversation.

Prefer read-only credentials/roles even when a server supports writes. Known official servers as of 2026-10-11 (re-check `platform-registry.json`): Google Ads MCP is read-only; Meta's hosted Ads MCP and Amazon Ads MCP Server can write, so the guard treats their non-read tools as gated.

## What to export (per platform, last 30–90 days unless noted)
| Need | Columns | Segment |
|---|---|---|
| Campaign performance (all) | Campaign, Campaign ID, Status, Campaign type/Objective, Budget, Cost/Spend, Impressions, Clicks, Conversions (named event), Conversion value, Currency | by Day |
| Search waste (Google, Microsoft) | Search term, Match type, Campaign, Ad group, Cost, Clicks, Impressions, Conversions | none |
| Budget/rank limits (Google, Microsoft) | Search impr. share, Lost IS (budget), Lost IS (rank) | by Day or none |
| Social saturation (Meta, TikTok, Snapchat, Pinterest, LinkedIn, X, Reddit) | Reach, Frequency, plus the campaign columns | none + a by-Day export |
| Pacing (monitor) | Campaign, Spend | by Day, month to date |
| Reconciliation | Orders/leads from CRM or analytics with date, ID, value, source/UTM | by Day |

Export conversions as a **named event** (e.g. Purchases, Leads) rather than Meta "Results", which changes meaning per ad set.

## Column mapping
`scripts/adslib/normalize.py → ALIASES` maps common header names from each platform to canonical columns. Unmapped columns are kept per row in `extra`. If a file maps badly, ingest prints the missing canonical columns; either re-export or add an alias (keep the change small and tested).

## Data handling
- Inputs are copied into `.ads/runs/<run>/inputs/` and hashed (sha256) so findings can be traced to exact files.
- `.ads/.gitignore` excludes inputs, normalized data and approvals. Exports can contain customer data (search terms, audiences); do not commit or share them without the client's permission.
- Currency: one currency per source. The engine never converts currencies; per-platform metrics stay in their own currency and mixed currencies are reported as a gap. If you blend in an analyst finding, use rates from `client.json → fx`, state the rate and date, and mark the result `estimated`.
- Time zones: platforms report in the ad account's time zone. Note mismatches with the client's reporting time zone as a gap when reconciling.
