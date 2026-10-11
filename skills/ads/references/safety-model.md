# Safety model

Default state: **read-only**. An account changes only through this chain, and every link is checked by code, not by instructions alone.

```
finalized run (fresh data, evidence)
   → proposal.json (exact actions: before/after, rollback, executor or manual steps)
   → ads.py propose  → changeset (content-hashed) + gate (all checks must pass) → approval code ADS-XXXXXX
   → user types "APPROVE ADS-XXXXXX [a1,a2]" in their own message
   → approve.py hook (UserPromptSubmit) records approval bound to the changeset hash and each executor's input hash, TTL 24h
   → guard.py hook (PreToolUse) allows a write tool call only if tool + input hash match an unused approved action
   → guard.py (PostToolUse) logs the result to .ads/executions.jsonl
```

## Gate checks (scripts/adslib/gate.py)
schema · source run finalized and not failed · data freshness (default ≤72h) · changeset not expired (72h) · ≤ max_actions · account allow-list set and matched · every action cites existing finding ids · rollback present · execution path (MCP executor with exact input, or manual steps) · no deletes (unless allowed) · new/enabled entities start PAUSED (unless allowed) · budget change ≤ ±30% · bid/target change ≤ ±25% · `before` known for any budget/bid change · no two actions on the same entity · optional cap on total daily spend increase.

Guardrails are set per client in `.ads/client.json → guardrails` and can only be overridden per proposal, visibly, in the changeset (which the user sees before approving).

## What the guard blocks (for the rest of the session once /ads loads)
- Write-capable tools on ad MCP servers (server names containing ads/meta/google-ads/amazon/… or tool names touching campaigns, ad sets, keywords, budgets, bids, audiences). Unknown/ambiguous tools are treated as writes.
- Re-use of an approval (each action is one-time), any input that differs from the approved one, approvals after expiry, and changesets edited after approval (hash mismatch).
- `Write`/`Edit` to `.ads/approvals/`, gate files, finalized `run.json`, the execution log, and the skill's `hooks/` folder.
- Bash containing an approval phrase, shell writes to those paths, and raw HTTP write requests to ad API hosts.

## Known limits (be honest with the user about these)
- Hooks run only when the skill is installed where the hook command looks: `<project>/.claude/skills/ads/` or `~/.claude/skills/ads/`. If neither path has the guard, the PreToolUse hook fails closed and blocks Bash/Write/MCP calls until fixed.
- Skill hooks register when `/ads` is invoked. A write made in the same session **before** the skill loads is not covered. For always-on protection, also add the same hooks to `.claude/settings.json` (see README).
- Bash detection of shell writes and HTTP calls is pattern-based and best-effort. The strong guarantees are on MCP tool calls and on the approval itself (which only a user prompt can create). Keep ad-platform credentials out of the shell environment so raw API writes are impossible.
- Tool-name classification can mislabel a read-only tool as a write (it gets blocked; add it by hand to `hooks/readonly_tools.json`). It errs toward blocking.
- `UserPromptSubmit` also fires for scheduled tasks and messages from other sessions. Never put an approval phrase in those.
- A platform MCP server may itself apply changes differently than requested. Always read back after execution.
