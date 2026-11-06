# Decision 3: Capabilities as a markdown checklist with three priorities and a critical gate

Date: 2026-11-06 · Status: accepted

## Context

The first version used numeric weights per check. People could not tell why an aspect scored 71 or how to change
what matters. A weighted mean also let many minor passes hide one fundamental gap, such as "no tests in CI".

## Decision

- Capabilities live in markdown: `- [check.id] priority: text` for scanner-checked items, and `- [ ] priority: text`
  for items judged by a reviewer (`docs/reviewer-verdicts.md`).
- There are exactly three priorities: `critical` (5), `important` (3) and `nice` (1).
- **Critical gate**: an aspect with an unmet critical capability is capped at 49, and one with a partially met
  critical capability at 74.
- A repository may override the default with `.sdlc360/capabilities.md`.

## Consequences

- The checklist is the contract that people edit. The scanner implements it.
- Every capability in the default checklist is justified in `assessment/acceptance-criteria/`: either by an external
  source (`assessment/references/`) or, explicitly, as a team convention.
- Team-only practices (such as writing outputs to `runs/<timestamp>_<name>/`) are not in the default checklist.
  A team that wants them adds a custom `- [ ]` line to its repository's `.sdlc360/capabilities.md`.
