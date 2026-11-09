# Changelog

## Unreleased

- New header: a black brand bar with the SDLC 360° mark, **Projects** and **Criteria** buttons and the theme switch
  on the right; below it, the open project with its source, commit, date and criteria. The Assessment / Capabilities
  tabs are gone: the assessment is the main view, and the settings are the **Criteria** page (`#criteria`;
  `#capabilities` still works).

- **Nine aspects of equal weight**: Docs & Architecture (merged), AI Harness, Skills, **Code Review** (new), Tests,
  Code Quality, CI/CD (now with one-command setup and pinned toolchains), Security & Secrets (now with the lockfile),
  LLM Usage & Cost. Architecture and Reproducibility are no longer aspects of their own.
- A check's aspect is its section in `assessment/capabilities.md`, not the module of its rule; older runs are
  regrouped the same way when opened.
- New checks: changes reach main through pull requests, changes are small (median files per change), an AI usage
  policy is written down, agent-written commits are attributed. CODEOWNERS and PR templates moved to Code Review.
- Removed: cloud cost controls, CI-minute cost (a duplicate of CI speed), provenance of results and seeded randomness
  (ML-specific; candidates for an ML profile).

- A capability's details are shorter: **How we check** (with "Not seen:" for blind spots and known flaws) and
  **Why it matters**. "Partially met" is explained in the verdict, only when it applies.
- A quote links to our own reference card (publisher, date, licence, retrieval date, the copy we keep and its
  SHA-256, key points) instead of the publisher's page, which may move. Reports embed the cards they cite.
- The overview shows the radar and the aspect scores only ("Where to start" and "What is going well" are gone).
- An open capability reads as three rows, **Expected**, **Found** and **What to do**, styled like the folded details. Criticality, status and
  percentage are shown only in the list on the left. **Accepted when** moved into the folded details. The detail
  panel is wider.
- Older runs list their aspects in the current order and under the current names, like the Criteria page. Their
  "Runs & Reproducibility" aspect (before 0.4) is shown as today's Reproducibility, its `run.*` checks as `rep.*`.
- `start.sh` / `stop.sh` work from WSL when the server runs on the Windows interpreter, and print the address at once.

## 0.5.0 (2026-11-06)

- Two tabs: **Assessment** and **Capabilities**, with the same layout. Recommendations, Dynamics and How it works are
  gone for now.
- Recommendations live in the Assessment: the overview says where to start and what is going well; an open
  capability shows what to do right in its row and its card, a met one gets a short acknowledgement.
- Every capability has one plain **Accepted when** sentence; its numbers are the thresholds and are edited inline in
  the Capabilities tab. The technical details are folded away.
- Thresholds now are the acceptance numbers themselves (`min_words` 340 instead of a "target" of 400), so the
  sentence and the verdict agree exactly.
- Scans from the app and `scan` without `--history` no longer re-score past commits.
- Open runs are re-judged in memory when loaded, so they show the current texts.

## 0.4.0 (2026-11-06)

- **Capabilities** instead of "expectations": the catalog is `assessment/capabilities.md`.
- **Profiles**, edited in the new **Capabilities** tab: switch capabilities off, change priorities, set thresholds,
  add your own capabilities with "met when" in plain words. Saved as `assessment/profiles/<name>.json`; *Standard* is
  the read-only baseline, *Prototype* a relaxed example. **Apply to this run** re-judges the open run at once.
- Thresholds of twelve rules (README length, docs pages, docstring share, test files, test ratio, file size, root
  files, diagrams, decision records, freshness of docs and architecture, size for boundary tooling) are parameters.
  The acceptance texts quote the numbers in force. A changed threshold is flagged until the project is re-assessed.
- `scan --profile`, `render --profile`; the manifest records the profile and the `reproduce` command includes it.
- `review.json` uses the key `capabilities` (`expectations` is still read).

## 0.3.0 (2026-11-06)

- Everything a person edits is in one folder, `assessment/`, with a guide: `expectations.md` (was
  `checklists/default.md`), `acceptance-criteria/` with one file per aspect (was one 790-line
  `checklists/acceptance.md`) and `references/` (was `docs/sources/`).
- Acceptance criteria are easier to read and edit: plain paragraphs and bullets, quotes as markdown quotes, and
  references named by their folder (`nist-ssdf`) instead of `S09`. A test keeps headings equal to the expectations.
- Fewer files in the root: `CONTRIBUTING.md` and `SECURITY.md` moved to `.github/`, `CLAUDE.md` to `.claude/`,
  the changelog to `docs/changelog.md`. `docs/adr/` became `docs/design-decisions/`, `docs/review.md` became
  `docs/reviewer-verdicts.md`.
- `doc.standard_files` also accepts a changelog in `docs/`.
- CI now runs on changes to `assessment/*.md` (they were skipped as documentation).

## 0.2.0 (2026-11-06)

- Every expectation is justified: `checklists/acceptance.md` says how it is judged (met / partially / not met,
  limits, known gaps) and quotes published guidance verbatim, or says it is our convention. 13 sources in
  `docs/sources/` with licences, dates and checksums.
- Runs & Reproducibility became **Reproducibility**: no expectation about a `runs/` folder any more; lockfiles,
  pinned toolchains, entry points, documented reproduction, provenance and seeds instead. pydantic-ai: 86.9 → 91.1.
- Aspects ordered as a project is built: architecture, docs, harness, skills, hygiene, tests, security,
  reproducibility, CI/CD, cost.
- New top-level tab **How it works**: components, the user journey, where to change what, scoring rules, sources.
- The detail panel shows "Partially met when", "Limits", "Known gap" and "Basis".
- README rewritten for readers who are not engineers; technical reference moved to `docs/usage.md`.
- Fixes: one workflow satisfies `ci.present`; every YAML form of the `pull_request` trigger counts;
  `CLAUDE.local.md` no longer counts as project instructions.

## 0.1.0 (2026-11-06)

- Ten-aspect scanner with a markdown checklist of expectations, three priorities and a critical gate.
- Run folders with manifest, report, HTML dashboard and log. `render` re-applies the checklist and review without re-scanning.
- Web app (`start.sh` / `stop.sh`): project picker, folder picker, scan jobs, Assessment / Recommendations / Dynamics.
- Dynamics: weekly velocity and re-scored past commits.
- Local server accepts only local `Host` / `Origin`. A failed scan leaves a `status: failed` manifest.
- Tests (unit + integration on real fixture repos), CI on Linux and Windows, pre-commit, design decision records.
