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

from .model import band, grade

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


def _check(cid: str, title: str, status: str, evidence: list[str], fix: str, accepted: str, looks_at: str, why: str, limits: str = "") -> dict:
    """A check shaped like the scanner's, so the app shows it the same way: Expected, Found, What to do."""
    return {
        "id": cid,
        "title": title,
        "status": status,
        "score": {"pass": 1.0, "partial": 0.5, "fail": 0.0}.get(status),
        "weight": 1,
        "priority": "important",
        "source": "auto",
        "evidence": evidence,
        "recommendation": fix if status in ("fail", "partial") else "",
        "method": {"accepted": accepted, "looks_at": looks_at, "limits": limits, "basis": [], "convention": why},
    }


def _level(value: float, good: float, fair: float, higher_is_better: bool = True) -> str:
    if higher_is_better:
        return "pass" if value >= good else "partial" if value >= fair else "fail"
    return "pass" if value <= good else "partial" if value <= fair else "fail"


def checks(sessions: list[dict], commits: list[dict], skills_available: list[str]) -> list[dict]:
    """The agent-use rules with their verdicts on this project; the evidence names real sessions and commits."""
    out: list[dict] = []
    own = [c for c in commits if not c["merge"]]
    agent = [c for c in own if c["agent"]]
    linked = [c for c in own if c.get("session")]
    work = [s for s in sessions if s["api_calls"] >= 10]

    def na(cid: str, title: str, why_na: str, accepted: str, looks_at: str, why: str) -> None:
        out.append(_check(cid, title, "na", [why_na], "", accepted, looks_at, why))

    # 1. attribution
    t = ("agent.attributed", "Commits made with an agent say so.")
    acc = "At least 90% of the commits made during agent sessions carry a Co-Authored-By trailer of the agent."
    how = "Commits made while a session was active (from its first to its last message, plus 30 minutes) are checked for an agent trailer."
    why = "Only attributed code can be followed: how much the agent writes, and how its code holds up later."
    if linked:
        tagged = [c for c in linked if c["agent"]]
        miss = next((c for c in linked if not c["agent"]), None)
        out.append(
            _check(
                *t,
                _level(len(tagged) / len(linked), 0.9, 0.5),
                [f"{len(tagged)}/{len(linked)} commits made during agent sessions carry the trailer"]
                + ([f"{_subj(miss)} has no agent trailer"] if miss else []),
                "Keep the agent's Co-Authored-By trailer in every commit message (AGENTS.md says so for this project).",
                acc,
                how,
                why,
                "A person committing during a session is counted as the session's commit.",
            )
        )
    else:
        na(*t, "No commit was made during a recorded session.", acc, how, why)

    # 2. work lands
    t = ("agent.lands", "Agent sessions end in a commit.")
    acc = "At least 80% of the working sessions (10 or more steps) produce a commit."
    how = "Each session is matched with the commits made while it was active."
    why = "Work that is not committed cannot be reviewed, reused or measured; its cost buys nothing that lasts."
    if work:
        empty = [s for s in work if not s.get("commits")]
        ev = [f"{len(work) - len(empty)}/{len(work)} working sessions produced a commit"]
        ev += [
            f"Session of {_day(s['start'])} ({s['active_hours']} active hours"
            + (f", {_money(s['cost'])}" if s["cost"] is not None else "")
            + ") made no commit"
            for s in empty[:3]
        ]
        out.append(
            _check(
                *t,
                _level((len(work) - len(empty)) / len(work), 0.8, 0.5),
                ev,
                "End each task with a commit, even a small one. Keep exploration in a short session of its own and say so in the first prompt.",
                acc,
                how,
                why,
                "A session that only explores or answers questions is fine without a commit; the rule cannot tell it apart.",
            )
        )
    else:
        na(*t, "No working session was recorded.", acc, how, why)

    # 3. small commits
    t = ("agent.small_commits", "Agent commits are small enough to review.")
    acc = f"At most 10% of the agent's commits change more than {BIG_COMMIT_FILES} files (generated files and lockfiles not counted)."
    how = "Files changed per agent commit, from git log."
    why = "Nobody reads a 30-file change line by line, so the agent's mistakes slip through, and a problem cannot be traced to one decision."
    if agent:
        big = sorted([c for c in agent if c["code_files"] > BIG_COMMIT_FILES], key=lambda c: -c["code_files"])
        med = statistics.median(c["code_files"] for c in agent)
        ev = [f"{len(big)}/{len(agent)} agent commits change more than {BIG_COMMIT_FILES} files", f"median: {med:g} files per commit"]
        ev += [f"{_subj(c)}: {c['code_files']} files, +{c['add']} −{c['rm']} lines" for c in big[:3]]
        out.append(
            _check(
                *t,
                _level(len(big) / len(agent), 0.1, 0.3, higher_is_better=False),
                ev,
                "One task, one commit: ask the agent to commit after each finished step, before it starts the next idea.",
                acc,
                how,
                why,
            )
        )
    else:
        na(*t, "No agent commit in the history.", acc, how, why)

    # 4. tests
    t = ("agent.tests", "Agent changes come with tests.")
    acc = "At least half of the agent's commits also change a test."
    how = "Whether an agent commit touches a test file (tests/, test_*.py, *_test.go, *.test.ts, …)."
    why = "A test is the cheapest proof that the agent's code does what was asked, and it guards that code later."
    if agent:
        with_t = [c for c in agent if c["tests"]]
        ex = [c for c in agent if not c["tests"] and c["code_files"] >= 3][:3]
        out.append(
            _check(
                *t,
                _level(len(with_t) / len(agent), 0.5, 0.25),
                [f"{len(with_t)}/{len(agent)} agent commits change a test"] + [f"{_subj(c)} changes {c['code_files']} files and no test" for c in ex],
                "Ask for the test in the same prompt as the change, and keep the test command in CLAUDE.md / AGENTS.md so the agent runs it.",
                acc,
                how,
                why,
                "Documentation and configuration commits need no test, but they are counted.",
            )
        )
    else:
        na(*t, "No agent commit in the history.", acc, how, why)

    # 5. friction
    t = ("agent.friction", "The agent rarely fails or waits for permission.")
    acc = "At most 3% of the agent's tool calls fail or are refused."
    how = "Failed tool results and refused tool calls in the session logs, against all tool calls."
    why = "Each failure is a retry paid in time and tokens; each permission stop waits for a person."
    calls = sum(s["tool_calls"] for s in sessions)
    if calls:
        err, den = sum(s["tool_errors"] for s in sessions), sum(s["denied"] for s in sessions)
        worst = sorted(sessions, key=lambda s: -(s["tool_errors"] + s["denied"]))[:2]
        out.append(
            _check(
                *t,
                _level((err + den) / calls, 0.03, 0.06, higher_is_better=False),
                [f"{err + den}/{calls} tool calls failed ({err}) or were refused ({den})"]
                + [f"session of {_day(s['start'])}: {s['tool_errors']} failed, {s['denied']} refused of {s['tool_calls']}" for s in worst],
                "Allow the safe read-only commands the agent keeps asking for, and write the working commands (test, lint, run) into CLAUDE.md.",
                acc,
                how,
                why,
                "A failed test run is counted as a failure, though running tests that fail is part of the work.",
            )
        )
    else:
        na(*t, "No tool call was recorded.", acc, how, why)

    # 6. lean context
    t = ("agent.lean_context", "Sessions stay focused, so the context stays lean.")
    acc = f"No more than a third of the working sessions run longer than {LONG_SESSION_HOURS:g} active hours."
    how = "Active hours per session (pauses over 5 minutes left out) and the tokens read on every step."
    why = "Every step re-reads the whole conversation: in a long session each small change is slower and more expensive."
    if work:
        longs = sorted([s for s in work if s["active_hours"] >= LONG_SESSION_HOURS], key=lambda s: -s["context_per_call"])
        short = [s for s in work if s["active_hours"] < LONG_SESSION_HOURS]
        ev = [f"{len(longs)}/{len(work)} working sessions ran {LONG_SESSION_HOURS:g}+ active hours"]
        if longs and short:
            ev.append(
                f"tokens read per step: {statistics.mean(s['context_per_call'] for s in longs) / 1000:,.0f}k in long sessions, "
                f"{statistics.mean(s['context_per_call'] for s in short) / 1000:,.0f}k in shorter ones"
            )
        ev += [
            f"session of {_day(s['start'])}: {s['active_hours']} active hours, {s['context_per_call'] / 1000:,.0f}k tokens per step"
            for s in longs[:2]
        ]
        out.append(
            _check(
                *t,
                _level(len(longs) / len(work), 0.0, 1 / 3, higher_is_better=False),
                ev,
                "Start a fresh session (/clear) for each new task; keep what must survive in CLAUDE.md or memory.",
                acc,
                how,
                why,
            )
        )
    else:
        na(*t, "No working session was recorded.", acc, how, why)

    # 7. skills
    t = ("agent.skills_used", "The project's skills are used.")
    acc = "At least half of the skills defined in the project were invoked in a recorded session."
    how = "Skills in .claude/skills/ and .agents/skills/ against Skill calls in the session logs."
    why = "A skill is the team's tested recipe; when it is not used, the agent improvises the same work each time."
    if skills_available:
        used = {k for s in sessions for k in s["skills"]}
        unused = [k for k in skills_available if k not in used]
        out.append(
            _check(
                *t,
                _level((len(skills_available) - len(unused)) / len(skills_available), 0.5, 0.01),
                [f"{len(skills_available) - len(unused)}/{len(skills_available)} skills were invoked"]
                + ([f"never invoked: {', '.join(unused)}"] if unused else []),
                "Name the skills in CLAUDE.md and make each description say when to use it, in the words people type.",
                acc,
                how,
                why,
                "A slash command typed by a person is not seen as a skill call.",
            )
        )
    else:
        na(*t, "The project defines no skills.", acc, how, why)
    return out


