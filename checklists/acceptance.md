# SDLC 360° — acceptance criteria

How each expectation in `default.md` is judged, in plain language, and why we expect it.
The scanner reads this file: the texts appear in the report next to the evidence ("Expected", "How checked",
"Limits", "Basis"). Change the criteria here first, then the code in `src/dimensions/`, and keep both in step:
`tests/unit/test_checklist.py` fails when a check has no acceptance block.

Verdicts: a check scores 0–1. **Met** ≥ 0.85, **Partially met** ≥ 0.35, otherwise **Not met**; **Not applicable**
when the practice does not apply to the project. Sources `S01`…`S13` are in `docs/sources/` (see its README).
**Basis** quotes are verbatim; *direct* means the source asks for this practice, *supporting* that it argues
for the goal behind it. **Convention** marks expectations that are our own judgement, without an external source.

## architecture

### arch.doc — An architecture document describes components, data flow and boundaries.
- **Checks:** Files matching `ARCHITECTURE*` or `DESIGN.md` anywhere in the tree, or `docs/*architecture*`, `docs/*design*`, `docs/*overview*`, `doc/*architecture*` or `docs/arc42/*` at any depth. The extension must be `.md`, `.mdx`, `.rst`, `.adoc` or `.txt`.
- **Met:** At least one such file exists.
- **Partially met:** Never.
- **Not met:** No such file.
- **Limits:** Only the file name is checked, so an empty file passes. `docs/design-system/button.md` or an ADR with "design" in its name also passes. An architecture section inside the README is not counted.
- **Known gap:** The checklist says the document describes components, data flow and boundaries. The content is never read.
- **Basis:**
  - S01 · p. 22 (supporting) · "Given a clear architecture document, AI agents can scaffold entire applications, generate consistent patterns across modules, and ensure that new code conforms to established conventions."
  - S08 · p. 28 (supporting) · "proprietary company data, such as codebases, wikis, architectural diagrams, documentation, and style guides—all of which can be managed through manual and automated context engineering."

### arch.diagrams — Architecture diagrams are kept as code (Mermaid / PlantUML / C4).
- **Checks:** The first 400 tracked `.md`/`.mdx` files are searched for a code fence opening with `mermaid`, `plantuml`, `d2`, `dot` or `graphviz`. It also counts `*.puml`, `*.plantuml`, `*.drawio`, `*.excalidraw`, `*.d2`, `*.mmd`, `*.dsl` and `*.c4` files anywhere. The total is the number of markdown files with a fence plus the number of diagram files.
- **Met:** A total of 2 or more.
- **Partially met:** A total of exactly 1.
- **Not met:** Zero.
- **Limits:** A markdown file counts once, however many diagrams it holds. Any `.dsl` file counts, Structurizr or not. Diagrams in `.rst`/`.adoc` and exported PNG/SVG images are not seen. Nothing checks that a diagram shows the architecture.
- **Known gap:** The fence pattern has no word boundary, so a `dotenv` code fence (common in READMEs for env examples) counts as a Graphviz diagram.
- **Basis:**
  - S08 · p. 32 (supporting) · "The AI, using RAG to access the latest API specs, architectural diagrams, and the codebase itself, provides a step-by-step answer"

### arch.adr — Significant decisions are recorded as ADRs.
- **Checks:** Folders whose path or name matches `*adr`, `*adrs`, `*decisions`, `*decision-records` or `docs/architecture/decisions`. It counts the tracked `.md` files beneath them at any depth.
- **Met:** 3 or more markdown files.
- **Partially met:** Exactly 2.
- **Not met:** 0 or 1.
- **Limits:** README and template files in the folder count as ADRs, and content is not checked. A folder such as `design-decisions` for something unrelated counts. ADRs written as `.rst`/`.adoc`, or kept outside such folders, are missed.
- **Basis:**
  - S09 · SP 800-218 PW.1.2 Ex.2, p.20 (direct) · "Maintain records of design decisions, risk responses, and approved exceptions that can be used for auditing and maintenance purposes throughout the rest of the software life cycle."
  - S01 · p. 22 (supporting) · "The developer's role shifts from writing boilerplate to making and documenting the structural decisions that boilerplate implements."
  - S03 · Keep CLAUDE.md short (supporting) · "Decisions that aren’t in the repo: which error helper the team settled on, how deploys work, what needs a migration review"

### arch.structure — Source code is organised into modules, not a flat root.
- **Checks:** Source files (by extension, excluding tests, `vendor/`, `third_party/`, `docs/`, `examples/`, `.github/`). It counts how many sit in the repo root and whether any sit in a subfolder.
- **Met:** At least one source file in a subfolder and at most 5 source files in the root.
- **Partially met:** 6 to 15 source files in the root, or all code in the root with at most 15 files.
- **Not met:** More than 15 source files in the root (score 0.3).
- **Not applicable:** No source files at all.
- **Limits:** `.sh` and `.ps1` count as source, so root helper scripts count against the repo. One nested file (for example `scripts/x.sh`) is enough. A flat `src/` holding hundreds of files is Met. Module cohesion is not judged.
- **Basis:**
  - S04 · Context retrieval and agentic search (supporting) · "Folder hierarchies, naming conventions, and timestamps all provide important signals that help both humans and agents understand how and when to utilize information."
  - S09 · SP 800-218 PO.1.2 Ex.1, p.14 (supporting) · "Define policies that specify risk-based software architecture and design requirements, such as making code modular to facilitate code reuse and updates"

### arch.fresh — The architecture document is maintained alongside the code.
- **Checks:** The newest commit touching any arch.doc file is compared with the newest commit touching the first 2,000 source files.
- **Met:** The architecture doc lags the code by no more than about 80 days.
- **Partially met:** A lag of about 81 to 248 days, or unknown dates (scores 0.5).
- **Not met:** A lag of more than about 248 days, or no architecture doc.
- **Limits:** The newest matching file wins. Editing an unrelated `docs/*design*` page or fixing a typo counts as maintenance. Whether the content matches the code is not checked.
- **Convention:** An architecture document that lags the code misleads people and agents more than no document; we use the same staleness rule as for docs.

### arch.boundaries — Module boundaries are explicit and enforced by tooling.
- **Checks:** Files anywhere named `.importlinter`, `importlinter.ini`, `.dependency-cruiser.*`, `nx.json`, `turbo.json`, `pnpm-workspace.yaml`, `go.work`, `lerna.json` or `*.sln`. Also a root `pyproject.toml` containing the text "importlinter" or "tach", and `ArchUnit`/`ArchRule`/`NetArchTest`/`deptry` text in up to 500 test files. Score: 0.5 per file found, plus 0.5 for a test hit.
- **Met:** Two or more of those files, or one file plus a test hit.
- **Partially met:** Exactly one file, or only a test hit.
- **Not met:** Nothing found.
- **Not applicable:** 50 or fewer source files.
- **Limits:** Whether the rules are run in CI or actually enforced is not checked. deptry is usually configured in `pyproject.toml`, not tests, so it is rarely seen there.
- **Known gap:** Workspace files (`*.sln`, `nx.json`, `pnpm-workspace.yaml`, `go.work`, `lerna.json`) declare workspaces, they do not enforce boundaries. Two `.sln` files give Met. The "tach" text test also matches "attach", "detach" and so on anywhere in `pyproject.toml`.
- **Basis:**
  - S07 · p. 9 (supporting) · "We need to work within software architectures that give us independence of action—more than ever, we need to be able to develop, test, and deploy software independently."

## docs

### doc.readme — The README explains what the project is and how to start.
- **Checks:** Root-level files matching `README*` (any case or extension). If there are several, it takes the first in sorted order. It counts word tokens (`\w+` runs, so code and URLs count too).
- **Met:** A root README with at least 340 words (words/400 >= 0.85).
- **Partially met:** A root README with 140 to 339 words.
- **Not met:** No root README, or one with fewer than 140 words.
- **Limits:** Only length is measured. Pasted logs, badges, licence text or code blocks raise the count. A README in a subfolder is ignored. A translated `README.ja.md` sorts before `README.md` and can be the one measured.
- **Known gap:** The checklist says the README explains what the project is and how to start. The code checks only the word count.
- **Basis:**
  - S05 · Why AGENTS.md? (supporting) · "README.md files are for humans: quick starts, project descriptions, and contribution guidelines."

### doc.readme_sections — The README covers setup, usage, testing, configuration and overview.
- **Checks:** It searches the README's headings plus the first 30,000 characters of its text, lowercased, for six topics: install/setup, usage, testing (`\btest`), configuration, architecture/overview, and contributing/development.
- **Met:** All 6 topics are found (5 of 6 gives 0.83).
- **Partially met:** 3 to 5 topics are found.
- **Not met:** 0 to 2 topics are found, or there is no root README.
- **Limits:** A topic only needs its keyword somewhere in the text, not a section. "run ", "design", "config", "develop" or "example" anywhere is enough. The README's content is not read for meaning.
- **Known gap:** The checklist lists five topics. The code adds a sixth, contributing, and needs all six for Met.
- **Convention:** Setup, usage, testing, configuration and overview are the questions every newcomer, human or agent, asks first.

### doc.links — Docs reference files that actually exist.
- **Checks:** Up to 300 tracked `.md` files, excluding those under root `node_modules/` or `vendor/`. It takes relative markdown links and images (no scheme, no leading `/`, `<` or `~`, anchors dropped) and backticked paths that contain `/` and end in an extension or `/`. Each one is resolved from the file's folder or from the repo root.
- **Met:** At most 5% of references are broken (1 - 3*broken/total >= 0.85). Also Met when there are no references at all.
- **Partially met:** More than 5% and up to about 21.7% of references are broken.
- **Not met:** More than about 21.7% of references are broken.
- **Limits:** A file counts as existing if it is on disk, even untracked or git-ignored. A path ending matching any tracked file also resolves (`x/y.py` matches `src/pkg/x/y.py`). Paths in code examples are checked like real links. Links in `.mdx`/`.rst` files are never checked. Anchors and external URLs are not checked. A repo with no docs passes.
- **Convention:** A broken path in a doc sends readers and agents to files that no longer exist; it is the cheapest staleness signal to measure.

### doc.freshness — Docs are updated together with the code.
- **Checks:** The newest commit touching the root README or any docs page (as found by doc.docs_dir) is compared with the newest commit touching the first 2,000 source files.
- **Met:** Docs were last changed no more than about 80 days before the code (full score up to 30 days, then a linear fade to 0 at 365 days).
- **Partially met:** Docs lag the code by about 81 to 248 days. Also when either date is unknown (for example no source files or no history), which scores 0.5.
- **Not met:** Docs lag the code by more than about 248 days, or there is no README and no docs page.
- **Limits:** Only the single newest doc touch counts, so a typo fix anywhere resets the clock. It does not check that docs changed in the same commits or PRs as the code they describe.
- **Basis:**
  - S07 · p. 86 (supporting) · "AI could be used to identify outdated documentation, summarize long project discussions, and detect inconsistencies between what systems are doing and what documentation claims they do."
  - S08 · p. 24 (supporting) · "Ideally, this documentation and metadata (for example, table and column descriptions) are treated as a code artifact. They are versioned, live alongside the data"

