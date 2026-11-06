# Cost: how each capability is judged

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

## cost.infra: Cloud resources have budgets, tags and cost checks.

**Accepted when.** Cloud resources have budgets, cost tags and cost checks.

**How we check.** IaC files: `*.tf`, `*.bicep`, `cdk.json`, `Pulumi.yaml`, `serverless.yml`, `template.yaml`, `*.cfn.yaml` anywhere, or any file under root `k8s/`, `helm/` or `charts/`. In those files (first 200) plus all workflow YAML, it collects distinct matches of: `infracost`, `aws_budgets_budget`, `azurerm_consumption_budget`, `google_billing_budget`, cost-center/cost_center, `tags`, `labels:`/`labels =`, `autoscal`, `spot`, `preemptible`, `resources:` followed by `limits`.

- **Met:** 3 or more distinct signals (score = distinct / 3).
- **Partially met:** Exactly 2 distinct signals (0.67).
- **Not met:** 0 or 1 signal (1 gives 0.33, below 0.35).
- **Not applicable:** No IaC file exists.

**What the check cannot see.** Weak signals add up. Workflow `tags:` push triggers and near-universal k8s `labels:` count, and `spot` matches inside words like "hotspot". Any file named `template.yaml` counts as IaC. Budgets are never required.

**Known flaw.** Signals are deduplicated by the exact matched text (lower-cased, not trimmed). So `labels:` and `labels =`, or `cost-center` and `cost_center`, count as two signals.

**Our convention.** Cloud spend without budgets or tags cannot be attributed or capped; applies only when infrastructure is defined as code.

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

## cost.ci: CI minutes are controlled (timeouts, cancel-in-progress, path filters).

**Accepted when.** CI minutes are controlled: outdated runs are cancelled, unrelated changes skipped, jobs have timeouts.

**How we check.** Only when GitHub workflows exist and the project uses an LLM SDK or IaC. In all workflow text it counts `timeout-minutes` occurrences and jobs. A job counts if its key is indented 2 spaces and the next line, at 4 spaces, is `runs-on` or `uses`; at least 1 job is assumed. It also looks for `cancel-in-progress: true` and a `paths:`/`paths-ignore:` line. Score = 0.4 x min(1, timeouts/jobs) + 0.35 x cancel + 0.25 x paths.

- **Met:** `cancel-in-progress: true` AND a path filter AND timeouts on at least 62.5% of counted jobs.
- **Partially met:** Score 0.35 to 0.85. Examples: cancel-in-progress alone, or cancel + paths, or timeouts covering at least 87.5% of jobs alone, or path filter + at least 25% timeout coverage.
- **Not met:** Below 0.35, e.g. only path filters, or timeouts on fewer than 87.5% of jobs with nothing else.
- **Not applicable:** No workflows, or no LLM/IaC usage.

**What the check cannot see.** Step-level `timeout-minutes` also count, and jobs whose first key is `name:`/`needs:`/`if:` are not counted, so the ratio is easily inflated. `cancel-in-progress: ${{ … }}` is not recognised. Expensive runners are reported but not scored. Other CI systems are ignored.

**Our convention.** Timeouts, cancel-in-progress and path filters stop CI minutes from being burned by hung or superseded jobs.

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
