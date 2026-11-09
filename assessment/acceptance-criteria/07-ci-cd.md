# CI/CD: how each capability is judged

Capabilities and their priorities are in [capabilities.md](../capabilities.md).
How to edit this file: [assessment/README.md](../README.md#acceptance-criteria).

## ci.present: CI runs on GitHub Actions.

**Accepted when.** At least one GitHub Actions workflow exists.

**How we check.** `.yml`/`.yaml` files under `.github/workflows/`, subfolders included. With none, it looks for `.gitlab-ci.yml`, `Jenkinsfile`, `azure-pipelines.yml`, `.circleci/config.yml`, `bitbucket-pipelines.yml` or `.travis.yml`.

- **Met:** At least one workflow file.
- **Partially met:** No workflows, but another CI config exists (0.4).
- **Not met:** No CI configuration.

**What the check cannot see.** Workflow content, triggers and validity are not read. Files in subfolders of `.github/workflows/` count although GitHub does not run them.

**Known flaw.** With no GitHub workflows, all other ci.* checks are forced to Not met, even if GitLab or another CI runs everything.

**Why we expect it.**

> It ensures that AI-generated code is consistently tested, secured, and deployed, turning individual productivity gains into systemic, organizational improvements.
>
> — [dora-2025-ai-capabilities-model](../references/dora-2025-ai-capabilities-model/), p. 61 · supporting

> Use code-based configuration for toolchains (e.g., pipelines-as-code, toolchains-as-code).
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218 PO.3.2 Ex.3, p.16 · supporting

## ci.pr: CI gates pull requests before merge.

**Accepted when.** CI runs on pull requests.

**How we check.** All workflow text, searched for the triggers `pull_request`, `pull_request_target` or `merge_group` in any YAML form: a key (`pull_request:`), a list item (`- pull_request`), a scalar (`on: pull_request`) or a flow list (`on: [push, pull_request]`).

- **Met:** One of those triggers is found.
- **Partially met:** Never.
- **Not met:** None is found, or there are no workflows.

**What the check cannot see.** A PR trigger on any workflow (for example a labeler) counts. It does not check that the workflow runs real checks or that branch protection marks them required, which "gates before merge" implies.

**Why we expect it.**

> In the outer loop, version control provides the scaffolding for human-in-the-loop review of changes before they are merged.
>
> — [dora-2025-ai-capabilities-model](../references/dora-2025-ai-capabilities-model/), p. 39 · direct

> Require branch to pass at least 1 status check before merging
>
> — [openssf-scorecard](../references/openssf-scorecard/), Branch-Protection (Tier 3) · direct

> Tests and quality gates that verify correctness
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 24 · supporting

## ci.stages: CI lints, tests and builds.

**Accepted when.** CI lints, tests and builds.

**How we check.** It searches `ci_text` (workflows plus the scripts they delegate to) for three stages. Lint/typecheck: `ruff`, `eslint`, `mypy`, `pre-commit run` and others. Test: the test.ci command list. Build: `\bbuild\b`, `docker build`, `cargo build`, `tsc` and others.

- **Met:** All 3 stages are found.
- **Partially met:** 2 of the 3.
- **Not met:** 0 or 1, or no workflows.

**What the check cannot see.** These are substring matches anywhere. A tool named in an install line or a delegated `pyproject.toml` dependency list counts as a stage.

**Known flaw.** The build pattern `\bbuild\b` matches any word "build", such as a job named `build:` that only runs tests, `pip install build` or a step title. The build stage is almost always "present".

**Our convention.** Lint, test and build in CI are the minimum feedback loop; each missing stage lets a class of defects reach main.

## rep.entrypoints: One command sets up, builds and tests the project.

**Accepted when.** One command sets up, builds or tests the project (a Makefile, scripts, `start.sh`, package.json scripts).

**How we check.** Any of these, matched by name anywhere: `Makefile`, `justfile`, `Taskfile.y*ml`, `noxfile.py`, `tox.ini`, `start*.sh`, `run*.sh`, `start*.bat`. Also any file under the root `scripts/`, a `"scripts":` key in the root `package.json`, or `[project.scripts]`, `[tool.poe` or `[tool.hatch.envs` in the root `pyproject.toml`.

- **Met:** At least one of these is found (the score is true/false).
- **Partially met:** never
- **Not met:** None is found.

**What the check cannot see.** The scanner checks that a runner exists, not that its commands set up, build or test. Any stray file in `scripts/`, or a Makefile in a vendored folder, meets it. `[project.scripts]` declares console entry points, not tasks. Gradle/Maven wrappers, `Rakefile`, `.csproj` and `Cargo` aliases are not recognised.

**Known flaw.** The checklist says "One command sets up, builds and tests the project". The code only checks that some task runner or script exists.

**Why we expect it.**

> The goal is to be able to reproduce testing and production environments in a fully automated fashion using only information from version control.
>
> — [dora-2025-ai-capabilities-model](../references/dora-2025-ai-capabilities-model/), p. 41 · supporting

## rep.environment: Runtime and toolchain versions are pinned (version files / container).

**Accepted when.** At least 2 files pin the runtime and tool versions (`.python-version`, `.nvmrc`, a Dockerfile and the like).

**How we check.** Counts files, matched by name anywhere: `.python-version`, `.nvmrc`, `.node-version`, `.tool-versions`, `mise.toml`, `.mise.toml`, `rust-toolchain*`, `global.json`, `.sdkmanrc`, `.java-version`, `.ruby-version`, `.go-version`, `Dockerfile`, `*.dockerfile`, `docker-compose*.yml`, `compose.y*ml`, `flake.nix`, `shell.nix`, `devbox.json`. It also counts any file under the root `.devcontainer/`.

- **Met:** 2 or more matching files (score = files / 2, capped at 1).
- **Partially met:** Exactly 1 matching file (0.5).
- **Not met:** None.

**What the check cannot see.** The scanner counts files, not distinct mechanisms. Two `Dockerfile`s, or two files in `.devcontainer/`, meet the check. File contents are never read, so an unpinned `FROM python:latest` counts. `Dockerfile.dev` and `docker-compose.yaml` are missed. A `global.json` that is not the .NET SDK file also counts.

**Known flaw.** The intent is "at least two pinning mechanisms", but the code counts matching files.

**Why we expect it.**

> Version everything: Store all production artifacts in version control. This includes application code, system configurations, test scripts, deployment scripts, container orchestration files, and cloud configuration files.
>
> — [dora-2025-ai-capabilities-model](../references/dora-2025-ai-capabilities-model/), p. 41 · direct

> pin image versions using immutable digests (e.g., SHA256 hashes) instead of mutable tags like latest
>
> — [openssf-ai-code-assistant-guide](../references/openssf-ai-code-assistant-guide/), Platform and Runtime Security Considerations > Container and Deployment Considerations · direct

> For Dockerfiles used in building and releasing your project, pin dependencies by hash.
>
> — [openssf-scorecard](../references/openssf-scorecard/), Pinned-Dependencies (remediation) · direct

## rep.documented: How to get the same result from a clean checkout is documented.

**Accepted when.** The docs explain how to set up and get the same results from a clean checkout.

**How we check.** Joins the text of the first 40 files matching `README*`, `CONTRIBUTING*`, `AGENTS.md` or `CLAUDE.md` anywhere, or any `docs/**.md`. It looks for (a) a markdown heading line (`#…`) containing install, setup, getting started, quick start/quickstart or development, and (b) reproduction wording: `reproduc*`, `rerun`/`re-run*`, `deterministic*`, or "same result(s)".

- **Met:** Both a setup heading and reproduction wording are found.
- **Partially met:** Only one of them is found (0.5).
- **Not met:** Neither is found.

**What the check cannot see.** Lines in code blocks that start with `#`, such as `# install deps`, count as headings. Any README in a subfolder or vendored package counts. Both checks are keyword matches: a "reproducible builds" badge or the word "rerun" satisfies (b). The scanner never checks that the steps lead to the same result.

**Why we expect it.**

> keep the install command in `CLAUDE.md` so Claude runs it whenever it starts in a new checkout
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Run sessions in parallel · supporting

> One of the most common pitfalls is storing only application source code in version control.
>
> — [dora-2025-ai-capabilities-model](../references/dora-2025-ai-capabilities-model/), p. 42 · supporting

> Include documentation of the entire training process, such as data preprocessing and model architecture.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218A PS.3.1.R3, p.21 · supporting

## ci.cd: Releases or deployments are automated.

**Accepted when.** Releases or deployments are automated, for example on a version tag.

**How we check.** Workflow text only (not delegated scripts). It looks for deploy keywords (`deploy`, `release`, `publish`, `docker push`, `helm`, `kubectl`, `aws-actions`, `goreleaser` and others). It also looks for a tag trigger (`tags:` followed by a list item) or `release:` followed by `types`. Score: 0.5 for any keyword, 0.5 for a tag/release trigger, 0.5 for 3 or more distinct keywords, capped at 1.

- **Met:** A keyword plus a tag/release trigger, or 3 or more distinct keywords.
- **Partially met:** 1 or 2 distinct keywords without a tag trigger, or a tag trigger alone.
- **Not met:** No keyword and no tag trigger, or no workflows.

**What the check cannot see.** The keywords are case-insensitive substrings. "release" in a branch filter, "publish" in a step name, `aws-actions` for test credentials, or a docs `deploy-pages` all count. Three such words give Met without any real release. `on: release` as a scalar is missed.

**Why we expect it.**

> If hosted on GitHub, use a GitHub action to release your package to language-specific hubs.
>
> — [openssf-scorecard](../references/openssf-scorecard/), Packaging (remediation) · direct

> Tag `v<new version>` and push the tag. CI publishes from there, never publish from your machine.
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Put team procedures in skills · supporting

> Continuous integration and deployment pipelines may need to evolve to reduce wait states and allow for higher-frequency delivery.
>
> — [dora-2025-state-of-ai-assisted-development](../references/dora-2025-state-of-ai-assisted-development/), p. 82 · supporting

## ci.hygiene: Jobs have timeouts, version matrices and protected environments.

**Accepted when.** CI jobs have timeouts, a version matrix, and protected environments or manual approval.

**How we check.** Workflow text only. It counts occurrences of `timeout-minutes` (job or step level) against detected jobs: 2-space keys whose next line is a 4-space `runs-on:` or `uses:`, minimum 1. It also looks for any `matrix:`, and for an `environment:` line or `workflow_dispatch`. Score = 0.4×min(1, timeouts/jobs) + 0.3×matrix + 0.3×(environment or dispatch).

- **Met:** A matrix, an environment or manual dispatch, and timeouts on at least about 63% of detected jobs.
- **Partially met:** A score of 0.35 to 0.84. Examples: timeouts on all jobs alone (0.4), matrix plus environment/dispatch (0.6), or one of those plus timeouts on at least 1 in 8 jobs.
- **Not met:** Below 0.35, for example only a matrix or only `workflow_dispatch`. Also when there are no workflows.

**What the check cannot see.** Jobs whose first key is `name:`, `needs:` or `if:` are not counted as jobs. Step-level timeouts inflate the ratio, so full timeout credit is easy to reach falsely.

**Known flaw.** The checklist says "protected environments". The code accepts any `workflow_dispatch` trigger instead, and never checks that an environment is protected.

**Why we expect it.**

> Separate and protect each environment involved in software development.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218 PO.5.1, p.17 · supporting

## ci.pinning: Third-party actions are pinned to commit SHAs.

**Accepted when.** Nearly all third-party actions (85%) are pinned to a commit SHA.

**How we check.** It finds `uses: owner/repo@ref` entries in workflow text, excluding `actions/*` and `github/*`. It counts every occurrence whose ref is exactly 40 lowercase hex characters as pinned.

- **Met:** At least 85% of third-party `uses:` occurrences are SHA-pinned, or there are no third-party actions.
- **Partially met:** 35% to 84% are pinned.
- **Not met:** Under 35% are pinned, or there are no workflows.

**What the check cannot see.** Occurrences are counted, not unique actions. Uppercase SHAs count as unpinned. Whether a SHA belongs to the claimed tag is not checked. Docker `uses:` and composite actions' internal `uses:` are not seen.

**Why we expect it.**

> use the latest versions of devops dependencies such as GitHub actions and lock the version to specific SHA
>
> — [openssf-ai-code-assistant-guide](../references/openssf-ai-code-assistant-guide/), Platform and Runtime Security Considerations > Operational Security · direct

> For GitHub workflows used in building and releasing your project, pin dependencies by hash.
>
> — [openssf-scorecard](../references/openssf-scorecard/), Pinned-Dependencies (remediation) · direct

> Regularly verify the integrity and check the provenance of each tool to identify potential problems.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218 PO.3.2 Ex.7, p.16 · supporting

## ci.speed: CI is fast: caching, cancel-in-progress and path filters.

**Accepted when.** CI caches dependencies, cancels outdated runs and skips unrelated changes.

**How we check.** Workflow text only. Cache: `actions/cache`, `cache: pip|npm|yarn|pnpm|gradle|maven|go|poetry|uv`, `enable-cache`, `setup-uv`, `Swatinem/rust-cache` or `cache-from`. Concurrency: a `concurrency:` line. Paths: a `paths:` or `paths-ignore:` line. Score = 0.45 cache + 0.35 concurrency + 0.2 paths.

- **Met:** All three are found (cache plus concurrency alone is only 0.8).
- **Partially met:** Any combination scoring 0.35 to 0.8: cache alone, concurrency alone, or two of the three.
- **Not met:** Nothing found, or only path filters (0.2), or no workflows.

**What the check cannot see.** Using `setup-uv` counts as caching even without `enable-cache`. Default caching in `setup-go` is not seen. Whether caches actually hit is not checked.

**Known flaw.** The checklist says "cancel-in-progress", but any `concurrency:` block counts, even without `cancel-in-progress: true`. Met also needs path filters, which many fast repos rightly do not use.

**Why we expect it.**

> We need fast feedback loops—faster than ever—to match AI-accelerated code generation.
>
> — [dora-2025-state-of-ai-assisted-development](../references/dora-2025-state-of-ai-assisted-development/), p. 9 · supporting
