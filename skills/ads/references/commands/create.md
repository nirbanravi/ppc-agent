# /ads create [platform] [from plan run]

Goal: turn an approved plan into exact, reviewable build actions. Nothing is created until the user approves.

## Steps
1. Require a finalized `plan` (or audit) run. If none, run `/ads plan` first.
2. Draft the build as a proposal file (`.ads/runs/<run>/proposal.json`) with one action per entity:
   - `operation: "create"`, full `after` spec (names, budgets, bidding, targeting, URLs, assets), **`after.status: "PAUSED"`** (the gate rejects anything else unless the client explicitly allows enabling new entities).
   - `evidence_finding_ids`: the plan/audit items that justify it. Use plan allocation reasoning by adding an analyst finding per major build decision if needed.
   - `rollback`: how to remove it (usually: pause/remove the created entity).
   - `executor` only if a connected MCP server exposes a create tool; copy its exact input. Otherwise `manual_steps` the user can follow in the platform UI.
3. Verify platform specifics online before drafting (field limits, ad format specs, required assets, policy categories). Put URLs in the run's `docs`.
4. `ads.py propose --run <run> --file proposal.json`. Fix every gate failure; never weaken guardrails to pass.
5. Show the user: the action list, what is manual vs automated, and the approval code. Explain that approving creates entities paused.
6. After approval and execution, read each entity back (read tool) and confirm it matches `after`. Report anything that differs.

Ad copy: write within platform limits, no claims the client cannot substantiate, and flag regulated categories (health, finance, housing, employment, politics) for the user's review.
