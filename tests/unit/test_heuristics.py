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


def test_path_scoped_claude_rules_are_scoped_context(make_repo):
    """`.claude/rules/` with `paths:` is the way the acceptance text quotes: it must count, a rule without it must not."""
    from src.dimensions.harness import assess

    big = {f"pkg{i // 50}/m{i}.py": "x = 1\n" for i in range(310)} | {"CLAUDE.md": "# x"}
    scoped = '---\npaths:\n  - "pkg0/**/*.py"\n---\nUse the pkg0 logger.\n'
    always = "---\ndescription: style\n---\nNo prints.\n"

    def score(files, name):
        return {c.id: c.score for c in assess(Repo(make_repo(big | files, name=name)))}["ai.scoped_context"]

    assert score({".claude/rules/pkg0.md": scoped}, "scoped") == 1.0
    assert score({".claude/rules/style.md": always}, "always") == 0.3  # loads always: not scoped
    assert score({}, "none") == 0.3


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


# ---- found by a blind review of a client data-migration repository (2026-11-11) ----


def _ids(module, root):
    return {c.id: c for c in module.assess(Repo(root))}


def test_a_path_into_a_dot_folder_is_not_broken(make_repo):
    root = make_repo({".claude/CLAUDE.md": "See `.cursor/mcp.json` and [rules](.github/x.md).\n", ".cursor/mcp.json": "{}", ".github/x.md": ""})
    assert broken_refs(Repo(root), ".claude/CLAUDE.md") == (2, [])


def test_a_generated_design_md_deep_in_the_tree_is_not_the_architecture_doc(make_repo):
    from src.dimensions import architecture

    deep = make_repo({"work/products/a/spec/design.md": "# design", "app.py": ""}, name="deep")
    assert _ids(architecture, deep)["arch.doc"].score == 0.0
    top = make_repo({"docs/architecture.md": "# arch", "app.py": ""}, name="top")
    assert _ids(architecture, top)["arch.doc"].score == 1.0


def test_build_commands_must_be_written_as_commands(make_repo):
    from src.dimensions import harness

    prose = "# Guide\n\nThe build phase produces artifacts. Always test the output; never skip a rule.\n" + "More text.\n" * 30
    c = _ids(harness, make_repo({"CLAUDE.md": prose}, name="prose"))["ai.instructions_quality"]
    assert "commands" not in c.evidence[1]
    c = _ids(harness, make_repo({"CLAUDE.md": prose + "\nRun `make test` before a commit.\n"}, name="cmd"))["ai.instructions_quality"]
    assert "commands" in c.evidence[1]


def test_hooks_that_only_track_are_not_guardrails(make_repo):
    import json

    from src.dimensions import harness

    def settings(cmd):
        return json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": cmd}]}]}})

    track = make_repo({".claude/settings.json": settings("python3 scripts/tokenization/tracker.py")}, name="track")
    assert _ids(harness, track)["ai.guardrails"].status == "fail"
    fmt = make_repo({".claude/settings.json": settings("bash .claude/hooks/format.sh")}, name="fmt")
    assert _ids(harness, fmt)["ai.guardrails"].status == "pass"


def test_a_vendored_linter_config_is_not_the_projects(make_repo):
    from src.dimensions import hygiene

    vend = make_repo({".claude/skills/linter/scripts/configs/ruff.toml": "", ".tool/configs/ruff.toml": "", "app.py": ""}, name="vend")
    assert _ids(hygiene, vend)["hyg.lint"].score == 0.0
    own = make_repo({"ruff.toml": "", "app.py": ""}, name="own")
    assert _ids(hygiene, own)["hyg.lint"].score == 1.0


def test_tests_named_by_what_they_check_count_as_a_layer(make_repo):
    from src.dimensions import tests

    root = make_repo({"app.py": "", "tests/test_app.py": "", "tests/post_build/t01_structure.py": "", "tests/reconcile.py": ""})
    assert _ids(tests, root)["test.layers"].status == "partial"


def test_a_docs_folder_of_a_package_counts(make_repo):
    from src.dimensions import documentation

    pages = {f"app/docs/p{i}.md": "# p" for i in range(6)} | {".claude/skills/x/docs/a.md": "", "README.md": "# x"}
    c = _ids(documentation, make_repo(pages))["doc.docs_dir"]
    assert c.evidence[0].startswith("6 doc pages") and c.score >= 0.85


