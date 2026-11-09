"""Integration: full scans of small but real git repositories (golden fixtures) and the run-folder contract."""

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from src.repo import Repo
from src.runner import list_projects, run_scan
from src.scanner import scan
from src.serve import local_request, make_handler

pytestmark = pytest.mark.integration

WORKFLOW = """name: ci
on: [push, pull_request]
permissions:
  contents: read
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567
      - run: ruff check .
      - run: pytest --cov=app --cov-fail-under=80
"""

MATURE = {
    "README.md": "# Demo\n\n## Overview\nWhat it is.\n\n## Setup\n`pip install -e .`\n\n## Usage\nRun `python -m app`.\n\n"
    "## Testing\n`pytest`\n\n## Configuration\nSee `.env.example`.\n\nRuns land in `runs/`; see [architecture](docs/architecture.md).\n",
    "AGENTS.md": "# Agent instructions\n\n## Commands\n- test: `pytest`\n- lint: `ruff check .`\n\n## Layout\n- `app/` code\n- `tests/` tests\n\n"
    "## Conventions\nYou must run tests before committing.\n",
    "CLAUDE.md": "@AGENTS.md\n",
    "docs/architecture.md": "# Architecture\n\n```mermaid\ngraph LR; cli-->core\n```\n",
    ".gitignore": ".env\n*.pem\n*.key\nruns/\n",
    ".env.example": "API_TOKEN=\n",
    "pyproject.toml": "[tool.ruff]\nline-length = 100\n[tool.mypy]\nstrict = true\n[tool.pytest.ini_options]\ntestpaths = ['tests']\n",
    ".github/workflows/ci.yml": WORKFLOW,
    "app/__init__.py": '"""App."""\n',
    "app/core.py": '"""Core."""\n\n\ndef add(a: int, b: int) -> int:\n    """Add."""\n    return a + b\n',
    "app/cli.py": '"""CLI."""\n\n\ndef main() -> int:\n    """Entry."""\n    return 0\n',
    "tests/test_core.py": "from app.core import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n",
    "tests/test_cli.py": "from app.cli import main\n\n\ndef test_main():\n    assert main() == 0\n",
    ".github/workflows/release.yml": WORKFLOW.replace("name: ci", "name: release"),
}
# the scanner's current thresholds: README >= 400 words, >= 5 test files, 2 workflows for full marks
MATURE["README.md"] += "\n## Details\n\n" + "This paragraph explains the project in plain words for new readers. " * 40
MATURE.update({f"tests/test_extra_{i}.py": f"def test_{i}():\n    assert True\n" for i in range(3)})


def statuses(report: dict) -> dict[str, str]:
    return {c["id"]: c["status"] for d in report["dimensions"] for c in d["checks"]}


@pytest.fixture
def mature(make_repo):
    return scan(Repo(make_repo(MATURE, name="mature")))


@pytest.fixture
def bare(make_repo):
    return scan(Repo(make_repo({"main.py": "print('hi')\n"}, name="bare")))


def test_mature_repo_meets_the_basics(mature):
    st = statuses(mature)
    for cid in (
        "doc.readme",
        "ai.instructions",
        "test.present",
        "test.ci",
        "ci.present",
        "ci.pr",
        "hyg.lint",
        "sec.no_secrets",
        "sec.gitignore",
        "sec.workflow_permissions",
        "ci.pinning",
        "doc.links",
    ):
        assert st[cid] == "pass", cid


def test_bare_repo_fails_the_criticals(bare):
    st = statuses(bare)
    for cid in ("doc.readme", "ai.instructions", "test.present", "test.ci", "ci.present", "hyg.lint", "sk.present", "arch.doc"):
        assert st[cid] == "fail", cid
    assert st["sec.no_secrets"] == "pass"  # nothing to leak is not a failure


def test_mature_scores_higher_and_bare_is_gated(mature, bare):
    assert mature["overall"]["score"] > bare["overall"]["score"] + 25
    gated = [d for d in bare["dimensions"] if d["capped_by"] or (d["score"] is not None and d["score"] <= 49)]
    assert gated


def test_every_aspect_reports_without_errors(mature):
    assert [d["id"] for d in mature["dimensions"]] == ["docs", "harness", "skills", "review", "tests", "hygiene", "cicd", "security", "cost"]
    assert not [c["id"] for d in mature["dimensions"] for c in d["checks"] if c["id"].endswith(".error")]


def test_cost_is_not_applicable_without_paid_resources(mature):
    cost = next(d for d in mature["dimensions"] if d["id"] == "cost")
    assert cost["score"] is None


