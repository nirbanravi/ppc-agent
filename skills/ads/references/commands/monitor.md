# /ads monitor [platforms]

Goal: is spend pacing to budget, did anything break, and what needs attention today.

## Steps
1. Budgets must exist in `.ads/client.json` → `budgets`. If missing, ask for monthly budgets per platform and add them (client.json is a normal editable file).
2. `ads.py start monitor --platforms ...`; ingest **daily** month-to-date exports (or read-only pulls). Data older than 2 days makes the run `partial`.
3. `ads.py monitor --run RUN_ID` → pacing table, tracking checks (including zero-conversion streaks), anomaly flags.
4. Analyst pass: explain each flag in one line with the likely cause and the check that would confirm it. Do not speculate beyond the data; put hypotheses in `questions`.
5. Finalize. Reply with a compact pacing table and the at-risk items first.

## Scheduling
If the user wants this daily, create a scheduled task whose prompt runs `/ads monitor` with the same data-pull steps. Scheduled runs are read-only; they must never contain an approval phrase.
