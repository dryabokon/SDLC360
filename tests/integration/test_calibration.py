"""Calibration end to end on local throw-away repositories: snapshot, comparison, pins, the reference set, the API."""

import json
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from src import calibration
from src.runner import list_projects

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def own_files(tmp_path, monkeypatch):
    """Never touch the real assessment/calibration files: the user's set and the pins live in tmp_path."""
    monkeypatch.setattr(calibration, "CUSTOM_SET", tmp_path / "custom.json")
    monkeypatch.setattr(calibration, "PINS", tmp_path / "pins.json")


def test_calibration_records_every_verdict_and_compares(make_repo, tmp_path):
    good = make_repo({"README.md": "# good\n", "tests/test_a.py": "def test_a():\n    assert True\n"}, name="good")
    bare = make_repo({"main.py": "print(1)\n"}, name="bare")
    repos = [
        {"target": str(good), "kind": "library", "why": "w", "builtin": True},
        {"target": str(bare), "kind": "application", "why": "", "builtin": False},
    ]
    runs, cache = tmp_path / "runs", tmp_path / "cache"
    seen: list[tuple[int, str]] = []

    first = calibration.run_calibration(repos, runs_dir=runs, cache_dir=cache, progress=lambda i, st, m: seen.append((i, st)))
    snap = json.loads(first.read_text(encoding="utf-8"))
    assert [r["status"] for r in snap["repos"]] == ["ok", "ok"]
    assert (0, "done") in seen and (1, "done") in seen
    assert snap["profile"] == "standard" and snap["checks"]
    assert set(snap["checks"]) == set(snap["repos"][0]["verdicts"]) | set(snap["repos"][1]["verdicts"])
    assert all((runs / r["run_id"] / "report.json").is_file() for r in snap["repos"])  # each one is a normal run
    assert calibration.load_pins() == {}  # local folders are read as they are: nothing to pin

    res = calibration.result(None, runs)
    assert res["previous"] is None and res["totals"]["ok"] == 2
    assert res["repos"][0]["dims"] and [c["order"] for c in sorted(res["checks"], key=lambda c: c["order"])] == list(range(len(res["checks"])))
    assert res["totals"]["verdicts"] == sum(c["assessed"] for c in res["checks"])
    shares = [c["met_share"] for c in res["checks"] if c["met_share"] is not None]
    assert shares == sorted(shares)  # fewest met first

    # same commits, a changed verdict: attributed to the scanner
    snap["id"], snap["started_at"] = "20000101-000000", "2000-01-01T00:00:00+00:00"
    cid = next(iter(snap["checks"]))
    snap["repos"][0]["verdicts"][cid] = "fail" if snap["repos"][0]["verdicts"][cid] != "fail" else "pass"
    (runs / "calibrations" / "20000101-000000.json").write_text(json.dumps(snap), encoding="utf-8")
    res = calibration.result(first.stem, runs)
    assert res["previous"]["id"] == "20000101-000000"
    assert [(c["id"], c["cause"]) for c in res["previous"]["changes"]] == [(cid, "scanner")]
    assert res["repos"][0]["same_commit"] is True

    # calibration runs are opened from the calibration, not listed as projects
    assert list_projects(runs) == []


def _fake_scan(heads: list[str], calls: list[dict]):
    """A scan of a GitHub repository without the network: records how it was called, returns a minimal run."""

    def scan(target, *, ref=None, refresh=False, runs_dir, **_):
        calls.append({"target": target, "ref": ref, "refresh": refresh})
        run = Path(runs_dir) / f"run{len(calls)}"
        run.mkdir(parents=True)
        report = {
            "repo": {"source": f"github.com/{target}", "head": {"sha": ref or heads[0], "date": "2026-11-01"}},
            "overall": {"score": 50.0, "grade": "D"},
            "dimensions": [{"id": "docs", "name": "Docs", "score": 50.0, "checks": [{"id": "doc.readme", "title": "README", "status": "pass"}]}],
        }
        (run / "report.json").write_text(json.dumps(report), encoding="utf-8")
        return run

    return scan


def test_github_repositories_are_pinned_until_moved_on(tmp_path):
    repos, calls, heads = [{"target": "owner/repo", "kind": "library"}], [], ["a" * 40]
    kw = {"runs_dir": tmp_path / "runs", "cache_dir": tmp_path / "c", "scan": _fake_scan(heads, calls)}

    calibration.run_calibration(repos, **kw)  # no pin yet: the latest commit, and pinned there
    assert calls[-1] == {"target": "owner/repo", "ref": None, "refresh": True}
    assert calibration.load_pins() == {"owner/repo": "a" * 40}

    heads[0] = "b" * 40  # the project moved on; the calibration does not
    calibration.run_calibration(repos, **kw)
    assert calls[-1] == {"target": "owner/repo", "ref": "a" * 40, "refresh": False}

    calibration.run_calibration(repos, latest=True, **kw)  # on purpose: the latest commit, and the pin moves
    assert calls[-1]["ref"] is None and calibration.load_pins() == {"owner/repo": "b" * 40}
    assert calibration.reference_set(tmp_path / "none.json", tmp_path / "none.json") == []


