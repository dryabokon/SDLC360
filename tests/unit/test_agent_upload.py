"""Claude Code sessions added to a run: the browser's parser equals Python's, only numbers are kept, the endpoint."""

import json
import re
import shutil
import subprocess
import threading
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from src import agent_usage, serve
from src.render import _template

T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
USE = {"input_tokens": 10, "output_tokens": 100, "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 50}


def _entry(kind, t, **kw):
    return json.dumps({"type": kind, "timestamp": t.isoformat().replace("+00:00", "Z"), **kw})


def _log(path: Path) -> Path:
    lines = [
        _entry("user", T0, message={"role": "user", "content": "add a secret-looking prompt"}),
        _entry(
            "assistant",
            T0 + timedelta(minutes=1),
            requestId="r1",
            message={"usage": USE, "content": [{"type": "tool_use", "name": "Edit", "input": {}}]},
        ),
        _entry("assistant", T0 + timedelta(minutes=1), requestId="r1", message={"usage": USE, "content": [{"type": "text", "text": "same request"}]}),
        _entry("user", T0 + timedelta(minutes=2), message={"content": [{"type": "tool_result", "is_error": True}]}),
        _entry("user", T0 + timedelta(minutes=2), toolDenialKind="user", message={"content": [{"type": "text", "text": "<system>"}]}),
        _entry(
            "assistant",
            T0 + timedelta(minutes=3),
            requestId="r2",
            message={
                "usage": USE,
                "content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "ship"}}, {"type": "tool_use", "name": "Agent"}],
            },
        ),
        _entry(  # a skill used by running its script (a Windows path): a use too, and the failure right after counts against it
            "assistant",
            T0 + timedelta(minutes=4),
            requestId="r3",
            message={
                "usage": USE,
                "content": [{"type": "tool_use", "name": "Bash", "input": {"command": r"python .claude\skills\review\scripts\run.py"}}],
            },
        ),
        _entry("user", T0 + timedelta(minutes=5), message={"content": [{"type": "tool_result", "is_error": True}]}),
        _entry(  # a note in a skills folder (no SKILL.md) read: a use of the note
            "assistant",
            T0 + timedelta(minutes=6),
            requestId="r3",
            message={"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "D:/repo/.agents/skills/secrets.md"}}]},
        ),
        _entry("user", T0 + timedelta(hours=2), message={"content": [{"type": "text", "text": "thanks"}]}),
        json.dumps({"type": "cost-state", "totalCostUSD": 2.5}),
        "not json",
        "[1, 2]",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


@pytest.mark.skipif(not shutil.which("node"), reason="node runs the browser's parser")
def test_browser_parser_equals_python(tmp_path):
    f = _log(tmp_path / "s1.jsonl")
    js = re.search(r"/\* parse_session:start.*?/\* parse_session:end \*/", _template(), re.S)
    assert js
    script = tmp_path / "run.mjs"
    script.write_text(
        js.group(0)
        + f"\nconst fs = await import('node:fs');\nconst f = new File([fs.readFileSync({json.dumps(str(f))})], 's1.jsonl');\n"
        + "console.log(JSON.stringify(await parseSession(f)));\n",
        encoding="utf-8",
    )
    got = json.loads(subprocess.run(["node", str(script)], capture_output=True, text=True, check=True).stdout)
    want = json.loads(json.dumps(agent_usage.parse_session(f)))  # tuples as lists
    for k in ("start", "end"):
        assert agent_usage._ts(got[k]) == agent_usage._ts(want[k])
        got.pop(k), want.pop(k)
    assert got == want


def test_only_numbers_are_kept(tmp_path):
    s = agent_usage.parse_session(_log(tmp_path / "s1.jsonl"))
    assert "secret-looking" not in json.dumps(s)
    (clean,) = agent_usage.clean_sessions([{**s, "prompt": "add a secret", "reads": [list(r) for r in s["reads"]]}])
    assert "prompt" not in clean and clean["api_calls"] == 3 and clean["skills"] == {"ship": 1, "review": 1, "secrets": 1}
    assert clean["skill_errors"] == {"ship": 1, "review": 1}  # the failed call came within 10 calls of both uses


@pytest.mark.parametrize(
    "bad",
    [
        {"id": "../x"},
        {"id": "s", "active_hours": -1},
        {"id": "s", "start": "yesterday"},
        {"id": "s", "tokens": {"input": "many"}},
        {"id": "s", "reads": [[1, 2, 3]]},
        {"id": "s", "api_calls": True},
    ],
)
def test_refuses_anything_else(bad):
    with pytest.raises(ValueError):
        agent_usage.clean_sessions([bad])


def _run(runs: Path, source: str, rid: str = "20261101-090000_x") -> str:
    (runs / rid).mkdir(parents=True)
    (runs / rid / "report.json").write_text(json.dumps({"repo": {"source": source}}), encoding="utf-8")
    return rid


def test_upload_endpoint(make_repo, tmp_path, monkeypatch):
    repo = make_repo({"a.py": "a = 1\n"}, name="proj")
    monkeypatch.setattr(serve, "resolve_target", lambda target, cache_dir: (repo, target))
    runs = tmp_path / "runs"
    gh, local = _run(runs, "github.com/acme/proj"), _run(runs, str(repo), "20261101-090001_y")
    session = json.loads(json.dumps(agent_usage.parse_session(_log(tmp_path / "s1.jsonl"))))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), serve.make_handler(runs, tmp_path / "cache"))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    def call(path, body=None):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    try:
        code, d = call(f"/api/agent?run={gh}")
        assert code == 200 and d["available"] is False and d["upload"] is True  # nothing yet: the page offers to add sessions
        code, d = call(f"/api/runs/{gh}/agent", {"sessions": [session]})
        assert code == 200 and d["available"] and d["origin"] == "upload" and d["summary"]["sessions"] == 1
        assert call(f"/api/agent?run={gh}")[1]["origin"] == "upload"  # kept with the run
        assert call(f"/api/runs/{local}/agent", {"sessions": [session]})[0] == 400  # a local folder reads its own logs
        assert call(f"/api/runs/{gh}/agent", {"sessions": [{"id": "x", "cost": -5}]})[0] == 400
        data = json.loads((runs / gh / agent_usage.SESSIONS_FILE).read_text(encoding="utf-8"))
        (runs / gh / agent_usage.SESSIONS_FILE).write_text(json.dumps({**data, "origin": "seed"}), encoding="utf-8")
        assert call(f"/api/runs/{gh}/agent", {"sessions": [session]})[0] == 409  # a demo is not replaced from the app
    finally:
        httpd.shutdown()
        httpd.server_close()
