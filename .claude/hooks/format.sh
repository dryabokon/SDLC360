#!/usr/bin/env bash
# PostToolUse hook: ruff-format and auto-fix the Python file Claude just edited. Never blocks the edit.
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
file="$(python -c 'import json,sys; print(json.load(sys.stdin).get("tool_input", {}).get("file_path", ""))' 2>/dev/null)"
[[ "$file" == *.py ]] || exit 0
for ruff in "$ROOT/.venv/Scripts/ruff.exe" "$ROOT/.venv/bin/ruff" ruff; do
    if command -v "$ruff" >/dev/null 2>&1; then
        "$ruff" format --quiet "$file" && "$ruff" check --fix --quiet "$file" >&2
        exit 0
    fi
done
exit 0
