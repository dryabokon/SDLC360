"""Timeline: is the project sustainable for Claude Code? Efficiency measures over its commits."""

from datetime import datetime, timedelta

from src import agent_usage

T0 = datetime(2026, 1, 5, 9, 0)


def _iso(minutes: int) -> str:
    return (T0 + timedelta(minutes=minutes)).isoformat()


def _ts(minutes: int) -> float:
    return (T0 + timedelta(minutes=minutes)).timestamp()


def _session(reads: list[tuple[int, int]], prompts: list[int] = (), calls: list[int] = (), errors: list[int] = (), cost: float | None = None) -> dict:
    return {
        "id": "s1",
        "start": _iso(0),
        "end": _iso(10_000),
        "cost": cost,
        "reads": [(_ts(m), r) for m, r in reads],
        "at": {"prompts": [_ts(m) for m in prompts], "calls": [_ts(m) for m in calls], "errors": [_ts(m) for m in errors]},
    }


def _commit(minutes: int, lines: int, session: str | None = "s1", agent: bool = True, subject: str = "s") -> dict:
    return {
        "sha": f"{minutes:08d}" + "0" * 32,
        "date": _iso(minutes),
        "subject": subject,
        "merge": False,
        "agent": agent,
        "code_add": lines,
        "code_lines": lines,
        "code_paths": [],
        "session": session,
    }


def test_a_commit_gets_what_happened_since_the_previous_commit_of_its_session():
    s = _session([(10, 50), (12, 50), (50, 100), (90, 800), (200, 999)], prompts=[5, 70, 80], calls=[11, 12, 91], errors=[12], cost=20.0)
    t = agent_usage.timeline([s], [_commit(100, 2), _commit(60, 40, subject="Fix the thing; and more words")])  # newest first
    second, first = t["commits"]
    assert (first["read"], first["cost"], first["minutes"]) == (200, 2.0, 7.0)  # 2 min, then a 38 min gap counted as 5
    assert second["read"] == 800 and second["minutes"] == 0
    assert first["subject"] == "Fix the thing" and first["full"] == "Fix the thing; and more words"


def _history(late: float) -> list[dict]:
    """Twenty commits alternating 10 and 1,000 lines; effort grows as lines^0.5, times `late` in the second half."""
    reads, commits = [], []
    for i in range(20):
        lines = 10 if i % 2 else 1000
        m = i * 10
        reads += [(m + 1, 1), (m + 5, round(1000 * lines**0.5 * (late if i >= 10 else 1)))]
        commits.insert(0, _commit(m + 9, lines))
    return agent_usage.timeline([_session(reads)], commits)


def test_the_index_compares_changes_of_the_same_size():
    t = _history(1.0)  # the same effort for the same size all along: no trend, however the sizes alternate
    cost = {i["key"]: i for i in t["indices"]}["cost"]
    assert t["window"] == 5 and cost["exponent"] == 0.5 and cost["ratio"] == 1.0 and not cost["clear"]
    assert {p["cost"] for p in t["series"] if p["cost"] is not None} == {100}


def test_a_dearer_change_shows_as_a_clear_rise():
    t = _history(3.0)
    cost = {i["key"]: i for i in t["indices"]}["cost"]
    assert cost["ratio"] > 2 and cost["clear"] and t["series"][-1]["cost"] > 200
    assert max(r["cost_x"] for r in t["commits"]) > 1.5 > min(r["cost_x"] for r in t["commits"])


def test_too_little_history():
    t = agent_usage.timeline([_session([(5, 10)])], [_commit(9, 300)])
    assert len(t["series"]) == 1 and all(i.get("ratio") is None for i in t["indices"])
    assert agent_usage.timeline([], [])["series"] == []
