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
python sdlc.py scan D:/path/to/repo --ref origin/feature-x  # another branch (default: the main branch, see below)
python sdlc.py scan D:/path/to/repo --ref working-copy      # the folder as it is now, uncommitted changes included
python sdlc.py scan D:/path/to/repo --forge azure           # name Azure DevOps settings in the steps (default: from the remote)
python sdlc.py list                                          # projects and their runs
python sdlc.py render runs/<run-id> --profile <name>         # re-apply a profile / acceptance / review.json, no re-scan
python sdlc.py handoff <run-id> --list                       # open findings in the order to fix them
python sdlc.py handoff <run-id> --check hyg.lint             # the prompt for a coding agent to fix one (or skill:<name>)
python sdlc.py serve --port 8360 --open                      # the web app in the foreground
```

`handoff` prints a prompt for a coding agent working in the assessed repository, built from the run alone. It carries
the finding's Expected, Found and What to do, asks the agent to check the finding against the code first (the scanner
can be wrong), make one small change in one commit, and name the scan that re-checks it. The order is broken or
behind skills first, then the ranked actions, then idle skills. Without `--check` it prints the first `--top` (5). In
the app, every open check and every broken, behind or idle skill has **Copy prompt for an agent** under What to do.

**Which commit a local folder is assessed at.** Not the branch that happens to be checked out. A local folder is assessed
at its main branch as it last fetched it: the most recently updated of `origin/HEAD`, `origin/main`, `origin/master` and
`origin/develop`. `origin/HEAD` alone misleads, because it is set when the folder is cloned and never follows the
server. A gitflow project has `main` from months ago and its work on `develop`. Without remote branches, the same rule
applies to the local ones. The scan reads a throw-away `git clone --shared` at that commit, so the folder and its `.git`
are never touched, and nothing is fetched. The report header names the branch and the commit. It also warns when the
folder last fetched more than 7 days ago (`git fetch` in the folder brings the newest commits). In the app, the scan form
offers the folder's branches, with the main branch preselected.

**Steps for the platform the project lives on.** Recommendations name GitHub, GitLab or Azure DevOps settings and files,
as the folder's remote says (`dev.azure.com` is Azure DevOps). Without a remote, the CI files decide. `--forge`
overrides it, for example for a mirror on two platforms.

## What a scan does

1. **Resolve the target.** GitHub repositories are cloned blobless into `.cache/repos/`. Local folders are read in
   place and never written to; for history a throw-away `git clone --shared` is used.
2. **Run the scanner rules** of the nine aspects on the current commit. Each rule records a score 0–1, the evidence
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
| Capabilities on / off, priorities, thresholds, your own capabilities | the **Criteria** page, saved as `assessment/profiles/<name>.json`; the catalog is `assessment/capabilities.md` |
| How each capability is judged | `assessment/acceptance-criteria/` (texts) and `src/dimensions/*.py` (rules) |
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
