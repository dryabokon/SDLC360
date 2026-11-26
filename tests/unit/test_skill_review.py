"""Skill verdicts: one per skill, from the code and git history, refined by the numbers of Claude Code sessions."""

from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src import skill_review
from src.repo import Repo
from tests.conftest import GIT

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)


class History:
    """A throw-away repository written commit by commit, each at a chosen date."""

    def __init__(self, root: Path):
        self.root = root
        root.mkdir()
        self.git("init", "-q", "-b", "main")

    def git(self, *args: str, when: datetime = NOW) -> None:
        env = {**os.environ, "GIT_AUTHOR_DATE": when.isoformat(), "GIT_COMMITTER_DATE": when.isoformat()}
        subprocess.run([*GIT, *args], cwd=self.root, check=True, capture_output=True, env=env)

    def commit(
        self, msg: str, when: datetime, write: dict[str, str] | None = None, rm: tuple[str, ...] = (), mv: tuple[tuple[str, str], ...] = ()
    ) -> None:
        for rel, text in (write or {}).items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8", newline="\n")
        for rel in rm:
            self.git("rm", "-q", rel)
        for a, b in mv:
            (self.root / b).parent.mkdir(parents=True, exist_ok=True)
            self.git("mv", a, b)
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", msg, when=when)

    def verdicts(self, sessions: list[dict] | None = None) -> dict:
        v = skill_review.verdicts(skill_review.facts(Repo(self.root)), sessions)
        assert v is not None
        return v


def skill(body: str, name: str = "deploy") -> str:
    return f"---\nname: {name}\ndescription: Deploy the app. Use when asked to deploy.\n---\n\n{body}\n"


def one(v: dict, name: str = "deploy") -> dict:
    return next(s for s in v["skills"] if s["name"] == name)


@pytest.fixture
def hist(tmp_path) -> History:
    return History(tmp_path / "repo")


def work(h: History, n: int = 3) -> None:
    """Commits in the area of the skill after its last edit: what "up to date" stands on."""
    for i in range(n):
        h.commit(f"work {i}", NOW - timedelta(days=7 - i), {"src/app.py": f"a = {i}\n"})


def busy(h: History, start: datetime, n: int = 25) -> None:
    """Work elsewhere in the repository, so a quiet area of a skill means something."""
    for i in range(n):
        h.commit(f"other work {i}", start + timedelta(days=i), {f"other/f{i}.py": f"x = {i}\n"})


def test_broken_when_git_deleted_what_it_names(hist):
    hist.commit("app", NOW - timedelta(days=30), {"src/deploy.py": "run()\n", ".claude/skills/deploy/SKILL.md": skill("Run `src/deploy.py`.")})
    hist.commit("drop the old deploy script", NOW - timedelta(days=10), rm=("src/deploy.py",))
    s = one(hist.verdicts())
    assert s["verdict"] == "broken"
    assert "src/deploy.py" in s["why"][0] and "drop the old deploy script" in s["why"][0]


def test_a_path_the_repository_never_had_is_a_note_not_broken(hist):
    """Regression: outputs, placeholders and other repositories' files are not 'gone' (pydantic-ai, a client repository)."""
    hist.commit(
        "app",
        NOW - timedelta(days=30),
        {"src/app.py": "a = 1\n", ".claude/skills/deploy/SKILL.md": skill("Edit `src/app.py`, write `out/report.md`, see `path/to/file.py`.")},
    )
    work(hist)
    s = one(hist.verdicts())
    assert s["verdict"] == "current"
    assert any("not in the repository" in n and "out/report.md" in n for n in s["notes"])


def test_behind_when_files_of_its_area_are_deleted_or_moved_after_its_last_edit(hist):
    hist.commit(
        "app",
        NOW - timedelta(days=60),
        {"src/pkg/a.py": "", "src/pkg/b.py": "", "src/pkg/c.py": "", ".claude/skills/deploy/SKILL.md": skill("Work in `src/pkg/`.")},
    )
    hist.commit("move a", NOW - timedelta(days=20), mv=(("src/pkg/a.py", "src/pkg/core/a.py"),))
    hist.commit("drop b", NOW - timedelta(days=15), rm=("src/pkg/b.py",))
    hist.commit("drop c", NOW - timedelta(days=10), rm=("src/pkg/c.py",))
    s = one(hist.verdicts())
    assert s["verdict"] == "behind"
    assert s["why"][0].startswith("3 commits deleted or moved files of its area")


