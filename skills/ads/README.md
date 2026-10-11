# /ads — paid media skill for Claude Code

Audits, plans, pacing checks, experiments, client reports and **approval-gated** account changes for Google, YouTube, Meta, LinkedIn, TikTok, Microsoft, Amazon, Reddit, Pinterest, Snapchat, Apple Ads and X.

- Works from exports (CSV/TSV/XLSX) or read-only API/MCP pulls.
- Every run is a versioned, hashed JSON record (`schemas/run.schema.json` v1.0.0), rendered to Markdown and HTML.
- Findings carry evidence (source file + rows + values) and a confidence score with reasons.
- Missing data, stale sources and failed steps are reported, and they change the run status (`complete` / `partial` / `failed`).
- Nothing changes in an ad account unless the exact action passed the gate and **you** typed its approval code.

## Install
Recommended: install the `SpendSentry` plugin (`/plugin marketplace add nirbanravi/ppc-agent`, then `/plugin install spendsentry@spendsentry`). The plugin's hooks guard ad-account writes whenever it is enabled.

Manual install (skill only):
```bash
# per project (recommended; the guard hook looks here first)
mkdir -p .claude/skills && cp -r ads .claude/skills/ads
# or for all projects
mkdir -p ~/.claude/skills && cp -r ads ~/.claude/skills/ads
```
Needs Python 3.9+. No packages required; `jsonschema` and `openpyxl` are used if present (stricter validation, XLSX input).

### Always-on protection (recommended)
Skill hooks start when `/ads` is first used in a session. To guard ad-account writes from the start of every session, add the same hooks to `.claude/settings.json`:
```json
{
  "hooks": {
    "PreToolUse": [{"matcher": "^(mcp__.*|Bash|Write|Edit|MultiEdit|NotebookEdit)$",
      "hooks": [{"type": "command", "command": "python3", "args": ["${CLAUDE_PROJECT_DIR}/.claude/skills/ads/hooks/guard.py"], "onFailure": "block"}]}],
    "PostToolUse": [{"matcher": "^mcp__.*",
      "hooks": [{"type": "command", "command": "python3", "args": ["${CLAUDE_PROJECT_DIR}/.claude/skills/ads/hooks/guard.py"]}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "python3", "args": ["${CLAUDE_PROJECT_DIR}/.claude/skills/ads/hooks/approve.py"]}]}]
  }
}
```

## Use
```
/ads audit google ./exports/google_campaigns.csv ./exports/search_terms.csv
/ads monitor all
/ads plan google,meta 15 lakh/month leads at ≤ ₹900
/ads optimize google
/ads experiment meta
/ads report latest
/ads validate docs
```
First run creates `.ads/` with `client.json` — set targets, monthly budgets and the `accounts` allow-list (writes stay blocked until it is set).

Approving a change: Claude shows the actions and a code like `ADS-C15127`. To approve, send a message that is exactly `APPROVE ADS-C15127` (optionally followed by action ids, e.g. `a1,a3`).

## Layout
```
SKILL.md                      router, rules, hooks
references/commands/*.md      one spec per command
references/platforms/*.md     per-platform exports, access, checklist
references/platform-registry.json   API versions/deadlines with verified dates (re-check when stale)
references/{safety-model,evidence-and-confidence,data-intake}.md
schemas/run.schema.json, changeset.schema.json
scripts/ads.py + adslib/      engine (ingest, checks, pacing, gate, finalize, render)
hooks/guard.py, approve.py    enforcement
examples/                     sample exports, analyst.json, proposal.json
```
Workspace (`.ads/` in your project): `runs/<run_id>/{run.json, report.md, report.html, inputs/, data/}`, `changesets/`, `approvals/`, `executions.jsonl`, `index.json`.

## Limits
- Computed checks cover tracking breaks, zero-conversion spend, CPA/ROAS vs target, budget- and rank-limited campaigns, CTR outliers, frequency, spend concentration, search-term waste, pacing and anomalies. Everything else is Claude's analyst pass, held to the same evidence rule.
- Platform facts in the registry were verified on 2026-10-11; Pinterest and Snapchat entries are unverified. The skill tells Claude to re-check online when entries are stale.
- See `references/safety-model.md` for what the guard can and cannot catch.
