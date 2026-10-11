"""Changesets and the pre-approval gate.

A changeset is a list of exact actions. The gate runs safety checks and, only if all pass,
issues a short approval code derived from the changeset's content hash. Any edit to the
changeset changes the hash, which invalidates the code and any approval made with it.
"""
import datetime as dt

from .util import canonical, iso, now_utc, read_json, sha256_obj, today, write_json
from .validate import validate

DEFAULT_GUARDRAILS = {
    "max_budget_change_pct": 30,
    "max_bid_change_pct": 25,
    "max_daily_spend_increase": None,  # absolute currency/day; None = no absolute cap
    "allow_delete": False,
    "allow_enable_new": False,          # new entities are created PAUSED unless allowed
    "max_actions": 25,
    "require_fresh_data_hours": 72,
    "allowed_accounts": [],             # empty = must be set in client.json before any write
    "approval_ttl_hours": 24,
    "changeset_ttl_hours": 72,
}

BUDGET_KEYS = ("daily_budget", "budget", "amount", "daily_budget_amount", "lifetime_budget")
BID_KEYS = ("bid", "cpc_bid", "max_cpc", "target_cpa", "target_roas", "bid_amount", "cost_cap")


def build_changeset(proposal, run, client):
    created = now_utc()
    g = dict(DEFAULT_GUARDRAILS)
    g.update(client.get("guardrails") or {})
    g.update(proposal.get("guardrails") or {})
    if not g.get("allowed_accounts"):
        g["allowed_accounts"] = client.get("accounts") or []
    actions = []
    for i, a in enumerate(proposal.get("actions", []), 1):
        a = dict(a)
        a.setdefault("action_id", f"a{i}")
        a.setdefault("risk", "medium")
        a.setdefault("executor", None)
        actions.append(a)
    seed = {"from_run": proposal.get("from_run") or run["run_id"], "actions": actions, "t": iso(created)}
    cs = {
        "schema_version": "1.0.0",
        "changeset_id": "cs-" + sha256_obj(seed)[:10],
        "created_at": iso(created),
        "expires_at": iso(created + dt.timedelta(hours=g["changeset_ttl_hours"])),
        "from_run": run["run_id"],
        "client": client.get("name", ""),
        "guardrails": {k: v for k, v in g.items() if k in ("max_budget_change_pct", "max_bid_change_pct", "max_daily_spend_increase", "allow_delete", "allow_enable_new", "max_actions", "require_fresh_data_hours", "allowed_accounts")},
        "actions": actions,
        "gate": None,
    }
    return cs, g


def changeset_hash(cs):
    body = {k: v for k, v in cs.items() if k != "gate"}
    return sha256_obj(body)


def approval_code(cs):
    return "ADS-" + changeset_hash(cs)[:6].upper()


def executor_input_hash(tool, tool_input):
    return sha256_obj({"tool": tool, "input": tool_input})


def _pct(before, after):
    try:
        b, a = float(before), float(after)
    except (TypeError, ValueError):
        return None
    if b == 0:
        return float("inf") if a else 0.0
    return (a - b) / b * 100


