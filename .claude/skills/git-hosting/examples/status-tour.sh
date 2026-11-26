#!/usr/bin/env bash
# A read-only tour of the repository you are in: who am I, open PRs, recent CI runs, open issues.
# Run from the skill folder:   cd skills/git-hosting && bash examples/status-tour.sh
# The repository comes from `git remote get-url origin` (here: this skills repository on GitHub).
set -e

python scripts/githost.py whoami
python scripts/githost.py prs --state all --top 5
python scripts/githost.py runs --top 5
python scripts/githost.py issues --top 5
