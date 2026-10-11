"""Deterministic checks over normalized exports.

Each check declares the columns it needs. If they are missing, the check is not run and a
data gap is recorded instead, so the report shows what could not be checked rather than
silently passing it.
"""
import datetime as dt
import statistics
from collections import defaultdict

from .confidence import cap_confidence, score
from .util import safe_div, fnum

import re

METRICS = ("spend", "impressions", "clicks", "conversions", "conv_value")
UPPER_FUNNEL = re.compile(r"awareness|reach|video ?views?|brand ?lift|engagement|thruplay|consideration|video_views|awareness", re.I)


def _agg(rows, key):
    out = defaultdict(lambda: {m: 0.0 for m in METRICS} | {"_has": set(), "budget": None, "lost_is_budget": [], "lost_is_rank": [], "impr_share": [], "frequency": [], "status": None, "campaign_type": None, "days": set()})
    for r in rows:
        k = r.get(key) or "(blank)"
        a = out[k]
        for m in METRICS:
            v = r.get(m)
            if v is not None:
                a[m] += v
                a["_has"].add(m)
        for m in ("lost_is_budget", "lost_is_rank", "impr_share", "frequency"):
            if r.get(m) is not None:
                a[m].append(r[m])
        if r.get("budget") is not None:
            a["budget"] = r["budget"]
        a["status"] = r.get("status") or a["status"]
        a["campaign_type"] = r.get("campaign_type") or a["campaign_type"]
        if r.get("date"):
            a["days"].add(r["date"])
    return out


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def _days(src):
    dr = src["manifest"].get("date_range") or {}
    try:
        return (dt.date.fromisoformat(dr["end"]) - dt.date.fromisoformat(dr["start"])).days + 1
    except (KeyError, TypeError, ValueError):
        return None


def _targets(client, platform):
    t = dict((client.get("targets") or {}).get("default", {}))
    t.update((client.get("targets") or {}).get(platform, {}))
    return t


class Ctx:
    def __init__(self, src, client):
        self.src = src
        self.sid = src["id"]
        self.platform = src["platform"]
        self.rows = src["rows"]
        self.cols = set(src["manifest"]["columns_present"])
        self.fresh = src["manifest"].get("freshness", "unknown")
        self.days = _days(src)
        self.targets = _targets(client, self.platform)
        self.cur = src["manifest"].get("currency") or ""
        self.findings, self.gaps, self.ran, self.skipped = [], [], [], []

    def needs(self, check_id, cols, why):
        missing = [c for c in cols if c not in self.cols]
        if missing:
            self.skipped.append(check_id)
            self.gaps.append({
                "what": f"{self.sid}: missing column(s) {', '.join(missing)}",
                "impact": f"Check {check_id} ({why}) was not run",
                "blocks_checks": [check_id],
                "how_to_fix": f"Re-export with {', '.join(missing)} included",
                "severity": "major" if check_id.startswith(("TRK", "PERF")) else "minor",
            })
            return False
        self.ran.append(check_id)
        return True

    def add(self, check_id, title, category, severity, kind, entity, description, evidence, conf, recommendation=None, impact=None):
        f = {
            "id": None, "check_id": check_id, "origin": "computed", "title": title, "category": category,
            "severity": severity, "kind": kind, "platform": self.platform, "entity": entity,
            "description": description, "evidence": evidence, "confidence": conf,
        }
        if recommendation:
            f["recommendation"] = recommendation
        if impact:
            f["impact"] = impact
        self.findings.append(f)

    def ev(self, selector, detail, values):
        return {"source_id": self.sid, "selector": selector, "detail": detail, "values": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in values.items()}}


