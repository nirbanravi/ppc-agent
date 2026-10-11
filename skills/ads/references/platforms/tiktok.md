# TikTok Ads

Registry key: `tiktok` — check `../platform-registry.json` for API version, deadlines and when this was last verified. Anything not in the registry or past `stale_after_days` must be looked up on the official docs before you rely on it.

## Exports to request
- Campaign/ad group report by day with cost, impressions, clicks (destination), conversions, value
- Ad-level report for creative fatigue

## Read-only access
TikTok API for Business v1.3 with a read-only access token.

## Analyst checklist (beyond the computed checks)
Each item becomes a finding only with evidence from loaded data; otherwise it becomes a question or a data gap.
- Pixel/Events API setup and deduplication.
- Creative velocity: ads older than ~2–3 weeks with falling CTR; native, sound-on creative.
- Smart+ vs manual campaigns overlap.
- Learning phase: conversion volume per ad group.

## Verify online before advising
- Current Smart+ campaign types and reporting fields
- Creative policy for the client's vertical
