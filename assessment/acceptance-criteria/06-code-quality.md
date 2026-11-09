# Code Quality: how each capability is judged

Capabilities and their priorities are in [capabilities.md](../capabilities.md).
How to edit this file: [assessment/README.md](../README.md#acceptance-criteria).

## hyg.lint: A linter is configured.

**Accepted when.** A linter is configured (ruff, ESLint, golangci-lint and the like).

**How we check.** Matched by name anywhere: `ruff.toml`, `.ruff.toml`, `.flake8`, `.pylintrc`, `pylintrc`, `.eslintrc*`, `eslint.config.*`, `biome.json*`, `.golangci.y*ml`, `clippy.toml`, `.rubocop.yml`, `detekt.yml`, `.editorconfig`, `stylecop.json`, `.swiftlint.yml`, `deno.json`. Also `[tool.ruff`/`[tool.pylint`/`[tool.flake8` in the root `pyproject.toml`, or `"eslint…`/`"@biomejs…` in the root `package.json`.

- **Met:** Any one of these is found.
- **Partially met:** never
- **Not met:** None found.

**What the check cannot see.** The scanner checks that a config exists, not that the linter runs. A config in a vendored or sub-project folder counts. It misses `[flake8]` in `setup.cfg`/`tox.ini`, ruff run with defaults, `.golangci.toml`, and Cargo `[lints]`.

**Known flaw.** `.editorconfig` is in the linter list, so any repo with an `.editorconfig` is Met for "A linter is configured".

**Why we expect it.**

> Use tools (e.g., linters, formatters) to standardize the style and formatting of the source code.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218 PW.5.1 Ex.7, p.22 · direct

> Additionally, mention type checking or the use of linters
>
> — [openssf-ai-code-assistant-guide](../references/openssf-ai-code-assistant-guide/), Programming Language-Specific Security Examples > Python and Dynamic Languages · supporting

## hyg.format: An auto-formatter is configured.

**Accepted when.** An auto-formatter is configured (ruff format, Black, Prettier and the like).

**How we check.** Matched by name anywhere: `.prettierrc*`, `prettier.config.*`, `rustfmt.toml`, `.rustfmt.toml`, `.clang-format`, `dprint.json`. Also `[tool.black`/`[tool.ruff.format`/`[tool.isort` in the root `pyproject.toml`, any `go.mod` (gofmt), `"prettier…`/`"@biomejs…` in the root `package.json`, a biome config found by `hyg.lint`, or any `[tool.ruff` section in `pyproject.toml`.

- **Met:** Any one is found.
- **Partially met:** never
- **Not met:** None found.

**What the check cannot see.** Any `[tool.ruff` section counts as "ruff format", even lint-only, but a standalone `ruff.toml` does not. Every Go module passes automatically, and Rust passes only with a `rustfmt.toml`. The scanner never checks enforcement in CI or hooks.

**Why we expect it.**

> Use tools (e.g., linters, formatters) to standardize the style and formatting of the source code.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218 PW.5.1 Ex.7, p.22 · direct

## hyg.types: Static typing is enforced.

**Accepted when.** Types are checked: a type checker is configured and about half of the Python files are annotated, or TypeScript runs in strict mode.

**How we check.** If any `.py` source file exists (the Python branch wins over TS): type-checker config (`[tool.mypy`/`[tool.pyright`/`[tool.basedpyright` in root `pyproject.toml`, or `mypy.ini`, `.mypy.ini`, `pyrightconfig.json` anywhere). It also counts the share of the first 300 Python source files with at least one annotated parameter or `->` return. Score = 0.5 x config + 0.5 x min(1, share / 0.7). Otherwise, if any JS/TS source file exists: score = 0.6 x any `tsconfig*.json` + 0.4 x any of them containing `"strict": true`.

- **Met:** Python: checker config AND at least 49% of files annotated. TS/JS: a tsconfig with `"strict": true`.
- **Partially met:** Python: config with under 49% annotated, or no config but at least 49% annotated. TS/JS: tsconfig without `strict: true` (0.6).
- **Not met:** Python: no config and under 49% annotated. TS/JS: no `tsconfig*.json` (e.g. plain JS).
- **Not applicable:** No Python and no JS/TS source files (e.g. Go, Rust, Java, Ruby, PHP).

**What the check cannot see.** The scanner never checks that the checker runs (CI/pre-commit) or how strict it is. `->` anywhere in a file, even in comments or strings, counts as annotated. One script `.py` in a TS repo switches to the Python branch. `strict` inherited via `extends` from a package is missed.

**Known flaw.** The checklist says typing is "enforced", but only config presence and annotation share are checked. Ruby, PHP, Lua and shell are dynamically typed yet not applicable (evidence says "no dynamically-typed code").

**Why we expect it.**

> For Python, follow PEP 8 and use type hints, as this can catch misuse early.
>
> — [openssf-ai-code-assistant-guide](../references/openssf-ai-code-assistant-guide/), TL;DR Sample Instructions · supporting

## hyg.precommit: Pre-commit hooks run format and lint locally.

**Accepted when.** Pre-commit hooks (pre-commit, husky, lefthook) run checks before every commit.

**How we check.** Matched by name anywhere: `.pre-commit-config.yaml`, `lefthook.yml`, `.lefthook.yml`, `lint-staged.config.*`, `.lintstagedrc*`, plus any file under root `.husky/`.

- **Met:** Any one is found.
- **Partially met:** never
- **Not met:** None found.

**What the check cannot see.** Hook contents are not read. Husky/lint-staged configured inside `package.json`, `lefthook.yaml`, and `.pre-commit-config.yml` are missed.

**Known flaw.** The checklist says hooks "run format and lint locally". The code only checks that a hook config file exists.

**Why we expect it.**

> Use development environments with automated features that encourage or require the use of secure coding practices with just-in-time training-in-place.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218 PW.5.1 Ex.5, p.22 · supporting

## arch.structure: Source code is organised into modules, not a flat root.

**Accepted when.** Code lives in folders, and at most {max_root_files} source files sit in the project root.

**How we check.** Source files (by extension, excluding tests, `vendor/`, `third_party/`, `docs/`, `examples/`, `.github/`). It counts how many sit in the repo root and whether any sit in a subfolder.

- **Met:** At least one source file in a subfolder and at most {max_root_files} source files in the root.
- **Partially met:** {max_root_files+1} to {max_root_files*3} source files in the root, or all code in the root with at most {max_root_files*3} files.
- **Not met:** More than {max_root_files*3} source files in the root (score 0.3).
- **Not applicable:** No source files at all.

**What the check cannot see.** `.sh` and `.ps1` count as source, so root helper scripts count against the repo. One nested file (for example `scripts/x.sh`) is enough. A flat `src/` holding hundreds of files is Met. Module cohesion is not judged.

**Why we expect it.**

> Folder hierarchies, naming conventions, and timestamps all provide important signals that help both humans and agents understand how and when to utilize information.
>
> — [anthropic-context-engineering](../references/anthropic-context-engineering/), Context retrieval and agentic search · supporting

> Define policies that specify risk-based software architecture and design requirements, such as making code modular to facilitate code reuse and updates
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218 PO.1.2 Ex.1, p.14 · supporting

## hyg.file_size: No oversized source files.

**Accepted when.** No source file is larger than {max_kb} KB (large projects may have a few).

**How we check.** On-disk size of the first 3000 source files (tests, vendor/, third_party/, docs/, examples/ and .github/ excluded). Files over {max_kb} KB ({max_kb*1000} bytes) are oversized. Score = 1 − min(1, oversized / D), where D = max(5, 5% of all source files).

- **Met:** Up to 100 source files: none oversized. Over 100: oversized files are at most 0.75% of source files.
- **Partially met:** Up to 100 source files: 1–3 oversized. Over 100: more than 0.75% and at most 3.25%.
- **Not met:** Up to 100 source files: 4 or more oversized. Over 100: above 3.25%.

**What the check cannot see.** Generated or minified source (bundled `.js`, protobuf stubs) counts. Big non-source files (JSON, notebooks, markdown) and tests are ignored. A repo with no source files is Met.

**Our convention.** Very large files hurt human review and overflow agent context budgets (see anthropic-context-engineering on limited attention).

## hyg.editor: .editorconfig / .gitattributes keep formatting consistent.

**Accepted when.** At least 2 settings files keep formatting consistent across editors (`.editorconfig`, `.gitattributes` and the like).

**How we check.** Files named `.editorconfig` or `.gitattributes` anywhere. Score = number of such files / 2, with no cap.

- **Met:** 2 or more such files.
- **Partially met:** Exactly 1 (0.5).
- **Not met:** None.

**What the check cannot see.** File contents are not read.

**Known flaw.** The scanner counts files, not the two kinds. Two `.gitattributes` in different folders meet it with no `.editorconfig`. The score is not capped: 3 files give 1.5, above the 0..1 range.

**Our convention.** Shared line-ending and whitespace rules prevent noisy diffs between Windows, Linux and agent-generated edits.

## arch.boundaries: Module boundaries are explicit and enforced by tooling.

**Accepted when.** A tool enforces module boundaries (import-linter, dependency-cruiser, ArchUnit or a workspace tool). Checked only for projects with more than {min_source_files} source files.

**How we check.** Files anywhere named `.importlinter`, `importlinter.ini`, `.dependency-cruiser.*`, `nx.json`, `turbo.json`, `pnpm-workspace.yaml`, `go.work`, `lerna.json` or `*.sln`. Also a root `pyproject.toml` containing the text "importlinter" or "tach", and `ArchUnit`/`ArchRule`/`NetArchTest`/`deptry` text in up to 500 test files. Score: 0.5 per file found, plus 0.5 for a test hit.

- **Met:** Two or more of those files, or one file plus a test hit.
- **Partially met:** Exactly one file, or only a test hit.
- **Not met:** Nothing found.
- **Not applicable:** {min_source_files} or fewer source files.

**What the check cannot see.** Whether the rules are run in CI or actually enforced is not checked. deptry is usually configured in `pyproject.toml`, not tests, so it is rarely seen there.

**Known flaw.** Workspace files (`*.sln`, `nx.json`, `pnpm-workspace.yaml`, `go.work`, `lerna.json`) declare workspaces, they do not enforce boundaries. Two `.sln` files give Met. The "tach" text test also matches "attach", "detach" and so on anywhere in `pyproject.toml`.

**Why we expect it.**

> We need to work within software architectures that give us independence of action—more than ever, we need to be able to develop, test, and deploy software independently.
>
> — [dora-2025-state-of-ai-assisted-development](../references/dora-2025-state-of-ai-assisted-development/), p. 9 · supporting