def run_checks(sources, client):
    findings, gaps, coverage = [], [], []
    currencies = defaultdict(set)
    for src in sources:
        c = Ctx(src, client)
        if src["manifest"].get("currency"):
            currencies[src["platform"]].add(src["manifest"]["currency"])
        rt = src["manifest"].get("report_type")
        if rt == "search_terms":
            _search_terms(c)
        else:
            _campaign_checks(c)
        if any(f["check_id"] == "TRK003" for f in c.findings):
            for f in c.findings:
                if f["check_id"] != "TRK003" and f["category"] in ("performance", "budget", "bidding", "search_terms", "measurement"):
                    f["confidence"] = cap_confidence(f["confidence"], 0.6, "a recent conversion tracking break in this source distorts conversion-based metrics")
        findings += c.findings
        gaps += c.gaps
        coverage.append({"source_id": c.sid, "ran": c.ran, "skipped": c.skipped})
    all_cur = set().union(*currencies.values()) if currencies else set()
    if len(all_cur) > 1:
        gaps.append({"what": f"Multiple currencies across sources: {', '.join(sorted(all_cur))}",
                     "impact": "Cross-platform totals and blended CPA/ROAS are not comparable without FX conversion; blended figures were not computed",
                     "how_to_fix": "Provide FX rates in client.json (fx) or export in one currency", "severity": "major"})
    return findings, gaps, coverage


