"""Code review: changes reach the main line through reviewed pull requests, stay small, and AI use is governed.

Read from the git history of HEAD only (no hosting API), so a local folder is judged the same way as a GitHub repo.
"""

from __future__ import annotations

import re
from statistics import median

from ..model import Checks, Dimension, short
from ..repo import Repo, run_git
from ._util import headings, instruction_files

RECENT = 100  # commits of the main line that are judged
MIN_COMMITS = 10  # below this the history says too little: not applicable
PR_MARK = re.compile(r"\(#\d+\)\s*$|^Merge pull request #\d+|^Merge branch '.+' into|See merge request [\w/.-]*!\d+", re.M)
AGENTS = r"claude|copilot|codex|cursor|gemini|aider|devin|jules|openai|anthropic|windsurf"
AI_TRAILER = re.compile(rf"^Co-authored-by:.*({AGENTS})|Generated (with|by) .*({AGENTS})", re.I | re.M)
POLICY_FILES = ("AI_POLICY*", "AI-POLICY*", "AI_USAGE*", "AI-USAGE*", "docs/*ai-polic*", "docs/*ai_polic*", "docs/*ai-usage*", ".github/AI*")
POLICY_HEADING = re.compile(r"\b(ai|llm|genai|copilot|coding agents?|generated code|ai[- ]assisted)\b", re.I)


def _main_line(repo: Repo) -> list[tuple[str, int]]:
    """(subject, files changed vs the first parent) for the latest commits of the main line, newest first."""
    out = run_git(
        repo.root, "log", "--first-parent", "--diff-merges=first-parent", f"-n{RECENT}", "--format=\x1e%s", "--name-only", "HEAD", check=False
    )
    commits = []
    for block in out.split("\x1e")[1:]:
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if lines:
            commits.append((lines[0], len(lines) - 1))
    return commits


def assess(repo: Repo):
    c = Checks()
    line = _main_line(repo) if repo.is_git else []
    enough = len(line) >= MIN_COMMITS

    min_share = repo.param("rev.via_pr", "min_share")
    via_pr = [s for s, _ in line if PR_MARK.search(s)]
    share = 100 * len(via_pr) / len(line) if line else 0.0
    c.add(
        "rev.via_pr",
        "Changes reach the main branch through pull requests",
        3,
        min(1.0, 0.85 * share / min_share) if enough and min_share else None,
        f"{len(via_pr)} of the last {len(line)} commits on the main line came through a pull request ({share:.0f}%)"
        if enough
        else f"only {len(line)} commits: too little history to judge",
        "Protect the main branch: changes, including an agent's, land only through a pull request that a person reviews.",
    )

    max_files = repo.param("rev.small_changes", "max_files")
    sizes = [n for _, n in line if n > 0]
    med = median(sizes) if sizes else 0
    c.add(
        "rev.small_changes",
        "Changes are small enough to review",
        2,
        (1.0 if med <= max_files else min(1.0, 0.85 * max_files / med)) if enough and sizes else None,
        f"median change touches {med:g} files (last {len(sizes)} commits on the main line)" if enough and sizes else "too little history to judge",
        "Split work into small pull requests; ask agents for one logical change at a time.",
    )

    policy = repo.find(*POLICY_FILES)
    top = ("", ".github/", "docs/")  # the project's own CONTRIBUTING / README, not those of vendored or reference folders
    docs = [f for f in repo.find("CONTRIBUTING*", "README*") if f.rsplit("/", 1)[0] + "/" in top or "/" not in f]
    docs += [f for f in instruction_files(repo) if "/" not in f or f.startswith(".github/")]
    sections = [f"{f}: {h}" for f in docs[:20] for h in headings(repo.read(f)) if POLICY_HEADING.search(h)]
    c.add(
        "rev.ai_policy",
        "The rules for using AI in this project are written down",
        2,
        bool(policy or sections),
        short(policy + sections, 3) if policy or sections else "no AI usage policy or AI section in CONTRIBUTING / README",
        "Write down which AI tools may be used, what data must not reach them and how AI-written changes are reviewed "
        "(an AI_POLICY.md or a section in CONTRIBUTING.md).",
    )

    log = run_git(repo.root, "log", f"-n{RECENT * 2}", "--format=%B\x1e", "HEAD", check=False) if repo.is_git else ""
    attributed = sum(bool(AI_TRAILER.search(m)) for m in log.split("\x1e"))
    agents_used = bool(instruction_files(repo)) or attributed > 0
    c.add(
        "rev.ai_attribution",
        "Commits made with AI agents say so",
        1,
        (1.0 if attributed else 0.0) if agents_used else None,
        f"{attributed} recent commits name an AI co-author" if agents_used else "no sign of coding agents: not applicable",
        "Keep the agent's Co-authored-by trailer in commits, so reviewers know which changes an agent wrote.",
    )
    return c.items


DIMENSION = Dimension("review", "Code Review", "Pull requests, change size, AI usage policy and attribution of agent-written commits.", assess)
