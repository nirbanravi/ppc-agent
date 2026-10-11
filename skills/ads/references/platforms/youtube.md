# YouTube (Google Ads video / Demand Gen)

Registry key: `youtube` — check `../platform-registry.json` for API version, deadlines and when this was last verified. Anything not in the registry or past `stale_after_days` must be looked up on the official docs before you rely on it.

## Exports to request
- Video campaign report by day with views, view rate, CPV, conversions
- Placement / channel report if available
- Brand lift results if any

## Read-only access
Same as Google Ads (YouTube buys run through Google Ads).

## Analyst checklist (beyond the computed checks)
Each item becomes a finding only with evidence from loaded data; otherwise it becomes a question or a data gap.
- Judge by the campaign's goal: reach/frequency and lift for awareness; conversions only for action-oriented campaigns.
- Frequency and reach across video campaigns; overlap with Display/Demand Gen.
- Creative: first-5-second hook, length vs format, vertical assets for Shorts.
- Placement exclusions and content suitability settings for the brand.

## Verify online before advising
- Current video campaign subtypes and their measurement options
- Lift study eligibility thresholds
