---
id: 01-google-new-sdlc-vibe-coding
title: The New SDLC With Vibe Coding: From ad-hoc prompting to Agentic Engineering
publisher: Google (Kaggle 5-Day AI Agents Intensive: Vibe Coding)
authors: Addy Osmani, Shubham Saboo, Sokratis Kartakis
published: 2026 (spring)
kind: whitepaper, 51 pages
url: https://www.kaggle.com/whitepaper-the-new-SDLC-with-vibe-coding
retrieved: 2026-11-06
license: No license stated in the document; copyright Google. Kept local only.
files:
  - local the-new-sdlc-with-vibe-coding.pdf b9a23474e6b1f0f8e5c14e6377d3578c281e727d904ae364e1e8c713518fa9de https://raw.githubusercontent.com/gsaini/awesome-software-engineering/main/whitepapers/ai-agentic-engineering/the-new-sdlc-with-vibe-coding.pdf
---

# The New SDLC With Vibe Coding: From ad-hoc prompting to Agentic Engineering

Kaggle serves the PDF only through its web app; the copy is fetched from a public GitHub mirror and pinned by SHA-256. Title page checked: title and authors match the Kaggle page.

## Key points

- Production work should sit at the "agentic engineering" end of the spectrum. Intent goes in formal specs, architecture docs and memory files. Output is checked by automated test suites, CI/CD gates and LM judges, not by "does it seem to work?" (p. 13)
- Context engineering is the core skill. Rule files (AGENTS.md, CLAUDE.md) are always-loaded static context, and skills are loaded on demand. Treat the static/dynamic split as an architectural decision that is reviewed and versioned. (p. 16-17)
- A harness surrounds the model. It includes rule files, tools/MCP servers, sandboxes, orchestration, deterministic hooks at lifecycle points (for example before a commit) and observability with cost metering. Most agent failures are configuration failures. (p. 28, p. 31)
- Set up an AGENTS.md early: stack, conventions, hard rules, workflow. Add a rule every time the agent repeats a mistake. (p. 43)
- Write tests and evals before generating code, because they are the contract with the AI. Review every shipped line, and watch for hallucinated packages and weak error handling. (p. 43-44)
- Treat AGENTS.md, prompts, eval suites and skill libraries as code: reviewed in PRs, versioned, owned by named engineers. Gate agent shipping on eval coverage with explicit rubrics. (p. 44)
- Make the prototype-vs-production boundary explicit. Before production, put in place evals in CI, traces of agent runs, scoped permissions per agent and security review. Adopt MCP/A2A open standards. (p. 45)
- Control token cost: send dense, high-signal context, and route simpler tasks (test generation, review, CI monitoring) to cheaper models. (p. 40-42)

## Used for

- `arch.doc`
- `arch.adr`
- `ai.mcp`
- `ai.instructions_fresh`
- `ai.instructions`
- `ai.settings`
- `ai.scoped_context`
- `ai.guardrails`
- `ai.extensions`
- `ai.instructions_quality`
- `ai.ci_agents`
- `sk.size`
- `sk.present`
- `test.present`
- `test.coverage`
- `test.layers`
- `sec.precommit_secrets`
- `sec.no_secrets`
- `ci.pr`
- `cost.llm_tracking`
- `cost.llm_efficiency`
- `cost.llm_limits`
