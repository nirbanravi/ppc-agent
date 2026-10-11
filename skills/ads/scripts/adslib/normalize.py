"""Read platform exports (CSV/TSV/XLSX, UTF-8 or UTF-16) into canonical rows.

Canonical columns are platform-neutral. Anything we cannot map is kept under
row["extra"] so nothing is silently thrown away.
"""
import csv
import datetime as dt
import io
import re
from pathlib import Path

CANONICAL = [
    "date", "account_id", "account", "campaign_id", "campaign", "ad_group", "ad", "keyword",
    "search_term", "match_type", "status", "campaign_type", "budget", "spend", "impressions",
    "clicks", "conversions", "conv_value", "currency", "reach", "frequency", "video_views",
    "impr_share", "lost_is_budget", "lost_is_rank", "installs", "period_start", "period_end",
]

# Lower-cased header -> canonical. Ordered roughly by how specific the header is.
ALIASES = {
    "date": ["day", "date", "gregorian date", "time period", "start date (in utc)", "stat_time_day", "segments.date", "by day"],
    "period_start": ["reporting starts", "start date", "starts"],
    "period_end": ["reporting ends", "end date", "ends"],
    "account_id": ["customer id", "account id", "advertiser id", "account_id", "ad account id", "org id"],
    "account": ["account", "account name", "advertiser name", "ad account name"],
    "campaign_id": ["campaign id", "campaign_id", "campaign.id"],
    "campaign": ["campaign", "campaign name", "campaign_name", "campaign.name"],
    "ad_group": ["ad group", "ad set name", "ad set", "ad group name", "adgroup name", "ad squad name", "line item name", "ad_group"],
    "ad": ["ad", "ad name", "ad_name", "creative name"],
    "keyword": ["keyword", "search keyword", "keyword text"],
    "search_term": ["search term", "search query", "customer search term", "search terms"],
    "match_type": ["match type", "search keyword match type", "keyword match type"],
    "status": ["campaign status", "status", "campaign state", "campaign delivery", "delivery", "state"],
    "campaign_type": ["campaign type", "advertising channel type", "objective", "campaign objective"],
    "budget": ["budget", "daily budget", "campaign budget", "ad set budget", "campaign daily budget", "budget amount", "daily budget amount"],
    "spend": ["cost", "spend", "amount spent", "total spent", "amount spent (usd)", "amount spent (inr)", "spend (usd)", "cost (usd)", "total cost", "local_spend", "spent", "amount_spent", "metrics.cost"],
    "impressions": ["impressions", "impr.", "impr", "impressions (total)", "metrics.impressions"],
    "clicks": ["clicks", "link clicks", "clicks (all)", "clicks (destination)", "taps", "swipes", "outbound clicks", "metrics.clicks"],
    "conversions": ["conversions", "conv.", "results", "purchases", "conversions (all)", "website purchases", "7 day total orders (#)", "14 day total orders (#)", "installs (total)", "total conversions", "leads", "conversion", "metrics.conversions"],
    "conv_value": ["conv. value", "conversion value", "conversions value", "revenue", "purchases conversion value", "website purchases conversion value", "7 day total sales", "14 day total sales", "total conversion value", "metrics.conversions_value", "conv value"],
    "currency": ["currency", "currency code", "account currency"],
    "reach": ["reach"],
    "frequency": ["frequency", "avg. frequency"],
    "video_views": ["views", "video views", "thruplays", "2-second continuous video plays", "video plays"],
    "impr_share": ["search impr. share", "impr. share", "impression share", "search impression share"],
    "lost_is_budget": ["search lost is (budget)", "lost is (budget)", "impression share lost to budget", "search lost impr. share (budget)"],
    "lost_is_rank": ["search lost is (rank)", "lost is (rank)", "impression share lost to rank", "search lost impr. share (rank)"],
    "installs": ["installs", "tap-through installs", "app installs"],
}

# Signals used only for auto-detecting the platform. A file is assigned a platform
# only when at least one signal matches; otherwise the caller must pass --platform.
PLATFORM_SIGNALS = [
    ("amazon", ["7 day total sales", "14 day total sales", "7 day total orders (#)", "advertised asin"]),
    ("apple", ["taps", "tap-through installs", "ttr", "cr (tap-through)"]),
    ("meta", ["amount spent", "ad set name", "reporting starts", "thruplays", "results"]),
    ("linkedin", ["total spent", "start date (in utc)", "campaign group name"]),
    ("snapchat", ["ad squad name", "swipes", "swipe up %"]),
    ("tiktok", ["clicks (destination)", "stat_time_day", "ad group name", "cost per result"]),
    ("google", ["impr.", "conv. value", "search impr. share", "customer id", "campaign.name"]),
    ("microsoft", ["conv.", "gregorian date", "revenue", "spend"]),
    ("reddit", ["ecpm", "ad group name", "post id"]),
    ("pinterest", ["pin id", "ad group name", "earned impressions", "pin clicks"]),
    ("x", ["promoted tweet", "post id", "engagements", "billed charge"]),
]

