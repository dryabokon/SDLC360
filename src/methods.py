"""Plain-language explanation of every automated check: what the scanner looks at, and when it counts as met.
Shown next to the evidence so a reader can judge the verdict without reading the code."""

METHODS: dict[str, tuple[str, str]] = {
    # id: (what we look at, when it counts as met)
    # --- security
    "sec.no_secrets": (
        "Every tracked text file at the assessed commit is matched against known token formats (AWS, GitHub, "
        'Anthropic, OpenAI, Slack, Google, Stripe, private-key blocks) and `secret = "…"` assignments. '
        "Placeholders like `your-key`, `xxxx`, env lookups are ignored. Git history is not scanned.",
        "No real-looking token is found. Hits inside tests count as likely fixtures (partially met).",
    ),
    "sec.no_sensitive_files": (
        "File names that usually hold credentials: .env, *.pem, *.key, *.p12, id_rsa, credentials.json, "
        "service-account*.json, *.tfstate, *.tfvars, .npmrc, .pypirc, .netrc. Templates (.env.example) "
        "and files under tests/, fixtures/, docs/, examples/ are ignored.",
        "None of these files is tracked by git.",
    ),
    "sec.gitignore": (
        ".gitignore rules for env files and key material.",
        "`.env` is ignored (70%) and key files such as *.pem / *.key are ignored (30%).",
    ),
    "sec.env_template": (
        "Whether code reads environment variables, and whether a template such as .env.example exists.",
        "Code reads env vars and a template documents them. Not applicable if no env vars are read.",
    ),
    "sec.policy": ("SECURITY.md in the root, .github/ or docs/.", "The file exists."),
    "sec.dep_updates": (".github/dependabot.yml or a Renovate config.", "Automated dependency updates are configured."),
    "sec.ci_scanning": (
        "Workflows and the scripts they call, searched for security tools: CodeQL, gitleaks, trufflehog, "
        "Trivy, Snyk, Semgrep, Bandit, pip-audit, npm audit, osv-scanner, dependency-review, zizmor, …",
        "At least two different tools run in CI (one tool = partially met).",
    ),
    "sec.precommit_secrets": (
        ".pre-commit-config.yaml / husky / lefthook for secret-scanning hooks.",
        "gitleaks, detect-secrets, trufflehog, ggshield or detect-private-key is hooked in.",
    ),
    "sec.workflow_permissions": (
        "Each workflow file for a top-level `permissions:` block; use of `pull_request_target`.",
        "Every workflow declares permissions (share = score); pull_request_target costs 30%.",
    ),
    "sec.codeowners": ("CODEOWNERS in the root, .github/ or docs/.", "The file exists."),
    # --- harness
    "ai.instructions": (
        "Agent instruction files: CLAUDE.md, AGENTS.md, GEMINI.md, .github/copilot-instructions.md, "
        ".cursorrules, .cursor/rules. Symlinks are followed.",
        "One of them sits at the repository root (only nested ones = partially met).",
    ),
    "ai.instructions_quality": (
        "The main instruction file (following `@imports` and symlinks): its length and whether it "
        "talks about commands, testing, layout and conventions.",
        "25–400 lines and all four topics covered; score blends topic coverage (70%) and size (30%).",
    ),
    "ai.instructions_fresh": (
        "Every repo path the instruction file mentions, checked at the assessed commit; the gap between "
        "the file's last change and the last code change.",
        "All referenced paths exist (60%) and the file changed within 30 days of the code (40%).",
    ),
    "ai.settings": (".claude/settings.json and whether it defines permission rules.", "The file exists (50%) and declares `permissions` (50%)."),
    "ai.guardrails": (
        "Agent hooks in .claude/settings.json, .claude/hooks/, pre-commit, husky, lefthook.",
        "Agent hooks are configured (100%); only generic pre-commit hooks = 60%.",
    ),
    "ai.extensions": (
        "Skills, subagents, commands and prompt files under .claude/, .agents/, .github/, .cursor/, .codex/.",
        "At least three such files exist.",
    ),
    "ai.mcp": (".mcp.json, .vscode/mcp.json or .cursor/mcp.json.", "A project MCP configuration exists."),
    "ai.no_local_leak": ("Tracked personal files: .claude/settings.local.json, CLAUDE.local.md.", "None is committed."),
    "ai.ci_agents": ("Workflows for AI agents: claude-code-action, codex-action, CodeRabbit, Copilot.", "At least one is used."),
    "ai.scoped_context": (
        "Nested CLAUDE.md / AGENTS.md below the root (only for repos with more than 300 source files).",
        "At least one nested instruction file exists.",
    ),
    # --- skills
    "sk.present": (
        "SKILL.md files, .claude/agents/*.md, .claude/commands/*.md, .github/prompts, .cursor/rules.",
        "At least three such markdown files exist.",
    ),
    "sk.frontmatter": (
        "YAML frontmatter of every skill / agent / command file.",
        "`name` and `description` are present (commands need only `description`); share = score.",
    ),
    "sk.descriptions": ("The `description` field of each file.", "40–1024 characters and phrased as a trigger ('use when …'); share = score."),
    "sk.size": ("Line count of every skill file.", "No file is longer than 500 lines."),
    "sk.links": ("Relative links and backticked paths inside skill files.", "All of them resolve to files in the repo."),
    "sk.layout": (
        "Skill folder names and supporting scripts/ references/ assets/ folders.",
        "Folders are kebab-case (60%) and supporting files exist (40%).",
    ),
    # --- docs
    "doc.readme": ("The root README and its length.", "A README of at least ~400 words."),
    "doc.readme_sections": (
        "README headings and text for setup, usage, testing, configuration, overview, contributing.",
        "All six topics are covered; share = score.",
    ),
    "doc.docs_dir": ("Markdown / reST pages under docs/, doc/, documentation/.", "At least three pages."),
    "doc.standard_files": ("LICENSE, CONTRIBUTING, CHANGELOG.", "All three exist; share = score."),
    "doc.links": (
        "Relative links and backticked file paths in up to 300 markdown files, resolved at the assessed commit.",
        "Every reference resolves; each broken one costs three times its share.",
    ),
    "doc.freshness": (
        "Last commit touching README / docs versus last commit touching source code.",
        "Docs changed within 30 days of the code; the score fades to zero at one year behind.",
    ),
    "doc.inline": (
        "Docstrings on Python functions/classes, or doc comments in other languages.",
        "At least 60% of Python definitions (50% of other files) are documented.",
    ),
    # --- architecture
    "arch.doc": ("ARCHITECTURE.md, DESIGN.md or docs/*architecture* / *design* / *overview* pages.", "Such a document exists."),
    "arch.diagrams": (
        "Mermaid / PlantUML / D2 / Graphviz blocks in markdown; .puml, .drawio, .excalidraw, .d2, .mmd files.",
        "At least two diagrams.",
    ),
    "arch.adr": ("Folders named adr, adrs, decisions, decision-records with markdown files.", "At least three ADRs."),
    "arch.structure": (
        "Where source files live: in top-level packages or loose in the root.",
        "Code is in folders and at most 5 source files sit in the root.",
    ),
    "arch.boundaries": (
        "import-linter, dependency-cruiser, ArchUnit, workspace tools (nx, turbo, pnpm, go.work, .sln). "
        "Only for repos with more than 50 source files.",
        "A boundary tool or workspace config exists.",
    ),
    "arch.fresh": (
        "Last commit touching the architecture document versus the last code change.",
        "Changed within 30 days of the code; fades to zero at one year behind.",
    ),
    # --- tests
    "test.present": ("Files under tests/, test/, spec/, __tests__/ or named test_*, *_test.*, *.test.*, *.spec.*.", "At least five test files."),
    "test.ratio": ("Number of test files divided by number of source files.", "Ratio of 0.4 or higher."),
    "test.framework": (
        "pytest/tox/nox config, jest/vitest/playwright/cypress config, package.json test script, Go/Rust runners.",
        "The test runner is configured explicitly.",
    ),
    "test.coverage": (
        "Coverage configuration and coverage flags in CI or task runners; minimum thresholds.",
        "Coverage is measured (60%) and a minimum is enforced (40%).",
    ),
    "test.ci": (
        "Workflow steps and the scripts / Makefile / nox / tox / package.json they call, searched for test commands.",
        "A test command runs in GitHub Actions (other CI systems = 50%).",
    ),
    "test.layers": (
        "Test paths and config mentioning integration, e2e (Playwright, Cypress, Selenium) or property tests.",
        "Two of the three layers exist.",
    ),
    # --- ci/cd
    "ci.present": ("Workflow files in .github/workflows.", "At least two workflows (other CI systems = 40%)."),
    "ci.pr": ("Workflow triggers.", "A `pull_request` or `merge_group` trigger exists."),
    "ci.stages": (
        "Workflows plus the scripts they call, searched for lint/type-check, test and build commands.",
        "All three stages are present; share = score.",
    ),
    "ci.cd": (
        "Release / deploy steps (publish, docker push, release actions, deploy tools) and tag/release triggers.",
        "Deploy steps exist and are triggered by tags or releases.",
    ),
    "ci.hygiene": (
        "`timeout-minutes`, `matrix`, `environment` / `workflow_dispatch` in workflows.",
        "Timeouts on every job (40%), a matrix (30%), environments or manual dispatch (30%).",
    ),
    "ci.pinning": (
        "`uses:` references to third-party actions (not actions/* or github/*).",
        "All of them are pinned to a full 40-character commit SHA.",
    ),
    "ci.speed": ("Dependency caching, `concurrency` groups, `paths` filters.", "Cache (45%), concurrency (35%), path filters (20%)."),
    # --- runs
    "run.folder": (
        "Top-level folders runs/, experiments/, outputs/, artifacts/, results/, mlruns/, wandb/ - tracked or on disk "
        "- and .gitignore entries for them.",
        "Such a folder exists (only a .gitignore entry = 50%).",
    ),
    "run.manifest": ("Files named manifest / config / params / metadata / metrics .json/.yaml/.toml inside run folders.", "At least two of them."),
    "run.documented": ("README, CLAUDE.md, AGENTS.md and docs/ for mentions of runs/, experiments/ or reproduction.", "Reproduction is described."),
    "run.tracking": (
        "MLflow, W&B, DVC, Sacred, Hydra, Aim, Neptune, ClearML, TensorBoard, Optuna in code or dependencies.",
        "A tracker is used. Not applicable when no experiment tooling or run folder exists.",
    ),
    "run.lockfile": (
        "uv.lock, poetry.lock, package-lock.json, pnpm-lock.yaml, Cargo.lock, go.sum, pinned requirements, …",
        "A real lockfile exists (an unpinned requirements.txt = 40%).",
    ),
    "run.environment": (
        "Dockerfile, compose files, .devcontainer, Nix, .python-version, .nvmrc, .tool-versions, rust-toolchain, mise.",
        "At least two pinning mechanisms.",
    ),
    "run.entrypoints": (
        "Makefile, justfile, Taskfile, noxfile, tox, scripts/, start*/run* shell scripts, package.json scripts, [project.scripts].",
        "One of them exists.",
    ),
    "run.seeds": (
        "Seed calls (seed(), random_state, manual_seed, set_seed) - only when numpy / torch / sklearn / jax are used.",
        "Seeds are set. Not applicable without an ML / numeric stack.",
    ),
    # --- cost
    "cost.llm_tracking": (
        "Only when an LLM SDK is imported or declared: reads of `usage.*_tokens`, cost counters, Langfuse / Helicone / LangSmith / OpenLIT.",
        "At least two places account for usage or cost.",
    ),
    "cost.llm_limits": ("max_tokens / max_output_tokens, budgets, spend limits, rate limits, max_retries in code.", "At least two such bounds."),
    "cost.llm_efficiency": (
        "Prompt caching (`cache_control`, semantic / disk / redis caches) and a central model constant.",
        "Caching (50%) and a central model config (50%).",
    ),
    "cost.infra": (
        "Terraform / Bicep / CDK / Pulumi / Helm files for budgets, cost tags, autoscaling, spot instances, infracost.",
        "Three different cost signals. Not applicable without infrastructure-as-code.",
    ),
    "cost.ci": (
        "Only when the project pays for LLMs or cloud: job timeouts, cancel-in-progress, path filters.",
        "Timeouts (40%), cancel-in-progress (35%), path filters (25%).",
    ),
    "cost.documented": (
        "README, docs/ and CLAUDE.md for cost, budget, pricing or spend.",
        "Costs are discussed. Not applicable without paid resources.",
    ),
    # --- hygiene
    "hyg.lint": ("ruff, flake8, pylint, eslint, biome, golangci-lint, clippy, rubocop, … configuration.", "A linter is configured."),
    "hyg.format": ("black, ruff format, isort, prettier, rustfmt, clang-format, dprint; gofmt for Go.", "A formatter is configured."),
    "hyg.types": (
        "Python: mypy / pyright config and how many files use annotations. TypeScript: tsconfig and `strict`.",
        "Python: checker configured (50%) + annotations in 70% of files (50%). TS: tsconfig (60%) + strict (40%).",
    ),
    "hyg.precommit": (".pre-commit-config.yaml, husky, lefthook, lint-staged.", "Local hooks are configured."),
    "hyg.editor": (".editorconfig and .gitattributes.", "Both exist; share = score."),
    "hyg.templates": ("Pull-request and issue templates under .github/.", "At least two templates."),
    "hyg.file_size": ("Source files larger than 60 KB.", "None (the score drops with the share of oversized files)."),
}


def method_for(check_id: str) -> dict:
    looks, met = METHODS.get(check_id, ("", ""))
    return {"looks_at": looks, "met_when": met}
