---
id: 08-dora-2025-ai-capabilities-model
title: DORA AI Capabilities Model
publisher: DORA, Google Cloud
authors: DORA research team
published: 2025-11 (v2025.1)
kind: practitioner guide, 97 pages
url: https://dora.dev/ai/capabilities-model/report/
retrieved: 2026-11-06
license: CC BY-NC-SA 4.0 (stated in the PDF). Local only because of size (9 MB).
files:
  - local 2025_dora_ai_capabilities_model.pdf 1d9541e728b6e402000c9d468e2cdce54ce3b2d6447d509cdb2b8ac40c193aaf https://services.google.com/fh/files/misc/2025_dora_ai_capabilities_model.pdf
---

# DORA AI Capabilities Model

## Key points

DORA, *AI Capabilities Model 2025*

- The seven capabilities, each with the chapter's start page:
  1. Clear and communicated AI stance (p. 15)
  2. Healthy data ecosystems (p. 21)
  3. AI-accessible internal data (p. 27)
  4. Strong version control practices (p. 37)
  5. Working in small batches (p. 45)
  6. User-centric focus (p. 53)
  7. Quality internal platforms (p. 59)

  The model diagram is on p. 9 and the one-page summary is on p. 14.
- AI stance: DORA measures how clear and well communicated the policy is, not what it says. It recommends a three-bucket policy (prohibited / permitted with guardrails / allowed), published as a living document with a list of approved tools (p. 16, p. 19). A clear stance amplifies individual effectiveness, organisational performance and throughput, and reduces friction (p. 15).
- Context engineering, not prompt engineering: give AI a "briefing packet" of codebase, style guide, current API docs, policies and tools (p. 28). Keep a shared, version-controlled library of context templates (p. 31). Supply only the most relevant context, using RAG or MCP, because large raw documents cause "context rot" and hallucinations (p. 32, p. 33, p. 34). Human-validated distilled summaries such as GEMINI.md are recommended (p. 33).
- Version control in the AI era: commit small, frequent, atomic changes. Version everything, including configuration, infrastructure, prompts and agent configuration files such as CLAUDE.md. Use trunk-based development and clear commit messages (Conventional Commits) (p. 39, p. 41). About 21% of respondents already store AI prompts in version control (p. 40).
- Small batches: work items should take hours to a couple of days; anything over a week is too big. Commit to trunk daily, use feature flags and set WIP limits (p. 49). Large AI-generated changes are hard to review, test and integrate safely (p. 47).
- A data quality framework means automated checks for accuracy, completeness and timeliness (p. 24). Document the data an app creates and uses in a README "data" section, and treat that metadata as a versioned code artifact (p. 24).
- Platforms: without a good platform, individual AI gains are "swallowed by bottlenecks in testing, security reviews, and complex deployment processes" (p. 60). AI's positive effect on organisational performance is negligible when platform quality is low and strong when it is high (p. 61). Clear feedback is the platform property most correlated with a good user experience (p. 63).
- User-centric focus: spec-driven development puts versioned specs before AI-written code (p. 56). Teams without a user focus see AI lower team performance (p. 55).
- Security for AI context: use least-privilege retrieval with the user's own credentials, and route AI connections through a vetted, centrally managed proxy or MCP server (p. 34).

## Used for

- `arch.doc`
- `arch.diagrams`
- `doc.freshness`
- `ai.mcp`
- `sk.present`
- `test.ci`
- `rep.entrypoints`
- `rep.documented`
- `rep.environment`
- `ci.pr`
- `ci.present`
