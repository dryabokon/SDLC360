"""CI/CD with GitHub Actions."""

from __future__ import annotations

import re

from ..model import Checks, Dimension, short
from ..repo import Repo
from .tests import TEST_CMD

LINT = r"ruff|flake8|pylint|black --check|mypy|pyright|eslint|prettier --check|biome|golangci|clippy|cargo fmt|rustfmt|ktlint|spotless|checkstyle|dotnet format|rubocop|pre-commit run|super-linter|megalinter|actionlint|shellcheck|hadolint"
BUILD = r"\bbuild\b|docker build|docker/build-push-action|python -m build|uv build|npm run build|cargo build|go build|mvn package|gradle(w)? (build|assemble)|dotnet build|tsc\b"
DEPLOY = r"deploy|release|publish|pypa/gh-action-pypi-publish|npm publish|docker push|push:\s*true|softprops/action-gh-release|semantic-release|release-please|goreleaser|helm|kubectl|terraform apply|vercel|netlify|fly deploy|azure/webapps-deploy|aws-actions"


def assess(repo: Repo):
    c = Checks()
    wf = repo.workflows
    txt = repo.workflow_text
    other = repo.find(".gitlab-ci.yml", "Jenkinsfile", "azure-pipelines.yml", ".circleci/config.yml", "bitbucket-pipelines.yml", ".travis.yml")
    c.add(
        "ci.present",
        "GitHub Actions workflows present",
        3,
        1.0 if wf else (0.4 if other else 0.0),
        short(wf) if wf else (f"non-GitHub CI: {short(other)}" if other else "no CI configuration"),
        "Add .github/workflows/ci.yml running lint + tests on push and pull_request.",
    )
    if not wf:
        for cid, t, w in (
            ("ci.pr", "Runs on pull requests", 2),
            ("ci.stages", "Lint + test + build stages", 3),
            ("ci.cd", "Release / deploy automation", 1.5),
            ("ci.hygiene", "Workflow hygiene", 1.5),
            ("ci.pinning", "Actions pinned to commit SHA", 1),
            ("ci.speed", "Caching & concurrency", 1),
        ):
            c.add(cid, t, w, 0.0, "no workflows")
        return c.items

    pr = re.search(r"^\s*(-\s*)?(pull_request|pull_request_target|merge_group)\b\s*(:|$)", txt, re.M) or re.search(
        r"\bon:\s*(\[[^\]]*\bpull_request|pull_request\b|merge_group\b)", txt
    )
    c.add(
        "ci.pr",
        "Runs on pull requests (gate before merge)",
        2,
        bool(pr),
        "pull_request trigger found" if pr else "no pull_request trigger",
        "Trigger CI on `pull_request` and mark the checks as required in branch protection.",
    )

    stages = {"lint/typecheck": LINT, "test": TEST_CMD, "build": BUILD}
    have = [k for k, p in stages.items() if re.search(p, repo.ci_text, re.I)]  # incl. scripts the workflows delegate to
    c.add(
        "ci.stages",
        "Lint + test + build stages",
        3,
        len(have) / len(stages),
        [f"stages: {', '.join(have) or 'none'}", f"missing: {', '.join(k for k in stages if k not in have) or '-'}"],
        "Cover lint/type-check, tests and a build/package step in CI.",
    )

    cd = sorted(set(m.lower() for m in re.findall(DEPLOY, txt, re.I)))[:6]
    tags = re.search(r"\btags:\s*(\[\s*['\"]?[\w*.-]|\n\s*-\s*['\"]?[\w*.-])|\brelease:\s*\n\s*types", txt)
    c.add(
        "ci.cd",
        "Release / deploy automation (CD)",
        1.5,
        min(1.0, 0.5 * bool(cd) + 0.5 * bool(tags) + (0.5 if len(cd) > 2 else 0)),
        [f"cd keywords: {', '.join(cd) or 'none'}", f"tag/release trigger: {bool(tags)}"],
        "Automate releases (tag-triggered publish, release-please, or environment deploys with approvals).",
    )

    timeouts = len(re.findall(r"timeout-minutes", txt))
    jobs = max(1, len(re.findall(r"^\s{2}[\w-]+:\s*\n\s{4}(runs-on|uses)", txt, re.M)))
    matrix = bool(re.search(r"\bmatrix\s*:", txt))
    envs = bool(re.search(r"^\s*environment\s*:", txt, re.M))
    s = 0.4 * min(1.0, timeouts / jobs) + 0.3 * matrix + 0.3 * (envs or bool(re.search(r"workflow_dispatch", txt)))
    c.add(
        "ci.hygiene",
        "Workflow hygiene (timeouts, matrix, environments / manual dispatch)",
        1.5,
        s,
        [f"timeout-minutes on {timeouts}/{jobs} jobs", f"matrix: {matrix}", f"environments: {envs}"],
        "Set `timeout-minutes` on every job, test across a version matrix, use environments for deploys.",
    )

    uses = re.findall(r"uses:\s*['\"]?([\w.-]+/[\w./-]+)@([\w.-]+)", txt)
    third = [(a, r) for a, r in uses if not a.startswith(("actions/", "github/", "./"))]
    pinned = [a for a, r in third if re.fullmatch(r"[0-9a-f]{40}", r)]
    c.add(
        "ci.pinning",
        "Third-party actions pinned to commit SHA",
        1,
        1.0 if not third else len(pinned) / len(third),
        f"{len(pinned)}/{len(third)} third-party actions SHA-pinned" if third else "no third-party actions",
        "Pin third-party actions to full commit SHAs (Dependabot keeps them updated).",
    )

    cache = bool(
        re.search(
            r"actions/cache|cache:\s*['\"]?(pip|npm|yarn|pnpm|gradle|maven|go|poetry|uv)|enable-cache|setup-uv|Swatinem/rust-cache|cache-from",
            txt,
            re.I,
        )
    )
    conc = bool(re.search(r"^\s*concurrency\s*:", txt, re.M))
    paths = bool(re.search(r"^\s*paths(-ignore)?\s*:", txt, re.M))
    c.add(
        "ci.speed",
        "Fast feedback (caching, concurrency, path filters)",
        1,
        0.45 * cache + 0.35 * conc + 0.2 * paths,
        [f"dependency cache: {cache}", f"concurrency group: {conc}", f"path filters: {paths}"],
        "Cache dependencies, add `concurrency: {group: ${{ github.ref }}, cancel-in-progress: true}`, use path filters.",
    )
    return c.items


DIMENSION = Dimension("cicd", "CI/CD", "GitHub Actions coverage: PR gating, stages, CD, hygiene, pinning, speed.", assess)
