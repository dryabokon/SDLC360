"""How a coding agent was used on a local project: Claude Code session logs joined with git history.

Prototype. It reads, never writes: the agent's own session logs (~/.claude/projects/<project>/<session>.jsonl, a
format Claude Code does not document, so every field is read defensively) and `git log` of the project. It reports
numbers and plain findings (what is good, what to improve, how), never the text of prompts or answers.

A session is linked to the commits made while it was active (from its first to its last entry, plus 30 minutes).
The cost is what Claude Code itself records for a finished session (`cost-state`): tokens priced at the API list
price. On a subscription this is not what was paid; it is the value of the work at API prices.
"""

from __future__ import annotations

import json
import re
import statistics
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

LOGS_ROOT = Path.home() / ".claude" / "projects"
IDLE = timedelta(minutes=5)  # a gap longer than this between two entries is not counted as active time
LINK_AFTER = timedelta(minutes=30)
BIG_COMMIT_FILES = 15
LONG_SESSION_HOURS = 3.0
TEST_PATH = re.compile(r"(^|/)(tests?|spec|__tests__)/|(^|/)test_[^/]+\.py$|_test\.(py|go)$|\.(test|spec)\.[jt]sx?$")
AGENT_TRAILER = re.compile(r"^(Co-Authored-By|Agent-Session):.*\b(claude|anthropic|copilot|codex|cursor|gemini|aider|devin)\b", re.I | re.M)
GENERATED = re.compile(r"(\.lock|lock\.json|\.min\.js|\.svg|\.csv|\.parquet|\.ipynb)$|(^|/)(dist|build|vendor|node_modules)/")
_CACHE: dict[tuple[str, float, int], dict] = {}


def log_dir(source: str, root: Path | None = None) -> Path | None:
    """Claude Code keeps a project's sessions in a folder named after its path: D:\\a\\b -> D--a-b."""
    if source.startswith("github.com/"):
        return None
    d = (root or LOGS_ROOT) / re.sub(r"[^A-Za-z0-9]", "-", str(Path(source)))
    return d if d.is_dir() else None


