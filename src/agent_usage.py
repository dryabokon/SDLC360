"""How a coding agent was used on a local project: Claude Code session logs joined with git history.

Prototype. It reads, never writes: the agent's own session logs (~/.claude/projects/<project>/<session>.jsonl, a
format Claude Code does not document, so every field is read defensively) and `git log` of the project. It reports
numbers and plain findings (what is good, what to improve, how), never the text of prompts or answers.

The numbers of a session (parse_session) carry no text, so they can travel: the hosted app keeps them in a run folder
(SESSIONS_FILE) with the commits they are joined with, sent by the browser (it parses the logs itself, the same way, see
parseSession in template.html) or put there by `python sdlc.py attach-sessions`.
A session is linked to the commits made while it was active (from its first to its last entry, plus 30 minutes).
The cost is what Claude Code itself records for a finished session (`cost-state`): tokens priced at the API list
price. On a subscription this is not what was paid; it is the value of the work at API prices.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import statistics
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from . import skill_review
from .hosting import is_remote
from .model import band, grade

LOGS_ROOT = Path.home() / ".claude" / "projects"
IDLE = timedelta(minutes=5)  # a gap longer than this between two entries is not counted as active time
LINK_AFTER = timedelta(minutes=30)
BIG_COMMIT_FILES = 15
LONG_SESSION_HOURS = 3.0
# the usual ratio of Claude prices to an input token: an answer token 5, writing to the cache 1.25, reading from it 0.1
# (the same 5 for answers on every current model; cached reads are 0.025-0.1, so the split is an estimate)
WEIGHT = {"input": 1.0, "output": 5.0, "cache_write": 1.25, "cache_read": 0.1}
COST_IN_WORK = (0.7, 0.4)  # pass at 70% or more of the cost in the work, partial at 40%
COST_REREAD = (0.2, 0.4)  # pass at 20% or less on re-reading long conversations, partial at 40%
COST_NO_COMMIT = (0.1, 0.25)  # pass at 10% or less on sessions without a commit, partial at 25%
FRESH_CONTEXT = 100_000  # tokens a step reads in a fresh session, when the project has no short sessions to tell
TEST_PATH = re.compile(r"(^|/)(tests?|spec|__tests__)/|(^|/)test_[^/]+\.py$|_test\.(py|go)$|\.(test|spec)\.[jt]sx?$")
AGENT_TRAILER = re.compile(r"^(Co-Authored-By|Agent-Session):.*\b(claude|anthropic|copilot|codex|cursor|gemini|aider|devin)\b", re.I | re.M)
GENERATED = re.compile(r"(\.lock|lock\.json|\.min\.js|\.svg|\.csv|\.parquet|\.ipynb)$|(^|/)(dist|build|vendor|node_modules)/")
# lines of source and docs: what it takes to change them is the measure; data files (gt.txt, .onnx, .json) are not
CODE = re.compile(r"\.(py|pyi|js|jsx|ts|tsx|html|css|sh|bat|ps1|go|rs|cs|cpp|cc|c|h|hpp|java|kt|sql|toml|ya?ml|md)$", re.I)
_CACHE: dict[tuple[str, float, int], dict] = {}
SESSIONS_FILE = "agent_sessions.json"  # in a run folder: {origin, attached, sessions, commits, skills}
MAX_SESSIONS = 2000
# a skill is also used when the agent runs its script or reads its files: .claude/skills/<name>/...
SKILL_PATH = re.compile(r"[\\/]skills[\\/]([A-Za-z0-9_.-]+?)(?:[\\/]|\.md\b)")  # a skill's folder, or a note: skills/<name>.md
AFTER_SKILL = 10  # the tool calls after a use of a skill whose failures are counted against it


def log_dir(source: str, root: Path | None = None) -> Path | None:
    """Claude Code keeps a project's sessions in a folder named after its path: D:\\a\\b -> D--a-b."""
    if is_remote(source):
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
    skill_errors: dict[str, int] = {}
    watch: dict[str, int] = {}  # skill -> tool results still counted against it
    reads: list[tuple[float, int]] = []  # (time, tokens the request read: input + cache), for each commit's effort
    at: dict[str, list[float]] = {"prompts": [], "calls": [], "errors": []}  # when each happened, for each commit's share
    cost = None
    days: dict[str, dict[str, float]] = {}  # per local day, for the timeline: a session can span days

    def day(t: datetime | None, key: str, v: float = 1) -> None:
        if t:
            d = days.setdefault(
                t.astimezone().date().isoformat(), {"hours": 0, "tool_calls": 0, "tool_errors": 0, "denied": 0, "output_tokens": 0, "read_tokens": 0}
            )
            d[key] += v

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
            day(t, "denied")
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
                day(t, "output_tokens", u.get("output_tokens") or 0)
                read = (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
                day(t, "read_tokens", read)
                if t:
                    reads.append((t.timestamp(), read))
                tok["cache_read"] += u.get("cache_read_input_tokens") or 0
                tok["cache_write"] += u.get("cache_creation_input_tokens") or 0
            for b in content if isinstance(content, list) else []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    n["tool_calls"] += 1
                    day(t, "tool_calls")
                    if t:
                        at["calls"].append(t.timestamp())
                    if b.get("name") == "Agent":
                        n["subagents"] += 1
                    raw_in = b.get("input")
                    inp: dict = raw_in if isinstance(raw_in, dict) else {}
                    if b.get("name") == "Skill":
                        name = str(inp.get("skill") or "?")
                        skills[name] = skills.get(name, 0) + 1
                        watch[name] = AFTER_SKILL
                    else:
                        hit = SKILL_PATH.search(str(inp.get("command") or inp.get("file_path") or inp.get("path") or ""))
                        if hit and hit.group(1) not in watch and hit.group(1).rsplit(":", 1)[-1] not in {k.rsplit(":", 1)[-1] for k in watch}:
                            skills[hit.group(1)] = skills.get(hit.group(1), 0) + 1
                            watch[hit.group(1)] = AFTER_SKILL
        elif e.get("type") == "user" and not e.get("isMeta"):
            if isinstance(content, str) and not content.startswith("<"):
                n["prompts"] += 1
                if t:
                    at["prompts"].append(t.timestamp())
            for b in content if isinstance(content, list) else []:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    for k in list(watch):
                        if b.get("is_error"):
                            skill_errors[k] = skill_errors.get(k, 0) + 1
                        watch[k] -= 1
                        if watch[k] <= 0:
                            del watch[k]
                if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error"):
                    n["tool_errors"] += 1
                    day(t, "tool_errors")
                    if t:
                        at["errors"].append(t.timestamp())
                elif isinstance(b, dict) and b.get("type") == "text" and not str(b.get("text", "")).startswith("<"):
                    n["prompts"] += 1
                    if t:
                        at["prompts"].append(t.timestamp())
    times.sort()
    active = sum((min(b - a, IDLE) for a, b in zip(times, times[1:], strict=False)), timedelta())
    for a, b in zip(times, times[1:], strict=False):
        day(b, "hours", min(b - a, IDLE).total_seconds() / 3600)
    context = (tok["input"] + tok["cache_read"] + tok["cache_write"]) / n["api_calls"] if n["api_calls"] else 0
    out = {
        "id": f.stem,
        "start": times[0].isoformat() if times else None,
        "end": times[-1].isoformat() if times else None,
        "active_hours": round(active.total_seconds() / 3600, 2),
        "by_day": {d: {k: round(v, 3) for k, v in x.items()} for d, x in sorted(days.items())},
        "span_hours": round((times[-1] - times[0]).total_seconds() / 3600, 1) if times else 0,
        "tokens": tok,
        "context_per_call": round(context),
        "cost": round(cost, 2) if cost is not None else None,
        "skills": skills,
        "skill_errors": skill_errors,
        "reads": sorted(reads),
        "at": {k: sorted(v) for k, v in at.items()},
        **n,
    }
    _CACHE[key] = out
    return out


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else ""


def git_author(repo: Path) -> str:
    """Whose commits are joined with the sessions on this machine: SDLC360_AUTHOR ("all": everyone's), else the
    e-mail this working copy commits with (a client project often has its own). Empty: everyone's."""
    a = os.environ.get("SDLC360_AUTHOR", "").strip()
    if a:
        return "" if a.lower() == "all" else a
    return _git(repo, "config", "user.email").strip()


def git_commits(repo: Path, author: str = "") -> list[dict]:
    """Commits of the current branch, newest first, with files and whether an agent co-authored them. With an author,
    only theirs: the sessions on one machine are one person's, and a colleague's commit made meanwhile is not theirs."""
    who = ["-F", f"--author=<{author}>"] if author else []  # -F: the e-mail as it is, not a pattern
    raw = _git(repo, "log", "--format=%x1e%H%x1f%cI%x1f%P%x1f%s%x1f%B%x1f", "--numstat", *who)
    out = []
    for rec in raw.split("\x1e")[1:]:
        head, _, stat = rec.rpartition("\x1f")
        sha, date, parents, subject, body = head.split("\x1f")[:5]
        files, add, rm, code_add, code_rm, code_paths = [], 0, 0, 0, 0, []
        for ln in stat.strip().splitlines():
            parts = ln.split("\t")
            if len(parts) == 3:
                files.append(parts[2])
                a, r = (int(parts[0]) if parts[0].isdigit() else 0), (int(parts[1]) if parts[1].isdigit() else 0)
                add, rm = add + a, rm + r
                if CODE.search(parts[2]) and not GENERATED.search(parts[2]):
                    code_add, code_rm = code_add + a, code_rm + r
                    if a:
                        code_paths.append(parts[2])
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
                "code_add": code_add,
                "code_lines": code_add + code_rm,
                "code_paths": code_paths,
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


HABITS = {  # the practice in plain words: opens What to do, also when the check is met
    "agent.attributed": "Keep the Co-Authored-By line in the commits the agent made.",
    "agent.lands": "End a working session with a commit.",
    "agent.small_commits": "Commit the agent's work in small steps you can review.",
    "agent.tests": "Ask the agent for tests with every change.",
    "agent.friction": "Allow the agent the commands it needs, so it neither fails nor waits for you.",
    "agent.lean_context": "One task, one session: start fresh with /clear when the task changes.",
    "agent.skills_used": "Use the project's skills, and delete the ones nobody uses.",
    "agent.cost_in_work": "Spend the agent's money on changes that get committed.",
    "agent.cost_reread": "One task, one session: in a long conversation every step pays for re-reading all of it.",
    "agent.cost_no_commit": "Finish what you start with the agent, or stop early.",
}


def _check(
    cid: str,
    title: str,
    status: str,
    evidence: list[str],
    fix: str,
    accepted: str,
    looks_at: str,
    why: str,
    limits: str = "",
) -> dict:
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
        "method": {"accepted": accepted, "habit": HABITS.get(cid, ""), "looks_at": looks_at, "limits": limits, "basis": [], "convention": why},
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
                f"Add the Co-Authored-By trailer of the agent to commit messages: {len(linked) - len(tagged)} of {len(linked)} "
                "commits made during sessions lack it. Say so in CLAUDE.md / AGENTS.md, so the agent keeps it.",
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
                f"End each task with a commit, even a small one: {len(empty)} of {len(work)} working sessions made none. "
                "Keep exploration in a short session of its own and say so in the first prompt.",
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
                f"Ask for the test in the same prompt as the change: {len(agent) - len(with_t)} of {len(agent)} agent commits change no test. "
                "Keep the test command in CLAUDE.md / AGENTS.md, so the agent runs it.",
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
    how = (
        "Skills in .claude/skills/ and .agents/skills/ against their uses in the session logs: "
        "a Skill call, or a command or read of a file in the skill's folder."
    )
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


def _effort(sessions: list[dict], commits: list[dict]) -> None:
    """Each agent commit's effort since its session's previous commit (or start): tokens read, active minutes, prompts,
    tool calls and failures. Its cost is its share of the session's reading times the session's cost. What a session
    does after its last commit goes to no commit.
    """
    for s in sessions:
        mine = sorted((c for c in commits if c.get("session") == s["id"]), key=lambda c: c["date"])
        reads = s.get("reads", [])
        total = sum(r for _, r in reads)
        since = 0.0
        at = s.get("at", {})
        for c in mine:
            t = _ts(c["date"]).timestamp()  # type: ignore[union-attr]
            mine_reads = [(ts, r) for ts, r in reads if since < ts <= t]
            c["read"] = sum(r for _, r in mine_reads)
            times = [ts for ts, _ in mine_reads]  # active time: gaps between the agent's requests, a pause over IDLE cut
            c["minutes"] = round(sum(min(b - a, IDLE.total_seconds()) for a, b in zip(times, times[1:], strict=False)) / 60, 1)
            for k in ("prompts", "calls", "errors"):
                c[k] = sum(1 for ts in at.get(k, []) if since < ts <= t)
            c["effort_cost"] = round(s["cost"] * c["read"] / total, 2) if s["cost"] is not None and total else None
            since = t


def _short(subject: str) -> str:
    """The first clause of a commit subject: enough to recognise it in a table."""
    s = re.split(r"; | - | \(|\. ", subject, maxsplit=1)[0].strip()
    return s if len(s) <= 70 else s[:67].rstrip() + "…"


# The two indices: what a change costs and how long it takes, against a change of the same size on the same project.
# Effort grows far slower than size (about lines^0.3 on the projects measured), so per-line figures only measure commit
# size; the index compares each commit with what a change of its size usually takes here (a log-log fit).
INDICES = [
    (
        "cost",
        "Cost of a typical change",
        "read",
        "Tokens and cost at API list prices of a change, against a change of the same size on this project.",
    ),
    (
        "time",
        "Time of a typical change",
        "minutes",
        "Minutes the agent worked on a change (pauses over 5 minutes left out), against a change of the same size here.",
    ),
]
BOOTSTRAP = 1000  # resamples for the 95% range of first window vs last window


def _fit(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Least squares y = a + b*x."""
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx if sxx else 0.0
    return my - b * mx, b


def _index(cs: list[dict], key: str, window: int) -> dict | None:
    """One index over the commits (oldest first): the rolling series rebased so the first window is 100, the ratio of the
    last window to the first with its 95% range, and the effort of a change of median size then and now."""
    data = [c for c in cs if c.get(key, 0) > 0 and c["code_lines"] > 0]
    if len(data) < 2 * window:
        return None
    xs, ys = [math.log(c["code_lines"]) for c in data], [math.log(c[key]) for c in data]
    a, b = _fit(xs, ys)
    res = {c["sha"]: y - a - b * x for c, x, y in zip(data, xs, ys, strict=True)}
    r = list(res.values())
    base = sum(r[:window]) / window
    rng = random.Random(0)  # the same data always gives the same range
    boot = sorted(
        math.exp(sum(rng.choice(r[-window:]) for _ in range(window)) / window - sum(rng.choice(r[:window]) for _ in range(window)) / window)
        for _ in range(BOOTSTRAP)
    )
    ratio = math.exp(sum(r[-window:]) / window - base)
    lo, hi = boot[int(0.025 * BOOTSTRAP)], boot[int(0.975 * BOOTSTRAP) - 1]
    size = statistics.median(c["code_lines"] for c in data)
    typical = math.exp(a + b * math.log(size) + base)
    series = {}
    for i in range(window - 1, len(data)):
        series[data[i]["sha"]] = round(100 * math.exp(sum(r[i - window + 1 : i + 1]) / window - base))
    return {
        "ratio": round(ratio, 2),
        "lo": round(lo, 2),
        "hi": round(hi, 2),
        "clear": lo > 1 or hi < 1,  # the 95% range leaves out 'no change'
        "exponent": round(b, 2),
        "size": round(size),
        "first": typical,
        "last": typical * ratio,
        "per_commit": {sha: round(math.exp(v), 2) for sha, v in res.items()},  # this commit against a usual one of its size
        "series": series,
    }


def timeline(sessions: list[dict], commits: list[dict], repo: Path | None = None) -> dict:
    """Is changing this project getting dearer or slower for the agent? Two size-adjusted indices over its commits.

    Each agent commit since the first session gets its effort (tokens, active minutes, cost share since its session's
    previous commit). Each index compares a commit with a change of the same size on this project and is drawn over
    the last `window` commits, 100 = the first window. The template only draws it.
    """
    del repo  # history alone is enough now; kept for the caller
    started = [s for s in sessions if s["start"]]
    first = min((t for s in started if (t := _ts(s["start"])) is not None), default=None)
    agent = [c for c in commits if c["agent"] and not c["merge"] and first and (_ts(c["date"]) or first) >= first]
    _effort(started, agent)
    measured = [c for c in reversed(agent) if c.get("read") and c["code_lines"]]  # oldest first
    window = max(5, min(20, len(measured) // 5))
    costed = [c for c in measured if c.get("effort_cost") is not None]
    usd_per_token = sum(c["effort_cost"] for c in costed) / max(1, sum(c["read"] for c in costed)) if costed else None
    indices = []
    for key, name, field, hint in INDICES:
        ix = _index(measured, field, window)
        indices.append({"key": key, "name": name, "hint": hint, "usd_per_token": usd_per_token if key == "cost" else None, **(ix or {})})
    by_key = {i["key"]: i for i in indices}
    series = [{"sha": c["sha"][:8], "date": c["date"], **{k: by_key[k].get("series", {}).get(c["sha"]) for k in by_key}} for c in measured]
    rows = [
        {
            "sha": c["sha"][:8],
            "date": c["date"],
            "subject": _short(c["subject"]),
            "full": c["subject"],
            "lines": c["code_lines"],
            "read": c.get("read"),
            "cost": c.get("effort_cost"),
            "minutes": c.get("minutes"),
            "cost_x": by_key["cost"].get("per_commit", {}).get(c["sha"]),
            "time_x": by_key["time"].get("per_commit", {}).get(c["sha"]),
        }
        for c in agent
    ]
    for i in indices:
        i.pop("per_commit", None)
        i.pop("series", None)
    return {"commits": rows[:300], "series": series, "indices": indices, "window": window, "measured": len(measured)}


def repo_skills(repo: Path) -> list[str]:
    bases = [repo / ".claude/skills", repo / ".agents/skills"]
    folders = {p.parent.name for b in bases for p in b.glob("*/SKILL.md")}
    notes = {p.stem for b in bases for p in b.glob("*.md") if p.name.lower() not in ("readme.md", "skill.md")}  # skills/<name>.md
    return sorted(folders | notes)


def report(source: str, root: Path | None = None, skill_facts: dict | None = None) -> dict:
    """The agent-use tab of one local project: one aspect, laid out like the others."""
    d = log_dir(source, root)
    repo = Path(source)
    if d is None or not repo.is_dir():
        if is_remote(source):
            return {"available": False, "upload": True, "reason": "Add the Claude Code sessions of this project to see how the agent works on it."}
        return {"available": False, "reason": "No Claude Code sessions were found for this folder."}
    author = git_author(repo)
    r = report_from([parse_session(f) for f in d.glob("*.jsonl")], git_commits(repo, author), repo_skills(repo), logs=str(d), skill_facts=skill_facts)
    r["summary"]["author"] = author
    return r


AREAS: tuple[dict, ...] = (  # the cycle of one task, with the practice from Anthropic's Claude Code best practices
    {
        "id": "gather",
        "name": "Gather context",
        "practice": "Tell Claude what it can't see",
        "checks": ("agent.friction",),
        "related": ("ai.instructions_quality",),
    },
    {
        "id": "action",
        "name": "Take action",
        "practice": "Keep each session focused",
        "checks": ("agent.cost_in_work", "agent.cost_reread", "agent.lean_context", "agent.cost_no_commit"),
        "related": (),
    },
    {
        "id": "verify",
        "name": "Verify work",
        "practice": "Give Claude a check to run",
        "checks": ("agent.tests",),
        "related": ("test.ci",),
    },
    {
        "id": "commit",
        "name": "Commit",
        "practice": "Enforce what can't have exceptions",
        "checks": ("agent.small_commits", "agent.lands", "agent.attributed"),
        "related": ("rev.via_pr", "ai.guardrails"),
    },
    {
        "id": "capture",
        "name": "Capture",
        "practice": "Put team procedures in skills",
        "checks": ("agent.skills_used",),
        "related": ("sk.descriptions",),
    },
)


def by_area(checks_: list[dict]) -> tuple[list[dict], list[dict]]:
    """The checks in the order of the cycle, each naming its area, and what each area has in place. Scores do not change."""
    by_id = {c["id"]: c for c in checks_}
    grouped, areas = [], []
    for a in AREAS:
        mine = [{**by_id[i], "area": a["id"]} for i in a["checks"] if i in by_id]
        grouped += mine
        assessed = [c for c in mine if c["status"] in ("pass", "partial", "fail")]
        areas.append(
            {
                "id": a["id"],
                "name": a["name"],
                "practice": a["practice"],
                "related": list(a["related"]),
                "in_place": len([c for c in assessed if c["status"] == "pass"]),
                "assessed": len(assessed),
            }
        )
    return grouped, areas


def report_from(sessions: list[dict], commits: list[dict], skills: list[str], logs: str = "", skill_facts: dict | None = None) -> dict:
    """The tab from the numbers of the sessions and the commits of the repository (git_commits); with the facts of the
    run's skills (skill_review.facts), the verdict of each skill, refined by the sessions."""
    sessions = sorted((s for s in sessions if s["api_calls"]), key=lambda s: s["start"] or "")
    _link(sessions, commits)
    own = [c for c in commits if not c["merge"]]
    costed = {s["id"] for s in sessions if s["cost"] is not None}
    total = sum(s["cost"] or 0 for s in sessions)
    paid = [c for c in own if c.get("session") in costed]
    tl = timeline(sessions, commits)
    split = money(sessions, commits, tl)
    cs = money_checks(split) + checks(sessions, commits, skills)
    scored = [c["score"] for c in cs if c["score"] is not None]
    score = round(100 * sum(scored) / len(scored), 1) if scored else None
    start = next((c["id"] for c in cs if c["status"] in ("fail", "partial")), None)  # the biggest loss comes first here
    grouped, areas = by_area(cs)
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
        "logs": logs,
        "summary": summary,
        "aspect": {
            "id": "agent",
            "name": "Claude Code efficiency",
            "description": "How Claude Code works on this project: the numbers of its sessions (no prompts, no code) "
            "and the git history. Other agents are not read.",
            "score": score,
            "uncapped_score": score,
            "grade": grade(score),
            "band": band(score),
            "capped_by": [],
            "adjust": 0,
            "review_notes": [],
            "checks": grouped,
            "areas": areas,
            "start": start,
        },
        "timeline": tl,
        "money": split,
        "sessions": sessions[::-1],
        "commits": commits[:200],
        "skill_verdicts": skill_review.verdicts(skill_facts, sessions),
    }


# ---------- sessions kept in a run folder: sent by the browser, or by `sdlc.py attach-sessions` ----------
_TOK = ("input", "output", "cache_read", "cache_write")
_COUNTS = ("prompts", "api_calls", "tool_calls", "tool_errors", "denied", "subagents")
_DAY = ("hours", "tool_calls", "tool_errors", "denied", "output_tokens", "read_tokens")
_ID = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _num(v: object, cap: float = 1e15) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 or v > cap:
        raise ValueError("sessions: a number is out of range")
    return v


def _iso(v: object) -> str | None:
    if v is None:
        return None
    t = _ts(v) if isinstance(v, str) else None
    if t is None or t.tzinfo is None:
        raise ValueError("sessions: a time is not ISO 8601 with a zone")
    return t.isoformat()


def clean_sessions(raw: object) -> list[dict]:
    """The numbers of sessions as parse_session makes them, checked field by field: anything else is refused, so
    nothing but numbers, times and skill names is ever kept (raises ValueError)."""
    if not isinstance(raw, list) or len(raw) > MAX_SESSIONS:
        raise ValueError(f"sessions: a list of at most {MAX_SESSIONS}")
    out = []
    for s in raw:
        if not isinstance(s, dict) or not isinstance(s.get("id"), str) or not _ID.match(s["id"]):
            raise ValueError("sessions: a session without a proper id")
        by_day, skills, at = s.get("by_day") or {}, s.get("skills") or {}, s.get("at") or {}
        skill_errors = s.get("skill_errors") or {}
        if (
            not isinstance(by_day, dict)
            or len(by_day) > 400
            or not isinstance(skills, dict)
            or len(skills) > 200
            or not isinstance(skill_errors, dict)
            or len(skill_errors) > 200
            or not isinstance(at, dict)
        ):
            raise ValueError("sessions: unexpected shape")
        reads = s.get("reads") or []
        if not isinstance(reads, list) or len(reads) > 200_000 or any(not isinstance(r, (list, tuple)) or len(r) != 2 for r in reads):
            raise ValueError("sessions: unexpected reads")
        lists = {k: at.get(k) or [] for k in ("prompts", "calls", "errors")}
        if any(not isinstance(v, list) or len(v) > 200_000 for v in lists.values()):
            raise ValueError("sessions: unexpected times")
        cost = s.get("cost")
        out.append(
            {
                "id": s["id"],
                "start": _iso(s.get("start")),
                "end": _iso(s.get("end")),
                "active_hours": _num(s.get("active_hours", 0), 1e5),
                "by_day": {
                    d: {k: _num(v.get(k, 0)) for k in _DAY}
                    for d, v in by_day.items()
                    if isinstance(d, str) and _DATE.match(d) and isinstance(v, dict)
                },
                "span_hours": _num(s.get("span_hours", 0), 1e6),
                "tokens": {k: int(_num((s.get("tokens") or {}).get(k, 0))) for k in _TOK},
                "context_per_call": _num(s.get("context_per_call", 0)),
                "cost": None if cost is None else _num(cost, 1e7),
                "skills": {str(k)[:80]: int(_num(v, 1e7)) for k, v in skills.items()},
                "skill_errors": {str(k)[:80]: int(_num(v, 1e7)) for k, v in skill_errors.items()},
                "reads": sorted([_num(a, 1e11), int(_num(b))] for a, b in reads),
                "at": {k: sorted(_num(x, 1e11) for x in v) for k, v in lists.items()},
                **{k: int(_num(s.get(k, 0), 1e9)) for k in _COUNTS},
            }
        )
    return out


def attach(run_dir: Path, sessions: list[dict], repo: Path, origin: str) -> dict:
    """Keep the numbers of the sessions in the run, with the commits and skills of the repository they are joined with
    (so showing them later needs no clone). origin: "upload" (from a browser) or "seed" (by the maintainers)."""
    data = {
        "origin": origin,
        "attached": datetime.now().astimezone().isoformat(timespec="seconds"),
        "sessions": clean_sessions(sessions),
        "commits": git_commits(repo),
        "skills": repo_skills(repo),
    }
    (run_dir / SESSIONS_FILE).write_text(json.dumps(data), encoding="utf-8")
    return data


def stored(run_dir: Path) -> dict | None:
    """The tab from the sessions kept in the run, or None when there are none."""
    f = run_dir / SESSIONS_FILE
    if not f.is_file():
        return None
    data = json.loads(f.read_text(encoding="utf-8"))
    rep = run_dir / "report.json"
    facts = json.loads(rep.read_text(encoding="utf-8")).get("skill_facts") if rep.is_file() else None
    r = report_from(data["sessions"], data["commits"], data.get("skills", []), skill_facts=facts)
    return {**r, "origin": data.get("origin"), "attached": data.get("attached")}


# ---------- where the money went: every dollar in one place, each place explained ----------
def _k(tokens: float) -> str:
    return f"{tokens / 1000:,.0f}k"


def _date(iso: str | None) -> str:
    t = _ts(iso)
    return t.astimezone().strftime("%d %b") if t else "?"


def money(sessions: list[dict], commits: list[dict], tl: dict) -> dict | None:
    """The recorded cost split three ways, each dollar counted once:
    - sessions that ended without a commit: all of their cost;
    - re-reading a long conversation: in the other sessions, what each step read beyond what a step reads in a short
      session of this project, priced as reads from the cache, as a share of the session's cost (WEIGHT: an estimate);
    - the rest went into the commits.
    Every part says what is wrong, where (the sessions), and what to do. The template only draws it."""
    costed = [s for s in sessions if s["cost"] is not None and s["api_calls"]]
    total = sum(s["cost"] for s in costed)
    if not costed or total <= 0:
        return None
    short = [s["context_per_call"] for s in costed if s["active_hours"] < 1 and s["api_calls"] >= 5]
    base = round(statistics.median(short)) if short else FRESH_CONTEXT

    idle = sorted((s for s in costed if not s.get("commits")), key=lambda s: -s["cost"])
    idle_cost = sum(s["cost"] for s in idle)

    long_items = []
    for s in costed:
        reads = [r for _, r in s.get("reads", [])]
        if not s.get("commits") or not sum(reads):
            continue
        units = sum(WEIGHT[k] * s["tokens"].get(k, 0) for k in WEIGHT)
        extra = s["cost"] * WEIGHT["cache_read"] * sum(max(0, r - base) for r in reads) / units if units else 0.0
        if extra >= 0.02 * total:  # a few cents are not worth a line
            long_items.append({**s, "extra": extra})
    long_items.sort(key=lambda s: -s["extra"])
    long_cost = sum(s["extra"] for s in long_items)
    useful = total - idle_cost - long_cost

    def pct(v: float) -> int:
        return round(100 * v / total)

    parts = [
        {
            "id": "work",
            "title": "Work that went into commits",
            "amount": round(useful, 2),
            "share": pct(useful),
        }
    ]
    if long_items:
        top = long_items[0]
        parts.append(
            {
                "id": "context",
                "title": "Re-reading long conversations",
                "amount": round(long_cost, 2),
                "share": pct(long_cost),
                "what": "Each step of a session sends the whole conversation so far to the model again. The longer a session runs, "
                f"the more every step costs. On this project a step in a short session reads about {_k(base)} tokens; in the "
                f"longest one it read {_k(top['context_per_call'])} on average, so most of its cost went on reading the same "
                "conversation again and again rather than on the changes.",
                "where": [
                    f"{_date(s['start'])}: {s['active_hours']:.1f} active hours, {s['commits']} commit{'s' if s['commits'] != 1 else ''}, "
                    f"{s['api_calls']} steps of {_k(s['context_per_call'])} tokens; "
                    f"cost ${s['cost']:.2f}, of which about ${s['extra']:.2f} on re-reading"
                    for s in long_items[:3]
                ],
                "fix": "One task, one session. After a commit, start a new session (or /clear) for the next task instead of going on "
                "in the same one. If a task has to go on, /compact first. Keep long logs and files out of the conversation: "
                "ask for the lines that matter.",
                "rule": "agent.lean_context",
            }
        )
    if idle:
        parts.append(
            {
                "id": "idle",
                "title": "Sessions without a commit",
                "amount": round(idle_cost, 2),
                "share": pct(idle_cost),
                "what": f"{len(idle)} of {len(costed)} sessions left nothing in the repository: questions, exploration, or work that "
                "was dropped. A question is fine; work that is not committed is paid for and lost.",
                "where": [f"{_date(s['start'])}: {s['active_hours']:.1f} active hours, {s['api_calls']} steps, ${s['cost']:.2f}" for s in idle[:3]],
                "fix": "End a piece of work with a commit, even a small one. If a session is only for questions or exploration, "
                "say so in the first prompt and keep it short.",
                "rule": "agent.lands",
            }
        )

    # the dearest changes, with how they compare to a change of their size, and the session they were made in
    by_sha = {c["sha"]: c.get("session") for c in commits}
    long_ids = {s["id"] for s in long_items}
    dear = sorted((c for c in tl.get("commits", []) if c.get("cost") is not None), key=lambda c: -c["cost"])[:3]
    changes = [
        {
            "subject": c["subject"],
            "sha": c["sha"],
            "cost": c["cost"],
            "times": c.get("cost_x"),
            "why": (f"{c['cost_x']:.1f}× a usual change of its size" if c.get("cost_x") else "no usual change to compare with")
            + ("; made in a long session" if by_sha.get(c["sha"]) in long_ids else ""),
        }
        for c in dear
    ]
    waste = long_cost + idle_cost
    headline = (
        f"Of ${total:.2f} at API prices, about ${useful:.2f} ({pct(useful)}%) went into the changes themselves"
        + (f", about ${long_cost:.2f} ({pct(long_cost)}%) on re-reading long conversations" if long_items else "")
        + (f", ${idle_cost:.2f} ({pct(idle_cost)}%) on sessions without a commit" if idle else "")
        + "."
    )
    lever = (
        "The biggest lever here: shorter sessions, one task each."
        if long_items and long_cost >= idle_cost
        else "The biggest lever here: finish work with a commit."
        if idle
        else "No big loss: the money went into the work."
    )
    losses = [p for p in parts if p["id"] != "work" and p["share"] >= 5]
    big = max(losses, key=lambda p: p["amount"]) if losses else None
    return {
        "total": round(total, 2),
        "lead": f"about {big['share']}% of it went on {big['title'][0].lower() + big['title'][1:]}" if big else "",
        "base_context": base,
        "headline": headline,
        "lever": lever if waste >= 0.05 * total else "No big loss: the money went into the work.",
        "parts": parts,
        "changes": changes,
        "note": "Cost at API prices as Claude Code records it. The split is an estimate: what a step read beyond a step of a short "
        f"session (about {_k(base)} tokens here) is priced as reading from the cache, at the usual ratio of Claude prices.",
    }


def money_checks(m: dict | None) -> list[dict]:
    """Where the money went, as three checks of the aspect: Expected, Found, What to do, like the others."""
    ids = (
        ("agent.cost_in_work", "Most of the money goes into the changes."),
        ("agent.cost_reread", "Little money goes on re-reading long conversations."),
        ("agent.cost_no_commit", "Little money goes on sessions without a commit."),
    )
    how = "The cost Claude Code records for each session (at API prices), the tokens each step read, and the commits."
    if m is None:
        accepted = (
            f"At least {COST_IN_WORK[0]:.0%} of the cost at API prices goes into the work that ends in commits.",
            f"No more than {COST_REREAD[0]:.0%} of the cost goes on what steps read beyond a step of a short session.",
            f"No more than {COST_NO_COMMIT[0]:.0%} of the cost goes on sessions that leave no commit.",
        )
        return [
            _check(cid, title, "na", ["no session with a recorded cost"], "", acc, how, "Where the money of AI-assisted work goes.")
            for (cid, title), acc in zip(ids, accepted, strict=True)
        ]
    total, by = m["total"], {p["id"]: p for p in m["parts"]}
    work, reread, idle = by.get("work"), by.get("context"), by.get("idle")

    def dollars(part: dict | None, words: str) -> str:
        return f"{round(part['amount'] if part else 0)}/{round(total)} dollars {words}"

    def share(part: dict | None) -> float:
        return part["amount"] / total if part else 0.0

    split = ", ".join(f"{p['title'].lower()} ${p['amount']:.2f} ({p['share']}%)" for p in m["parts"])
    dear = [f"dearest change: {c['subject']} · ${c['cost']:.2f} · {c['why']}" for c in m["changes"][:2]]
    estimate = m["note"]
    out = [
        _check(
            *ids[0],
            _level(share(work), *COST_IN_WORK),
            [dollars(work, "of the cost went into the work that ended in commits"), f"split: {split}", *dear],
            "Start with the biggest loss: "
            + (max((p for p in (reread, idle) if p), key=lambda p: p["amount"])["title"].lower() if reread or idle else "none")
            + ". The two checks below say where it is and what to do.",
            f"At least {COST_IN_WORK[0]:.0%} of the cost at API prices goes into the work that ends in commits.",
            how,
            "The cost of a change is the price of AI-assisted work; what does not reach a commit is paid for and lost.",
            estimate,
        )
    ]
    reread_ev = [dollars(reread, "of the cost went on re-reading long conversations")]
    if reread:
        reread_ev.append(f"tokens read per step: about {_k(m['base_context'])} in a short session of this project")
        reread_ev += [f"session of {w.split(':', 1)[0]}: {w.split(':', 1)[1].strip().replace('; ', ', ')}" for w in reread["where"]]
    out.append(
        _check(
            *ids[1],
            _level(share(reread), *COST_REREAD, higher_is_better=False),
            reread_ev,
            reread["fix"] if reread else "",
            f"No more than {COST_REREAD[0]:.0%} of the cost goes on what steps read beyond a step of a short session of this project.",
            how,
            "Each step sends the whole conversation so far to the model again: the longer a session runs, the more every step "
            "costs, and most of it pays for reading the same conversation again rather than for the changes.",
            estimate,
        )
    )
    idle_ev = [dollars(idle, "of the cost went on sessions without a commit")]
    if idle:
        idle_ev += [f"session of {w.split(':', 1)[0]}: {w.split(':', 1)[1].strip()}" for w in idle["where"]]
    out.append(
        _check(
            *ids[2],
            _level(share(idle), *COST_NO_COMMIT, higher_is_better=False),
            idle_ev,
            idle["fix"] if idle else "",
            f"No more than {COST_NO_COMMIT[0]:.0%} of the cost goes on sessions that leave no commit.",
            how,
            "A question is fine; work that is not committed is paid for and lost.",
        )
    )
    return out
