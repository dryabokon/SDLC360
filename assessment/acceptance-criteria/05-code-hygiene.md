# Code hygiene: how each capability is judged

Capabilities and their priorities are in [capabilities.md](../capabilities.md).
How to edit this file: [assessment/README.md](../README.md#acceptance-criteria).

## hyg.lint: A linter is configured.

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

## hyg.file_size: No oversized source files.

**How we check.** On-disk size of the first 3000 source files (tests, vendor/, third_party/, docs/, examples/ and .github/ excluded). Files over {max_kb} KB ({max_kb*1000} bytes) are oversized. Score = 1 − min(1, oversized / D), where D = max(5, 5% of all source files).

- **Met:** Up to 100 source files: none oversized. Over 100: oversized files are at most 0.75% of source files.
- **Partially met:** Up to 100 source files: 1–3 oversized. Over 100: more than 0.75% and at most 3.25%.
- **Not met:** Up to 100 source files: 4 or more oversized. Over 100: above 3.25%.

**What the check cannot see.** Generated or minified source (bundled `.js`, protobuf stubs) counts. Big non-source files (JSON, notebooks, markdown) and tests are ignored. A repo with no source files is Met.

**Our convention.** Very large files hurt human review and overflow agent context budgets (see anthropic-context-engineering on limited attention).

## hyg.editor: .editorconfig / .gitattributes keep formatting consistent.

**How we check.** Files named `.editorconfig` or `.gitattributes` anywhere. Score = number of such files / 2, with no cap.

- **Met:** 2 or more such files.
- **Partially met:** Exactly 1 (0.5).
- **Not met:** None.

**What the check cannot see.** File contents are not read.

**Known flaw.** The scanner counts files, not the two kinds. Two `.gitattributes` in different folders meet it with no `.editorconfig`. The score is not capped: 3 files give 1.5, above the 0..1 range.

**Our convention.** Shared line-ending and whitespace rules prevent noisy diffs between Windows, Linux and agent-generated edits.

## hyg.templates: PR and issue templates guide contributors.

**How we check.** Files at `.github/pull_request_template.md`, `.github/PULL_REQUEST_TEMPLATE*` (including that folder), `.github/ISSUE_TEMPLATE/*` (including `config.yml`) and `docs/pull_request_template.md`. Score = min(1, count / 2).

- **Met:** 2 or more matching files.
- **Partially met:** Exactly 1.
- **Not met:** None.

**What the check cannot see.** A root-level `pull_request_template.md` (supported by GitHub) is missed, and so are org-wide templates from a `.github` repository. Template content is not checked.

**Known flaw.** The checklist says "PR and issue templates", but two issue-template files (or one plus `config.yml`) meet it with no PR template.

**Our convention.** PR and issue templates turn the review checklist into a habit; a nice-to-have sign of maturity.
