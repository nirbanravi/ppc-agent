#!/usr/bin/env python3
"""/ads engine CLI. Stdlib only.

  ads.py init [--client NAME] [--currency INR] [--timezone Asia/Kolkata]
  ads.py start <command> [--platforms google,meta] [--question TEXT] [--supersedes RUN_ID] [--from RUN_ID,...]
  ads.py ingest --run RUN_ID FILE [FILE...] [--platform P] [--kind export|api_pull|mcp_pull|crm|analytics] [--pulled-at ISO]
  ads.py audit --run RUN_ID          deterministic checks
  ads.py monitor --run RUN_ID        pacing + anomalies + tracking checks
  ads.py finalize RUN_ID [--analyst FILE]
  ads.py render RUN_ID [--audience internal|client]
  ads.py validate PATH               run.json, changeset, or analyst.json
  ads.py propose --run RUN_ID --file PROPOSAL.json
  ads.py gate CHANGESET_ID
  ads.py status
  ads.py show RUN_ID
  ads.py docs-check
"""
import argparse
import datetime as dt
import json
import math
import os
import secrets
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from adslib import PLATFORMS, RUN_SCHEMA_VERSION, SKILL_VERSION  # noqa: E402
from adslib import checks as checks_mod  # noqa: E402
from adslib import gate as gate_mod  # noqa: E402
from adslib import pacing as pacing_mod  # noqa: E402
from adslib import render as render_mod  # noqa: E402
from adslib.confidence import cap_confidence, level_for  # noqa: E402
from adslib.normalize import IngestError, ingest_file  # noqa: E402
from adslib.util import iso, now_utc, read_json, sha256_file, sha256_obj, slug, today, write_json  # noqa: E402
from adslib.validate import semantic_checks_run, validate  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parents[1]
REGISTRY = SKILL_DIR / "references" / "platform-registry.json"
COMMANDS = ["audit", "plan", "create", "monitor", "optimize", "experiment", "report", "validate"]
DATA_COMMANDS = {"audit", "monitor", "optimize"}
SEV_W = {"critical": 25, "high": 12, "medium": 5, "low": 2, "info": 0}


