"""Claude Code efficiency in the five areas of the cycle: a new view of the same checks, the score does not change."""

from src import agent_usage


def _c(cid, status, score):
    return {"id": cid, "status": status, "score": score}


def test_every_check_belongs_to_exactly_one_area():
    listed = [c for a in agent_usage.AREAS for c in a["checks"]]
    assert sorted(listed) == sorted(agent_usage.HABITS)


def test_checks_follow_the_cycle_and_areas_count_what_is_in_place():
    given = [
        _c("agent.cost_in_work", "partial", 0.5),
        _c("agent.tests", "fail", 0.0),
        _c("agent.friction", "pass", 1.0),
        _c("agent.lands", "pass", 1.0),
        _c("agent.attributed", "na", None),
    ]
    grouped, areas = agent_usage.by_area(given)
    assert [c["id"] for c in grouped] == ["agent.friction", "agent.cost_in_work", "agent.tests", "agent.lands", "agent.attributed"]
    assert [c["area"] for c in grouped] == ["gather", "action", "verify", "commit", "commit"]
    got = {a["id"]: (a["in_place"], a["assessed"]) for a in areas}
    assert got == {"gather": (1, 1), "action": (0, 1), "verify": (0, 1), "commit": (1, 1), "capture": (0, 0)}


def test_the_score_and_the_first_step_stay_as_they_were():
    session = {
        "id": "s1",
        "start": "2026-10-12T09:00:00+00:00",
        "end": "2026-10-12T10:00:00+00:00",
        "cost": 1.0,
        "api_calls": 10,
        "active_hours": 1.0,
        "span_hours": 1.0,
        "context_per_call": 50_000,
        "reads": [],
        "tokens": {"input": 10, "output": 10, "cache_read": 10, "cache_write": 10},
        "tool_calls": 10,
        "tool_errors": 5,
        "denied": 0,
        "skills": {},
    }
    aspect = agent_usage.report_from([session], [], [])["aspect"]
    plain = agent_usage.money_checks(agent_usage.money([session], [], {"commits": []}))
    assert {c["id"] for c in plain} <= {c["id"] for c in aspect["checks"]}
    scored = [c["score"] for c in aspect["checks"] if c["score"] is not None]
    assert aspect["score"] == round(100 * sum(scored) / len(scored), 1)
    assert [a["id"] for a in aspect["areas"]] == ["gather", "action", "verify", "commit", "capture"]
    assert aspect["start"] in {c["id"] for c in aspect["checks"]}
