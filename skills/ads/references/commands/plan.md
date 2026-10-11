# /ads plan [platforms] [budget] [goal]

Goal: a campaign structure and budget allocation plan with stated reasoning and confidence.

## Inputs to confirm (ask at most 3 questions, only for what is missing)
- Objective and primary KPI (CPA, ROAS, leads, installs, reach) and target.
- Total budget, period, currency; any fixed commitments.
- Constraints: platforms allowed, markets/languages, creative availability, tracking status.

## Steps
1. `ads.py start plan --platforms ... --question "..."`. If there is history, ingest it (or `--from <audit run>` to reuse a finalized audit's sources and findings).
2. If history exists, base allocation on observed marginal performance (campaign CPA/ROAS, impression share lost to budget). If not, say the plan is a starting hypothesis and set confidence `low`.
3. Write `analyst.json` → `plan`:
   ```json
   {"objective": "...", "total_budget": 1500000, "currency": "INR", "period": "month",
    "allocations": [{"platform": "google", "name": "Search - Brand", "budget": 150000, "share_pct": 10,
                     "goal": "CPA ≤ 600", "rationale": "...cite finding ids or 'no history'", "confidence": "medium"}],
    "structure": ["..."], "milestones": ["Week 1: ...", "Day 14 review: ..."], "risks": ["..."]}
   ```
   Shares must sum to 100 (±1). Keep a 5–15% test reserve when the user agrees.
4. Add `findings` only for evidence-based observations; plan reasoning lives in `rationale`.
5. Platform rules that shape structure (e.g. minimum budgets, learning-phase rules, campaign-type availability) must be verified online and listed in `docs`.
6. Finalize. Reply with the allocation table (short), the 2–3 biggest assumptions, and what data would raise confidence.

`plan` never changes an account. To build it, use `/ads create`.
