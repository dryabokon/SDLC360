# Documentation: how each capability is judged

Capabilities and their priorities are in [capabilities.md](../capabilities.md).
How to edit this file: [assessment/README.md](../README.md#acceptance-criteria).

## doc.readme: The README explains what the project is and how to start.

**Accepted when.** The README has at least {min_words} words.

**How we check.** Root-level files matching `README*` (any case or extension). If there are several, it takes the first in sorted order. It counts word tokens (`\w+` runs, so code and URLs count too).

- **Met:** A root README with at least {min_words} words.
- **Partially met:** A root README with at least {min_words:partial} words.
- **Not met:** No root README, or one with fewer than {min_words:partial} words.

**What the check cannot see.** Only length is measured. Pasted logs, badges, licence text or code blocks raise the count. A README in a subfolder is ignored. A translated `README.ja.md` sorts before `README.md` and can be the one measured.

**Known flaw.** The checklist says the README explains what the project is and how to start. The code checks only the word count.

**Why we expect it.**

> README.md files are for humans: quick starts, project descriptions, and contribution guidelines.
>
> — [agents-md](../references/agents-md/), Why AGENTS.md? · supporting

## doc.readme_sections: The README covers setup, usage, testing, configuration and overview.

**Accepted when.** The README covers installation, usage, testing, configuration, an overview and contributing.

**How we check.** It searches the README's headings plus the first 30,000 characters of its text, lowercased, for six topics: install/setup, usage, testing (`\btest`), configuration, architecture/overview, and contributing/development.

- **Met:** All 6 topics are found (5 of 6 gives 0.83).
- **Partially met:** 3 to 5 topics are found.
- **Not met:** 0 to 2 topics are found, or there is no root README.

**What the check cannot see.** A topic only needs its keyword somewhere in the text, not a section. "run ", "design", "config", "develop" or "example" anywhere is enough. The README's content is not read for meaning.

**Known flaw.** The checklist lists five topics. The code adds a sixth, contributing, and needs all six for Met.

**Our convention.** Setup, usage, testing, configuration and overview are the questions every newcomer, human or agent, asks first.

## doc.links: Docs reference files that actually exist.

**Accepted when.** Links to files in the docs work: at most 1 in 20 points to a file that does not exist.

**How we check.** Up to 300 tracked `.md` files, excluding those under root `node_modules/` or `vendor/`. It takes relative markdown links and images (no scheme, no leading `/`, `<` or `~`, anchors dropped) and backticked paths that contain `/` and end in an extension or `/`. Each one is resolved from the file's folder or from the repo root.

- **Met:** At most 5% of references are broken (1 - 3*broken/total >= 0.85). Also Met when there are no references at all.
- **Partially met:** More than 5% and up to about 21.7% of references are broken.
- **Not met:** More than about 21.7% of references are broken.

**What the check cannot see.** A file counts as existing if it is on disk, even untracked or git-ignored. A path ending matching any tracked file also resolves (`x/y.py` matches `src/pkg/x/y.py`). Paths in code examples are checked like real links. Links in `.mdx`/`.rst` files are never checked. Anchors and external URLs are not checked. A repo with no docs passes.

**Our convention.** A broken path in a doc sends readers and agents to files that no longer exist; it is the cheapest staleness signal to measure.

## doc.freshness: Docs are updated together with the code.

**Accepted when.** The docs were updated no more than {max_lag_days} days before the latest code change.

**How we check.** The newest commit touching the root README or any docs page (as found by doc.docs_dir) is compared with the newest commit touching the first 2,000 source files.

- **Met:** Docs were last changed no more than about {max_lag_days} days before the code (full score up to {grace_days} days, then a linear fade to 0 at {zero_days} days).
- **Partially met:** Docs lag the code by about {max_lag_days+1} to {partial_days} days. Also when either date is unknown (for example no source files or no history), which scores 0.5.
- **Not met:** Docs lag the code by more than about {partial_days} days, or there is no README and no docs page.

**What the check cannot see.** Only the single newest doc touch counts, so a typo fix anywhere resets the clock. It does not check that docs changed in the same commits or PRs as the code they describe.

**Why we expect it.**

> AI could be used to identify outdated documentation, summarize long project discussions, and detect inconsistencies between what systems are doing and what documentation claims they do.
>
> — [dora-2025-state-of-ai-assisted-development](../references/dora-2025-state-of-ai-assisted-development/), p. 86 · supporting

> Ideally, this documentation and metadata (for example, table and column descriptions) are treated as a code artifact. They are versioned, live alongside the data
>
> — [dora-2025-ai-capabilities-model](../references/dora-2025-ai-capabilities-model/), p. 24 · supporting

## doc.docs_dir: Deeper documentation lives in a docs/ folder.

**Accepted when.** A docs folder holds at least {min_pages} pages.

**How we check.** It counts `.md`, `.mdx`, `.rst` and `.adoc` files at any depth under the root `docs/`, `doc/`, `documentation/` or `website/docs/`.

- **Met:** {min_pages} or more pages.
- **Partially met:** {min_pages:partial} or more pages.
- **Not met:** Fewer.

**What the check cannot see.** Only the count matters, so empty stubs and ADRs count. Docs in nested packages, other folder names, wikis or external sites are not seen.

**Our convention.** Deeper material belongs in versioned docs next to the code rather than in a wiki the agent cannot read.

## doc.standard_files: LICENSE, CONTRIBUTING and CHANGELOG are present.

**Accepted when.** LICENSE, CONTRIBUTING and CHANGELOG files are present.

**How we check.** Basename matches anywhere in the tree for LICENSE (`LICENSE*`, `COPYING*`), CONTRIBUTING (`CONTRIBUTING*`) and CHANGELOG (`CHANGELOG*`, `CHANGES*`, `HISTORY*`, `RELEASES*`).

- **Met:** All 3 are found.
- **Partially met:** 2 of the 3 are found.
- **Not met:** 0 or 1 is found.

**What the check cannot see.** The files can sit in any folder, including vendored or fixture folders. Content is not read.

**Known flaw.** The patterns match any file whose basename starts with those words. A source file such as `history.py`, `changes.ts`, `releases.go` or `license_check.py` satisfies the check.

**Why we expect it.**

> The lack of a license will impede any kind of security review or audit and creates a legal risk for potential users.
>
> — [openssf-scorecard](../references/openssf-scorecard/), License · direct

## doc.inline: Public code is documented inline (docstrings / doc comments).

**Accepted when.** At least {min_share}% of Python functions and classes have a docstring (other languages: doc comments in at least 43% of files).

**How we check.** If there is any Python source, it takes up to 400 `.py` source files. It counts `def` and `class` headers with a non-underscore name whose `:` ends the line, then checks whether the next line opens a `"""` or `'''` docstring. Without Python, it takes up to 400 `.ts`, `.tsx`, `.js`, `.go`, `.rs`, `.java`, `.cs` or `.kt` files. A file counts if it contains `/**`, a `///` line or `// Capitalword `.

- **Met:** Python: at least {min_share}% of the counted definitions have docstrings. Other languages: at least 42.5% of files have a doc comment.
- **Partially met:** Python: at least {min_share:partial}%. Other languages: 17.5% to 42.4%.
- **Not met:** Python below {min_share:partial}%. Other languages below 17.5%.
- **Not applicable:** Python source exists but no definition header matched. If the repo has neither Python nor the listed languages, the check is not produced and drops out of the report.

**What the check cannot see.** Multi-line signatures (common after black or ruff format), one-line defs and headers with trailing comments are skipped entirely. Prefixed docstrings (`r"""`) are missed. Any comment starting `// TODO ` counts as a doc comment. `.jsx`, `.rb`, `.php` and C/C++ are never examined.

**Known flaw.** Python always wins. A mostly TypeScript or Go repo with one `.py` script is judged only on that Python file.

**Our convention.** Docstrings are the context an agent reads at the point of change; public code without them is guessed at.
