# LLM Usage & Cost: how each capability is judged

Capabilities and their priorities are in [capabilities.md](../capabilities.md).
How to edit this file: [assessment/README.md](../README.md#acceptance-criteria).

## cost.llm_tracking: LLM token usage and cost are tracked per call / run.

**Accepted when.** The code records LLM token usage and cost.

**How we check.** LLM detection looks at source files (first 4000, excluding root `scripts/`, `examples/` and `.github/`). It looks for line-start Python imports of anthropic, openai, langchain*, llama_index, litellm, google genai/generativeai, mistralai, cohere, groq, ollama or claude_agent_sdk. It also looks for JS `require`/`from` of `openai`, `@anthropic-ai/*`, `ai`, `@ai-sdk/*` or `langchain*`, and for the same packages declared in requirements, `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml` or `*.csproj`. If found, it searches source lines for `usage.input_tokens/output_tokens/prompt_tokens/completion_tokens/total_tokens`, `cost_usd`, `total_cost`, `token_count`, `count_tokens`, `track_cost`, `cost_tracker`, `get_openai_callback`, `langfuse`, `helicone`, `langsmith` or `openlit`.

- **Met:** 2 or more matching lines (score = lines / 2).
- **Partially met:** Exactly 1 matching line.
- **Not met:** No matching line.
- **Not applicable:** No LLM SDK import or dependency is detected.

**What the check cannot see.** Comments count. Two lines in one file count as two places. The scanner never checks that usage is persisted per call or run. It misses other styles: `usage["input_tokens"]`, Gemini `usage_metadata`, and custom names. Go and Rust LLM clients (e.g. `go-openai`) are not detected as LLM usage.

**Why we expect it.**

> Observability: Logs, traces, evaluations, cost and latency metering. Without observability, there is no way to tell whether the agent is doing well or quietly drifting.
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 28 · direct

> When that happens, run `/usage` in the session to see where it went.
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Change a default · supporting

> The key is for the AI system or agents to be constantly updated with relevant context and constantly measured for accuracy, usefulness, and cost.
>
> — [dora-2025-state-of-ai-assisted-development](../references/dora-2025-state-of-ai-assisted-development/), p. 83 · supporting

## cost.llm_limits: LLM calls are bounded by max_tokens, budgets and retries.

**Accepted when.** LLM calls are bounded: maximum tokens, budgets and retry limits.

**How we check.** Only when an LLM SDK is detected (see `cost.llm_tracking`). Source lines are searched for the words `max_tokens`, `max_output_tokens`, `max_completion_tokens`, `budget`, `max_cost`, `spend_limit`, `rate_limit` or `max_retries`.

- **Met:** 2 or more matching lines.
- **Partially met:** Exactly 1 matching line.
- **Not met:** None.
- **Not applicable:** No LLM SDK detected.

**What the check cannot see.** The same keyword twice (e.g. `max_tokens` on two calls) meets it, so budgets or retries are not required. The word `budget` in any unrelated comment counts. The scanner never checks that every call is bounded. `budgets` (plural) and camelCase `maxTokens` do not match.

**Why we expect it.**

> What stops it? `--max-turns`, `--max-budget-usd`, a spend limit.
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Let Claude run without you · direct

> Adaptive Tool Budgeting. Apply usage ceilings (cost, rate, or token budgets) with automatic revocation or throttling when exceeded.
>
> — [owasp-agentic-top10-2026](../references/owasp-agentic-top10-2026/), ASI02 guideline 5, p.15 · direct

> This creates an expensive "prompting loop" that burns through API tokens with low first-pass success rates.
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 40 · supporting

## cost.llm_efficiency: Prompt caching and a central model config keep spend down.

**Accepted when.** Prompts are cached and models are configured in one place.

**How we check.** Only when an LLM SDK is detected. Source lines are searched for caching (`cache_control`, `prompt_cach`, `semantic_cache`, `lru_cache`, `@cache`, `diskcache`, `redis`) and for "model config": `MODEL`, `model_name`, `model_id` or `DEFAULT_MODEL` followed by `:` or `=`, case-insensitive.

- **Met:** Both a caching match and a model-config match (0.5 + 0.5).
- **Partially met:** Exactly one of the two (0.5).
- **Not met:** Neither.
- **Not applicable:** No LLM SDK detected.

**What the check cannot see.** Any `lru_cache` or `redis` use counts as prompt caching even if unrelated to LLM calls.

**Known flaw.** The model-config pattern has no word boundary. Any inline `model="gpt-4o"` keyword argument, `self.model =` or `data_model:` matches, so a hard-coded model in a call meets "central model config".

**Why we expect it.**

> routes deterministic, lower-complexity tasks (Test Generation, Code Review, and CI/CD monitoring) to smaller, faster, and significantly cheaper models.
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 42 · supporting

> Set `model: haiku` in a subagent’s definition if its work is simple
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Know what subagents cost · supporting

## cost.documented: Expected costs and budgets are documented.

**Accepted when.** Expected costs or budgets are written down.

**How we check.** Text of the first 30 files matching `README*`, `CLAUDE.md` or `COST*.md` anywhere, or any `docs/**.md`, searched case-insensitively for words starting with `cost`, `budget`, `pricing` or `spend`, or for a `$` followed by a digit.

- **Met:** Any match.
- **Partially met:** never
- **Not met:** No match while the check applies.
- **Not applicable:** No LLM SDK and no IaC detected.

**What the check cannot see.** Any incidental phrase ("at no cost", "low-cost", "spending time") meets it. The scanner never checks that expected costs, budgets or owners are actually stated.

**Known flaw.** Bug: `\b\$\d` needs a letter or digit before `$`, so "costs $5" matches only through the word "cost", and a bare "$20/month" is not detected.

**Our convention.** People can only keep to a budget that is written down next to the code that spends it.