def test_azure_devops_pull_request_merges_count(make_repo):
    from src.dimensions.review import assess

    root = make_repo({"README.md": "x\n"}, name="azure-prs")
    _commits(root, [(f"Merged PR {600 + i}: fix the camera assignment", 1) for i in range(12)] + [("direct push", 1)] * 2)
    assert "12 of the last 15" in {c.id: c for c in assess(Repo(root))}["rev.via_pr"].evidence[0]


def test_unittest_is_a_test_framework(make_repo):
    from src.dimensions import tests

    ut = "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n"
    root = make_repo({"app.py": "", "tests/framework/test_app.py": ut}, name="ut")
    c = _ids(tests, root)["test.framework"]
    assert c.status == "pass" and "unittest" in c.evidence[0]
    bare = make_repo({"app.py": "", "tests/test_app.py": "def test_x():\n    assert True\n"}, name="bare")
    assert _ids(tests, bare)["test.framework"].status == "fail"  # pytest-style tests with no config: still not configured


def test_azure_pipelines_with_any_name_are_read(make_repo):
    from src.dimensions import cicd, tests

    yml = "trigger: [main]\nsteps:\n  - script: python -m unittest discover -s tests\n"
    root = make_repo({"app.py": "", "tests/test_app.py": "", "azure-pipelines-flight-smoke.yml": yml}, name="azure")
    assert _ids(tests, root)["test.ci"].status == "pass"  # the pipeline runs the tests
    present = _ids(cicd, root)["ci.present"]
    assert present.score is None and "azure-pipelines-flight-smoke.yml" in present.evidence[0]  # another CI: not judged, not failed


def test_azure_pipelines_in_a_folder_and_their_templates_are_read(make_repo):
    # Control Center / FireFly layout: no file named azure-pipelines*, tests and scanners run only in an included template.
    from src.dimensions import harness, security, tests
    from src.dimensions._util import forge

    pr = "pr:\n  branches:\n    include: [main]\nstages:\n  - template: templates/dotnet-build-test.yml\n"
    tmpl = (
        "steps:\n  - task: DotNetCoreCLI@2\n    inputs:\n      command: 'restore'\n"
        "  - script: dotnet list src/App.csproj package --vulnerable --include-transitive\n"
        "  - task: DotNetCoreCLI@2\n    displayName: Test\n    inputs:\n      command: 'test'\n      projects: tests/**/*.csproj\n"
        "  - task: Gitleaks@3\n"
    )
    review = "trigger: none\npr: none\nsteps:\n  - script: echo '##vso[build.updatebuildnumber]AI Review'\n"
    files = {
        "src/App.cs": "",
        "tests/AppTests.cs": "",
        ".azure/pipelines/pr-review-linux.yml": pr,
        ".azure/pipelines/templates/dotnet-build-test.yml": tmpl,
        ".azure/pipelines/ai-reviewer.yml": review,
    }
    root = make_repo(files, name="azure-folder")
    repo = Repo(root)
    assert forge(repo) == "azure" and ".azure/pipelines/templates/dotnet-build-test.yml" in repo.other_ci
    assert _ids(tests, root)["test.ci"].status == "pass"  # DotNetCoreCLI test task in the template
    scan = _ids(security, root)["sec.ci_scanning"]
    assert scan.status == "pass" and "gitleaks" in scan.evidence[0] and "package --vulnerable" in scan.evidence[0]
    assert _ids(harness, root)["ai.ci_agents"].status == "pass"  # an AI review pipeline, not only claude-code-action

    # a restore task followed by an unrelated "command: test" elsewhere is not a test run
    restore = "steps:\n  - task: DotNetCoreCLI@2\n    inputs:\n      command: 'restore'\n  - task: Bash@3\n"
    bare = make_repo({"src/App.cs": "", "tests/AppTests.cs": "", ".azure/pipelines/ci.yml": restore}, name="azure-restore")
    assert _ids(tests, bare)["test.ci"].status != "pass"


