import pytest

from src.model import band, grade
from src.scanner import critical_cap, finalize, status_of


@pytest.mark.parametrize(("score", "status"), [(None, "na"), (1.0, "pass"), (0.85, "pass"), (0.84, "partial"), (0.35, "partial"), (0.34, "fail")])
def test_status_thresholds(score, status):
    assert status_of(score) == status


def test_status_pending_review():
    assert status_of(None, pending=True) == "review"


@pytest.mark.parametrize(
    ("score", "g", "b"),
    [(None, "N/A", "na"), (95, "A", "good"), (80, "B", "good"), (70, "C", "warning"), (49, "F", "serious"), (10, "F", "critical")],
)
def test_grade_and_band(score, g, b):
    assert grade(score) == g and band(score) == b


def test_critical_cap_takes_the_strictest():
    checks = [
        {"id": "a", "priority": "critical", "status": "partial"},
        {"id": "b", "priority": "critical", "status": "fail"},
        {"id": "c", "priority": "important", "status": "fail"},
    ]
    assert critical_cap(checks) == (49.0, ["a", "b"])
    assert critical_cap([{"id": "a", "priority": "critical", "status": "pass"}]) == (None, [])


def _report(critical_score: float) -> dict:
    checks = [
        {"id": "x.crit", "title": "c", "weight": 5, "score": critical_score, "evidence": [], "recommendation": "fix"},
        {"id": "x.other", "title": "o", "weight": 3, "score": 1.0, "evidence": [], "recommendation": ""},
    ]
    items = {
        "x": [
            {"id": "x.crit", "text": "Crit", "priority": "critical", "weight": 5.0, "custom": False},
            {"id": "x.other", "text": "Other", "priority": "important", "weight": 3.0, "custom": False},
            {"id": "custom.x.mine", "text": "Mine", "priority": "nice", "weight": 1.0, "custom": True},
        ]
    }
    return {"repo": {"source": "t"}, "checklist": {"items": items}, "dimensions": [{"id": "x", "name": "X", "auto_checks": checks}]}


def test_finalize_applies_gate_and_is_idempotent():
    rep = finalize(_report(0.0))
    d = rep["dimensions"][0]
    assert d["uncapped_score"] == 37.5  # 3 of 8 weighted points; the custom item awaits review and is not scored
    assert d["score"] == 37.5 and d["capped_by"] == []  # already below the cap
    assert [c["status"] for c in d["checks"]] == ["fail", "pass", "review"]
    assert finalize(rep)["dimensions"][0]["score"] == 37.5


def test_finalize_caps_partial_critical_at_74():
    d = finalize(_report(0.8))["dimensions"][0]
    assert d["uncapped_score"] == 87.5 and d["score"] == 74.0 and d["capped_by"] == ["x.crit"]


def test_review_verdicts_and_adjust_are_applied():
    review = {"expectations": {"custom.x.mine": {"status": "met", "note": "seen"}}, "dimensions": {"x": {"adjust": 50, "notes": ["n"]}}}
    d = finalize(_report(1.0), review)["dimensions"][0]
    mine = d["checks"][2]
    assert mine["status"] == "pass" and mine["evidence"] == ["seen"]
    assert d["adjust"] == 20.0  # clamped to +-20
    assert d["score"] == 100.0
