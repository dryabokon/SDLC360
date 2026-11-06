# Skills: how each capability is judged

Capabilities and their priorities are in [capabilities.md](../capabilities.md).
How to edit this file: [assessment/README.md](../README.md#acceptance-criteria).

## sk.present: Reusable agent procedures exist as markdown skills / subagents / commands.

**How we check.** Counts files named `SKILL.md` anywhere (case-insensitive), `.md` under root `.claude/agents/`, `agents/`, `.github/agents/`, `.md` under `.claude/commands/` and `commands/`, `.github/prompts/*.prompt.md`, `.cursor/rules/*.mdc` and `.github/instructions/*.instructions.md`.

- **Met:** Three or more such files.
- **Partially met:** Exactly two.
- **Not met:** One or none.

**What the check cannot see.** Any markdown in a root `agents/` or `commands/` folder counts (e.g. a `README.md` or design notes). A `SKILL.md` under `agents/` is counted twice. File quality is not judged here.

**Why we expect it.**

> The most powerful pattern for managing dynamic context is Agent Skills: structured, portable packages of procedural knowledge that the agent loads only when the task calls for it.
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 17 · direct

> That kind of knowledge goes in a skill: a procedure or a piece of team knowledge saved at `.claude/skills/<name>/SKILL.md`.
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Put team procedures in skills · direct

> Create a shared, version-controlled library of these reusable context templates or briefing packets for common tasks.
>
> — [dora-2025-ai-capabilities-model](../references/dora-2025-ai-capabilities-model/), p. 31 · direct

## sk.frontmatter: Every skill declares a name and description in frontmatter.

**How we check.** Each file found by `sk.present`: it must start with a `---` YAML block. Skills and subagents need non-empty `name` and `description`; commands, prompts and rules need only `description`.

- **Met:** At least 85% of the files have the required fields.
- **Partially met:** 35–84% do.
- **Not met:** Under 35% do.
- **Not applicable:** No skill/agent/command/rule files exist.

**What the check cannot see.** The parser is minimal: a BOM or blank line before `---` means "no frontmatter". Kebab-case `name` (mentioned in the recommendation) is not enforced. Values are not validated beyond being non-empty.

**Known flaw.** The checklist says "every skill declares a name"; command, prompt and rule files pass without one.

**Why we expect it.**

> The `SKILL.md` file must contain YAML frontmatter followed by Markdown content.
>
> — [agent-skills-spec](../references/agent-skills-spec/), SKILL.md format · direct

> For a skill Claude can start on its own, it sees the name and description in every session, but only reads the full file when the task calls for it.
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Put team procedures in skills · supporting

## sk.descriptions: Descriptions say what the skill does and when to use it.

**How we check.** Each file's frontmatter `description`: length 40–1024 characters and contains "use when/this/for/to", the word "when", or "trigger…"/"invoke…".

- **Met:** At least 85% of files have such a description.
- **Partially met:** 35–84%.
- **Not met:** Under 35% (missing descriptions count as failures).
- **Not applicable:** No skill/agent/command/rule files exist.

**What the check cannot see.** The word "when" anywhere passes, even in "what happens when it fails". The "what it does" half is not checked at all.

**Known flaw.** The checklist asks for what AND when; only a "when"-style keyword plus length is checked.

**Why we expect it.**

> Should describe both what the skill does and when to use it
>
> — [agent-skills-spec](../references/agent-skills-spec/), `description` field · direct

> description: Reviews changed files against the spec they were built from. Use after implementing a feature, before opening the PR.
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Know what subagents cost · supporting

> If a human engineer can’t definitively say which tool should be used in a given situation, an AI agent can’t be expected to do better.
>
> — [anthropic-context-engineering](../references/anthropic-context-engineering/), The anatomy of effective context · supporting

## sk.links: Links and scripts referenced by skills exist.

**How we check.** In every skill/agent/command/rule file: relative markdown links and backticked paths with an extension or trailing slash. Each must resolve from the file's folder, the repo root, or as a path suffix of any file. URLs and absolute paths are ignored.

- **Met:** At least 85% of references resolve, or there are no references.
- **Partially met:** 35–84% resolve.
- **Not met:** Under 35% resolve.
- **Not applicable:** No skill/agent/command/rule files exist.

**What the check cannot see.** Scripts named inside fenced code blocks without backticks around the path (e.g. `python scripts/run.py` as a whole command line) are not checked. The suffix fallback can match an unrelated file with the same tail. Files with no references score as fully OK.

**Why we expect it.**

> When referencing other files in your skill, use relative paths from the skill root
>
> — [agent-skills-spec](../references/agent-skills-spec/), File references · supporting

## sk.size: Skills stay concise and push detail into references.

**How we check.** Line count (including frontmatter) of every skill/agent/command/rule file; over 500 lines counts as oversized.

- **Met:** At most 15% of files are oversized.
- **Partially met:** 16–65% are oversized.
- **Not met:** More than 65% are oversized.
- **Not applicable:** No skill/agent/command/rule files exist.

**What the check cannot see.** Counts lines, not words or tokens: a 400-line file of very long lines passes.

**Known flaw.** The checklist says skills "push detail into references"; that is not checked here (only `sk.layout` rewards reference folders).

**Why we expect it.**

> Keep your main `SKILL.md` under 500 lines. Move detailed reference material to separate files.
>
> — [agent-skills-spec](../references/agent-skills-spec/), Progressive disclosure · direct

> The agent sees only lightweight metadata at startup, loads full instructions when a task matches, and pulls deep reference material only when explicitly needed.
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 17 · supporting

> The `CLAUDE.md` rule applies to skills too: only write down what Claude can’t find on its own.
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Put team procedures in skills · supporting

## sk.layout: Skills follow one layout and kebab-case naming.

**How we check.** For each `SKILL.md`, whether its parent folder name is lowercase kebab-case (and the file is named exactly `SKILL.md`). Also whether any file exists under `*/skills/<name>/scripts/`, `references/` or `assets/`. Score = 0.6 × share of well-named skills + 0.4 if any supporting file exists.

- **Met:** Supporting files exist and at least 75% of skill folders are kebab-case.
- **Partially met:** No supporting files but at least 58% kebab-case (max 0.6); or supporting files with under 75% kebab-case; or there are agents/commands but no `SKILL.md` at all (fixed 0.5).
- **Not met:** No supporting files and under 58% of skill folders are kebab-case.
- **Not applicable:** No skill/agent/command/rule files exist.

**What the check cannot see.** A lower-case `skill.md` or a root `SKILL.md` counts as badly named. Folder placement (`.claude/skills/` vs elsewhere) is not checked, so "one layout" is not enforced.

**Known flaw.** The `*/skills/...` pattern needs something before `skills/`, so a root-level `skills/<name>/scripts/` (the layout the recommendation suggests) is never detected. Also, skills that need no scripts/references can never be Met.

**Why we expect it.**

> May only contain unicode lowercase alphanumeric characters (`a-z`, `0-9`) and hyphens (`-`)
>
> — [agent-skills-spec](../references/agent-skills-spec/), `name` field · direct
