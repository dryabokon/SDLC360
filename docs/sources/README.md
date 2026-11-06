# Sources

Published material that the SDLC360 checklist is built on. Each expectation in `checklists/acceptance.md` cites
these sources verbatim under **Basis** (by id `S01`…`S13`), or is marked as our own **Convention**.

| Id | Source | Publisher | Published | Licence | Stored | Expectations citing it |
|---|---|---|---|---|---|---|
| S01 | [The New SDLC With Vibe Coding: From ad-hoc prompting to Agentic Engineering](01-google-new-sdlc-vibe-coding/SOURCE.md) | Google (Kaggle 5-Day AI Agents Intensive: Vibe Coding) | 2026 (spring) | none stated; © Google | fetch.py → local/ | 22 |
| S02 | [Harness engineering: leveraging Codex in an agent-first world](02-openai-harness-engineering/SOURCE.md) | OpenAI (engineering blog) | 2026-02-11 | © OpenAI | link only | 0 |
| S03 | [Best practices for Claude Code](03-anthropic-claude-code-best-practices/SOURCE.md) | Anthropic (Claude Code documentation) | living document; version modified 2026-11-04 | © Anthropic | fetch.py → local/ | 22 |
| S04 | [Effective context engineering for AI agents](04-anthropic-context-engineering/SOURCE.md) | Anthropic (engineering blog) | 2025-09-29 | © Anthropic | fetch.py → local/ | 3 |
| S05 | [AGENTS.md: a simple, open format for guiding coding agents](05-agents-md/SOURCE.md) | Agentic AI Foundation (Linux Foundation); originally OpenAI | 2025; under the Agentic AI Foundation since 2025-12-09 | MIT | in git | 6 |
| S06 | [Agent Skills specification](06-agent-skills-spec/SOURCE.md) | agentskills.io (open standard, originally Anthropic) | 2025-12 (open standard) | Apache-2.0 | in git | 5 |
| S07 | [State of AI-assisted Software Development 2025](07-dora-2025-state-of-ai-assisted-software-development/SOURCE.md) | DORA, Google Cloud | 2025-10 (v2025.2) | CC BY-NC-SA 4.0 | fetch.py → local/ | 8 |
| S08 | [DORA AI Capabilities Model](08-dora-2025-ai-capabilities-model/SOURCE.md) | DORA, Google Cloud | 2025-11 (v2025.1) | CC BY-NC-SA 4.0 | fetch.py → local/ | 11 |
| S09 | [NIST SP 800-218A: Secure Software Development Practices for Generative AI and Dual-Use Foundation Models (SSDF Community Profile)](09-nist-sp-800-218a-ssdf-genai/SOURCE.md) | NIST | 2024-07 | Public domain (U.S. Government work) | in git | 23 |
| S10 | [OWASP Top 10 for Agentic Applications 2026](10-owasp-top10-agentic-applications-2026/SOURCE.md) | OWASP Gen AI Security Project, Agentic Security Initiative | 2025-12 | CC BY-SA 4.0 | in git | 3 |
| S11 | [Security-Focused Guide for AI Code Assistant Instructions](11-openssf-ai-code-assistant-instructions/SOURCE.md) | OpenSSF Best Practices and AI/ML Working Groups | 2025-08-01 | Apache-2.0 | in git | 11 |
| S12 | [OpenSSF Scorecard: check documentation](12-openssf-scorecard-checks/SOURCE.md) | OpenSSF | living document (main branch) | Apache-2.0 | in git | 12 |
| S13 | [The ML Test Score: A Rubric for ML Production Readiness and Technical Debt Reduction](13-google-ml-test-score/SOURCE.md) | Google; IEEE Big Data 2017 | 2017 | © 2017 IEEE, personal use only | fetch.py → local/ | 3 |

