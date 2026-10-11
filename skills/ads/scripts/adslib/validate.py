"""JSON Schema validation. Uses `jsonschema` if installed; otherwise a built-in validator that
covers the keywords our schemas use (type, enum, const, required, properties,
additionalProperties:false, items, minItems, minimum, maximum, pattern, $ref to #/$defs)."""
import re
from pathlib import Path

from .util import read_json

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"
TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def load_schema(name):
    return read_json(SCHEMA_DIR / f"{name}.schema.json")


def _is_type(v, t):
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    return isinstance(v, TYPES[t])


def _check(v, s, root, path, errs):
    if "$ref" in s:
        ref = s["$ref"].split("/")[-1]
        s = root["$defs"][ref]
    if "const" in s and v != s["const"]:
        errs.append(f"{path}: must equal {s['const']!r}")
    if "enum" in s and v not in s["enum"]:
        errs.append(f"{path}: {v!r} not in {s['enum']}")
    if "type" in s:
        ts = s["type"] if isinstance(s["type"], list) else [s["type"]]
        if not any(_is_type(v, t) for t in ts):
            errs.append(f"{path}: expected {'/'.join(ts)}, got {type(v).__name__}")
            return
    if isinstance(v, dict):
        for k in s.get("required", []):
            if k not in v:
                errs.append(f"{path}: missing required '{k}'")
        props = s.get("properties", {})
        for k, sub in props.items():
            if k in v:
                _check(v[k], sub, root, f"{path}.{k}", errs)
        if s.get("additionalProperties") is False:
            for k in v:
                if k not in props:
                    errs.append(f"{path}: unexpected property '{k}'")
    if isinstance(v, list):
        if "minItems" in s and len(v) < s["minItems"]:
            errs.append(f"{path}: needs at least {s['minItems']} item(s)")
        if "items" in s:
            for i, item in enumerate(v):
                _check(item, s["items"], root, f"{path}[{i}]", errs)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if "minimum" in s and v < s["minimum"]:
            errs.append(f"{path}: {v} < minimum {s['minimum']}")
        if "maximum" in s and v > s["maximum"]:
            errs.append(f"{path}: {v} > maximum {s['maximum']}")
    if isinstance(v, str) and "pattern" in s and not re.search(s["pattern"], v):
        errs.append(f"{path}: {v!r} does not match {s['pattern']}")


def validate(obj, name):
    schema = load_schema(name)
    try:
        import jsonschema  # optional, stricter
        v = jsonschema.Draft202012Validator(schema)
        return [f"{'.'.join(str(p) for p in e.absolute_path) or '$'}: {e.message}" for e in v.iter_errors(obj)]
    except ImportError:
        errs = []
        _check(obj, schema, schema, "$", errs)
        return errs


def semantic_checks_run(run):
    """Rules a schema cannot express."""
    errs = []
    src_ids = {s["id"] for s in run.get("sources", {}).get("data", [])}
    ids = set()
    for f in run.get("findings", []):
        if f.get("id") in ids:
            errs.append(f"finding {f.get('id')}: duplicate id")
        ids.add(f.get("id"))
        for e in f.get("evidence", []):
            if e.get("source_id") not in src_ids and not str(e.get("source_id", "")).startswith(("doc:", "run:")):
                errs.append(f"finding {f.get('id')}: evidence cites unknown source '{e.get('source_id')}' (use a data source id, 'doc:<url>' or 'run:<run_id>')")
        if f.get("kind") == "estimated" and not (f.get("impact", {}).get("method") or f.get("description")):
            errs.append(f"finding {f.get('id')}: estimated finding must explain its method")
    for x in run.get("experiments", []):
        for fid in x.get("based_on_findings", []):
            if fid not in ids:
                errs.append(f"experiment {x.get('id')}: references unknown finding {fid}")
    if run.get("status") == "complete" and (run.get("errors") or any(g.get("severity") == "blocking" for g in run.get("data_gaps", []))):
        errs.append("status is 'complete' but there are errors or blocking gaps; must be 'partial'")
    return errs
