# Changelog

## Unreleased

- **Hand a finding to a coding agent** (`python sdlc.py handoff <run> [--list | --check <id>]`, and **Copy prompt
  for an agent** under What to do in the app): a prompt built from the run alone with Expected, Found and What to do,
  for the agent working in the assessed repository. It checks the finding against the code first, makes one change in one
  commit and names the scan that re-checks it. Broken or behind skills come first. A skill broken by failing
  calls now says so in What to do (it said "files that are gone").
- **Three wrong verdicts fixed on Azure DevOps projects** (found on fly2-integration-tests and its neighbours):
  `rev.via_pr` now counts Azure's `Merged PR 123:` merges (control-center-backend: 88 of 100, was 0);
  `test.framework` accepts `unittest.TestCase` suites; an Azure pipeline under any name
  (`azure-pipelines-flight-smoke.yml`) counts as another CI and is read for test and security steps.
- **One remote: GitHub.** GitLab is no longer used for SDLC360 itself: `.gitlab-ci.yml` is gone (`.github/workflows`
  runs the same gates), AGENTS.md and `.env.example` name `origin` (github.com/dryabokon/sdlc360) only. Assessing
  repositories on GitLab is unchanged.
- **Skill verdicts are kept in `report.json`** (they were `null`), and plain notes `.agents/skills/<name>.md` are judged
  like skills: reading one in a Claude Code session is a use.
- **Claude Code efficiency in five areas**: Gather context, Take action, Verify work, Commit and Capture, each with the
  practice from Anthropic's Claude Code best practices and what is in place. The checks and the score are unchanged;
  related checks of other aspects are linked for reference and scored where they are.
- **Fixed: a refreshed repository was assessed at an old branch.** `git fetch origin` + `checkout FETCH_HEAD` on a
  detached cached clone took the first branch by name, not the default one (rich was assessed at a 2022 release
  branch, httpx and smolagents at 2025 ones). A refresh now fetches the remote's default branch (`refresh_clone`).
- **Seven wrong verdicts fixed**, found by a blind review of a client data-migration repository against its code:
  a link into a dot folder (`.cursor/mcp.json`) counted as broken (`doc.links`, `sk.links`, `ai.instructions_fresh`);
  a generated `design.md` deep in the tree counted as the architecture document (`arch.doc`, `arch.fresh`); the word
  "build" in a sentence counted as a build command (`ai.instructions_quality`); agent hooks that only count tokens
  counted as guardrails (`ai.guardrails`); a linter skill's own `ruff.toml` counted as the project's linter
  (`hyg.lint`, `hyg.format`); integration tests named by what they check (`post_build/`, `reconcile.py`) were not
  seen (`test.layers`); a package's `docs/` folder was not counted (`doc.docs_dir`). Regression tests in
  `tests/unit/test_heuristics.py`; on the reference set only pydantic-ai changed (two link checks now Met).
- **Fixed** `ai.instructions`: `.claude/CLAUDE.md` is a root instruction file (Claude Code reads it as the project file);
  it was Partially met and its quality and freshness were not judged.
- **What to do, the same for every check.** Every check names its habit in plain words (`**The habit.**` in the
  acceptance criteria, `HABITS` for Claude Code efficiency); What to do starts with it, in plain text, and a met check ends
  with a green "✓ Done". An open one gives the step for this project with how many are left and of what (the missing
  sections, files and links named) and up to five items. A check that needs another first says so and links it (CI before its stages, the
  instruction file before its quality). Nine checks that had no step now have one.
- **GitLab projects** get GitLab steps (merge requests, `.gitlab-ci.yml`, Renovate, `.gitlab/` templates, CODEOWNERS
  approval), from the repository URL or the remotes of a working copy. `.gitlab-ci.yml` is read for test and security
  steps and GitLab's SAST / Secret Detection templates count. The GitHub Actions checks are Not applicable when another
  CI runs instead of failing (they cannot read it yet), and GitLab merge request and issue templates count.
- **Fixed** `ai.scoped_context`: Claude Code rules in `.claude/rules/` with a `paths:` filter, the way its acceptance
  text quotes, now count as scoped context; a rule without `paths:` loads always and does not.
- **Where the money went**, as three checks first in the Claude Code efficiency aspect (`agent.cost_in_work`,
  `agent.cost_reread`, `agent.cost_no_commit`): the cost at API prices split three ways, each dollar once (work in
  commits, re-reading long conversations, sessions without a commit), each with Expected, Found and What to do; the
  biggest loss is also in the aspect's head line. Timeline totals. Computed in `agent_usage.money`.

