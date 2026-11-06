"""One scan = one run folder. Shared by the CLI and the local web server."""

from __future__ import annotations

import contextlib
import json
import logging
import re
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from . import __version__
from .history import score_history, velocity
from .profiles import STANDARD, defaults
from .profiles import checklist as profile_checklist
from .profiles import resolve as resolve_checklist
from .render import render_html
from .repo import Repo, resolve_target, run_git
from .scanner import finalize, scan

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUNS = PROJECT_ROOT / "runs"
DEFAULT_CACHE = PROJECT_ROOT / ".cache" / "repos"
RUN_ID_RE = re.compile(r"^[\w.-]+$")
log = logging.getLogger("sdlc360")


def slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", s.replace("github.com/", "")).strip("-")[:60] or "repo"


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
    runs_dir: Path = DEFAULT_RUNS,
    cache_dir: Path = DEFAULT_CACHE,
    progress: Callable[[str], None] | None = None,
) -> Path:
    say = progress or (lambda m: None)
    started = datetime.now(UTC)
    say(f"resolving {target}")
    root, source = resolve_target(target, Path(cache_dir), ref, refresh)
    nm = name or slug(source.split("/", 1)[-1] if source.startswith("github.com/") else Path(source).name)
    run_dir = Path(runs_dir) / f"{started.strftime('%Y%m%d-%H%M%S')}_{nm}"
    run_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(run_dir / "scan.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(fh)
    try:
        log.info("scanning %s (%s) -> %s", source, root, run_dir)
        say("scanning HEAD")
        repo = Repo(root, source)
        cl = resolve_checklist(root, checklist, profile)
        log.info("capabilities: %s (%s)", cl["path"], (cl.get("profile") or {}).get("name", cl["origin"]))
        report = scan(repo, only=only, checklist=cl)
        for d in report["dimensions"]:
            log.info("  %-24s %6s  %s  (%.2fs)", d["name"], d["score"], d["grade"], d["elapsed_s"])
        say("computing velocity")
        hist = {"velocity": velocity(repo), "scores": []}
        if history_points > 1 and repo.is_git:
            pts = score_history(repo, lambda r: scan(r, only=only, checklist=cl), history_points, history_months, say)
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
            "resolved_path": str(root),
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
            + (f" --ref {repo.head['sha']}" if repo.head.get("sha") else "")
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


def list_projects(runs_dir: Path = DEFAULT_RUNS) -> list[dict]:
    """Group runs by source repo; newest run first within each project."""
    projects: dict[str, dict] = {}
    for rep_path in sorted(Path(runs_dir).glob("*/report.json"), reverse=True):
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
                "name": src.replace("github.com/", "").replace("\\", "/").rstrip("/").split("/")[-1]
                if not src.startswith("github.com/")
                else src.replace("github.com/", ""),
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
