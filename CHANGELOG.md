# Changelog

## 0.1.0 (2026-11-06)

- Ten-aspect scanner with a markdown checklist of expectations, three priorities and a critical gate.
- Run folders with manifest, report, HTML dashboard and log. `render` re-applies the checklist and review without re-scanning.
- Web app (`start.sh` / `stop.sh`): project picker, folder picker, scan jobs, Assessment / Recommendations / Dynamics.
- Dynamics: weekly velocity and re-scored past commits.
- Local server accepts only local `Host` / `Origin`. A failed scan leaves a `status: failed` manifest.
- Tests (unit + integration on real fixture repos), CI on Linux and Windows, pre-commit, ADRs.
