"""Profiles: named settings of the capability catalog, edited in the web app.

The catalog (assessment/capabilities.md) lists every capability with its standard priority. A profile
(assessment/profiles/<id>.json) stores only what differs from it:

    {
      "name": "Prototype",
      "description": "...",
      "capabilities": {"arch.adr": {"enabled": false}, "test.coverage": {"priority": "nice"},
                       "doc.readme": {"params": {"target_words": 200}}},
      "custom": [{"aspect": "security", "text": "Keys are rotated quarterly.", "priority": "important",
                  "met_when": "The runbook shows a rotation in the last 90 days."}]
    }

Thresholds (`params`) are read by the scanner rules, so they apply at the next scan. Priorities, switched-off
capabilities and your own capabilities are re-applied to an existing run without re-scanning.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .checklist import CATALOG, PRIORITIES, PRIORITY_WEIGHT, REPO_CHECKLIST, _slug, parse

PROFILES = CATALOG.parent / "profiles"
STANDARD = "standard"
PROFILE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
MAX_TEXT = 300
MAX_MET_WHEN = 1000


@dataclass(frozen=True)
class Param:
    key: str
    label: str
    default: float
    unit: str
    min: float
    max: float
    step: float = 1


# Thresholds a profile may change. Each one IS the acceptance threshold quoted in the capability's "Accepted when"
# sentence ("There are at least {min_files} test files"). Rules read them via Repo.param(); texts quote them as {key},
# and {key:partial} for the level where "Partially met" starts.
PARAMS: dict[str, list[Param]] = {
    "arch.diagrams": [Param("min_diagrams", "Diagrams kept as code", 2, "diagrams", 1, 50)],
    "arch.adr": [Param("min_records", "Recorded design decisions", 3, "records", 1, 100)],
    "arch.structure": [Param("max_root_files", "Source files allowed in the root", 5, "files", 0, 200)],
    "arch.boundaries": [Param("min_source_files", "Checked for projects with more source files than", 50, "files", 0, 100000)],
    "arch.fresh": [Param("max_lag_days", "Architecture document may lag the code by", 80, "days", 1, 3650)],
    "doc.readme": [Param("min_words", "README length", 340, "words", 20, 10000, 10)],
    "doc.docs_dir": [Param("min_pages", "Pages in the docs folder", 3, "pages", 1, 500)],
    "doc.freshness": [Param("max_lag_days", "Docs may lag the code by", 80, "days", 1, 3650)],
    "doc.inline": [Param("min_share", "Documented Python functions and classes", 51, "%", 1, 100)],
    "test.present": [Param("min_files", "Test files", 5, "files", 1, 10000)],
    "test.ratio": [Param("min_ratio", "Test files per source file", 0.34, "", 0.01, 5, 0.01)],
    "hyg.file_size": [Param("max_kb", "Largest acceptable source file", 60, "KB", 1, 10000)],
    "rev.via_pr": [Param("min_share", "Commits on the main line that came through a pull request", 60, "%", 1, 100)],
    "rev.small_changes": [Param("max_files", "Files a typical change touches", 10, "files", 1, 1000)],
}


def defaults() -> dict[str, dict[str, float]]:
    return {cid: {p.key: p.default for p in ps} for cid, ps in PARAMS.items()}


def derived(params: dict[str, float]) -> dict[str, float]:
    """Values the detailed texts need that follow from the thresholds (freshness: full score and partial limits)."""
    out = dict(params)
    if "max_lag_days" in params:
        m = params["max_lag_days"]
        out["grace_days"] = round(m * 30 / 80)
        out["partial_days"] = round(m * 248 / 80)
        out["zero_days"] = round(m * 365 / 80)
    return out


PLACEHOLDER_RE = re.compile(r"\{(\w+)(?:([*+])([\d.]+)|:(partial))?\}")


def fill(text: str, params: dict[str, float]) -> str:
    """Replace {key}, {key*3}, {key+1} and {key:partial} with numbers. Counts are rounded up."""
    if not params or "{" not in text:
        return text
    values = derived(params)

    def sub(m: re.Match) -> str:
        key, op, arg = m.group(1), m.group(2), m.group(3)
        if key not in values:
            return m.group(0)
        v = float(values[key])
        if m.group(4):  # where Partially met starts: score 0.35 on the reach() scale
            v = v * 0.35 / 0.85
        elif op:
            v = v * float(arg) if op == "*" else v + float(arg)
        whole = float(values[key]).is_integer()
        return str(math.ceil(v - 1e-9)) if whole else f"{v:.2f}".rstrip("0").rstrip(".")

    return PLACEHOLDER_RE.sub(sub, text)


# ---------- profiles on disk ----------


def _path(pid: str) -> Path:
    if not PROFILE_ID_RE.match(pid or ""):
        raise ValueError(f"Bad profile id: {pid!r} (lowercase letters, digits and dashes)")
    return PROFILES / f"{pid}.json"


def load(pid: str = STANDARD) -> dict:
    p = _path(pid)
    if not p.is_file():
        raise ValueError(f"No such profile: {pid}")
    data = json.loads(p.read_text(encoding="utf-8"))
    return dict(validate(data), id=pid, builtin=pid == STANDARD)


def list_profiles() -> list[dict]:
    out = []
    for f in sorted(PROFILES.glob("*.json")):
        try:
            prof = load(f.stem)
        except (ValueError, OSError):
            continue
        out.append({"id": f.stem, "name": prof["name"], "description": prof["description"], "builtin": prof["builtin"]})
    return sorted(out, key=lambda p: (not p["builtin"], p["name"].lower()))


def save(pid: str, data: dict) -> dict:
    if pid == STANDARD:
        raise ValueError("The Standard profile is the published baseline and cannot be changed. Save a copy under a new name.")
    clean = validate(data)
    p = _path(pid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(clean, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return load(pid)


def delete(pid: str) -> None:
    if pid == STANDARD:
        raise ValueError("The Standard profile cannot be deleted.")
    p = _path(pid)
    if p.is_file():
        p.unlink()


def validate(data: dict) -> dict:
    """Keep only known capabilities, valid priorities and in-range numbers; raise on anything malformed."""
    if not isinstance(data, dict):
        raise ValueError("A profile is a JSON object")
    catalog = parse(CATALOG.read_text(encoding="utf-8"))
    known = {i["id"] for its in catalog.values() for i in its if not i["custom"]}
    name = str(data.get("name", "")).strip()[:60]
    if not name:
        raise ValueError("A profile needs a name")
    caps: dict[str, dict] = {}
    for cid, ov in (data.get("capabilities") or {}).items():
        if cid not in known or not isinstance(ov, dict):
            continue
        c: dict = {}
        if ov.get("enabled") is False:
            c["enabled"] = False
        if ov.get("priority") in PRIORITIES:
            c["priority"] = ov["priority"]
        spec = {p.key: p for p in PARAMS.get(cid, [])}
        vals = {}
        for k, v in (ov.get("params") or {}).items():
            if k in spec:
                try:
                    x = float(v)
                except (TypeError, ValueError):
                    raise ValueError(f"{cid}: {spec[k].label} must be a number") from None
                if not spec[k].min <= x <= spec[k].max:
                    raise ValueError(f"{cid}: {spec[k].label} must be between {spec[k].min:g} and {spec[k].max:g}")
                if x != spec[k].default:
                    vals[k] = int(x) if x.is_integer() and float(spec[k].default).is_integer() else x
        if vals:
            c["params"] = vals
        if c:
            caps[cid] = c
    custom = []
    for it in data.get("custom") or []:
        if not isinstance(it, dict):
            continue
        aspect, text = str(it.get("aspect", "")), str(it.get("text", "")).strip()
        if aspect not in catalog:
            raise ValueError(f"Unknown aspect for your own capability: {aspect!r}")
        if not text or len(text) > MAX_TEXT:
            raise ValueError(f"Your own capability needs a text of 1-{MAX_TEXT} characters")
        custom.append(
            {
                "aspect": aspect,
                "text": text,
                "priority": it.get("priority") if it.get("priority") in PRIORITIES else "important",
                "met_when": str(it.get("met_when", "")).strip()[:MAX_MET_WHEN],
            }
        )
    return {"name": name, "description": str(data.get("description", "")).strip()[:300], "capabilities": caps, "custom": custom}


# ---------- profile -> effective checklist ----------


def checklist(pid: str = STANDARD) -> dict:
    """The capability list a scan uses: catalog + profile overrides, with every threshold in force."""
    prof = load(pid)
    items = parse(CATALOG.read_text(encoding="utf-8"))
    out: dict[str, list[dict]] = {}
    for aspect, its in items.items():
        out[aspect] = []
        for it in its:
            ov = prof["capabilities"].get(it["id"], {})
            if ov.get("enabled") is False:
                continue
            prio = ov.get("priority", it["priority"])
            out[aspect].append(dict(it, priority=prio, weight=PRIORITY_WEIGHT[prio]))
    for c in prof["custom"]:
        out.setdefault(c["aspect"], []).append(
            {
                "id": f"custom.{c['aspect']}.{_slug(c['text'])}",
                "text": c["text"],
                "priority": c["priority"],
                "weight": PRIORITY_WEIGHT[c["priority"]],
                "custom": True,
                "met_when": c["met_when"],
            }
        )
    params = defaults()
    for cid, ov in prof["capabilities"].items():
        if cid in params:
            params[cid].update(ov.get("params", {}))
    return {"origin": "profile", "profile": {"id": pid, "name": prof["name"]}, "path": str(_path(pid)), "items": out, "params": params}


def catalog_for_ui() -> dict:
    """Everything the settings tab shows: aspects, capabilities with their standard priority, thresholds."""
    items = parse(CATALOG.read_text(encoding="utf-8"))
    return {
        "aspects": {a: [{"id": i["id"], "text": i["text"], "priority": i["priority"]} for i in its if not i["custom"]] for a, its in items.items()},
        "params": {cid: [asdict(p) for p in ps] for cid, ps in PARAMS.items()},
    }


def resolve(repo_root: Path | None = None, explicit: str | Path | None = None, profile: str | None = None) -> dict:
    """Pick what to assess against: an explicit file > a chosen profile > the repo's .sdlc360/capabilities.md > Standard."""
    if explicit and Path(explicit).is_file():
        return {"origin": "explicit", "path": str(explicit), "items": parse(Path(explicit).read_text(encoding="utf-8")), "params": defaults()}
    if profile:
        return checklist(profile)
    for rel in REPO_CHECKLIST if repo_root else ():
        f = Path(repo_root) / rel  # type: ignore[arg-type]
        if f.is_file():
            return {"origin": "repository", "path": str(f), "items": parse(f.read_text(encoding="utf-8")), "params": defaults()}
    return checklist(STANDARD)
