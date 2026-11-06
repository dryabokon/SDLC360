# 0003. Expectations as a markdown checklist with three priorities and a critical gate

Date: 2026-11-06 · Status: accepted

## Context

The first version used numeric weights per check. People could not tell why an aspect scored 71 or how to change
what matters. A weighted mean also let many minor passes hide one fundamental gap, such as "no tests in CI".

## Decision

- Expectations live in markdown: `- [check.id] priority: text` for scanner-checked items, and `- [ ] priority: text`
  for items judged by a reviewer (`docs/review.md`).
- There are exactly three priorities: `critical` (5), `important` (3) and `nice` (1).
- **Critical gate**: an aspect with an unmet critical expectation is capped at 49, and one with a partially met
  critical expectation at 74.
- A repository may override the default with `.sdlc360/expectations.md`.

## Consequences

- The checklist is the contract that people edit. The scanner implements it.
- Some default expectations (`runs/`, skills, cost tracking) are conventions of our team. Libraries that do not
  share them score lower by design. Per-profile checklists (library / service / agentic) are the planned remedy.
