# Usage reference

The README explains what SDLC360 is for. This page has the details: commands, run folders, configuration, tests.

## Requirements

Python 3.12+ and git. The tool itself uses only the standard library.

## Web app

```bash
./start.sh --open      # http://127.0.0.1:8360/ in the background; log in .cache/server.log
./stop.sh              # stop it (a scan in progress is interrupted; finished runs stay)
PORT=8361 ./start.sh   # another port
```

Pick a project in the header, or enter a GitHub URL / `owner/repo` / choose a local folder and press **Scan**.

## Command line

```bash
python sdlc.py scan https://github.com/encode/httpx --open   # or owner/repo, or D:/path/to/repo
python sdlc.py scan owner/repo --history 8 --months 12       # also re-score 8 past commits (stored, not shown yet)
python sdlc.py scan owner/repo --profile prototype          # another profile (assessment/profiles/)
python sdlc.py list                                          # projects and their runs
python sdlc.py render runs/<run-id> --profile <name>         # re-apply a profile / acceptance / review.json, no re-scan
python sdlc.py serve --port 8360 --open                      # the web app in the foreground
```

## What a scan does

1. **Resolve the target.** GitHub repositories are cloned blobless into `.cache/repos/`. Local folders are read in
   place and never written to; for history a throw-away `git clone --shared` is used.
2. **Run the scanner rules** of the ten aspects on the current commit. Each rule records a score 0–1, the evidence
   it found and a recommendation.
3. **Apply the profile** (`--profile`, default *Standard*; a repository may bring `.sdlc360/capabilities.md`):
   which capabilities count, their priority (`critical` / `important` / `nice`) and the thresholds the rules use.
   An unmet critical capability caps its aspect at 49, a partially met one at 74.
4. **History** (only with `--history N`): re-score a sample of past commits and compute weekly velocity. The data is
   kept in the run for a trend view that the app does not show for now.
5. **Write a run folder** and render a self-contained HTML report.

## Run folders

Every scan writes `runs/<UTC yyyymmdd-HHMMSS>_<name>/`:

| File | Content |
|---|---|
| `manifest.json` | status, target, assessed commit, options, checklist path, tool version and git SHA, `reproduce` command |
| `report.json` | raw scanner output (`auto_checks`) plus the final, checklist-applied scores |
| `report.html` | the dashboard; opens offline |
| `scan.log` | what was scanned and how long each aspect took |
| `review.json` | optional reviewer verdicts for your own capabilities ([format](reviewer-verdicts.md)) |

To reproduce a run, execute its `manifest.json → reproduce` command with the tool at `manifest.json → tool.git_sha`.
A failed scan still leaves a manifest with `"status": "failed"` and the error.

This is how SDLC360 itself keeps its results reproducible. It is our convention: the assessment does not expect
other repositories to have a `runs/` folder.

## Configuration

| What | Where |
|---|---|
| Capabilities on / off, priorities, thresholds, your own capabilities | the **Capabilities** tab, saved as `assessment/profiles/<name>.json`; the catalog is `assessment/capabilities.md` |
| How each capability is judged | `assessment/acceptance-criteria/` (texts) and `src/dimensions/<aspect>.py` (rules) |
| Published basis | `assessment/references/` ([index](../assessment/references/README.md)); `python assessment/references/fetch.py` restores local copies |
| Reviewer verdicts | `runs/<id>/review.json` ([format](reviewer-verdicts.md)) |
| Secrets | `.env` (git-ignored, template `.env.example`) holds `GH_PAT` for maintainers only; scans need no secrets |

## Testing

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt   # .venv/bin/pip on Linux/macOS
.venv/Scripts/python -m pytest --cov            # unit + integration, coverage floor in pyproject.toml
.venv/Scripts/ruff check . && .venv/Scripts/ruff format --check . && .venv/Scripts/mypy
```

Integration tests build small real git repositories (a "mature" and a "bare" fixture) and assert the verdicts of
key checks. Every calibration fix gets a regression test in `tests/unit/test_heuristics.py`. The checklist,
acceptance criteria and sources are cross-checked by `tests/unit/test_checklist.py`.
