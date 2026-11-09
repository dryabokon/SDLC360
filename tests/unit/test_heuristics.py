"""Known false positives found while calibrating on reference repositories must stay fixed."""

from src.dimensions._util import broken_refs, instruction_files
from src.dimensions.security import scan_secrets
from src.repo import Repo

# assembled at runtime so that secret scanners do not flag this file
AWS = "AKIA" + "Z7QW3RT5YU8IO2P4"
GH = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"


def test_detects_real_looking_tokens(make_repo):
    repo = Repo(make_repo({"app/config.py": f'AWS = "{AWS}"\nTOKEN = "{GH}"\n'}))
    assert {f["kind"] for f in scan_secrets(repo)} == {"AWS access key", "GitHub token"}


def test_ignores_placeholders_identifiers_and_fixtures(make_repo):
    repo = Repo(
        make_repo(
            {
                "app/settings.py": 'api_key = "your-api-key-goes-here-123"\nclient_secret = "oauth_client_secret_name"\n',
                "tests/fixtures/creds.py": f'KEY = "{AWS}"\n',
            }
        )
    )
    assert scan_secrets(repo) == []


def test_secret_in_tests_is_marked_as_test(make_repo):
    repo = Repo(make_repo({"tests/test_x.py": f'K = "{AWS}"\n'}))
    assert [f["in_test"] for f in scan_secrets(repo)] == [True]


def test_broken_refs_skip_urls_absolute_and_package_relative(make_repo):
    repo = Repo(
        make_repo(
            {
                "README.md": "[ok](docs/a.md) [web](https://x.y/z) `/opt/app/conf.yml` `transport/http.py` [gone](docs/missing.md) `src/nope.py`\n",
                "docs/a.md": "a",
                "src/pkg/transport/http.py": "",
            }
        )
    )
    checked, broken = broken_refs(repo, "README.md")
    assert broken == ["docs/missing.md", "src/nope.py"]
    assert checked == 4


def test_instruction_files_match_exact_basenames(make_repo):
    repo = Repo(make_repo({"AGENTS.md": "# a", "docs/elevenlabs_agents.md": "x"}))
    assert instruction_files(repo) == ["AGENTS.md"]


def test_root_start_script_is_an_entry_point(make_repo):
    from src.dimensions.reproducibility import assess

    checks = {c.id: c for c in assess(Repo(make_repo({"start.sh": "#!/usr/bin/env bash\n", "app.py": ""})))}
    assert checks["rep.entrypoints"].score == 1.0


def test_tag_trigger_in_flow_and_block_style(make_repo):
    from src.dimensions.cicd import assess

    for tags in ('tags: ["v*"]', "tags:\n      - 'v*'"):
        wf = f"on:\n  push:\n    {tags}\njobs:\n  r:\n    steps:\n      - run: gh release create x\n"
        checks = {c.id: c for c in assess(Repo(make_repo({".github/workflows/release.yml": wf}, name=f"r{len(tags)}")))}
        assert "tag/release trigger: True" in checks["ci.cd"].evidence


def test_pinned_requirements_variant_counts_as_lockfile(make_repo):
    from src.dimensions.reproducibility import assess

    checks = {c.id: c for c in assess(Repo(make_repo({"requirements-dev.txt": "pytest==9.2.0\n", "app.py": ""})))}
    assert checks["rep.lockfile"].score == 1.0


def test_reproducibility_does_not_depend_on_folder_names(make_repo):
    """A runs/ folder is a team convention; it must neither be required nor rewarded."""
    from src.dimensions.reproducibility import assess

    base = {"app.py": "", "uv.lock": "x", ".python-version": "3.12", "Dockerfile": "FROM python:3.12"}
    with_runs = {c.id: c.score for c in assess(Repo(make_repo({**base, "runs/r1/manifest.json": "{}"}, name="a")))}
    without = {c.id: c.score for c in assess(Repo(make_repo(base, name="b")))}
    assert with_runs == without


