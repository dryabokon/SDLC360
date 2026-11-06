"""Registry of assessment dimensions. Order = order of tabs and radar axes: design -> build -> verify -> deliver -> operate."""

from . import architecture, cicd, cost, documentation, harness, hygiene, reproducibility, security, skills, tests

DIMENSIONS = [
    architecture.DIMENSION,
    documentation.DIMENSION,
    harness.DIMENSION,
    skills.DIMENSION,
    hygiene.DIMENSION,
    tests.DIMENSION,
    security.DIMENSION,
    reproducibility.DIMENSION,
    cicd.DIMENSION,
    cost.DIMENSION,
]
