# Calibration on reference repositories

Well-run open-source projects serve as a sanity check for the scanner rules. When a strong project fails a
check, either the project really lacks the practice or the rule is wrong. Each rule fix gets a regression test in
`tests/unit/test_heuristics.py`.

## Reference set

Scores below are from 2026-11-06 with the default checklist and history 6.

| Repository | Overall | Notes |
|---|---|---|
| pydantic/pydantic-ai | 86.9 (B) | highest; Runs gated (no `runs/`, our convention) |
| openai/openai-agents-python | 78.5 | |
| modelcontextprotocol/python-sdk | 76.7 | |
| anthropics/claude-agent-sdk-python | 64.8 | |
| fastapi/typer | 59.9 | library: no skills, no runs, cost N/A |
| huggingface/smolagents | 59.8 | |
| fastapi/full-stack-fastapi-template | 53.1 | commits a `.env` (template values), so it is correctly flagged |
| encode/httpx | 52.9 | mature library, but it lacks our AI-harness and runs conventions |
| Textualize/rich | 50.8 | same |

No repository is green on every aspect. `runs/`, skills and cost tracking are conventions of our team, and
libraries score lower by design (see `adr/0003-checklist-and-critical-gate.md`).

## False positives fixed during calibration

- A `CLAUDE.md` that is a git symlink to `AGENTS.md`, or a thin `@AGENTS.md` import, now counts as an instruction file.
- Tests run through `scripts/test`, `Makefile`, `noxfile`, `tox` or `package.json` scripts now count as tests in CI.
- `tests/fixtures/.netrc` and other fixtures no longer count as committed credentials.
- The word "anthropic" in a path no longer counts as LLM usage; only imports and dependency declarations do.
- Cost is N/A for projects without LLM or infrastructure-as-code resources.
- `.github/` scripts are no longer counted as product source.
- `*AGENTS.md` no longer matches `elevenlabs_agents.md`; only exact instruction-file names match.
- `.agents/skills` is recognised as a skills location.
- Identifiers such as `oauth_client_secret` are no longer taken for secret values.
- Absolute paths in docs (`/opt/...`) are no longer reported as broken links.
