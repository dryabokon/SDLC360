# Agent instructions

Rules for any coding agent (Claude Code, Codex, ...) working in this repository. Keep this file short and current:
point to the docs instead of copying them, and fix a rule here the moment it goes stale. Task-shaped know-how lives
in `.claude/skills/<name>/SKILL.md`.

## What this is

SDLC360 scans a git repository (GitHub or local) and assesses nine aspects of its engineering maturity against a
markdown checklist of capabilities. Output: a run folder in `runs/` with `report.html`. Stdlib-only Python 3.12.
Read `README.md` first, then `docs/architecture.md`.

## Commands

- run the app: `./start.sh` / `./stop.sh` (http://127.0.0.1:8360/)
- scan: `python sdlc.py scan <url|owner/repo|path> [--no-history]`
- calibrate: `python sdlc.py calibrate [--latest]` (as **Run calibration** in the app: pinned commits; writes `runs/calibrations/<id>.json`)
- tests: `.venv/Scripts/python -m pytest --cov` (Linux/macOS: `.venv/bin/...`)
- lint, format, types: `.venv/Scripts/ruff check .`, `.venv/Scripts/ruff format .`, `.venv/Scripts/mypy`
- setup: `python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt && .venv/Scripts/pre-commit install`

## Layout

- `sdlc.py`: CLI entry point; `src/cli.py` defines the commands.
- `assessment/`: defines the assessment, see `assessment/README.md`. `capabilities.md` (catalog, standard priority),
  `profiles/<name>.json` (overrides edited on the Criteria page; `standard` is read-only),
  `acceptance-criteria/<NN-aspect>.md` (how each one is judged, quotes), `references/<name>/` (published basis),
  `calibration/reference-set.json` (default reference repositories, read-only), `calibration/custom.json` (added in the app)
  and `calibration/pins.json` (the commit each one is assessed at).
- `src/profiles.py`: profiles and `PARAMS`, the thresholds a profile may change. A rule reads them with
  `repo.param(check_id, key)`, never a literal; its acceptance text quotes them as `{key}`.
- `src/dimensions/<rules>.py`: scanner rules, grouped by topic. The aspect a check belongs to is its section in
  `assessment/capabilities.md`, not its module (`src/dimensions/__init__.py` lists the aspects). A check id
  (`sec.no_secrets`) must have a block in `assessment/acceptance-criteria/` and usually a line in the catalog.
  Quotes must be verbatim from `assessment/references/`.
- `src/scanner.py`: `scan()` produces raw `auto_checks`; `finalize()` applies checklist, review and the critical gate.
  `finalize()` must stay idempotent: re-rendering a run never re-scans.
- `src/agent_usage.py`: the Agent use tab (prototype): Claude Code session logs (`~/.claude/projects/`, read only)
  joined with `git log`, judged by rules shaped like scanner checks. `serve.py` also keeps Claude Code
  telemetry posted to `/v1/*` in `.cache/telemetry/`.
- `src/runner.py`: one scan = one run folder; `src/serve.py`: local web app; `src/template.html`: the whole UI.
- `tests/unit`, `tests/integration`: the integration fixtures are real throw-away git repos (`tests/conftest.py`).

## Conventions

- You must not add runtime dependencies: stdlib only (`docs/design-decisions/01-standard-library-only.md`). Dev tools go in
  `requirements-dev.txt`, pinned with `==`.
- You must never write into a scanned local repository: read files in place, use `git clone --shared` for history.
- A changed heuristic needs a test. A fixed false positive gets a regression test in `tests/unit/test_heuristics.py`.
- Thresholds, scores and ranking are computed in Python. The template only renders them.
- Scores are shown as verdicts with evidence. Do not add fractional weights to checks that are not in the checklist.
- Commit without `-q` and end the message with the `Co-Authored-By` trailer: the Agent use tab links sessions to
  commits by them. One finished task, one commit.
- Never commit `.env`, `runs/*` or `.cache/`. Test secrets are assembled at runtime (`"AKIA" + "..."`).
- Before finishing: ruff, mypy and pytest are green; README / docs / this file are updated if behaviour changed.
