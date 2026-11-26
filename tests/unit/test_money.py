"""Where the money went: every dollar counted once, the losses explained, the lever named."""

import pytest

from src import agent_usage


def _s(sid, cost, commits, steps, read, hours=1.0, out=1000):
    reads = [[1_700_000_000 + i, read] for i in range(steps)]
    return {
        "id": sid,
        "start": "2026-10-12T09:00:00+00:00",
        "end": "2026-10-12T12:00:00+00:00",
        "cost": cost,
        "commits": commits,
        "api_calls": steps,
        "active_hours": hours,
        "context_per_call": read,
        "reads": reads,
        "tokens": {"input": 10 * steps, "output": out * steps, "cache_read": (read - 10) * steps, "cache_write": 0},
    }


def _tl(*costs):
    return {"commits": [{"sha": f"c{i}", "subject": f"change {i}", "cost": c, "cost_x": 2.0} for i, c in enumerate(costs)]}


def test_parts_add_up_and_name_the_long_sessions():
    sessions = [
        _s("short", 1.0, 1, 10, 60_000, hours=0.5),  # sets what a step reads in a short session
        _s("long", 60.0, 10, 400, 350_000, hours=7.5),
        _s("idle", 2.0, 0, 20, 60_000, hours=0.3),
    ]
    m = agent_usage.money(sessions, [{"sha": "c0", "session": "long"}], _tl(15.0, 3.0))
    assert m and m["base_context"] == 60_000
    by = {p["id"]: p for p in m["parts"]}
    assert sum(p["amount"] for p in m["parts"]) == pytest.approx(63.0, abs=0.02)
    assert by["idle"]["amount"] == 2.0
    assert 0 < by["context"]["amount"] < 60.0  # a share of the long session, never more than it cost
    assert "7.5 active hours, 10 commits" in by["context"]["where"][0]
    assert m["lever"].startswith("The biggest lever here: shorter sessions")
    assert m["changes"][0]["cost"] == 15.0 and "made in a long session" in m["changes"][0]["why"]
    assert by["context"]["rule"] == "agent.lean_context" and by["idle"]["rule"] == "agent.lands"


def test_no_loss_says_so():
    m = agent_usage.money([_s("a", 3.0, 2, 10, 50_000, hours=0.5)], [], _tl(1.5))
    assert [p["id"] for p in m["parts"]] == ["work"]
    assert m["lever"] == "No big loss: the money went into the work."


def test_nothing_costed_no_card():
    s = _s("a", None, 1, 10, 50_000)
    assert agent_usage.money([s], [], _tl()) is None


def test_three_checks_in_the_aspect_format():
    sessions = [_s("short", 1.0, 1, 10, 60_000, hours=0.5), _s("long", 60.0, 10, 400, 350_000, hours=7.5), _s("idle", 2.0, 0, 20, 60_000, hours=0.3)]
    m = agent_usage.money(sessions, [{"sha": "c0", "session": "long"}], _tl(15.0))
    work, reread, idle = agent_usage.money_checks(m)
    assert (work["id"], reread["id"], idle["id"]) == ("agent.cost_in_work", "agent.cost_reread", "agent.cost_no_commit")
    assert reread["status"] == "fail" and reread["recommendation"].startswith("One task, one session")
    assert reread["evidence"][0].endswith("dollars of the cost went on re-reading long conversations")
    assert idle["status"] == "pass" and idle["recommendation"] == ""  # $2 of $63: little
    assert m["lead"].startswith("about ") and "re-reading long conversations" in m["lead"]
    assert all(c["method"]["accepted"] and c["method"]["looks_at"] and c["method"]["convention"] for c in (work, reread, idle))


def test_checks_without_cost_are_not_applicable():
    checks = agent_usage.money_checks(None)
    assert [c["status"] for c in checks] == ["na"] * 3
    assert all(c["method"]["accepted"] for c in checks)
