"""Confidence scoring. Transparent multiplicative model; every penalty is listed as a reason."""


def level_for(score):
    return "high" if score >= 0.75 else "medium" if score >= 0.5 else "low"


def score(base=0.9, completeness=1.0, conversions=None, clicks=None, freshness="fresh",
          days=None, extra=None, cap=None):
    s, reasons = base, []
    if completeness < 1.0:
        s *= 0.6 + 0.4 * completeness
        reasons.append(f"{round((1 - completeness) * 100)}% of the columns this check needs are missing")
    if conversions is not None:
        if conversions < 5:
            s *= 0.6
            reasons.append(f"very small conversion sample ({conversions:g})")
        elif conversions < 20:
            s *= 0.8
            reasons.append(f"small conversion sample ({conversions:g})")
        elif conversions < 50:
            s *= 0.92
            reasons.append(f"moderate conversion sample ({conversions:g})")
    if clicks is not None and clicks < 100:
        s *= 0.8
        reasons.append(f"few clicks ({clicks:g})")
    fresh_mult = {"fresh": 1.0, "aging": 0.9, "stale": 0.75, "unknown": 0.85}
    s *= fresh_mult.get(freshness, 0.85)
    if freshness != "fresh":
        reasons.append(f"data freshness is {freshness}")
    if days is not None:
        if days < 7:
            s *= 0.7
            reasons.append(f"only {days} day(s) of data")
        elif days < 14:
            s *= 0.85
            reasons.append(f"short window ({days} days)")
    for mult, why in (extra or []):
        s *= mult
        reasons.append(why)
    if cap is not None and s > cap[0]:
        s = cap[0]
        reasons.append(cap[1])
    s = round(max(0.0, min(1.0, s)), 2)
    if not reasons:
        reasons.append("complete columns, adequate sample, fresh data")
    return {"level": level_for(s), "score": s, "reasons": reasons}


def cap_confidence(conf, max_score, why):
    if conf["score"] > max_score:
        conf = dict(conf)
        conf["score"] = max_score
        conf["level"] = level_for(max_score)
        conf["reasons"] = list(conf.get("reasons", [])) + [why]
    return conf
