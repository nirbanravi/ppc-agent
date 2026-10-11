# /ads optimize [platform]

Goal: ranked, evidence-tied change proposals, packaged as a gated changeset.

## Steps
1. Start from a finalized audit or monitor run on **fresh** data (≤72h by default; the gate checks this). If the latest run is older, run a new one.
2. Rank candidate changes by (impact range × confidence) and reversibility. Prefer: fix tracking → stop clear waste → rebalance budget → bid/target tweaks → structural changes.
3. If any TRK finding is open, propose only tracking fixes and waste cuts; do not move budget on broken conversion data.
4. Write `proposal.json` (schema: `schemas/changeset.schema.json`):
   - one action per entity; `before` must contain the live current value (read it via a read-only tool or the export — the gate refuses changes without a known `before`);
   - budget changes within ±30% and bid changes within ±25% per changeset unless the client's guardrails say otherwise;
   - pause instead of delete;
   - `executor` = exact MCP tool + input when available, otherwise `manual_steps`;
   - `rollback` always.
5. `ads.py propose --run RUN_ID --file proposal.json`.
6. Present: a table of actions (entity, change, why, evidence id, risk), anything manual, and the approval code. Say plainly: "Nothing has changed yet."
7. Only after the user's own `APPROVE <code>` message: run each MCP executor with the exact stored input, one at a time; read back each change; stop on the first error and report it. Then `ads.py status`.
8. Suggest a follow-up `/ads monitor` 3–7 days later to check the effect.