def test_unpinned_requirements_are_not_a_lockfile(make_repo):
    from src.dimensions.reproducibility import assess

    checks = {c.id: c for c in assess(Repo(make_repo({"requirements.txt": "requests>=2\npytest==9.2.0\n", "app.py": ""})))}
    assert checks["rep.lockfile"].score == 0.4


def test_one_workflow_is_enough_and_all_pr_trigger_forms_count(make_repo):
    from src.dimensions.cicd import assess

    for i, on in enumerate(("on: pull_request", "on:\n  - push\n  - pull_request", "on: [push, pull_request]", "on:\n  pull_request:\n")):
        wf = f"name: ci\n{on}\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - run: pytest\n"
        checks = {c.id: c.score for c in assess(Repo(make_repo({".github/workflows/ci.yml": wf}, name=f"w{i}")))}
        assert checks["ci.present"] == 1.0 and checks["ci.pr"] == 1.0, on


def test_personal_claude_local_md_is_not_project_instructions(make_repo):
    from src.dimensions.harness import assess

    checks = {c.id: c.score for c in assess(Repo(make_repo({"CLAUDE.local.md": "# mine", "app.py": ""})))}
    assert checks["ai.instructions"] == 0.0


def _commits(root, messages: list[tuple[str, int]]) -> None:
    """Add commits to a fixture repo: (message, number of files the commit touches)."""
    from tests.conftest import _git

    for n, (msg, files) in enumerate(messages):
        for f in range(files):
            (root / f"src_{n}_{f}.py").write_text(f"x = {n}\n", encoding="utf-8")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "--allow-empty", "-m", msg)


def test_review_counts_pull_request_marks_and_change_size(make_repo):
    from src.dimensions.review import assess

    root = make_repo({"README.md": "x\n"}, name="prs")
    _commits(root, [(f"Fix thing (#{i})", 2) for i in range(5)] + [("Merge pull request #9 from a/b", 1)] + [("direct push", 1)] * 8)
    checks = {c.id: c for c in assess(Repo(root))}
    assert "6 of the last 15" in checks["rev.via_pr"].evidence[0]  # 6 PRs, 8 pushes and the fixture commit
    assert checks["rev.via_pr"].status == "partial"  # 40% against a 60% bar
    assert checks["rev.small_changes"].score == 1.0  # median 1 file

    big = make_repo({"README.md": "x\n"}, name="big")
    _commits(big, [("Big change (#1)", 20)] * 12)
    assert {c.id: c for c in assess(Repo(big))}["rev.small_changes"].status == "partial"  # median 20 files vs 10 (partial up to ~24)


def test_review_needs_history(make_repo):
    from src.dimensions.review import assess

    checks = {c.id: c for c in assess(Repo(make_repo({"README.md": "x\n"}, name="young")))}
    assert checks["rev.via_pr"].score is None and checks["rev.small_changes"].score is None


def test_ai_policy_and_attribution(make_repo):
    from src.dimensions.review import assess

    root = make_repo({"AGENTS.md": "# Agents\n", "CONTRIBUTING.md": "# Contributing\n\n## Using AI coding agents\n\nRules.\n"}, name="ai")
    _commits(root, [("Add feature\n\nCo-Authored-By: Claude <noreply@anthropic.com>", 1)])
    checks = {c.id: c for c in assess(Repo(root))}
    assert checks["rev.ai_policy"].score == 1.0 and "CONTRIBUTING.md" in checks["rev.ai_policy"].evidence[0]
    assert checks["rev.ai_attribution"].score == 1.0

    plain = {c.id: c for c in assess(Repo(make_repo({"README.md": "x\n"}, name="noai")))}
    assert plain["rev.ai_policy"].score == 0.0 and plain["rev.ai_attribution"].score is None  # no sign of agents


def test_ai_policy_ignores_readmes_of_nested_folders(make_repo):
    """Reference cards (assessment/references/x/README.md) titled "... AI agents" are not the project's AI policy."""
    from src.dimensions.review import assess

    root = make_repo({"README.md": "# Tool\n", "assessment/references/x/README.md": "# Effective context engineering for AI agents\n"})
    assert {c.id: c for c in assess(Repo(root))}["rev.ai_policy"].score == 0.0
