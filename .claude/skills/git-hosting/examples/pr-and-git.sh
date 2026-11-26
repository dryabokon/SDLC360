#!/usr/bin/env bash
# Look at one PR / MR, prepare a PR without creating it, and use git with the token as a header.
# Run from the skill folder:   cd skills/git-hosting && bash examples/pr-and-git.sh
set -e

python scripts/githost.py pr "https://gitlab.com/gitlab-org/cli/-/merge_requests/4555"
python scripts/githost.py pr-create --source main --target main --title "Example" --body "Dry run: nothing is sent without --apply."
python scripts/githost.py git ls-remote origin HEAD
