#!/usr/bin/env python3
"""UserPromptSubmit hook: turns the user's own message 'APPROVE ADS-XXXXXX [a1,a2]' into an approval.

Only a human-submitted prompt reaches this hook, so Claude cannot approve its own changes.
(Caveat: scheduled tasks and messages from other sessions also fire UserPromptSubmit; do not put
an approval phrase in a scheduled task prompt.)
The approval binds the exact changeset hash and each action's exact executor input hash.
"""
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

PHRASE = re.compile(r"^\s*APPROVE\s+(ADS-[0-9A-F]{6})(?:\s+([a-z0-9,\s]+))?\s*$", re.I | re.M)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def say(text):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": text}}))
    sys.exit(0)


def find_ads(cwd):
    for r in (os.environ.get("CLAUDE_PROJECT_DIR"), cwd, os.getcwd()):
        if r:
            for p in [Path(r), *Path(r).parents]:
                if (p / ".ads").is_dir():
                    return p / ".ads"
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)
    m = PHRASE.search(data.get("prompt", ""))
    if not m:
        sys.exit(0)
    code = m.group(1).upper()
    wanted = {x.strip() for x in (m.group(2) or "").replace(" ", ",").split(",") if x.strip()}
    ads = find_ads(data.get("cwd"))
    if not ads:
        say(f"ads approval: no .ads workspace found; {code} was NOT recorded.")
    now = dt.datetime.now(dt.timezone.utc)
    for gp in sorted((ads / "changesets").glob("cs-*.gate.json")):
        gate = json.loads(gp.read_text())
        if gate.get("approval_code") != code:
            continue
        cs_id = gp.name.replace(".gate.json", "")
        cs = json.loads((ads / "changesets" / f"{cs_id}.json").read_text())
        body = {k: v for k, v in cs.items() if k != "gate"}
        sha = hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()
        if sha != gate.get("changeset_sha256") or not gate.get("passed"):
            say(f"ads approval: {code} matches {cs_id} but the changeset changed after gating or the gate failed. NOT approved. Re-run gate.")
        if now >= dt.datetime.fromisoformat(cs["expires_at"].replace("Z", "+00:00")):
            say(f"ads approval: changeset {cs_id} has expired. NOT approved. Re-run optimize/create on fresh data.")
        ids = [a["action_id"] for a in cs["actions"]]
        unknown = wanted - set(ids)
        if unknown:
            say(f"ads approval: unknown action id(s) {sorted(unknown)} for {cs_id}. NOT approved. Valid: {ids}")
        chosen = [a for a in cs["actions"] if not wanted or a["action_id"] in wanted]
        ttl = gate.get("approval_ttl_hours", 24)
        appr = {
            "changeset_id": cs_id, "changeset_sha256": sha, "approval_code": code,
            "approved_at": now.isoformat(), "expires_at": (now + dt.timedelta(hours=ttl)).isoformat(),
            "approved_via": "user prompt (UserPromptSubmit hook)", "session_id": data.get("session_id"),
            "prompt_excerpt": m.group(0).strip()[:120],
            "actions": {a["action_id"]: ({"tool": a["executor"]["tool"], "input_sha256": gate["executors"][a["action_id"]]["input_sha256"], "used": False}
                                         if a.get("executor") else {"manual": True, "used": False}) for a in chosen},
        }
        (ads / "approvals").mkdir(exist_ok=True)
        prev_path = ads / "approvals" / f"{cs_id}.json"
        if prev_path.exists():
            try:
                prev = json.loads(prev_path.read_text())
                if prev.get("changeset_sha256") == sha and prev.get("session_id") == data.get("session_id") and prev.get("prompt_excerpt") == appr["prompt_excerpt"] \
                        and (now - dt.datetime.fromisoformat(prev["approved_at"])).total_seconds() < 120:
                    say(f"ads approval recorded by the user for {cs_id} (duplicate hook run ignored).")
            except (ValueError, KeyError):
                pass
        (ads / "approvals" / f"{cs_id}.json").write_text(json.dumps(appr, indent=2))
        with open(ads / "executions.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"event": "approved", "at": now.isoformat(), "changeset_id": cs_id, "actions": list(appr["actions"]), "session": data.get("session_id")}) + "\n")
        manual = [a["action_id"] for a in chosen if not a.get("executor")]
        say(f"ads approval recorded by the user for {cs_id}: actions {list(appr['actions'])} valid until {appr['expires_at']}. "
            f"Execute each MCP action with exactly the tool and input stored in the changeset (any difference is blocked). "
            + (f"Actions {manual} are manual: give the user the steps; do not attempt them. " if manual else "")
            + "Then verify each change by reading it back and run ads.py status.")
    say(f"ads approval: code {code} does not match any gated changeset. NOT approved.")


if __name__ == "__main__":
    main()
