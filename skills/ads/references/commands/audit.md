# /ads audit [platform|all] [files...]

Goal: an evidence-backed account audit the user can act on and show a client.

## Steps
1. `ads.py start audit --platforms <list> --question "<what the user wants to know>"` → RUN_ID.
2. Get data (see [data-intake](../data-intake.md)). Minimum useful set per platform: campaign report by day for the last 30–90 days with spend, impressions, clicks, conversions, conversion value, budget, status. Search platforms: also search terms. If the user gave read-only API/MCP access, pull the same reports, save each pull as CSV/JSON under the project, then ingest with `--kind mcp_pull --pulled-at <ISO time>`.
3. `ads.py ingest --run RUN_ID <files>`; read the printed warnings and missing columns.
4. `ads.py audit --run RUN_ID` → computed findings + gaps.
5. Analyst pass. Open `references/platforms/<platform>.md` for each platform and work through its checklist using only the loaded data. Check `platform-registry.json`; re-verify anything stale online. Write `.ads/runs/RUN_ID/analyst.json`:
   - `summary.headline`: 1–2 sentences, the most important thing first. If tracking is broken, that is the headline.
   - `findings[]`: only what the computed checks missed. Each needs `id` (A-1…), evidence pointing at a `source_id` + selector + values, `kind`, `confidence` with reasons, and `doc_refs` for any platform rule you relied on.
   - `assumptions[]`, `questions[]` (what you would ask the client), `docs[]` (URL + verified_at for every doc you used).
6. `ads.py validate .ads/runs/RUN_ID/analyst.json`, then `ads.py finalize RUN_ID`.
7. Reply: status, health score, overall confidence, top 3 findings (title + confidence + evidence in one line each), the gaps that most limit the audit, paths to report.md/html. Offer `/ads optimize` for fixes and `/ads report` for a client version.

## Do not
- Do not restate a computed finding as an analyst finding.
- Do not judge CPA across campaigns with different objectives without saying so.
- Do not quote industry benchmarks unless you looked them up this session and cite them; they are weak evidence (cap at medium).
