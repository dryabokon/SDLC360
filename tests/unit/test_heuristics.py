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
    from src.dimensions.runs import assess

    checks = {c.id: c for c in assess(Repo(make_repo({"start.sh": "#!/usr/bin/env bash\n", "app.py": ""})))}
    assert checks["run.entrypoints"].score == 1.0


def test_tag_trigger_in_flow_and_block_style(make_repo):
    from src.dimensions.cicd import assess

    for tags in ('tags: ["v*"]', "tags:\n      - 'v*'"):
        wf = f"on:\n  push:\n    {tags}\njobs:\n  r:\n    steps:\n      - run: gh release create x\n"
        checks = {c.id: c for c in assess(Repo(make_repo({".github/workflows/release.yml": wf}, name=f"r{len(tags)}")))}
        assert "tag/release trigger: True" in checks["ci.cd"].evidence


def test_pinned_requirements_variant_counts_as_lockfile(make_repo):
    from src.dimensions.runs import assess

    checks = {c.id: c for c in assess(Repo(make_repo({"requirements-dev.txt": "pytest==9.2.0\n", "app.py": ""})))}
    assert checks["run.lockfile"].score == 1.0