def _campaign_checks(c):
    if "campaign" not in c.cols:
        c.gaps.append({"what": f"{c.sid}: no campaign column", "impact": "Campaign-level checks skipped", "severity": "major", "how_to_fix": "Export at campaign level or lower"})
        return
    agg = _agg(c.rows, "campaign")
    tot = {m: sum(a[m] for a in agg.values()) for m in METRICS}
    has_conv = "conversions" in c.cols
    acct_cpa = safe_div(tot["spend"], tot["conversions"]) if has_conv else None

    # TRK001: account spends with zero conversions
    if c.needs("TRK001", ["spend", "conversions"], "conversion tracking presence"):
        if tot["spend"] > 0 and tot["conversions"] == 0:
            c.add("TRK001", "Spend with zero recorded conversions across the whole export", "tracking", "critical", "observed",
                  "account", "Either conversion tracking is broken/not imported, the wrong conversion column was exported, or the account genuinely produced no conversions.",
                  [c.ev("all rows", "Total spend vs total conversions", {"spend": tot["spend"], "conversions": 0})],
                  score(completeness=1, freshness=c.fresh, days=c.days),
                  "Verify conversion actions are active and included in the 'Conversions' column; compare against CRM/analytics for the same dates.")

    # TRK002: individual campaigns burning money with zero conversions
    if has_conv and "spend" in c.cols and acct_cpa:
        c.ran.append("TRK002")
        thresh = max(2 * (c.targets.get("cpa") or acct_cpa), 0.05 * tot["spend"])
        for name, a in sorted(agg.items(), key=lambda kv: -kv[1]["spend"]):
            if a["conversions"] == 0 and a["spend"] >= thresh:
                upper = bool(UPPER_FUNNEL.search(f"{name} {a.get('campaign_type') or ''}"))
                c.add("TRK002", f"'{name}' spent {fnum(a['spend'])} {c.cur} with 0 conversions" + (" (looks like an awareness/reach campaign)" if upper else ""),
                      "performance", "low" if upper else "high", "observed", name,
                      f"Spend is above the waste threshold of {fnum(thresh)} (the larger of 2× CPA benchmark and 5% of account spend) with no conversions."
                      + (" The name/objective suggests an upper-funnel goal, so zero conversions may be expected; judge it on reach/view metrics instead." if upper else ""),
                      [c.ev(f"campaign='{name}'", "Campaign totals for the export period", {"spend": a["spend"], "clicks": a["clicks"], "conversions": 0, "benchmark_cpa": c.targets.get("cpa") or acct_cpa})],
                      score(clicks=a["clicks"], freshness=c.fresh, days=c.days, extra=[(0.9, "zero conversions can also mean a delayed or upper-funnel objective")]),
                      "Confirm the campaign's objective and conversion setup; if it is a conversion campaign, cut budget or pause pending a tracking check.",
                      {"metric": "spend_without_conversions", "low": round(a["spend"] * 0.5, 2), "high": round(a["spend"], 2), "unit": c.cur, "method": "Upper bound = full spend; lower bound assumes half still drives assisted/untracked value"})

    # TRK003: conversions dropped to zero recently while spend continued (needs daily data)
    if c.needs("TRK003", ["date", "spend", "conversions"], "recent tracking break detection"):
        _tracking_break(c)

    # PERF001: CPA vs target
    if has_conv and c.targets.get("cpa") and "spend" in c.cols:
        c.ran.append("PERF001")
        tgt = c.targets["cpa"]
        if acct_cpa and acct_cpa > tgt * 1.15:
            excess = tot["spend"] - tot["conversions"] * tgt
            c.add("PERF001", f"CPA {fnum(acct_cpa)} is {round((acct_cpa / tgt - 1) * 100)}% above target {fnum(tgt)}", "performance", "high", "observed", "account",
                  "Blended CPA across all campaigns in this export exceeds the client target.",
                  [c.ev("all rows", "spend / conversions", {"spend": tot["spend"], "conversions": tot["conversions"], "cpa": acct_cpa, "target_cpa": tgt})],
                  score(conversions=tot["conversions"], freshness=c.fresh, days=c.days),
                  "Shift budget from campaigns above 1.5x target CPA to those below target; see campaign-level findings.",
                  {"metric": "cost_above_target", "low": round(excess * 0.5, 2), "high": round(excess, 2), "unit": c.cur, "method": "Spend minus conversions x target CPA; low end assumes only half is recoverable"})
    elif has_conv and not c.targets.get("cpa"):
        c.gaps.append({"what": f"No CPA target for {c.platform}", "impact": "PERF001 judged against account average only", "blocks_checks": ["PERF001"], "how_to_fix": "Add targets.<platform>.cpa to .ads/client.json", "severity": "minor"})

    # PERF002: ROAS vs target
    if c.needs("PERF002", ["spend", "conv_value"], "return on ad spend"):
        roas = safe_div(tot["conv_value"], tot["spend"])
        tgt = c.targets.get("roas")
        if has_conv and tot["conversions"] > 0 and tot["conv_value"] == 0:
            c.add("VAL001", "Conversions recorded but conversion value is zero", "measurement", "high", "observed", "account",
                  "ROAS cannot be measured and value-based bidding has nothing to optimise towards.",
                  [c.ev("all rows", "conversions vs conv_value", {"conversions": tot["conversions"], "conv_value": 0})],
                  score(freshness=c.fresh, days=c.days),
                  "Pass transaction values (or lead values) with conversions, or confirm this is a lead-gen account where value is not used.")
        elif roas is not None and tgt and roas < tgt * 0.85:
            c.add("PERF002", f"ROAS {roas:.2f} is below target {tgt:.2f}", "performance", "high", "observed", "account",
                  "Blended return on ad spend is more than 15% under target.",
                  [c.ev("all rows", "conv_value / spend", {"spend": tot["spend"], "conv_value": tot["conv_value"], "roas": roas, "target_roas": tgt})],
                  score(conversions=tot["conversions"] if has_conv else None, freshness=c.fresh, days=c.days,
                        extra=[(0.9, "platform-reported value; not reconciled with orders/CRM")]),
                  "Reconcile platform value with backend revenue before cutting spend; then rebalance toward campaigns above target.")

    # PERF003: campaigns far above account CPA holding meaningful spend
    if has_conv and acct_cpa and "spend" in c.cols:
        c.ran.append("PERF003")
        for name, a in agg.items():
            share = safe_div(a["spend"], tot["spend"]) or 0
            cpa = safe_div(a["spend"], a["conversions"])
            if cpa and share >= 0.10 and cpa > 2 * acct_cpa:
                excess = a["spend"] - a["conversions"] * acct_cpa
                c.add("PERF003", f"'{name}' CPA {fnum(cpa)} is {cpa / acct_cpa:.1f}x the account average on {round(share * 100)}% of spend",
                      "budget", "high" if share >= 0.25 else "medium", "observed", name,
                      "A large share of budget is going to a campaign that converts at a much higher cost than the rest of the account.",
                      [c.ev(f"campaign='{name}'", "Campaign vs account", {"spend": a["spend"], "conversions": a["conversions"], "cpa": cpa, "account_cpa": acct_cpa, "spend_share": share})],
                      score(conversions=a["conversions"], freshness=c.fresh, days=c.days,
                            extra=[(0.9, "campaigns can have different objectives/funnel roles; confirm before comparing")]),
                      "Check whether the campaign has a different role (prospecting, brand awareness). If not, reduce budget or tighten targeting.",
                      {"metric": "excess_cost_vs_account_cpa", "low": round(excess * 0.3, 2), "high": round(excess, 2), "unit": c.cur, "method": "Spend minus conversions x account CPA; range reflects uncertain recoverability"})

    # BUD001 / RNK001: impression share (search platforms)
    if c.platform in ("google", "microsoft", "youtube") or "lost_is_budget" in c.cols:
        if c.needs("BUD001", ["lost_is_budget"], "budget-constrained campaigns"):
            for name, a in agg.items():
                lib = _mean(a["lost_is_budget"])
                cpa = safe_div(a["spend"], a["conversions"]) if has_conv else None
                if lib is not None and lib >= 0.20 and (cpa is None or not acct_cpa or cpa <= acct_cpa):
                    c.add("BUD001", f"'{name}' loses {round(lib * 100)}% impression share to budget" + (" while converting at or below account CPA" if cpa else ""),
                          "budget", "medium", "observed", name,
                          "The campaign is capped by budget; if its marginal CPA holds, more budget should buy more conversions.",
                          [c.ev(f"campaign='{name}'", "Average Search lost IS (budget)", {"lost_is_budget": lib, "cpa": cpa, "account_cpa": acct_cpa, "budget": a["budget"]})],
                          score(conversions=a["conversions"] if has_conv else None, freshness=c.fresh, days=c.days,
                                extra=[(0.85, "marginal CPA on extra budget is usually higher than average CPA")]),
                          "Test a 15–20% budget increase funded from campaigns flagged in PERF003, and watch marginal CPA for 2 weeks.")
        if "lost_is_rank" in c.cols:
            c.ran.append("RNK001")
            for name, a in agg.items():
                lir = _mean(a["lost_is_rank"])
                if lir is not None and lir >= 0.40 and a["impressions"] >= 1000:
                    c.add("RNK001", f"'{name}' loses {round(lir * 100)}% impression share to ad rank", "bidding", "medium", "observed", name,
                          "Most missed auctions are due to rank (bid x quality), not budget.",
                          [c.ev(f"campaign='{name}'", "Average Search lost IS (rank)", {"lost_is_rank": lir, "impressions": a["impressions"]})],
                          score(freshness=c.fresh, days=c.days),
                          "Review ad relevance/landing page quality and bid targets before raising bids.")

    # CTR001: CTR outliers
    if c.needs("CTR001", ["impressions", "clicks"], "click-through outliers"):
        ctrs = {n: safe_div(a["clicks"], a["impressions"]) for n, a in agg.items() if a["impressions"] >= 1000}
        vals = [v for v in ctrs.values() if v is not None]
        if len(vals) >= 3:
            med = statistics.median(vals)
            for n, v in ctrs.items():
                if med and v is not None and v < 0.25 * med:
                    a = agg[n]
                    c.add("CTR001", f"'{n}' CTR {v * 100:.2f}% is under a quarter of the account median ({med * 100:.2f}%)", "creative", "low", "observed", n,
                          "Very low engagement relative to sibling campaigns; can reflect creative fatigue, poor targeting, or a placement mix (e.g. video/display) that is not comparable.",
                          [c.ev(f"campaign='{n}'", "clicks / impressions", {"impressions": a["impressions"], "clicks": a["clicks"], "ctr": v, "account_median_ctr": med})],
                          score(freshness=c.fresh, days=c.days, extra=[(0.8, "CTR norms differ by campaign type and placement")]),
                          "Compare like-for-like campaign types before acting; refresh creative if types match.")

    # FREQ001: frequency (social)
    if "frequency" in c.cols:
        c.ran.append("FREQ001")
        for n, a in agg.items():
            fq = _mean(a["frequency"])
            if fq and fq >= 5 and a["spend"] > 0:
                c.add("FREQ001", f"'{n}' average frequency {fq:.1f}", "creative", "medium", "observed", n,
                      "High frequency over the reported window suggests audience saturation and creative fatigue risk.",
                      [c.ev(f"campaign='{n}'", "Average frequency across rows", {"frequency": fq, "spend": a["spend"]})],
                      score(freshness=c.fresh, days=c.days, extra=[(0.85, "frequency was averaged across rows, not de-duplicated reach")]),
                      "Broaden the audience or rotate in new creative; watch CPA trend alongside frequency.")

    # BUD002: spend concentration
    if "spend" in c.cols and tot["spend"] > 0 and len(agg) >= 3:
        c.ran.append("BUD002")
        top_name, top = max(agg.items(), key=lambda kv: kv[1]["spend"])
        share = top["spend"] / tot["spend"]
        if share >= 0.6:
            c.add("BUD002", f"'{top_name}' takes {round(share * 100)}% of spend", "structure", "info", "observed", top_name,
                  "Heavy concentration is fine if intentional (e.g. a PMax/Advantage+ core) but makes the account sensitive to one campaign's performance.",
                  [c.ev(f"campaign='{top_name}'", "Spend share", {"spend": top["spend"], "total_spend": tot["spend"], "share": share})],
                  score(freshness=c.fresh, days=c.days))


