"""Render a run record to Markdown and self-contained HTML. Same content, two formats."""
import html

from .util import fnum

SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
PLATFORM_NAMES = {"google": "Google Ads", "meta": "Meta", "youtube": "YouTube", "linkedin": "LinkedIn", "tiktok": "TikTok",
                  "microsoft": "Microsoft Ads", "amazon": "Amazon Ads", "reddit": "Reddit", "pinterest": "Pinterest",
                  "snapchat": "Snapchat", "apple": "Apple Ads", "x": "X", "unknown": "Unknown"}


def _sorted_findings(run):
    return sorted(run.get("findings", []), key=lambda f: (SEV_ORDER.get(f["severity"], 9), -f["confidence"]["score"]))


def _vals(values):
    return ", ".join(f"{k}={fnum(v) if isinstance(v, (int, float)) else v}" for k, v in (values or {}).items())


def _md_esc(s):
    return str(s if s is not None else "").replace("|", "\\|").replace("\n", " ")


def _dr(d):
    d = d or {}
    return f"{d.get('start') or '?'} → {d.get('end') or '?'}"


def to_markdown(run, audience="internal"):
    c, s = run["client"], run["summary"]
    L = []
    L.append(f"# {c['name']} — {run['command'].capitalize()} report")
    L.append("")
    plats = ", ".join(PLATFORM_NAMES.get(p, p) for p in run["scope"]["platforms"])
    L.append(f"**Status:** {run['status'].upper()}" + (f" — {run['status_reason']}" if run.get("status_reason") else ""))
    L.append(f"**Platforms:** {plats}  ")
    L.append(f"**Data period:** {_dr(run['scope'].get('date_range'))}  ")
    L.append(f"**Generated:** {run.get('finalized_at') or run['created_at']} · run `{run['run_id']}` rev {run.get('revision', 1)}")
    oc = s.get("overall_confidence")
    if oc:
        L.append(f"**Overall confidence:** {oc['level']} ({oc['score']:.2f})")
    L.append("")
    L.append("## Summary")
    L.append(s["headline"])
    if s.get("score") is not None:
        L.append(f"\nHealth score: **{round(s['score'])}/100** (penalties weighted by severity × confidence)")
    if s.get("key_metrics"):
        L.append("\n| Metric | Value | Type | Source |\n|---|---|---|---|")
        for m in s["key_metrics"]:
            L.append(f"| {_md_esc(m['name'])} | {_md_esc(fnum(m['value']) if isinstance(m['value'], (int, float)) else m['value'])}{(' ' + m['unit']) if m.get('unit') else ''} | {m.get('kind', 'observed')} | {m.get('source_id', '')} |")

    L.append("\n## Data quality and limits")
    if run["errors"]:
        L.append("**Errors (parts of this run failed):**")
        for e in run["errors"]:
            L.append(f"- [{e['stage']}] {e.get('source_id', '')} {e['message']}")
    if run["data_gaps"]:
        L.append("**Missing or limited data:**")
        for g in sorted(run["data_gaps"], key=lambda g: {"blocking": 0, "major": 1, "minor": 2}.get(g.get("severity", "minor"), 3)):
            L.append(f"- **{g.get('severity', 'minor')}** — {g['what']}. {g['impact']}." + (f" Fix: {g['how_to_fix']}" if g.get("how_to_fix") else ""))
    if not run["errors"] and not run["data_gaps"]:
        L.append("No errors or data gaps recorded.")
    L.append("\n| Source | Platform | Type | Rows | Period | Freshness | Notes |\n|---|---|---|---|---|---|---|")
    for d in run["sources"]["data"]:
        L.append(f"| `{d['id']}` | {PLATFORM_NAMES.get(d['platform'], d['platform'])} | {d.get('report_type', d['kind'])} | {d['rows']} | {_dr(d.get('date_range'))} | {d['freshness']} | {_md_esc('; '.join(d.get('warnings', [])))} |")

    fs = _sorted_findings(run)
    if fs:
        L.append(f"\n## Findings ({len(fs)})")
        for f in fs:
            L.append(f"\n### {f['id']} · {f['severity'].upper()} · {_md_esc(f['title'])}")
            L.append(f"*{PLATFORM_NAMES.get(f['platform'], f['platform'])} · {f['category']} · {f['kind']} · {f['origin']}* — confidence **{f['confidence']['level']}** ({f['confidence']['score']:.2f}): {'; '.join(f['confidence']['reasons'])}")
            if f.get("description"):
                L.append(f"\n{f['description']}")
            L.append("\nEvidence:")
            for e in f["evidence"]:
                L.append(f"- `{e['source_id']}` {e.get('selector', '')} — {e['detail']}" + (f" ({_vals(e.get('values'))})" if e.get("values") else ""))
            if f.get("impact"):
                im = f["impact"]
                L.append(f"\nEstimated impact: {fnum(im.get('low'))}–{fnum(im.get('high'))} {im.get('unit', '')} {im.get('metric', '')}. Method: {im.get('method', 'not stated')}")
            if f.get("recommendation"):
                L.append(f"\n**Recommendation:** {f['recommendation']}")

    if run.get("pacing"):
        L.append("\n## Pacing\n\n| Entity | Platform | Period | Budget | Spend to date | Expected | Projected | Pace | Status |\n|---|---|---|---|---|---|---|---|---|")
        for p in run["pacing"]:
            L.append(f"| {_md_esc(p['entity'])} | {p['platform']} | {p.get('period', '')} | {fnum(p['budget'])} | {fnum(p['spend_to_date'])} | {fnum(p['expected_to_date'])} | {fnum(p.get('projected_end'))} | {p['pace_pct']}% | {p['status']} |")

    if run.get("plan"):
        L.append("\n## Plan")
        L += _plan_md(run["plan"])

    if run.get("experiments"):
        L.append("\n## Experiments")
        for x in run["experiments"]:
            L.append(f"\n### {x['id']} · {_md_esc(x['hypothesis'])}")
            L.append(f"- Platform: {x['platform']} · Priority: {x.get('priority', '—')} · Confidence: {x['confidence']['level']}")
            L.append(f"- Primary metric: {x['primary_metric']}" + (f"; guardrails: {', '.join(x['guardrail_metrics'])}" if x.get("guardrail_metrics") else ""))
            L.append(f"- Design: {x['design']}")
            L.append(f"- MDE: {x.get('mde') or '—'} · Duration: {fnum(x.get('estimated_duration_days'))} days · Budget: {fnum(x.get('budget_needed'))}")
            if x.get("decision_rule"):
                L.append(f"- Decision rule: {x['decision_rule']}")

    if run.get("changeset_ids"):
        L.append("\n## Proposed changes")
        L.append("These are proposals only. Nothing has changed in any account. Each changeset needs a passing gate and explicit approval.")
        for cid in run["changeset_ids"]:
            L.append(f"- `{cid}` — see `.ads/changesets/{cid}.json`")

    if run.get("assumptions") or run.get("questions"):
        L.append("\n## Assumptions and open questions")
        for a in run.get("assumptions", []):
            L.append(f"- Assumption: {a}")
        for q in run.get("questions", []):
            L.append(f"- Question: {q}")

    if audience == "internal" and run["sources"]["docs"]:
        L.append("\n## Platform documentation used")
        for d in run["sources"]["docs"]:
            stale = " **(STALE — re-verify)**" if d.get("stale") else ""
            L.append(f"- [{d.get('title') or d['url']}]({d['url']}) — verified {d.get('verified_at') or 'never'}{stale}" + (f" · {d['used_for']}" if d.get("used_for") else ""))

    L.append(f"\n---\n*Integrity: sha256 `{run['integrity']['content_sha256'][:16]}…` · schema {run['schema_version']} · skill {run.get('skill_version', '')}. Estimates are labelled; all other numbers come from the listed sources.*")
    return "\n".join(L) + "\n"


