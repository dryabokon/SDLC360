"""Registry of assessment dimensions (order = order on the radar chart)."""

from . import architecture, cicd, cost, documentation, harness, hygiene, runs, security, skills, tests

DIMENSIONS = [
    security.DIMENSION,
    harness.DIMENSION,
    skills.DIMENSION,
    documentation.DIMENSION,
    architecture.DIMENSION,
    tests.DIMENSION,
    cicd.DIMENSION,
    runs.DIMENSION,
    cost.DIMENSION,
    hygiene.DIMENSION,
]