def _tracking_break(c):
    by_day = defaultdict(lambda: {"spend": 0.0, "conversions": 0.0})
    for r in c.rows:
        if r.get("date"):
            by_day[r["date"]]["spend"] += r.get("spend") or 0
            by_day[r["date"]]["conversions"] += r.get("conversions") or 0
    days = sorted(by_day)
    if len(days) < 10:
        return
    streak = 0
    for d in reversed(days):
        if by_day[d]["conversions"] == 0 and by_day[d]["spend"] > 0:
            streak += 1
        else:
            break
    prior = [by_day[d]["conversions"] for d in days[:-streak or None]][-14:]
    prior_avg = _mean(prior) or 0
    if streak >= 2 and prior_avg >= 1:
        spend = sum(by_day[d]["spend"] for d in days[-streak:])
        c.add("TRK003", f"Conversions dropped to zero for the last {streak} days while spend continued", "tracking", "critical", "observed", "account",
              "A sudden stop after steady conversions usually means a tag, pixel, CAPI or import broke, or reporting lag on the most recent days.",
              [c.ev(f"dates {days[-streak]}..{days[-1]}", "Daily totals", {"days_zero": streak, "spend_in_window": spend, "prior_14d_avg_conversions": prior_avg})],
              score(freshness=c.fresh, extra=[(0.85, "conversion lag can explain 1–3 day gaps")] if streak < 4 else None),
              "Check tag diagnostics / Events Manager / offline import status today; compare with backend orders for the same days.")


