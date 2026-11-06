"""Project dynamics: weekly velocity from git log, and maturity scores re-computed at historical commits."""

from __future__ import annotations

import logging
import os
import shutil
import stat
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .repo import Repo, run_git

log = logging.getLogger("sdlc360")


def _force_remove(func, path, _exc) -> None:
    """git marks object files read-only on Windows; clear the flag and retry."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        pass


DOC_HINT = ("readme", "docs/", "doc/", ".md", ".rst", "architecture", "adr")


def _week_start(dt: datetime) -> datetime:
    d = dt - timedelta(days=dt.weekday())
    return d.replace(hour=0, minute=0, second=0, microsecond=0)


def velocity(repo: Repo, weeks: int = 52) -> dict:
    """Weekly activity: commits, active authors, files touched, % commits touching tests / docs.
    Uses only commit + tree data (`--name-only`), so it works on blobless clones without fetching blobs."""
    if not repo.is_git or not repo.head:
        return {"weeks": []}
    head_t = datetime.fromisoformat(repo.head["date"])
    since = _week_start(head_t) - timedelta(weeks=weeks - 1)
    out = run_git(repo.root, "log", "--no-merges", f"--since={since.isoformat()}", "--format=\x1e%ct\x1f%ae", "--name-only", "HEAD", check=False)
    buckets: dict[datetime, dict] = {}
    for i in range(weeks):
        w = since + timedelta(weeks=i)
        buckets[w] = {"commits": 0, "authors": set(), "files": 0, "tests": 0, "docs": 0}
    for rec in out.split("\x1e"):
        rec = rec.strip()
        if not rec:
            continue
        head, *files = rec.splitlines()
        ts, author = head.split("\x1f", 1)
        w = _week_start(datetime.fromtimestamp(int(ts), UTC))
        b = buckets.get(w)
        if b is None:
            continue
        files = [f for f in files if f.strip()]
        b["commits"] += 1
        b["authors"].add(author.lower())
        b["files"] += len(files)
        b["tests"] += any(Repo.is_test(f) for f in files)
        b["docs"] += any(h in f.lower() for f in files for h in DOC_HINT)
    rows = []
    for w, b in sorted(buckets.items()):
        n = b["commits"]
        rows.append(
            {
                "week": w.date().isoformat(),
                "commits": n,
                "authors": len(b["authors"]),
                "files": b["files"],
                "tests_pct": round(100 * b["tests"] / n, 1) if n else None,
                "docs_pct": round(100 * b["docs"] / n, 1) if n else None,
            }
        )
    return {"weeks": rows}


def sample_commits(repo: Repo, points: int = 8, months: int = 12) -> list[dict]:
    """Pick up to `points` first-parent commits evenly spaced over the last `months` (or the repo's life if shorter)."""
    if not repo.is_git or not repo.head or points < 1:
        return []
    head_t = datetime.fromisoformat(repo.head["date"])
    first = run_git(repo.root, "log", "--reverse", "--first-parent", "--format=%ct", "HEAD", check=False).split("\n", 1)[0].strip()
    first_t = datetime.fromtimestamp(int(first), UTC) if first.isdigit() else head_t
    start = max(first_t, head_t - timedelta(days=30.5 * months))
    span = (head_t - start).total_seconds()
    shas, seen = [], set()
    for i in range(points):
        t = head_t if i == points - 1 else start + timedelta(seconds=span * (i + 1) / points)
        line = run_git(repo.root, "log", "-1", "--first-parent", f"--before={int(t.timestamp())}", "--format=%H\x1f%ct", "HEAD", check=False).strip()
        if not line:
            continue
        sha, ct = line.split("\x1f")
        if sha not in seen:
            seen.add(sha)
            shas.append({"sha": sha, "date": datetime.fromtimestamp(int(ct), UTC).isoformat()})
    return shas


def score_history(
    repo: Repo, scan_fn: Callable[[Repo], dict], points: int = 8, months: int = 12, progress: Callable[[str], None] | None = None
) -> list[dict]:
    """Re-run the scan at sampled historical commits using temporary detached worktrees."""
    commits = sample_commits(repo, points, months)
    result = []
    tmp_root = Path(tempfile.mkdtemp(prefix="sdlc360-hist-"))
    # Our own blobless cache clones: use worktrees (blobs are fetched lazily from the promisor remote).
    # User's local repos: never write into their .git - use a throwaway `clone --shared` instead.
    partial = run_git(repo.root, "config", "--get", "remote.origin.promisor", check=False).strip() == "true"
    shared: Path | None = None
    try:
        if not partial:
            shared = tmp_root / "_shared"
            run_git(tmp_root, "clone", "--quiet", "--shared", "--no-checkout", str(repo.root), shared.name)
        for i, c in enumerate(commits, 1):
            if c["sha"] == repo.head.get("sha"):
                continue  # the current scan covers HEAD
            msg = f"history {i}/{len(commits)}: {c['sha'][:8]} ({c['date'][:10]})"
            log.info(msg)
            if progress:
                progress(msg)
            wt = tmp_root / c["sha"][:12]
            try:
                if partial:
                    run_git(repo.root, "worktree", "add", "--detach", "--force", str(wt), c["sha"])
                    target = wt
                else:
                    assert shared is not None
                    run_git(shared, "checkout", "--quiet", "--force", "--detach", c["sha"])
                    run_git(shared, "clean", "-qfdx")
                    target = shared
                rep = scan_fn(Repo(target, repo.source))
                result.append(
                    {"sha": c["sha"], "date": c["date"], "overall": rep["overall"]["score"], "dims": {d["id"]: d["score"] for d in rep["dimensions"]}}
                )
            except Exception as e:  # keep going: one bad commit must not kill the timeline
                log.warning("history point %s failed: %s", c["sha"][:8], e)
            finally:
                if partial:
                    run_git(repo.root, "worktree", "remove", "--force", str(wt), check=False)
    finally:
        if partial:
            run_git(repo.root, "worktree", "prune", check=False)
        shutil.rmtree(tmp_root, onexc=_force_remove)
    return result