57 of 71 expectations are backed by at least one source; 14 are conventions:
`arch.fresh`, `doc.readme_sections`, `doc.links`, `doc.docs_dir`, `doc.inline`, `hyg.file_size`, `hyg.editor`, `hyg.templates`, `test.framework`, `sec.gitignore`, `ci.stages`, `cost.infra`, `cost.ci`, `cost.documented`.

## Layout and licences

Each folder holds `SOURCE.md` (metadata in the frontmatter, key points, which expectations cite it) and the original.

- **In git**: originals whose licence allows redistribution and that are small (NIST public domain, OWASP CC BY-SA,
  OpenSSF / AGENTS.md / Agent Skills under Apache-2.0 or MIT).
- **`local/`** (git-ignored): originals that are copyrighted without a licence to redistribute (Google whitepaper,
  Anthropic pages, IEEE paper) or too large for git (DORA reports, CC BY-NC-SA). Restore them with
  `python docs/sources/fetch.py`; it verifies each file against the SHA-256 recorded at retrieval
  (add `--text` to write `.txt` extracts, which need `pypdf`).
- **Link only**: OpenAI's article (openai.com blocks automated downloads; save it from a browser into `local/`).

Retrieved 2026-11-06. To add a source: create `NN-slug/SOURCE.md` with the same frontmatter, then cite it as
`- SNN · <page or section> (direct|supporting) · "<verbatim quote>"` in `checklists/acceptance.md`.

## Candidate expectations proposed by the sources (not adopted yet)

Practices the sources ask for that the checklist does not cover yet. Each needs a decision and an analytical rule
before it is added.