### doc.docs_dir — Deeper documentation lives in a docs/ folder.
- **Checks:** It counts `.md`, `.mdx`, `.rst` and `.adoc` files at any depth under the root `docs/`, `doc/`, `documentation/` or `website/docs/`.
- **Met:** 3 or more pages.
- **Partially met:** Exactly 2 pages.
- **Not met:** 0 or 1 page (1/3 = 0.33).
- **Limits:** Only the count matters, so empty stubs and ADRs count. Docs in nested packages, other folder names, wikis or external sites are not seen.
- **Convention:** Deeper material belongs in versioned docs next to the code rather than in a wiki the agent cannot read.

### doc.standard_files — LICENSE, CONTRIBUTING and CHANGELOG are present.
- **Checks:** Basename matches anywhere in the tree for LICENSE (`LICENSE*`, `COPYING*`), CONTRIBUTING (`CONTRIBUTING*`) and CHANGELOG (`CHANGELOG*`, `CHANGES*`, `HISTORY*`, `RELEASES*`).
- **Met:** All 3 are found.
- **Partially met:** 2 of the 3 are found.
- **Not met:** 0 or 1 is found.
- **Limits:** The files can sit in any folder, including vendored or fixture folders. Content is not read.
- **Known gap:** The patterns match any file whose basename starts with those words. A source file such as `history.py`, `changes.ts`, `releases.go` or `license_check.py` satisfies the check.
- **Basis:**
  - S12 · License (direct) · "The lack of a license will impede any kind of security review or audit and creates a legal risk for potential users."

### doc.inline — Public code is documented inline (docstrings / doc comments).
- **Checks:** If there is any Python source, it takes up to 400 `.py` source files. It counts `def` and `class` headers with a non-underscore name whose `:` ends the line, then checks whether the next line opens a `"""` or `'''` docstring. Without Python, it takes up to 400 `.ts`, `.tsx`, `.js`, `.go`, `.rs`, `.java`, `.cs` or `.kt` files. A file counts if it contains `/**`, a `///` line or `// Capitalword `.
- **Met:** Python: at least 51% of the counted definitions have docstrings. Other languages: at least 42.5% of files have a doc comment.
- **Partially met:** Python: 21% to 50%. Other languages: 17.5% to 42.4%.
- **Not met:** Python below 21%. Other languages below 17.5%.
- **Not applicable:** Python source exists but no definition header matched. If the repo has neither Python nor the listed languages, the check is not produced and drops out of the report.
- **Limits:** Multi-line signatures (common after black or ruff format), one-line defs and headers with trailing comments are skipped entirely. Prefixed docstrings (`r"""`) are missed. Any comment starting `// TODO ` counts as a doc comment. `.jsx`, `.rb`, `.php` and C/C++ are never examined.
- **Known gap:** Python always wins. A mostly TypeScript or Go repo with one `.py` script is judged only on that Python file.
- **Convention:** Docstrings are the context an agent reads at the point of change; public code without them is guessed at.

## harness

### ai.instructions — The repo has an agent instruction file (CLAUDE.md / AGENTS.md).
- **Checks:** Tracked files with the exact (case-sensitive) name `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules` anywhere, `.github/copilot-instructions.md`, and files under root `.cursor/rules/`. `CLAUDE.local.md` is personal configuration (see `ai.no_local_leak`) and does not count.
- **Met:** One of those files sits at the repo root or under `.github/`.
- **Partially met:** Only nested ones exist (e.g. `pkg/CLAUDE.md`) or only `.cursor/rules/*` files.
- **Not met:** None found.
- **Limits:** Contents are not judged here; an empty `CLAUDE.md` passes. Lower-case `claude.md` is not recognised.
- **Basis:**
  - S01 · p. 43 (direct) · "Set up an AGENTS.md (or equivalent) for the project. Pick the convention that matches the coding agent of choice."
  - S03 · Tell Claude what it can’t see (direct) · "Only write down what Claude can’t find by reading the repo, or what it would otherwise spend time rediscovering every session."
  - S05 · How to use AGENTS.md? (direct) · "Create an AGENTS.md file at the root of the repository."

### ai.instructions_quality — The instruction file states build/test commands, layout and conventions.
- **Checks:** The main file: `CLAUDE.md`, else `AGENTS.md`, else `.github/copilot-instructions.md`, else the first root/.github instruction file. Symlinks are followed, as are up to 5 `@file.md` import lines. In headings plus the first 20,000 characters it looks for four topics: commands (build/run/install/make/npm/pip/cargo…), testing (`test…`), layout (architect/structure/layout/directory/module), conventions (convention/style/guideline/rule/must/never/always). It also counts lines.
- **Met:** All four topics are present and the combined text is 8–800 lines.
- **Partially met:** Everything else between the extremes, e.g. three topics at any size, all four but under 8 or over 800 lines, or one topic in a 25–400-line file.
- **Not met:** No root-level instruction file, no topic words at all, or only one topic in a file under 8 or over 800 lines.
- **Limits:** Keywords are common English words ("run", "test", "must", "always"), so almost any prose scores on all four. No command is checked for correctness. The main file may be an untracked file that exists only on disk. Nested-only instruction files score 0 here.
- **Known gap:** The checklist says the file "states build/test commands"; the code only looks for words like "run" or "test", not actual commands.
- **Basis:**
  - S01 · p. 43 (direct) · "Start with ten lines: stack, conventions, hard rules, workflow. Add a rule every time the agent does something it should not do again."
  - S03 · Keep CLAUDE.md short (direct) · "How to confirm work in this repo: the exact test, typecheck, and lint commands, and how to run a single test file"
  - S05 · 2. Cover what matters (direct) · "Add sections that help an agent work effectively with your project. Popular choices: … Build and test commands … Code style guidelines"

### ai.instructions_fresh — The instruction file matches the current code (no stale paths).
- **Checks:** In the main file (or the imported file for a ≤3-line wrapper): relative markdown links and backticked paths with an extension or trailing slash. Each must resolve from the file's folder, the repo root, or as a path suffix of any file. Also compares the file's last commit with the latest commit touching source code. Score = 0.6 × share of paths resolving + 0.4 × freshness (1.0 within 30 days, falling to 0 at 365 days behind).
- **Met:** Score ≥ 0.85, e.g. all paths resolve and the file was updated within ~155 days of the last code change, or at least 75% resolve and it is within 30 days.
- **Partially met:** Score 0.35–0.85, e.g. all paths resolve but the file is a year behind (0.6), or half resolve and it is fresh (0.7).
- **Not met:** No root instruction file, or most paths are broken and the file is stale (e.g. all broken and more than ~72 days behind).
- **Limits:** The suffix fallback is lenient (`x/y.py` matches any `.../x/y.py`). Paths in fenced code without backticks, and stale commands, are not checked. Any trivial commit to the file resets freshness. References in `@`-imported files are ignored unless the main file is a thin wrapper.
- **Known gap:** If freshness cannot be computed (no source files or no dates), it defaults to 0.5, so the best possible score is 0.8. A docs-only repo with perfect references can never be Met.
- **Basis:**
  - S05 · FAQ: Can I update it later? (direct) · "Absolutely. Treat AGENTS.md as living documentation."
  - S01 · p. 44 (supporting) · "Treat AGENTS.md, system prompts, eval suites, and skill libraries as code … Without this discipline, the harness drifts and agent behaviour becomes irreproducible across the team."
  - S03 · Keep CLAUDE.md short (supporting) · "`/doctor prompt-audit` flags instructions that were written for older models, point at files that no longer exist, or contradict each other."

### ai.settings — Shared agent settings define what agents may and may not do.
- **Checks:** Root `.claude/settings.json`, parsed as JSON for a non-empty `permissions` key.
- **Met:** The file exists and has a non-empty `permissions` entry.
- **Partially met:** The file exists but has no `permissions`, or is not valid JSON (0.5).
- **Not met:** No `.claude/settings.json`.
- **Limits:** The rules are not read: an allow-everything policy passes. Other agents' settings (Codex, Cursor, Copilot) are not considered.
- **Known gap:** The checklist says settings define what agents "may and may not do"; deny rules are not required, any non-empty `permissions` passes.
- **Basis:**
  - S03 · Choose who a rule applies to (direct) · "`.claude/settings.json` and the hooks in it belong to the repo. Once you commit them, they apply to everyone who works in the repo."
  - S10 · ASI05 guideline 6, p.24 (direct) · "Access control and approvals: Require human approval for elevated runs; keep an allowlist for auto-execution under version control; enforce role and action-based controls."
  - S01 · p. 29 (supporting) · "The developer defines the tools the agent will have access to (like specific APIs or database schemas) and sets the fundamental rules the agent cannot break."

### ai.guardrails — Hooks enforce formatting, linting and tests automatically.
- **Checks:** A non-empty `hooks` key in `.claude/settings.json`. Otherwise any file under root `.claude/hooks/` or `.husky/`, or any `.pre-commit-config.yaml` / `lefthook.yml` anywhere.
- **Met:** `.claude/settings.json` declares agent hooks.
- **Partially met:** No agent hooks, but one of those hook files exists (0.6).
- **Not met:** Neither.
- **Limits:** What the hooks run is never inspected. Hooks in `settings.local.json` or plugins are not seen. `lefthook.yaml` / `.lefthook.yml` are missed (security reads `.lefthook.yml`).
- **Known gap:** The checklist says hooks enforce formatting, linting and tests; the code never checks what they do, and a full pre-commit setup can never be Met without Claude agent hooks.
- **Basis:**
  - S01 · p. 28 (direct) · "Deterministic code that runs at specific lifecycle points: before a tool call, after a file edit, before a commit. Hooks are the place for things the agent should never forget"
  - S03 · Enforce the rules that can’t have exceptions (direct) · "If something has to happen every time, make it a hook, a deny rule, or a managed setting."
  - S07 · p. 40 (supporting) · "an increase in change volume without a corresponding set of evolved guardrails, roles, and “golden paths” could increase verification and coordination costs."