def die(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def ws_root(create=False):
    env = os.environ.get("ADS_HOME")
    if env:
        return Path(env)
    cur = Path.cwd()
    for p in [cur, *cur.parents]:
        if (p / ".ads").is_dir():
            return p / ".ads"
    if create:
        return cur / ".ads"
    die("No .ads workspace found. Run: ads.py init --client 'Client name'")


def client_cfg(root):
    c = read_json(root / "client.json")
    if c is None:
        die("Missing .ads/client.json; run init")
    return c


def run_dir(root, rid):
    d = root / "runs" / rid
    if not d.is_dir():
        die(f"Run {rid} not found")
    return d


# ---------------------------------------------------------------- init / start
CLIENT_TEMPLATE = {
    "name": "Client",
    "currency": "INR",
    "timezone": "Asia/Kolkata",
    "accounts": [],
    "targets": {"default": {"cpa": None, "roas": None}},
    "budgets": [],
    "guardrails": {},
    "fx": {},
    "notes": "accounts = allow-list for any write. targets per platform override default, e.g. targets.google.cpa. budgets: [{platform, entity:'*'|campaign, period:'month', amount, month:'YYYY-MM'}]",
}


def cmd_init(a):
    root = ws_root(create=True)
    for sub in ("runs", "changesets", "approvals"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    if not (root / "client.json").exists():
        c = dict(CLIENT_TEMPLATE)
        c.update({k: v for k, v in {"name": a.client, "currency": a.currency, "timezone": a.timezone}.items() if v})
        c["targets"] = {"default": {k: v for k, v in c["targets"]["default"].items() if v is not None}}
        write_json(root / "client.json", c)
    gi = root / ".gitignore"
    if not gi.exists():
        gi.write_text("# Exports and normalized data can contain client data. Commit run.json/report files deliberately.\nruns/*/data/\nruns/*/inputs/\napprovals/\n")
    if not (root / "index.json").exists():
        write_json(root / "index.json", {"runs": [], "changesets": []})
    print(f"Workspace ready at {root}")
    print(f"Edit {root / 'client.json'}: targets, budgets and the 'accounts' allow-list (writes stay blocked until it is set).")


def cmd_start(a):
    root = ws_root()
    client = client_cfg(root)
    if a.command not in COMMANDS:
        die(f"Unknown command {a.command}; one of {COMMANDS}")
    plats = [p.strip() for p in (a.platforms or "").split(",") if p.strip()]
    bad = [p for p in plats if p not in PLATFORMS]
    if bad:
        die(f"Unknown platform(s) {bad}; valid: {PLATFORMS}")
    t = now_utc()
    rid = f"{t.strftime('%Y%m%dT%H%MZ')}-{a.command}-{slug(client['name'])}-{secrets.token_hex(3)}"
    revision, supersedes = 1, None
    if a.supersedes:
        prev = read_json(root / "runs" / a.supersedes / "run.json")
        if not prev:
            die(f"Cannot supersede {a.supersedes}: not finalized")
        revision, supersedes = prev.get("revision", 1) + 1, a.supersedes
    d = root / "runs" / rid
    (d / "data").mkdir(parents=True)
    draft = {
        "schema_version": RUN_SCHEMA_VERSION, "run_id": rid, "revision": revision, "supersedes": supersedes,
        "command": a.command, "status": "partial", "created_at": iso(t), "finalized_at": None, "skill_version": SKILL_VERSION,
        "client": {k: client.get(k) for k in ("name", "currency", "timezone", "targets") if client.get(k) is not None},
        "scope": {"platforms": plats, "question": a.question or ""},
        "sources": {"data": [], "docs": []}, "data_gaps": [], "errors": [],
        "summary": {"headline": ""}, "findings": [], "experiments": [], "pacing": [], "changeset_ids": [],
        "assumptions": [], "questions": [], "integrity": {"content_sha256": ""},
        "_coverage": [],
    }
    if a.from_runs:
        for src_id in a.from_runs.split(","):
            prev = read_json(root / "runs" / src_id / "run.json")
            if not prev:
                draft["errors"].append({"stage": "start", "source_id": src_id, "message": "referenced run is missing or not finalized", "recoverable": True})
                continue
            draft["sources"]["data"] += [s for s in prev["sources"]["data"] if s["id"] not in {x["id"] for x in draft["sources"]["data"]}]
            for f in prev["findings"]:
                f = dict(f)
                f["evidence"] = f["evidence"] + [{"source_id": f"run:{src_id}", "detail": f"carried over from run {src_id}"}]
                draft["findings"].append(f)
            draft["pacing"] += prev.get("pacing", [])
            draft["data_gaps"] += prev.get("data_gaps", [])
            draft["errors"] += prev.get("errors", [])
            draft["sources"]["docs"] += prev["sources"].get("docs", [])
            for p in prev["scope"]["platforms"]:
                if p not in draft["scope"]["platforms"]:
                    draft["scope"]["platforms"].append(p)
            draft.setdefault("_from_runs", []).append({"run_id": src_id, "status": prev["status"], "finalized_at": prev.get("finalized_at")})
    write_json(d / "draft.json", draft)
    print(rid)


# ---------------------------------------------------------------- ingest
def freshness_for(end, command):
    if not end:
        return "unknown"
    lag = (today() - dt.date.fromisoformat(end)).days
    fresh, aging = (2, 7) if command in ("monitor", "optimize") else (14, 45)
    return "fresh" if lag <= fresh else "aging" if lag <= aging else "stale"


def cmd_ingest(a):
    root = ws_root()
    d = run_dir(root, a.run)
    draft = read_json(d / "draft.json")
    if draft is None:
        die("Run is already finalized; start a new revision with --supersedes")
    inputs = d / "inputs"
    inputs.mkdir(exist_ok=True)
    ok = 0
    for f in a.files:
        p = Path(f)
        sid = f"src{len(draft['sources']['data']) + 1}-{slug(p.stem, 20)}"
        if not p.exists():
            draft["errors"].append({"stage": "ingest", "source_id": sid, "message": f"file not found: {f}", "recoverable": True})
            print(f"✗ {f}: not found", file=sys.stderr)
            continue
        try:
            res = ingest_file(p, a.platform)
        except IngestError as e:
            draft["errors"].append({"stage": "ingest", "source_id": sid, "message": f"{p.name}: {e}", "recoverable": True})
            print(f"✗ {p.name}: {e}", file=sys.stderr)
            continue
        h = sha256_file(p)
        if any(s["sha256"] == h for s in draft["sources"]["data"]):
            print(f"• {p.name}: identical file already ingested, skipped")
            continue
        shutil.copy2(p, inputs / p.name)
        dr = res["date_range"]
        days = None
        if dr.get("start") and dr.get("end"):
            days = (dt.date.fromisoformat(dr["end"]) - dt.date.fromisoformat(dr["start"])).days + 1
        cur = res["currencies"][0] if len(res["currencies"]) == 1 else None
        if len(res["currencies"]) > 1:
            res["warnings"].append(f"Multiple currencies in one file: {res['currencies']}")
        manifest = {
            "id": sid, "kind": a.kind, "platform": res["platform"], "path": str(inputs / p.name), "sha256": h,
            "rows": len(res["rows"]), "report_type": res["report_type"],
            "date_range": {"start": dr.get("start"), "end": dr.get("end"), **({"days": days} if days else {})},
            "pulled_at": a.pulled_at, "freshness": freshness_for(dr.get("end"), draft["command"]),
            "columns_present": res["columns_present"], "columns_missing": res["columns_missing"],
            "currency": cur, "warnings": res["warnings"],
        }
        if res["platform"] == "unknown":
            draft["data_gaps"].append({"what": f"{sid}: platform not identified", "impact": "Platform-specific checks and labels may be wrong", "how_to_fix": "Re-run ingest with --platform", "severity": "major"})
        if manifest["freshness"] == "stale":
            draft["data_gaps"].append({"what": f"{sid}: data ends {dr.get('end')}", "impact": "Findings describe that period, not the account today", "how_to_fix": "Export a recent date range", "severity": "major" if draft["command"] in ("monitor", "optimize") else "minor"})
        draft["sources"]["data"].append(manifest)
        write_json(d / "data" / f"{sid}.json", {"manifest": manifest, "rows": res["rows"]})
        if res["platform"] not in draft["scope"]["platforms"] and res["platform"] != "unknown":
            draft["scope"]["platforms"].append(res["platform"])
        ok += 1
        print(f"✓ {p.name} → {sid}: {res['platform']}, {len(res['rows'])} rows, {res['report_type']}, {dr.get('start')}→{dr.get('end')}, freshness {manifest['freshness']}")
        for w in res["warnings"]:
            print(f"    ! {w}")
        if res["columns_missing"]:
            print(f"    missing columns: {', '.join(res['columns_missing'])}")
    _update_scope_dates(draft)
    write_json(d / "draft.json", draft)
    if ok == 0 and a.files:
        sys.exit(1)


def _update_scope_dates(draft):
    s = [x["date_range"]["start"] for x in draft["sources"]["data"] if x.get("date_range", {}).get("start")]
    e = [x["date_range"]["end"] for x in draft["sources"]["data"] if x.get("date_range", {}).get("end")]
    if s and e:
        days = (dt.date.fromisoformat(max(e)) - dt.date.fromisoformat(min(s))).days + 1
        draft["scope"]["date_range"] = {"start": min(s), "end": max(e), "days": days}


def _load_sources(d, draft):
    out = []
    for m in draft["sources"]["data"]:
        f = d / "data" / f"{m['id']}.json"
        if f.exists():
            blob = read_json(f)
            out.append({"id": m["id"], "platform": m["platform"], "manifest": m, "rows": blob["rows"]})
    return out


def _assign_ids(findings, existing):
    used = {f["id"] for f in existing if f.get("id")}
    counters = {}
    for f in findings:
        if f.get("id"):
            continue
        k = f.get("check_id", "F")
        counters[k] = counters.get(k, 0) + 1
        while f"{k}-{counters[k]}" in used:
            counters[k] += 1
        f["id"] = f"{k}-{counters[k]}"
        used.add(f["id"])
    return findings


def _key_metrics(sources, client):
    out = []
    by = {}
    for s in sources:
        if s["manifest"].get("report_type") == "search_terms":
            continue  # avoid double counting with campaign exports
        p = s["platform"]
        b = by.setdefault(p, {"spend": 0.0, "conversions": 0.0, "conv_value": 0.0, "cur": set(), "has": set(), "sid": s["id"]})
        for r in s["rows"]:
            for m in ("spend", "conversions", "conv_value"):
                if r.get(m) is not None:
                    b[m] += r[m]
                    b["has"].add(m)
        if s["manifest"].get("currency"):
            b["cur"].add(s["manifest"]["currency"])
    for p, b in by.items():
        cur = next(iter(b["cur"])) if len(b["cur"]) == 1 else (client.get("currency") + "?" if client.get("currency") else "")
        if "spend" in b["has"]:
            out.append({"name": f"{p} spend", "value": round(b["spend"], 2), "unit": cur, "kind": "observed", "source_id": b["sid"]})
        if "conversions" in b["has"]:
            out.append({"name": f"{p} conversions", "value": round(b["conversions"], 2), "kind": "observed", "source_id": b["sid"]})
            if b["conversions"]:
                out.append({"name": f"{p} CPA", "value": round(b["spend"] / b["conversions"], 2), "unit": cur, "kind": "observed", "source_id": b["sid"]})
        if "conv_value" in b["has"] and b["spend"]:
            out.append({"name": f"{p} ROAS", "value": round(b["conv_value"] / b["spend"], 2), "unit": "x", "kind": "observed", "source_id": b["sid"]})
    return out


def cmd_audit(a, monitor=False):
    root = ws_root()
    d = run_dir(root, a.run)
    draft = read_json(d / "draft.json")
    if draft is None:
        die("Run already finalized")
    client = client_cfg(root)
    sources = _load_sources(d, draft)
    if not sources:
        draft["errors"].append({"stage": "monitor" if monitor else "audit", "message": "no data sources ingested", "recoverable": True})
        write_json(d / "draft.json", draft)
        die("No data ingested for this run")
    # re-runs replace previous computed output
    draft["findings"] = [f for f in draft["findings"] if f.get("origin") != "computed" or "evidence" in f and any(str(e.get("source_id", "")).startswith("run:") for e in f["evidence"])]
    draft["data_gaps"] = [g for g in draft["data_gaps"] if not g.get("_computed")]
    f, g, cov = checks_mod.run_checks(sources, client)
    if monitor:
        prow, pf, pg = pacing_mod.pacing(sources, client)
        f += pf + pacing_mod.anomalies(sources)
        g += pg
        draft["pacing"] = prow
    for x in g:
        x["_computed"] = True
    draft["findings"] += _assign_ids(f, draft["findings"])
    draft["data_gaps"] += g
    draft["_coverage"] = cov
    draft["summary"]["key_metrics"] = _key_metrics(sources, client)
    write_json(d / "draft.json", draft)
    sev = {}
    for x in f:
        sev[x["severity"]] = sev.get(x["severity"], 0) + 1
    print(f"{len(f)} computed finding(s): " + ", ".join(f"{k} {v}" for k, v in sorted(sev.items(), key=lambda kv: list(SEV_W).index(kv[0]))))
    for x in sorted(f, key=lambda x: list(SEV_W).index(x["severity"])):
        print(f"  {x['id']:<10} {x['severity']:<8} {x['confidence']['level']:<6} {x['title']}")
    if g:
        print(f"{len(g)} data gap(s):")
        for x in g:
            print(f"  [{x.get('severity')}] {x['what']} — {x['impact']}")
    if monitor and draft["pacing"]:
        print("Pacing:")
        for p in draft["pacing"]:
            print(f"  {p['entity']:<24} {p['pace_pct']:>6}%  spend {p['spend_to_date']} / expected {p['expected_to_date']}  → projected {p['projected_end']} vs {p['budget']}  [{p['status']}]")


# ---------------------------------------------------------------- finalize / render
def _registry():
    return read_json(REGISTRY, {"platforms": {}})


def _doc_stale(verified_at, max_days=45):
    if not verified_at:
        return True
    try:
        return (today() - dt.date.fromisoformat(verified_at[:10])).days > max_days
    except ValueError:
        return True


def _merge_analyst(draft, an):
    for f in an.get("findings", []):
        f = dict(f)
        f["origin"] = "analyst"
        draft["findings"].append(f)
    for k in ("experiments", "assumptions", "questions", "data_gaps", "errors", "changeset_ids"):
        draft[k] = draft.get(k, []) + an.get(k, [])
    draft["sources"]["docs"] += an.get("docs", [])
    if an.get("plan"):
        draft["plan"] = an["plan"]
    if an.get("summary"):
        km = an["summary"].get("key_metrics")
        draft["summary"].update({k: v for k, v in an["summary"].items() if k != "key_metrics"})
        if km:
            draft["summary"]["key_metrics"] = draft["summary"].get("key_metrics", []) + km
    if an.get("status_reason"):
        draft["status_reason"] = an["status_reason"]


def cmd_finalize(a):
    root = ws_root()
    d = run_dir(root, a.run)
    if (d / "run.json").exists():
        die("Run already finalized and immutable. Start a new revision: ads.py start <command> --supersedes " + a.run)
    draft = read_json(d / "draft.json")
    an_path = Path(a.analyst) if a.analyst else d / "analyst.json"
    if an_path.exists():
        try:
            an = read_json(an_path)
        except json.JSONDecodeError as e:
            die(f"analyst file is not valid JSON: {e}")
        _merge_analyst(draft, an)
    run = {k: v for k, v in draft.items() if not k.startswith("_")}
    for g in run["data_gaps"]:
        g.pop("_computed", None)

    # docs: registry entries for platforms in scope are always listed, with staleness
    reg = _registry()["platforms"]
    have = {x["url"] for x in run["sources"]["docs"]}
    for p in run["scope"]["platforms"]:
        e = reg.get(p)
        if not e:
            continue
        for u in e.get("sources", [])[:1]:
            if u not in have:
                run["sources"]["docs"].append({"url": u, "title": f"{e['name']}: {e.get('api', '')}", "verified_at": e.get("verified_at"), "used_for": "platform version/rules baseline (registry)"})
                have.add(u)
        if e.get("status") == "unverified" or _doc_stale(e.get("verified_at"), e.get("stale_after_days") or 0):
            run["data_gaps"].append({"what": f"Platform rules for {e['name']} not verified recently (status: {e.get('status')}, verified {e.get('verified_at') or 'never'})", "impact": "Version/policy-dependent advice for this platform is capped at low confidence", "how_to_fix": "Look up current official docs and record them in analyst.json docs[]", "severity": "minor"})
    for doc in run["sources"]["docs"]:
        doc["stale"] = _doc_stale(doc.get("verified_at"))
    stale_docs = {x["url"] for x in run["sources"]["docs"] if x["stale"]}
    src_fresh = {s["id"]: s["freshness"] for s in run["sources"]["data"]}

    # confidence caps for analyst work
    for f in run["findings"]:
        if f.get("origin") == "analyst":
            if "confidence" not in f:
                f["confidence"] = {"level": "low", "score": 0.4, "reasons": ["analyst did not state confidence"]}
            if any(src_fresh.get(e.get("source_id")) == "stale" for e in f.get("evidence", [])):
                f["confidence"] = cap_confidence(f["confidence"], 0.74, "cites stale data")
            if any(u in stale_docs for u in f.get("doc_refs", [])):
                f["confidence"] = cap_confidence(f["confidence"], 0.49, "relies on platform docs not verified in the last 45 days")
            if all(str(e.get("source_id", "")).startswith("doc:") for e in f.get("evidence", [])) and f.get("evidence"):
                f["confidence"] = cap_confidence(f["confidence"], 0.6, "supported by documentation only, not account data")
        f["confidence"]["level"] = level_for(f["confidence"]["score"])
    _assign_ids(run["findings"], [])

    # status
    reasons = []
    if run["command"] in DATA_COMMANDS and not run["sources"]["data"]:
        status = "failed"
        reasons.append("no account data was loaded")
    else:
        status = "complete"
        if run["errors"]:
            status = "partial"
            reasons.append(f"{len(run['errors'])} error(s) during the run")
        if any(g.get("severity") == "blocking" for g in run["data_gaps"]):
            status = "partial"
            reasons.append("blocking data gap(s)")
        if run["command"] in ("monitor", "optimize") and any(s["freshness"] in ("stale", "unknown") for s in run["sources"]["data"]):
            status = "partial"
            reasons.append("stale or undated data for a time-sensitive command")
    run["status"] = status
    if reasons:
        run["status_reason"] = "; ".join(reasons) + (f". {run['status_reason']}" if run.get("status_reason") else "")

    # summary, score, overall confidence
    fs = run["findings"]
    if fs:
        wsum = sum(max(SEV_W[f["severity"]], 1) for f in fs)
        oc = sum(f["confidence"]["score"] * max(SEV_W[f["severity"]], 1) for f in fs) / wsum
    else:
        oc = 0.5 if run["sources"]["data"] else 0.2
    major = sum(1 for g in run["data_gaps"] if g.get("severity") == "major")
    blocking = sum(1 for g in run["data_gaps"] if g.get("severity") == "blocking")
    oc = max(0.05, oc * (0.95 ** major) * (0.75 ** blocking) * (0.8 if run["errors"] else 1))
    oreasons = [f"{len(fs)} finding(s)", f"{major} major / {blocking} blocking gap(s)"] + (["errors present"] if run["errors"] else [])
    run["summary"]["overall_confidence"] = {"level": level_for(oc), "score": round(oc, 2), "reasons": oreasons}
    if run["command"] in ("audit", "monitor") and run["sources"]["data"]:
        pen = sum(SEV_W[f["severity"]] * f["confidence"]["score"] for f in fs if f.get("kind") != "recommendation")
        run["summary"]["score"] = round(100 * math.exp(-pen / 100), 1)  # diminishing penalties; never negative
    else:
        run["summary"].setdefault("score", None)
    if not run["summary"].get("headline"):
        sev = {}
        for f in fs:
            sev[f["severity"]] = sev.get(f["severity"], 0) + 1
        top = ", ".join(f"{v} {k}" for k, v in sorted(sev.items(), key=lambda kv: list(SEV_W).index(kv[0]))) or "no issues flagged by automated checks"
        run["summary"]["headline"] = f"{run['command'].capitalize()} of {', '.join(run['scope']['platforms']) or 'no platforms'}: {top}." + (f" Status {status}: {run.get('status_reason')}." if status != "complete" else "")

    run["finalized_at"] = iso(now_utc())
    run["integrity"] = {"content_sha256": "", "inputs_sha256": [s["sha256"] for s in run["sources"]["data"]]}
    errs = validate(run, "run") + semantic_checks_run(run)
    if errs:
        write_json(d / "validation_errors.json", errs)
        print("Validation failed; run NOT finalized. Fix analyst.json (or the draft) and retry:", file=sys.stderr)
        for e in errs[:40]:
            print("  - " + e, file=sys.stderr)
        sys.exit(2)
    body = dict(run)
    body["integrity"] = {k: v for k, v in run["integrity"].items() if k != "content_sha256"}
    run["integrity"]["content_sha256"] = sha256_obj(body)
    write_json(d / "run.json", run)
    (d / "validation_errors.json").unlink(missing_ok=True)
    os.replace(d / "draft.json", d / "draft.finalized.json")
    _render(d, run, "internal")
    idx = read_json(root / "index.json", {"runs": [], "changesets": []})
    idx["runs"].append({"run_id": run["run_id"], "command": run["command"], "status": run["status"], "revision": run.get("revision", 1),
                        "supersedes": run.get("supersedes"), "finalized_at": run["finalized_at"], "platforms": run["scope"]["platforms"],
                        "findings": len(fs), "sha256": run["integrity"]["content_sha256"]})
    write_json(root / "index.json", idx)
    print(f"Finalized {run['run_id']} — status {status.upper()}" + (f" ({run.get('status_reason')})" if run.get("status_reason") else ""))
    print(f"  overall confidence {run['summary']['overall_confidence']['level']} ({run['summary']['overall_confidence']['score']})" + (f", score {run['summary']['score']}/100" if run['summary'].get('score') is not None else ""))
    print(f"  {d / 'run.json'}\n  {d / 'report.md'}\n  {d / 'report.html'}")


def _render(d, run, audience):
    suffix = "" if audience == "internal" else ".client"
    (d / f"report{suffix}.md").write_text(render_mod.to_markdown(run, audience), encoding="utf-8")
    (d / f"report{suffix}.html").write_text(render_mod.to_html(run, audience), encoding="utf-8")


def cmd_render(a):
    root = ws_root()
    d = run_dir(root, a.run)
    run = read_json(d / "run.json")
    if not run:
        die("Run not finalized")
    _render(d, run, a.audience)
    suffix = "" if a.audience == "internal" else ".client"
    print(f"{d / f'report{suffix}.md'}\n{d / f'report{suffix}.html'}")


# ---------------------------------------------------------------- validate
def cmd_validate(a):
    obj = read_json(a.path)
    if obj is None:
        die(f"{a.path} not found")
    if "changeset_id" in obj:
        errs = validate(obj, "changeset")
        kind = "changeset"
    elif "run_id" in obj and "integrity" in obj:
        errs = validate(obj, "run") + semantic_checks_run(obj)
        kind = "run"
        if obj["integrity"].get("content_sha256"):
            body = dict(obj)
            body["integrity"] = {k: v for k, v in obj["integrity"].items() if k != "content_sha256"}
            if sha256_obj(body) != obj["integrity"]["content_sha256"]:
                errs.append("integrity: content hash mismatch — run.json was modified after finalize")
    else:
        kind = "analyst"
        errs = []
        for i, f in enumerate(obj.get("findings", [])):
            for k in ("id", "title", "category", "severity", "kind", "platform", "evidence", "confidence"):
                if k not in f:
                    errs.append(f"findings[{i}] missing {k}")
            if not f.get("evidence"):
                errs.append(f"findings[{i}] has no evidence")
    if errs:
        print(f"{kind}: {len(errs)} problem(s)")
        for e in errs:
            print("  - " + e)
        sys.exit(1)
    print(f"{kind}: valid")


# ---------------------------------------------------------------- changesets
def cmd_propose(a):
    root = ws_root()
    client = client_cfg(root)
    d = run_dir(root, a.run)
    run = read_json(d / "run.json")
    if not run:
        die("Proposals must come from a finalized run (finalize first)")
    proposal = read_json(a.file)
    if not proposal or not proposal.get("actions"):
        die("Proposal file must contain an 'actions' list")
    cs, g = gate_mod.build_changeset(proposal, run, client)
    gate = gate_mod.run_gate(cs, run, g["approval_ttl_hours"])
    write_json(root / "changesets" / f"{cs['changeset_id']}.json", cs)
    write_json(root / "changesets" / f"{cs['changeset_id']}.gate.json", gate)
    idx = read_json(root / "index.json", {"runs": [], "changesets": []})
    idx["changesets"].append({"changeset_id": cs["changeset_id"], "from_run": run["run_id"], "created_at": cs["created_at"], "actions": len(cs["actions"]), "gate_passed": gate["passed"]})
    write_json(root / "index.json", idx)
    print(gate_mod.preview(cs, gate))
    sys.exit(0 if gate["passed"] else 3)


def cmd_gate(a):
    root = ws_root()
    cs = read_json(root / "changesets" / f"{a.changeset}.json")
    if not cs:
        die("changeset not found")
    run = read_json(root / "runs" / cs["from_run"] / "run.json")
    client = client_cfg(root)
    ttl = (client.get("guardrails") or {}).get("approval_ttl_hours", gate_mod.DEFAULT_GUARDRAILS["approval_ttl_hours"])
    gate = gate_mod.run_gate(cs, run, ttl)
    write_json(root / "changesets" / f"{a.changeset}.gate.json", gate)
    print(gate_mod.preview(cs, gate))
    sys.exit(0 if gate["passed"] else 3)


def cmd_status(a):
    root = ws_root()
    idx = read_json(root / "index.json", {"runs": [], "changesets": []})
    print("Runs:")
    for r in idx["runs"][-20:]:
        print(f"  {r['run_id']}  {r['status']:<8} rev{r['revision']}  {r['findings']} findings  {','.join(r['platforms'])}")
    drafts = [p.parent.name for p in (root / "runs").glob("*/draft.json")]
    if drafts:
        print("Open drafts (not finalized): " + ", ".join(drafts))
    print("Changesets:")
    for c in idx["changesets"][-20:]:
        appr = read_json(root / "approvals" / f"{c['changeset_id']}.json")
        state = "approved" if appr else ("gate passed, awaiting approval" if c["gate_passed"] else "gate failed")
        if appr:
            used = sum(1 for x in appr["actions"].values() if x.get("used"))
            state += f" ({used}/{len(appr['actions'])} executed, expires {appr['expires_at']})"
        print(f"  {c['changeset_id']}  {c['actions']} action(s)  {state}")
    log = root / "executions.jsonl"
    if log.exists():
        lines = log.read_text().strip().splitlines()[-10:]
        print("Recent execution log:")
        for ln in lines:
            e = json.loads(ln)
            print(f"  {e['at']}  {e['event']:<10} {e.get('changeset_id', '')} {e.get('action_id', '')} {e.get('tool', '')}")


def cmd_show(a):
    root = ws_root()
    d = run_dir(root, a.run)
    run = read_json(d / "run.json") or read_json(d / "draft.json")
    print(json.dumps({k: run[k] for k in ("run_id", "command", "status", "status_reason", "summary") if k in run}, indent=2))


def cmd_docs_check(a):
    reg = _registry()
    print(f"Registry {reg.get('registry_version')} (today {today()}):")
    for p, e in reg["platforms"].items():
        stale = e.get("status") == "unverified" or _doc_stale(e.get("verified_at"), e.get("stale_after_days") or 0)
        print(f"  {p:<10} {'STALE/UNVERIFIED' if stale else 'ok':<17} verified {e.get('verified_at') or 'never':<11} {e.get('current_version', '')}")
        for dl in e.get("deadlines", []):
            print(f"             deadline: {dl['what']} — {dl['when']}")


def main():
    ap = argparse.ArgumentParser(prog="ads.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("init"); p.add_argument("--client"); p.add_argument("--currency"); p.add_argument("--timezone"); p.set_defaults(fn=cmd_init)
    p = sp.add_parser("start"); p.add_argument("command"); p.add_argument("--platforms"); p.add_argument("--question"); p.add_argument("--supersedes"); p.add_argument("--from", dest="from_runs"); p.set_defaults(fn=cmd_start)
    p = sp.add_parser("ingest"); p.add_argument("--run", required=True); p.add_argument("files", nargs="+"); p.add_argument("--platform", choices=PLATFORMS); p.add_argument("--kind", default="export", choices=["export", "api_pull", "mcp_pull", "manual", "crm", "analytics"]); p.add_argument("--pulled-at"); p.set_defaults(fn=cmd_ingest)
    p = sp.add_parser("audit"); p.add_argument("--run", required=True); p.set_defaults(fn=lambda a: cmd_audit(a, False))
    p = sp.add_parser("monitor"); p.add_argument("--run", required=True); p.set_defaults(fn=lambda a: cmd_audit(a, True))
    p = sp.add_parser("finalize"); p.add_argument("run"); p.add_argument("--analyst"); p.set_defaults(fn=cmd_finalize)
    p = sp.add_parser("render"); p.add_argument("run"); p.add_argument("--audience", default="internal", choices=["internal", "client"]); p.set_defaults(fn=cmd_render)
    p = sp.add_parser("validate"); p.add_argument("path"); p.set_defaults(fn=cmd_validate)
    p = sp.add_parser("propose"); p.add_argument("--run", required=True); p.add_argument("--file", required=True); p.set_defaults(fn=cmd_propose)
    p = sp.add_parser("gate"); p.add_argument("changeset"); p.set_defaults(fn=cmd_gate)
    p = sp.add_parser("status"); p.set_defaults(fn=cmd_status)
    p = sp.add_parser("show"); p.add_argument("run"); p.set_defaults(fn=cmd_show)
    p = sp.add_parser("docs-check"); p.set_defaults(fn=cmd_docs_check)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
