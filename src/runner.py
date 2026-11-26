"""One scan = one run folder. Shared by the CLI and the local web server."""

from __future__ import annotations

import contextlib
import json
import logging
import re
import shutil
import sys
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from . import __version__, skill_review
from .dimensions._util import forge as forge_of
from .history import _force_remove, score_history, velocity
from .hosting import is_remote, short_name
from .profiles import STANDARD, defaults
from .profiles import checklist as profile_checklist
from .profiles import resolve as resolve_checklist
from .render import render_html
from .repo import STALE_FETCH_DAYS, WORKING_COPY, Repo, checkout_ref, default_ref, fetched_at, resolve_target, run_git
from .scanner import finalize, scan

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUNS = PROJECT_ROOT / "runs"
DEFAULT_CACHE = PROJECT_ROOT / ".cache" / "repos"
RUN_ID_RE = re.compile(r"^[\w.-]+$")
log = logging.getLogger("sdlc360")


def slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", short_name(s)).strip("-")[:60] or "repo"


def self_version() -> dict:
    try:
        sha = run_git(PROJECT_ROOT, "rev-parse", "HEAD").strip()
        dirty = bool(run_git(PROJECT_ROOT, "status", "--porcelain").strip())
        return {"version": __version__, "git_sha": sha, "dirty": dirty}
    except Exception:
        return {"version": __version__, "git_sha": None, "dirty": None}


