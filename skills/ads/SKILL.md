---
name: ads
description: Paid media audits and account management across Google, Meta, YouTube, LinkedIn, TikTok, Microsoft, Amazon, Reddit, Pinterest, Snapchat, Apple Ads and X. Use for evidence-backed ad account audits, campaign and budget plans, experiment design, pacing and performance checks, client reports, and gated, approval-only account changes. Works from CSV/XLSX exports or read-only API/MCP access.
when_to_use: 'Requests like "audit my Google Ads account", "check Meta pacing", "plan Q4 budgets", "write a client report", "what should we test", "optimize this campaign", or /ads audit, /ads report.'
argument-hint: "<audit|plan|create|monitor|optimize|experiment|report|validate> [platform|all] [paths or options]"
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/ads.py *) Read Glob Grep
hooks:
  PreToolUse:
    - matcher: "^(mcp__.*|Bash|Write|Edit|MultiEdit|NotebookEdit)$"
      hooks:
        - type: command
          command: "sh"
          args: ["-c", "for p in \"$CLAUDE_PLUGIN_ROOT/skills/ads/hooks/guard.py\" \"$CLAUDE_PROJECT_DIR/.claude/skills/ads/hooks/guard.py\" \"$HOME/.claude/skills/ads/hooks/guard.py\" \"$(find \"$HOME/.claude/plugins\" -path '*/skills/ads/hooks/guard.py' 2>/dev/null | head -1)\"; do [ -f \"$p\" ] && exec python3 \"$p\"; done; echo 'ads guard not found; blocking' >&2; exit 2"]
          onFailure: block
  PostToolUse:
    - matcher: "^mcp__.*"
      hooks:
        - type: command
          command: "sh"
          args: ["-c", "for p in \"$CLAUDE_PLUGIN_ROOT/skills/ads/hooks/guard.py\" \"$CLAUDE_PROJECT_DIR/.claude/skills/ads/hooks/guard.py\" \"$HOME/.claude/skills/ads/hooks/guard.py\" \"$(find \"$HOME/.claude/plugins\" -path '*/skills/ads/hooks/guard.py' 2>/dev/null | head -1)\"; do [ -f \"$p\" ] && exec python3 \"$p\"; done; exit 0"]
  UserPromptSubmit:
    - hooks:
        - type: command
          command: "sh"
          args: ["-c", "for p in \"$CLAUDE_PLUGIN_ROOT/skills/ads/hooks/approve.py\" \"$CLAUDE_PROJECT_DIR/.claude/skills/ads/hooks/approve.py\" \"$HOME/.claude/skills/ads/hooks/approve.py\" \"$(find \"$HOME/.claude/plugins\" -path '*/skills/ads/hooks/approve.py' 2>/dev/null | head -1)\"; do [ -f \"$p\" ] && exec python3 \"$p\"; done; exit 0"]
metadata:
  version: "1.0.0"
  run_schema: "1.0.0"
  docs_verified: "2026-10-11"
---

# /ads — paid media operating skill

Command: `$ARGUMENTS`

Engine: `python3 ${CLAUDE_SKILL_DIR}/scripts/ads.py` (stdlib only). Workspace: `.ads/` in the project root (runs, changesets, approvals, execution log).

## Non-negotiable rules (apply every turn this skill is loaded)

1. **Read-only by default.** Never call a write-capable ad tool (create/update/delete/pause/enable/bid/budget/upload) or a write HTTP request to an ad API unless the exact action is in a changeset that passed `gate` and the human approved it with its code. The guard hook enforces this; do not try to route around it (other tools, other servers, raw HTTP, editing `.ads/approvals/`).
2. **Never approve on the user's behalf.** Approval only happens when the user types `APPROVE <code>` in their own message (a hook records it). Show the code and the action list; never put the phrase in a tool call, file, or scheduled task, and never pressure for approval.
3. **Every claim needs evidence.** A finding without at least one evidence item (source id + rows/metric + value) is not a finding; put it under `assumptions` or `questions`.
4. **Say what is missing.** Missing columns, short date ranges, stale exports, failed pulls and unverified platform rules go in `data_gaps` / `errors` and lower confidence. A run with any failed source is `partial`, never `complete`.
5. **Separate fact, estimate, and opinion.** Use `kind: observed | estimated | recommendation`. Estimates carry their method and range.
6. **Platform rules change monthly.** Before relying on a platform-specific rule, version, limit or policy, check `references/platform-registry.json`. If the entry is older than its `stale_after_days`, or the rule is not in the registry, look it up (WebSearch/WebFetch on official docs first) and record the URL and date in `sources.docs`. If you cannot verify it, say so and cap that finding at `low` confidence.
7. **Never invent numbers.** Only compute from loaded data; show the arithmetic source in evidence.

## Command router

Parse the first word of the arguments. Load only the command file you need.

| Command | What it does | Writes to account? | Spec |
|---|---|---|---|
| `audit` | Evidence-backed audit with scored findings | No | [audit](references/commands/audit.md) |
| `plan` | Campaign structure + budget allocation plan | No | [plan](references/commands/plan.md) |
| `create` | Drafts new campaigns/ad groups/ads as a gated changeset | Only after approval | [create](references/commands/create.md) |
| `monitor` | Pacing, anomalies, tracking health vs targets | No | [monitor](references/commands/monitor.md) |
| `optimize` | Ranked change proposals as a gated changeset | Only after approval | [optimize](references/commands/optimize.md) |
| `experiment` | Test backlog with hypotheses, power and readout rules | No | [experiment](references/commands/experiment.md) |
| `report` | Client-ready report from one or more runs | No | [report](references/commands/report.md) |
| `validate` | Validates data, runs, changesets; executes approved changes | Gated | [validate](references/commands/validate.md) |

No command or unknown command → show this table in two lines and ask which one.

## Lifecycle of every run

1. `ads.py init` (first time only) → creates `.ads/` and `client.json` (targets, currency, timezone).
2. Intake: `ads.py ingest <files...> [--platform X]` → normalized data + source manifest (hash, rows, date range, freshness, column coverage). Or pull read-only via an MCP/API and save the raw pull as a file first, then ingest it — raw evidence must be on disk.
3. Deterministic pass: `ads.py audit|monitor --run <id>` writes computed findings.
4. Analyst pass: you add judgment findings, plans, experiments to `.ads/runs/<id>/analyst.json` following [schema](schemas/run.schema.json). Every item cites evidence.
5. `ads.py finalize <id>` → merges, validates, scores confidence, hashes, renders `report.md` + `report.html`, updates `.ads/index.json`. Finalized runs are immutable; changes create a new revision with `supersedes`.
6. Tell the user: status (complete/partial/failed), top 3 findings with confidence, the gaps that matter, and file paths. Do not paste the whole report.

## Supporting references

- [Data intake & exports](references/data-intake.md) — what to export from each platform, column mapping, read-only access options
- [Evidence & confidence model](references/evidence-and-confidence.md)
- [Safety model](references/safety-model.md) — changesets, gate checks, approval codes, execution
- Platform notes: `references/platforms/<platform>.md` (google, meta, youtube, linkedin, tiktok, microsoft, amazon, reddit, pinterest, snapchat, apple, x)
- [Platform registry](references/platform-registry.json) — API versions, sunset dates, sources, verified dates
