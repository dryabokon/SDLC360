---
name: scan-repo
description: Run an SDLC360 assessment of a GitHub or local repository and summarise the result. Use when the user asks to assess, scan, score or audit a repository, or wants to know what a project lacks.
---

# Scan a repository

1. Resolve the target: a GitHub URL, `owner/repo`, or an absolute local path that is a git repository.
2. Run the scan. A quick scan without history takes seconds. A full scan re-scores 8 past commits and takes up to
   a few minutes on large repositories:

   ```bash
   python sdlc.py scan <target> --no-history     # quick
   python sdlc.py scan <target> --history 8      # also re-score 8 past commits (slower)
   ```

   The last line of output is the run folder `runs/<id>/`.
3. Read `runs/<id>/report.json` and do not scrape the HTML:
   - `overall.score`, `overall.grade`
   - `dimensions[]`: `score`, `capped_by` (critical gate), `checks[]` with `status`, `priority`, `evidence`, `recommendation`
   - `top_actions[]`: ranked fixes
4. Report back in this order: the overall result; the aspects capped by the critical gate and why; the 5 most
   valuable actions with their evidence. Quote evidence from `checks[].evidence` and do not invent it.
5. Point the user to `runs/<id>/report.html`, or to `./start.sh` for the web app.

If the scan fails, read `runs/<id>/scan.log` and `manifest.json` (`status: failed`, `error`).
