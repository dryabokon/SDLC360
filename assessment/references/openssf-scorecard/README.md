---
id: openssf-scorecard
title: OpenSSF Scorecard: check documentation
publisher: OpenSSF
authors: ossf/scorecard contributors
published: living document (main branch)
kind: automated check catalogue
url: https://github.com/ossf/scorecard/blob/main/docs/checks.md
retrieved: 2026-11-06
license: Apache-2.0
files:
  - commit checks.md fa84a01753971589571c22597d5b7f65ed34dc373dfc466d2233437faf4dc81f https://raw.githubusercontent.com/ossf/scorecard/main/docs/checks.md
---

# OpenSSF Scorecard: check documentation

The closest existing catalogue of analytical (non-LLM) repository checks; several of ours mirror Scorecard checks.

## Key points

- Token-Permissions: workflows should set read-only top-level permissions and declare write scopes per job. (Token-Permissions)
- Pinned-Dependencies: pin GitHub Actions and Dockerfile images by hash, commit lockfiles and declare exact versions. Pair pinning with automated update tooling. (Pinned-Dependencies)
- Dependency-Update-Tool checks for a Dependabot or Renovate config. The check only detects that the tool is enabled; it does not check that its pull requests are merged. (Dependency-Update-Tool)
- SAST looks for CodeQL or SonarCloud on recent PRs, or `github/codeql-action` in workflows. Vulnerabilities queries OSV for unfixed issues in code and dependencies. (SAST; Vulnerabilities)
- Branch-Protection is scored in tiers: no force-push/deletion, then required reviews, then required status checks, then two reviewers plus code-owner review. Code-Review requires human review; reviews by AI bots do not count. (Branch-Protection; Code-Review)
- CI-Tests looks for tests run before merge. Security-Policy looks for a SECURITY.md with contact links, disclosure text and timelines. License looks for a top-level LICENSE. (CI-Tests; Security-Policy; License)
- Dangerous-Workflow (rated Critical) flags `pull_request_target`/`workflow_run` combined with a PR checkout, and script injection from untrusted `github.event.*` context. Binary-Artifacts flags committed executables. (Dangerous-Workflow; Binary-Artifacts)
- SBOM and Signed-Releases give credit for SBOMs and signatures or SLSA provenance attached to releases. (SBOM; Signed-Releases)

## Used for

- `doc.standard_files`
- `rev.via_pr`
- `sec.codeowners`
- `ci.pr`
- `rep.environment`
- `ci.cd`
- `ci.pinning`
- `rep.lockfile`
- `sec.ci_scanning`
- `sec.dep_updates`
- `sec.workflow_permissions`
- `sec.policy`
