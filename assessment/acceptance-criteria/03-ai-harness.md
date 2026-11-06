# AI harness: how each expectation is judged

Expectations and their priorities are in [expectations.md](../expectations.md).
How to edit this file: [assessment/README.md](../README.md#acceptance-criteria).

## ai.instructions: The repo has an agent instruction file (CLAUDE.md / AGENTS.md).

**How we check.** Tracked files with the exact (case-sensitive) name `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules` anywhere, `.github/copilot-instructions.md`, and files under root `.cursor/rules/`. `CLAUDE.local.md` is personal configuration (see `ai.no_local_leak`) and does not count.

- **Met:** One of those files sits at the repo root or under `.github/`.
- **Partially met:** Only nested ones exist (e.g. `pkg/CLAUDE.md`) or only `.cursor/rules/*` files.
- **Not met:** None found.

**What the check cannot see.** Contents are not judged here; an empty `CLAUDE.md` passes. Lower-case `claude.md` is not recognised.

**Why we expect it.**

> Set up an AGENTS.md (or equivalent) for the project. Pick the convention that matches the coding agent of choice.
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 43 · direct

> Only write down what Claude can’t find by reading the repo, or what it would otherwise spend time rediscovering every session.
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Tell Claude what it can’t see · direct

> Create an AGENTS.md file at the root of the repository.
>
> — [agents-md](../references/agents-md/), How to use AGENTS.md? · direct

## ai.instructions_quality: The instruction file states build/test commands, layout and conventions.

**How we check.** The main file: `CLAUDE.md`, else `AGENTS.md`, else `.github/copilot-instructions.md`, else the first root/.github instruction file. Symlinks are followed, as are up to 5 `@file.md` import lines. In headings plus the first 20,000 characters it looks for four topics: commands (build/run/install/make/npm/pip/cargo…), testing (`test…`), layout (architect/structure/layout/directory/module), conventions (convention/style/guideline/rule/must/never/always). It also counts lines.

- **Met:** All four topics are present and the combined text is 8–800 lines.
- **Partially met:** Everything else between the extremes, e.g. three topics at any size, all four but under 8 or over 800 lines, or one topic in a 25–400-line file.
- **Not met:** No root-level instruction file, no topic words at all, or only one topic in a file under 8 or over 800 lines.

**What the check cannot see.** Keywords are common English words ("run", "test", "must", "always"), so almost any prose scores on all four. No command is checked for correctness. The main file may be an untracked file that exists only on disk. Nested-only instruction files score 0 here.

**Known flaw.** The checklist says the file "states build/test commands"; the code only looks for words like "run" or "test", not actual commands.

**Why we expect it.**

> Start with ten lines: stack, conventions, hard rules, workflow. Add a rule every time the agent does something it should not do again.
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 43 · direct

> How to confirm work in this repo: the exact test, typecheck, and lint commands, and how to run a single test file
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Keep CLAUDE.md short · direct

> Add sections that help an agent work effectively with your project. Popular choices: … Build and test commands … Code style guidelines
>
> — [agents-md](../references/agents-md/), 2. Cover what matters · direct

## ai.instructions_fresh: The instruction file matches the current code (no stale paths).

**How we check.** In the main file (or the imported file for a ≤3-line wrapper): relative markdown links and backticked paths with an extension or trailing slash. Each must resolve from the file's folder, the repo root, or as a path suffix of any file. Also compares the file's last commit with the latest commit touching source code. Score = 0.6 × share of paths resolving + 0.4 × freshness (1.0 within 30 days, falling to 0 at 365 days behind).

- **Met:** Score ≥ 0.85, e.g. all paths resolve and the file was updated within ~155 days of the last code change, or at least 75% resolve and it is within 30 days.
- **Partially met:** Score 0.35–0.85, e.g. all paths resolve but the file is a year behind (0.6), or half resolve and it is fresh (0.7).
- **Not met:** No root instruction file, or most paths are broken and the file is stale (e.g. all broken and more than ~72 days behind).

**What the check cannot see.** The suffix fallback is lenient (`x/y.py` matches any `.../x/y.py`). Paths in fenced code without backticks, and stale commands, are not checked. Any trivial commit to the file resets freshness. References in `@`-imported files are ignored unless the main file is a thin wrapper.

**Known flaw.** If freshness cannot be computed (no source files or no dates), it defaults to 0.5, so the best possible score is 0.8. A docs-only repo with perfect references can never be Met.

**Why we expect it.**

> Absolutely. Treat AGENTS.md as living documentation.
>
> — [agents-md](../references/agents-md/), FAQ: Can I update it later? · direct

> Treat AGENTS.md, system prompts, eval suites, and skill libraries as code … Without this discipline, the harness drifts and agent behaviour becomes irreproducible across the team.
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 44 · supporting

> `/doctor prompt-audit` flags instructions that were written for older models, point at files that no longer exist, or contradict each other.
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Keep CLAUDE.md short · supporting

## ai.settings: Shared agent settings define what agents may and may not do.

**How we check.** Root `.claude/settings.json`, parsed as JSON for a non-empty `permissions` key.

- **Met:** The file exists and has a non-empty `permissions` entry.
- **Partially met:** The file exists but has no `permissions`, or is not valid JSON (0.5).
- **Not met:** No `.claude/settings.json`.

**What the check cannot see.** The rules are not read: an allow-everything policy passes. Other agents' settings (Codex, Cursor, Copilot) are not considered.

**Known flaw.** The checklist says settings define what agents "may and may not do"; deny rules are not required, any non-empty `permissions` passes.

**Why we expect it.**

> `.claude/settings.json` and the hooks in it belong to the repo. Once you commit them, they apply to everyone who works in the repo.
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Choose who a rule applies to · direct

> Access control and approvals: Require human approval for elevated runs; keep an allowlist for auto-execution under version control; enforce role and action-based controls.
>
> — [owasp-agentic-top10-2026](../references/owasp-agentic-top10-2026/), ASI05 guideline 6, p.24 · direct

> The developer defines the tools the agent will have access to (like specific APIs or database schemas) and sets the fundamental rules the agent cannot break.
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 29 · supporting

## ai.guardrails: Hooks enforce formatting, linting and tests automatically.

**How we check.** A non-empty `hooks` key in `.claude/settings.json`. Otherwise any file under root `.claude/hooks/` or `.husky/`, or any `.pre-commit-config.yaml` / `lefthook.yml` anywhere.

- **Met:** `.claude/settings.json` declares agent hooks.
- **Partially met:** No agent hooks, but one of those hook files exists (0.6).
- **Not met:** Neither.

**What the check cannot see.** What the hooks run is never inspected. Hooks in `settings.local.json` or plugins are not seen. `lefthook.yaml` / `.lefthook.yml` are missed (security reads `.lefthook.yml`).

**Known flaw.** The checklist says hooks enforce formatting, linting and tests; the code never checks what they do, and a full pre-commit setup can never be Met without Claude agent hooks.

**Why we expect it.**

> Deterministic code that runs at specific lifecycle points: before a tool call, after a file edit, before a commit. Hooks are the place for things the agent should never forget
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 28 · direct

> If something has to happen every time, make it a hook, a deny rule, or a managed setting.
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Enforce the rules that can’t have exceptions · direct

> an increase in change volume without a corresponding set of evolved guardrails, roles, and “golden paths” could increase verification and coordination costs.
>
> — [dora-2025-state-of-ai-assisted-development](../references/dora-2025-state-of-ai-assisted-development/), p. 40 · supporting

## ai.no_local_leak: Personal agent settings are not committed.

**How we check.** Tracked files ending in `.claude/settings.local.json` or `CLAUDE.local.md` (case-sensitive, any depth).

- **Met:** None is tracked.
- **Partially met:** never.
- **Not met:** At least one is tracked.

**What the check cannot see.** Other personal files (`.vscode/settings.json`, `.cursor/` user rules, `.env.local`) are not checked. When scanning a non-git folder, ignored local files on disk are flagged too.

**Why we expect it.**

> Your personal preferences go in `CLAUDE.local.md` instead of `CLAUDE.md`, and you add that file to `.gitignore` so it stays out of the repo.
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Keep CLAUDE.md short · direct

## ai.extensions: Repeated workflows are packaged as skills, subagents or commands.

**How we check.** Counts files at any depth under the root folders `.claude/skills/`, `.claude/agents/` (`.md`), `.claude/commands/` (`.md`), `.github/prompts/` (`.md`), `.github/chatmodes/`, `.github/instructions/`, `.github/agents/`, `.cursor/rules/`, `.codex/`, `.claude-plugin/`, `.agents/skills/`, `.agents/agents/`.

- **Met:** Three or more such files.
- **Partially met:** Exactly two files.
- **Not met:** One file or none.

**What the check cannot see.** Counts files, not workflows: one skill with a `SKILL.md` and two reference files is Met. `.claude-plugin/plugin.json` counts. Root-level `skills/`, `agents/`, `commands/` folders and nested packages' `.claude/` folders are not counted (unlike `sk.present`).

**Why we expect it.**

> Reusable system prompts, skill libraries, MCP server connections, and evaluation harnesses compound across projects. Treat them as infrastructure: documented, maintained, and improved deliberately.
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 45 · direct

> A more capable model knows more about engineering, but not how your team does a release, what your incident runbook says, or how you want API docs written.
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Put team procedures in skills · supporting

> specialized sub-agents can handle focused tasks with clean context windows.
>
> — [anthropic-context-engineering](../references/anthropic-context-engineering/), Sub-agent architectures · supporting

## ai.ci_agents: AI agents are wired into CI for review or triage.

**How we check.** Text of `.github/workflows/*` (not delegated scripts) for `anthropics/claude-code-action`, `claude-code-base-action`, `openai/codex-action`, `coderabbit` or `copilot`, case-insensitive.

- **Met:** Any of those strings appears.
- **Partially met:** never.
- **Not met:** None appears.

**What the check cannot see.** "copilot" anywhere (a comment, job name, branch filter) counts. AI reviewers installed as GitHub Apps or repo settings (Copilot review, CodeRabbit app, `.coderabbit.yaml`) are invisible. Other actions (Gemini, custom LLM scripts) are missed.

**Why we expect it.**

> AI-generated first-pass reviews can reveal issues quickly and reduce time spent on routine feedback.
>
> — [dora-2025-state-of-ai-assisted-development](../references/dora-2025-state-of-ai-assisted-development/), p. 82 · direct

> AI serving as a first-pass reviewer that can identify potential bugs, style violations, security vulnerabilities, and performance issues before a human reviewer sees the code.
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 23 · supporting

> `claude -p "prompt"` runs once and exits, which is how Claude Code ends up in CI jobs, git hooks, and shell loops.
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Run Claude from a script · supporting

## ai.scoped_context: Large codebases give agents scoped, per-package context.

**How we check.** Counts non-test source files (excluding `vendor/`, `third_party/`, `docs/`, `examples/`, `.github/`); if over 300, looks for instruction files (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules`, `CLAUDE.local.md`) in any subfolder other than `.github/` and `.cursor/`.

- **Met:** Large repo with at least one nested instruction file.
- **Partially met:** never.
- **Not met:** Large repo with no nested instruction file (0.3).
- **Not applicable:** 300 or fewer source files.

**What the check cannot see.** A single nested file anywhere (even `docs/CLAUDE.md` or a personal `CLAUDE.local.md`) is Met for a 5,000-file monorepo. Whether packages are actually covered is not checked. Nested `.cursor/rules` folders are ignored.

**Why we expect it.**

> If a rule only matters in one part of the codebase, put it in `.claude/rules/` with a `paths:` filter so it only loads when Claude is actually working there.
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Scope rules to one part of the codebase · direct

> Place another AGENTS.md inside each package. Agents automatically read the nearest file in the directory tree
>
> — [agents-md](../references/agents-md/), 4. Large monorepo? Use nested AGENTS.md files for subprojects · direct

> Too much static context wastes tokens and dilutes signals. Too little means the agent forgets critical rules.
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 16 · supporting

## ai.mcp: External tools the project relies on are declared as MCP servers.

**How we check.** Any `.mcp.json` anywhere, root `.vscode/mcp.json` or `.cursor/mcp.json`.

- **Met:** One of those files exists.
- **Partially met:** never.
- **Not met:** None exists.

**What the check cannot see.** Contents are not read, so an empty file passes. The scanner cannot know whether the project relies on external tools, so a project that needs none is Not met rather than Not applicable.

**Why we expect it.**

> Adopt open standards for tools and inter-agent communication. Model Context Protocol (MCP) for tool access
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 45 · direct

> For systems without a CLI, there’s MCP.
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Connect the tools Claude needs · supporting

> An approach that intelligently selects, structures, and feeds only the most relevant context to the AI, rather than entire raw documents.
>
> — [dora-2025-ai-capabilities-model](../references/dora-2025-ai-capabilities-model/), p. 32 · supporting
