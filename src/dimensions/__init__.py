"""Rule sets and the aspects of the report.

A rule set (one module) produces checks; the aspect a check belongs to is its section in assessment/capabilities.md,
so a check can move to another aspect without touching its rule. Order of DIMENSIONS = order of tabs and radar axes.
"""

from ..model import Aspect
from . import architecture, cicd, cost, documentation, harness, hygiene, reproducibility, review, security, skills, tests

RULES = [
    architecture.DIMENSION,
    documentation.DIMENSION,
    harness.DIMENSION,
    skills.DIMENSION,
    review.DIMENSION,
    tests.DIMENSION,
    hygiene.DIMENSION,
    cicd.DIMENSION,
    security.DIMENSION,
    reproducibility.DIMENSION,
    cost.DIMENSION,
]

DIMENSIONS = [
    Aspect("docs", "Docs & Architecture", "README, architecture and design decisions, kept current and linked correctly."),
    Aspect("harness", "AI Harness", "Agent instructions, shared settings, hooks, MCP and agents in CI."),
    Aspect("skills", "Skills", "Repeated agent procedures packaged as well-formed, discoverable skills."),
    Aspect("review", "Code Review", "Pull requests, change size, ownership, AI usage policy and attribution."),
    Aspect("tests", "Tests", "Test suite, growth with the code, coverage, and tests in CI."),
    Aspect("hygiene", "Code Quality", "Linting, formatting, typing, pre-commit and code structure."),
    Aspect("cicd", "CI/CD", "Pull request gates, one-command setup, pinned toolchains, automated releases, CI hygiene."),
    Aspect("security", "Security & Secrets", "No committed secrets, locked and updated dependencies, scanning, least-privilege CI."),
    Aspect("cost", "LLM Usage & Cost", "Token usage and cost tracked and bounded in code that calls LLMs (N/A otherwise)."),
]

# rule sets and aspects of older versions -> the current aspect, for checks that the catalog does not place
# (an assessment error, or a check of an older run)
LEGACY = {"architecture": "docs", "documentation": "docs", "reproducibility": "cicd", "runs": "cicd"}
