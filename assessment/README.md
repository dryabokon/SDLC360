# Assessment: what we expect and how we judge it

Everything a person edits to change the assessment lives here. The code in `src/` only executes it.

| Folder / file | What it says | Who edits it |
|---|---|---|
| [expectations.md](expectations.md) | **What we expect** from a project: one line per expectation, grouped by aspect, each with a priority (critical / important / nice) | anyone who disagrees with what is expected or how much it matters |
| [acceptance-criteria/](acceptance-criteria/) | **How each expectation is judged**: what is checked, when it is met, partially met or not met, what the check cannot see, and why we expect it. One file per aspect | whoever changes a check, together with its rule in `src/dimensions/<aspect>.py` |
| [references/](references/README.md) | **Why we expect it**: the published guidance (whitepapers, research reports, standards, specifications, engineering articles) that the criteria quote | whoever adds or replaces a reference |

A changed text is applied to an existing run without re-scanning: `python sdlc.py render runs/<run-id>`.
A changed rule in `src/dimensions/` takes effect at the next scan.

## Expectations

```markdown
## security                                          <- aspect
- [sec.no_secrets] critical: No secrets are committed.   <- checked by the scanner rule with this id
- [ ] important: Keys are rotated every quarter.        <- your own expectation, judged by a reviewer
```

- **critical**: without it the aspect is not healthy. Not met caps the aspect at 49, partially met at 74.
- **important**: expected from a mature project. **nice**: a sign of high maturity.
- Delete a line to drop an expectation. A project can bring its own list in `.sdlc360/expectations.md`.

## Acceptance criteria

One block per expectation. The heading repeats the expectation word for word (a test keeps the two in step).

```markdown
## sec.no_secrets: No secrets are committed.

**How we check.** What the scanner looks at, in plain words.

- **Met:** ...
- **Partially met:** ...
- **Not met:** ...
- **Not applicable:** ...              (only if the practice can be irrelevant to a project)

**What the check cannot see.** Honest limits of the rule.

**Known flaw.** Where the rule does not yet check what the expectation says. (optional; remove when fixed)

**Why we expect it.**

> Continuously monitor each environment for plaintext secrets.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218A PO.5.1.R6, p.19 · direct
```

- The citation line names the reference folder, the page or section, and how strong the support is:
  **direct** means the reference asks for this practice, **supporting** means it argues for the goal behind it.
- An expectation without a published basis says so instead of quoting: `**Our convention.** why we expect it anyway.`
- Tests fail when a check has no block, when a block has neither a quote nor a convention, or when a citation names a
  reference that is not in `references/`.
