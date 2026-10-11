# Snapchat Ads

Registry key: `snapchat` — check `../platform-registry.json` for API version, deadlines and when this was last verified. Anything not in the registry or past `stale_after_days` must be looked up on the official docs before you rely on it.

## Exports to request
- Campaign/ad squad report by day with spend, impressions, swipes, conversions
- Creative-level report

## Read-only access
Snap Marketing API (OAuth, snapchat-marketing-api scope). Registry entry unverified.

## Analyst checklist (beyond the computed checks)
Each item becomes a finding only with evidence from loaded data; otherwise it becomes a question or a data gap.
- Snap Pixel + Conversions API.
- Vertical full-screen creative quality and first-second hook.
- Frequency and audience size.

## Verify online before advising
- API version and attribution defaults (unverified in registry)
