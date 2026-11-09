---
id: agents-md
title: AGENTS.md: a simple, open format for guiding coding agents
publisher: Agentic AI Foundation (Linux Foundation); originally OpenAI
authors: agentsmd/agents.md contributors
published: 2025; under the Agentic AI Foundation since 2025-12-09
kind: open format
url: https://agents.md/
retrieved: 2026-11-06
license: MIT (github.com/agentsmd/agents.md)
files:
  - commit agents-md-repo-readme.md 60ec51c226560aaf2c49a0b8a2452c8cf24459c37a816764979dc917076c7afb https://raw.githubusercontent.com/agentsmd/agents.md/main/README.md
  - commit agents-md-site.md 77a2766757c87424b5cdbeb091841d0a4efc3b491c71bfbe2359aeeac50174d3 https://agents.md/
---

# AGENTS.md: a simple, open format for guiding coding agents

agents-md-site.md is a text extract of the site (FAQ: placement, nesting, precedence).

## Key points

- AGENTS.md is a "README for agents": a predictable place for agent instructions, kept separate from the human-facing README. (README; Why AGENTS.md?)
- Put AGENTS.md at the repository root. (How to use AGENTS.md? / 1. Add AGENTS.md)
- Cover the project overview, build and test commands, code style, testing instructions and security considerations. Also add PR/commit guidelines and deployment steps. (2. Cover what matters; 3. Add extra instructions)
- In monorepos, use nested AGENTS.md files per package. The nearest file wins. (4. Large monorepo?)
- Treat AGENTS.md as living documentation. Listed test commands will be run by agents, which fix failures before finishing. (FAQ)
- One AGENTS.md works across many agents. Migrate other files with a rename plus symlinks for backward compatibility. (One AGENTS.md works across many agents; FAQ: How do I migrate existing docs to AGENTS.md?)

## Used for

- `doc.readme`
- `ai.instructions`
- `ai.instructions_quality`
- `ai.instructions_fresh`
- `ai.scoped_context`
- `test.ratio`
