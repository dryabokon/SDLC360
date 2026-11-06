---
id: anthropic-claude-code-best-practices
title: Best practices for Claude Code
publisher: Anthropic (Claude Code documentation)
authors: Anthropic
published: living document; version modified 2026-11-04
kind: documentation page
url: https://www.anthropic.com/engineering/claude-code-best-practices
retrieved: 2026-11-06
license: Copyright Anthropic. Kept local only.
files:
  - local best-practices.html db5e114366b896a494bafd09b62693107dd5d082e70323a27a40ed8a172245c2 https://www.anthropic.com/engineering/claude-code-best-practices
---

# Best practices for Claude Code

The URL redirects to the Claude Code docs; the page changes over time, so the checksum is informational.

## Key points

- Put in CLAUDE.md only what Claude cannot find by reading the repo: exact test/typecheck/lint commands, misleading spots, decisions made outside the repo, and anything corrected twice. Keep it short (under 200 lines). (Tell Claude what it can’t see; Keep CLAUDE.md short)
- Caveat: the guide lists "Describe your architecture and file layout in CLAUDE.md" as advice to stop following, because Claude reads the repo itself. This argues against requiring layout prose in the instruction file. (What you can stop doing)
- Personal preferences go in CLAUDE.local.md, which is gitignored. Path-specific rules go in `.claude/rules/` with `paths:` filters. Team procedures go in `.claude/skills/<name>/SKILL.md`. Skills with side effects should use `disable-model-invocation: true`. (Keep CLAUDE.md short; Scope rules to one part of the codebase; Put team procedures in skills)
- Give the agent a pass/fail check (tests, build, linter). Enforce critical checks with a Stop hook, and ask for evidence such as the command and its output. (Give Claude a check to run; Enforce the check with a Stop hook)
- Rules that must hold every time belong in hooks, deny rules or managed settings, not in CLAUDE.md. A committed `.claude/settings.json` applies to the whole team. Deny reads of `.env` and secrets. Keep the enforced set small. (Enforce the rules that can’t have exceptions; Limit access with permission rules and the sandbox; Choose who a rule applies to)
- Connect external systems through a CLI or MCP. Turn off unused MCP servers because their tools consume context. (Connect the tools Claude needs)
- Unattended runs need a definition of done, a self-check, limited permissions, turn/budget caps (`--max-turns`, `--max-budget-usd`) and a human sign-off. Protect `main` with a branch rule. (Let Claude run without you; Start runs on a schedule or an event)
- Manage cost with `/usage`, cheaper models for simple subagents, and read-only reviewer subagents with tools restricted in their definition. (Change a default; Know what subagents cost)

## Used for

- `arch.adr`
- `ai.mcp`
- `ai.instructions_fresh`
- `ai.instructions`
- `ai.settings`
- `ai.scoped_context`
- `ai.guardrails`
- `ai.extensions`
- `ai.no_local_leak`
- `ai.instructions_quality`
- `ai.ci_agents`
- `sk.size`
- `sk.present`
- `sk.frontmatter`
- `sk.descriptions`
- `test.present`
- `sec.env_template`
- `rep.documented`
- `ci.cd`
- `cost.llm_tracking`
- `cost.llm_efficiency`
- `cost.llm_limits`
