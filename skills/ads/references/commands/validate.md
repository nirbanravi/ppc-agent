# /ads validate [path | changeset id | docs]

Goal: check that inputs, outputs and proposed changes are trustworthy before anyone relies on them.

- `ads.py validate <run.json>` — schema, semantic rules (every finding has evidence that points at a real source), and the integrity hash (detects edits after finalize).
- `ads.py validate <analyst.json>` — quick structural check before finalize.
- `ads.py validate <changeset.json>` then `ads.py gate <changeset_id>` — re-runs all gate checks (freshness, allow-listed accounts, change limits, evidence, rollback, execution path, expiry).
- `ads.py docs-check` — lists platform registry entries that are stale or unverified and the next API deadlines. For each stale entry relevant to the user's work, look it up online, then tell the user what changed. Do not edit `platform-registry.json` silently; show the diff and the sources.
- `ads.py status` — runs, open drafts, changesets, approvals, and the execution log.

Report results as: what passed, what failed (with the exact check), and what to do next.