- **GitLab CI** with the gates of `ci.yml`.
- **Hosted** on Cloud Run behind Google sign-in (`deploy/gcp/site.sh`, `docs/deploy-gcp.md`): repository URLs
  only, GitHub and the hosts in `SDLC360_GIT_HOSTS`; assessments shared in a Cloud Storage bucket. `site.sh seed` fills
  the project list with the reference set and `SDLC360_SEED`.
- The header reads just "SDLC 360°: AI-readiness of a project repo".
- **Claude Code efficiency for any repository assessed by URL**, hosted too: pick the project's folder under
  `.claude/projects` in the browser; it sends only numbers (no prompts, no code). Seeded examples show it with
  their authors' sessions (`site.sh sessions`, `python sdlc.py attach-sessions`).

- **Agent use** tab (prototype) for local projects, laid out like an aspect: seven rules about how the coding agent
  works (attributed, sessions end in a commit, small commits, tests, little friction, lean context, skills used),
  judged from Claude Code session logs and git history; Found names the real sessions and commits.
- The app receives Claude Code telemetry (OTLP/JSON on `/v1/metrics`, `/v1/logs`) into `.cache/telemetry/`.

- **Calibration** in the Overview of the **Criteria** page (or `python sdlc.py calibrate`): the reference set
  with the reason each repository is in it, your own repositories added to it, and **Run calibration**. A calibration
  assesses each repository at its latest commit with the Standard criteria and saves a snapshot of every verdict in
  `runs/calibrations/<id>.json`. The result says what was assessed, by which scanner commit, what was recorded, how
  each check split across the set, and which verdicts changed since the previous calibration: on the same commit (the
  scanner changed them) or on a newer one (the project did).
- The calibration result is one matrix: every check on every reference repository, with overall and per-aspect scores
  on top. The **Criteria** page shows for each capability how it did on the reference set (column **Ref. set** and a
  block in the details), so you can decide whether to keep, relax or switch it off. A rule in the matrix opens it in
  its aspect.
- The **Projects** button is gone: the project name in the second row is the selector.
- Reference repositories are pinned to commits (`assessment/calibration/pins.json`): calibrations differ only where
  the rules changed. **Move to latest commits** / `calibrate --latest` moves the pins on purpose.
- Calibration runs are no longer listed under the projects; they open from the matrix.
- The Criteria page shows **Ref. set** as `met/assessed`, marked `*` when the profile's numbers differ from the
  standard ones the calibration used. The text under a rule states facts and does not advise switching a rare rule off.
- **Apply to open run** and **Delete** moved to the profile bar.

- New header: a black brand bar with the SDLC 360° mark, **Projects** and **Criteria** buttons and the theme switch
  on the right; below it, the open project with its source, commit, date and criteria. The Assessment / Capabilities
  tabs are gone: the assessment is the main view, and the settings are the **Criteria** page (`#criteria`;
  `#capabilities` still works).

- **Nine aspects of equal weight**: Docs & Architecture (merged), AI Harness, Skills, **Code Review** (new), Tests,
  Code Quality, CI/CD (now with one-command setup and pinned toolchains), Security & Secrets (now with the lockfile),
  LLM Usage & Cost. Architecture and Reproducibility are no longer aspects of their own.
- A check's aspect is its section in `assessment/capabilities.md`, not the module of its rule; older runs are
  regrouped the same way when opened.
- New checks: changes reach main through pull requests, changes are small (median files per change), an AI usage
  policy is written down, agent-written commits are attributed. CODEOWNERS and PR templates moved to Code Review.
- Removed: cloud cost controls, CI-minute cost (a duplicate of CI speed), provenance of results and seeded randomness
  (ML-specific; candidates for an ML profile).

- A capability's details are shorter: **How we check** (with "Not seen:" for blind spots and known flaws) and
  **Why it matters**. "Partially met" is explained in the verdict, only when it applies.
- A quote links to our own reference card (publisher, date, licence, retrieval date, the copy we keep and its
  SHA-256, key points) instead of the publisher's page, which may move. Reports embed the cards they cite.
- The overview shows the radar and the aspect scores only ("Where to start" and "What is going well" are gone).
- An open capability reads as three rows, **Expected**, **Found** and **What to do**, styled like the folded details. Criticality, status and
  percentage are shown only in the list on the left. **Accepted when** moved into the folded details. The detail
  panel is wider.
- Older runs list their aspects in the current order and under the current names, like the Criteria page. Their
  "Runs & Reproducibility" aspect (before 0.4) is shown as today's Reproducibility, its `run.*` checks as `rep.*`.
