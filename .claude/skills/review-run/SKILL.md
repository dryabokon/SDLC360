---
name: review-run
description: Act as the SDLC360 reviewer, judging the checklist's own "- [ ]" expectations of a run and writing review.json with evidence. Use when a report shows "Awaiting review" items, or the user asks to review or verify an assessment.
---

# Review a run

Scanner rules judge `- [check.id]` items. Items written as `- [ ] priority: text` need a reviewer. The reviewer
must work from evidence in the repository at the assessed commit.

1. Open `runs/<id>/report.json`. Collect the checks with `status == "review"`; their ids look like
   `custom.<aspect>.<slug>`. Note `repo.head.sha` and `manifest.json → resolved_path`.
2. For each expectation:
   - Write down the acceptance criterion first ("met when ..."), then look for evidence in the repo at that commit:
     files, config, CI, git history.
   - Pick a verdict: `met`, `partial`, `unmet`, or `na` (does not apply to this project).
   - Note concrete evidence (`path:line`, command and output). No evidence means `unmet`, not `met`.
3. Write `runs/<id>/review.json` in the format of [docs/review.md](../../../docs/review.md). Add `dimensions.<id>.adjust`
   only when an automated score is clearly wrong, and always with a note.
4. Re-render and check the result: `python sdlc.py render runs/<id>`.

Do not change scanner verdicts by editing `report.json`. Disagreements with a scanner rule become an issue or
a fix through the `calibrate-check` skill.
