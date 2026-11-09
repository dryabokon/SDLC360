"""Calibration: assess the reference set with the Standard criteria and record what the rules said.

The reference set is a list of well-run repositories (assessment/calibration/reference-set.json, read-only) plus the
ones a user adds in the app (assessment/calibration/custom.json). Each GitHub repository is pinned to a commit
(assessment/calibration/pins.json): a calibration assesses the same commits until they are moved on on purpose, so
two calibrations differ only where the rules changed. A local folder is read as it is and cannot be pinned.

A calibration writes one snapshot to runs/calibrations/<id>.json: every verdict of every check on every repository,
with the commit it was made on and the version of the scanner that made it. Comparing two snapshots shows what a
change to the rules did: a verdict that changed on the same commit was changed by the scanner, not by the project.

Calibration judges nothing itself. It records verdicts and counts them.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from .checklist import CATALOG
from .profiles import STANDARD
from .repo import check_target
from .runner import DEFAULT_CACHE, DEFAULT_RUNS, run_scan, self_version

CAL_DIR = CATALOG.parent / "calibration"
DEFAULT_SET = CAL_DIR / "reference-set.json"
CUSTOM_SET = CAL_DIR / "custom.json"
PINS = CAL_DIR / "pins.json"
KINDS = {"agentic": "Agentic project", "library": "Library", "template": "Template", "application": "Application"}
SNAPSHOT_ID_RE = re.compile(r"^\d{8}-\d{6}$")
MAX_WHY = 200
ASSESSED = ("pass", "partial", "fail")  # n/a and awaiting review are not verdicts on the practice


def _key(target: str) -> str:
    """One spelling per repository: owner/repo for GitHub, the resolved path for a local folder."""
    t = target.strip().strip('"')
    p = Path(t).expanduser()
    if p.exists():
        return str(p.resolve()).lower()
    return re.sub(r"^(https?://)?(www\.)?github\.com/", "", t).removesuffix(".git").strip("/").lower()


def _is_local(target: str) -> bool:
    return Path(target.strip().strip('"')).expanduser().exists()


def _read(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [r for r in data.get("repos", []) if isinstance(r, dict) and r.get("target")]


def reference_set(default: Path | None = None, custom: Path | None = None) -> list[dict]:
    """The default repositories first, then the user's own; each with `builtin` and its pinned commit."""
    out, seen, pins = [], set(), load_pins()
    for builtin, path in ((True, default or DEFAULT_SET), (False, custom or CUSTOM_SET)):
        for r in _read(path):
            k = _key(r["target"])
            if k in seen:
                continue
            seen.add(k)
            kind = r.get("kind") if r.get("kind") in KINDS else "application"
            out.append({"target": r["target"], "kind": kind, "why": str(r.get("why", "")), "builtin": builtin, "pin": pins.get(k)})
    return out


def load_pins(path: Path | None = None) -> dict[str, str]:
    f = path or PINS
    if not f.is_file():
        return {}
    return {str(k): str(v) for k, v in json.loads(f.read_text(encoding="utf-8")).get("pins", {}).items()}


def save_pins(pins: dict[str, str], path: Path | None = None) -> None:
    f = path or PINS
    f.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "description": "The commit each reference repository is assessed at. Moved on only by a calibration at the latest commits.",
        "pins": dict(sorted(pins.items())),
    }
    f.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def _write_custom(repos: list[dict], custom: Path) -> None:
    custom.parent.mkdir(parents=True, exist_ok=True)
    body = {"description": "Repositories added to the reference set in the app.", "repos": repos}
    custom.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def add_custom(target: str, kind: str = "application", why: str = "", default: Path | None = None, custom: Path | None = None) -> dict:
    custom = custom or CUSTOM_SET
    info = check_target(target)  # raises ValueError with a message for the user
    if kind not in KINDS:
        raise ValueError(f"Unknown kind: {kind}")
    target = info["display"] if info["kind"] == "github" else str(Path(target.strip().strip('"')).expanduser().resolve())
    if any(_key(r["target"]) == _key(target) for r in reference_set(default, custom)):
        raise ValueError(f"{target} is already in the reference set.")
    repos = _read(custom) + [{"target": target, "kind": kind, "why": why.strip()[:MAX_WHY]}]
    _write_custom(repos, custom)
    return {"target": target, "kind": kind, "why": why.strip()[:MAX_WHY], "builtin": False}


