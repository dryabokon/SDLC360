"""Core data model: checks, dimension results, scoring and grading."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field

from .repo import Repo


@dataclass
class Check:
    id: str
    title: str
    weight: float
    score: float | None  # 0..1, None = not applicable
    evidence: list[str] = field(default_factory=list)
    recommendation: str = ""

    @property
    def status(self) -> str:
        if self.score is None:
            return "na"
        if self.score >= 0.85:
            return "pass"
        if self.score >= 0.35:
            return "partial"
        return "fail"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status
        return d


@dataclass
class DimensionResult:
    id: str
    name: str
    description: str
    checks: list[Check]

    @property
    def score(self) -> float | None:
        applicable = [c for c in self.checks if c.score is not None and c.weight > 0]
        total = sum(c.weight for c in applicable)
        if not total:
            return None
        return round(100 * sum(c.weight * (c.score or 0.0) for c in applicable) / total, 1)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "score": self.score,
            "grade": grade(self.score),
            "checks": [c.to_dict() for c in self.checks],
        }


class Checks:
    """Small builder used by dimension modules."""

    def __init__(self) -> None:
        self.items: list[Check] = []

    def add(self, id: str, title: str, weight: float, score: float | bool | None, evidence: list[str] | str | None = None, rec: str = "") -> Check:
        if isinstance(score, bool):
            score = 1.0 if score else 0.0
        if score is not None:
            score = max(0.0, min(1.0, float(score)))
        ev = [evidence] if isinstance(evidence, str) else list(evidence or [])
        c = Check(id, title, weight, score, ev, rec if (score is None or score < 0.85) else "")
        self.items.append(c)
        return c


@dataclass
class Dimension:
    id: str
    name: str
    description: str
    assess: Callable[[Repo], list[Check]]

    def run(self, repo: Repo) -> DimensionResult:
        return DimensionResult(self.id, self.name, self.description, self.assess(repo))


def grade(score: float | None) -> str:
    if score is None:
        return "N/A"
    for limit, g in ((90, "A"), (80, "B"), (65, "C"), (50, "D")):
        if score >= limit:
            return g
    return "F"


def band(score: float | None) -> str:
    """Status band used for colouring: good / warning / serious / critical."""
    if score is None:
        return "na"
    if score >= 75:
        return "good"
    if score >= 50:
        return "warning"
    if score >= 30:
        return "serious"
    return "critical"


def ratio(n: int, d: int) -> float:
    return n / d if d else 0.0


def short(paths: list[str], n: int = 5) -> str:
    if not paths:
        return "none"
    s = ", ".join(paths[:n])
    return s + (f" (+{len(paths) - n} more)" if len(paths) > n else "")
