# Reviewer verdicts (`review.json`)

Scanner rules cover the `- [check.id]` expectations. Your own expectations (`- [ ] priority: text`) show as
**Awaiting review** until a reviewer records a verdict. The reviewer can be a person or an agent (see the
`review-run` skill).

Put `review.json` into the run folder and re-render:

```bash
python sdlc.py render runs/<run-id>            # picks up runs/<run-id>/review.json
python sdlc.py render runs/<run-id> --review path/to/review.json
```

## Format

```json
{
  "reviewer": "name or agent id",
  "expectations": {
    "custom.security.keys-rotate-quarterly": {
      "status": "met | partial | unmet | na",
      "criteria": "what had to be true for 'met'",
      "note": "evidence: file:line, command output, link",
      "recommendation": "what to do if not met"
    }
  },
  "dimensions": {
    "security": { "adjust": -5, "notes": ["why the automated score is off"] }
  }
}
```

- Ids of custom expectations are `custom.<aspect>.<slug of the text>`. The run's `report.json → dimensions[].checks[].id`
  lists them.
- `adjust` is clamped to ±20 and is shown in the UI next to the notes. Use it rarely, and always with a note.
- Verdicts without `note` evidence should not be trusted. The UI shows the note as "Found".
