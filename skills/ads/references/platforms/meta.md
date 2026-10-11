# Meta (Facebook & Instagram)

Registry key: `meta` — check `../platform-registry.json` for API version, deadlines and when this was last verified. Anything not in the registry or past `stale_after_days` must be looked up on the official docs before you rely on it.

## Exports to request
- Campaign and ad set report by day with Amount spent, Impressions, Reach, Frequency, Link clicks, named conversion event and value
- Ad-level report with creative names for fatigue checks
- Events Manager: event match quality / diagnostics screenshots or export (if diagnosing tracking)

## Read-only access
Meta's hosted Ads MCP server can READ and WRITE — connect with the least-privileged role and expect the guard to gate writes. A read-only system user token via the Marketing API is the safest option.

## Analyst checklist (beyond the computed checks)
Each item becomes a finding only with evidence from loaded data; otherwise it becomes a question or a data gap.
- Pixel + Conversions API deduplication and event match quality; which event each ad set optimises for.
- Attribution setting per ad set (click/view windows) when comparing with other platforms.
- Learning phase: ad sets with too few optimisation events per week; budget fragmentation across many ad sets.
- Frequency and creative fatigue (FREQ001 plus CTR/CPA trend by ad).
- Advantage+ campaigns vs manual: overlap and audience exclusions (existing customers).
- Placements: check v26 placement changes in the registry before recommending placement edits.

## Verify online before advising
- Current Marketing API version and deprecations (several land 2026-10-27)
- Reporting breakdowns still available
- Special ad category rules for the client's vertical
