"""Cost management: LLM spend, cloud infrastructure spend, CI minutes."""

from __future__ import annotations

import re

from ..model import Checks, Dimension, short
from ..repo import Repo

_PKGS = r"anthropic|openai|langchain[\w-]*|llama[_-]index|litellm|google[.-]genai|google[.-]generativeai|mistralai|cohere|groq|ollama|claude[_-]agent[_-]sdk"
# Actual SDK usage only: imports in code, or a declared dependency - not the bare word in a comment or path.
LLM_IMPORT = re.compile(
    rf"^\s*(?:import|from)\s+({_PKGS.replace('[.-]', '.').replace('[_-]', '_')})\b"
    r"|(?:require\(|from\s+)['\"](openai|@anthropic-ai/[\w-]+|ai|@ai-sdk/[\w-]+|langchain[\w/-]*)['\"]",
    re.M | re.I,
)
LLM_DEP = re.compile(rf"^\s*['\"]?({_PKGS}|@anthropic-ai/[\w-]+|@ai-sdk/[\w-]+)['\"]?\s*(?:[=<>~!:;,\[\]]|$)", re.M | re.I)


def assess(repo: Repo):
    c = Checks()
    src = [f for f in repo.source_files[:4000] if not f.startswith((".github/", "scripts/", "examples/"))]
    deps = repo.find("requirements*.txt", "pyproject.toml", "package.json", "go.mod", "Cargo.toml", "*.csproj")
    llm = repo.grep(LLM_IMPORT, files=src, max_hits=3) + repo.grep(LLM_DEP, files=deps, max_hits=3)
    llm_files = sorted({h[0] for h in llm})

    if llm:
        usage = repo.grep(
            r"usage\.(input_tokens|output_tokens|prompt_tokens|completion_tokens|total_tokens)|\b(cost_usd|total_cost|token_count|count_tokens|track_cost|cost_tracker|get_openai_callback|langfuse|helicone|langsmith|openlit)\b",
            files=src,
            max_hits=5,
        )
        c.add(
            "cost.llm_tracking",
            "LLM token usage / cost is tracked",
            3,
            min(1.0, len(usage) / 2),
            [f"LLM SDK used in: {short(llm_files, 3)}"] + [f"{h[0]}:{h[1]}" for h in usage[:3]]
            if usage
            else [f"LLM SDK used in: {short(llm_files, 3)}", "no usage/cost accounting found"],
            "Log `usage.input_tokens/output_tokens` per call, convert to $ with a price table, and persist per run.",
        )
        limits = repo.grep(
            r"\b(max_tokens|max_output_tokens|max_completion_tokens|budget|max_cost|spend_limit|rate_limit|max_retries)\b", files=src, max_hits=5
        )
        c.add(
            "cost.llm_limits",
            "LLM calls bounded (max_tokens, budgets, retries)",
            2,
            min(1.0, len(limits) / 2),
            short([f"{h[0]}:{h[1]}" for h in limits], 3),
            "Set max_tokens on every call and a per-run budget that aborts when exceeded.",
        )
        caching = repo.grep(r"cache_control|prompt_cach|semantic_cache|lru_cache|@cache\b|diskcache|redis", files=src, max_hits=3)
        model_cfg = repo.grep(r"(MODEL|model_name|model_id|DEFAULT_MODEL)\s*[:=]", files=src, max_hits=3)
        c.add(
            "cost.llm_efficiency",
            "Cost efficiency (prompt caching, central model config)",
            1.5,
            0.5 * bool(caching) + 0.5 * bool(model_cfg),
            [f"caching: {short([h[0] for h in caching], 2)}", f"model config: {short([h[0] for h in model_cfg], 2)}"],
            "Use prompt caching for long stable prefixes and keep model choice in one config so cheaper tiers are one edit away.",
        )
    else:
        for cid, t, w in (
            ("cost.llm_tracking", "LLM token usage / cost is tracked", 3),
            ("cost.llm_limits", "LLM calls bounded (max_tokens, budgets, retries)", 2),
            ("cost.llm_efficiency", "Cost efficiency (prompt caching, central model config)", 1.5),
        ):
            c.add(cid, t, w, None, "no LLM SDK usage detected")

    iac = repo.find("*.tf", "*.bicep", "cdk.json", "Pulumi.yaml", "serverless.yml", "template.yaml", "*.cfn.yaml", "k8s/*", "helm/*", "charts/*")
    if iac:
        tf = "\n".join(repo.read(f) for f in iac[:200])
        infra = re.findall(
            r"infracost|aws_budgets_budget|azurerm_consumption_budget|google_billing_budget|cost[-_]?center|\btags\b|labels\s*[:=]|autoscal|spot|preemptible|resources:\s*\n\s*limits",
            tf + repo.workflow_text,
            re.I,
        )
        c.add(
            "cost.infra",
            "Cloud cost controls (budgets, tagging, infracost, limits)",
            2.5,
            min(1.0, len(set(i.lower() for i in infra)) / 3),
            [f"IaC files: {len(iac)}", f"signals: {', '.join(sorted(set(i.lower().strip() for i in infra))[:6]) or 'none'}"],
            "Tag resources with cost-center/owner, define budgets + alerts in IaC, and run infracost on PRs.",
        )
    else:
        c.add("cost.infra", "Cloud cost controls (budgets, tagging, infracost, limits)", 2.5, None, "no infrastructure-as-code")

    if repo.workflows and (llm or iac):  # CI minutes only matter once the project pays for resources
        txt = repo.workflow_text
        jobs = max(1, len(re.findall(r"^\s{2}[\w-]+:\s*\n\s{4}(runs-on|uses)", txt, re.M)))
        timeouts = len(re.findall(r"timeout-minutes", txt))
        cancel = bool(re.search(r"cancel-in-progress:\s*true", txt))
        paths = bool(re.search(r"^\s*paths(-ignore)?\s*:", txt, re.M))
        big = re.findall(r"runs-on:\s*\S*(large|xlarge|gpu|macos)", txt, re.I)
        s = 0.4 * min(1.0, timeouts / jobs) + 0.35 * cancel + 0.25 * paths
        c.add(
            "cost.ci",
            "CI minutes controlled (timeouts, cancel-in-progress, path filters)",
            1.5,
            s,
            [f"timeouts {timeouts}/{jobs} jobs", f"cancel-in-progress: {cancel}", f"path filters: {paths}"]
            + ([f"expensive runners: {len(big)}"] if big else []),
            "Cancel superseded runs, cap job time and skip CI for doc-only changes.",
        )
    else:
        c.add("cost.ci", "CI minutes controlled", 1.5, None, "no paid resources detected" if repo.workflows else "no workflows")

    docs = "\n".join(repo.read(f) for f in repo.find("README*", "docs/*.md", "CLAUDE.md", "COST*.md")[:30])
    documented = re.search(r"\b(cost|budget|pricing|spend|\$\d)", docs, re.I)
    applicable = bool(llm or iac)
    c.add(
        "cost.documented",
        "Expected costs / budgets documented",
        1,
        bool(documented) if applicable else None,
        "cost/budget discussed in docs" if documented else ("not documented" if applicable else "no paid-resource usage detected"),
        "Document expected per-run / monthly costs, budgets and who owns them.",
    )
    return c.items


DIMENSION = Dimension("cost", "Cost Management", "LLM token/cost tracking & limits, cloud budgets and tagging, CI-minute hygiene.", assess)
