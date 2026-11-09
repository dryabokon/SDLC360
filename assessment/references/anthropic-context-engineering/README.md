---
id: anthropic-context-engineering
title: Effective context engineering for AI agents
publisher: Anthropic (engineering blog)
authors: Anthropic Applied AI team
published: 2025-09-29
kind: article
url: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
retrieved: 2026-11-06
license: Copyright Anthropic. Kept local only.
files:
  - local effective-context-engineering.html e9efcb5c95018b634c17b3f33fd605c79df46557f206de8de66c5c1e05702b2a https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
---

# Effective context engineering for AI agents

## Key points

- Treat context as a finite "attention budget". Aim for the smallest set of high-signal tokens that produces the desired outcome. (Why context engineering is important to building capable agents; The anatomy of effective context)
- Write system prompts at the "right altitude": neither brittle hard-coded logic nor vague guidance. Organise them in clear sections and keep them minimal but sufficient. (The anatomy of effective context)
- Tools should be self-contained, unambiguous and minimal in overlap. Bloated tool sets are a common failure mode. (The anatomy of effective context)
- Use a few diverse, canonical examples rather than long lists of edge-case rules. (The anatomy of effective context)
- Prefer "just in time" retrieval through lightweight identifiers. Folder hierarchy and naming conventions are signals that agents use, so repo structure matters. (Context retrieval and agentic search)
- Hybrid model: CLAUDE.md is loaded up front, and the rest is found with glob/grep on demand. (Context retrieval and agentic search)
- For long-horizon work, use compaction, structured note-taking (for example NOTES.md) and sub-agents with clean contexts that return condensed summaries. (Context engineering for long-horizon tasks)

## Used for

- `ai.extensions`
- `sk.descriptions`
- `arch.structure`
