"""Skills & agent markdown: are reusable agent capabilities captured as well-structured markdown files?"""

from __future__ import annotations

import re

from ..model import Checks, Dimension, short
from ..repo import Repo
from ._util import broken_refs, frontmatter


def assess(repo: Repo):
    c = Checks()
    skills = repo.find("SKILL.md")
    agents = repo.find(".claude/agents/*.md", "agents/*.md", ".github/agents/*.md")
    commands = repo.find(".claude/commands/*.md", ".github/prompts/*.prompt.md", "commands/*.md")
    rules = repo.find(".cursor/rules/*.mdc", ".github/instructions/*.instructions.md")
    total = len(skills) + len(agents) + len(commands) + len(rules)

    c.add(
        "sk.present",
        "Skills / subagents / commands exist as markdown",
        3,
        min(1.0, total / 3),
        [f"skills: {len(skills)}", f"subagents: {len(agents)}", f"commands/prompts: {len(commands)}", f"rules: {len(rules)}"],
        "Package recurring procedures as `.claude/skills/<name>/SKILL.md` (with frontmatter) and specialists as `.claude/agents/<name>.md`.",
    )

    if not total:
        for cid, title, w in (
            ("sk.frontmatter", "Valid frontmatter (name + description)", 3),
            ("sk.descriptions", "Descriptions say what AND when to use", 2),
            ("sk.size", "Concise bodies with progressive disclosure", 1.5),
            ("sk.links", "Internal references resolve", 1),
            ("sk.layout", "Consistent layout & naming", 1),
        ):
            c.add(cid, title, w, None, "no skill files")
        return c.items

    files = skills + agents + commands + rules
    fm_ok, desc_good, sizes, issues, vague = 0, 0, [], [], []
    for f in files:
        text = repo.read(f)
        fm = frontmatter(text) or {}
        need = ("name", "description") if f in skills or f in agents else ("description",)
        if all(fm.get(k) for k in need):
            fm_ok += 1
        else:
            issues.append(f"{f}: missing {', '.join(k for k in need if not fm.get(k))}")
        desc = fm.get("description", "")
        if 40 <= len(desc) <= 1024 and re.search(r"\b(use (when|this|for|to)|when\b|trigger|invoke)", desc, re.I):
            desc_good += 1
        else:
            vague.append(f)
        sizes.append((f, len(text.splitlines())))

    c.add(
        "sk.frontmatter",
        "Valid frontmatter (name + description)",
        3,
        fm_ok / len(files),
        [f"{fm_ok}/{len(files)} valid"] + issues[:5],
        f"Add frontmatter, `name` (kebab-case) and `description`, to the {len(files) - fm_ok} files that lack it, starting with the ones listed.",
        todo=issues[:5],
    )
    c.add(
        "sk.descriptions",
        "Descriptions say what AND when to use",
        2,
        desc_good / len(files),
        f"{desc_good}/{len(files)} descriptions are 40–1024 chars and contain a 'use when…' trigger",
        f"Rewrite the {len(files) - desc_good} descriptions that do not say when to use the skill: what it does, then 'Use when …', "
        "so the agent picks it at the right moment. Start with the ones listed.",
        todo=vague[:5],
    )

    big = [f"{f} ({n} lines)" for f, n in sizes if n > 500]
    c.add(
        "sk.size",
        "Concise bodies with progressive disclosure (<500 lines)",
        1.5,
        1 - len(big) / len(files),
        [f"oversized: {short(big)}"] if big else [f"all {len(files)} files under 500 lines"],
        f"Cut the {len(big)} files over 500 lines: move the detail into `references/` and the code into `scripts/`.",
        todo=big[:5],
    )

    n_refs, broken = 0, []
    for f in files:
        n, b = broken_refs(repo, f)
        n_refs += n
        broken += [f"{f} -> {x}" for x in b]
    c.add(
        "sk.links",
        "Internal references resolve",
        1,
        1.0 if not n_refs else 1 - len(broken) / n_refs,
        [f"{n_refs - len(broken)}/{n_refs} references ok"] + broken[:5],
        f"Fix or remove the {len(broken)} references to files that are gone, starting with the ones listed.",
        todo=broken[:5],
    )

    bad_names = [f for f in skills if not re.search(r"/[a-z0-9]+(-[a-z0-9]+)*/SKILL\.md$", f)]
    support = repo.find("*/skills/*/scripts/*", "*/skills/*/references/*", "*/skills/*/assets/*")
    c.add(
        "sk.layout",
        "Consistent layout & naming (kebab-case dirs, scripts/references)",
        1,
        (0.6 * (1 - len(bad_names) / max(1, len(skills))) + 0.4 * bool(support)) if skills else 0.5,
        [f"non-kebab skill dirs: {short(bad_names)}" if bad_names else "naming ok", f"supporting files: {len(support)}"],
        (f"Rename the {len(bad_names)} skill folders that are not kebab-case (`my-skill/SKILL.md`). " if bad_names else "")
        + "Keep the extras of a skill in `scripts/`, `references/` and `assets/` next to its SKILL.md.",
        todo=bad_names[:5],
    )
    return c.items


DIMENSION = Dimension(
    "skills", "Skills & Agent Markdown", "Reusable agent skills, subagents and commands captured as well-structured markdown.", assess
)
