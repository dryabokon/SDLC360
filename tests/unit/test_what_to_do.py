"""What to do: the habit in plain words for every check, the first step for this project, its platform and its items."""

import subprocess

from src import agent_usage
from src.acceptance import criteria
from src.repo import Repo
from src.scanner import PREREQUISITE, finalize


def _checks(module, root):
    return {c.id: c for c in module.assess(Repo(root))}


def test_every_check_has_a_short_habit():
    """The habit opens What to do, also when the check is met: one plain sentence, no thresholds."""
    for cid, block in criteria().items():
        habit = block.get("habit", "")
        assert habit and len(habit) <= 130 and "{" not in habit, cid
    ids = {c["id"] for c in agent_usage.money_checks(None)} | set(agent_usage.HABITS)
    assert all(agent_usage.HABITS.get(i) for i in ids)


def test_prerequisites_name_real_checks():
    assert set(PREREQUISITE) | set(PREREQUISITE.values()) <= set(criteria())


def _report(present: float, pr: float) -> dict:
    checks = [
        {"id": "ci.present", "title": "CI", "weight": 3, "score": present, "evidence": [], "recommendation": "add CI"},
        {"id": "ci.pr", "title": "PR", "weight": 2, "score": pr, "evidence": [], "recommendation": ""},
    ]
    items = {
        "cicd": [
            {"id": "ci.present", "text": "CI runs", "priority": "critical", "weight": 5.0, "custom": False},
            {"id": "ci.pr", "text": "CI gates", "priority": "important", "weight": 3.0, "custom": False},
        ]
    }
    return {"repo": {"source": "t"}, "checklist": {"items": items}, "dimensions": [{"id": "cicd", "name": "CI/CD", "auto_checks": checks}]}


def _by_id(rep: dict) -> dict:
    return {c["id"]: c for d in rep["dimensions"] for c in d["checks"]}


def test_a_check_waiting_for_another_says_first():
    by = _by_id(finalize(_report(0.0, 0.0)))
    assert by["ci.pr"]["blocked_by"] == "ci.present" and by["ci.present"]["blocked_by"] == ""
    again = _by_id(finalize(finalize(_report(1.0, 0.0))))
    assert again["ci.pr"]["blocked_by"] == ""  # CI exists: its own step applies


def test_steps_say_how_many_are_left_and_name_them(make_repo):
    from src.dimensions import documentation

    root = make_repo({"README.md": "# x\n\n## Install\n\nSee [the guide](docs/gone.md) and `src/missing.py`.\n", "app.py": ""})
    c = _checks(documentation, root)
    sec = c["doc.readme_sections"]
    assert (
        sec.recommendation.startswith("Add the 5 missing topics to the README")
        and "how to use it" in sec.recommendation
        and "how to run the tests" in sec.recommendation
    )
    links = c["doc.links"]
    assert links.todo == ["README.md -> docs/gone.md", "README.md -> src/missing.py"] and "the 2 links" in links.recommendation
    files = c["doc.standard_files"]
    assert files.recommendation.startswith("Add LICENSE, CONTRIBUTING, CHANGELOG")


def test_met_check_keeps_no_steps(make_repo):
    from src.dimensions import documentation

    c = _checks(documentation, make_repo({"README.md": "# x\n", "LICENSE": "", "CONTRIBUTING.md": "", "CHANGELOG.md": ""}))
    assert c["doc.standard_files"].status == "pass" and c["doc.standard_files"].recommendation == ""


def test_gitlab_project_gets_gitlab_steps(make_repo):
    from src.dimensions import cicd, hygiene, security, tests

    root = make_repo({"app.py": "", "tests/test_app.py": "", ".gitlab-ci.yml": "test:\n  script:\n    - pytest\n"}, name="gl")
    ci = _checks(cicd, root)
    assert ci["ci.present"].score is None and ci["ci.pr"].score is None  # GitLab CI is not read yet: not judged, not failed
    assert _checks(tests, root)["test.ci"].score == 1.0  # but its test step is seen
    assert "merge_request_templates" in _checks(hygiene, root)["hyg.templates"].recommendation
    sec = _checks(security, root)
    assert "Renovate" in sec["sec.dep_updates"].recommendation and ".gitlab/" in sec["sec.codeowners"].recommendation


def test_remote_decides_the_platform(make_repo):
    from src.dimensions import hygiene

    root = make_repo({"app.py": ""}, name="local")
    assert ".github/" in _checks(hygiene, root)["hyg.templates"].recommendation
    subprocess.run(["git", "remote", "add", "origin", "https://gitlab.example.com/g/r.git"], cwd=root, check=True)
    assert ".gitlab/" in _checks(hygiene, root)["hyg.templates"].recommendation


def test_claude_md_in_dot_claude_is_the_root_instruction_file(make_repo):
    """Claude Code reads ./CLAUDE.md or ./.claude/CLAUDE.md: either one is the project's briefing."""
    from src.dimensions import harness

    c = _checks(harness, make_repo({".claude/CLAUDE.md": "# Build\n\nRun `make test`.\n", "app.py": ""}))
    assert c["ai.instructions"].score == 1.0 and "(.claude/CLAUDE.md)" in c["ai.instructions_quality"].title


def test_steps_name_the_tool_of_the_language(make_repo):
    from src.dimensions import hygiene

    py = _checks(hygiene, make_repo({"a.py": "x = 1\n", "b.py": ""}, name="py"))
    assert "ruff" in py["hyg.lint"].recommendation and "ruff format" in py["hyg.format"].recommendation
    js = _checks(hygiene, make_repo({"a.ts": "export const x = 1\n"}, name="js"))
    assert "ESLint" in js["hyg.lint"].recommendation and "Prettier" in js["hyg.format"].recommendation
