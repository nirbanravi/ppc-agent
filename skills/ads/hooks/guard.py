#!/usr/bin/env python3
"""PreToolUse / PostToolUse guard for the /ads skill.

Blocks, for the rest of the session once /ads is loaded:
  * write-capable tools on ad-platform MCP servers, unless the exact tool + input matches an
    action in an approved, unexpired, unused changeset approval;
  * raw HTTP writes to ad-platform API hosts from Bash (never allowed; use MCP executor or manual steps);
  * any tool edit to .ads/approvals, gate files, finalized run.json, or this hooks folder.

Unknown/ambiguous ad tools are treated as writes (fail closed). Non-ad tools are left alone.
Exit 0 with no output = no opinion (normal permission flow still applies).
"""
import contextlib
import datetime as dt
try:
    import fcntl  # POSIX
except ImportError:  # Windows: duplicate-registration race is not serialised
    fcntl = None
import hashlib
import json
import os
import re
import sys
from pathlib import Path

# Server-name tokens (split on _ - .) that mark an ad platform server, e.g. "google-ads-mcp", "meta_ads", "amazon-ads".
TOKEN_KEYWORDS = {"ads", "ad", "adwords", "gads", "meta", "facebook", "fb", "instagram", "linkedin", "tiktok", "bing", "msads",
                  "amazon", "sponsored", "reddit", "pinterest", "snap", "snapchat", "searchads", "twitter", "youtube", "dv360",
                  "adspirer", "marketing", "advertising"}
COMPOUND_KEYWORDS = ["googleads", "metaads", "amazonads", "microsoftads", "appleads", "searchads", "tiktokads", "linkedinads", "xads"]
# Tool names that touch ad objects on any server (covers aggregator MCPs with neutral server names).
AD_OBJECTS = re.compile(r"campaign|ad_?set|ad_?group|ad_?squad|keyword|creative|audience|bid|budget|ad_?account|line_?item|insertion_?order", re.I)
READ_VERBS = re.compile(r"(^|[_\-.])(get|list|search|query|read|fetch|describe|report|reports|insight|insights|stats|analytics|"
                        r"estimate|forecast|preview|lookup|find|count|status|info|metadata|schema|whoami|me|accounts|gaql|"
                        r"diagnose|diagnostics|history|audit|explain|check)([_\-.]|$)", re.I)
WRITE_VERBS = re.compile(r"(create|update|delete|remove|mutate|pause|enable|activate|deactivate|set|edit|upload|apply|launch|"
                         r"publish|modify|change|add|archive|duplicate|copy|submit|bid|budget_update|patch|post|put|"
                         r"execute|run_?action|request|send|attach|detach|link|unlink|approve|reject|resume|stop|start)", re.I)
API_HOSTS = ["googleads.googleapis.com", "graph.facebook.com", "api.linkedin.com", "business-api.tiktok.com",
             "bingads.microsoft.com", "api.ads.microsoft.com", "advertising-api", "ads-api.reddit.com", "api.pinterest.com",
             "adsapi.snapchat.com", "api.searchads.apple.com", "api.ads.apple.com", "ads-api.x.com", "ads-api.twitter.com",
             "mcp.facebook.com"]
HTTP_WRITE = re.compile(r"(-X\s*(POST|PUT|PATCH|DELETE)|--request\s+(POST|PUT|PATCH|DELETE)|\s-d\s|--data|--form|\s-F\s|"
                        r"requests\.(post|put|patch|delete)|method\s*=\s*['\"](POST|PUT|PATCH|DELETE)|:mutate|\.post\(|\.patch\(|\.delete\()", re.I)
PROTECTED = [re.compile(p) for p in (r"\.ads/approvals", r"\.ads/changesets/[^/]+\.gate\.json", r"\.ads/runs/[^/]+/run\.json",
                                     r"\.ads/executions\.jsonl", r"skills/ads/hooks/")]
SHELL_WRITE = re.compile(r"(>|\btee\b|\bcp\b|\bmv\b|\brm\b|\btouch\b|\bsed\s+-i|\bpython3?\s+-c|\bnode\s+-e|\bperl\b|\bchmod\b|\bln\b|\bdd\b|\btruncate\b)")


def out(decision, reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision, "permissionDecisionReason": reason}}))
    sys.exit(0)


def deny(reason):
    out("deny", "[ads guard] " + reason)


def find_ads(cwd):
    roots = [os.environ.get("CLAUDE_PROJECT_DIR"), cwd, os.getcwd()]
    for r in roots:
        if not r:
            continue
        for p in [Path(r), *Path(r).parents]:
            if (p / ".ads").is_dir():
                return p / ".ads"
    return None


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def input_hash(tool, tool_input):
    return hashlib.sha256(canonical({"tool": tool, "input": tool_input}).encode("utf-8")).hexdigest()


def is_ad_server(tool):
    parts = tool.split("__")
    server = parts[1].lower() if len(parts) > 2 else ""
    name = parts[-1].lower()
    extra = []
    ads = find_ads(None)
    if ads and (ads / "guard.json").exists():  # additive only: more servers to protect
        try:
            extra = [s.lower() for s in json.loads((ads / "guard.json").read_text()).get("ad_servers", [])]
        except (OSError, ValueError):
            pass
    tokens = set(re.split(r"[_\-.\s]+", server))
    if tokens & TOKEN_KEYWORDS or any(k in server for k in COMPOUND_KEYWORDS + extra):
        return True
    return bool(AD_OBJECTS.search(name))


def readonly_allowlist():
    p = Path(__file__).with_name("readonly_tools.json")
    try:
        return set(json.loads(p.read_text()).get("tools", []))
    except (OSError, ValueError):
        return set()


