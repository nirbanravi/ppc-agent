# LinkedIn Ads

Registry key: `linkedin` — check `../platform-registry.json` for API version, deadlines and when this was last verified. Anything not in the registry or past `stale_after_days` must be looked up on the official docs before you rely on it.

## Exports to request
- Campaign performance by day with spend, impressions, clicks, conversions, leads (Lead Gen forms) and cost per lead
- Demographics report (job function, seniority, company size)

## Read-only access
LinkedIn Marketing API with r_ads / r_ads_reporting scopes (read). Requests need the Linkedin-Version header; latest is not applied by default.

## Analyst checklist (beyond the computed checks)
Each item becomes a finding only with evidence from loaded data; otherwise it becomes a question or a data gap.
- Audience size and expansion settings; overly narrow vs overly broad targeting.
- Lead quality: reconcile Lead Gen form leads with CRM (MQL/SQL) — platform CPL alone misleads.
- Objective vs KPI fit (website conversions vs lead gen vs engagement).
- Frequency on small ABM lists; creative rotation.

## Verify online before advising
- Current monthly API version
- Conversion and qualified-lead optimisation availability
