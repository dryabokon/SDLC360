---
id: agent-skills-spec
title: Agent Skills specification
publisher: agentskills.io (open standard, originally Anthropic)
authors: agentskills/agentskills contributors
published: 2025-12 (open standard)
kind: specification
url: https://agentskills.io/specification
retrieved: 2026-11-06
license: Apache-2.0 code, CC-BY-4.0 docs (github.com/agentskills/agentskills)
files:
  - commit specification.mdx b9079c0c10b7930e8c6a20ff2bc10cda2a3343c55185120e3f1116a1a529b220 https://raw.githubusercontent.com/agentskills/agentskills/main/docs/specification.mdx
---

# Agent Skills specification

## Key points

- A skill is a directory with a required `SKILL.md` and optional `scripts/`, `references/` and `assets/`. (Directory structure)
- The frontmatter must contain `name` and `description`. Optional fields are license, compatibility, metadata and allowed-tools. (Frontmatter)
- `name`: 1-64 characters, lowercase alphanumeric plus hyphens, no leading, trailing or consecutive hyphens, and must match the parent directory name. (`name` field)
- `description`: 1-1024 characters, says what the skill does and when to use it, and includes keywords for matching. (`description` field)
- Progressive disclosure: keep SKILL.md under 500 lines (about 5000 tokens) and move detail into focused reference files. (Progressive disclosure; `references/`)
- Use relative file references kept one level deep. Scripts should document dependencies and give helpful errors. Validate skills with `skills-ref validate`. (File references; `scripts/`; Validation)

## Used for

- `sk.size`
- `sk.frontmatter`
- `sk.links`
- `sk.layout`
- `sk.descriptions`
