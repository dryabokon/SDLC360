# Code Review: how each capability is judged

Capabilities and their priorities are in [capabilities.md](../capabilities.md).
How to edit this file: [assessment/README.md](../README.md#acceptance-criteria).

## rev.via_pr: Changes reach the main branch through pull requests.

**Accepted when.** At least {min_share}% of the recent commits on the main branch came through a pull request.

**How we check.** The last 100 commits of the main line (HEAD, first parent only) are read from git. A commit came through a pull request when its subject carries a mark that GitHub or GitLab leaves: `Merge pull request #12`, a squash subject ending in `(#12)`, `Merge branch 'x' into main` or `See merge request !12`.

- **Met:** At least {min_share}% of them.
- **Partially met:** At least {min_share:partial}%.
- **Not met:** Fewer.
- **Not applicable:** Fewer than 10 commits.

**What the check cannot see.** Whether a person approved the pull request: approvals live on the hosting service, not in git. Rebase merges and squash subjects that drop the `(#12)` look like direct pushes. A team that works directly on `main` with pair review is judged as not met.

**Why we expect it.**

> This check determines whether the project requires human code review before pull requests (merge requests) are merged.
>
> — [openssf-scorecard](../references/openssf-scorecard/), Code-Review · direct

> Perform peer review of code, and review any existing code review, analysis, or testing results as part of the peer review.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218 PW.7.2 Ex.1, p.23 · direct

## rev.small_changes: Changes are small enough to review.

**Accepted when.** A typical change touches at most {max_files} files.

**How we check.** The median number of files changed by the last 100 commits of the main line (a merge counts against its first parent, so one merged pull request is one change).

- **Met:** The median is {max_files} files or fewer.
- **Partially met:** Up to about {max_files*2.43} files.
- **Not met:** More.
- **Not applicable:** Fewer than 10 commits.

**What the check cannot see.** Files, not lines: a one-line change in many files counts as large, a rewrite of one huge file as small. Generated files and lockfiles count.

**Why we expect it.**

> Teams should consider how they will ensure that all contributions are small, logical changes instead of one giant, hard-to-review code dump.
>
> — [dora-2025-ai-capabilities-model](../references/dora-2025-ai-capabilities-model/), p. 41 · direct

> Each change, whether made by a human or an AI, should be committed as a distinct, atomic unit.
>
> — [dora-2025-ai-capabilities-model](../references/dora-2025-ai-capabilities-model/), p. 39 · direct

## rev.ai_policy: The rules for using AI in this project are written down.

**Accepted when.** An AI usage policy exists, as its own file or as a section of CONTRIBUTING, the README or the agent instructions.

**How we check.** A file named like `AI_POLICY.md`, `AI_USAGE.md` or `docs/ai-policy.md`, or a heading in CONTRIBUTING, the README or an agent instruction file that names AI, LLMs, Copilot, coding agents or generated code.

- **Met:** Such a file or section exists.
- **Not met:** None.

**What the check cannot see.** What the policy says, or whether anyone follows it. A heading such as "AI agents" in an instruction file counts, even if it only lists commands.

**Why we expect it.**

> These new survey findings affirm our recommendation to invest in making an organization’s stance on AI-assisted development clear and communicated to its software developers
>
> — [dora-2025-state-of-ai-assisted-development](../references/dora-2025-state-of-ai-assisted-development/), p. 53 · direct

> This framework should be published as a “living document” in a central, easily searchable hub, such as an internal developer portal or wiki.
>
> — [dora-2025-ai-capabilities-model](../references/dora-2025-ai-capabilities-model/), p. 19 · supporting

## sec.codeowners: CODEOWNERS assigns reviewers for sensitive paths.

**Accepted when.** A `CODEOWNERS` file assigns reviewers.

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

## hyg.templates: PR and issue templates guide contributors.

**Accepted when.** Pull request and issue templates exist.

**How we check.** Files at `.github/pull_request_template.md`, `.github/PULL_REQUEST_TEMPLATE*` (including that folder), `.github/ISSUE_TEMPLATE/*` (including `config.yml`) and `docs/pull_request_template.md`. Score = min(1, count / 2).

- **Met:** 2 or more matching files.
- **Partially met:** Exactly 1.
- **Not met:** None.

**What the check cannot see.** A root-level `pull_request_template.md` (supported by GitHub) is missed, and so are org-wide templates from a `.github` repository. Template content is not checked.

**Known flaw.** The checklist says "PR and issue templates", but two issue-template files (or one plus `config.yml`) meet it with no PR template.

**Our convention.** PR and issue templates turn the review checklist into a habit; a nice-to-have sign of maturity.

## rev.ai_attribution: Commits made with AI agents say so.

**Accepted when.** Recent commits name the AI agent that helped write them.

**How we check.** The messages of the last 200 commits are searched for a `Co-authored-by:` trailer or a "Generated with / by" line that names an agent (Claude, Copilot, Codex, Cursor, Gemini, Aider, Devin, Jules and the like).

- **Met:** At least one such commit.
- **Not met:** None, although the repository has agent instruction files.
- **Not applicable:** No agent instruction files and no attributed commits: there is no sign that agents are used.

**What the check cannot see.** Agents used without attribution, which is exactly what it asks about. It does not check that every agent-written commit is attributed.

**Our convention.** Reviewers judge a change better when they know an agent wrote it; the sources ask to train reviewers on generated code, which presumes they can tell.

**Why we expect it.**

> Train reviewers on the failure modes of generated code, and tune review checklists accordingly.
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 44 · supporting