### ai.no_local_leak — Personal agent settings are not committed.
- **Checks:** Tracked files ending in `.claude/settings.local.json` or `CLAUDE.local.md` (case-sensitive, any depth).
- **Met:** None is tracked.
- **Partially met:** never.
- **Not met:** At least one is tracked.
- **Limits:** Other personal files (`.vscode/settings.json`, `.cursor/` user rules, `.env.local`) are not checked. When scanning a non-git folder, ignored local files on disk are flagged too.
- **Basis:**
  - S03 · Keep CLAUDE.md short (direct) · "Your personal preferences go in `CLAUDE.local.md` instead of `CLAUDE.md`, and you add that file to `.gitignore` so it stays out of the repo."

### ai.extensions — Repeated workflows are packaged as skills, subagents or commands.
- **Checks:** Counts files at any depth under the root folders `.claude/skills/`, `.claude/agents/` (`.md`), `.claude/commands/` (`.md`), `.github/prompts/` (`.md`), `.github/chatmodes/`, `.github/instructions/`, `.github/agents/`, `.cursor/rules/`, `.codex/`, `.claude-plugin/`, `.agents/skills/`, `.agents/agents/`.
- **Met:** Three or more such files.
- **Partially met:** Exactly two files.
- **Not met:** One file or none.
- **Limits:** Counts files, not workflows: one skill with a `SKILL.md` and two reference files is Met. `.claude-plugin/plugin.json` counts. Root-level `skills/`, `agents/`, `commands/` folders and nested packages' `.claude/` folders are not counted (unlike `sk.present`).
- **Basis:**
  - S01 · p. 45 (direct) · "Reusable system prompts, skill libraries, MCP server connections, and evaluation harnesses compound across projects. Treat them as infrastructure: documented, maintained, and improved deliberately."
  - S03 · Put team procedures in skills (supporting) · "A more capable model knows more about engineering, but not how your team does a release, what your incident runbook says, or how you want API docs written."
  - S04 · Sub-agent architectures (supporting) · "specialized sub-agents can handle focused tasks with clean context windows."

### ai.ci_agents — AI agents are wired into CI for review or triage.
- **Checks:** Text of `.github/workflows/*` (not delegated scripts) for `anthropics/claude-code-action`, `claude-code-base-action`, `openai/codex-action`, `coderabbit` or `copilot`, case-insensitive.
- **Met:** Any of those strings appears.
- **Partially met:** never.
- **Not met:** None appears.
- **Limits:** "copilot" anywhere (a comment, job name, branch filter) counts. AI reviewers installed as GitHub Apps or repo settings (Copilot review, CodeRabbit app, `.coderabbit.yaml`) are invisible. Other actions (Gemini, custom LLM scripts) are missed.
- **Basis:**
  - S07 · p. 82 (direct) · "AI-generated first-pass reviews can reveal issues quickly and reduce time spent on routine feedback."
  - S01 · p. 23 (supporting) · "AI serving as a first-pass reviewer that can identify potential bugs, style violations, security vulnerabilities, and performance issues before a human reviewer sees the code."
  - S03 · Run Claude from a script (supporting) · "`claude -p "prompt"` runs once and exits, which is how Claude Code ends up in CI jobs, git hooks, and shell loops."

