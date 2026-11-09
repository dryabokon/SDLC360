# Assessment: which capabilities we look for and how we judge them

Everything that defines the assessment lives here. The code in `src/` only executes it.

| Folder / file | What it says | Who changes it, and how |
|---|---|---|
| [profiles/](profiles/) | **Which capabilities count for you**: on / off, priority, thresholds, your own capabilities. `standard.json` is the published baseline, `prototype.json` a relaxed example | anyone, in the **Capabilities** tab of the app (no file editing needed) |
| [capabilities.md](capabilities.md) | **The catalog**: every capability, grouped by aspect, with its standard priority | whoever adds or rewords a scanner rule |
| [acceptance-criteria/](acceptance-criteria/) | **How each capability is judged**: what is checked, when it is met, partially met or not met, what the check cannot see, and why we expect it. One file per aspect | whoever changes a rule in `src/dimensions/<aspect>.py`, in the same pull request |
| [references/](references/README.md) | **Why we expect it**: published guidance (whitepapers, research reports, standards, specifications, engineering articles) that the criteria quote | whoever adds or replaces a reference |

In the app, **Apply to this run** re-judges the open run with a profile at once (on / off, priorities, your own
capabilities). Changed thresholds take effect when the project is re-assessed, because the rules measure with them.
From the command line: `python sdlc.py scan <target> --profile <name>` and `python sdlc.py render runs/<id> --profile <name>`.

## Accepted when

Every capability has one plain sentence that says when it is accepted, for example
"There are at least {min_files} test files." This is what people read in the app, and the numbers in it are what they
change in the **Capabilities** tab. Each `{key}` is a threshold of the rule (listed with its range in
`src/profiles.py → PARAMS`), so the sentence always states the number the verdict is based on. Tests fail when a
sentence and its rule disagree on the thresholds.

Everything else in a block is for readers who want to dig deeper. The app shows it folded away under "How this is
checked, and why it matters", after the Accepted when sentence (in the Assessment; the Capabilities tab keeps that
sentence in view, because it is edited there), in two parts: **How we check** (the rule, then "Not seen:" with the blind spots and any
known flaw) and **Why it matters** (each quote, with the card of its reference). "Partially met" is shown in the
verdict only when that is the verdict; "Not met" and "Not applicable" stay in the file for developers.

## Acceptance criteria

One block per capability. The heading repeats the capability word for word (a test keeps the two in step).

```markdown
## sec.no_secrets: No secrets are committed.

**Accepted when.** No passwords, tokens or API keys are written in the tracked files.

**How we check.** What the scanner looks at, in plain words.

- **Met:** ...
- **Partially met:** ...
- **Not met:** ...
- **Not applicable:** ...              (only if the practice can be irrelevant to a project)

**What the check cannot see.** Honest limits of the rule.

**Known flaw.** Where the rule does not yet check what the capability says. (optional; remove when fixed)

**Why we expect it.**

> Continuously monitor each environment for plaintext secrets.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218A PO.5.1.R6, p.19 · direct
```

- The citation line names the reference folder, the page or section, and how strong the support is:
  **direct** means the reference asks for this practice, **supporting** means it argues for the goal behind it.
- A capability without a published basis says so instead of quoting: `**Our convention.** why we expect it anyway.`
- Tests fail when a check has no block, when a block has neither a quote nor a convention, or when a citation names a
  reference that is not in `references/`.