def test_unreachable_repository_is_recorded_and_others_go_on(make_repo, tmp_path):
    ok = make_repo({"README.md": "# x\n"}, name="ok")
    repos = [{"target": str(tmp_path / "gone"), "kind": "library"}, {"target": str(ok), "kind": "library"}]
    snap = json.loads(calibration.run_calibration(repos, runs_dir=tmp_path / "runs", cache_dir=tmp_path / "c").read_text(encoding="utf-8"))
    assert [r["status"] for r in snap["repos"]] == ["failed", "ok"]
    assert snap["repos"][0]["error"]


def test_custom_reference_repositories(make_repo, tmp_path):
    default, custom = tmp_path / "set.json", tmp_path / "custom.json"
    default.write_text(json.dumps({"repos": [{"target": "encode/httpx", "kind": "library", "why": "d"}]}), encoding="utf-8")
    assert [r["builtin"] for r in calibration.reference_set(default, custom)] == [True]

    with pytest.raises(ValueError, match="already"):
        calibration.add_custom("https://github.com/Encode/httpx", "library", "", default, custom)
    with pytest.raises(ValueError):
        calibration.add_custom("not a repo", "library", "", default, custom)
    with pytest.raises(ValueError, match="kind"):
        calibration.add_custom("owner/repo", "rocket", "", default, custom)

    added = calibration.add_custom("https://github.com/owner/repo", "agentic", "  ours  ", default, custom)
    assert added == {"target": "owner/repo", "kind": "agentic", "why": "ours", "builtin": False}
    assert [r["target"] for r in calibration.reference_set(default, custom)] == ["encode/httpx", "owner/repo"]

    calibration.remove_custom("owner/repo", custom)
    assert len(calibration.reference_set(default, custom)) == 1
    with pytest.raises(ValueError):
        calibration.remove_custom("encode/httpx", custom)  # a default one cannot be removed


def test_default_reference_set_is_valid():
    repos = calibration.reference_set()
    assert len(repos) >= 5 and all(r["kind"] in calibration.KINDS and r["why"] for r in repos)


def test_snapshot_id_is_checked(tmp_path):
    with pytest.raises(ValueError):
        calibration.load_snapshot("../secret", tmp_path)


def test_calibration_api(make_repo, tmp_path, monkeypatch):
    from src.serve import make_handler

    ref = make_repo({"README.md": "# ref\n"}, name="ref")
    default = tmp_path / "set.json"
    default.write_text(json.dumps({"repos": [{"target": str(ref), "kind": "library", "why": "a fixture"}]}), encoding="utf-8")
    monkeypatch.setattr(calibration, "DEFAULT_SET", default)
    runs = tmp_path / "runs"
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(runs, tmp_path / "cache"))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    def call(path, body=None):
        req = urllib.request.Request(
            base + path, data=None if body is None else json.dumps(body).encode(), headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    try:
        code, d = call("/api/calibration")
        assert code == 200 and d["result"] is None and [r["target"] for r in d["set"]] == [str(ref)]

        assert call("/api/calibration/repos", {"target": "owner/extra"})[0] == 200
        assert call("/api/calibration/repos", {"target": "owner/extra"})[0] == 400  # already there
        assert len(call("/api/calibration")[1]["set"]) == 2
        assert call("/api/calibration/repos/remove", {"target": "owner/extra"})[0] == 200
        assert call("/api/calibration/repos/remove", {"target": str(ref)})[0] == 400  # a default one stays

        code, job = call("/api/calibration/run", {})
        assert code == 202
        for _ in range(120):
            j = call(f"/api/jobs/{job['job']}")[1]
            if j["status"] in ("done", "error"):
                break
            time.sleep(0.5)
        assert j["status"] == "done" and j["repos"][0]["status"] == "done"

        d = call("/api/calibration")[1]
        assert d["result"]["totals"]["ok"] == 1 and d["snapshots"][0]["id"] == j["run_id"]
        assert call(f"/api/calibration/{j['run_id']}")[0] == 200
        assert call("/api/calibration/../x")[0] == 404
        assert call("/api/projects")[1] == []  # the calibration run is not a project
    finally:
        httpd.shutdown()
        httpd.server_close()
