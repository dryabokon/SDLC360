# Calibration on reference repositories

Well-run open-source projects serve as a sanity check for the scanner rules. When a strong project fails a
check, either the project really lacks the practice or the rule is wrong. Each rule fix gets a regression test in
`tests/unit/test_heuristics.py`.

## Reference set

Scores below are from 2026-11-06 with the default checklist and history 6.

| Repository | Overall | Notes |
|---|---|---|
| pydantic/pydantic-ai | 86.9 (B) | highest; was gated on Runs for lacking `runs/` (removed since, see below) |
| openai/openai-agents-python | 78.5 | |
| modelcontextprotocol/python-sdk | 76.7 | |
| anthropics/claude-agent-sdk-python | 64.8 | |
| fastapi/typer | 59.9 | library: no skills, no runs, cost N/A |
| huggingface/smolagents | 59.8 | |
| fastapi/full-stack-fastapi-template | 53.1 | commits a `.env` (template values), so it is correctly flagged |
| encode/httpx | 52.9 | mature library, but it lacks our AI-harness and runs conventions |
| Textualize/rich | 50.8 | same |

No repository is green on every aspect. Skills and cost tracking matter mostly for agentic projects, so libraries
score lower there. The `runs/` folder expectation was removed from the default checklist on 2026-11-06: it is a
team convention, and reproducibility is now judged by lockfiles, pinned toolchains, entry points and provenance.

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

## False negatives found by scanning SDLC360 itself

- A flow-style tag trigger (`tags: ["v*"]`) is now recognised as a release trigger.
- Pinned `requirements-*.txt` variants (for example `requirements-dev.txt`) now count as a lockfile.
