---
name: git-hosting
description: Work with GitHub and GitLab from the terminal - pull/merge request status (reviews, approvals, CI checks, unresolved threads), why a CI run or pipeline failed (failed job and step, errors, the log up to the failure), issues, preparing a PR/MR, and git push/fetch with a token that never lands in the URL or .git/config. Read-only by default; creating a PR needs explicit confirmation; never merges, approves or force-pushes. Use when the user mentions GitHub, GitLab, a PR or MR, Actions, pipelines, CI, a github.com or gitlab link, or asks why CI failed or where their PR is stuck.
license: MIT
compatibility: Requires Python 3.9+ (standard library only) and git. GH_TOKEN / GITLAB_TOKEN for private repositories and for CI logs.
---

# GitHub and GitLab

One CLI, `scripts/githost.py`, same commands for both hosts (and the same shape as the azure-devops skill).
Commands are relative to this skill's folder (in Claude Code: `${CLAUDE_SKILL_DIR}`); run them from the user's
checkout - the repository and host come from its `git remote`, or from `--repo owner/name [--host github|gitlab]`,
or from a pasted URL.

```bash
python scripts/githost.py whoami                         # host, repo, user - run this first
python scripts/githost.py prs [--mine|--reviewing] [--state open|closed|merged|all]
python scripts/githost.py pr N|URL                       # reviews/approvals, CI checks, unresolved threads
python scripts/githost.py runs [--failed] [--branch B]   # Actions runs / pipelines
python scripts/githost.py run ID|URL|last-failed [--branch B] [--log-lines N]
python scripts/githost.py issues [--mine] [--state open|closed|all];  python scripts/githost.py issue N|URL
python scripts/githost.py pr-create --source B [--target B] --title T --body-file F [--draft] [--apply]
python scripts/githost.py git <git args>                 # e.g. git push -u origin my-branch
```

Every command takes `--json` (use it when you process the output), `--repo`, `--host`, `--remote`, `--timeout`.

## Configuration

`GH_TOKEN` (or `GITHUB_TOKEN`), `GITLAB_TOKEN`, `GITLAB_HOST` - environment or the nearest `.env` (see
`.env.example`). Public repositories read without tokens, except CI logs and review threads. If a command says a
token is needed, tell the user which variable and point to `.env.example`; never ask for the token in chat, never
print or commit it.

## Rules

1. **Read-only unless asked.** The writes are `pr-create --apply` and `git push`.
2. **PR / MR:** run `pr-create` without `--apply`, show title, branches and body, add `--apply` only after the user
   confirms. Look at 2-3 merged PRs first (`prs --state merged`) and follow the repo's conventions. If the dry run
   reports an open request for the same branches, link it instead of creating another.
3. **git:** commit on a branch, not on the default branch, unless the user says otherwise. Push with
   `githost.py git push -u origin <branch>` when plain `git push` has no credentials - the token goes as a
   per-command HTTP header. Force-push is refused by the script; never work around it without an explicit request.
4. **Never** merge, approve, close, comment or delete through this skill - there are no commands for it on purpose.

## Typical requests

- **"Where is my PR stuck?"** → `prs --mine`, then `pr N`. Report missing approvals, failing checks (follow up
  with `run <id>` for a failing one), unresolved threads grouped by file. Passing checks are only counted.
- **"Why did CI fail?"** → `run URL` or `run last-failed [--branch B]`. Jobs are ordered by when they failed: the
  first is usually the cause. Read the job's errors (annotations), then *error-looking lines from the whole log*,
  then the log tail, which ends at the failure. "No job ran" means the workflow could not start (invalid workflow
  file, or a run waiting for approval). Quote the decisive line, explain, propose the fix.
- **"What's assigned to me?"** → `issues --mine`; `issue N` for one.

## Examples

Run from this folder (`bash examples/<name>.sh`):
- `examples/status-tour.sh` - whoami, PRs, CI runs, issues of this repository.
- `examples/why-did-ci-fail.sh` - `run last-failed` on busy public projects (GitHub and GitLab).
- `examples/pr-and-git.sh` - one MR by URL, a PR dry run, git with the token header.

## Gotchas

- GitHub job logs and GitLab job traces need a token even for public projects; GitHub review threads need one
  too (GraphQL). Without a token you still get the failed job, step and annotations.
- GitLab "pipelines" are reported in the same shape as GitHub "runs"; a GitLab job's *stage* is shown as its step.
- Self-managed GitLab: the host comes from the git remote; set `GITLAB_HOST` only when there is no remote.