def _search_terms(c):
    if not c.needs("ST001", ["search_term", "spend", "conversions"], "wasted search terms"):
        return
    agg = _agg(c.rows, "search_term")
    tot_spend = sum(a["spend"] for a in agg.values())
    tot_conv = sum(a["conversions"] for a in agg.values())
    acct_cpa = c.targets.get("cpa") or safe_div(tot_spend, tot_conv)
    if not acct_cpa:
        c.gaps.append({"what": "No conversions and no CPA target in search terms export", "impact": "ST001 cannot set a waste threshold", "severity": "major"})
        return
    waste = [(t, a) for t, a in agg.items() if a["conversions"] == 0 and a["spend"] >= acct_cpa]
    waste.sort(key=lambda x: -x[1]["spend"])
    if waste:
        wspend = sum(a["spend"] for _, a in waste)
        top = waste[:15]
        c.add("ST001", f"{len(waste)} search terms spent ≥ 1 CPA ({fnum(acct_cpa)}) with no conversions", "search_terms", "high" if wspend > 0.1 * tot_spend else "medium", "observed",
              "search terms", f"Together they cost {fnum(wspend)} {c.cur} ({round(wspend / tot_spend * 100) if tot_spend else 0}% of search term spend). Top terms listed in evidence.",
              [c.ev(f"search_term='{t}'", "No conversions", {"spend": a["spend"], "clicks": a["clicks"]}) for t, a in top],
              score(freshness=c.fresh, days=c.days, extra=[(0.85, "terms can still assist conversions; review intent before adding negatives")]),
              "Review intent; add irrelevant terms as negatives (phrase/exact) via an `optimize` changeset.",
              {"metric": "search_term_waste", "low": round(wspend * 0.4, 2), "high": round(wspend, 2), "unit": c.cur, "method": "Spend on non-converting terms; low end assumes 60% are relevant and kept"})