def test_new_files_in_its_area_do_not_make_it_behind(hist):
    """Regression: a busy folder gains files all the time; that does not change a procedure (pydantic-ai docs-parity)."""
    hist.commit("app", NOW - timedelta(days=60), {"src/pkg/a.py": "", ".claude/skills/deploy/SKILL.md": skill("Work in `src/pkg/`.")})
    for i in range(5):
        hist.commit(f"add {i}", NOW - timedelta(days=20 - i), {f"src/pkg/n{i}.py": ""})
    assert one(hist.verdicts())["verdict"] == "current"


def test_idle_when_its_area_is_quiet_for_half_a_year_in_a_busy_repository(hist):
    hist.commit("app", NOW - timedelta(days=400), {"legacy/run.py": "", ".claude/skills/deploy/SKILL.md": skill("Run `legacy/run.py`.")})
    busy(hist, NOW - timedelta(days=100))
    s = one(hist.verdicts())
    assert s["verdict"] == "idle" and "180 days" in s["why"][0]


def test_a_young_repository_is_too_young_to_call_a_skill_idle(hist):
    """Regression: a client repository's history started a month earlier; a quiet area there is no evidence."""
    hist.commit("app", NOW - timedelta(days=40), {"legacy/run.py": "", ".claude/skills/deploy/SKILL.md": skill("Run `legacy/run.py`.")})
    busy(hist, NOW - timedelta(days=30))
    s = one(hist.verdicts())
    assert s["verdict"] == "current" and s["why"] == ["the file it names exists today, unchanged after its last edit on 2026-10-11"]


def test_unknown_when_it_names_no_file_of_the_project(hist):
    hist.commit(
        "app",
        NOW - timedelta(days=10),
        {
            ".claude/skills/deploy/SKILL.md": skill("Be careful. See `.claude/skills/other/SKILL.md`."),
            ".claude/skills/other/SKILL.md": skill("x", name="other"),
        },
    )
    assert one(hist.verdicts())["verdict"] == "unknown"  # another skill is no code area


def test_copies_are_one_skill_and_shipped_skills_are_not_judged(hist):
    body = skill("Run `src/app.py`.")
    hist.commit(
        "app",
        NOW - timedelta(days=10),
        {
            "src/app.py": "",
            ".claude/skills/deploy/SKILL.md": body,
            ".cursor/skills/deploy/SKILL.md": body,
            "pkg/.agents/skills/tour/SKILL.md": skill("x", "tour"),
        },
    )
    work(hist)
    v = hist.verdicts()
    assert [s["name"] for s in v["skills"]] == ["deploy"]
    assert any(n.startswith("also kept in .cursor/skills/deploy/SKILL.md") for n in v["skills"][0]["notes"])
    assert v["shipped"] == ["pkg/.agents/skills/tour/SKILL.md"]


def _sessions(uses: dict[str, int], errors: dict[str, int] | None = None, n: int = 3, step: int = 3) -> list[dict]:
    """n sessions, the newest today, one every `step` days."""
    out = [{"id": f"s{i}", "start": (NOW - timedelta(days=i * step)).isoformat(), "skills": {}, "skill_errors": {}} for i in range(n)]
    out[0]["skills"], out[0]["skill_errors"] = uses, errors or {}
    return out


@pytest.fixture
def live(hist) -> History:
    hist.commit("app", NOW - timedelta(days=30), {"src/app.py": "", ".claude/skills/deploy/SKILL.md": skill("Run `src/app.py`.")})
    work(hist)
    return hist


