# Contributing

1. Set up: `python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt && .venv/Scripts/pre-commit install`
   (Linux/macOS: `.venv/bin/...`).
2. Change one thing per pull request. A new or changed check updates `src/dimensions/<aspect>.py`, `src/methods.py`,
   `checklists/default.md` and adds a test.
3. A false positive found on a real repository becomes a regression test in `tests/unit/test_heuristics.py`.
4. Before pushing: `ruff check .`, `ruff format .`, `mypy`, `pytest --cov` must all pass. CI runs the same on Linux and Windows.
5. Record user-visible changes in `CHANGELOG.md` and significant design decisions as an ADR in `docs/adr/`.
