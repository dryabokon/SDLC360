# Agent instructions

Rules for any coding agent (Claude Code, Codex, ...) working in this repository. Keep this file short and current:
point to the docs instead of copying them, and fix a rule here the moment it goes stale. Task-shaped know-how lives
in `.claude/skills/<name>/SKILL.md`.

## What this is

SDLC360 scans a git repository (GitHub or local) and assesses ten aspects of its engineering maturity against a
markdown checklist of expectations. Output: a run folder in `runs/` with `report.html`. Stdlib-only Python 3.12.
Read `README.md` first, then `docs/architecture.md`.

## Commands

- run the app: `./start.sh` / `./stop.sh` (http://127.0.0.1:8360/)
- scan: `python sdlc.py scan <url|owner/repo|path> [--no-history]`
- tests: `.venv/Scripts/python -m pytest --cov` (Linux/macOS: `.venv/bin/...`)
- lint, format, types: `.venv/Scripts/ruff check .`, `.venv/Scripts/ruff format .`, `.venv/Scripts/mypy`
- setup: `python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt && .venv/Scripts/pre-commit install`

## Layout

- `sdlc.py`: CLI entry point; `src/cli.py` defines the commands.
- `src/dimensions/<aspect>.py`: scanner rules. A check id (`sec.no_secrets`) must also appear in
  `src/methods.py` (how it is checked, when it is met) and usually in `checklists/default.md`.
- `src/scanner.py`: `scan()` produces raw `auto_checks`; `finalize()` applies checklist, review and the critical gate.
  `finalize()` must stay idempotent: re-rendering a run never re-scans.
- `src/runner.py`: one scan = one run folder; `src/serve.py`: local web app; `src/template.html`: the whole UI.
- `tests/unit`, `tests/integration`: the integration fixtures are real throw-away git repos (`tests/conftest.py`).

## Conventions

- You must not add runtime dependencies: stdlib only (`docs/adr/0001-stdlib-only.md`). Dev tools go in
  `requirements-dev.txt`, pinned with `==`.
- You must never write into a scanned local repository: read files in place, use `git clone --shared` for history.
- A changed heuristic needs a test. A fixed false positive gets a regression test in `tests/unit/test_heuristics.py`.
- Thresholds, scores and ranking are computed in Python. The template only renders them.
- Scores are shown as verdicts with evidence. Do not add fractional weights to checks that are not in the checklist.
- Never commit `.env`, `runs/*` or `.cache/`. Test secrets are assembled at runtime (`"AKIA" + "..."`).
- Before finishing: ruff, mypy and pytest are green; README / docs / this file are updated if behaviour changed.