NULLS = {"", "--", "-", "—", " --", "n/a", "na", "null", "none", "< 10%", "<10%", "> 90%", ">90%"}
DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%Y%m%d", "%a, %b %d, %Y"]


class IngestError(Exception):
    pass


def _decode(raw):
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise IngestError("Could not decode file (tried UTF-16, UTF-8, CP1252, Latin-1)")


def read_table(path):
    """Return list of raw rows (list of strings)."""
    p = Path(path)
    ext = p.suffix.lower()
    if ext in (".xlsx", ".xlsm"):
        try:
            import openpyxl  # optional
        except ImportError as e:
            raise IngestError("XLSX needs openpyxl (pip install openpyxl) or export as CSV") from e
        wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
        ws = wb.worksheets[0]
        return [["" if c is None else str(c) for c in row] for row in ws.iter_rows(values_only=True)]
    if ext not in (".csv", ".tsv", ".txt"):
        raise IngestError(f"Unsupported file type {ext}; use CSV, TSV or XLSX")
    text = _decode(p.read_bytes())
    sample = text[:5000]
    delim = "\t" if sample.count("\t") > sample.count(",") else ","
    return list(csv.reader(io.StringIO(text), delimiter=delim))


def _norm_header(h):
    return re.sub(r"\s+", " ", (h or "").strip().strip('"').lower())


def _alias_lookup():
    table = {}
    for canon, names in ALIASES.items():
        for n in names:
            table.setdefault(n, canon)
    return table


ALIAS = _alias_lookup()


def _map_header(h):
    n = _norm_header(h)
    if n in ALIAS:
        return ALIAS[n]
    # "Amount spent (EUR)", "Cost (INR)" etc.
    base = re.sub(r"\s*\([a-z]{3}\)$", "", n)
    if base in ALIAS:
        return ALIAS[base]
    return None


def find_header(rows, max_scan=15):
    best, best_i = 0, None
    for i, row in enumerate(rows[:max_scan]):
        mapped = {_map_header(c) for c in row if _map_header(c)}
        score = len(mapped) + (2 if {"spend", "impressions"} & mapped else 0)
        if score > best and len(mapped) >= 2:
            best, best_i = score, i
    if best_i is None:
        raise IngestError("No recognisable header row in the first 15 lines (need at least two known columns such as Campaign, Cost, Impressions)")
    return best_i


def detect_platform(headers):
    hs = {_norm_header(h) for h in headers}
    scores = []
    for plat, signals in PLATFORM_SIGNALS:
        s = sum(1 for sig in signals if sig in hs)
        if s:
            scores.append((s, plat))
    if not scores:
        return None, 0
    scores.sort(reverse=True)
    top = scores[0]
    tie = len(scores) > 1 and scores[1][0] == top[0]
    return (None if tie else top[1]), top[0]