def write_outputs(run_dir: Path, report: dict) -> Path:
    (run_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    html = run_dir / "report.html"
    html.write_text(render_html(report), encoding="utf-8")
    return html


def pick_ref(root: Path, source: str, ref: str | None, tmp: Path) -> tuple[Path, dict]:
    """What a scan reads, and the report's word on it. A local folder is assessed at its default branch as last fetched
    (or at `ref`), from a throw-away shared clone: its own files and .git are never touched. `working-copy`: as it is now."""
    if is_remote(source):  # our clone, already at `ref` or at the remote's default branch
        branch = run_git(root, "rev-parse", "--abbrev-ref", "HEAD", check=False).strip()
        return root, {"name": ref or branch, "kind": "given" if ref else "default", "why": "" if ref else "the remote's default branch"}
    current = run_git(root, "rev-parse", "--abbrev-ref", "HEAD", check=False).strip()
    if ref == WORKING_COPY:
        return root, {"name": current, "kind": WORKING_COPY, "why": "the working copy as it is now, uncommitted changes included"}
    name, why = (ref, "chosen") if ref else default_ref(root)
    if name is None:
        return root, {"name": current, "kind": WORKING_COPY, "why": why}
    checkout_ref(root, name, tmp / "repo")
    info: dict = {"name": name, "kind": "given" if ref else "default", "why": why, "working_copy_branch": current}
    when = fetched_at(root, name)
    if "/" in name and run_git(root, "rev-parse", "--verify", "--quiet", f"refs/remotes/{name}", check=False).strip():
        info["fetched_at"] = when.isoformat(timespec="seconds") if when else None
        age = (datetime.now(UTC) - when).days if when else None
        if age is None or age > STALE_FETCH_DAYS:
            info["stale"] = (
                f"as last fetched {age} days ago: git fetch in the folder brings the newest commits" if age is not None else "never fetched"
            )
    return tmp / "repo", info


def run_scan(
    target: str,
    *,
    ref: str | None = None,
    name: str | None = None,
    only: list[str] | None = None,
    history_points: int = 8,
    history_months: int = 12,
    refresh: bool = False,
    checklist: str | None = None,
    profile: str | None = None,
    forge: str | None = None,
    runs_dir: Path = DEFAULT_RUNS,
    cache_dir: Path = DEFAULT_CACHE,
    progress: Callable[[str], None] | None = None,
) -> Path:
    say = progress or (lambda m: None)
    started = datetime.now(UTC)
    say(f"resolving {target}")
    root, source = resolve_target(target, Path(cache_dir), ref, refresh)
    nm = name or slug(source.rsplit("/", 1)[-1] if is_remote(source) else Path(source).name)
    run_dir = Path(runs_dir) / f"{started.strftime('%Y%m%d-%H%M%S')}_{nm}"
    run_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(run_dir / "scan.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(fh)
    tmp = Path(tempfile.mkdtemp(prefix="sdlc360-ref-"))
    try:
        folder = root
        root, ref_info = pick_ref(root, source, ref, tmp)
        log.info("scanning %s at %s (%s; %s) -> %s", source, ref_info["name"], ref_info["why"] or ref_info["kind"], root, run_dir)
        say(f"scanning {ref_info['name']}")
        repo = Repo(root, source)
        repo.forge = forge
        cl = resolve_checklist(root, checklist, profile)
        log.info("capabilities: %s (%s)", cl["path"], (cl.get("profile") or {}).get("name", cl["origin"]))
        report = scan(repo, only=only, checklist=cl)
        report["repo"]["ref"] = ref_info
        report["repo"]["forge"] = forge_of(repo)
        if report["repo"].get("head") and ref_info["kind"] != WORKING_COPY:
            report["repo"]["head"]["branch"] = ref_info["name"]
        say("judging skills")
        report["skill_facts"] = skill_review.facts(repo)  # HEAD only: what the code and git say about each skill
        report = finalize(report)  # scan() finalized before the facts existed: the skill verdicts need them
        for d in report["dimensions"]:
            log.info("  %-24s %6s  %s", d["name"], d["score"], d["grade"])
        say("computing velocity")
        hist = {"velocity": velocity(repo), "scores": []}
        if history_points > 1 and repo.is_git:

            def scan_past(r: Repo) -> dict:
                r.forge = forge
                return scan(r, only=only, checklist=cl)

            pts = score_history(repo, scan_past, history_points, history_months, say)
            pts.append(
                {
                    "sha": repo.head.get("sha"),
                    "date": repo.head.get("date"),
                    "overall": report["overall"]["score"],
                    "dims": {d["id"]: d["score"] for d in report["dimensions"]},
                }
            )
            hist["scores"] = sorted(pts, key=lambda p: p["date"] or "")
        report["history"] = hist
        log.info("overall %s (%s)", report["overall"]["score"], report["overall"]["grade"])
        manifest = {
            "schema": "sdlc360/run-manifest@1",
            "run_id": run_dir.name,
            "status": "ok",
            "command": ["python", "sdlc.py", *sys.argv[1:]],
            "target": target,
            "ref": ref,
            "assessed_ref": ref_info,
            "resolved_path": str(folder),
            "source": source,
            "target_head": repo.head,
            "options": {
                "only": only,
                "history_points": history_points,
                "history_months": history_months,
                "checklist": cl["path"],
                "profile": (cl.get("profile") or {}).get("id"),
            },
            "tool": self_version(),
            "python": sys.version.split()[0],
            "started_at": started.isoformat(timespec="seconds"),
            "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "outputs": ["manifest.json", "report.json", "report.html", "scan.log"],
            "reproduce": f"python sdlc.py scan {target}"
            + (f" --ref {WORKING_COPY}" if ref_info["kind"] == WORKING_COPY else f" --ref {repo.head['sha']}" if repo.head.get("sha") else "")
            + (f" --profile {cl['profile']['id']}" if cl.get("profile") else ""),
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        write_outputs(run_dir, report)
        say("done")
        return run_dir
    except Exception as e:  # leave a trace instead of a silent half-written folder
        log.exception("scan failed")
        failed = {
            "schema": "sdlc360/run-manifest@1",
            "run_id": run_dir.name,
            "status": "failed",
            "error": f"{type(e).__name__}: {e}",
            "target": target,
            "ref": ref,
            "tool": self_version(),
            "started_at": started.isoformat(timespec="seconds"),
            "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        (run_dir / "manifest.json").write_text(json.dumps(failed, indent=2), encoding="utf-8")
        raise
    finally:
        log.removeHandler(fh)
        fh.close()
        shutil.rmtree(tmp, onexc=_force_remove)


def rerender(run_dir: Path, review_path: Path | None = None, checklist: str | None = None, profile: str | None = None) -> Path:
    """Re-apply capabilities (profile), acceptance texts and review.json to a run, without re-scanning."""
    report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    report.setdefault("scan_params", defaults())  # runs before 0.4 used the standard thresholds
    old = report.get("checklist") or {}
    src = Path(report["repo"]["source"])
    if checklist or profile:
        report["checklist"] = resolve_checklist(src if src.is_dir() else None, checklist, profile)
    elif old.get("origin") == "profile":  # pick up edits to the same profile
        with contextlib.suppress(ValueError):  # a profile deleted since: keep the snapshot
            report["checklist"] = profile_checklist(old["profile"]["id"])
    elif old.get("origin", "default") in ("default", "none"):  # runs before 0.4
        report["checklist"] = profile_checklist(STANDARD)
    elif old.get("origin") == "explicit" and old.get("path") and Path(old["path"]).is_file():
        report["checklist"] = resolve_checklist(None, old["path"])
    rp = review_path or run_dir / "review.json"
    review = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else None
    return write_outputs(run_dir, finalize(report, review))


def calibration_run_ids(runs_dir: Path = DEFAULT_RUNS) -> set[str]:
    """Runs made by a calibration (runs/calibrations/*.json): they are opened from the calibration, not listed as projects."""
    ids: set[str] = set()
    for f in (Path(runs_dir) / "calibrations").glob("*.json"):
        try:
            ids |= {r["run_id"] for r in json.loads(f.read_text(encoding="utf-8")).get("repos", []) if r.get("run_id")}
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return ids


def list_projects(runs_dir: Path = DEFAULT_RUNS) -> list[dict]:
    """Group runs by source repo; newest run first within each project."""
    projects: dict[str, dict] = {}
    hidden = calibration_run_ids(runs_dir)
    for rep_path in sorted(Path(runs_dir).glob("*/report.json"), reverse=True):
        if rep_path.parent.name in hidden:
            continue
        try:
            rep = json.loads(rep_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        man_path = rep_path.with_name("manifest.json")
        man = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {}
        src = rep["repo"]["source"]
        p = projects.setdefault(
            src,
            {
                "source": src,
                "target": man.get("target", src),
                "name": short_name(src) if is_remote(src) else src.replace("\\", "/").rstrip("/").split("/")[-1],
                "runs": [],
            },
        )
        p["runs"].append(
            {
                "id": rep_path.parent.name,
                "generated_at": rep["generated_at"],
                "score": rep["overall"]["score"],
                "grade": rep["overall"]["grade"],
                "reviewed": bool(rep.get("review")),
                "profile": ((rep.get("checklist") or {}).get("profile") or {}).get("id"),
            }
        )
    return sorted(projects.values(), key=lambda p: p["runs"][0]["generated_at"], reverse=True)
