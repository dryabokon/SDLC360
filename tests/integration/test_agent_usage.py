"""Agent use: a synthetic Claude Code session log joined with a throw-away git repository."""

import json
import subprocess
from datetime import UTC, datetime, timedelta

import pytest

from src import agent_usage

pytestmark = pytest.mark.integration
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false"]


def _entry(kind, t, **kw):
    return json.dumps({"type": kind, "timestamp": t.isoformat().replace("+00:00", "Z"), **kw})


def _commit(root, rel, text, msg, when):
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(text, encoding="utf-8")
    env = {"GIT_AUTHOR_DATE": when.isoformat(), "GIT_COMMITTER_DATE": when.isoformat()}
    subprocess.run([*GIT, "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run([*GIT, "commit", "-q", "-m", msg], cwd=root, check=True, capture_output=True, env={**__import__("os").environ, **env})


def test_sessions_are_counted_linked_and_explained(make_repo, tmp_path):
    t0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
    root = make_repo({"README.md": "# x\n", ".claude/skills/ship/SKILL.md": "---\nname: ship\n---\n"}, name="proj")
    _commit(root, "app/a.py", "a = 1\n", "Add a\n\nCo-Authored-By: Claude Opus <noreply@anthropic.com>", t0 + timedelta(minutes=20))
    _commit(root, "app/b.py", "b = 1\n", "Add b by hand", t0 + timedelta(days=3))

    logs = tmp_path / "logs" / agent_usage.re.sub(r"[^A-Za-z0-9]", "-", str(root))
    logs.mkdir(parents=True)
    use = {"input_tokens": 10, "output_tokens": 100, "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 50}
    lines = [
        _entry("user", t0, message={"role": "user", "content": "add a"}),
        _entry(
            "assistant",
            t0 + timedelta(minutes=1),
            requestId="r1",
            message={"usage": use, "content": [{"type": "tool_use", "id": "x", "name": "Edit", "input": {}}]},
        ),
        _entry("assistant", t0 + timedelta(minutes=1), requestId="r1", message={"usage": use, "content": [{"type": "text", "text": "same request"}]}),
        _entry("user", t0 + timedelta(minutes=2), message={"content": [{"type": "tool_result", "tool_use_id": "x", "is_error": True}]}),
        _entry(
            "assistant",
            t0 + timedelta(minutes=3),
            requestId="r2",
            message={"usage": use, "content": [{"type": "tool_use", "id": "y", "name": "Skill", "input": {"skill": "ship"}}]},
        ),
        _entry("user", t0 + timedelta(hours=2), message={"role": "user", "content": "thanks"}),  # after a long pause
        json.dumps({"type": "cost-state", "totalCostUSD": 2.5}),
        "not json",
    ]
    (logs / "s1.jsonl").write_text("\n".join(lines), encoding="utf-8")

    r = agent_usage.report(str(root), tmp_path / "logs")
    assert r["available"]
    (s,) = r["sessions"]
    assert s["api_calls"] == 2 and s["tokens"]["output"] == 200  # one request counted once
    assert s["tool_calls"] == 2 and s["tool_errors"] == 1 and s["prompts"] == 2 and s["skills"] == {"ship": 1}
    assert s["active_hours"] < 0.2 and s["span_hours"] == 2.0  # the pause is not active time
    assert s["cost"] == 2.5 and s["commits"] == 1 and s["cost_per_commit"] == 2.5

    by_subject = {c["subject"]: c for c in r["commits"]}
    assert by_subject["Add a"]["agent"] and by_subject["Add a"]["session"] == "s1" and by_subject["Add a"]["cost"] == 2.5
    assert not by_subject["Add b by hand"]["agent"] and by_subject["Add b by hand"]["session"] is None
    assert r["summary"]["agent_commits"] == 1 and r["summary"]["cost_per_commit"] == 2.5

    titles = [f["title"] for f in r["findings"]]
    assert "Agent code goes straight to the main branch" in titles
    assert "The project's skills are in use" in titles
    assert all(f["seen"] and f["why"] and f["fix"] and f["who"] for f in r["findings"])
    tones = [f["tone"] for f in r["findings"]]
    assert tones == sorted(tones, key=lambda t: t == "good")  # what to improve first


def test_no_logs_or_github(tmp_path):
    assert not agent_usage.report("github.com/a/b", tmp_path)["available"]
    assert not agent_usage.report(str(tmp_path), tmp_path)["available"]


def test_telemetry_is_received_and_kept(tmp_path, monkeypatch):
    import threading
    import urllib.request
    from http.server import ThreadingHTTPServer

    from src import serve

    monkeypatch.setattr(serve, "TELEMETRY", tmp_path / "telemetry")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), serve.make_handler(tmp_path / "runs", tmp_path / "cache"))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        body = json.dumps({"resourceMetrics": [{"scopeMetrics": []}]}, indent=1).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{httpd.server_address[1]}/v1/metrics", data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            assert r.status == 200
        (line,) = (tmp_path / "telemetry" / "metrics.jsonl").read_text(encoding="utf-8").splitlines()  # one export, one line
        assert json.loads(line) == {"resourceMetrics": [{"scopeMetrics": []}]}
    finally:
        httpd.shutdown()
        httpd.server_close()