def classify(tool, tool_input):
    if tool in readonly_allowlist():
        return "read"
    name = tool.split("__")[-1]
    method = str((tool_input or {}).get("method", "")).upper()
    if method == "GET":
        return "read"
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        return "write"
    if WRITE_VERBS.search(name) and not re.match(r"^(get|list|search|query|fetch|read)", name, re.I):
        return "write"
    if READ_VERBS.search(name):
        return "read"
    return "write"  # unknown: fail closed


def now():
    return dt.datetime.now(dt.timezone.utc)


def log(ads, entry):
    entry["at"] = now().replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with open(ads / "executions.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


@contextlib.contextmanager
def locked(ads):
    """Serialise guard/approve runs: the same hook can be registered twice (plugin hooks.json + skill frontmatter)."""
    if fcntl is None:
        yield
        return
    with open(ads / ".guard.lock", "a+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def find_approval(ads, tool, tool_input, tool_use_id=None):
    h = input_hash(tool, tool_input)
    for p in sorted((ads / "approvals").glob("cs-*.json")):
        try:
            a = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        exp = dt.datetime.fromisoformat(a["expires_at"].replace("Z", "+00:00"))
        if now() >= exp:
            continue
        cs_path = ads / "changesets" / f"{a['changeset_id']}.json"
        try:
            cs = json.loads(cs_path.read_text())
        except (OSError, ValueError):
            continue
        body = {k: v for k, v in cs.items() if k != "gate"}
        if hashlib.sha256(canonical(body).encode("utf-8")).hexdigest() != a["changeset_sha256"]:
            continue  # changeset edited after approval: void
        for aid, act in a["actions"].items():
            if act.get("input_sha256") == h and act.get("tool") == tool:
                if not act.get("used"):
                    return p, a, aid
                if tool_use_id and act.get("tool_use_id") == tool_use_id:
                    return p, a, aid  # same call seen by a duplicate hook registration

    return None


def pre(data):
    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}

    if tool in ("Write", "Edit", "NotebookEdit", "MultiEdit"):
        path = str(ti.get("file_path") or ti.get("notebook_path") or "")
        if any(p.search(path) for p in PROTECTED):
            deny(f"{path} is managed by the ads engine/hooks and cannot be edited by tools. Approvals come only from the user typing APPROVE <code>.")
        return

    if tool == "Bash":
        cmd = str(ti.get("command", ""))
        if re.search(r"APPROVE\s+ADS-[0-9A-F]{6}", cmd, re.I):
            deny("approval phrases may only come from the user's own message")
        if any(p.search(cmd) for p in PROTECTED) and SHELL_WRITE.search(cmd) and "scripts/ads.py" not in cmd:
            deny("shell writes to approvals, gate files, finalized runs, execution log or guard hooks are blocked")
        if any(h in cmd for h in API_HOSTS) and HTTP_WRITE.search(cmd):
            deny("raw HTTP writes to ad platform APIs are blocked. Use an approved changeset with an MCP executor, or give the user manual steps.")
        return

    if tool.startswith("mcp__") and is_ad_server(tool):
        if classify(tool, ti) == "read":
            return
        ads = find_ads(data.get("cwd"))
        if not ads:
            deny(f"{tool} can change an ad account and there is no .ads workspace with approvals. Run /ads optimize or create to build a changeset first.")
        with locked(ads):
            hit = find_approval(ads, tool, ti, data.get("tool_use_id"))
            if hit and not hit[1]["actions"][hit[2]].get("used"):
                path, appr, aid = hit
                appr["actions"][aid].update({"used": True, "authorized_at": now().isoformat(), "tool_use_id": data.get("tool_use_id")})
                path.write_text(json.dumps(appr, indent=2))
                log(ads, {"event": "authorized", "changeset_id": appr["changeset_id"], "action_id": aid, "tool": tool, "input_sha256": input_hash(tool, ti), "tool_use_id": data.get("tool_use_id")})
            elif not hit:
                log(ads, {"event": "blocked", "tool": tool, "input_sha256": input_hash(tool, ti), "session": data.get("session_id")})
        if not hit:
            deny(f"{tool} looks write-capable and this exact call (tool + input) is not in an approved, unexpired changeset. "
                 "Build a changeset (ads.py propose), pass the gate, and have the user type the approval code. If this tool is read-only, add it to hooks/readonly_tools.json manually.")
        # No allow decision: the user's normal permission prompt still applies as a second check.
        return


def post(data):
    tool = data.get("tool_name", "")
    if not (tool.startswith("mcp__") and is_ad_server(tool)):
        return
    if classify(tool, data.get("tool_input") or {}) == "read":
        return
    ads = find_ads(data.get("cwd"))
    if not ads:
        return
    tid = data.get("tool_use_id")
    log_path = ads / "executions.jsonl"
    with locked(ads):
        if tid and log_path.exists() and f'"tool_use_id": "{tid}", "response_excerpt"' in log_path.read_text()[-200000:]:
            return  # already logged by a duplicate hook registration
        _post_log(ads, data, tool)


def _post_log(ads, data, tool):
    resp = data.get("tool_response")
    text = canonical(resp)[:2000] if resp is not None else ""
    log(ads, {"event": "executed", "tool": tool, "input_sha256": input_hash(tool, data.get("tool_input") or {}), "tool_use_id": data.get("tool_use_id"), "response_excerpt": text})


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        print("[ads guard] unreadable hook input", file=sys.stderr)
        sys.exit(2)
    ev = data.get("hook_event_name")
    if ev == "PreToolUse":
        pre(data)
    elif ev == "PostToolUse":
        post(data)
    sys.exit(0)


if __name__ == "__main__":
    main()
