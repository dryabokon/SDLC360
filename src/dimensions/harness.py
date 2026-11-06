"""AI harness: is the repo set up for agentic, AI-assisted development (Claude Code, Codex, Copilot, Cursor…)?"""

from __future__ import annotations

import json
import re

from ..model import Checks, Dimension, short
from ..repo import Repo
from ._util import broken_refs, freshness_score, headings, instruction_files


def assess(repo: Repo):
    c = Checks()
    inst = instruction_files(repo)
    shared = [f for f in inst if not f.endswith("CLAUDE.local.md")]  # personal file: does not count as project instructions
    root_inst = [f for f in shared if "/" not in f or f.startswith(".github/")]
    c.add(
        "ai.instructions",
        "Agent instruction file (CLAUDE.md / AGENTS.md / copilot-instructions)",
        4,
        1.0 if root_inst else (0.5 if shared else 0.0),
        short(inst) if inst else "none found",
        "Add a root CLAUDE.md (or AGENTS.md, symlinked/imported by CLAUDE.md) describing build/test commands, "
        "layout, conventions and do/don't rules for agents.",
    )

    main = next(
        (f for f in ("CLAUDE.md", "AGENTS.md", ".github/copilot-instructions.md") if f in repo.files or repo.exists(f)),
        root_inst[0] if root_inst else None,
    )
    main = repo.resolve_link(main) if main else None  # CLAUDE.md -> AGENTS.md symlinks: judge the real file
    if main:
        text = repo.read(main)
        # follow Claude Code `@path` imports (e.g. a one-line CLAUDE.md containing `@AGENTS.md`)
        imports = [i for i in re.findall(r"(?m)^\s*@([\w./-]+\.md)\s*$", text)[:5] if i in repo.files]
        thin_wrapper = len(text.splitlines()) <= 3 and imports
        text += "".join("\n" + repo.read(i) for i in imports)
        if thin_wrapper:
            main = imports[0]  # judge freshness / references on the file that holds the content
        lines = len(text.splitlines())
        hs = " ".join(headings(text)) + " " + text.lower()[:20000]
        topics = {
            "commands": r"\b(build|run|install|make|npm|uv|pip|cargo|go run|dotnet|gradle)\b",
            "testing": r"\btest",
            "architecture/layout": r"architect|structure|layout|directory|modules?",
            "conventions": r"convention|style|guideline|rule|must|never|always",
        }
        hit = [k for k, p in topics.items() if re.search(p, hs)]
        size_ok = 1.0 if 25 <= lines <= 400 else (0.6 if 8 <= lines <= 800 else 0.3)
        c.add(
            "ai.instructions_quality",
            f"Instruction file is actionable ({main})",
            3,
            0.7 * len(hit) / len(topics) + 0.3 * size_ok,
            [f"{lines} lines", f"covers: {', '.join(hit) or 'none'}", f"missing: {', '.join(k for k in topics if k not in hit) or '-'}"],
            "Keep it 25–400 lines: exact build/test/lint commands, repo map, conventions, and gotchas. "
            "Move long reference material into linked docs or skills.",
        )

        n, broken = broken_refs(repo, main)
        code_time = repo.last_modified(repo.source_files[:2000])
        fs, fmsg = freshness_score(repo.last_modified([main]), code_time)
        ref_score = 1.0 if n == 0 else 1 - len(broken) / n
        c.add(
            "ai.instructions_fresh",
            "Instruction file is up to date with the code",
            2.5,
            0.6 * ref_score + 0.4 * fs,
            [f"{n - len(broken)}/{n} referenced paths exist" + (f"; broken: {short(broken)}" if broken else ""), fmsg],
            "Fix stale paths and refresh the file whenever structure or commands change (e.g. a CI step or hook that validates referenced paths).",
        )
    else:
        c.add("ai.instructions_quality", "Instruction file is actionable", 3, 0.0, "no instruction file")
        c.add("ai.instructions_fresh", "Instruction file is up to date with the code", 2.5, 0.0, "no instruction file")

    settings = repo.find(".claude/settings.json")
    perm = hooks = False
    if settings:
        try:
            data = json.loads(repo.read(settings[0]))
            perm = bool(data.get("permissions"))
            hooks = bool(data.get("hooks"))
        except (ValueError, AttributeError):
            pass
    c.add(
        "ai.settings",
        "Shared agent settings with permission policy (.claude/settings.json)",
        2,
        (0.5 + 0.5 * perm) if settings else 0.0,
        [f"settings: {short(settings)}", f"permissions defined: {perm}"] if settings else "no shared settings",
        "Commit .claude/settings.json with allow/deny permission rules (e.g. deny reading .env, allow test commands).",
    )

    hook_files = repo.find(".claude/hooks/*", ".husky/*", ".pre-commit-config.yaml", "lefthook.yml")
    c.add(
        "ai.guardrails",
        "Automated guardrails (agent hooks / pre-commit)",
        2,
        1.0 if hooks else (0.6 if hook_files else 0.0),
        [f"agent hooks in settings: {hooks}", f"hook files: {short(hook_files)}"],
        "Add hooks that run formatters/linters/tests after edits and block writes to secrets, "
        "so the harness enforces quality instead of relying on the prompt.",
    )

    ext = repo.find(
        ".claude/agents/*.md",
        ".claude/commands/*.md",
        ".claude/skills/*",
        ".github/prompts/*.md",
        ".github/chatmodes/*",
        ".github/instructions/*",
        ".cursor/rules/*",
        ".codex/*",
        ".claude-plugin/*",
        ".agents/skills/*",
        ".agents/agents/*",
        ".github/agents/*",
    )
    c.add(
        "ai.extensions",
        "Reusable agent workflows (skills / subagents / commands / prompts)",
        2,
        min(1.0, len(ext) / 3),
        short(ext),
        "Capture repeated workflows (review, release, debugging) as skills or subagents.",
    )

    mcp = repo.find(".mcp.json", ".vscode/mcp.json", ".cursor/mcp.json")
    c.add(
        "ai.mcp",
        "Project MCP servers declared (.mcp.json)",
        0.5,
        bool(mcp),
        short(mcp),
        "If the project relies on external tools (DB, issue tracker, docs), declare them in .mcp.json.",
    )

    local_leak = [f for f in repo.files if re.search(r"(^|/)(\.claude/settings\.local\.json|CLAUDE\.local\.md)$", f)]
    c.add(
        "ai.no_local_leak",
        "Personal agent config not committed (settings.local.json)",
        1,
        not local_leak,
        short(local_leak) if local_leak else "ok",
        "Remove personal settings from git and add them to .gitignore.",
    )

    ai_ci = re.findall(r"anthropics/claude-code-action|claude-code-base-action|openai/codex-action|coderabbit|copilot", repo.workflow_text, re.I)
    c.add(
        "ai.ci_agents",
        "AI agents wired into CI (review / triage)",
        1,
        bool(ai_ci),
        f"found: {', '.join(sorted(set(a.lower() for a in ai_ci)))}" if ai_ci else "none",
        "Optionally add anthropics/claude-code-action for PR review or @claude mentions.",
    )

    nested = [f for f in inst if "/" in f and not f.startswith((".github/", ".cursor/"))]
    big = len(repo.source_files) > 300
    c.add(
        "ai.scoped_context",
        "Scoped context for large codebases (nested CLAUDE.md / AGENTS.md)",
        1,
        (1.0 if nested else 0.3) if big else None,
        short(nested) if nested else ("none" if big else "small repo"),
        "Add per-package CLAUDE.md files so agents load only the context relevant to the subtree.",
    )
    return c.items


DIMENSION = Dimension("harness", "AI Harness", "Agent instructions, settings, hooks, MCP and CI agents for modern AI-assisted development.", assess)