def test_a_feature_spec_is_not_the_architecture_document(make_repo):
    # Fly repos: superpowers specs named *-design.md were taken as THE architecture doc; the real one in documentation/ was missed.
    from src.dimensions import architecture

    specs = {
        "app.py": "",
        "docs/superpowers/specs/2026-09-03-runtime-amd64-pipeline-design.md": "# Pipeline design\n",
        "docs/plans/2026-10-01-main-viewmodel-design.md": "# Plan\n",
    }
    checks = _ids(architecture, make_repo(specs, name="specs-only"))
    assert checks["arch.doc"].status == "fail" and checks["arch.fresh"].status == "fail"

    real = make_repo({**specs, "documentation/architecture/overview.md": "# Architecture\n"}, name="documentation-dir")
    doc = _ids(architecture, real)["arch.doc"]
    assert doc.status == "pass" and doc.evidence == ["documentation/architecture/overview.md"]


def test_steps_name_the_platform_the_project_lives_on(make_repo):
    from src.dimensions import review
    from src.dimensions._util import forge
    from tests.conftest import _git

    def steps(root, override=None):
        repo = Repo(root)
        repo.forge = override
        return forge(repo), {c.id: c for c in review.assess(repo)}["rev.via_pr"].recommendation

    azure = make_repo({"app.py": ""}, name="on-azure")
    _git(azure, "remote", "add", "origin", "https://acme@dev.azure.com/acme/Proj/_git/app")
    f, step = steps(azure)
    assert f == "azure" and "Branch policies" in step and "Settings" not in step
    gh = make_repo({"app.py": ""}, name="on-github")
    _git(gh, "remote", "add", "origin", "git@github.com:acme/app.git")
    assert steps(gh)[0] == "github" and "Settings → Branches" in steps(gh)[1]
    pipelines = make_repo({"app.py": "", "azure-pipelines-smoke.yml": "steps: []\n"}, name="no-remote")
    assert steps(pipelines)[0] == "azure"  # no remote: the CI files tell
    assert steps(azure, "github")[0] == "github"  # --forge for a mirror on two platforms
    assert steps(make_repo({"app.py": ""}, name="plain"))[0] == "github"


def test_an_azure_pull_request_template_is_enough_there(make_repo):
    from src.dimensions import hygiene
    from tests.conftest import _git

    root = make_repo({"app.py": "", ".azuredevops/pull_request_template.md": "- [ ] tests\n"}, name="azure-tmpl")
    _git(root, "remote", "add", "origin", "https://dev.azure.com/acme/Proj/_git/app")
    assert _ids(hygiene, root)["hyg.templates"].score == 1.0  # Azure Repos keeps no issue templates in the repository


def test_credential_files_are_judged_by_what_they_hold(make_repo):
    from src.dimensions import security

    flight = "# flight parameters\nORIGIN_LAT=50.45\nPN_V_MAX=12\nCLS_NAMES=drone,plane\nAUTH_MODE=oauth\nMAX_TOKENS=4000\n"
    cert = "-----BEGIN " + "CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n"
    config = make_repo({"infra/.env": flight, "tools/emu/.env": "MEDIAMTX_RTSP_PORT=8554\n", "ca.pem": cert, ".env.example": "API_TOKEN=\n"})
    c = _ids(security, config)["sec.no_sensitive_files"]
    assert c.status == "pass" and "configuration" in c.evidence[0] and "infra/.env" in c.evidence[0]  # the Fly2-agent case

    def verdict(files, name):
        return _ids(security, make_repo(files, name=name))["sec.no_sensitive_files"]

    assert verdict({".env": "DB_PASSWORD=admin1\n"}, "pw").status == "fail"
    assert verdict({".env": f"GH={GH}\n"}, "token").status == "fail"  # a known token format under any name
    assert verdict({".env": "DATABASE_URL=postgres://app:s3cr3t@db:5432/app\n"}, "url").status == "fail"
    assert verdict({".env": "PASSWORD=changeme\nAPI_KEY=${API_KEY}\nSECRET=\n"}, "ph").status == "pass"  # placeholders
    key = "-----BEGIN " + "RSA PRIVATE KEY-----\nMIIE\n-----END RSA PRIVATE KEY-----\n"
    assert verdict({"deploy.key": key}, "key").status == "fail"
    assert verdict({"prod.tfstate": "{}"}, "state").status == "fail"  # state holds secrets by its kind
    fails = verdict({".env": "DB_PASSWORD=admin1\nPORT=80\n"}, "masked")
    assert "DB_PASSWORD" in fails.evidence[0] and "admin1" not in " ".join(fails.evidence)  # names, never values