def report(source: str, root: Path | None = None) -> dict:
    """The agent-use tab of one local project: one aspect, laid out like the others."""
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
    own = [c for c in commits if not c["merge"]]
    costed = {s["id"] for s in sessions if s["cost"] is not None}
    total = sum(s["cost"] or 0 for s in sessions)
    paid = [c for c in own if c.get("session") in costed]
    cs = checks(sessions, commits, skills)
    scored = [c["score"] for c in cs if c["score"] is not None]
    score = round(100 * sum(scored) / len(scored), 1) if scored else None
    summary = {
        "first": sessions[0]["start"] if sessions else None,
        "last": sessions[-1]["end"] if sessions else None,
        "sessions": len(sessions),
        "active_hours": round(sum(s["active_hours"] for s in sessions), 1),
        "commits": len(own),
        "agent_commits": len([c for c in own if c["agent"]]),
        "cost": round(total, 2),
        "cost_sessions": len(costed),
        "cost_per_commit": round(total / len(paid), 2) if paid else None,
    }
    return {
        "available": True,
        "logs": str(d),
        "summary": summary,
        "aspect": {
            "id": "agent",
            "name": "Agent use",
            "description": "How a coding agent works on this project: its session logs on this machine (read only) and the git history.",
            "score": score,
            "uncapped_score": score,
            "grade": grade(score),
            "band": band(score),
            "capped_by": [],
            "adjust": 0,
            "review_notes": [],
            "checks": cs,
        },
        "sessions": sessions[::-1],  # not shown yet: the data for the trend over time
        "commits": commits[:200],
    }
