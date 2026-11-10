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
import math
import random
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
# lines of source and docs: what it takes to change them is the measure; data files (gt.txt, .onnx, .json) are not
CODE = re.compile(r"\.(py|pyi|js|jsx|ts|tsx|html|css|sh|bat|ps1|go|rs|cs|cpp|cc|c|h|hpp|java|kt|sql|toml|ya?ml|md)$", re.I)
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
                    if b.get("name") == "Skill":
                        name = str((b.get("input") or {}).get("skill") or "?")
                        skills[name] = skills.get(name, 0) + 1
        elif e.get("type") == "user" and not e.get("isMeta"):
            if isinstance(content, str) and not content.startswith("<"):
                n["prompts"] += 1
                if t:
                    at["prompts"].append(t.timestamp())
            for b in content if isinstance(content, list) else []:
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
        "reads": sorted(reads),
        "at": {k: sorted(v) for k, v in at.items()},
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
            "name": "Claude Code efficiency",
            "description": "How Claude Code works on this project: its session logs on this machine (read only) "
            "and the git history. Other agents are not read.",
            "score": score,
            "uncapped_score": score,
            "grade": grade(score),
            "band": band(score),
            "capped_by": [],
            "adjust": 0,
            "review_notes": [],
            "checks": cs,
        },
        "timeline": timeline(sessions, commits, repo),
        "sessions": sessions[::-1],
        "commits": commits[:200],
    }
