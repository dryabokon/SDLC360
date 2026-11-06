# Security: how each capability is judged

Capabilities and their priorities are in [capabilities.md](../capabilities.md).
How to edit this file: [assessment/README.md](../README.md#acceptance-criteria).

## sec.no_secrets: No secrets or API keys are hard-coded in tracked files.

**How we check.** Every tracked, non-binary text file up to 500 KB at HEAD, line by line (lines over 2000 chars skipped). Skips lock files, `*.min.js`, `*.map`, `*.svg` and `fixture(s)/`, `testdata/`, `__snapshots__/` folders. Looks for AWS, GitHub, Anthropic, OpenAI, Slack, Google, Stripe-live tokens, private-key blocks, and "generic" quoted values of 16+ chars assigned to names like `api_key`, `password`, `client_secret`.

- **Met:** No finding at all. Values that look like placeholders (contain `example`, `test`, `dummy`, `xxxx`, `${`, `process.env`, …) are ignored; generic values must mix letters and digits, have 6+ distinct characters, and are ignored entirely in test files.
- **Partially met:** No real-format token outside tests, but either a generic assigned secret was found (score 0.5) or real-format tokens appear only in test files (0.75).
- **Not met:** At least one real-format token (AWS, GitHub, private key block, etc.) in a non-test file.

**What the check cannot see.** Only HEAD, never git history, so a rotated-out-but-committed secret is invisible. Unknown token formats (Azure, GCP JSON keys, DB URLs with passwords) are missed. A real key containing `test` or `sample` is skipped. Private-key blocks in README examples are flagged. Stops after 50 findings.

**Why we expect it.**

> Continuously monitor each environment for plaintext secrets.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218A PO.5.1.R6, p.19 · direct

> Emphasize that credentials and sensitive tokens must never be hard-coded or exposed
>
> — [openssf-ai-code-assistant-guide](../references/openssf-ai-code-assistant-guide/), Secure Coding Principles > Authentication, Authorization & Secrets Management · direct

> The harness runs deterministic hooks (e.g., blocking a commit if the agent tries to push a hard-coded password).
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 30 · supporting

## sec.no_sensitive_files: No credential files (.env, private keys, tfstate) are committed.

**How we check.** Tracked files whose name (anywhere in the tree) matches `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.jks`, `*.keystore`, `id_rsa`, `id_ed25519`, `credentials.json`, `service-account*.json`, `*.tfstate`, `*.tfvars`, `.npmrc`, `.pypirc`, `.netrc`, `.env`, `.env.*`, `*.env`. Excludes paths containing `example`, ending in `.example/.sample/.template/.dist/.default(s)` or `.env.test`, and anything under `test(s)/`, `fixture(s)/`, `testdata/`, `example(s)/`, `sample(s)/`, `doc(s)/`.

- **Met:** None of those files is committed.
- **Partially met:** never.
- **Not met:** At least one such file is committed.

**What the check cannot see.** Judges by file name only, never contents: a `.npmrc` with just a registry URL, a public CA `*.pem` or a non-secret `*.tfvars` fails the check. `id_ecdsa`, `id_dsa`, `*.kdbx` are not looked for. A real secret file inside `docs/` or `examples/` passes. History is not checked.

**Why we expect it.**

> Only store sensitive data used during AI model development, including production data, within organization-approved environments and locations within those environments.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218A PO.5.1.R2, p.18 · supporting

> Check for any secrets or sensitive data in the suggested code.
>
> — [openssf-ai-code-assistant-guide](../references/openssf-ai-code-assistant-guide/), TL;DR > Be Security-Conscious · supporting

## sec.ci_scanning: CI scans code, dependencies and secrets on every change.

**How we check.** The CI text: `.github/workflows/*.yml|yaml` plus scripts, `Makefile`, `noxfile.py`, `tox.ini`, `package.json`, `pyproject.toml` they call. Counts distinct tool names found anywhere in it: codeql, gitleaks, trufflehog, detect-secrets, trivy, snyk, semgrep, bandit, pip-audit, npm audit, osv-scanner, dependency-review, grype, zizmor, checkov, tfsec, safety check, govulncheck, cargo audit, scorecard.

- **Met:** Two or more different tool names appear.
- **Partially met:** Exactly one tool name appears.
- **Not met:** None appear, including when there are no GitHub workflows at all.

**What the check cannot see.** Plain text match: a name in a comment or a disabled job counts. CodeQL "default setup", GitHub secret scanning or Snyk apps configured outside workflows are invisible. GitLab CI, Jenkins etc. are not read. `cargo-audit` (hyphen) is not matched. Triggers (every PR?) are not checked.

**Known flaw.** The checklist promises scanning of code, dependencies AND secrets; the code only counts tool names, so two SAST tools (e.g. codeql + semgrep) with no dependency or secret scan are Met.

**Why we expect it.**

> Build into the toolchain automatic detection of known vulnerabilities in software components.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218 PW.4.4 Ex.2, p.22 · direct

> Include steps to run security scans (SAST/DAST) and dependency checks in the CI/CD pipeline to catch vulnerabilities early
>
> — [openssf-ai-code-assistant-guide](../references/openssf-ai-code-assistant-guide/), Platform and Runtime Security Considerations > Operational Security · direct

> Using SAST tools can prevent known classes of bugs from being inadvertently introduced in the codebase.
>
> — [openssf-scorecard](../references/openssf-scorecard/), SAST · direct

## sec.dep_updates: Dependency updates are automated (Dependabot / Renovate).

**How we check.** Looks for `.github/dependabot.yml` / `.yaml`, any file named `renovate.json` or `.renovaterc*` anywhere, or `.github/renovate.json*`.

- **Met:** Any of those files exists.
- **Partially met:** never.
- **Not met:** None exists.

**What the check cannot see.** Contents are not read: a Dependabot file covering one ecosystem out of three, or a disabled Renovate config, passes. Renovate config inside `package.json` or a root `renovate.json5`, and Renovate run as a hosted app with org-level config, are missed.

**Why we expect it.**

> These tools automate the process of updating dependencies by scanning for outdated or insecure requirements, and opening a pull request to update them if found.
>
> — [openssf-scorecard](../references/openssf-scorecard/), Dependency-Update-Tool · direct

> Implement processes to update deployed software components to newer versions
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218 PW.4.1 Ex.7, p.21 · supporting

> When suggesting dependency versions, prefer the latest stable release and mention updating dependencies regularly to patch vulnerabilities
>
> — [openssf-ai-code-assistant-guide](../references/openssf-ai-code-assistant-guide/), Addressing Software Supply Chain Security > Stay Updated & Monitor Vulnerabilities · supporting

## sec.gitignore: .gitignore keeps env files and keys out of git.

**How we check.** Concatenates every tracked `.gitignore` in the repo (root and subfolders) and looks for an env rule (a line starting with `.env`, `*.env`, or `/.env` after a slash) and a key rule (`*.pem`, `*.key`, `*.p12`, or the text `.pem` / `.key` anywhere).

- **Met:** Both an env rule and a key rule are present (0.7 + 0.3).
- **Partially met:** Only the env rule is present (0.7).
- **Not met:** Only the key rule (0.3), neither, or no `.gitignore` at all.

**What the check cannot see.** Raw text match: commented-out lines, negations like `!*.pem`, and `.envrc` all count. A rule in a nested `.gitignore` counts as if it covered the whole repo. `.git/info/exclude` and global ignores are not seen. Does not check that `.env.*` variants are covered.

**Our convention.** Ignoring `.env` and key files is the first line of defence against the committed-credential failures that `sec.no_sensitive_files` detects.

## sec.workflow_permissions: CI workflows run with least-privilege tokens.

**How we check.** Each `.github/workflows/*.yml|yaml` file: does it contain a `permissions:` line at any indentation (top-level or per job)? Also whether the word `pull_request_target` appears in any workflow.

- **Met:** At least 85% of workflow files declare `permissions:` and no workflow mentions `pull_request_target`.
- **Partially met:** 35–84% of workflows declare permissions without `pull_request_target`, or 65%+ with it (the 0.3 penalty caps such repos at Partially met).
- **Not met:** Under 35% declare permissions (under 65% if `pull_request_target` is used).
- **Not applicable:** The repo has no GitHub workflow files.

**What the check cannot see.** Only presence of the key counts, so `permissions: write-all` passes. The repository/org default token setting is invisible. `pull_request_target` in a comment still costs 0.3. Non-GitHub CI is ignored.

**Known flaw.** The checklist says "least-privilege tokens", but the value of `permissions:` is never inspected.

**Why we expect it.**

> This check determines whether the project's automated workflows tokens follow the principle of least privilege.
>
> — [openssf-scorecard](../references/openssf-scorecard/), Token-Permissions · direct

> Configure each development endpoint and the development resources to provide the least functionality needed by users and services and to enforce the principle of least privilege.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218 PO.5.2 Ex.2, p.18 · supporting

> Always instruct the AI to follow the principle of least privilege (e.g. minimal file system permissions, least-privileged user accounts for services, etc.) in any configuration or code it proposes.
>
> — [openssf-ai-code-assistant-guide](../references/openssf-ai-code-assistant-guide/), Secure Coding Principles > Secure Defaults & Configurations · supporting

## sec.env_template: Required configuration is documented in an .env.example template.

**How we check.** Whether non-test source code (first 3000 source files, excluding `vendor/`, `third_party/`, `docs/`, `examples/`, `.github/`) reads env vars (`os.environ`, `getenv(`, `process.env.`, `dotenv`, `env::var`, `System.getenv`, `Environment.GetEnvironmentVariable`, case-insensitive), then looks anywhere for `.env.example`, `.env.sample`, `.env.template`, `*.env.example`, `.env.dist`.

- **Met:** Code reads env vars and one of those template files exists.
- **Partially met:** never.
- **Not met:** Code reads env vars but no template file exists (score 0.2).
- **Not applicable:** No env-var reading is detected in source.

**What the check cannot see.** The template's contents are never compared with the variables the code uses; an empty `.env.example` passes. `example.env`, `.env.local.example`, `.env.defaults` are not recognised. Ruby `ENV[...]` and config-file-based apps are not detected. "dotenv" in a comment counts as env usage.

**Why we expect it.**

> Integration tests need DATABASE_URL set, see .env.example
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Keep CLAUDE.md short · supporting

> Implement the default settings (or groups of default settings, if applicable), and document each setting for software administrators.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218 PW.9.2, p.25 · supporting

> Never include API keys, passwords, or secrets in code output, and use environment variables or secure vault references instead.
>
> — [openssf-ai-code-assistant-guide](../references/openssf-ai-code-assistant-guide/), TL;DR Sample Instructions · supporting

## sec.precommit_secrets: A pre-commit hook blocks secrets before they are committed.

**How we check.** Text of any `.pre-commit-config.yaml`, `lefthook.yml` or `.lefthook.yml` anywhere, plus files under root `.husky/`. Looks for gitleaks, detect-secrets, trufflehog, detect-private-key or ggshield.

- **Met:** Any of those names appears.
- **Partially met:** never.
- **Not met:** None appears, or there is no hook config.

**What the check cannot see.** A commented-out hook counts. `detect-private-key` alone (only catches PEM blocks) passes. `lefthook.yaml` and `.lefthook.yaml` are not read. Hooks only run if each developer installs them; that is not verifiable.

**Why we expect it.**

> The harness runs deterministic hooks (e.g., blocking a commit if the agent tries to push a hard-coded password).
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 30 · direct

> Use automated tools to identify and remediate documented and verified unsafe software practices on a continuous basis as human-readable code is checked into the code repository.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218 PW.7.2 Ex.6, p.23 · supporting

## sec.policy: A SECURITY.md explains how to report vulnerabilities.

**How we check.** Any file named `SECURITY.md` (case-insensitive, anywhere in the tree), plus `.github/SECURITY.md` and `docs/SECURITY.md`.

- **Met:** Such a file exists.
- **Partially met:** never.
- **Not met:** None exists.

**What the check cannot see.** Contents are not read, and any `security.md` anywhere (e.g. a docs page about security features) passes. An org-wide policy inherited from a `.github` repository is not seen.

**Known flaw.** The checklist says the file "explains how to report vulnerabilities"; the code only checks that the file exists.

**Why we expect it.**

> Establish a vulnerability disclosure program, and make it easy for security researchers to learn about your program and report possible vulnerabilities.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218 RV.1.3 Ex.1, p.26 · direct

> Place a security policy file `SECURITY.md` in the root directory of your repository.
>
> — [openssf-scorecard](../references/openssf-scorecard/), Security-Policy (remediation) · direct

## sec.codeowners: CODEOWNERS assigns reviewers for sensitive paths.

**How we check.** Any file named `CODEOWNERS` anywhere in the tree (case-insensitive), plus `.github/CODEOWNERS`, `docs/CODEOWNERS`.

- **Met:** Such a file exists.
- **Partially met:** never.
- **Not met:** None exists.

**What the check cannot see.** Contents are not read: an empty file, or one with a single `*` owner, passes. A `CODEOWNERS` in a subfolder GitHub ignores (e.g. a vendored package) also passes.

**Known flaw.** The checklist says owners are assigned "for sensitive paths"; no path coverage is checked.

**Why we expect it.**

> Have the code owner review and approve all changes made to the code by others.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218 PS.1.1 Ex.4, p.18 · direct

> Require review from code owners
>
> — [openssf-scorecard](../references/openssf-scorecard/), Branch-Protection (Tier 4) · direct