def test_run_folder_contract(make_repo, tmp_path):
    root = make_repo(MATURE, name="mature")
    runs = tmp_path / "runs"
    run_dir = run_scan(str(root), history_points=0, runs_dir=runs, cache_dir=tmp_path / "cache")
    assert sorted(p.name for p in run_dir.iterdir()) == ["manifest.json", "report.html", "report.json", "scan.log"]
    man = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert man["status"] == "ok" and man["target_head"]["sha"] and man["reproduce"].startswith("python sdlc.py scan")
    html = (run_dir / "report.html").read_text(encoding="utf-8")
    assert "/*__REPORT__*/null" not in html and '"sdlc360/report@2"' in html
    assert [p["name"] for p in list_projects(runs)] == ["mature"]


def test_failed_scan_leaves_a_failed_manifest(make_repo, tmp_path, monkeypatch):
    root = make_repo({"a.py": ""}, name="boom")

    def explode(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr("src.runner.scan", explode)
    with pytest.raises(RuntimeError):
        run_scan(str(root), history_points=0, runs_dir=tmp_path / "runs", cache_dir=tmp_path / "cache")
    (man,) = (tmp_path / "runs").glob("*/manifest.json")
    assert json.loads(man.read_text(encoding="utf-8"))["status"] == "failed"


@pytest.mark.parametrize(
    ("host", "origin", "ok"),
    [
        ("127.0.0.1:8360", None, True),
        ("localhost:8360", "http://localhost:8360", True),
        ("evil.example:8360", None, False),  # DNS rebinding
        ("127.0.0.1:8360", "https://evil.example", False),  # cross-site POST
        (None, None, False),
    ],
)
def test_local_request_guard(host, origin, ok):
    assert local_request(host, origin) is ok


def test_server_api(tmp_path):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(tmp_path / "runs", tmp_path / "cache"))
    (tmp_path / "runs").mkdir()
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        assert json.loads(urllib.request.urlopen(base + "/api/projects").read()) == []
        assert b'"app"' in urllib.request.urlopen(base + "/").read()
        req = urllib.request.Request(base + "/api/scan", data=b'{"target": ""}', method="POST")
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        assert e.value.code == 400
        req = urllib.request.Request(base + "/api/projects", headers={"Origin": "https://evil.example"})
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        assert e.value.code == 403
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_report_embeds_a_card_for_every_cited_reference(mature):
    """A report is self-contained: each quote's source card travels with it, also in a static report.html."""
    cited = {b["source"] for d in mature["dimensions"] for c in d["checks"] for b in c["method"].get("basis", [])}
    assert cited and set(mature["references"]) == cited
    assert all(r["title"] and r["retrieved"] for r in mature["references"].values())


def test_catalog_embeds_reference_cards():
    from src.serve import catalog

    cat = catalog()
    cited = {b["source"] for m in cat["methods"].values() for b in m["basis"]}
    assert set(cat["references"]) == cited


def test_an_older_run_lines_up_with_the_current_aspects(mature):
    """Older runs had other aspects ("architecture", "runs" with run.* checks, ...); finalize() places their checks by
    the current catalog, so they line up with the Capabilities tab, and doing it twice changes nothing."""
    import copy

    from src.dimensions import DIMENSIONS
    from src.scanner import finalize

    old = copy.deepcopy(mature)
    checks = [c for d in old["dimensions"] for c in d["auto_checks"]]
    for c in checks:
        c["id"] = c["id"].replace("rep.", "run.")
    old["dimensions"] = [
        {"id": "architecture", "name": "Architecture", "auto_checks": [c for c in checks if c["id"].startswith("arch.")]},
        {"id": "runs", "name": "Runs & Reproducibility", "auto_checks": [c for c in checks if c["id"].startswith("run.")]},
        {"id": "security", "name": "Old name", "auto_checks": [c for c in checks if not c["id"].startswith(("arch.", "run."))]},
    ]
    once = finalize(old)
    assert [d["id"] for d in once["dimensions"]] == [d.id for d in DIMENSIONS]
    assert [d["name"] for d in once["dimensions"]] == [d.name for d in DIMENSIONS]
    where = {c["id"]: d["id"] for d in once["dimensions"] for c in d["checks"]}
    assert where["rep.lockfile"] == "security" and where["rep.entrypoints"] == "cicd" and where["arch.doc"] == "docs"
    assert where["sec.codeowners"] == "review"
    again = finalize(copy.deepcopy(once))
    assert {c["id"]: d["id"] for d in again["dimensions"] for c in d["checks"]} == where
