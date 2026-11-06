# Reproducibility: how each expectation is judged

Expectations and their priorities are in [expectations.md](../expectations.md).
How to edit this file: [assessment/README.md](../README.md#acceptance-criteria).

## rep.lockfile: Dependencies are locked to exact versions.

**How we check.** Lockfiles anywhere in the tree by file name: `uv.lock`, `poetry.lock`, `Pipfile.lock`, `pdm.lock`, `pixi.lock`, `conda-lock.yml`, `requirements*.lock`, `package-lock.json`, `npm-shrinkwrap.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lock(b)`, `Cargo.lock`, `go.sum`, `Gemfile.lock`, `composer.lock`, `packages.lock.json`, `gradle.lockfile`, `flake.lock`. It also reads every `requirements*.txt` and `constraints*.txt`.

- **Met:** At least one lockfile exists, or at least one `requirements*.txt` / `constraints*.txt` is "fully pinned". Fully pinned means it has at least one requirement line and every one contains `==` or ` @ `. Comments and lines starting with `-` are ignored.
- **Partially met:** No lockfile and no fully pinned file, but at least one `requirements*.txt` exists (score 0.4).
- **Not met:** No lockfile and no `requirements*.txt` at all, for example a `pyproject.toml` or `package.json` with no lock.
- **Not applicable:** The repository has no manifest (`pyproject.toml`, `setup.py`, `setup.cfg`, `requirements*.txt`, `package.json`, `Cargo.toml`, `go.mod`, `Gemfile`, `composer.json`, `*.csproj`, `pom.xml`, `build.gradle*`, `environment.yml`) and no source files.

**What the check cannot see.** The scanner checks that a lockfile exists, not that it is current or matches the manifest. A lockfile in a fixture, vendored or sub-project folder counts for the whole repo. `==` anywhere on the line counts as pinned, including `foo==1.*` and `foo>=1; python_version=="3.8"`. Maven, plain Gradle and NuGet projects without a lock are not met.

**Known flaw.** The checklist says "every requirement is pinned", but one fully pinned file is enough. A pinned `requirements-dev.txt` or `constraints.txt` makes the check Met even when the runtime `requirements.txt` is unpinned.

**Why we expect it.**

> Dependency gatekeeping: Allowlist and pin; scan for typosquats (PyPI, npm, LangChain, LlamaIndex); verify provenance before install or activation
>
> — [owasp-agentic-top10-2026](../references/owasp-agentic-top10-2026/), ASI04 guideline 2, p.21 · direct

> If your project is producing an application and the package manager supports lock files (e.g. `package-lock.json` for npm), make sure to check these in the source code as well.
>
> — [openssf-scorecard](../references/openssf-scorecard/), Pinned-Dependencies (remediation) · direct

> Maintain a list of organization-approved commercial software components and component versions along with their provenance data.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218 PW.4.1 Ex.5, p.21 · supporting

## rep.environment: Runtime and toolchain versions are pinned (version files / container).

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

## rep.entrypoints: One command sets up, builds and tests the project.

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

## rep.documented: How to get the same result from a clean checkout is documented.

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

## rep.provenance: Results record the code version and configuration that produced them.

**How we check.** Source files (first 3000) are searched for an ML import (`import torch|tensorflow|sklearn|jax|xgboost|lightgbm`, `from torch|sklearn|transformers|tensorflow|jax import`) and for tracker words (`mlflow`, `wandb`, `dvc`, `sacred`, `aim`, `neptune`, `clearml`, `comet_ml`, `tensorboard`, `lightning.pytorch.loggers`). Tracker words are also searched in requirements, `pyproject.toml` and `package.json`. It also looks for `dvc.yaml`, `.dvc/config`, `MLproject`, and for git-SHA code (`rev-parse HEAD`, `git describe`, `GITHUB_SHA`, `GIT_COMMIT`, `git_sha`, `commit_sha`, `get_git_hash`, `repo.head.commit`).

- **Met:** The check applies, and a tracker word, a DVC/MLproject file or git-SHA code is found.
- **Partially met:** never
- **Not met:** An ML import is found, but no tracker, no DVC/MLproject file and no SHA-recording code.
- **Not applicable:** No ML import, no tracker word and no DVC/MLproject file.

**What the check cannot see.** A tracker word alone makes the check both applicable and Met, so it can only fail for ML imports without tracking. The scanner never checks that config or seed are logged with results. `from torch.nn import`-style imports are not detected as ML.

**Known flaw.** Bug: the tracker pattern includes the bare word `aim` (case-insensitive), so any comment such as "we aim to…" makes the check applicable and Met.

**Why we expect it.**

> Track the provenance of an AI model and its components and derivatives, including the training libraries, frameworks, and pipelines used to build the model.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218A PS.3.2.R1, p.21 · direct

> Where applicable, use an attestations framework such as in-toto or similar to create verifiable records of your build and deployment processes
>
> — [openssf-ai-code-assistant-guide](../references/openssf-ai-code-assistant-guide/), Addressing Software Supply Chain Security > Generate Software Bill of Materials (SBOM) · supporting

> Signed releases attest to the provenance of the artifact.
>
> — [openssf-scorecard](../references/openssf-scorecard/), Signed-Releases · supporting

## rep.seeds: Randomness is seeded where results depend on it.

**How we check.** Applies only when an ML import (same pattern as `rep.provenance`, first 2000 source files) is found. Source files are then searched for `seed(`, `random_state`, `manual_seed`, `set_seed`, `--seed` or `SEED =` (case-insensitive, so `seed=` also counts).

- **Met:** At least one seed match.
- **Partially met:** never
- **Not met:** ML import found, no seed match.
- **Not applicable:** No ML import, even if only a tracker is present.

**What the check cannot see.** One match anywhere is enough. The scanner never checks that every RNG (python, numpy, torch) is seeded or that the seed is recorded. Test files are excluded, and numpy-only numeric code is never applicable.

**Known flaw.** Bug: `\b--seed` needs a letter or digit right before the `-`, so `add_argument("--seed")` never matches.

**Why we expect it.**

> Random number generation is an obvious source of non-determinism, which can be alleviated with seeding.
>
> — [google-ml-test-score](../references/google-ml-test-score/), Infra 1, p.4 · direct