- S01 · p. 44 · "Set the bar at the eval, not the demo." → Repos that build LLM agents keep an eval suite with explicit rubrics and run it in CI.
- S01 · p. 44 · "Treat AGENTS.md, system prompts, eval suites, and skill libraries as code: reviewed in pull requests, versioned with the project, owned by named engineers." → CODEOWNERS assigns owners to agent instruction files, .claude/ settings and skills.
- S01 · p. 44 · "Train reviewers on the failure modes of generated code, and tune review checklists accordingly." → PR template/review checklist covers AI-generated-code risks (hallucinated dependencies, error handling).
- S01 · p. 45 · "Make the boundary explicit: which projects, which branches, which environments warrant which mode of working." → Repo states its maturity level (prototype vs production) and the rigour it requires.
- S01 · p. 25 · "Success comes from giving agents success criteria rather than step-by-step instructions, then letting them iterate." → Features are specified in versioned spec files with acceptance criteria (e.g. specs/, SPEC.md).
- S03 · Limit access with permission rules and the sandbox · "`deny` rules hold in every permission mode, including auto and `bypassPermissions`, which is exactly why the `.env` rule belongs there" → Shared agent settings deny agent reads of .env and secret files.
- S03 · Keep CLAUDE.md short · "The memory guide recommends staying under 200." → The agent instruction file stays concise (under ~200 lines).
- S03 · Put team procedures in skills · "For a workflow with side effects, like actually cutting that release, add `disable-model-invocation: true`." → Skills with side effects (release, deploy) are user-invoked only.
- S03 · Know what subagents cost · "Give a custom subagent in `.claude/agents/` only `tools: Read, Grep, Glob`." → Subagent definitions restrict tools to the minimum (e.g. read-only reviewers).
- S03 · Enforce the check with a Stop hook · "The `Stop` hook version of the typecheck rule is a few lines in `.claude/settings.json`." → A Stop hook (or equivalent) enforces tests/typecheck before the agent reports done.
- S04 · The anatomy of effective context · "One of the most common failure modes we see is bloated tool sets that cover too much functionality or lead to ambiguous decision points about which tool to use." → Declared MCP servers/tools are minimal and non-overlapping.
- S04 · The anatomy of effective context · "we recommend working to curate a set of diverse, canonical examples that effectively portray the expected behavior of the agent." → Instruction files and skills point to canonical example code instead of long rule lists.
- S05 · FAQ: How do I migrate existing docs to AGENTS.md? · "Rename existing files to AGENTS.md and create symbolic links for backward compatibility" → One canonical instruction file; agent-specific files (CLAUDE.md, GEMINI.md) link or defer to it instead of diverging.
- S05 · 3. Add extra instructions · "Commit messages or pull request guidelines, security gotchas, large datasets, deployment steps: anything you’d tell a new teammate belongs here too." → The instruction file covers PR/commit conventions and security gotchas.
- S06 · `name` field · "Must match the parent directory name" → Each skill's frontmatter name equals its directory name and meets the length limits (name 64, description 1024).
- S06 · Validation · "Use the [skills-ref](https://github.com/agentskills/agentskills/tree/main/skills-ref) reference library to validate your skills" → Skills are validated automatically (skills-ref validate) in CI or pre-commit.
- S06 · File references · "Keep file references one level deep from `SKILL.md`. Avoid deeply nested reference chains." → Skill references are one level deep from SKILL.md.
- S08 · p. 19 · "This framework should be published as a “living document” in a central, easily searchable hub, such as an internal developer portal or wiki." → The repo states or links its AI usage policy: permitted tools, prohibited data, human-review rules (e.g. an AI section in CONTRIBUTING or AI_POLICY.md).
- S07 · p. 53 · "These new survey findings affirm our recommendation to invest in making an organization’s stance on AI-assisted development clear and communicated to its software developers" → Same as above. This is DORA AI capability #1 and has the strongest backing of the seven.
- S08 · p. 41 · "Teams should consider how they will ensure that all contributions are small, logical changes instead of one giant, hard-to-review code dump." → Commits and PRs stay small (median lines changed per commit/PR under a threshold), measured from git history.
- S08 · p. 49 · "Any batch of code that takes longer than a week to complete is too big." → Branches and PRs are short-lived (merged within days), measured from git/PR history.
- S08 · p. 49 · "Developers must commit and merge their work into the mainline (trunk) at least once per day." → Trunk-based development: few long-lived branches and frequent merges to main.
- S08 · p. 39 · "Each change, whether made by a human or an AI, should be committed as a distinct, atomic unit." → Commit history shows frequent, atomic commits rather than rare bulk commits.
- S08 · p. 41 · "By clearly explaining the “why” behind a change, not just the “what”, teams create an invaluable historical record." → A commit message convention (e.g. Conventional Commits) is documented and enforced (commitlint or a CI check).
- S08 · p. 41 · "Store AI prompts: Prompts contain valuable context about a task. By versioning them, teams can share knowledge … and create an audit trail for agentic workflows." → Prompts used by agents and by LLM features live as versioned files in the repo, not inline strings or outside git.
- S08 · p. 38 · "comprehensive use includes not just application code, but also system configurations, test and deployment scripts, and infrastructure definitions." → Infrastructure and deployment configuration are versioned in the repo as code (IaC, container/orchestration files).
- S08 · p. 49 · "Use feature flags (or other progressive delivery methods) to decouple deployment from release." → Incomplete features are merged behind feature flags (a flag library or config is present).
- S08 · p. 24 · "we recommend introducing automated checks and monitoring to ensure data accuracy, completeness, and timeliness." → Projects that own data have automated data-quality / schema assertions in tests or CI.
- S08 · p. 24 · "a team may agree to add and maintain a “data” section to an application’s README.md that includes information about what data is created or used by this application." → The README (or docs) has a data section describing the datasets the app creates and uses.
- S08 · p. 56 · "SDD breaks coding into phases, generating versionable outputs." → Specs or requirements for AI-built features are versioned in the repo (e.g. specs/ folder) before implementation.
- S09 · SP 800-218 PW.1.1, p.20 · "Use forms of risk modeling – such as threat modeling, attack modeling, or attack surface mapping – to help assess the security risk for the software." → A threat model (THREAT_MODEL.md or a security section of the architecture doc) exists and is kept current.
- S09 · SP 800-218 PS.3.2, p.19 · "Collect, safeguard, maintain, and share provenance data for all components of each software release (e.g., in a software bill of materials [SBOM])." → The release workflow generates an SBOM (SPDX or CycloneDX) for every release.
- S09 · SP 800-218 PW.7.2 Ex.1, p.23 · "Perform peer review of code, and review any existing code review, analysis, or testing results as part of the peer review." → Changes reach the default branch only through reviewed pull requests (required approvals).
- S09 · SP 800-218A PW.6.1.C1, p.24 · "Consider using secure model serialization mechanisms that reduce or eliminate vectors for the introduction of malicious content." → Committed or downloaded model weights use safe formats (e.g. safetensors), not pickle-based files.
- S10 · ASI02 guideline 7, p.15 · "Enforce fully qualified tool names and version pins to avoid tool alias collisions or typo squatted tools" → MCP servers and agent tools declared in the repo are pinned to exact versions from trusted sources (no unpinned `npx`/`@latest`).
- S10 · ASI02 guideline 2, p.15 · "Require explicit authentication for each tool invocation and human confirmation for high-impact or destructive actions (delete, transfer, publish)." → Shared agent settings deny, or require confirmation for, destructive commands (rm -rf, force-push, publish, deploy).
- S10 · ASI05 guideline 4, p.23 · "Execution environment security: Never run as root. Run code in sandboxed containers with strict limits including network access" → Agents run in a sandbox committed to the repo (sandbox setting or devcontainer, with a network allowlist).
- S11 · Secure Coding Principles in AI Instructions · "One of the first sections in your instructions should reinforce general secure coding best practices." → The agent instruction file has a security section (secrets handling, input validation, dependency policy, least privilege).
- S11 · Platform and Runtime Security Considerations > Container and Deployment Considerations · "Use minimal base images and avoid running containers with the root user." → Dockerfiles use a minimal, digest-pinned base image and switch to a non-root USER.
- S11 · Addressing Software Supply Chain Security > Generate Software Bill of Materials (SBOM) · "Generate an SBOM by using tools that support standard formats like SPDX or CycloneDX" → The release workflow generates an SBOM (SPDX or CycloneDX).
- S12 · Dangerous-Workflow · "This check determines whether the project's GitHub Action workflows has dangerous code patterns." → Workflows avoid `pull_request_target`/`workflow_run` combined with a PR checkout, and never interpolate untrusted `github.event.*` context into `run:` scripts.
- S12 · Code-Review · "This check determines whether the project requires human code review before pull requests (merge requests) are merged." → Recent changes on the default branch were merged through human-approved pull requests.
- S12 · Binary-Artifacts · "Including generated executables in the source repository increases user risk." → No generated binaries (.exe, .dll, .so, .jar, .class, .pyc) are committed.
- S12 · Vulnerabilities · "An open vulnerability is readily exploited by attackers and should be fixed as soon as possible." → Locked dependencies have no known open vulnerabilities (e.g. osv-scanner is clean, or ignores are justified in osv-scanner.toml).
- S12 · SBOM · "An SBOM can give users information about what dependencies your project has which allows them to identify vulnerabilities in the software supply chain." → An SBOM is produced in CI and attached to releases.
- S13 · Infra 4, p.5 · "Model quality is validated before attempting to serve it" → ML repos gate model promotion on an automated evaluation step with explicit quality thresholds.
- S13 · Data 1, p.2 · "Feature expectations are captured in a schema" → ML or data repos define a data schema or validation (e.g. pandera, Great Expectations, TFDV) that is checked automatically.
- S13 · Infra 2, p.4 · "a simple unit test to generate random input data, and train the model for a single step of gradient descent is quite powerful" → Training code has a fast smoke test (one training step on random data) that runs in CI.
