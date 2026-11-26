@../AGENTS.md

Claude Code specifics: skills in `skills/` (next to this file) load by description (`/scan-repo`, `/review-run`, `/calibrate-check`; `git-hosting` and `gcp` come from github.com/dryabokon/skills-for-agents, copied as they are).
A hook formats edited Python files with ruff (`hooks/format.sh`). Use the Chrome tools to look at UI changes
at http://127.0.0.1:8360/ after `./start.sh`.
