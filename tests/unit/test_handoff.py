"""A finding handed to a coding agent: the prompt is built from the run alone, broken skills come first."""

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from src import cli, handoff, serve
from src.runner import run_scan
from tests.conftest import _git

SKILL = "---\nname: deploy\ndescription: Deploy the app. Use when asked to deploy.\n---\nRun `app/deploy.py`.\n"


@pytest.fixture
def run(make_repo, tmp_path, monkeypatch):
    """A run of a small repository whose skill names a file git deleted: a broken skill and open checks."""
    monkeypatch.setattr(handoff.agent_usage, "LOGS_ROOT", tmp_path / "no-logs")  # no Claude Code sessions here
    root = make_repo({"app/__init__.py": "", "app/deploy.py": "", "tests/test_app.py": "", ".claude/skills/deploy/SKILL.md": SKILL}, name="proj")
    _git(root, "rm", "-q", "app/deploy.py")
    _git(root, "commit", "-q", "-m", "drop deploy")
    return run_scan(str(root), history_points=0, runs_dir=tmp_path / "runs", cache_dir=tmp_path / "cache")


def _report(run_dir):
    return json.loads((run_dir / "report.json").read_text(encoding="utf-8"))


def test_broken_skills_come_first_then_the_ranked_actions(run):
    rep = _report(run)
    ids = [f["id"] for f in handoff.findings(rep, handoff.skill_verdicts(run, rep))]
    assert ids[0] == "skill:deploy"
    assert ids[1:4] == [a["check_id"] for a in rep["top_actions"][:3]]


def test_a_check_prompt_carries_expected_found_and_what_to_do(run):
    rep = _report(run)
    c = next(c for d in rep["dimensions"] for c in d["checks"] if c["id"] == "hyg.lint")
    p = handoff.prompt(rep, "hyg.lint")
    assert f"Expected: {c['title']}" in p and c["recommendation"] in p and f"- {c['evidence'][0]}" in p
    assert "Check the finding against the code first" in p and "should show hyg.lint as Met" in p
    assert f"python sdlc.py scan {rep['repo']['source']} --no-history" in p


def test_a_skill_prompt_names_what_is_gone(run):
    rep = _report(run)
    p = handoff.prompt(rep, "skill:deploy", handoff.skill_verdicts(run, rep))
    assert "app/deploy.py" in p and "is judged broken" in p and "should show the skill deploy as Up to date" in p


def test_a_met_or_unknown_finding_has_no_prompt(run):
    rep = _report(run)
    met = next(c["id"] for d in rep["dimensions"] for c in d["checks"] if c["status"] == "pass")
    for fid in (met, "no.such_check", "skill:nope"):
        with pytest.raises(KeyError):
            handoff.prompt(rep, fid, handoff.skill_verdicts(run, rep))


def test_cli(run, capsys):
    assert cli.main(["handoff", str(run), "--list"]) == 0
    assert capsys.readouterr().out.splitlines()[0].startswith("skill:deploy")
    assert cli.main(["handoff", str(run), "--top", "2"]) == 0
    assert capsys.readouterr().out.count("Fix exactly one finding") == 2
    assert cli.main(["handoff", str(run), "--check", "no.such_check"]) == 2


def test_endpoint(run, tmp_path):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), serve.make_handler(run.parent, tmp_path / "cache"))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}/api/handoff"

    def call(q):
        try:
            with urllib.request.urlopen(base + q, timeout=20) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    try:
        code, d = call(f"?run={run.name}&id=hyg.lint")
        assert code == 200 and "Fix exactly one finding: hyg.lint" in d["prompt"]
        assert call(f"?run={run.name}&id=no.such_check")[0] == 404
        assert call("?run=../etc&id=hyg.lint")[0] == 404
    finally:
        httpd.shutdown()
