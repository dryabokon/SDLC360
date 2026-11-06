# SDLC360

A 360° maturity assessment of any git repository: a GitHub URL / `owner/repo`, or a local folder.
It answers one question per aspect: **does this project meet the expectations we hold for a well-run,
AI-assisted codebase?**, and shows the answer as a checklist with evidence, a radar and a bar chart.

Ten aspects are assessed: Security & Secrets · AI Harness · Skills · Documentation · Architecture ·
Tests · CI/CD · Reproducibility · Cost Management · Code Hygiene.

The assessment is **analytical, not LLM-based**: every expectation is checked by a deterministic scanner rule
over the files and git history at one commit. The same commit always gives the same verdict.

## Quick start

Requirements: Python 3.12+ and git. The tool itself uses only the standard library.

```bash
./start.sh --open      # web app at http://127.0.0.1:8360/ (background; log in .cache/server.log)
./stop.sh              # stop it
```

In the web app pick a project in the header, or enter a GitHub URL / choose a local folder and press **Scan**.

From the command line:

```bash
python sdlc.py scan https://github.com/encode/httpx --open   # or owner/repo, or D:/path/to/repo
python sdlc.py scan . --no-history                           # quick: skip re-scoring past commits
python sdlc.py list                                          # projects and their runs
python sdlc.py render runs/<run-id> --review review.json     # re-apply checklist / reviewer verdicts, no re-scan
```

## Usage: what a scan does

1. **Resolve the target.** GitHub repos are cloned blobless into `.cache/repos/`; local folders are read in place
   and never written to.
2. **Run the scanner rules** of the ten aspects at HEAD. Each rule records a verdict (Met / Partially met /
   Not met / Not applicable) and the evidence it found.
3. **Apply the checklist** (`checklists/default.md`, or the repo's own `.sdlc360/expectations.md`): it decides
   which expectations count and their priority (`critical` / `important` / `nice`). An unmet critical expectation
   caps its aspect at 49, a partially met one at 74.
4. **Dynamics**: re-score a sample of past commits (`--history 8 --months 12`) and compute weekly velocity.
5. **Write a run folder** (see below) and render a self-contained HTML report.

## Runs and reproducibility

This is how SDLC360 *itself* keeps its results reproducible. It is our convention, and the assessment does not
expect other repositories to have a `runs/` folder: the Reproducibility aspect checks lockfiles, pinned toolchains,
entry points, documentation and provenance instead.

Every scan writes `runs/<UTC yyyymmdd-HHMMSS>_<name>/`:

| File | Content |
|---|---|
| `manifest.json` | status, target, assessed commit, options, checklist path, tool version and git SHA, `reproduce` command |
| `report.json` | raw scanner output (`auto_checks`) plus the final, checklist-applied scores |
| `report.html` | the dashboard; opens offline |
| `scan.log` | what was scanned and how long each aspect took |

To reproduce a run, execute its `manifest.json → reproduce` command with the tool at `manifest.json → tool.git_sha`.
A failed scan still leaves a manifest with `"status": "failed"` and the error.

## Configuration

- **Expectations**: edit `checklists/default.md`, or commit `.sdlc360/expectations.md` into the assessed repository.
  Format and gate rules are explained at the top of the default file.
- **Reviewer verdicts** for your own (`- [ ]`) expectations: `review.json` next to the run, see `docs/review.md`.
- **Environment**: `.env` (git-ignored, template in `.env.example`) holds `GH_PAT`. It is used only by maintainers
  for GitHub administration. The scanner itself needs no secrets and clones public repositories anonymously.
- **Port**: `PORT=8361 ./start.sh`.

## Testing

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt   # .venv/bin/pip on Linux/macOS
.venv/Scripts/python -m pytest --cov            # unit + integration, coverage floor in pyproject.toml
.venv/Scripts/ruff check . && .venv/Scripts/ruff format --check . && .venv/Scripts/mypy
```

Integration tests build small real git repositories (a "mature" and a "bare" fixture) and assert the verdicts
of key checks. Every calibration fix (a false positive found on a reference repository) gets a regression test in
`tests/unit/test_heuristics.py`.

## Overview of the code

```
sdlc.py              entry point (CLI)
start.sh / stop.sh   web app in the background
src/                 the tool: repo access, scanner, checklist, history, runner, web server, HTML template
src/dimensions/      one module per aspect; each check returns score + evidence + recommendation
checklists/          expectations (what we want), with priorities
docs/                architecture, decisions (ADRs), reviewer format
tests/               unit and integration tests
runs/                scan outputs (git-ignored except its README)
```

Architecture and the reasoning behind it: [docs/architecture.md](docs/architecture.md) and [docs/adr/](docs/adr/).

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). Agents working in this repository follow [AGENTS.md](AGENTS.md).
