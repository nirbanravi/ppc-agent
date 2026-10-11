"""Budget pacing and simple anomaly detection on daily data."""
import calendar
import datetime as dt
import statistics
from collections import defaultdict

from .confidence import score
from .util import fnum, today


def _status(pace, projected, budget):
    if budget <= 0:
        return "unknown"
    dev = projected / budget - 1
    if abs(dev) > 0.20:
        return "at_risk"
    if pace > 1.10:
        return "over"
    if pace < 0.90:
        return "under"
    return "on_track"


def pacing(sources, client):
    """Budgets come from client.json 'budgets': [{platform, entity ('*' or campaign), period:'month', amount, month:'YYYY-MM'?}]."""
    rows_out, findings, gaps = [], [], []
    budgets = client.get("budgets") or []
    if not budgets:
        gaps.append({"what": "No budgets in .ads/client.json", "impact": "Pacing cannot be computed", "how_to_fix": "Add budgets: [{platform, entity:'*', period:'month', amount}]", "severity": "blocking"})
        return rows_out, findings, gaps
    for b in budgets:
        plat = b.get("platform")
        srcs = [s for s in sources if s["platform"] == plat and "date" in s["manifest"]["columns_present"] and "spend" in s["manifest"]["columns_present"]]
        if not srcs:
            gaps.append({"what": f"No daily spend data for {plat}", "impact": f"Pacing for {plat} budget {fnum(b.get('amount'))} not computed", "how_to_fix": f"Export {plat} campaign report segmented by day for the current month", "severity": "blocking"})
            continue
        src = max(srcs, key=lambda s: s["manifest"]["date_range"].get("end") or "")
        last = dt.date.fromisoformat(src["manifest"]["date_range"]["end"])
        month = b.get("month") or last.strftime("%Y-%m")
        y, m = map(int, month.split("-"))
        dim = calendar.monthrange(y, m)[1]
        ent = b.get("entity", "*")
        spend = 0.0
        for r in src["rows"]:
            d = r.get("date")
            if not d or not d.startswith(month):
                continue
            if ent != "*" and r.get("campaign") != ent:
                continue
            spend += r.get("spend") or 0
        elapsed = last.day if last.strftime("%Y-%m") == month else dim
        expected = b["amount"] * elapsed / dim
        pace = spend / expected if expected else 0
        projected = spend / elapsed * dim if elapsed else 0
        status = _status(pace, projected, b["amount"])
        lag_days = (today() - last).days
        rows_out.append({"entity": ent if ent != "*" else f"{plat} (all)", "platform": plat, "period": month, "budget": b["amount"],
                         "spend_to_date": round(spend, 2), "expected_to_date": round(expected, 2), "projected_end": round(projected, 2),
                         "pace_pct": round(pace * 100, 1), "status": status, "source_id": src["id"]})
        if status in ("over", "under", "at_risk"):
            fresh = src["manifest"].get("freshness", "unknown")
            findings.append({
                "id": None, "check_id": "PACE001", "origin": "computed",
                "title": f"{plat} {ent if ent != '*' else 'account'} pacing {round(pace * 100)}% — projected {fnum(projected)} vs budget {fnum(b['amount'])}",
                "category": "pacing", "severity": "high" if status == "at_risk" else "medium", "kind": "estimated", "platform": plat,
                "entity": ent, "description": f"Linear projection from {elapsed} of {dim} days. Data ends {last.isoformat()} ({lag_days} day(s) before today).",
                "evidence": [{"source_id": src["id"], "selector": f"{month}-01..{last.isoformat()}" + ("" if ent == "*" else f", campaign='{ent}'"), "detail": "Month-to-date spend vs linear budget",
                              "values": {"spend_to_date": round(spend, 2), "expected_to_date": round(expected, 2), "budget": b["amount"], "days_elapsed": elapsed, "days_in_month": dim}}],
                "confidence": score(freshness=fresh, days=elapsed, extra=[(0.85, "linear projection ignores planned flighting/seasonality")] + ([(0.8, f"data lags today by {lag_days} days")] if lag_days > 2 else [])),
                "recommendation": "Adjust daily budgets so remaining spend = budget − spend_to_date over remaining days" + (f" (≈{fnum((b['amount'] - spend) / max(dim - elapsed, 1))}/day)" if dim > elapsed else ""),
            })
    return rows_out, findings, gaps


def anomalies(sources, z=3.0):
    """Flag last-day spend/CPA swings vs the trailing 14 days (robust z using MAD)."""
    findings = []
    for s in sources:
        if "date" not in s["manifest"]["columns_present"]:
            continue
        by = defaultdict(lambda: {"spend": 0.0, "conversions": 0.0, "clicks": 0.0})
        for r in s["rows"]:
            if r.get("date"):
                for m in by[r["date"]]:
                    by[r["date"]][m] += r.get(m) or 0
        days = sorted(by)
        if len(days) < 15:
            continue
        hist, last = days[-15:-1], days[-1]
        for metric in ("spend", "clicks"):
            xs = [by[d][metric] for d in hist]
            med = statistics.median(xs)
            mad = statistics.median([abs(x - med) for x in xs]) or (med * 0.1 or 1)
            val = by[last][metric]
            rz = 0.6745 * (val - med) / mad
            if abs(rz) >= z:
                findings.append({
                    "id": None, "check_id": "ANOM001", "origin": "computed",
                    "title": f"{s['platform']} {metric} on {last} is {'up' if rz > 0 else 'down'} sharply ({fnum(val)} vs median {fnum(med)})",
                    "category": "performance", "severity": "medium", "kind": "observed", "platform": s["platform"], "entity": "account",
                    "description": "Robust z-score against the previous 14 days. Partial-day data or reporting lag can cause false alarms on the latest day.",
                    "evidence": [{"source_id": s["id"], "selector": f"{hist[0]}..{last}", "detail": f"Daily {metric}", "values": {"latest": val, "median_14d": med, "robust_z": round(rz, 2)}}],
                    "confidence": score(freshness=s["manifest"].get("freshness", "unknown"), extra=[(0.8, "single-day signal; may be partial day")]),
                    "recommendation": "Check change history and delivery for that day before reacting.",
                })
    return findings
