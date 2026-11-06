---
id: owasp-agentic-top10-2026
title: OWASP Top 10 for Agentic Applications 2026
publisher: OWASP Gen AI Security Project, Agentic Security Initiative
authors: OWASP GenAI contributors
published: 2025-12
kind: risk list, 57 pages
url: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
retrieved: 2026-11-06
license: CC BY-SA 4.0 (site-wide licence of genai.owasp.org; not repeated in the PDF)
files:
  - commit OWASP-Top-10-for-Agentic-Applications-2026.pdf a2db94cd00b08e0b3a5e5b619afe024bdbcd74503111085705e4f3dd886fcb5c https://genai.owasp.org/download/52117/?tmstv=1765059207
---

# OWASP Top 10 for Agentic Applications 2026

## Key points

- The core control across the list is "least agency": each tool gets a least-privilege profile (scopes, rate, egress allowlist), and high-impact or destructive actions need human confirmation. (ASI02 guidelines 1-2, p.14-15; ASI03 guideline 4, p.18)
- Agent tools and code execution should run in sandboxes with egress allowlists. Agents should never run as root, and filesystem access should be restricted to a working directory. (ASI02 guideline 3, p.15; ASI05 guideline 4, p.23-24)
- Agentic supply chain covers MCP servers, tool descriptors, prompts and agent dependencies. Recommended controls: SBOM/AIBOM, an allowlist with pinning, typosquat scanning, provenance checks before install, and reproducible builds. (ASI04 guidelines 1-3, p.21)
- Prompts, orchestration scripts and memory schemas belong in version control with peer review. Prompts, tools and configs should be pinned by content hash and commit ID. (ASI04 guidelines 4 and 7, p.21)
- An auto-execution allowlist should be kept under version control, and elevated runs need human approval. (ASI05 guideline 6, p.24)
- Runaway cost is a named risk ("loop amplification", "bill spikes"). The mitigation is usage ceilings on cost, rate or tokens, with throttling or revocation when they are exceeded. (ASI02 common example 5, p.13; guideline 5, p.15)
- Log every tool invocation and agent action in immutable logs, and monitor for drift. Have kill switches and credential revocation ready. (ASI02 guideline 8, p.15; ASI04 guideline 8, p.21; ASI10 guidelines 1 and 4, p.38)
- A real-world example is lockfile poisoning: an agent regenerated a lockfile from unpinned specs and pulled a backdoored version. (ASI05 example scenario 8, p.23)

## Used for

- `ai.settings`
- `rep.lockfile`
- `cost.llm_limits`