def parse_number(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s.lower() in NULLS:
        return None
    pct = s.endswith("%")
    s = re.sub(r"[^\d,.\-eE]", "", s)
    if s.count(",") and s.count("."):
        s = s.replace(",", "") if s.rfind(".") > s.rfind(",") else s.replace(".", "").replace(",", ".")
    elif s.count(",") == 1 and len(s.split(",")[1]) != 3:
        s = s.replace(",", ".")  # decimal comma
    else:
        s = s.replace(",", "")
    try:
        n = float(s)
    except ValueError:
        return None
    return n / 100 if pct else n


def parse_date(v):
    s = (v or "").strip()
    if not s or s.lower() in NULLS:
        return None
    s = s.split("T")[0].split(" - ")[0].strip()
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


PREAMBLE_RANGE = re.compile(r"([A-Z][a-z]+ \d{1,2}, \d{4})\s*[-–]\s*([A-Z][a-z]+ \d{1,2}, \d{4})")


def _preamble_range(lines):
    for row in lines:
        m = PREAMBLE_RANGE.search(" ".join(row))
        if m:
            a, b = parse_date(m.group(1)), parse_date(m.group(2))
            if a and b:
                return a, b
    return None


NUMERIC = {"budget", "spend", "impressions", "clicks", "conversions", "conv_value", "reach", "frequency",
           "video_views", "impr_share", "lost_is_budget", "lost_is_rank", "installs"}


def ingest_file(path, platform=None):
    rows = read_table(path)
    if not rows:
        raise IngestError("File is empty")
    hi = find_header(rows)
    headers = rows[hi]
    warnings = []
    detected, strength = detect_platform(headers)
    if platform and detected and detected != platform and strength >= 2:
        warnings.append(f"Columns look like {detected} but --platform {platform} was given; using {platform}")
    plat = platform or detected or "unknown"
    if plat == "unknown":
        warnings.append("Platform could not be detected from headers; pass --platform")

    colmap, unmapped = {}, []
    for idx, h in enumerate(headers):
        c = _map_header(h)
        if c and c not in colmap.values():
            colmap[idx] = c
        elif c:  # second column mapping to the same canonical (e.g. 'Results' and 'Purchases')
            unmapped.append(h)
        else:
            unmapped.append(h)

    pre = _preamble_range(rows[:hi])
    out, dropped_totals, bad_numbers = [], 0, 0
    for raw in rows[hi + 1:]:
        if not any(str(c).strip() for c in raw):
            continue
        first = str(raw[0]).strip().lower() if raw else ""
        if first.startswith("total") or first in ("totals", "grand total"):
            dropped_totals += 1
            continue
        r = {"extra": {}}
        for idx, cell in enumerate(raw):
            if idx >= len(headers):
                continue
            canon = colmap.get(idx)
            if canon is None:
                if str(cell).strip():
                    r["extra"][headers[idx]] = cell
                continue
            if canon in NUMERIC:
                n = parse_number(cell)
                if n is None and str(cell).strip() and str(cell).strip().lower() not in NULLS:
                    bad_numbers += 1
                r[canon] = n
            elif canon in ("date", "period_start", "period_end"):
                d = parse_date(cell)
                r[canon] = d.isoformat() if d else None
            else:
                r[canon] = str(cell).strip() or None
        # campaign-level rows with an all-blank campaign are usually totals
        if "campaign" in colmap.values() and not r.get("campaign") and not r.get("ad_group"):
            dropped_totals += 1
            continue
        out.append(r)

    if any(_norm_header(h) == "results" for h in headers):
        warnings.append("'Results' was mapped to conversions; Meta 'Results' follows each ad set's optimisation event, so rows may count different events. Prefer an explicit event column (e.g. Purchases, Leads)")
    if dropped_totals:
        warnings.append(f"Removed {dropped_totals} total/summary row(s) so they are not double counted")
    if bad_numbers:
        warnings.append(f"{bad_numbers} numeric cell(s) could not be parsed and were treated as missing")

    dates = sorted({r["date"] for r in out if r.get("date")})
    if dates:
        start, end, granularity = dates[0], dates[-1], "daily" if len(dates) > 1 else "single_day"
    else:
        ps = sorted({r["period_start"] for r in out if r.get("period_start")})
        pe = sorted({r["period_end"] for r in out if r.get("period_end")})
        if ps and pe:
            start, end = ps[0], pe[-1]
        elif pre:
            start, end = pre[0].isoformat(), pre[1].isoformat()
        else:
            start = end = None
        granularity = "aggregate"
        if start is None:
            warnings.append("No date column or date range found; time-based checks (pacing, freshness, trends) cannot run")

    currencies = sorted({r["currency"] for r in out if r.get("currency")})
    if not currencies:
        for h in headers:
            m = re.search(r"\(([A-Z]{3})\)", h or "")
            if m:
                currencies = [m.group(1)]
                break

    present = sorted(set(colmap.values()))
    return {
        "platform": plat,
        "rows": out,
        "header_row_index": hi,
        "columns_present": present,
        "columns_missing": [c for c in ("date", "campaign", "spend", "impressions", "clicks", "conversions", "conv_value", "budget") if c not in present],
        "unmapped_columns": unmapped,
        "date_range": {"start": start, "end": end, "granularity": granularity},
        "currencies": currencies,
        "warnings": warnings,
        "report_type": _report_type(present),
    }


def _report_type(present):
    if "search_term" in present:
        return "search_terms"
    if "keyword" in present:
        return "keywords"
    if "ad" in present:
        return "ads"
    if "ad_group" in present:
        return "ad_groups"
    if "campaign" in present:
        return "campaigns"
    return "unknown"
