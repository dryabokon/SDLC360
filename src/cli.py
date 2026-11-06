"""Command line interface: `python sdlc.py scan|render|list|serve`."""

from __future__ import annotations

import argparse
import logging
import sys
import webbrowser
from pathlib import Path

from . import __version__
from .runner import DEFAULT_CACHE, DEFAULT_RUNS, list_projects, rerender, run_scan


def cmd_scan(a: argparse.Namespace) -> int:
    run_dir = run_scan(
        a.target,
        ref=a.ref,
        name=a.name,
        only=a.only.split(",") if a.only else None,
        history_points=0 if a.no_history else a.history,
        history_months=a.months,
        refresh=a.refresh,
        checklist=a.checklist,
        profile=a.profile,
        runs_dir=Path(a.runs_dir),
        cache_dir=Path(a.cache_dir),
    )
    print(str(run_dir))
    if a.open:
        webbrowser.open((run_dir / "report.html").resolve().as_uri())
    return 0


def cmd_render(a: argparse.Namespace) -> int:
    html = rerender(Path(a.run_dir), Path(a.review) if a.review else None, a.checklist, a.profile)
    print(str(html))
    if a.open:
        webbrowser.open(html.resolve().as_uri())
    return 0


def cmd_list(a: argparse.Namespace) -> int:
    projects = list_projects(Path(a.runs_dir))
    for p in projects:
        print(p["source"])
        for r in p["runs"]:
            print(f"   {r['id']:55s} {r['score']!s:>6} {r['grade']:>3}  {'reviewed' if r['reviewed'] else 'auto'}")
    if not projects:
        print("no runs yet")
    return 0


def cmd_serve(a: argparse.Namespace) -> int:
    from .serve import serve

    serve(a.port, Path(a.runs_dir), Path(a.cache_dir), a.open)
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="sdlc.py", description="360° SDLC maturity assessment of a repository.")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--runs-dir", default=str(DEFAULT_RUNS))
    common.add_argument("--cache-dir", default=str(DEFAULT_CACHE))

    s = sub.add_parser("scan", parents=[common], help="scan a local git folder, GitHub URL or owner/repo")
    s.add_argument("target")
    s.add_argument("--ref", help="branch / tag / sha to check out (GitHub targets)")
    s.add_argument("--name", help="run name suffix (default: repo name)")
    s.add_argument("--only", help="comma-separated dimension ids")
    s.add_argument("--history", type=int, default=8, help="historical commits to re-score for the Dynamics view (default 8)")
    s.add_argument("--months", type=int, default=12, help="history window in months (default 12)")
    s.add_argument("--no-history", action="store_true", help="skip historical re-scoring")
    s.add_argument("--profile", help="profile id from assessment/profiles/ (default: the repo's .sdlc360/capabilities.md, else standard)")
    s.add_argument("--checklist", help="a capabilities markdown file instead of a profile")
    s.add_argument("--refresh", action="store_true", help="git fetch a cached clone before scanning")
    s.add_argument("--open", action="store_true", help="open the HTML report when done")
    s.set_defaults(func=cmd_scan)

    r = sub.add_parser("render", help="re-render a run (merging review.json if present)")
    r.add_argument("run_dir")
    r.add_argument("--review", help="path to review JSON (default: <run_dir>/review.json)")
    r.add_argument("--profile", help="re-apply another profile (thresholds need a re-scan)")
    r.add_argument("--checklist", help="re-apply a capabilities markdown file")
    r.add_argument("--open", action="store_true")
    r.set_defaults(func=cmd_render)

    ls = sub.add_parser("list", parents=[common], help="list scanned projects and their runs")
    ls.set_defaults(func=cmd_list)

    sv = sub.add_parser("serve", parents=[common], help="local web app: choose projects, scan, browse")
    sv.add_argument("--port", type=int, default=8360)
    sv.add_argument("--open", action="store_true", help="open the browser")
    sv.set_defaults(func=cmd_serve)

    a = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
    return a.func(a)