def _ts(s: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None
    except ValueError:
        return None


def parse_session(f: Path) -> dict:
    """Numbers of one session file. Usage is counted once per API request (an answer spans several entries)."""
    st = f.stat()
    key = (str(f), st.st_mtime, st.st_size)
    if key in _CACHE:
        return _CACHE[key]
    times: list[datetime] = []
    requests: set[str] = set()
    tok = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    n = {"prompts": 0, "api_calls": 0, "tool_calls": 0, "tool_errors": 0, "denied": 0, "subagents": 0}
    skills: dict[str, int] = {}
    cost = None
    for line in f.open(encoding="utf-8", errors="replace"):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if not isinstance(e, dict):
            continue
        t = _ts(e.get("timestamp"))
        if t and e.get("type") in ("user", "assistant"):
            times.append(t)
        if e.get("type") == "cost-state" and isinstance(e.get("totalCostUSD"), (int, float)):
            cost = float(e["totalCostUSD"])
        if e.get("toolDenialKind"):
            n["denied"] += 1
        m = e.get("message")
        if not isinstance(m, dict):
            continue
        content = m.get("content")
        if e.get("type") == "assistant":
            rid = e.get("requestId") or m.get("id") or ""
            u = m.get("usage")
            if isinstance(u, dict) and rid not in requests:
                requests.add(rid)
                n["api_calls"] += 1
                tok["input"] += u.get("input_tokens") or 0
                tok["output"] += u.get("output_tokens") or 0
                tok["cache_read"] += u.get("cache_read_input_tokens") or 0
                tok["cache_write"] += u.get("cache_creation_input_tokens") or 0
            for b in content if isinstance(content, list) else []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    n["tool_calls"] += 1
                    if b.get("name") == "Agent":
                        n["subagents"] += 1
                    if b.get("name") == "Skill":
                        name = str((b.get("input") or {}).get("skill") or "?")
                        skills[name] = skills.get(name, 0) + 1
        elif e.get("type") == "user" and not e.get("isMeta"):
            if isinstance(content, str):
                n["prompts"] += 1 if not content.startswith("<") else 0
            for b in content if isinstance(content, list) else []:
                if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error"):
                    n["tool_errors"] += 1
                elif isinstance(b, dict) and b.get("type") == "text" and not str(b.get("text", "")).startswith("<"):
                    n["prompts"] += 1
    times.sort()
    active = sum((min(b - a, IDLE) for a, b in zip(times, times[1:], strict=False)), timedelta())
    context = (tok["input"] + tok["cache_read"] + tok["cache_write"]) / n["api_calls"] if n["api_calls"] else 0
    out = {
        "id": f.stem,
        "start": times[0].isoformat() if times else None,
        "end": times[-1].isoformat() if times else None,
        "active_hours": round(active.total_seconds() / 3600, 2),
        "span_hours": round((times[-1] - times[0]).total_seconds() / 3600, 1) if times else 0,
        "tokens": tok,
        "context_per_call": round(context),
        "cost": round(cost, 2) if cost is not None else None,
        "skills": skills,
        **n,
    }
    _CACHE[key] = out
    return out


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else ""


def git_commits(repo: Path) -> list[dict]:
    """Commits of the current branch, newest first, with files and whether an agent co-authored them."""
    raw = _git(repo, "log", "--format=%x1e%H%x1f%cI%x1f%P%x1f%s%x1f%B%x1f", "--numstat")
    out = []
    for rec in raw.split("\x1e")[1:]:
        head, _, stat = rec.rpartition("\x1f")
        sha, date, parents, subject, body = head.split("\x1f")[:5]
        files, add, rm = [], 0, 0
        for ln in stat.strip().splitlines():
            parts = ln.split("\t")
            if len(parts) == 3:
                files.append(parts[2])
                add += int(parts[0]) if parts[0].isdigit() else 0
                rm += int(parts[1]) if parts[1].isdigit() else 0
        out.append(
            {
                "sha": sha,
                "date": date,
                "subject": subject,
                "merge": len(parents.split()) > 1,
                "agent": bool(AGENT_TRAILER.search(body)),
                "files": len(files),
                "code_files": sum(1 for p in files if not GENERATED.search(p)),
                "tests": any(TEST_PATH.search(p) for p in files),
                "add": add,
                "rm": rm,
            }
        )
    return out


def _link(sessions: list[dict], commits: list[dict]) -> None:
    """Each commit goes to the session active when it was made (the latest started one, if several)."""
    for c in commits:
        t = _ts(c["date"])
        cands = [s for s in sessions if s["start"] and t and _ts(s["start"]) <= t <= _ts(s["end"]) + LINK_AFTER]  # type: ignore[operator]
        c["session"] = max(cands, key=lambda s: s["start"])["id"] if cands else None
    for s in sessions:
        mine = [c for c in commits if c.get("session") == s["id"]]
        s["commits"] = len(mine)
        s["cost_per_commit"] = round(s["cost"] / len(mine), 2) if s["cost"] is not None and mine else None
        for c in mine:
            c["cost"] = s["cost_per_commit"]


def _money(v: float | None) -> str:
    return "–" if v is None else f"${v:,.0f}" if v >= 10 else f"${v:,.2f}"


def _subj(c: dict) -> str:
    s = c["subject"]
    return f"{c['sha'][:8]} “{s if len(s) <= 80 else s[:77] + '…'}”"


def _day(iso: str | None) -> str:
    t = _ts(iso)
    return t.strftime("%d %b %Y") if t else "?"


def findings(sessions: list[dict], commits: list[dict], skills_available: list[str]) -> list[dict]:
    """Plain findings with an example from this project: what we see, why it matters, what to do."""
    out: list[dict] = []
    agent = [c for c in commits if c["agent"] and not c["merge"]]
    costed = [s for s in sessions if s["cost"] is not None]

    def add(tone: str, title: str, seen: str, example: str, why: str, fix: str, who: list[str]) -> None:
        out.append({"tone": tone, "title": title, "seen": seen, "example": example, "why": why, "fix": fix, "who": who})

    if agent:
        share = len(agent) / max(1, len([c for c in commits if not c["merge"]]))
        add(
            "good",
            "Agent work is visible in the history",
            f"{len(agent)} of {len([c for c in commits if not c['merge']])} commits ({share:.0%}) say an agent co-authored them.",
            f"Latest: {_subj(agent[0])}.",
            "You can tell which code the agent wrote, so its quality can be followed over time.",
            "Keep the Co-Authored-By trailer on every agent commit.",
            ["Team lead"],
        )
    idle = [s for s in costed if s["commits"] == 0 and (s["cost"] or 0) >= 1]
    if idle:
        worst = max(idle, key=lambda s: s["cost"] or 0)
        add(
            "improve",
            "Some sessions ended without a commit",
            f"{len(idle)} of {len(costed)} sessions with a recorded cost produced no commit, "
            f"together {_money(sum(s['cost'] or 0 for s in idle))} at API prices.",
            f"Session of {_day(worst['start'])}: {worst['active_hours']} active hours, {_money(worst['cost'])}, no commit.",
            "Work that is not committed cannot be reviewed, reused or measured; "
            "often it is exploration that should have been a short, separate session.",
            "End each task with a commit, even a small one; keep exploration in short sessions and say so in the first prompt.",
            ["Developer", "Business"],
        )
    big = sorted([c for c in agent if c["code_files"] > BIG_COMMIT_FILES], key=lambda c: -c["code_files"])
    if agent:
        med = statistics.median(c["code_files"] for c in agent)
        if big:
            b = big[0]
            add(
                "improve",
                "Agent commits are too big to review",
                f"{len(big)} of {len(agent)} agent commits change more than {BIG_COMMIT_FILES} files; the median is {med:g}.",
                f"{_subj(b)}: {b['code_files']} files, +{b['add']} −{b['rm']} lines.",
                "Nobody reads a 20-file change line by line, so agent mistakes slip through, and a problem cannot be traced to one decision.",
                "One task, one commit: ask the agent to commit after each finished step, and to stop and commit before starting the next idea.",
                ["Developer", "Team lead"],
            )
        else:
            add(
                "good",
                "Agent commits stay reviewable",
                f"The median agent commit changes {med:g} files.",
                "",
                "Small changes are reviewed for real.",
                "Keep it so.",
                ["Team lead"],
            )
    if commits and not any(c["merge"] for c in commits) and agent:
        add(
            "improve",
            "Agent code goes straight to the main branch",
            "There is not a single merge in the history: every change was committed directly.",
            f"{agent[0]['sha'][:8]} went to the branch without a pull request.",
            "No second pair of eyes and no automatic gate between the agent's output and the shared code.",
            "Let the agent work on a branch and open a pull request; CI and a reviewer approve it.",
            ["Team lead", "Business"],
        )
    if agent:
        with_tests = [c for c in agent if c["tests"]]
        share = len(with_tests) / len(agent)
        without = next((c for c in agent if not c["tests"] and c["code_files"] >= 3), None)
        add(
            "good" if share >= 0.5 else "improve",
            "Tests come with the agent's changes" if share >= 0.5 else "Agent changes rarely come with tests",
            f"{len(with_tests)} of {len(agent)} agent commits ({share:.0%}) also change tests.",
            f"For example {_subj(without)} changes {without['code_files']} files and no test." if without else "",
            "A test is the cheapest proof that the agent's code does what was asked, and it guards it later.",
            "Ask for the test in the same prompt as the change, and keep the test command in CLAUDE.md / AGENTS.md so the agent runs it.",
            ["Developer"],
        )
    calls = sum(s["tool_calls"] for s in sessions)
    if calls:
        err = sum(s["tool_errors"] for s in sessions)
        den = sum(s["denied"] for s in sessions)
        worst = max(sessions, key=lambda s: s["tool_errors"] + s["denied"])
        add(
            "improve" if (err + den) / calls > 0.05 else "good",
            "The agent often hits errors and permission stops" if (err + den) / calls > 0.05 else "The agent works with little friction",
            f"{err} failed tool calls and {den} refused ones out of {calls} ({(err + den) / calls:.0%}).",
            f"Session of {_day(worst['start'])}: {worst['tool_errors']} failures, {worst['denied']} refusals in {worst['tool_calls']} calls.",
            "Each failure is a retry the developer pays for in time and tokens; each permission stop waits for a human.",
            "Allow the safe read-only commands the agent keeps asking for, and write the working commands (test, lint, run) into CLAUDE.md.",
            ["Developer"],
        )
    if costed:
        longs = [s for s in sessions if s["active_hours"] >= LONG_SESSION_HOURS]
        short = [s for s in sessions if s["active_hours"] < LONG_SESSION_HOURS and s["api_calls"] >= 10]
        if longs and short:
            lc = statistics.mean(s["context_per_call"] for s in longs)
            sc = statistics.mean(s["context_per_call"] for s in short)
            if lc > 1.2 * sc:
                ex = max(longs, key=lambda s: s["context_per_call"])
                add(
                    "improve",
                    "Long sessions carry a heavy context",
                    f"In sessions of {LONG_SESSION_HOURS:g}+ active hours every step reads {lc / 1000:,.0f}k tokens of context, "
                    f"in shorter ones {sc / 1000:,.0f}k.",
                    f"Session of {_day(ex['start'])}: {ex['active_hours']} active hours, {ex['context_per_call'] / 1000:,.0f}k tokens per step.",
                    "Every step re-reads the whole conversation: a long session makes each small change slower and more expensive.",
                    "Start a fresh session (/clear) for each new task; keep what must survive in CLAUDE.md or memory.",
                    ["Developer", "Business"],
                )
    used = {k for s in sessions for k in s["skills"]}
    if skills_available:
        unused = [k for k in skills_available if k not in used]
        rare = len(unused) > len(skills_available) / 2
        add(
            "improve" if rare else "good",
            ("The project's skills are not used" if len(unused) == len(skills_available) else "Most of the project's skills are not used")
            if rare
            else "The project's skills are in use",
            f"{len(skills_available)} skills are defined; {len(skills_available) - len(unused)} were invoked in {len(sessions)} sessions.",
            f"Never invoked: {', '.join(unused[:5])}." if unused else "",
            "A skill is the team's tested recipe; when it is not used, the agent improvises the same work each time.",
            "Name the skills in CLAUDE.md and make each description say when to use it, in the words people type.",
            ["Team lead", "Developer"],
        )
    return sorted(out, key=lambda f: f["tone"] == "good")  # what to improve first


def report(source: str, root: Path | None = None) -> dict:
    """The agent-use tab of one local project."""
    d = log_dir(source, root)
    repo = Path(source)
    if d is None or not repo.is_dir():
        reason = (
            "GitHub projects have no local agent logs." if source.startswith("github.com/") else "No Claude Code sessions were found for this folder."
        )
        return {"available": False, "reason": reason}
    sessions = sorted((parse_session(f) for f in d.glob("*.jsonl")), key=lambda s: s["start"] or "")
    sessions = [s for s in sessions if s["api_calls"]]
    commits = git_commits(repo)
    _link(sessions, commits)
    skills = sorted({p.parent.name for base in (".claude/skills", ".agents/skills") for p in (repo / base).glob("*/SKILL.md")})
    agent = [c for c in commits if c["agent"] and not c["merge"]]
    costed = [s for s in sessions if s["cost"] is not None]
    linked = [c for c in commits if c.get("session")]
    total = sum(s["cost"] or 0 for s in costed)
    return {
        "available": True,
        "logs": str(d),
        "summary": {
            "first": sessions[0]["start"] if sessions else None,
            "last": sessions[-1]["end"] if sessions else None,
            "sessions": len(sessions),
            "active_hours": round(sum(s["active_hours"] for s in sessions), 1),
            "commits": len([c for c in commits if not c["merge"]]),
            "agent_commits": len(agent),
            "linked_commits": len(linked),
            "cost": round(total, 2),
            "cost_sessions": len(costed),
            "cost_per_commit": round(total / len([c for c in linked if c["session"] in {s["id"] for s in costed}]), 2)
            if any(c["session"] in {s["id"] for s in costed} for c in linked)
            else None,
            "skills_available": skills,
        },
        "findings": findings(sessions, commits, skills),
        "sessions": sessions[::-1],
        "commits": commits[:60],
    }