### ai.scoped_context — Large codebases give agents scoped, per-package context.
- **Checks:** Counts non-test source files (excluding `vendor/`, `third_party/`, `docs/`, `examples/`, `.github/`); if over 300, looks for instruction files (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules`, `CLAUDE.local.md`) in any subfolder other than `.github/` and `.cursor/`.
- **Met:** Large repo with at least one nested instruction file.
- **Partially met:** never.
- **Not met:** Large repo with no nested instruction file (0.3).
- **Not applicable:** 300 or fewer source files.
- **Limits:** A single nested file anywhere (even `docs/CLAUDE.md` or a personal `CLAUDE.local.md`) is Met for a 5,000-file monorepo. Whether packages are actually covered is not checked. Nested `.cursor/rules` folders are ignored.
- **Basis:**
  - S03 · Scope rules to one part of the codebase (direct) · "If a rule only matters in one part of the codebase, put it in `.claude/rules/` with a `paths:` filter so it only loads when Claude is actually working there."
  - S05 · 4. Large monorepo? Use nested AGENTS.md files for subprojects (direct) · "Place another AGENTS.md inside each package. Agents automatically read the nearest file in the directory tree"
  - S01 · p. 16 (supporting) · "Too much static context wastes tokens and dilutes signals. Too little means the agent forgets critical rules."

### ai.mcp — External tools the project relies on are declared as MCP servers.
- **Checks:** Any `.mcp.json` anywhere, root `.vscode/mcp.json` or `.cursor/mcp.json`.
- **Met:** One of those files exists.
- **Partially met:** never.
- **Not met:** None exists.
- **Limits:** Contents are not read, so an empty file passes. The scanner cannot know whether the project relies on external tools, so a project that needs none is Not met rather than Not applicable.
- **Basis:**
  - S01 · p. 45 (direct) · "Adopt open standards for tools and inter-agent communication. Model Context Protocol (MCP) for tool access"
  - S03 · Connect the tools Claude needs (supporting) · "For systems without a CLI, there’s MCP."
  - S08 · p. 32 (supporting) · "An approach that intelligently selects, structures, and feeds only the most relevant context to the AI, rather than entire raw documents."

## skills

### sk.present — Reusable agent procedures exist as markdown skills / subagents / commands.
- **Checks:** Counts files named `SKILL.md` anywhere (case-insensitive), `.md` under root `.claude/agents/`, `agents/`, `.github/agents/`, `.md` under `.claude/commands/` and `commands/`, `.github/prompts/*.prompt.md`, `.cursor/rules/*.mdc` and `.github/instructions/*.instructions.md`.
- **Met:** Three or more such files.
- **Partially met:** Exactly two.
- **Not met:** One or none.
- **Limits:** Any markdown in a root `agents/` or `commands/` folder counts (e.g. a `README.md` or design notes). A `SKILL.md` under `agents/` is counted twice. File quality is not judged here.
- **Basis:**
  - S01 · p. 17 (direct) · "The most powerful pattern for managing dynamic context is Agent Skills: structured, portable packages of procedural knowledge that the agent loads only when the task calls for it."
  - S03 · Put team procedures in skills (direct) · "That kind of knowledge goes in a skill: a procedure or a piece of team knowledge saved at `.claude/skills/<name>/SKILL.md`."
  - S08 · p. 31 (direct) · "Create a shared, version-controlled library of these reusable context templates or briefing packets for common tasks."

### sk.frontmatter — Every skill declares a name and description in frontmatter.
- **Checks:** Each file found by `sk.present`: it must start with a `---` YAML block. Skills and subagents need non-empty `name` and `description`; commands, prompts and rules need only `description`.
- **Met:** At least 85% of the files have the required fields.
- **Partially met:** 35–84% do.
- **Not met:** Under 35% do.
- **Not applicable:** No skill/agent/command/rule files exist.
- **Limits:** The parser is minimal: a BOM or blank line before `---` means "no frontmatter". Kebab-case `name` (mentioned in the recommendation) is not enforced. Values are not validated beyond being non-empty.
- **Known gap:** The checklist says "every skill declares a name"; command, prompt and rule files pass without one.
- **Basis:**
  - S06 · SKILL.md format (direct) · "The `SKILL.md` file must contain YAML frontmatter followed by Markdown content."
  - S03 · Put team procedures in skills (supporting) · "For a skill Claude can start on its own, it sees the name and description in every session, but only reads the full file when the task calls for it."

### sk.descriptions — Descriptions say what the skill does and when to use it.
- **Checks:** Each file's frontmatter `description`: length 40–1024 characters and contains "use when/this/for/to", the word "when", or "trigger…"/"invoke…".
- **Met:** At least 85% of files have such a description.
- **Partially met:** 35–84%.
- **Not met:** Under 35% (missing descriptions count as failures).
- **Not applicable:** No skill/agent/command/rule files exist.
- **Limits:** The word "when" anywhere passes, even in "what happens when it fails". The "what it does" half is not checked at all.
- **Known gap:** The checklist asks for what AND when; only a "when"-style keyword plus length is checked.
- **Basis:**
  - S06 · `description` field (direct) · "Should describe both what the skill does and when to use it"
  - S03 · Know what subagents cost (supporting) · "description: Reviews changed files against the spec they were built from. Use after implementing a feature, before opening the PR."
  - S04 · The anatomy of effective context (supporting) · "If a human engineer can’t definitively say which tool should be used in a given situation, an AI agent can’t be expected to do better."

### sk.links — Links and scripts referenced by skills exist.
- **Checks:** In every skill/agent/command/rule file: relative markdown links and backticked paths with an extension or trailing slash. Each must resolve from the file's folder, the repo root, or as a path suffix of any file. URLs and absolute paths are ignored.
- **Met:** At least 85% of references resolve, or there are no references.
- **Partially met:** 35–84% resolve.
- **Not met:** Under 35% resolve.
- **Not applicable:** No skill/agent/command/rule files exist.
- **Limits:** Scripts named inside fenced code blocks without backticks around the path (e.g. `python scripts/run.py` as a whole command line) are not checked. The suffix fallback can match an unrelated file with the same tail. Files with no references score as fully OK.
- **Basis:**
  - S06 · File references (supporting) · "When referencing other files in your skill, use relative paths from the skill root"

### sk.size — Skills stay concise and push detail into references.
- **Checks:** Line count (including frontmatter) of every skill/agent/command/rule file; over 500 lines counts as oversized.
- **Met:** At most 15% of files are oversized.
- **Partially met:** 16–65% are oversized.
- **Not met:** More than 65% are oversized.
- **Not applicable:** No skill/agent/command/rule files exist.
- **Limits:** Counts lines, not words or tokens: a 400-line file of very long lines passes.
- **Known gap:** The checklist says skills "push detail into references"; that is not checked here (only `sk.layout` rewards reference folders).
- **Basis:**
  - S06 · Progressive disclosure (direct) · "Keep your main `SKILL.md` under 500 lines. Move detailed reference material to separate files."
  - S01 · p. 17 (supporting) · "The agent sees only lightweight metadata at startup, loads full instructions when a task matches, and pulls deep reference material only when explicitly needed."
  - S03 · Put team procedures in skills (supporting) · "The `CLAUDE.md` rule applies to skills too: only write down what Claude can’t find on its own."

### sk.layout — Skills follow one layout and kebab-case naming.
- **Checks:** For each `SKILL.md`, whether its parent folder name is lowercase kebab-case (and the file is named exactly `SKILL.md`). Also whether any file exists under `*/skills/<name>/scripts/`, `references/` or `assets/`. Score = 0.6 × share of well-named skills + 0.4 if any supporting file exists.
- **Met:** Supporting files exist and at least 75% of skill folders are kebab-case.
- **Partially met:** No supporting files but at least 58% kebab-case (max 0.6); or supporting files with under 75% kebab-case; or there are agents/commands but no `SKILL.md` at all (fixed 0.5).
- **Not met:** No supporting files and under 58% of skill folders are kebab-case.
- **Not applicable:** No skill/agent/command/rule files exist.
- **Limits:** A lower-case `skill.md` or a root `SKILL.md` counts as badly named. Folder placement (`.claude/skills/` vs elsewhere) is not checked, so "one layout" is not enforced.
- **Known gap:** The `*/skills/...` pattern needs something before `skills/`, so a root-level `skills/<name>/scripts/` (the layout the recommendation suggests) is never detected. Also, skills that need no scripts/references can never be Met.
- **Basis:**
  - S06 · `name` field (direct) · "May only contain unicode lowercase alphanumeric characters (`a-z`, `0-9`) and hyphens (`-`)"

## hygiene

### hyg.lint — A linter is configured.
- **Checks:** Matched by name anywhere: `ruff.toml`, `.ruff.toml`, `.flake8`, `.pylintrc`, `pylintrc`, `.eslintrc*`, `eslint.config.*`, `biome.json*`, `.golangci.y*ml`, `clippy.toml`, `.rubocop.yml`, `detekt.yml`, `.editorconfig`, `stylecop.json`, `.swiftlint.yml`, `deno.json`. Also `[tool.ruff`/`[tool.pylint`/`[tool.flake8` in the root `pyproject.toml`, or `"eslint…`/`"@biomejs…` in the root `package.json`.
- **Met:** Any one of these is found.
- **Partially met:** never
- **Not met:** None found.
- **Limits:** The scanner checks that a config exists, not that the linter runs. A config in a vendored or sub-project folder counts. It misses `[flake8]` in `setup.cfg`/`tox.ini`, ruff run with defaults, `.golangci.toml`, and Cargo `[lints]`.
- **Known gap:** `.editorconfig` is in the linter list, so any repo with an `.editorconfig` is Met for "A linter is configured".
- **Basis:**
  - S09 · SP 800-218 PW.5.1 Ex.7, p.22 (direct) · "Use tools (e.g., linters, formatters) to standardize the style and formatting of the source code."
  - S11 · Programming Language-Specific Security Examples > Python and Dynamic Languages (supporting) · "Additionally, mention type checking or the use of linters"

### hyg.format — An auto-formatter is configured.
- **Checks:** Matched by name anywhere: `.prettierrc*`, `prettier.config.*`, `rustfmt.toml`, `.rustfmt.toml`, `.clang-format`, `dprint.json`. Also `[tool.black`/`[tool.ruff.format`/`[tool.isort` in the root `pyproject.toml`, any `go.mod` (gofmt), `"prettier…`/`"@biomejs…` in the root `package.json`, a biome config found by `hyg.lint`, or any `[tool.ruff` section in `pyproject.toml`.
- **Met:** Any one is found.
- **Partially met:** never
- **Not met:** None found.
- **Limits:** Any `[tool.ruff` section counts as "ruff format", even lint-only, but a standalone `ruff.toml` does not. Every Go module passes automatically, and Rust passes only with a `rustfmt.toml`. The scanner never checks enforcement in CI or hooks.
- **Basis:**
  - S09 · SP 800-218 PW.5.1 Ex.7, p.22 (direct) · "Use tools (e.g., linters, formatters) to standardize the style and formatting of the source code."

### hyg.types — Static typing is enforced.
- **Checks:** If any `.py` source file exists (the Python branch wins over TS): type-checker config (`[tool.mypy`/`[tool.pyright`/`[tool.basedpyright` in root `pyproject.toml`, or `mypy.ini`, `.mypy.ini`, `pyrightconfig.json` anywhere). It also counts the share of the first 300 Python source files with at least one annotated parameter or `->` return. Score = 0.5 x config + 0.5 x min(1, share / 0.7). Otherwise, if any JS/TS source file exists: score = 0.6 x any `tsconfig*.json` + 0.4 x any of them containing `"strict": true`.
- **Met:** Python: checker config AND at least 49% of files annotated. TS/JS: a tsconfig with `"strict": true`.
- **Partially met:** Python: config with under 49% annotated, or no config but at least 49% annotated. TS/JS: tsconfig without `strict: true` (0.6).
- **Not met:** Python: no config and under 49% annotated. TS/JS: no `tsconfig*.json` (e.g. plain JS).
- **Not applicable:** No Python and no JS/TS source files (e.g. Go, Rust, Java, Ruby, PHP).
- **Limits:** The scanner never checks that the checker runs (CI/pre-commit) or how strict it is. `->` anywhere in a file, even in comments or strings, counts as annotated. One script `.py` in a TS repo switches to the Python branch. `strict` inherited via `extends` from a package is missed.
- **Known gap:** The checklist says typing is "enforced", but only config presence and annotation share are checked. Ruby, PHP, Lua and shell are dynamically typed yet not applicable (evidence says "no dynamically-typed code").
- **Basis:**
  - S11 · TL;DR Sample Instructions (supporting) · "For Python, follow PEP 8 and use type hints, as this can catch misuse early."

### hyg.precommit — Pre-commit hooks run format and lint locally.
- **Checks:** Matched by name anywhere: `.pre-commit-config.yaml`, `lefthook.yml`, `.lefthook.yml`, `lint-staged.config.*`, `.lintstagedrc*`, plus any file under root `.husky/`.
- **Met:** Any one is found.
- **Partially met:** never
- **Not met:** None found.
- **Limits:** Hook contents are not read. Husky/lint-staged configured inside `package.json`, `lefthook.yaml`, and `.pre-commit-config.yml` are missed.
- **Known gap:** The checklist says hooks "run format and lint locally". The code only checks that a hook config file exists.
- **Basis:**
  - S09 · SP 800-218 PW.5.1 Ex.5, p.22 (supporting) · "Use development environments with automated features that encourage or require the use of secure coding practices with just-in-time training-in-place."

### hyg.file_size — No oversized source files.
- **Checks:** On-disk size of the first 3000 source files (tests, vendor/, third_party/, docs/, examples/ and .github/ excluded). Files over 60,000 bytes are oversized. Score = 1 − min(1, oversized / D), where D = max(5, 5% of all source files).
- **Met:** Up to 100 source files: none oversized. Over 100: oversized files are at most 0.75% of source files.
- **Partially met:** Up to 100 source files: 1–3 oversized. Over 100: more than 0.75% and at most 3.25%.
- **Not met:** Up to 100 source files: 4 or more oversized. Over 100: above 3.25%.
- **Limits:** Generated or minified source (bundled `.js`, protobuf stubs) counts. Big non-source files (JSON, notebooks, markdown) and tests are ignored. A repo with no source files is Met.
- **Convention:** Very large files hurt human review and overflow agent context budgets (see S04 on limited attention).

### hyg.editor — .editorconfig / .gitattributes keep formatting consistent.
- **Checks:** Files named `.editorconfig` or `.gitattributes` anywhere. Score = number of such files / 2, with no cap.
- **Met:** 2 or more such files.
- **Partially met:** Exactly 1 (0.5).
- **Not met:** None.
- **Limits:** File contents are not read.
- **Known gap:** The scanner counts files, not the two kinds. Two `.gitattributes` in different folders meet it with no `.editorconfig`. The score is not capped: 3 files give 1.5, above the 0..1 range.
- **Convention:** Shared line-ending and whitespace rules prevent noisy diffs between Windows, Linux and agent-generated edits.

### hyg.templates — PR and issue templates guide contributors.
- **Checks:** Files at `.github/pull_request_template.md`, `.github/PULL_REQUEST_TEMPLATE*` (including that folder), `.github/ISSUE_TEMPLATE/*` (including `config.yml`) and `docs/pull_request_template.md`. Score = min(1, count / 2).
- **Met:** 2 or more matching files.
- **Partially met:** Exactly 1.
- **Not met:** None.
- **Limits:** A root-level `pull_request_template.md` (supported by GitHub) is missed, and so are org-wide templates from a `.github` repository. Template content is not checked.
- **Known gap:** The checklist says "PR and issue templates", but two issue-template files (or one plus `config.yml`) meet it with no PR template.
- **Convention:** PR and issue templates turn the review checklist into a habit; a nice-to-have sign of maturity.

## tests

### test.present — The project has an automated test suite.
- **Checks:** Tracked source-extension files under a `test/`, `tests/`, `__tests__/`, `spec/`, `specs/`, `e2e/` or `integration_test(s)/` folder, or named `test_*`, `*_test.*`, `*.test.*`, `*.spec.*` or `*test(s).cs/java/kt`. It counts files.
- **Met:** 5 or more test files.
- **Partially met:** 2 to 4 test files.
- **Not met:** 0 or 1 test file.
- **Limits:** It counts files, not tests: `conftest.py`, helpers, fixtures and empty files count. Vendored tests count. Names such as `latest.java` or `contest.cs` count as tests. Whether the tests run or pass is not checked.
- **Basis:**
  - S01 · p. 43 (direct) · "Write the tests and evals before generating the code. Together they are the contract with the AI."
  - S03 · Give Claude a check to run (direct) · "Give Claude something it can run that comes back pass or fail."
  - S09 · SP 800-218 PW.8.2, p.24 (direct) · "Scope the testing, design the tests, perform the testing, and document the results"

### test.ci — Tests run in CI on every push and pull request.
- **Checks:** It searches `ci_text` (GitHub workflow YAML plus the scripts/Makefile/nox/tox/package.json/pyproject they delegate to) for a test command such as `pytest`, `tox`, `nox`, `npm test`, `jest`, `go test`, `cargo test`, `mvn test`, `dotnet test` or `make test`.
- **Met:** Any test command is found in that text.
- **Partially met:** None is found, but `.gitlab-ci.yml`, `Jenkinsfile`, `azure-pipelines.yml` or `.circleci/config.yml` exists (scores 0.5, file not read).
- **Not met:** Neither.
- **Limits:** This is a plain substring match. `pip install pytest` in a lint job counts. A delegated `Makefile` or `pyproject.toml` is read whole, so `pytest` listed as a dependency or in an unused make target counts. Bitbucket and Travis configs are ignored here.
- **Known gap:** The checklist says "on every push and pull request". Triggers are not checked, so a test step in a nightly-only or manual workflow is Met.
- **Basis:**
  - S07 · p. 72 (direct) · "whether code is created by hand or by AI, the same automated testing and deployment processes are applied"
  - S08 · p. 39 (direct) · "the convergent process of code review and automated testing is necessary to ensure that changes conform to organizational standards"
  - S09 · SP 800-218A PW.8.1.C1, p.25 (direct) · "Consider automating tests within a development pipeline as part of regression testing where possible."

### test.ratio — Tests grow with the code (healthy test-to-source ratio).
- **Checks:** The number of test files (as in test.present) divided by the number of source files.
- **Met:** A ratio of 0.34 or more (ratio/0.4 >= 0.85).
- **Partially met:** A ratio of 0.14 to 0.33.
- **Not met:** A ratio below 0.14.
- **Not applicable:** No source files.
- **Limits:** It counts files, not lines or tests. Vendored tests inflate the ratio. Shell scripts count as source. One large test file per many modules looks weak even if coverage is high.
- **Basis:**
  - S05 · README: Sample AGENTS.md file / Testing instructions (supporting) · "Add or update tests for the code you change, even if nobody asked."

### test.coverage — Coverage is measured and a minimum is enforced.
- **Checks:** Coverage files anywhere (`.coveragerc`, `codecov.yml`, `.codecov.yml`, `coverage.config.*`, `.nycrc*`, `jacoco*`, `tarpaulin.toml`). Coverage keywords (`--cov`, `coverage run`, `--coverage`, `codecov`, `coveralls`, `fail_under` and others) in the root `pyproject.toml`, `package.json`, `ci_text` or any `Makefile`/`justfile`. Threshold keywords (`fail_under`, `fail-under`, `coverageThreshold`, `--cov-fail-under`, `minimum_coverage`) are searched in the same places and in the coverage files. Score: 0.6 if measured, plus 0.4 if a threshold is found.
- **Met:** Coverage is measured and a threshold keyword is found.
- **Partially met:** Measured without a threshold (0.6), or a threshold keyword alone (0.4).
- **Not met:** No coverage file or keyword.
- **Limits:** The threshold value is not checked, so `fail_under = 0` passes. A local-only config with no CI step can pass. Thresholds kept in `jest.config.*`/`vitest.config.*` or as a Codecov `target:` are not seen.
- **Basis:**
  - S01 · p. 44 (supporting) · "Require eval coverage with explicit rubrics as a precondition for any agent shipping into a shared workflow, the same way test coverage gates a service deployment."
  - S13 · §I Introduction, p.1 (supporting) · "does not include generic software engineering best practices such as ensuring good unit test coverage … Such strategies remain necessary as well."

### test.framework — The test runner is configured explicitly.
- **Checks:** Anywhere in the tree: `pytest.ini`, `conftest.py`, `tox.ini`, `noxfile.py`, `jest/vitest/playwright/cypress` configs, `karma.conf.*`, `.mocharc*`, `phpunit.xml*` or `*.runsettings`. Also `[tool.pytest` in the root `pyproject.toml`, a `"test":` key in the root `package.json`, a `*_test.go` test file, or a root `Cargo.toml` alongside test files.
- **Met:** Test files exist and at least one of these is found.
- **Partially met:** Never.
- **Not met:** No test files, or none of the above.
- **Limits:** Whether the config works is not checked. The npm-init placeholder `"test": "echo \"Error: no test specified\" && exit 1"` passes. A lone `conftest.py` passes.
- **Known gap:** There is no detection for Maven/Gradle (JUnit in `pom.xml`/`build.gradle`), RSpec (`.rspec`, `spec_helper.rb`), .NET test projects without `.runsettings`, or plain `unittest`. Those repos are Not met even when the runner is configured.
- **Convention:** An explicitly configured test runner gives humans and agents one unambiguous command and test discovery rule.

### test.layers — Beyond unit tests there are integration / e2e / property tests.
- **Checks:** It searches the test file paths plus the root `pyproject.toml` and `package.json` for three layers: integration (`integration`), e2e (`e2e`, `end.to.end`, `playwright`, `cypress`, `selenium`) and property/fuzz (`hypothesis`, `fast-check`, `proptest`, `quickcheck`, `fuzz`).
- **Met:** 2 or 3 layers are detected.
- **Partially met:** Exactly 1 layer.
- **Not met:** None, or no test files.
- **Limits:** It matches names and dependency lists, not real tests. A `hypothesis` dependency or an "integration" folder name counts even if empty. Layers named differently (`acceptance`, `system`, `smoke`) are missed.
- **Known gap:** The checklist asks for integration/e2e/property tests "beyond unit tests", which one layer satisfies. The code needs two layers for Met.
- **Basis:**
  - S13 · Infra 3, p.5 (direct) · "there must be a fully automated test that runs regularly and exercises the entire pipeline"
  - S01 · p. 23 (supporting) · "Agents can produce test cases, including edge cases and property-based tests, that humans might not think of."
  - S09 · SP 800-218A PW.8.1.R1, p.25 (supporting) · "Several forms of code testing can be used for AI models, including unit testing, integration testing, penetration testing, red teaming, use case testing, and adversarial testing."

## security

### sec.no_secrets — No secrets or API keys are hard-coded in tracked files.
- **Checks:** Every tracked, non-binary text file up to 500 KB at HEAD, line by line (lines over 2000 chars skipped). Skips lock files, `*.min.js`, `*.map`, `*.svg` and `fixture(s)/`, `testdata/`, `__snapshots__/` folders. Looks for AWS, GitHub, Anthropic, OpenAI, Slack, Google, Stripe-live tokens, private-key blocks, and "generic" quoted values of 16+ chars assigned to names like `api_key`, `password`, `client_secret`.
- **Met:** No finding at all. Values that look like placeholders (contain `example`, `test`, `dummy`, `xxxx`, `${`, `process.env`, …) are ignored; generic values must mix letters and digits, have 6+ distinct characters, and are ignored entirely in test files.
- **Partially met:** No real-format token outside tests, but either a generic assigned secret was found (score 0.5) or real-format tokens appear only in test files (0.75).
- **Not met:** At least one real-format token (AWS, GitHub, private key block, etc.) in a non-test file.
- **Limits:** Only HEAD, never git history, so a rotated-out-but-committed secret is invisible. Unknown token formats (Azure, GCP JSON keys, DB URLs with passwords) are missed. A real key containing `test` or `sample` is skipped. Private-key blocks in README examples are flagged. Stops after 50 findings.
- **Basis:**
  - S09 · SP 800-218A PO.5.1.R6, p.19 (direct) · "Continuously monitor each environment for plaintext secrets."
  - S11 · Secure Coding Principles > Authentication, Authorization & Secrets Management (direct) · "Emphasize that credentials and sensitive tokens must never be hard-coded or exposed"
  - S01 · p. 30 (supporting) · "The harness runs deterministic hooks (e.g., blocking a commit if the agent tries to push a hard-coded password)."

### sec.no_sensitive_files — No credential files (.env, private keys, tfstate) are committed.
- **Checks:** Tracked files whose name (anywhere in the tree) matches `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.jks`, `*.keystore`, `id_rsa`, `id_ed25519`, `credentials.json`, `service-account*.json`, `*.tfstate`, `*.tfvars`, `.npmrc`, `.pypirc`, `.netrc`, `.env`, `.env.*`, `*.env`. Excludes paths containing `example`, ending in `.example/.sample/.template/.dist/.default(s)` or `.env.test`, and anything under `test(s)/`, `fixture(s)/`, `testdata/`, `example(s)/`, `sample(s)/`, `doc(s)/`.
- **Met:** None of those files is committed.
- **Partially met:** never.
- **Not met:** At least one such file is committed.
- **Limits:** Judges by file name only, never contents: a `.npmrc` with just a registry URL, a public CA `*.pem` or a non-secret `*.tfvars` fails the check. `id_ecdsa`, `id_dsa`, `*.kdbx` are not looked for. A real secret file inside `docs/` or `examples/` passes. History is not checked.
- **Basis:**
  - S09 · SP 800-218A PO.5.1.R2, p.18 (supporting) · "Only store sensitive data used during AI model development, including production data, within organization-approved environments and locations within those environments."
  - S11 · TL;DR > Be Security-Conscious (supporting) · "Check for any secrets or sensitive data in the suggested code."

### sec.ci_scanning — CI scans code, dependencies and secrets on every change.
- **Checks:** The CI text: `.github/workflows/*.yml|yaml` plus scripts, `Makefile`, `noxfile.py`, `tox.ini`, `package.json`, `pyproject.toml` they call. Counts distinct tool names found anywhere in it: codeql, gitleaks, trufflehog, detect-secrets, trivy, snyk, semgrep, bandit, pip-audit, npm audit, osv-scanner, dependency-review, grype, zizmor, checkov, tfsec, safety check, govulncheck, cargo audit, scorecard.
- **Met:** Two or more different tool names appear.
- **Partially met:** Exactly one tool name appears.
- **Not met:** None appear, including when there are no GitHub workflows at all.
- **Limits:** Plain text match: a name in a comment or a disabled job counts. CodeQL "default setup", GitHub secret scanning or Snyk apps configured outside workflows are invisible. GitLab CI, Jenkins etc. are not read. `cargo-audit` (hyphen) is not matched. Triggers (every PR?) are not checked.
- **Known gap:** The checklist promises scanning of code, dependencies AND secrets; the code only counts tool names, so two SAST tools (e.g. codeql + semgrep) with no dependency or secret scan are Met.
- **Basis:**
  - S09 · SP 800-218 PW.4.4 Ex.2, p.22 (direct) · "Build into the toolchain automatic detection of known vulnerabilities in software components."
  - S11 · Platform and Runtime Security Considerations > Operational Security (direct) · "Include steps to run security scans (SAST/DAST) and dependency checks in the CI/CD pipeline to catch vulnerabilities early"
  - S12 · SAST (direct) · "Using SAST tools can prevent known classes of bugs from being inadvertently introduced in the codebase."

### sec.dep_updates — Dependency updates are automated (Dependabot / Renovate).
- **Checks:** Looks for `.github/dependabot.yml` / `.yaml`, any file named `renovate.json` or `.renovaterc*` anywhere, or `.github/renovate.json*`.
- **Met:** Any of those files exists.
- **Partially met:** never.
- **Not met:** None exists.
- **Limits:** Contents are not read: a Dependabot file covering one ecosystem out of three, or a disabled Renovate config, passes. Renovate config inside `package.json` or a root `renovate.json5`, and Renovate run as a hosted app with org-level config, are missed.
- **Basis:**
  - S12 · Dependency-Update-Tool (direct) · "These tools automate the process of updating dependencies by scanning for outdated or insecure requirements, and opening a pull request to update them if found."
  - S09 · SP 800-218 PW.4.1 Ex.7, p.21 (supporting) · "Implement processes to update deployed software components to newer versions"
  - S11 · Addressing Software Supply Chain Security > Stay Updated & Monitor Vulnerabilities (supporting) · "When suggesting dependency versions, prefer the latest stable release and mention updating dependencies regularly to patch vulnerabilities"

### sec.gitignore — .gitignore keeps env files and keys out of git.
- **Checks:** Concatenates every tracked `.gitignore` in the repo (root and subfolders) and looks for an env rule (a line starting with `.env`, `*.env`, or `/.env` after a slash) and a key rule (`*.pem`, `*.key`, `*.p12`, or the text `.pem` / `.key` anywhere).
- **Met:** Both an env rule and a key rule are present (0.7 + 0.3).
- **Partially met:** Only the env rule is present (0.7).
- **Not met:** Only the key rule (0.3), neither, or no `.gitignore` at all.
- **Limits:** Raw text match: commented-out lines, negations like `!*.pem`, and `.envrc` all count. A rule in a nested `.gitignore` counts as if it covered the whole repo. `.git/info/exclude` and global ignores are not seen. Does not check that `.env.*` variants are covered.
- **Convention:** Ignoring `.env` and key files is the first line of defence against the committed-credential failures that `sec.no_sensitive_files` detects.

### sec.workflow_permissions — CI workflows run with least-privilege tokens.
- **Checks:** Each `.github/workflows/*.yml|yaml` file: does it contain a `permissions:` line at any indentation (top-level or per job)? Also whether the word `pull_request_target` appears in any workflow.
- **Met:** At least 85% of workflow files declare `permissions:` and no workflow mentions `pull_request_target`.
- **Partially met:** 35–84% of workflows declare permissions without `pull_request_target`, or 65%+ with it (the 0.3 penalty caps such repos at Partially met).
- **Not met:** Under 35% declare permissions (under 65% if `pull_request_target` is used).
- **Not applicable:** The repo has no GitHub workflow files.
- **Limits:** Only presence of the key counts, so `permissions: write-all` passes. The repository/org default token setting is invisible. `pull_request_target` in a comment still costs 0.3. Non-GitHub CI is ignored.
- **Known gap:** The checklist says "least-privilege tokens", but the value of `permissions:` is never inspected.
- **Basis:**
  - S12 · Token-Permissions (direct) · "This check determines whether the project's automated workflows tokens follow the principle of least privilege."
  - S09 · SP 800-218 PO.5.2 Ex.2, p.18 (supporting) · "Configure each development endpoint and the development resources to provide the least functionality needed by users and services and to enforce the principle of least privilege."
  - S11 · Secure Coding Principles > Secure Defaults & Configurations (supporting) · "Always instruct the AI to follow the principle of least privilege (e.g. minimal file system permissions, least-privileged user accounts for services, etc.) in any configuration or code it proposes."

### sec.env_template — Required configuration is documented in an .env.example template.
- **Checks:** Whether non-test source code (first 3000 source files, excluding `vendor/`, `third_party/`, `docs/`, `examples/`, `.github/`) reads env vars (`os.environ`, `getenv(`, `process.env.`, `dotenv`, `env::var`, `System.getenv`, `Environment.GetEnvironmentVariable`, case-insensitive), then looks anywhere for `.env.example`, `.env.sample`, `.env.template`, `*.env.example`, `.env.dist`.
- **Met:** Code reads env vars and one of those template files exists.
- **Partially met:** never.
- **Not met:** Code reads env vars but no template file exists (score 0.2).
- **Not applicable:** No env-var reading is detected in source.
- **Limits:** The template's contents are never compared with the variables the code uses; an empty `.env.example` passes. `example.env`, `.env.local.example`, `.env.defaults` are not recognised. Ruby `ENV[...]` and config-file-based apps are not detected. "dotenv" in a comment counts as env usage.
- **Basis:**
  - S03 · Keep CLAUDE.md short (supporting) · "Integration tests need DATABASE_URL set, see .env.example"
  - S09 · SP 800-218 PW.9.2, p.25 (supporting) · "Implement the default settings (or groups of default settings, if applicable), and document each setting for software administrators."
  - S11 · TL;DR Sample Instructions (supporting) · "Never include API keys, passwords, or secrets in code output, and use environment variables or secure vault references instead."

### sec.precommit_secrets — A pre-commit hook blocks secrets before they are committed.
- **Checks:** Text of any `.pre-commit-config.yaml`, `lefthook.yml` or `.lefthook.yml` anywhere, plus files under root `.husky/`. Looks for gitleaks, detect-secrets, trufflehog, detect-private-key or ggshield.
- **Met:** Any of those names appears.
- **Partially met:** never.
- **Not met:** None appears, or there is no hook config.
- **Limits:** A commented-out hook counts. `detect-private-key` alone (only catches PEM blocks) passes. `lefthook.yaml` and `.lefthook.yaml` are not read. Hooks only run if each developer installs them; that is not verifiable.
- **Basis:**
  - S01 · p. 30 (direct) · "The harness runs deterministic hooks (e.g., blocking a commit if the agent tries to push a hard-coded password)."
  - S09 · SP 800-218 PW.7.2 Ex.6, p.23 (supporting) · "Use automated tools to identify and remediate documented and verified unsafe software practices on a continuous basis as human-readable code is checked into the code repository."

### sec.policy — A SECURITY.md explains how to report vulnerabilities.
- **Checks:** Any file named `SECURITY.md` (case-insensitive, anywhere in the tree), plus `.github/SECURITY.md` and `docs/SECURITY.md`.
- **Met:** Such a file exists.
- **Partially met:** never.
- **Not met:** None exists.
- **Limits:** Contents are not read, and any `security.md` anywhere (e.g. a docs page about security features) passes. An org-wide policy inherited from a `.github` repository is not seen.
- **Known gap:** The checklist says the file "explains how to report vulnerabilities"; the code only checks that the file exists.
- **Basis:**
  - S09 · SP 800-218 RV.1.3 Ex.1, p.26 (direct) · "Establish a vulnerability disclosure program, and make it easy for security researchers to learn about your program and report possible vulnerabilities."
  - S12 · Security-Policy (remediation) (direct) · "Place a security policy file `SECURITY.md` in the root directory of your repository."

### sec.codeowners — CODEOWNERS assigns reviewers for sensitive paths.
- **Checks:** Any file named `CODEOWNERS` anywhere in the tree (case-insensitive), plus `.github/CODEOWNERS`, `docs/CODEOWNERS`.
- **Met:** Such a file exists.
- **Partially met:** never.
- **Not met:** None exists.
- **Limits:** Contents are not read: an empty file, or one with a single `*` owner, passes. A `CODEOWNERS` in a subfolder GitHub ignores (e.g. a vendored package) also passes.
- **Known gap:** The checklist says owners are assigned "for sensitive paths"; no path coverage is checked.
- **Basis:**
  - S09 · SP 800-218 PS.1.1 Ex.4, p.18 (direct) · "Have the code owner review and approve all changes made to the code by others."
  - S12 · Branch-Protection (Tier 4) (direct) · "Require review from code owners"

## reproducibility

### rep.lockfile — Dependencies are locked to exact versions.
- **Checks:** Lockfiles anywhere in the tree by file name: `uv.lock`, `poetry.lock`, `Pipfile.lock`, `pdm.lock`, `pixi.lock`, `conda-lock.yml`, `requirements*.lock`, `package-lock.json`, `npm-shrinkwrap.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lock(b)`, `Cargo.lock`, `go.sum`, `Gemfile.lock`, `composer.lock`, `packages.lock.json`, `gradle.lockfile`, `flake.lock`. It also reads every `requirements*.txt` and `constraints*.txt`.
- **Met:** At least one lockfile exists, or at least one `requirements*.txt` / `constraints*.txt` is "fully pinned". Fully pinned means it has at least one requirement line and every one contains `==` or ` @ `. Comments and lines starting with `-` are ignored.
- **Partially met:** No lockfile and no fully pinned file, but at least one `requirements*.txt` exists (score 0.4).
- **Not met:** No lockfile and no `requirements*.txt` at all, for example a `pyproject.toml` or `package.json` with no lock.
- **Not applicable:** The repository has no manifest (`pyproject.toml`, `setup.py`, `setup.cfg`, `requirements*.txt`, `package.json`, `Cargo.toml`, `go.mod`, `Gemfile`, `composer.json`, `*.csproj`, `pom.xml`, `build.gradle*`, `environment.yml`) and no source files.
- **Limits:** The scanner checks that a lockfile exists, not that it is current or matches the manifest. A lockfile in a fixture, vendored or sub-project folder counts for the whole repo. `==` anywhere on the line counts as pinned, including `foo==1.*` and `foo>=1; python_version=="3.8"`. Maven, plain Gradle and NuGet projects without a lock are not met.
- **Known gap:** The checklist says "every requirement is pinned", but one fully pinned file is enough. A pinned `requirements-dev.txt` or `constraints.txt` makes the check Met even when the runtime `requirements.txt` is unpinned.
- **Basis:**
  - S10 · ASI04 guideline 2, p.21 (direct) · "Dependency gatekeeping: Allowlist and pin; scan for typosquats (PyPI, npm, LangChain, LlamaIndex); verify provenance before install or activation"
  - S12 · Pinned-Dependencies (remediation) (direct) · "If your project is producing an application and the package manager supports lock files (e.g. `package-lock.json` for npm), make sure to check these in the source code as well."
  - S09 · SP 800-218 PW.4.1 Ex.5, p.21 (supporting) · "Maintain a list of organization-approved commercial software components and component versions along with their provenance data."

### rep.environment — Runtime and toolchain versions are pinned (version files / container).
- **Checks:** Counts files, matched by name anywhere: `.python-version`, `.nvmrc`, `.node-version`, `.tool-versions`, `mise.toml`, `.mise.toml`, `rust-toolchain*`, `global.json`, `.sdkmanrc`, `.java-version`, `.ruby-version`, `.go-version`, `Dockerfile`, `*.dockerfile`, `docker-compose*.yml`, `compose.y*ml`, `flake.nix`, `shell.nix`, `devbox.json`. It also counts any file under the root `.devcontainer/`.
- **Met:** 2 or more matching files (score = files / 2, capped at 1).
- **Partially met:** Exactly 1 matching file (0.5).
- **Not met:** None.
- **Limits:** The scanner counts files, not distinct mechanisms. Two `Dockerfile`s, or two files in `.devcontainer/`, meet the check. File contents are never read, so an unpinned `FROM python:latest` counts. `Dockerfile.dev` and `docker-compose.yaml` are missed. A `global.json` that is not the .NET SDK file also counts.
- **Known gap:** The intent is "at least two pinning mechanisms", but the code counts matching files.
- **Basis:**
  - S08 · p. 41 (direct) · "Version everything: Store all production artifacts in version control. This includes application code, system configurations, test scripts, deployment scripts, container orchestration files, and cloud configuration files."
  - S11 · Platform and Runtime Security Considerations > Container and Deployment Considerations (direct) · "pin image versions using immutable digests (e.g., SHA256 hashes) instead of mutable tags like latest"
  - S12 · Pinned-Dependencies (remediation) (direct) · "For Dockerfiles used in building and releasing your project, pin dependencies by hash."

### rep.entrypoints — One command sets up, builds and tests the project.
- **Checks:** Any of these, matched by name anywhere: `Makefile`, `justfile`, `Taskfile.y*ml`, `noxfile.py`, `tox.ini`, `start*.sh`, `run*.sh`, `start*.bat`. Also any file under the root `scripts/`, a `"scripts":` key in the root `package.json`, or `[project.scripts]`, `[tool.poe` or `[tool.hatch.envs` in the root `pyproject.toml`.
- **Met:** At least one of these is found (the score is true/false).
- **Partially met:** never
- **Not met:** None is found.
- **Limits:** The scanner checks that a runner exists, not that its commands set up, build or test. Any stray file in `scripts/`, or a Makefile in a vendored folder, meets it. `[project.scripts]` declares console entry points, not tasks. Gradle/Maven wrappers, `Rakefile`, `.csproj` and `Cargo` aliases are not recognised.
- **Known gap:** The checklist says "One command sets up, builds and tests the project". The code only checks that some task runner or script exists.
- **Basis:**
  - S08 · p. 41 (supporting) · "The goal is to be able to reproduce testing and production environments in a fully automated fashion using only information from version control."

### rep.documented — How to get the same result from a clean checkout is documented.
- **Checks:** Joins the text of the first 40 files matching `README*`, `CONTRIBUTING*`, `AGENTS.md` or `CLAUDE.md` anywhere, or any `docs/**.md`. It looks for (a) a markdown heading line (`#…`) containing install, setup, getting started, quick start/quickstart or development, and (b) reproduction wording: `reproduc*`, `rerun`/`re-run*`, `deterministic*`, or "same result(s)".
- **Met:** Both a setup heading and reproduction wording are found.
- **Partially met:** Only one of them is found (0.5).
- **Not met:** Neither is found.
- **Limits:** Lines in code blocks that start with `#`, such as `# install deps`, count as headings. Any README in a subfolder or vendored package counts. Both checks are keyword matches: a "reproducible builds" badge or the word "rerun" satisfies (b). The scanner never checks that the steps lead to the same result.
- **Basis:**
  - S03 · Run sessions in parallel (supporting) · "keep the install command in `CLAUDE.md` so Claude runs it whenever it starts in a new checkout"
  - S08 · p. 42 (supporting) · "One of the most common pitfalls is storing only application source code in version control."
  - S09 · SP 800-218A PS.3.1.R3, p.21 (supporting) · "Include documentation of the entire training process, such as data preprocessing and model architecture."

### rep.provenance — Results record the code version and configuration that produced them.
- **Checks:** Source files (first 3000) are searched for an ML import (`import torch|tensorflow|sklearn|jax|xgboost|lightgbm`, `from torch|sklearn|transformers|tensorflow|jax import`) and for tracker words (`mlflow`, `wandb`, `dvc`, `sacred`, `aim`, `neptune`, `clearml`, `comet_ml`, `tensorboard`, `lightning.pytorch.loggers`). Tracker words are also searched in requirements, `pyproject.toml` and `package.json`. It also looks for `dvc.yaml`, `.dvc/config`, `MLproject`, and for git-SHA code (`rev-parse HEAD`, `git describe`, `GITHUB_SHA`, `GIT_COMMIT`, `git_sha`, `commit_sha`, `get_git_hash`, `repo.head.commit`).
- **Met:** The check applies, and a tracker word, a DVC/MLproject file or git-SHA code is found.
- **Partially met:** never
- **Not met:** An ML import is found, but no tracker, no DVC/MLproject file and no SHA-recording code.
- **Not applicable:** No ML import, no tracker word and no DVC/MLproject file.
- **Limits:** A tracker word alone makes the check both applicable and Met, so it can only fail for ML imports without tracking. The scanner never checks that config or seed are logged with results. `from torch.nn import`-style imports are not detected as ML.
- **Known gap:** Bug: the tracker pattern includes the bare word `aim` (case-insensitive), so any comment such as "we aim to…" makes the check applicable and Met.
- **Basis:**
  - S09 · SP 800-218A PS.3.2.R1, p.21 (direct) · "Track the provenance of an AI model and its components and derivatives, including the training libraries, frameworks, and pipelines used to build the model."
  - S11 · Addressing Software Supply Chain Security > Generate Software Bill of Materials (SBOM) (supporting) · "Where applicable, use an attestations framework such as in-toto or similar to create verifiable records of your build and deployment processes"
  - S12 · Signed-Releases (supporting) · "Signed releases attest to the provenance of the artifact."

### rep.seeds — Randomness is seeded where results depend on it.
- **Checks:** Applies only when an ML import (same pattern as `rep.provenance`, first 2000 source files) is found. Source files are then searched for `seed(`, `random_state`, `manual_seed`, `set_seed`, `--seed` or `SEED =` (case-insensitive, so `seed=` also counts).
- **Met:** At least one seed match.
- **Partially met:** never
- **Not met:** ML import found, no seed match.
- **Not applicable:** No ML import, even if only a tracker is present.
- **Limits:** One match anywhere is enough. The scanner never checks that every RNG (python, numpy, torch) is seeded or that the seed is recorded. Test files are excluded, and numpy-only numeric code is never applicable.
- **Known gap:** Bug: `\b--seed` needs a letter or digit right before the `-`, so `add_argument("--seed")` never matches.
- **Basis:**
  - S13 · Infra 1, p.4 (direct) · "Random number generation is an obvious source of non-determinism, which can be alleviated with seeding."

## cicd

### ci.present — CI runs on GitHub Actions.
- **Checks:** `.yml`/`.yaml` files under `.github/workflows/`, subfolders included. With none, it looks for `.gitlab-ci.yml`, `Jenkinsfile`, `azure-pipelines.yml`, `.circleci/config.yml`, `bitbucket-pipelines.yml` or `.travis.yml`.
- **Met:** At least one workflow file.
- **Partially met:** No workflows, but another CI config exists (0.4).
- **Not met:** No CI configuration.
- **Limits:** Workflow content, triggers and validity are not read. Files in subfolders of `.github/workflows/` count although GitHub does not run them.
- **Known gap:** With no GitHub workflows, all other ci.* checks are forced to Not met, even if GitLab or another CI runs everything.
- **Basis:**
  - S08 · p. 61 (supporting) · "It ensures that AI-generated code is consistently tested, secured, and deployed, turning individual productivity gains into systemic, organizational improvements."
  - S09 · SP 800-218 PO.3.2 Ex.3, p.16 (supporting) · "Use code-based configuration for toolchains (e.g., pipelines-as-code, toolchains-as-code)."

### ci.pr — CI gates pull requests before merge.
- **Checks:** All workflow text, searched for the triggers `pull_request`, `pull_request_target` or `merge_group` in any YAML form: a key (`pull_request:`), a list item (`- pull_request`), a scalar (`on: pull_request`) or a flow list (`on: [push, pull_request]`).
- **Met:** One of those triggers is found.
- **Partially met:** Never.
- **Not met:** None is found, or there are no workflows.
- **Limits:** A PR trigger on any workflow (for example a labeler) counts. It does not check that the workflow runs real checks or that branch protection marks them required, which "gates before merge" implies.
- **Basis:**
  - S08 · p. 39 (direct) · "In the outer loop, version control provides the scaffolding for human-in-the-loop review of changes before they are merged."
  - S12 · Branch-Protection (Tier 3) (direct) · "Require branch to pass at least 1 status check before merging"
  - S01 · p. 24 (supporting) · "Tests and quality gates that verify correctness"

### ci.stages — CI lints, tests and builds.
- **Checks:** It searches `ci_text` (workflows plus the scripts they delegate to) for three stages. Lint/typecheck: `ruff`, `eslint`, `mypy`, `pre-commit run` and others. Test: the test.ci command list. Build: `\bbuild\b`, `docker build`, `cargo build`, `tsc` and others.
- **Met:** All 3 stages are found.
- **Partially met:** 2 of the 3.
- **Not met:** 0 or 1, or no workflows.
- **Limits:** These are substring matches anywhere. A tool named in an install line or a delegated `pyproject.toml` dependency list counts as a stage.
- **Known gap:** The build pattern `\bbuild\b` matches any word "build", such as a job named `build:` that only runs tests, `pip install build` or a step title. The build stage is almost always "present".
- **Convention:** Lint, test and build in CI are the minimum feedback loop; each missing stage lets a class of defects reach main.

### ci.cd — Releases or deployments are automated.
- **Checks:** Workflow text only (not delegated scripts). It looks for deploy keywords (`deploy`, `release`, `publish`, `docker push`, `helm`, `kubectl`, `aws-actions`, `goreleaser` and others). It also looks for a tag trigger (`tags:` followed by a list item) or `release:` followed by `types`. Score: 0.5 for any keyword, 0.5 for a tag/release trigger, 0.5 for 3 or more distinct keywords, capped at 1.
- **Met:** A keyword plus a tag/release trigger, or 3 or more distinct keywords.
- **Partially met:** 1 or 2 distinct keywords without a tag trigger, or a tag trigger alone.
- **Not met:** No keyword and no tag trigger, or no workflows.
- **Limits:** The keywords are case-insensitive substrings. "release" in a branch filter, "publish" in a step name, `aws-actions` for test credentials, or a docs `deploy-pages` all count. Three such words give Met without any real release. `on: release` as a scalar is missed.
- **Basis:**
  - S12 · Packaging (remediation) (direct) · "If hosted on GitHub, use a GitHub action to release your package to language-specific hubs."
  - S03 · Put team procedures in skills (supporting) · "Tag `v<new version>` and push the tag. CI publishes from there, never publish from your machine."
  - S07 · p. 82 (supporting) · "Continuous integration and deployment pipelines may need to evolve to reduce wait states and allow for higher-frequency delivery."

### ci.hygiene — Jobs have timeouts, version matrices and protected environments.
- **Checks:** Workflow text only. It counts occurrences of `timeout-minutes` (job or step level) against detected jobs: 2-space keys whose next line is a 4-space `runs-on:` or `uses:`, minimum 1. It also looks for any `matrix:`, and for an `environment:` line or `workflow_dispatch`. Score = 0.4×min(1, timeouts/jobs) + 0.3×matrix + 0.3×(environment or dispatch).
- **Met:** A matrix, an environment or manual dispatch, and timeouts on at least about 63% of detected jobs.
- **Partially met:** A score of 0.35 to 0.84. Examples: timeouts on all jobs alone (0.4), matrix plus environment/dispatch (0.6), or one of those plus timeouts on at least 1 in 8 jobs.
- **Not met:** Below 0.35, for example only a matrix or only `workflow_dispatch`. Also when there are no workflows.
- **Limits:** Jobs whose first key is `name:`, `needs:` or `if:` are not counted as jobs. Step-level timeouts inflate the ratio, so full timeout credit is easy to reach falsely.
- **Known gap:** The checklist says "protected environments". The code accepts any `workflow_dispatch` trigger instead, and never checks that an environment is protected.
- **Basis:**
  - S09 · SP 800-218 PO.5.1, p.17 (supporting) · "Separate and protect each environment involved in software development."

### ci.pinning — Third-party actions are pinned to commit SHAs.
- **Checks:** It finds `uses: owner/repo@ref` entries in workflow text, excluding `actions/*` and `github/*`. It counts every occurrence whose ref is exactly 40 lowercase hex characters as pinned.
- **Met:** At least 85% of third-party `uses:` occurrences are SHA-pinned, or there are no third-party actions.
- **Partially met:** 35% to 84% are pinned.
- **Not met:** Under 35% are pinned, or there are no workflows.
- **Limits:** Occurrences are counted, not unique actions. Uppercase SHAs count as unpinned. Whether a SHA belongs to the claimed tag is not checked. Docker `uses:` and composite actions' internal `uses:` are not seen.
- **Basis:**
  - S11 · Platform and Runtime Security Considerations > Operational Security (direct) · "use the latest versions of devops dependencies such as GitHub actions and lock the version to specific SHA"
  - S12 · Pinned-Dependencies (remediation) (direct) · "For GitHub workflows used in building and releasing your project, pin dependencies by hash."
  - S09 · SP 800-218 PO.3.2 Ex.7, p.16 (supporting) · "Regularly verify the integrity and check the provenance of each tool to identify potential problems."

### ci.speed — CI is fast: caching, cancel-in-progress and path filters.
- **Checks:** Workflow text only. Cache: `actions/cache`, `cache: pip|npm|yarn|pnpm|gradle|maven|go|poetry|uv`, `enable-cache`, `setup-uv`, `Swatinem/rust-cache` or `cache-from`. Concurrency: a `concurrency:` line. Paths: a `paths:` or `paths-ignore:` line. Score = 0.45 cache + 0.35 concurrency + 0.2 paths.
- **Met:** All three are found (cache plus concurrency alone is only 0.8).
- **Partially met:** Any combination scoring 0.35 to 0.8: cache alone, concurrency alone, or two of the three.
- **Not met:** Nothing found, or only path filters (0.2), or no workflows.
- **Limits:** Using `setup-uv` counts as caching even without `enable-cache`. Default caching in `setup-go` is not seen. Whether caches actually hit is not checked.
- **Known gap:** The checklist says "cancel-in-progress", but any `concurrency:` block counts, even without `cancel-in-progress: true`. Met also needs path filters, which many fast repos rightly do not use.
- **Basis:**
  - S07 · p. 9 (supporting) · "We need fast feedback loops—faster than ever—to match AI-accelerated code generation."

## cost

### cost.llm_tracking — LLM token usage and cost are tracked per call / run.
- **Checks:** LLM detection looks at source files (first 4000, excluding root `scripts/`, `examples/` and `.github/`). It looks for line-start Python imports of anthropic, openai, langchain*, llama_index, litellm, google genai/generativeai, mistralai, cohere, groq, ollama or claude_agent_sdk. It also looks for JS `require`/`from` of `openai`, `@anthropic-ai/*`, `ai`, `@ai-sdk/*` or `langchain*`, and for the same packages declared in requirements, `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml` or `*.csproj`. If found, it searches source lines for `usage.input_tokens/output_tokens/prompt_tokens/completion_tokens/total_tokens`, `cost_usd`, `total_cost`, `token_count`, `count_tokens`, `track_cost`, `cost_tracker`, `get_openai_callback`, `langfuse`, `helicone`, `langsmith` or `openlit`.
- **Met:** 2 or more matching lines (score = lines / 2).
- **Partially met:** Exactly 1 matching line.
- **Not met:** No matching line.
- **Not applicable:** No LLM SDK import or dependency is detected.
- **Limits:** Comments count. Two lines in one file count as two places. The scanner never checks that usage is persisted per call or run. It misses other styles: `usage["input_tokens"]`, Gemini `usage_metadata`, and custom names. Go and Rust LLM clients (e.g. `go-openai`) are not detected as LLM usage.
- **Basis:**
  - S01 · p. 28 (direct) · "Observability: Logs, traces, evaluations, cost and latency metering. Without observability, there is no way to tell whether the agent is doing well or quietly drifting."
  - S03 · Change a default (supporting) · "When that happens, run `/usage` in the session to see where it went."
  - S07 · p. 83 (supporting) · "The key is for the AI system or agents to be constantly updated with relevant context and constantly measured for accuracy, usefulness, and cost."

### cost.llm_limits — LLM calls are bounded by max_tokens, budgets and retries.
- **Checks:** Only when an LLM SDK is detected (see `cost.llm_tracking`). Source lines are searched for the words `max_tokens`, `max_output_tokens`, `max_completion_tokens`, `budget`, `max_cost`, `spend_limit`, `rate_limit` or `max_retries`.
- **Met:** 2 or more matching lines.
- **Partially met:** Exactly 1 matching line.
- **Not met:** None.
- **Not applicable:** No LLM SDK detected.
- **Limits:** The same keyword twice (e.g. `max_tokens` on two calls) meets it, so budgets or retries are not required. The word `budget` in any unrelated comment counts. The scanner never checks that every call is bounded. `budgets` (plural) and camelCase `maxTokens` do not match.
- **Basis:**
  - S03 · Let Claude run without you (direct) · "What stops it? `--max-turns`, `--max-budget-usd`, a spend limit."
  - S10 · ASI02 guideline 5, p.15 (direct) · "Adaptive Tool Budgeting. Apply usage ceilings (cost, rate, or token budgets) with automatic revocation or throttling when exceeded."
  - S01 · p. 40 (supporting) · "This creates an expensive "prompting loop" that burns through API tokens with low first-pass success rates."

### cost.infra — Cloud resources have budgets, tags and cost checks.
- **Checks:** IaC files: `*.tf`, `*.bicep`, `cdk.json`, `Pulumi.yaml`, `serverless.yml`, `template.yaml`, `*.cfn.yaml` anywhere, or any file under root `k8s/`, `helm/` or `charts/`. In those files (first 200) plus all workflow YAML, it collects distinct matches of: `infracost`, `aws_budgets_budget`, `azurerm_consumption_budget`, `google_billing_budget`, cost-center/cost_center, `tags`, `labels:`/`labels =`, `autoscal`, `spot`, `preemptible`, `resources:` followed by `limits`.
- **Met:** 3 or more distinct signals (score = distinct / 3).
- **Partially met:** Exactly 2 distinct signals (0.67).
- **Not met:** 0 or 1 signal (1 gives 0.33, below 0.35).
- **Not applicable:** No IaC file exists.
- **Limits:** Weak signals add up. Workflow `tags:` push triggers and near-universal k8s `labels:` count, and `spot` matches inside words like "hotspot". Any file named `template.yaml` counts as IaC. Budgets are never required.
- **Known gap:** Signals are deduplicated by the exact matched text (lower-cased, not trimmed). So `labels:` and `labels =`, or `cost-center` and `cost_center`, count as two signals.
- **Convention:** Cloud spend without budgets or tags cannot be attributed or capped; applies only when infrastructure is defined as code.

### cost.llm_efficiency — Prompt caching and a central model config keep spend down.
- **Checks:** Only when an LLM SDK is detected. Source lines are searched for caching (`cache_control`, `prompt_cach`, `semantic_cache`, `lru_cache`, `@cache`, `diskcache`, `redis`) and for "model config": `MODEL`, `model_name`, `model_id` or `DEFAULT_MODEL` followed by `:` or `=`, case-insensitive.
- **Met:** Both a caching match and a model-config match (0.5 + 0.5).
- **Partially met:** Exactly one of the two (0.5).
- **Not met:** Neither.
- **Not applicable:** No LLM SDK detected.
- **Limits:** Any `lru_cache` or `redis` use counts as prompt caching even if unrelated to LLM calls.
- **Known gap:** The model-config pattern has no word boundary. Any inline `model="gpt-4o"` keyword argument, `self.model =` or `data_model:` matches, so a hard-coded model in a call meets "central model config".
- **Basis:**
  - S01 · p. 42 (supporting) · "routes deterministic, lower-complexity tasks (Test Generation, Code Review, and CI/CD monitoring) to smaller, faster, and significantly cheaper models."
  - S03 · Know what subagents cost (supporting) · "Set `model: haiku` in a subagent’s definition if its work is simple"

### cost.ci — CI minutes are controlled (timeouts, cancel-in-progress, path filters).
- **Checks:** Only when GitHub workflows exist and the project uses an LLM SDK or IaC. In all workflow text it counts `timeout-minutes` occurrences and jobs. A job counts if its key is indented 2 spaces and the next line, at 4 spaces, is `runs-on` or `uses`; at least 1 job is assumed. It also looks for `cancel-in-progress: true` and a `paths:`/`paths-ignore:` line. Score = 0.4 x min(1, timeouts/jobs) + 0.35 x cancel + 0.25 x paths.
- **Met:** `cancel-in-progress: true` AND a path filter AND timeouts on at least 62.5% of counted jobs.
- **Partially met:** Score 0.35 to 0.85. Examples: cancel-in-progress alone, or cancel + paths, or timeouts covering at least 87.5% of jobs alone, or path filter + at least 25% timeout coverage.
- **Not met:** Below 0.35, e.g. only path filters, or timeouts on fewer than 87.5% of jobs with nothing else.
- **Not applicable:** No workflows, or no LLM/IaC usage.
- **Limits:** Step-level `timeout-minutes` also count, and jobs whose first key is `name:`/`needs:`/`if:` are not counted, so the ratio is easily inflated. `cancel-in-progress: ${{ … }}` is not recognised. Expensive runners are reported but not scored. Other CI systems are ignored.
- **Convention:** Timeouts, cancel-in-progress and path filters stop CI minutes from being burned by hung or superseded jobs.

### cost.documented — Expected costs and budgets are documented.
- **Checks:** Text of the first 30 files matching `README*`, `CLAUDE.md` or `COST*.md` anywhere, or any `docs/**.md`, searched case-insensitively for words starting with `cost`, `budget`, `pricing` or `spend`, or for a `$` followed by a digit.
- **Met:** Any match.
- **Partially met:** never
- **Not met:** No match while the check applies.
- **Not applicable:** No LLM SDK and no IaC detected.
- **Limits:** Any incidental phrase ("at no cost", "low-cost", "spending time") meets it. The scanner never checks that expected costs, budgets or owners are actually stated.
- **Known gap:** Bug: `\b\$\d` needs a letter or digit before `$`, so "costs $5" matches only through the word "cost", and a bare "$20/month" is not detected.
- **Convention:** People can only keep to a budget that is written down next to the code that spends it.
