"""Tests: existence, proportion, tooling, coverage and execution in CI."""

from __future__ import annotations

import re

from ..model import Checks, Dimension, ratio, short
from ..repo import Repo

TEST_CMD = r"pytest|python -m unittest|tox|nox|npm (run )?test|pnpm (run )?test|yarn test|jest|vitest|mocha|go test|cargo test|cargo nextest|mvn (-\S+ )*(test|verify)|gradlew? (test|check)|dotnet test|rspec|phpunit|make test|just test|uv run pytest|bun test|ctest"


def assess(repo: Repo):
    c = Checks()
    tests, src = repo.test_files, repo.source_files
    c.add(
        "test.present",
        "Automated tests exist",
        3,
        min(1.0, len(tests) / 5),
        f"{len(tests)} test files",
        "Add a test suite (unit tests for core logic first).",
    )
    r = ratio(len(tests), len(src))
    c.add(
        "test.ratio",
        "Test-to-source file ratio",
        2,
        min(1.0, r / 0.4) if src else None,
        f"{len(tests)} test / {len(src)} source files (ratio {r:.2f}; target ≥ 0.4)",
        "Grow tests alongside features; aim for at least one test module per core module.",
    )

    cfg = repo.find(
        "pytest.ini",
        "conftest.py",
        "tox.ini",
        "noxfile.py",
        "jest.config.*",
        "vitest.config.*",
        "karma.conf.*",
        "playwright.config.*",
        "cypress.config.*",
        ".mocharc*",
        "phpunit.xml*",
        "*.runsettings",
    )
    pp = repo.read("pyproject.toml")
    if "[tool.pytest" in pp:
        cfg.append("pyproject.toml [tool.pytest]")
    pkg = repo.read("package.json")
    if re.search(r'"test"\s*:', pkg):
        cfg.append("package.json scripts.test")
    if any(f.endswith("_test.go") for f in tests) or (repo.exists("Cargo.toml") and tests):
        cfg.append("built-in test runner")
    c.add(
        "test.framework",
        "Test framework configured",
        1,
        bool(cfg) if tests else 0.0,
        short(cfg),
        "Configure the runner explicitly (pyproject [tool.pytest.ini_options], vitest.config, …).",
    )

    cov_files = repo.find(".coveragerc", "codecov.yml", ".codecov.yml", "coverage.config.*", ".nycrc*", "jacoco*", "tarpaulin.toml")
    cov_txt = re.findall(
        r"--cov\b|coverage run|coverageThreshold|fail_under|--coverage|cover-?profile|jacoco|tarpaulin|codecov|coveralls|llvm-cov",
        pp + pkg + repo.ci_text + "\n".join(repo.read(f) for f in repo.find("Makefile", "justfile")),
        re.I,
    )
    threshold = re.search(
        r"fail_under|fail-under|coverageThreshold|--cov-fail-under|minimum_coverage",
        pp + pkg + repo.ci_text + "\n".join(repo.read(f) for f in cov_files),
        re.I,
    )
    c.add(
        "test.coverage",
        "Coverage measured (and gated)",
        2,
        (0.6 if (cov_files or cov_txt) else 0.0) + (0.4 if threshold else 0.0),
        [f"coverage config: {short(cov_files) if cov_files else ('inline' if cov_txt else 'none')}", f"threshold enforced: {bool(threshold)}"],
        "Measure coverage in CI and enforce a floor (e.g. `--cov-fail-under=80`).",
    )

    in_ci = [m.group(0) for m in re.finditer(TEST_CMD, repo.ci_text, re.I)]
    other_ci = repo.find(".gitlab-ci.yml", "Jenkinsfile", "azure-pipelines.yml", ".circleci/config.yml")
    c.add(
        "test.ci",
        "Tests run in CI",
        3,
        1.0 if in_ci else (0.5 if other_ci else 0.0),
        f"test commands in workflows: {', '.join(sorted(set(x.strip() for x in in_ci))) or 'none'}",
        "Run the full test suite on every push and pull request.",
    )

    kinds = {
        "integration": r"integration",
        "e2e": r"e2e|end.to.end|playwright|cypress|selenium",
        "property/fuzz": r"hypothesis|fast-check|proptest|quickcheck|fuzz",
    }
    blob = " ".join(tests).lower() + " " + pp.lower() + pkg.lower()
    have = [k for k, p in kinds.items() if re.search(p, blob)]
    c.add(
        "test.layers",
        "Multiple test layers (integration / e2e / property)",
        1,
        len(have) / 2 if tests else 0.0,
        f"layers detected: {', '.join(have) or 'unit only'}",
        "Add integration or e2e tests for critical user paths.",
    )
    return c.items


DIMENSION = Dimension("tests", "Tests", "Test presence, ratio, tooling, coverage gates, CI execution and test layers.", assess)
