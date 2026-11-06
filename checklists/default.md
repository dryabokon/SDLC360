# SDLC 360° — expectations checklist

This file is the contract between people and the assessor. Each line is an **expectation** about the project.

    - [check.id] priority: expectation text     -> evaluated automatically by the scanner check with that id
    - [ ] priority: expectation text            -> your own expectation; judged by the reviewer agent

Priorities:

- `critical` — without it the aspect cannot be considered healthy. **Gate:** if not met, the aspect score is capped
  at 49 (Weak); if partially met, at 74 (Needs work) — no matter what else passes.
- `important` — expected from a mature project.
- `nice` — a sign of high maturity; missing it is not a problem.

Delete a line to drop an expectation. Override per project by committing `.sdlc360/expectations.md`
to the assessed repository, or pass `--checklist <file>` to `python sdlc.py scan`.

## security
- [sec.no_secrets] critical: No secrets or API keys are hard-coded in tracked files.
- [sec.no_sensitive_files] critical: No credential files (.env, private keys, tfstate) are committed.
- [sec.ci_scanning] important: CI scans code, dependencies and secrets on every change.
- [sec.dep_updates] important: Dependency updates are automated (Dependabot / Renovate).
- [sec.gitignore] important: .gitignore keeps env files and keys out of git.
- [sec.workflow_permissions] important: CI workflows run with least-privilege tokens.
- [sec.env_template] nice: Required configuration is documented in an .env.example template.
- [sec.precommit_secrets] nice: A pre-commit hook blocks secrets before they are committed.
- [sec.policy] nice: A SECURITY.md explains how to report vulnerabilities.
- [sec.codeowners] nice: CODEOWNERS assigns reviewers for sensitive paths.

## harness
- [ai.instructions] critical: The repo has an agent instruction file (CLAUDE.md / AGENTS.md).
- [ai.instructions_quality] important: The instruction file states build/test commands, layout and conventions.
- [ai.instructions_fresh] important: The instruction file matches the current code (no stale paths).
- [ai.settings] important: Shared agent settings define what agents may and may not do.
- [ai.guardrails] important: Hooks enforce formatting, linting and tests automatically.
- [ai.no_local_leak] important: Personal agent settings are not committed.
- [ai.extensions] nice: Repeated workflows are packaged as skills, subagents or commands.
- [ai.ci_agents] nice: AI agents are wired into CI for review or triage.
- [ai.scoped_context] nice: Large codebases give agents scoped, per-package context.
- [ai.mcp] nice: External tools the project relies on are declared as MCP servers.

## skills
- [sk.present] critical: Reusable agent procedures exist as markdown skills / subagents / commands.
- [sk.frontmatter] important: Every skill declares a name and description in frontmatter.
- [sk.descriptions] important: Descriptions say what the skill does and when to use it.
- [sk.links] important: Links and scripts referenced by skills exist.
- [sk.size] nice: Skills stay concise and push detail into references.
- [sk.layout] nice: Skills follow one layout and kebab-case naming.

## docs
- [doc.readme] critical: The README explains what the project is and how to start.
- [doc.readme_sections] important: The README covers setup, usage, testing, configuration and overview.
- [doc.links] important: Docs reference files that actually exist.
- [doc.freshness] important: Docs are updated together with the code.
- [doc.docs_dir] nice: Deeper documentation lives in a docs/ folder.
- [doc.standard_files] nice: LICENSE, CONTRIBUTING and CHANGELOG are present.
- [doc.inline] nice: Public code is documented inline (docstrings / doc comments).

## architecture
- [arch.doc] critical: An architecture document describes components, data flow and boundaries.
- [arch.diagrams] important: Architecture diagrams are kept as code (Mermaid / PlantUML / C4).
- [arch.adr] important: Significant decisions are recorded as ADRs.
- [arch.structure] important: Source code is organised into modules, not a flat root.
- [arch.fresh] important: The architecture document is maintained alongside the code.
- [arch.boundaries] nice: Module boundaries are explicit and enforced by tooling.

## tests
- [test.present] critical: The project has an automated test suite.
- [test.ci] critical: Tests run in CI on every push and pull request.
- [test.ratio] important: Tests grow with the code (healthy test-to-source ratio).
- [test.coverage] important: Coverage is measured and a minimum is enforced.
- [test.framework] nice: The test runner is configured explicitly.
- [test.layers] nice: Beyond unit tests there are integration / e2e / property tests.

## cicd
- [ci.present] critical: CI runs on GitHub Actions.
- [ci.pr] important: CI gates pull requests before merge.
- [ci.stages] important: CI lints, tests and builds.
- [ci.cd] important: Releases or deployments are automated.
- [ci.hygiene] nice: Jobs have timeouts, version matrices and protected environments.
- [ci.pinning] nice: Third-party actions are pinned to commit SHAs.
- [ci.speed] nice: CI is fast: caching, cancel-in-progress and path filters.

## runs
- [run.folder] critical: Each execution writes its outputs to a runs/ folder.
- [run.manifest] important: Every run records its config and git SHA (traceable).
- [run.lockfile] important: Dependencies are locked.
- [run.documented] important: How to reproduce a run is documented.
- [run.environment] important: The runtime environment is pinned (container / version files).
- [run.tracking] nice: Experiments are tracked (MLflow / W&B / DVC / manifests).
- [run.entrypoints] nice: One-command entry points exist (Makefile / just / scripts).
- [run.seeds] nice: Randomness is seeded where results depend on it.

## cost
- [cost.llm_tracking] critical: LLM token usage and cost are tracked per call / run.
- [cost.llm_limits] important: LLM calls are bounded by max_tokens, budgets and retries.
- [cost.infra] important: Cloud resources have budgets, tags and cost checks.
- [cost.llm_efficiency] nice: Prompt caching and a central model config keep spend down.
- [cost.ci] nice: CI minutes are controlled (timeouts, cancel-in-progress, path filters).
- [cost.documented] nice: Expected costs and budgets are documented.

## hygiene
- [hyg.lint] critical: A linter is configured.
- [hyg.format] important: An auto-formatter is configured.
- [hyg.types] important: Static typing is enforced.
- [hyg.precommit] important: Pre-commit hooks run format and lint locally.
- [hyg.file_size] nice: No oversized source files.
- [hyg.editor] nice: .editorconfig / .gitattributes keep formatting consistent.
- [hyg.templates] nice: PR and issue templates guide contributors.