- `start.sh` / `stop.sh` work from WSL when the server runs on the Windows interpreter, and print the address at once.

## 0.5.0 (2026-11-06)

- Two tabs: **Assessment** and **Capabilities**, with the same layout. Recommendations, Dynamics and How it works are
  gone for now.
- Recommendations live in the Assessment: the overview says where to start and what is going well; an open
  capability shows what to do right in its row and its card, a met one gets a short acknowledgement.
- Every capability has one plain **Accepted when** sentence; its numbers are the thresholds and are edited inline in
  the Capabilities tab. The technical details are folded away.
- Thresholds now are the acceptance numbers themselves (`min_words` 340 instead of a "target" of 400), so the
  sentence and the verdict agree exactly.
- Scans from the app and `scan` without `--history` no longer re-score past commits.
- Open runs are re-judged in memory when loaded, so they show the current texts.

## 0.4.0 (2026-11-06)

- **Capabilities** instead of "expectations": the catalog is `assessment/capabilities.md`.
- **Profiles**, edited in the new **Capabilities** tab: switch capabilities off, change priorities, set thresholds,
  add your own capabilities with "met when" in plain words. Saved as `assessment/profiles/<name>.json`; *Standard* is
  the read-only baseline, *Prototype* a relaxed example. **Apply to this run** re-judges the open run at once.
- Thresholds of twelve rules (README length, docs pages, docstring share, test files, test ratio, file size, root
  files, diagrams, decision records, freshness of docs and architecture, size for boundary tooling) are parameters.
  The acceptance texts quote the numbers in force. A changed threshold is flagged until the project is re-assessed.
- `scan --profile`, `render --profile`; the manifest records the profile and the `reproduce` command includes it.
- `review.json` uses the key `capabilities` (`expectations` is still read).

## 0.3.0 (2026-11-06)

- Everything a person edits is in one folder, `assessment/`, with a guide: `expectations.md` (was
  `checklists/default.md`), `acceptance-criteria/` with one file per aspect (was one 790-line
  `checklists/acceptance.md`) and `references/` (was `docs/sources/`).
- Acceptance criteria are easier to read and edit: plain paragraphs and bullets, quotes as markdown quotes, and
  references named by their folder (`nist-ssdf`) instead of `S09`. A test keeps headings equal to the expectations.
- Fewer files in the root: `CONTRIBUTING.md` and `SECURITY.md` moved to `.github/`, `CLAUDE.md` to `.claude/`,
  the changelog to `docs/changelog.md`. `docs/adr/` became `docs/design-decisions/`, `docs/review.md` became
  `docs/reviewer-verdicts.md`.
- `doc.standard_files` also accepts a changelog in `docs/`.
- CI now runs on changes to `assessment/*.md` (they were skipped as documentation).

## 0.2.0 (2026-11-06)

- Every expectation is justified: `checklists/acceptance.md` says how it is judged (met / partially / not met,
  limits, known gaps) and quotes published guidance verbatim, or says it is our convention. 13 sources in
  `docs/sources/` with licences, dates and checksums.
- Runs & Reproducibility became **Reproducibility**: no expectation about a `runs/` folder any more; lockfiles,
  pinned toolchains, entry points, documented reproduction, provenance and seeds instead. pydantic-ai: 86.9 → 91.1.
- Aspects ordered as a project is built: architecture, docs, harness, skills, hygiene, tests, security,
  reproducibility, CI/CD, cost.
- New top-level tab **How it works**: components, the user journey, where to change what, scoring rules, sources.
- The detail panel shows "Partially met when", "Limits", "Known gap" and "Basis".
- README rewritten for readers who are not engineers; technical reference moved to `docs/usage.md`.
- Fixes: one workflow satisfies `ci.present`; every YAML form of the `pull_request` trigger counts;
  `CLAUDE.local.md` no longer counts as project instructions.

## 0.1.0 (2026-11-06)

- Ten-aspect scanner with a markdown checklist of expectations, three priorities and a critical gate.
- Run folders with manifest, report, HTML dashboard and log. `render` re-applies the checklist and review without re-scanning.
- Web app (`start.sh` / `stop.sh`): project picker, folder picker, scan jobs, Assessment / Recommendations / Dynamics.
- Dynamics: weekly velocity and re-scored past commits.
- Local server accepts only local `Host` / `Origin`. A failed scan leaves a `status: failed` manifest.
- Tests (unit + integration on real fixture repos), CI on Linux and Windows, pre-commit, design decision records.
