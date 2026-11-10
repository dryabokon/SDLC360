# Calibration on reference repositories

Well-run open-source projects serve as a sanity check for the scanner rules. When a strong project fails a
check, either the project really lacks the practice or the rule is wrong. Each rule fix gets a regression test in
`tests/unit/test_heuristics.py`.

## Running a calibration

Open the Overview of the **Criteria** page and press the refresh button, or run `python sdlc.py calibrate`. The reference set is
`assessment/calibration/reference-set.json` (read-only) plus the repositories added in the app
(`assessment/calibration/custom.json`). Each repository is assessed at its latest commit with the Standard criteria,
as a normal run, and the calibration saves one snapshot of every verdict in `runs/calibrations/<id>.json` together
with the scanner version and the commit of each repository. The page shows what was assessed, by which scanner, what
was recorded and how each check split across the set, and compares the snapshot with the previous one. A verdict
that changed on the same commit was changed by the scanner; one on a newer commit may have been changed by the project.

GitHub repositories are pinned: a calibration assesses the commits in `assessment/calibration/pins.json`, so two
calibrations differ only where the rules changed. The refresh button in the app (`python sdlc.py calibrate --latest`)
assesses the latest commits and moves the pins there; commit `pins.json` with it. To recheck a rule change on the
same commits, run `python sdlc.py calibrate` without `--latest`. A repository added to the set is
pinned at its first calibration. A local folder is read as it is and cannot be pinned. Calibration runs are opened
from the matrix and are not listed under the projects.

## Reference set (2026-11-09)

Nine aspects, Standard criteria, pinned commits (`assessment/calibration/pins.json`). Calibrating again at the same
commits on the same day reproduced every one of the 593 verdicts.

| Repository | Kind | Commit | Overall |
|---|---|---|---|
| pydantic/pydantic-ai | agentic | `6e6aa81f` | 91.9 (A) |
| openai/openai-agents-python | agentic | `1fc77bbc` | 80.9 (B) |
| modelcontextprotocol/python-sdk | agentic | `77001c96` | 80.6 (B) |
| anthropics/claude-agent-sdk-python | agentic | `2209f2c1` | 70.1 (C) |
| huggingface/smolagents | agentic | `96f33faa` | 65.3 (C) |
| fastapi/typer | library | `00381d6c` | 61.9 (D) |
| fastapi/full-stack-fastapi-template | template | `aabb9012` | 59.6 (D) |
| Textualize/rich | library | `3a109ccd` | 56.2 (D) |
| encode/httpx | library | `b5addb64` | 54.8 (D) |

Seven checks are met by none of the nine (among them `arch.adr` and `ai.mcp`), fifteen by all of them. A check that
no reference repository meets is not wrong by that fact alone: open the evidence of a few before changing it.

## False positives fixed during calibration

- A `CLAUDE.md` that is a git symlink to `AGENTS.md`, or a thin `@AGENTS.md` import, now counts as an instruction file.
- Tests run through `scripts/test`, `Makefile`, `noxfile`, `tox` or `package.json` scripts now count as tests in CI.
- `tests/fixtures/.netrc` and other fixtures no longer count as committed credentials.
- The word "anthropic" in a path no longer counts as LLM usage; only imports and dependency declarations do.
- Cost is N/A for projects without LLM or infrastructure-as-code resources.
- `.github/` scripts are no longer counted as product source.
- `*AGENTS.md` no longer matches `elevenlabs_agents.md`; only exact instruction-file names match.
- `.agents/skills` is recognised as a skills location.
- Identifiers such as `oauth_client_secret` are no longer taken for secret values.
- Absolute paths in docs (`/opt/...`) are no longer reported as broken links.

## False negatives found by scanning SDLC360 itself

- A flow-style tag trigger (`tags: ["v*"]`) is now recognised as a release trigger.
- Pinned `requirements-*.txt` variants (for example `requirements-dev.txt`) now count as a lockfile.
