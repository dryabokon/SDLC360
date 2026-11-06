---
name: calibrate-check
description: Fix a wrong SDLC360 verdict (false positive or false negative) or add a new check, with a regression test. Use when a report marks something Met or Not met incorrectly, or a new expectation needs a scanner rule.
---

# Calibrate or add a check

1. **Reproduce.** Scan the repository where the verdict is wrong (`python sdlc.py scan <target> --no-history`).
   Copy the check's `evidence` from `report.json` and find the exact file or line that misleads the rule.
2. **Write the failing test first.** Use `tests/unit/test_heuristics.py` and build a minimal repo with the
   `make_repo` fixture that has the same shape. Assemble secrets at runtime (`"AKIA" + "..."`).
3. **Fix the rule** in `src/dimensions/<aspect>.py`. Prefer a narrower pattern over a new exception list.
4. **Keep the contract in sync** for a new or renamed check:
   - `assessment/acceptance-criteria/<NN-aspect>.md`: how it is checked, met / partially / not met, what the check
     cannot see, and under **Why we expect it** a verbatim quote from `assessment/references/` (or an
     **Our convention.** paragraph saying why we expect it anyway). Format: `assessment/README.md`;
   - `assessment/expectations.md`: the expectation line with a priority (one or two `critical` items per aspect);
   - `tests/unit/test_checklist.py::test_default_checklist_is_consistent` must stay green.
5. **Check for collateral damage.** Run `pytest`, then re-scan one or two reference repositories from
   [docs/calibration.md](../../../docs/calibration.md) and compare verdicts with the previous run.
6. Add a line to `docs/changelog.md`.
