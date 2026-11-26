# SDLC360

**Assess your AI-agent readiness.**

- **360° feedback** on docs and architecture, AI harness, skills, code review, tests, code quality, CI/CD,
  security and secrets, LLM usage and cost.
- **Recommendations.** For every gap: what was expected, what was found and the next step to fix it.
- **Agent efficiency over time.** The cost (tokens, $) and time (minutes) of a typical change by Claude Code,
  commit by commit, adjusted for change size: see if your project gets easier or harder for the agent.

## How it works

Rules are taken from industry guides, tested on top open-source projects, and then run on your repository.

![Rules come from industry guides and are tested on top open-source projects; the rules of nine aspects check your repository; for every gap: expected, found, what to do](docs/images/how-it-works.svg)

### Theory

- **Anthropic:** Claude Code best practices, context engineering for AI agents
- **OpenAI:** harness engineering, AGENTS.md
- **Google / DORA:** the new SDLC with AI agents, State of AI-assisted Software Development 2025
- **Security:** NIST SSDF for generative AI, OWASP Top 10 for Agentic Applications, OpenSSF Scorecard

### Practice

- **Agent frameworks and SDKs:** Pydantic AI, OpenAI Agents SDK, MCP Python SDK, Claude Agent SDK, smolagents
- **Mature libraries:** httpx, Rich, Typer, Full Stack FastAPI Template

If a strong project fails a rule, we fix the rule.

## 360-degree view of your project

The score in docs and architecture, AI harness, skills, code review, tests, code quality, CI/CD, security and
secrets, LLM usage and cost.

![Overview: a maturity radar and the score of each area](docs/images/overview.png)

## Your AI agent over time

Where the money goes: into the changes, into re-reading long conversations, into sessions that end without a commit.
On one of our own projects, more than half of the cost went on re-reading: every step of a long session sends the whole
conversation again. One task per session fixes it.

![Claude Code efficiency: 51 of 87 dollars went on re-reading long conversations, with the sessions and what to do](docs/images/agent-cost.png)

Cost and time of a typical change, commit by commit. 100 is where you started; above 100, changes cost more.

![Timeline: the cost and time of a typical change, commit by commit](docs/images/timeline.png)

## Check your own project

Run it locally (Python 3.12+ and git, nothing to install). It is read-only and sends nothing.

```
git clone https://github.com/dryabokon/SDLC360.git sdlc360
cd sdlc360
python sdlc.py serve --open
```

Then **Open a project → Browse…** → your working copy → **Assess** → tab **Claude Code efficiency**. It counts your
commits only (`SDLC360_AUTHOR=all` counts everyone's) and the sessions Claude Code still keeps, about 30 days
(`"cleanupPeriodDays": 90` in `~/.claude/settings.json` keeps more).


