#!/usr/bin/env bash
# The latest failed CI run of a busy public project: failed job and step, its errors, the log up to the failure.
# Run from the skill folder:   cd skills/git-hosting && bash examples/why-did-ci-fail.sh
# GitHub serves job logs only with GH_TOKEN; without it you still get the failed job, step and annotations.
# Your own repository: run `python scripts/githost.py run last-failed` inside its checkout.
set -e

python scripts/githost.py run last-failed --repo cli/cli --log-lines 15
python scripts/githost.py run last-failed --repo gitlab-org/cli --host gitlab --log-lines 15
