import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path


def now_utc():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(ts):
    return ts.isoformat().replace("+00:00", "Z")


def today():
    override = os.environ.get("ADS_TODAY")  # for tests / reproducible reruns
    return dt.date.fromisoformat(override) if override else dt.date.today()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_obj(obj):
    return sha256_bytes(canonical(obj).encode("utf-8"))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def slug(s, maxlen=24):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "client").lower()).strip("-")
    return (s or "client")[:maxlen].strip("-")


def read_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, default=str)
        f.write("\n")
    os.replace(tmp, p)


def fnum(x, digits=2):
    if x is None:
        return "—"
    if isinstance(x, (int, float)):
        if abs(x) >= 1000:
            return f"{x:,.0f}"
        return f"{x:,.{digits}f}".rstrip("0").rstrip(".") if isinstance(x, float) else f"{x:,}"
    return str(x)


def safe_div(a, b):
    try:
        return a / b if b else None
    except TypeError:
        return None
