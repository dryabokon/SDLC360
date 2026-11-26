"""AI harness: is the repo set up for agentic, AI-assisted development (Claude Code, Codex, Copilot, Cursor…)?"""

from __future__ import annotations

import json
import re

from ..model import Checks, Dimension, short
from ..repo import Repo
from ._util import broken_refs, freshness_score, headings, instruction_files, on


def claude_rules(repo: Repo) -> list[str]:
    """Claude Code rule files: `.claude/rules/**/*.md`, at the root or in a package."""
    return [f for f in repo.files if re.search(r"(^|/)\.claude/rules/.+\.md$", f)]


def has_paths_filter(text: str) -> bool:
    """A rule with `paths:` in its frontmatter loads only for the files it names; without it, it loads always."""
    m = re.match(r"---[ \t]*\r?\n(.*?)\r?\n---", text, re.S)
    return bool(m and re.search(r"^paths[ \t]*:", m.group(1), re.M))


GUARD = re.compile(
    r"format|fmt|lint|ruff|black|prettier|eslint|biome|mypy|pyright|tsc\b|test|gitleaks|secret|guard|block|protect|deny|validat|pre-commit",
    re.I,
)
TOPIC_WORDS = {
    "commands": "the exact build, run and install commands",
    "testing": "how to run the tests",
    "architecture/layout": "a map of the folders",
    "conventions": "the rules: what to always and never do",
}


def assess(repo: Repo):
    c = Checks()
    inst = instruction_files(repo)
    shared = [f for f in inst if not f.endswith("CLAUDE.local.md")]  # personal file: does not count as project instructions
    root_inst = [f for f in shared if "/" not in f or f.startswith(".github/") or f == ".claude/CLAUDE.md"]  # Claude Code reads both
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
        (f for f in ("CLAUDE.md", ".claude/CLAUDE.md", "AGENTS.md", ".github/copilot-instructions.md") if f in repo.files or repo.exists(f)),
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
        code = " ".join(re.findall(r"`{1,3}[^`]+`{1,3}", text[:20000])).lower()  # inline code and code blocks
        topics = {
            "commands": r"`[^`]*\b(make|npm|npx|pnpm|yarn|uv|pip|python|pytest|cargo|go (run|test|build)|dotnet|gradlew?|mvn|just|tox|nox|ruff|docker|bash|\./)",
            "testing": r"\btest",
            "architecture/layout": r"architect|structure|layout|directory|modules?",
            "conventions": r"convention|style|guideline|rule|must|never|always",
        }
        hit = [k for k, p in topics.items() if re.search(p, code if k == "commands" else hs)]
        size_ok = 1.0 if 25 <= lines <= 400 else (0.6 if 8 <= lines <= 800 else 0.3)
        c.add(
            "ai.instructions_quality",
            f"Instruction file is actionable ({main})",
            3,
            0.7 * len(hit) / len(topics) + 0.3 * size_ok,
            [f"{lines} lines", f"covers: {', '.join(hit) or 'none'}", f"missing: {', '.join(k for k in topics if k not in hit) or '-'}"],
            " ".join(
                ([f"Add to {main}: " + "; ".join(TOPIC_WORDS[k] for k in topics if k not in hit) + "."] if len(hit) < len(topics) else [])
                + (
                    [f"It has {lines} lines: keep it between 25 and 400, and move long reference material into linked docs or skills."]
                    if size_ok < 1
                    else []
                )
            )
            or "Make the commands exact and copy-pasteable, and say what the agent must never do.",
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
            (
                f"Fix the {len(broken)} {'path' if len(broken) == 1 else 'paths'} in {main} that no longer exist (listed), "
                if broken
                else f"Re-read {main} against the code: "
            )
            + "and update it in the same change whenever the structure or the commands change.",
            todo=[f"{main}: {x}" for x in broken[:5]],
        )
    else:
        c.add("ai.instructions_quality", "Instruction file is actionable", 3, 0.0, "no instruction file")
        c.add("ai.instructions_fresh", "Instruction file is up to date with the code", 2.5, 0.0, "no instruction file")

    settings = repo.find(".claude/settings.json")
    perm = hooks = False
    hook_cmds: list[str] = []
    if settings:
        try:
            data = json.loads(repo.read(settings[0]))
            perm = bool(data.get("permissions"))
            hooks = bool(data.get("hooks"))
            hook_cmds = re.findall(r'"command"\s*:\s*"((?:[^"\\]|\\.)*)"', json.dumps(data.get("hooks") or {}))
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
    guard = [h for h in hook_cmds if GUARD.search(h)]  # a hook that only logs or counts tokens guards nothing
    c.add(
        "ai.guardrails",
        "Automated guardrails (agent hooks / pre-commit)",
        2,
        1.0 if guard else (0.6 if hook_files else (0.2 if hooks else 0.0)),
        [
            f"agent hooks in settings: {len(hook_cmds)}" + (f", checking or blocking: {len(guard)}" if hook_cmds else ""),
            f"hook files: {short(hook_files)}",
        ],
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
        on(
            repo,
            "Add anthropics/claude-code-action to a workflow, so Claude reviews every pull request and answers @claude.",
            "Add a merge request job to .gitlab-ci.yml that runs `claude -p` with your review prompt and posts the findings to the merge request.",
            "Add a pipeline that runs `claude -p` with your review prompt as a build validation of the main branch, and posts the "
            "findings to the pull request through the Azure DevOps REST API.",
        ),
    )

    nested = [f for f in inst if "/" in f and not f.startswith((".github/", ".cursor/"))]
    nested += [f for f in claude_rules(repo) if has_paths_filter(repo.read(f, 4000))]
    big = len(repo.source_files) > 300
    c.add(
        "ai.scoped_context",
        "Scoped context for large codebases (nested CLAUDE.md / AGENTS.md / .claude/rules with paths)",
        1,
        (1.0 if nested else 0.3) if big else None,
        short(nested) if nested else ("none" if big else "small repo"),
        "Add per-package CLAUDE.md files, or `.claude/rules/*.md` with a `paths:` filter, so agents load only the context "
        "relevant to the code they work on.",
    )
    return c.items


DIMENSION = Dimension("harness", "AI Harness", "Agent instructions, settings, hooks, MCP and CI agents for modern AI-assisted development.", assess)