def test_sessions_idle_when_the_work_goes_on_without_it(live):
    s = one(live.verdicts(_sessions({"other": 4})))  # sessions over 6 days, the area changed 5 days ago
    assert s["verdict"] == "idle" and s["basis"] == "code, git and sessions"
    assert "not used in 3 sessions" in s["why"][0] and "2 commits changed its area" in s["why"][1]


def test_sessions_idle_when_unused_over_two_weeks(live):
    assert one(live.verdicts(_sessions({}, n=4, step=6)))["verdict"] == "idle"  # 18 days, no use


def test_a_few_days_of_sessions_without_its_work_do_not_make_it_idle(live):
    """Regression: 3 sessions over 3 days built something else; its skills are not idle for that."""
    v = live.verdicts(_sessions({}, step=1))  # 2 days, the area last changed 5 days ago
    assert one(v)["verdict"] == "current"
    assert "no skill of the project was used in them" in v["basis_note"]  # said once, not under each skill


def test_sessions_broken_when_calls_after_it_fail(live):
    s = one(live.verdicts(_sessions({"plugin:deploy": 3}, {"deploy": 4})))
    assert s["verdict"] == "broken" and "failed in the 10 calls after a use" in s["why"][0]


def test_sessions_confirm_a_working_skill(live):
    s = one(live.verdicts(_sessions({"deploy": 5}, {"deploy": 1})))
    assert s["verdict"] == "current" and s["why"][0].startswith("used 5 times in 3 sessions")


def test_too_few_sessions_leave_use_unjudged(live):
    v = live.verdicts(_sessions({}, n=2))
    s = one(v)
    assert s["verdict"] == "current" and v["basis"] == "code and git"
    assert "2 Claude Code sessions" in v["basis_note"] and "too few" in v["basis_note"]


def test_up_to_date_shows_its_proof_and_numbers(hist):
    """The proof is what it names exists and what changed since did not take it away; the numbers are the table's columns."""
    hist.commit("app", NOW - timedelta(days=30), {"src/app.py": "", ".claude/skills/deploy/SKILL.md": skill("Run `src/app.py`.")})
    hist.commit("work", NOW - timedelta(days=5), {"src/app.py": "a = 1\n"})
    v = hist.verdicts()
    s = one(v)
    assert s["verdict"] == "current"
    assert s["why"] == ["the file it names exists today", "1 commit changed them after its last edit on 2026-10-21; none deleted or moved its files"]
    assert s["metrics"] == {"files": 1, "gone": 0, "changes": 1, "removed": 0, "days": 25, "lines": 6, "scripts": 0, "uses": None, "errors": None}
    assert [c[0] for c in v["columns"]] == ["files", "gone", "changes", "removed", "days", "scripts", "lines"]  # no sessions, no use columns


def test_a_broad_area_is_noted_not_hidden(hist):
    """openai-agents' docs-sync names `src/agents`, 60% of the commits: the proof still holds; the breadth is said."""
    hist.commit("app", NOW - timedelta(days=60), {"src/pkg/a.py": "", ".claude/skills/deploy/SKILL.md": skill("Sync docs with `src/pkg/`.")})
    for i in range(25):
        hist.commit(f"src {i}", NOW - timedelta(days=50 - i), {f"src/pkg/f{i}.py": ""})
    s = one(hist.verdicts())
    assert s["verdict"] == "current" and any(n.startswith("broad area: 25 of the repository's 26") for n in s["notes"])


def test_a_procedure_naming_no_file_is_left_to_the_sessions(hist):
    hist.commit("app", NOW - timedelta(days=10), {".claude/skills/deploy/SKILL.md": skill("Plan first, then code, then review.")})
    s = one(hist.verdicts())
    assert s["verdict"] == "unknown" and s["title"] == "Procedure" and "only the sessions can check it" in s["why"][0]
    assert s["do"].startswith("Add Claude Code sessions")  # not "rewrite it for the tool"


def test_no_skills_no_verdicts(make_repo):
    assert skill_review.facts(Repo(make_repo({"a.py": ""}))) is None
    assert skill_review.verdicts(None) is None
