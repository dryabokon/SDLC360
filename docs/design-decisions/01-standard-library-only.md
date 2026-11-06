# Decision 1: Standard library only at runtime

Date: 2026-11-06 · Status: accepted

## Context

SDLC360 scans arbitrary repositories on developer laptops (Windows and Linux) and in CI. Installing it should be
trivial and should not conflict with the scanned project's environment.

## Decision

The runtime uses only the Python 3.12 standard library: `subprocess` + git for repository access,
`http.server` for the web app, and a single self-contained HTML template with inline SVG charts. Development tools
(pytest, ruff, mypy, pre-commit) are pinned in `requirements-dev.txt` and are never imported by `src/`.

## Consequences

- `python sdlc.py ...` works on any machine with Python and git. No install step is needed.
- YAML, TOML and markdown are parsed with regular expressions and small helpers, which is less robust than real
  parsers. Each such heuristic needs a test.
- The UI has no framework. `template.html` must stay disciplined (render only, no scoring).
