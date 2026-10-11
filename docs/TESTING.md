# Testing SpendSentry before you launch

Work through these in order. Each stage catches problems the previous one can't.

## 1. Automated (every commit, free)
```bash
sh tests/run_tests.sh                       # 15 engine + hook checks
claude plugin validate --strict .           # marketplace + plugin + skill manifests
```
CI runs both on push (see `.github/workflows/ci.yml`).

## 2. Behaviour evals (before each release, small cost)
```bash
claude plugin eval . --runs 3 --trust-plugin --no-publish
```
Each case runs with and without the plugin. Keep only cases where SpendSentry should change behaviour, and add a case for every bug you fix. Good next cases:
- given exports with a tracking break → headline mentions tracking before budget advice
- user asks for +125% budget → refuses one-step change, cites the ±30% limit
- Meta export uses "Results" → warns that the event differs by ad set
- stale export (60 days old) for `monitor` → run is `partial`

## 3. Install test (once per release)
```bash
claude plugin marketplace add ./          # from the repo root
claude plugin install spendsentry@spendsentry
claude plugin details spendsentry@spendsentry         # expect 1 skill, 3 hooks
```
In a scratch project, run `/ads audit` on `skills/ads/examples/exports/` and check that `.ads/runs/*/report.html` opens.

## 4. Real accounts (the test that matters)
Use 3–5 real accounts across at least 3 platforms, including a messy one.
1. **Exports first, read-only always.** Use exports or a read-only user. Never run the first tests with write-capable credentials.
2. **Keep client data out of git.** Inputs live in `.ads/runs/*/inputs/` (gitignored). For public examples, anonymise names and scale all numbers by one factor.
3. **Score each audit against your own judgement.** For every finding, mark it correct, wrong or trivial. Note anything important it missed. Target: ≥80% correct on high-confidence findings and no critical misses.
4. **Check the numbers.** Pick 5 numbers per report and recompute them in the platform UI for the same dates and currency.
5. **Test failure honesty.** Remove the conversions column, give a 60-day-old export, or ingest a wrong file. The report must say so and the status must change.
6. **Test the write path on a sandbox.** Use a test account (Google Ads test accounts, Meta sandbox ad accounts, TikTok sandbox) with a write-capable MCP server. Approve one small change, read it back, then try a replay and a modified input. Both must be blocked.
7. Log every column-mapping miss as an alias issue.

## 5. Beta users (2–3 weeks)
Give it to 5–10 PPC practitioners. Ask each for one real audit and these three answers: what was wrong, what was missing, and would you send this report to a client? Fix the top issues before the public launch.