def _plan_md(plan):
    L = []
    if plan.get("objective"):
        L.append(f"**Objective:** {plan['objective']}")
    if plan.get("total_budget") is not None:
        L.append(f"**Total budget:** {fnum(plan['total_budget'])} {plan.get('currency', '')} / {plan.get('period', 'period')}")
    if plan.get("allocations"):
        L.append("\n| Platform | Campaign / line | Budget | Share | Goal | Rationale | Confidence |\n|---|---|---|---|---|---|---|")
        for a in plan["allocations"]:
            L.append(f"| {a.get('platform', '')} | {_md_esc(a.get('name', ''))} | {fnum(a.get('budget'))} | {fnum(a.get('share_pct'))}% | {_md_esc(a.get('goal', ''))} | {_md_esc(a.get('rationale', ''))} | {a.get('confidence', '')} |")
    for sec in ("structure", "milestones", "risks"):
        if plan.get(sec):
            L.append(f"\n**{sec.capitalize()}:**")
            for item in plan[sec]:
                L.append(f"- {item if isinstance(item, str) else _md_esc(item)}")
    return L


CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1b;--muted:#6b6a65;--line:#e4e1d9;--card:#fff;--crit:#b42318;--high:#c4320a;--med:#b54708;--low:#4b5563;--info:#3b5bdb;--ok:#067647;--warn:#b54708;--accent:#1f3a5f}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#141413;--fg:#ecebe6;--muted:#a3a29b;--line:#2c2b28;--card:#1c1c1a;--crit:#f97066;--high:#fd853a;--med:#fdb022;--low:#9ca3af;--info:#91a7ff;--ok:#47cd89;--warn:#fdb022;--accent:#9ec5fe}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:980px;margin:0 auto;padding:32px 16px 64px}h1{font-size:28px;margin:0 0 4px}h2{font-size:19px;margin:36px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}h3{font-size:15px;margin:0}
.meta{color:var(--muted);font-size:13px}.pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:600;border:1px solid currentColor}
.complete{color:var(--ok)}.partial{color:var(--warn)}.failed{color:var(--crit)}
.critical{color:var(--crit)}.high{color:var(--high)}.medium{color:var(--med)}.low{color:var(--low)}.info{color:var(--info)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:10px 0}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}.kpi .v{font-size:22px;font-weight:650}.kpi .n{color:var(--muted);font-size:12px}
table{width:100%;border-collapse:collapse;font-size:13px;display:block;overflow-x:auto}th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted);font-weight:600}
ul{padding-left:20px;margin:6px 0}.ev{font-size:13px;color:var(--muted)}.ev code{color:var(--fg)}code{font:12px ui-monospace,SFMono-Regular,Menlo,monospace}
.gap-blocking{border-left:3px solid var(--crit)}.gap-major{border-left:3px solid var(--warn)}.gap-minor{border-left:3px solid var(--line)}
.conf{font-size:12px;color:var(--muted)}.rec{margin-top:8px}footer{margin-top:40px;color:var(--muted);font-size:12px}
@media print{body{background:#fff}.card{break-inside:avoid}}
"""


def _e(x):
    return html.escape(str(x if x is not None else ""))


def to_html(run, audience="internal"):
    c, s = run["client"], run["summary"]
    P = []
    plats = ", ".join(PLATFORM_NAMES.get(p, p) for p in run["scope"]["platforms"])
    P.append(f"<header><h1>{_e(c['name'])} — {_e(run['command'].capitalize())} report</h1>")
    P.append(f"<div class='meta'><span class='pill {run['status']}'>{run['status'].upper()}</span> · {_e(plats)} · data {_e(_dr(run['scope'].get('date_range')))} · generated {_e(run.get('finalized_at') or run['created_at'])}</div>")
    if run.get("status_reason"):
        P.append(f"<p class='meta'>{_e(run['status_reason'])}</p>")
    P.append("</header>")

    P.append("<h2>Summary</h2>")
    P.append(f"<p>{_e(s['headline'])}</p>")
    oc = s.get("overall_confidence")
    kp = []
    if s.get("score") is not None:
        kp.append(("Health score", f"{round(s['score'])}/100"))
    if oc:
        kp.append(("Overall confidence", f"{oc['level']} ({oc['score']:.2f})"))
    for m in s.get("key_metrics", []):
        v = fnum(m["value"]) if isinstance(m["value"], (int, float)) else m["value"]
        kp.append((m["name"] + (" (est.)" if m.get("kind") == "estimated" else ""), f"{v}{(' ' + m['unit']) if m.get('unit') else ''}"))
    if kp:
        P.append("<div class='kpis'>" + "".join(f"<div class='card kpi'><div class='v'>{_e(v)}</div><div class='n'>{_e(n)}</div></div>" for n, v in kp) + "</div>")

    P.append("<h2>Data quality and limits</h2>")
    for e in run["errors"]:
        P.append(f"<div class='card gap-blocking'><strong>Error</strong> [{_e(e['stage'])}] {_e(e.get('source_id', ''))} {_e(e['message'])}</div>")
    for g in sorted(run["data_gaps"], key=lambda g: {"blocking": 0, "major": 1, "minor": 2}.get(g.get("severity", "minor"), 3)):
        sev = g.get("severity", "minor")
        P.append(f"<div class='card gap-{sev}'><strong>{_e(sev)}</strong> — {_e(g['what'])}. {_e(g['impact'])}." + (f" <span class='meta'>Fix: {_e(g['how_to_fix'])}</span>" if g.get("how_to_fix") else "") + "</div>")
    if not run["errors"] and not run["data_gaps"]:
        P.append("<p class='meta'>No errors or data gaps recorded.</p>")
    P.append("<table><tr><th>Source</th><th>Platform</th><th>Type</th><th>Rows</th><th>Period</th><th>Freshness</th><th>Notes</th></tr>")
    for d in run["sources"]["data"]:
        P.append(f"<tr><td><code>{_e(d['id'])}</code></td><td>{_e(PLATFORM_NAMES.get(d['platform'], d['platform']))}</td><td>{_e(d.get('report_type', d['kind']))}</td><td>{d['rows']}</td><td>{_e(_dr(d.get('date_range')))}</td><td>{_e(d['freshness'])}</td><td>{_e('; '.join(d.get('warnings', [])))}</td></tr>")
    P.append("</table>")

    fs = _sorted_findings(run)
    if fs:
        P.append(f"<h2>Findings ({len(fs)})</h2>")
        for f in fs:
            P.append("<div class='card'>")
            P.append(f"<h3><span class='{f['severity']}'>{f['severity'].upper()}</span> · {_e(f['title'])}</h3>")
            P.append(f"<div class='conf'>{_e(f['id'])} · {_e(PLATFORM_NAMES.get(f['platform'], f['platform']))} · {_e(f['category'])} · {_e(f['kind'])} · confidence <strong>{_e(f['confidence']['level'])}</strong> ({f['confidence']['score']:.2f}) — {_e('; '.join(f['confidence']['reasons']))}</div>")
            if f.get("description"):
                P.append(f"<p>{_e(f['description'])}</p>")
            P.append("<ul class='ev'>" + "".join(f"<li><code>{_e(e['source_id'])}</code> {_e(e.get('selector', ''))} — {_e(e['detail'])}" + (f" ({_e(_vals(e.get('values')))})" if e.get("values") else "") + "</li>" for e in f["evidence"]) + "</ul>")
            if f.get("impact"):
                im = f["impact"]
                P.append(f"<div class='meta'>Estimated impact: {_e(fnum(im.get('low')))}–{_e(fnum(im.get('high')))} {_e(im.get('unit', ''))} {_e(im.get('metric', ''))}. Method: {_e(im.get('method', 'not stated'))}</div>")
            if f.get("recommendation"):
                P.append(f"<div class='rec'><strong>Recommendation:</strong> {_e(f['recommendation'])}</div>")
            P.append("</div>")

    if run.get("pacing"):
        P.append("<h2>Pacing</h2><table><tr><th>Entity</th><th>Platform</th><th>Period</th><th>Budget</th><th>Spend to date</th><th>Expected</th><th>Projected</th><th>Pace</th><th>Status</th></tr>")
        for p in run["pacing"]:
            cls = {"on_track": "complete", "under": "partial", "over": "partial", "at_risk": "failed"}.get(p["status"], "")
            P.append(f"<tr><td>{_e(p['entity'])}</td><td>{_e(p['platform'])}</td><td>{_e(p.get('period', ''))}</td><td>{fnum(p['budget'])}</td><td>{fnum(p['spend_to_date'])}</td><td>{fnum(p['expected_to_date'])}</td><td>{fnum(p.get('projected_end'))}</td><td>{p['pace_pct']}%</td><td class='{cls}'>{_e(p['status'])}</td></tr>")
        P.append("</table>")

    if run.get("plan"):
        plan = run["plan"]
        P.append("<h2>Plan</h2>")
        if plan.get("objective"):
            P.append(f"<p><strong>Objective:</strong> {_e(plan['objective'])}</p>")
        if plan.get("total_budget") is not None:
            P.append(f"<p><strong>Total budget:</strong> {fnum(plan['total_budget'])} {_e(plan.get('currency', ''))} / {_e(plan.get('period', 'period'))}</p>")
        if plan.get("allocations"):
            P.append("<table><tr><th>Platform</th><th>Line</th><th>Budget</th><th>Share</th><th>Goal</th><th>Rationale</th><th>Confidence</th></tr>")
            for a in plan["allocations"]:
                P.append(f"<tr><td>{_e(a.get('platform'))}</td><td>{_e(a.get('name'))}</td><td>{fnum(a.get('budget'))}</td><td>{fnum(a.get('share_pct'))}%</td><td>{_e(a.get('goal'))}</td><td>{_e(a.get('rationale'))}</td><td>{_e(a.get('confidence'))}</td></tr>")
            P.append("</table>")
        for sec in ("structure", "milestones", "risks"):
            if plan.get(sec):
                P.append(f"<h3 style='margin-top:14px'>{sec.capitalize()}</h3><ul>" + "".join(f"<li>{_e(i)}</li>" for i in plan[sec]) + "</ul>")

    if run.get("experiments"):
        P.append("<h2>Experiments</h2>")
        for x in run["experiments"]:
            P.append(f"<div class='card'><h3>{_e(x['id'])} · {_e(x['hypothesis'])}</h3><div class='conf'>{_e(x['platform'])} · priority {_e(x.get('priority', '—'))} · confidence {_e(x['confidence']['level'])}</div>"
                     f"<ul><li>Primary metric: {_e(x['primary_metric'])}" + (f"; guardrails: {_e(', '.join(x['guardrail_metrics']))}" if x.get("guardrail_metrics") else "") + "</li>"
                     f"<li>Design: {_e(x['design'])}</li><li>MDE: {_e(x.get('mde') or '—')} · Duration: {fnum(x.get('estimated_duration_days'))} days · Budget: {fnum(x.get('budget_needed'))}</li>"
                     + (f"<li>Decision rule: {_e(x['decision_rule'])}</li>" if x.get("decision_rule") else "") + "</ul></div>")

    if run.get("changeset_ids"):
        P.append("<h2>Proposed changes</h2><p>Proposals only — nothing has changed in any account. Each changeset needs a passing gate and explicit approval.</p><ul>" + "".join(f"<li><code>{_e(c)}</code></li>" for c in run["changeset_ids"]) + "</ul>")

    if run.get("assumptions") or run.get("questions"):
        P.append("<h2>Assumptions and open questions</h2><ul>" + "".join(f"<li>Assumption: {_e(a)}</li>" for a in run.get("assumptions", [])) + "".join(f"<li>Question: {_e(q)}</li>" for q in run.get("questions", [])) + "</ul>")

    if audience == "internal" and run["sources"]["docs"]:
        P.append("<h2>Platform documentation used</h2><ul>")
        for d in run["sources"]["docs"]:
            P.append(f"<li><a href='{_e(d['url'])}'>{_e(d.get('title') or d['url'])}</a> — verified {_e(d.get('verified_at') or 'never')}" + (" <strong class='failed'>STALE — re-verify</strong>" if d.get("stale") else "") + (f" · {_e(d['used_for'])}" if d.get("used_for") else "") + "</li>")
        P.append("</ul>")

    P.append(f"<footer>Run <code>{_e(run['run_id'])}</code> rev {run.get('revision', 1)} · sha256 <code>{_e(run['integrity']['content_sha256'][:16])}…</code> · schema {_e(run['schema_version'])}. Estimates are labelled; all other numbers come from the listed sources.</footer>")
    title = f"{c['name']} {run['command']} report"
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{_e(title)}</title><style>{CSS}</style></head><body><main>" + "\n".join(P) + "</main></body></html>\n")