def run_gate(cs, run, ttl_hours=24):
    checks = []

    def chk(cid, ok, msg, action=None):
        checks.append({"check": cid, "passed": bool(ok), "detail": msg, **({"action_id": action} if action else {})})

    errs = validate(cs, "changeset")
    chk("schema", not errs, "valid" if not errs else "; ".join(errs[:8]))

    g = cs["guardrails"]
    chk("run_finalized", run is not None and run.get("integrity", {}).get("content_sha256"), f"source run {cs['from_run']} is finalized" if run else f"run {cs['from_run']} not found or not finalized")
    if run:
        chk("run_not_failed", run.get("status") != "failed", f"source run status: {run.get('status')}")
        ends = [s.get("date_range", {}).get("end") for s in run["sources"]["data"] if s.get("date_range", {}).get("end")]
        if ends:
            lag_h = (today() - dt.date.fromisoformat(max(ends))).days * 24
            chk("data_fresh", lag_h <= g["require_fresh_data_hours"], f"latest data {max(ends)} is ~{lag_h}h old (limit {g['require_fresh_data_hours']}h)")
        else:
            chk("data_fresh", False, "source run has no dated data; cannot prove freshness")
        finding_ids = {f["id"] for f in run.get("findings", [])}
    else:
        finding_ids = set()

    expires = dt.datetime.fromisoformat(cs["expires_at"].replace("Z", "+00:00"))
    chk("not_expired", now_utc() < expires, f"changeset expires {cs['expires_at']}")
    chk("max_actions", len(cs["actions"]) <= g["max_actions"], f"{len(cs['actions'])} action(s), limit {g['max_actions']}")
    chk("allowed_accounts_set", bool(g.get("allowed_accounts")), "allowed_accounts configured" if g.get("allowed_accounts") else "client.json has no 'accounts' allow-list; writes are blocked until it is set")

    seen, spend_increase = {}, 0.0
    for a in cs["actions"]:
        aid = a["action_id"]
        chk("account_allowed", a["account_id"] in (g.get("allowed_accounts") or []), f"account {a['account_id']}", aid)
        missing = [fid for fid in a.get("evidence_finding_ids", []) if fid not in finding_ids]
        chk("evidence_exists", a.get("evidence_finding_ids") and not missing, "cites " + ", ".join(a.get("evidence_finding_ids", [])) + (f"; unknown: {missing}" if missing else ""), aid)
        chk("rollback_defined", bool(a.get("rollback")), "rollback provided" if a.get("rollback") else "no rollback", aid)
        has_exec = bool(a.get("executor") and a["executor"].get("tool", "").startswith("mcp__") and isinstance(a["executor"].get("input"), dict))
        chk("execution_path", has_exec or bool(a.get("manual_steps")), "MCP executor with exact input" if has_exec else ("manual steps for a human" if a.get("manual_steps") else "no executor and no manual steps"), aid)
        if a["operation"] == "delete":
            chk("delete_allowed", g["allow_delete"], "delete operations are disabled by guardrails (prefer pause)", aid)
        if a["operation"] in ("create", "enable"):
            st = str((a.get("after") or {}).get("status", "")).upper()
            chk("new_entities_paused", g["allow_enable_new"] or (a["operation"] == "create" and st == "PAUSED"), f"after.status={st or 'unset'}; new or enabled entities must start PAUSED unless allow_enable_new", aid)
        b, af = a.get("before") or {}, a.get("after") or {}
        for k in BUDGET_KEYS:
            if k in af:
                p = _pct(b.get(k), af[k])
                if p is None:
                    chk("budget_before_known", False, f"{k}: before value missing, cannot bound change", aid)
                else:
                    chk("budget_change_within_limit", abs(p) <= g["max_budget_change_pct"], f"{k} {b.get(k)} → {af[k]} ({p:+.0f}%, limit ±{g['max_budget_change_pct']}%)", aid)
                    try:
                        spend_increase += max(0.0, float(af[k]) - float(b.get(k) or 0)) if "lifetime" not in k else 0
                    except (TypeError, ValueError):
                        pass
        for k in BID_KEYS:
            if k in af:
                p = _pct(b.get(k), af[k])
                if p is None:
                    chk("bid_before_known", False, f"{k}: before value missing, cannot bound change", aid)
                else:
                    chk("bid_change_within_limit", abs(p) <= g["max_bid_change_pct"], f"{k} {b.get(k)} → {af[k]} ({p:+.0f}%, limit ±{g['max_bid_change_pct']}%)", aid)
        key = (a["platform"], a["account_id"], a.get("entity_id") or a["entity"])
        if key in seen and a["operation"] != "add_negative":
            chk("no_conflicts", False, f"also changed by {seen[key]}", aid)
        seen.setdefault(key, aid)
    if g.get("max_daily_spend_increase") is not None:
        chk("daily_spend_increase", spend_increase <= g["max_daily_spend_increase"], f"total daily budget increase {spend_increase:.2f} (limit {g['max_daily_spend_increase']})")

    passed = all(c["passed"] for c in checks)
    gate = {
        "checked_at": iso(now_utc()),
        "changeset_sha256": changeset_hash(cs),
        "passed": passed,
        "checks": checks,
        "approval_code": approval_code(cs) if passed else None,
        "approval_ttl_hours": ttl_hours,
        "executors": {a["action_id"]: ({"tool": a["executor"]["tool"], "input_sha256": executor_input_hash(a["executor"]["tool"], a["executor"]["input"])} if a.get("executor") else None) for a in cs["actions"]},
    }
    return gate


def preview(cs, gate):
    L = [f"Changeset {cs['changeset_id']} from run {cs['from_run']} — {len(cs['actions'])} action(s)", ""]
    for a in cs["actions"]:
        b, af = a.get("before") or {}, a.get("after") or {}
        diff = ", ".join(f"{k}: {b.get(k, '∅')} → {v}" for k, v in af.items())
        L.append(f"  [{a['action_id']}] {a['platform']}/{a['account_id']} {a['operation']} {a['entity_type']} '{a['entity']}' {diff}  (risk {a.get('risk')}; evidence {', '.join(a.get('evidence_finding_ids', []))})")
        L.append(f"        via: {a['executor']['tool'] if a.get('executor') else 'MANUAL — ' + '; '.join(a.get('manual_steps', []))}")
    L.append("")
    fails = [c for c in gate["checks"] if not c["passed"]]
    if gate["passed"]:
        L.append(f"GATE PASSED ({len(gate['checks'])} checks).")
        L.append(f"Approval code: {gate['approval_code']}  (valid {gate['approval_ttl_hours']}h after approval; any edit to the changeset voids it)")
        L.append("The user approves by typing the word APPROVE followed by the code, optionally followed by action ids (e.g. a1,a3).")
    else:
        L.append(f"GATE FAILED — {len(fails)} check(s):")
        for c in fails:
            L.append(f"  ✗ {c['check']}{' [' + c['action_id'] + ']' if c.get('action_id') else ''}: {c['detail']}")
        L.append("No approval code issued. Fix the changeset and re-run gate.")
    return "\n".join(L)