def remove_custom(target: str, custom: Path | None = None) -> None:
    custom = custom or CUSTOM_SET
    repos = _read(custom)
    keep = [r for r in repos if _key(r["target"]) != _key(target)]
    if len(keep) == len(repos):
        raise ValueError(f"{target} is not one of your reference repositories.")
    _write_custom(keep, custom)


def _entry(ref: dict, run_dir: Path) -> dict:
    """What a snapshot keeps of one run: the commit, the scores and every verdict."""
    rep = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    head = rep["repo"].get("head") or {}
    verdicts, checks = {}, {}
    for d in rep["dimensions"]:
        for c in d["checks"]:
            verdicts[c["id"]] = c["status"]
            checks[c["id"]] = {"title": c.get("title", ""), "aspect": d["id"], "aspect_name": d["name"], "priority": c.get("priority")}
    return {
        **ref,
        "status": "ok",
        "run_id": run_dir.name,
        "source": rep["repo"]["source"],
        "commit": head.get("sha"),
        "commit_date": head.get("date"),
        "score": rep["overall"]["score"],
        "grade": rep["overall"]["grade"],
        "dims": {d["id"]: d["score"] for d in rep["dimensions"]},
        "verdicts": verdicts,
        "_checks": checks,
    }


def run_calibration(
    repos: list[dict] | None = None,
    *,
    latest: bool = False,
    runs_dir: Path = DEFAULT_RUNS,
    cache_dir: Path = DEFAULT_CACHE,
    pins_path: Path | None = None,
    progress: Callable[[int, str, str], None] | None = None,
    scan: Callable[..., Path] = run_scan,
) -> Path:
    """Assess each repository with the Standard criteria at its pinned commit (or the latest, which moves the pin).

    A repository without a pin is assessed at its latest commit and pinned there. One that fails is recorded and the
    others go on.
    """
    say = progress or (lambda i, status, msg: None)
    repos = reference_set() if repos is None else repos
    pins = load_pins(pins_path)
    started = datetime.now(UTC)
    out_dir = Path(runs_dir) / "calibrations"
    out_dir.mkdir(parents=True, exist_ok=True)
    entries, checks = [], {}
    for i, ref in enumerate(repos):
        say(i, "running", "")
        base = {k: ref[k] for k in ("target", "kind", "why", "builtin") if k in ref}
        key, local = _key(ref["target"]), _is_local(ref["target"])
        pin = None if latest or local else pins.get(key)
        try:
            run_dir = scan(
                ref["target"],
                ref=pin,
                history_points=0,
                refresh=pin is None,
                profile=STANDARD,
                runs_dir=runs_dir,
                cache_dir=cache_dir,
                progress=lambda m, i=i: say(i, "running", m),
            )
            e = _entry(base, run_dir)
            checks.update(e.pop("_checks"))
            e["pinned"] = not local
            entries.append(e)
            if not local and e.get("commit"):
                pins[key] = e["commit"]
            say(i, "done", "")
        except Exception as ex:  # an unreachable repository must not sink the calibration
            entries.append({**base, "status": "failed", "error": f"{type(ex).__name__}: {ex}"})
            say(i, "failed", str(ex))
    save_pins(pins, pins_path)
    snap = {
        "schema": "sdlc360/calibration@1",
        "id": started.strftime("%Y%m%d-%H%M%S"),
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "profile": STANDARD,
        "latest": latest,
        "tool": self_version(),
        "repos": entries,
        "checks": checks,
    }
    path = out_dir / f"{snap['id']}.json"
    path.write_text(json.dumps(snap, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def list_snapshots(runs_dir: Path = DEFAULT_RUNS) -> list[dict]:
    out = []
    for f in sorted((Path(runs_dir) / "calibrations").glob("*.json"), reverse=True):
        try:
            s = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        ok = [r for r in s.get("repos", []) if r.get("status") == "ok"]
        out.append({"id": s["id"], "started_at": s["started_at"], "repos": len(s.get("repos", [])), "ok": len(ok), "tool": s.get("tool", {})})
    return out


def load_snapshot(sid: str, runs_dir: Path = DEFAULT_RUNS) -> dict:
    if not SNAPSHOT_ID_RE.match(sid):
        raise ValueError("bad calibration id")
    f = Path(runs_dir) / "calibrations" / f"{sid}.json"
    if not f.is_file():
        raise ValueError("calibration not found")
    return json.loads(f.read_text(encoding="utf-8"))


def _previous(sid: str, runs_dir: Path) -> dict | None:
    older = [s["id"] for s in list_snapshots(runs_dir) if s["id"] < sid]
    return load_snapshot(older[0], runs_dir) if older else None


def summarize(snap: dict, prev: dict | None) -> dict:
    """What the calibration produced, in numbers the app shows as they are."""
    ok = [r for r in snap["repos"] if r["status"] == "ok"]
    checks = []
    for order, (cid, meta) in enumerate(snap.get("checks", {}).items()):  # catalog order of the first report
        counts = {s: 0 for s in (*ASSESSED, "na", "review")}
        for r in ok:
            st = r["verdicts"].get(cid)
            if st in counts:
                counts[st] += 1
        assessed = sum(counts[s] for s in ASSESSED)
        checks.append(
            {
                "id": cid,
                "order": order,
                **meta,
                "counts": counts,
                "assessed": assessed,
                "met_share": round(counts["pass"] / assessed, 3) if assessed else None,
                "verdicts": [{"target": r["target"], "run_id": r["run_id"], "status": r["verdicts"].get(cid, "na")} for r in ok],
            }
        )
    checks.sort(key=lambda c: (c["met_share"] is None, c["met_share"] if c["met_share"] is not None else 0, c["aspect"], c["id"]))
    by_target = {_key(r["target"]): r for r in (prev or {}).get("repos", []) if r.get("status") == "ok"}
    repos, changes = [], []
    for r in snap["repos"]:
        p = by_target.get(_key(r["target"]))
        row = {
            k: r.get(k)
            for k in ("target", "kind", "why", "builtin", "status", "error", "run_id", "source", "commit", "commit_date", "score", "grade", "dims")
        }
        row["previous"] = {"score": p["score"], "commit": p.get("commit")} if p else None
        row["same_commit"] = bool(p and r.get("commit") and p.get("commit") == r.get("commit"))
        repos.append(row)
        if r["status"] != "ok" or not p:
            continue
        for cid in sorted(set(r["verdicts"]) | set(p["verdicts"])):
            before, after = p["verdicts"].get(cid), r["verdicts"].get(cid)
            if before != after:
                meta = snap.get("checks", {}).get(cid) or (prev or {}).get("checks", {}).get(cid) or {}
                changes.append(
                    {
                        "target": r["target"],
                        "run_id": r["run_id"],
                        "id": cid,
                        "title": meta.get("title", ""),
                        "aspect": meta.get("aspect"),
                        "before": before,
                        "after": after,
                        "cause": "scanner" if row["same_commit"] else "project",
                    }
                )
    verdicts = sum(c["assessed"] for c in checks)
    return {
        "id": snap["id"],
        "started_at": snap["started_at"],
        "finished_at": snap["finished_at"],
        "profile": snap.get("profile", STANDARD),
        "tool": snap.get("tool", {}),
        "repos": repos,
        "checks": checks,
        "totals": {
            "repos": len(snap["repos"]),
            "ok": len(ok),
            "failed": len(snap["repos"]) - len(ok),
            "checks": len(checks),
            "verdicts": verdicts,
            "met": sum(c["counts"]["pass"] for c in checks),
            "partial": sum(c["counts"]["partial"] for c in checks),
            "not_met": sum(c["counts"]["fail"] for c in checks),
            "never_met": sum(1 for c in checks if c["assessed"] and not c["counts"]["pass"]),
            "always_met": sum(1 for c in checks if c["assessed"] and c["counts"]["pass"] == c["assessed"]),
        },
        "previous": None
        if not prev
        else {
            "id": prev["id"],
            "started_at": prev["started_at"],
            "tool": prev.get("tool", {}),
            "changes": changes,
            "by_scanner": sum(1 for c in changes if c["cause"] == "scanner"),
            "by_project": sum(1 for c in changes if c["cause"] == "project"),
            "added": [r["target"] for r in snap["repos"] if r["status"] == "ok" and _key(r["target"]) not in by_target],
        },
    }


def result(sid: str | None = None, runs_dir: Path = DEFAULT_RUNS) -> dict | None:
    """The summary of one calibration (the latest when no id), compared with the one before it."""
    if sid is None:
        snaps = list_snapshots(runs_dir)
        if not snaps:
            return None
        sid = snaps[0]["id"]
    snap = load_snapshot(sid, runs_dir)
    return summarize(snap, _previous(sid, runs_dir))
