"""One verdict per skill of the project, with its evidence (prototype).

A skill is tied to its area: the files and folders of the project its SKILL.md points at (links and backticked paths,
outside the skill's own folder). The code and the git history of that area say whether the skill still fits; the
Claude Code sessions, when there are any, say whether the agent uses it and how that goes.

Verdicts, checked in this order, the first that applies is the answer, so each skill gets exactly one:
- broken:  points at files git deleted or moved; or, in the sessions, the calls right after it fail;
- behind:  nothing it names is gone, but files of its area were deleted or moved after its last edit;
- idle:    no work in its area and no use; or, in the sessions, the work went on without it;
- current: every file it names exists and what changed since its last edit did not take its files away; with
           sessions, it is used and holds. It says the skill still fits the code, not that it makes the agent better;
- unknown: a procedure that names no file of the project: only the sessions can check it.

facts() runs once at scan time (it reads git); verdicts() turns the facts (and the numbers of the sessions) into
verdicts, so re-rendering a run never reads the repository again. Thresholds live here; the template only shows them.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import PurePosixPath

from .dimensions._util import frontmatter, normalize_path, resolve_refs
from .repo import Repo, run_git

WINDOW_DAYS = 180  # "recent": the last half year of the repository, up to its last commit
BEHIND_COMMITS = 3  # commits that deleted or moved files of the skill's area after its last edit: "behind"
MIN_REPO_RECENT = 20  # a quiet area means something only when the repository itself was busy meanwhile
MIN_SESSIONS = 3  # sessions needed to judge use at all
MIN_SPAN_DAYS = 14  # without work in its area meanwhile, sessions must cover this long to call an unused skill idle
ERRORS_PER_USE = 1.0  # failed tool calls in the 10 calls after a use, on average, that make a skill "broken"
MIN_USES = 3
WIDE_SHARE = 0.25  # an area with this share of the repository's recent commits is the project, not the skill's area
WIDE_FILES = 20
MAX_COMMITS = 3000
FIX = re.compile(r"^(fix|hotfix|bugfix|revert)\b|\b(fix(es|ed)?|bug|regression|revert)\b", re.I)
TOOLING = re.compile(r"/(scripts|assets|templates?|references)/|\.(py|sh|js|ts|ps1|json|ya?ml|toml|j2|tmpl)$", re.I)

# the project's own skills live in a dot-folder at the root; a SKILL.md elsewhere ships with the product (a package,
# an example, a test fixture) and is not a procedure for working on this repository
SKILLS_DIR = re.compile(r"(^|/)skills(/|$)")
PROJECT_SKILL = re.compile(r"^\.(claude|agents|cursor|github|codex|gemini|windsurf)/")
# a plain markdown file right in a project skills folder (.agents/skills/secrets.md): a note the agent reads when AGENTS.md
# or a prompt sends it there. It has no SKILL.md, so no description picks it, but it is judged like a skill all the same
NOTE = re.compile(r"^\.(claude|agents|cursor|github|codex|gemini|windsurf)/skills/(?!readme\.md$|skill\.md$)[^/]+\.md$", re.I)
NOTE_HINT = (
    "a plain note, not a SKILL.md: the agent reads it only when AGENTS.md or a prompt sends it there; "
    "as <name>/SKILL.md with a description it is picked by itself"
)
TITLES = {"broken": "Broken", "behind": "Behind the code", "idle": "Idle", "current": "Up to date", "unknown": "Procedure"}
ADVICE = {
    "broken": "Fix the skill first: it sends the agent to files that are gone, which is worse than no skill.",
    "behind": "Bring the skill up to date with its area: read the commits listed and change the steps that no longer hold.",
    "idle": "Delete the skill, or, if the work it covers still happens, rewrite its description in the words people use, so the agent picks it.",
    "current": "Keep it. Add a script or a check at the end, so the agent does the same steps every time.",
    "current_tooled": "Keep it: steps with a script are the shape to copy for the next recurring task.",
    "process": "Add Claude Code sessions: only they show whether the agent uses it and how that goes.",
    "more_sessions": f"Judge it again when the sessions cover {MIN_SPAN_DAYS} days or more: unused by then, it is idle.",
}
RULES = {
    "broken": "It points at files git deleted or moved, or the calls right after it fail (sessions).",
    "behind": f"Nothing it names is gone, but {BEHIND_COMMITS} or more commits deleted or moved files of its area after it was last edited.",
    "idle": f"No commit in its area for {WINDOW_DAYS} days and no use; or no use in {MIN_SESSIONS} or more sessions while its area "
    f"changed, or over {MIN_SPAN_DAYS} days or more.",
    "current": f"Every file it names exists and fewer than {BEHIND_COMMITS} commits deleted or moved files of its area since its last "
    "edit; or the sessions use it without failures. It fits the code; whether it helps, only sessions tell.",
    "unknown": "It names no file of the project: a procedure (plan, review, write-up). The code cannot check it; the sessions can.",
}
SHIPPED = "Skills outside the dot-folders at the root ship with the product (a package, an example, a test) and are not judged here."
COLUMNS = [  # (metric, header, what it counts): the table of the tab
    ("files", "Files named", "files and folders of the project its SKILL.md names, all of which exist unless 'Gone' says otherwise"),
    ("gone", "Gone", "files it names that git deleted or moved: the agent is sent to nothing"),
    ("changes", "Changes since edit", "commits that changed the files it names after the skill was last edited"),
    ("removed", "Removed since edit", f"of those, commits that deleted or moved its files ({BEHIND_COMMITS} or more: behind)"),
    ("days", "Days since edit", "days from the skill's last edit to the repository's last commit"),
    ("scripts", "Scripts", "scripts, templates and references next to SKILL.md: steps the agent runs, not only reads"),
    ("lines", "Lines", "lines of SKILL.md"),
    ("uses", "Uses", "times the agent used it in the sessions (the Skill tool, its scripts or its files; a note: reading it)"),
    ("errors", "Errors after", "failed tool calls in the 10 calls after a use"),
]
ORDER = {"broken": 0, "behind": 1, "idle": 2, "current": 3, "unknown": 4}


def _n(k: int, word: str) -> str:
    return f"{k} {word}{'' if k == 1 else 's'}"


def _log(root) -> list[dict]:
    """Commits of HEAD, newest first, merges left out: sha, date, subject, the paths it touched (files), the paths it
    deleted or renamed (moved: both names of a rename) and the paths it deleted or renamed away (gone)."""
    raw = run_git(root, "log", f"-n{MAX_COMMITS}", "--no-merges", "-M", "--format=%x1e%H%x1f%cI%x1f%s", "--name-status", check=False)
    out = []
    for rec in raw.split("\x1e")[1:]:
        head, _, names = rec.partition("\n")
        parts = head.split("\x1f")
        if len(parts) < 3:
            continue
        files: list[str] = []
        moved: list[str] = []
        gone: list[str] = []
        for ln in names.splitlines():
            cols = ln.split("\t")
            if len(cols) < 2:
                continue
            st, paths = cols[0][:1], cols[1:]
            files += paths
            if st in ("D", "R"):
                moved += paths
            if st in ("D", "R"):
                gone.append(paths[0])
        out.append({"sha": parts[0], "date": parts[1], "subject": parts[2], "files": files, "moved": moved, "gone": gone})
    return out


def _under(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip("/") + "/")


def _when(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def _brief(c: dict) -> str:
    s = c["subject"]
    return f"{c['sha'][:8]} {c['date'][:10]} “{s if len(s) <= 70 else s[:67] + '…'}”"


def _gone(ref: str, folder: str, commits: list[dict]) -> dict | None:
    """The commit that deleted or moved away what a ref that resolves to nothing pointed at, if git ever had it."""
    r = ref.rstrip("/")
    cands = {normalize_path(str(PurePosixPath(folder, r))), normalize_path(re.sub(r"^(\./)+", "", r))} - {""}
    suffix = "/" + normalize_path(r).lower()
    relative = "/" in r and not r.startswith(".")
    for c in commits:  # newest first: the latest deletion
        for g in c["gone"]:
            if g in cands or any(g.startswith(x + "/") for x in cands) or (relative and g.lower().endswith(suffix)):
                return c
    return None


def facts(repo: Repo) -> dict | None:
    """What the code and git say about each skill (SKILL.md) of the repository. None when it has none. A skill kept in
    several places (.claude/skills, .agents/skills, .cursor/skills) is one skill: its copies are named."""
    every = sorted(repo.find("SKILL.md"), key=lambda f: (not f.startswith(".claude/"), not f.startswith(".agents/"), f))
    files = [f for f in every if PROJECT_SKILL.match(f)] + sorted(f for f in repo.files if NOTE.match(f))
    if not files and not every:
        return None
    commits = _log(repo.root) if repo.is_git else []
    head = _when(commits[0]["date"]) if commits else None
    since = head - timedelta(days=WINDOW_DAYS) if head else None
    old_enough = bool(commits) and (len(commits) >= MAX_COMMITS or _when(commits[-1]["date"]) <= since)  # type: ignore[operator]
    recent_repo = sum(1 for c in commits if since and _when(c["date"]) >= since)
    out: list[dict] = []
    seen: dict[str, dict] = {}
    for f in files:
        note = bool(NOTE.match(f))
        folder = f if note else str(PurePosixPath(f).parent)  # a note is its own folder: the commits that touch it are its edits
        key = PurePosixPath(f).stem if note else PurePosixPath(folder).name
        if key in seen:
            seen[key]["copies"].append(f)
            continue
        text = repo.read(f)
        fm = frontmatter(text) or {}
        found, unresolved = resolve_refs(repo, f)
        gone = [(r, c) for r in unresolved if (c := _gone(r, folder, commits))]
        area = sorted({p for p in found if not _under(p, folder) and not SKILLS_DIR.search(p)})  # other skills are no code area
        own = [c for c in commits if any(_under(x, folder) for x in c["files"])]
        last_edit, created = (own[0], own[-1]) if own else (None, None)
        in_area = [c for c in commits if c not in own and any(_under(x, a) for x in c["files"] for a in area)]
        after = [c for c in in_area if last_edit and _when(c["date"]) > _when(last_edit["date"])]
        moved = [c for c in after if any(_under(x, a) for x in c["moved"] for a in area)]
        born = _when(created["date"]) if created else None
        before = [c for c in in_area if born and _when(c["date"]) < born]
        later = [c for c in in_area if born and _when(c["date"]) >= born]
        item = {
            "name": fm.get("name") or key,
            "folder": key,
            "path": f,
            "note": note,
            "copies": [],
            "lines": len(text.splitlines()),
            "tooling": sorted(x for x in repo.files if _under(x, folder) and x != f and TOOLING.search(x))[:5],
            "area": area[:20],
            "area_size": len(area),
            "gone": [f"{r} (gone in {_brief(c)})" for r, c in gone][:5],
            "missing": [r for r in unresolved if r not in {g for g, _ in gone}][:10],
            "created": created["date"] if created else None,
            "last_edit": last_edit["date"] if last_edit else None,
            "area_commits": len(in_area),
            "after_edit": len(after),
            "moved_after_edit": len(moved),
            "moved_examples": [_brief(c) for c in moved[:3]],
            "moved_files": sorted({x for c in moved for x in c["moved"] if any(_under(x, a) for a in area)})[:5],
            "recent": sum(1 for c in in_area if since and _when(c["date"]) >= since),
            "area_dates": [c["date"] for c in in_area if since and _when(c["date"]) >= since][:1000],  # to compare with the sessions
            "fixes_before": sum(1 for c in before if FIX.search(c["subject"])),
            "fixes_after": sum(1 for c in later if FIX.search(c["subject"])),
            "commits_before": len(before),
            "commits_after": len(later),
        }
        seen[key] = item
        out.append(item)
    return {
        "window_days": WINDOW_DAYS,
        "head": commits[0]["date"] if commits else None,
        "repo_recent": recent_repo,
        "old_enough": old_enough,
        "skills": out,
        "shipped": [f for f in every if not PROJECT_SKILL.match(f)][:50],
    }


def _bare(name: str) -> str:
    return name.rsplit(":", 1)[-1]  # "plugin:skill" -> "skill"


def usage(sessions: list[dict]) -> dict:
    """How often each skill was used in the sessions, and how many calls failed right after a use."""
    uses: dict[str, int] = {}
    errors: dict[str, int] = {}
    for s in sessions:
        for k, v in (s.get("skills") or {}).items():
            uses[_bare(k)] = uses.get(_bare(k), 0) + v
        for k, v in (s.get("skill_errors") or {}).items():
            errors[_bare(k)] = errors.get(_bare(k), 0) + v
    starts = sorted(s["start"] for s in sessions if s.get("start"))
    ends = sorted(s.get("end") or s["start"] for s in sessions if s.get("start"))
    return {"sessions": len(sessions), "first": starts[0] if starts else None, "last": ends[-1] if ends else None, "uses": uses, "errors": errors}


def _period(u: dict | None) -> str:
    if not u or not u["first"] or not u["last"]:
        return ""
    a, b = u["first"][:10], u["last"][:10]
    return f" ({a})" if a == b else f" ({a} – {b})"


def _one(f: dict, fx: dict, u: dict | None) -> dict:
    with_sessions = bool(u and u["sessions"] >= MIN_SESSIONS)
    names = {f["folder"], f["name"]}
    n = sum((u or {}).get("uses", {}).get(k, 0) for k in names)
    err = sum((u or {}).get("errors", {}).get(k, 0) for k in names)
    since = f"after its last edit on {f['last_edit'][:10]}" if f["last_edit"] else "since it was added"
    calls = f"used {_n(n, 'time')} in {_n(u['sessions'], 'session')}" if u else ""
    period = _period(u)
    during = 0
    span = 0.0
    if u and u["first"] and u["last"]:
        a, b = _when(u["first"]), _when(u["last"]) + timedelta(days=1)
        during = sum(1 for d in f.get("area_dates", []) if a <= _when(d) <= b)
        span = (b - a).total_seconds() / 86400 - 1
    share = f["recent"] / fx["repo_recent"] if fx["repo_recent"] else 0.0
    wide = bool(f["area"]) and (f["area_size"] > WIDE_FILES or (f["recent"] >= MIN_REPO_RECENT and share >= WIDE_SHARE))
    k = f["area_size"]
    exist = "the file it names exists" if k == 1 else f"all {k} files it names exist"
    v, why, do = "unknown", [], ""
    if f["gone"]:
        v, why = "broken", ["points at what git deleted or moved: " + "; ".join(f["gone"][:3])]
    elif with_sessions and n >= MIN_USES and err / n >= ERRORS_PER_USE:
        v, why = "broken", [f"{calls}; {_n(err, 'tool call')} failed in the 10 calls after a use ({err / n:.1f} per use)"]
    elif f["moved_after_edit"] >= BEHIND_COMMITS:
        v = "behind"
        why = [f"{_n(f['moved_after_edit'], 'commit')} deleted or moved files of its area {since}", *f["moved_examples"]]
        if f["moved_files"]:
            why.append("files deleted or moved: " + ", ".join(f["moved_files"]))
    elif u and with_sessions and n == 0 and (during or span >= MIN_SPAN_DAYS):
        v = "idle"
        why = [f"not used in {_n(u['sessions'], 'session')}{period}"]
        if during:
            why.append(f"meanwhile {_n(during, 'commit')} changed its area: the work went on without it")
    elif f["area"] and not wide and not f["recent"] and fx["old_enough"] and fx["repo_recent"] >= MIN_REPO_RECENT and n == 0:
        v, why = "idle", [f"no commit touched its area in the last {WINDOW_DAYS} days, while the repository had {fx['repo_recent']}"]
    elif with_sessions and n:
        v, why = "current", [f"{calls}{period}, {_n(err, 'failed call')} right after"]
    elif f["area"]:  # the proof: what it names is there, and what changed since did not take it away
        v = "current"
        if f["after_edit"]:
            moved = f"{f['moved_after_edit']} of them deleted or moved its files" if f["moved_after_edit"] else "none deleted or moved its files"
            why = [f"{exist} today", f"{_n(f['after_edit'], 'commit')} changed them {since}; {moved}"]
        else:
            why = [f"{exist} today, unchanged {since}"]
    else:
        why = [f"{'the note' if f.get('note') else 'its SKILL.md'} names no file of the project: a procedure, so only the sessions can check it"]
        do = ADVICE["more_sessions"] if with_sessions else ADVICE["process"]
    if v == "current":
        do = ADVICE["current_tooled"] if f["tooling"] else ADVICE["current"]
    notes = [NOTE_HINT] if f.get("note") else []
    if wide:
        notes.append(f"broad area: {f['recent']} of the repository's {fx['repo_recent']} recent commits touch it")
    if f["area"]:
        notes.append(f"judged by: {', '.join(f['area'][:4])}" + (f" and {f['area_size'] - 4} more" if f["area_size"] > 4 else ""))
    if f["missing"]:
        k = len(f["missing"])
        notes.append(
            f"{_n(k, 'path')} it names {'is' if k == 1 else 'are'} not in the repository (outputs or placeholders), "
            f"not judged: {', '.join(f['missing'][:3])}"
        )
    if f["copies"]:
        notes.append("also kept in " + ", ".join(f["copies"]))
    head, edit = fx.get("head"), f["last_edit"]
    metrics = {  # the numbers behind the verdict, one column each in the table
        "files": f["area_size"],
        "gone": len(f["gone"]),
        "changes": f["after_edit"],
        "removed": f["moved_after_edit"],
        "days": (_when(head) - _when(edit)).days if head and edit else None,
        "lines": f["lines"],
        "scripts": len(f["tooling"]),
        "uses": n if with_sessions else None,
        "errors": err if with_sessions else None,
    }
    return {
        "name": f["name"],
        "path": f["path"],
        "metrics": metrics,
        "verdict": v,
        "title": TITLES[v],
        "why": why,
        "notes": notes,
        "do": do or ADVICE[v],
        "basis": "code, git and sessions" if with_sessions else "code and git",
    }


def _basis(u: dict | None, fx: dict) -> str:
    """One line on what the verdicts stand on: said once, not under every skill."""
    if not u:
        return "Judged by the code and git history. Add Claude Code sessions to see whether the agent uses each skill and how that goes."
    period = _period(u)
    if u["sessions"] < MIN_SESSIONS:
        return (
            f"Judged by the code and git history; {_n(u['sessions'], 'Claude Code session')}{period}: "
            f"too few to judge use ({MIN_SESSIONS} are needed)."
        )
    names = {k for f in fx["skills"] for k in (f["folder"], f["name"])}
    used = sorted((k, v) for k, v in u["uses"].items() if k in names)
    said = "used: " + ", ".join(f"{k} ×{v}" for k, v in used) if used else "no skill of the project was used in them"
    return f"Judged by the code, git history and {_n(u['sessions'], 'Claude Code session')}{period}; {said}."


def verdicts(fx: dict | None, sessions: list[dict] | None = None) -> dict | None:
    """The verdict of each skill, worst first, with how many got each; sessions refine them when given."""
    if not fx:
        return None
    u = usage(sessions) if sessions else None
    items = sorted((_one(f, fx, u) for f in fx["skills"]), key=lambda x: (ORDER[x["verdict"]], x["name"]))
    return {
        "skills": items,
        "order": list(ORDER),
        "columns": COLUMNS if u and u["sessions"] >= MIN_SESSIONS else [c for c in COLUMNS if c[0] not in ("uses", "errors")],
        "counts": {k: sum(1 for x in items if x["verdict"] == k) for k in ORDER},
        "basis": "code, git and sessions" if u and u["sessions"] >= MIN_SESSIONS else "code and git",
        "basis_note": _basis(u, fx),
        "sessions": u["sessions"] if u else 0,
        "shipped": fx.get("shipped", []),
        "titles": TITLES,
        "rules": RULES,
        "shipped_note": SHIPPED,
    }
