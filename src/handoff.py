"""Hand a finding to a coding agent: one prompt per open check or skill verdict of a run, built from the run alone.

The prompt carries Expected, Found and What to do as the report states them, so the agent working in the assessed
repository needs neither the report nor SDLC360. It first checks the finding against the code (the scanner reads
files, not intent, and can be wrong), then makes one small change, one commit, and says how to re-check it.
Which findings come first is decided here; the app only shows the text.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import agent_usage, hosting

OPEN = ("fail", "partial")
SKILL_FIRST = ("broken", "behind")  # a skill that sends the agent to files that are gone is worse than no skill: first
SKILL_LATER = ("idle",)
SKILL_PREFIX = "skill:"


def skill_verdicts(run_dir: Path, report: dict) -> dict | None:
    """The skill verdicts as the app shows them: refined by the sessions kept in the run or, for a local folder, by its
    Claude Code sessions (never on the hosted app: those would be the server's own)."""
    kept = agent_usage.stored(run_dir)
    if kept and kept.get("skill_verdicts"):
        return kept["skill_verdicts"]
    source = report["repo"]["source"]
    if not hosting.cloud() and not hosting.is_remote(source):
        tab = agent_usage.report(source, skill_facts=report.get("skill_facts"))
        if tab.get("available") and tab.get("skill_verdicts"):
            return tab["skill_verdicts"]
    return report.get("skill_verdicts")


def _checks(report: dict) -> dict[str, tuple[dict, dict]]:
    return {c["id"]: (d, c) for d in report["dimensions"] for c in d["checks"]}


def findings(report: dict, verdicts: dict | None = None) -> list[dict]:
    """Every finding worth a prompt, in the order to fix them: broken or behind skills, the ranked actions of the report,
    then idle skills. Each is {id, kind, title, status}."""
    skills = (verdicts or {}).get("skills") or []
    first = [s for s in skills if s["verdict"] in SKILL_FIRST]
    later = [s for s in skills if s["verdict"] in SKILL_LATER]
    as_item = lambda s: {"id": SKILL_PREFIX + s["name"], "kind": "skill", "title": f"{s['title']}: {s['name']}", "status": s["verdict"]}  # noqa: E731
    ranked = [{"id": a["check_id"], "kind": "check", "title": a["check"], "status": a["status"]} for a in report.get("top_actions", [])]
    return [as_item(s) for s in first] + ranked + [as_item(s) for s in later]


def _head(report: dict) -> str:
    repo = report["repo"]
    h = repo.get("head") or {}
    at = f" at commit {h['sha'][:8]}" if h.get("sha") else ""
    return f"SDLC360 assessed this repository ({repo['source']}{at}, {str(report.get('generated_at', ''))[:10]})."


def _rescan(report: dict) -> str:
    return f"python sdlc.py scan {report['repo']['source']} --no-history"


STEPS = """Steps:
1. Check the finding against the code first. SDLC360 reads files, not intent, and can be wrong. If the finding does
   not hold, stop and say why, quoting the files; change nothing.
2. Make the smallest change that meets Expected. Follow this repository's AGENTS.md / CLAUDE.md for commits,
   permissions and tests. One finding is one commit.
3. Run the project's tests; they must stay green.
4. Report what changed, the commit, and how to re-check: {rescan} (run from SDLC360) should show {fid} as {done}."""


def check_prompt(report: dict, cid: str) -> str:
    d, c = _checks(report)[cid]
    m = c.get("method") or {}
    found = "\n".join(f"- {e}" for e in c.get("evidence") or []) or "- nothing found"
    todo = "\n".join(f"  - {t}" for t in c.get("todo") or [])
    unseen = " ".join(x for x in (m.get("limits"), m.get("known_gap")) if x)
    parts = [
        _head(report),
        f"Fix exactly one finding: {cid} ({d['name']}), now {'not met' if c['status'] == 'fail' else 'partially met'}"
        + (", critical" if c.get("priority") == "critical" else "")
        + ".",
        f"Expected: {c['title']}" + (f"\nAccepted when: {m['accepted']}" if m.get("accepted") else ""),
        f"Found:\n{found}",
        f"What to do: {c.get('recommendation') or ''}" + (f"\n{todo}" if todo else ""),
    ]
    if m.get("looks_at"):
        parts.append(f"How SDLC360 checks it: {m['looks_at']}" + (f"\nWhat it cannot see: {unseen}" if unseen else ""))
    parts.append(STEPS.format(rescan=_rescan(report), fid=cid, done="Met"))
    return "\n\n".join(parts)


def skill_prompt(report: dict, s: dict) -> str:
    why = "\n".join(f"- {w}" for w in s.get("why") or [])
    notes = "\n".join(f"- {n}" for n in s.get("notes") or [])
    parts = [
        _head(report),
        f"Fix exactly one finding: the skill {s['name']} ({s['path']}) is judged {s['title'].lower()} ({s.get('basis', 'code and git')}).",
        "Expected: every file the skill names exists, its steps match the code, and the agent uses it without failures.",
        f"Found:\n{why}" + (f"\nNotes:\n{notes}" if notes else ""),
        f"What to do: {s['do']}",
    ]
    parts.append(STEPS.format(rescan=_rescan(report), fid=f"the skill {s['name']}", done="Up to date"))
    return "\n\n".join(parts)


def prompt(report: dict, fid: str, verdicts: dict | None = None) -> str:
    """The prompt for one finding: a check id (`hyg.lint`) or `skill:<name>`. KeyError when the run has no such finding."""
    if fid.startswith(SKILL_PREFIX):
        name = fid[len(SKILL_PREFIX) :]
        s = next((x for x in (verdicts or {}).get("skills") or [] if x["name"] == name), None)
        if s is None:
            raise KeyError(fid)
        return skill_prompt(report, s)
    checks = _checks(report)
    if fid not in checks or checks[fid][1].get("status") not in OPEN:
        raise KeyError(fid)
    return check_prompt(report, fid)


def handoff(run_dir: Path, fid: str | None = None, top: int = 5) -> str:
    """The prompt for one finding, or for the first `top` findings, separated by a line of dashes."""
    report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    verdicts = skill_verdicts(run_dir, report)
    ids = [fid] if fid else [f["id"] for f in findings(report, verdicts)[:top]]
    return "\n\n-----\n\n".join(prompt(report, i, verdicts) for i in ids)
