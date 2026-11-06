# 0002. One scan = one immutable run folder

Date: 2026-11-06 · Status: accepted

## Context

Assessments must be comparable over time and reproducible: which commit was assessed, by which version of the
tool, with which checklist.

## Decision

Every scan writes `runs/<UTC yyyymmdd-HHMMSS>_<name>/` with `manifest.json` (status, target, assessed commit,
options, checklist path, tool version and git SHA, `reproduce` command), `report.json`, `report.html` and `scan.log`.
The report stores raw scanner output (`auto_checks`) separately from final scores. `render` re-applies the
checklist and review to a run without re-scanning.

## Consequences

- Projects and their history in the web app are just a listing of `runs/`. There is no database.
- A failed scan leaves a manifest with `status: failed` instead of a silent half-written folder.
- `runs/` is git-ignored (outputs, not sources). Only `runs/README.md` is tracked.
