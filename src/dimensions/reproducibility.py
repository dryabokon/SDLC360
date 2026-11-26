"""Reproducibility: can someone else rebuild the project and get the same results from the same commit?

Judged by what the repository pins and documents (lockfiles, toolchain versions, entry points, provenance),
never by a folder layout: output conventions such as `runs/` are a team choice, not a universal practice.
"""

from __future__ import annotations

import re

from ..model import Checks, Dimension, short
from ..repo import Repo
from ._util import for_language

LOCKFILES = (
    "uv.lock",
    "poetry.lock",
    "Pipfile.lock",
    "pdm.lock",
    "pixi.lock",
    "conda-lock.yml",
    "requirements*.lock",
    "package-lock.json",
    "npm-shrinkwrap.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lockb",
    "bun.lock",
    "Cargo.lock",
    "go.sum",
    "Gemfile.lock",
    "composer.lock",
    "packages.lock.json",
    "gradle.lockfile",
    "flake.lock",
)
MANIFESTS = (
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements*.txt",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "Gemfile",
    "composer.json",
    "*.csproj",
    "pom.xml",
    "build.gradle*",
    "environment.yml",
)
ENV_PINS = (
    ".python-version",
    ".nvmrc",
    ".node-version",
    ".tool-versions",
    "mise.toml",
    ".mise.toml",
    "rust-toolchain*",
    "global.json",
    ".sdkmanrc",
    ".java-version",
    ".ruby-version",
    ".go-version",
    "Dockerfile",
    "*.dockerfile",
    "docker-compose*.yml",
    "compose.y*ml",
    ".devcontainer/*",
    "flake.nix",
    "shell.nix",
    "devbox.json",
)
ENTRYPOINTS = ("Makefile", "justfile", "Justfile", "Taskfile.y*ml", "noxfile.py", "tox.ini", "scripts/*", "start*.sh", "run*.sh", "start*.bat")


def assess(repo: Repo):
    c = Checks()
    manifests = repo.find(*MANIFESTS)

    locks = repo.find(*LOCKFILES)
    pinned_reqs = [f for f in repo.find("requirements*.txt", "constraints*.txt") if _fully_pinned(repo.read(f))]
    unpinned_reqs = [f for f in repo.find("requirements*.txt") if f not in pinned_reqs]
    lock_score = 1.0 if (locks or pinned_reqs) else (0.4 if unpinned_reqs else 0.0)
    c.add(
        "rep.lockfile",
        "Dependencies locked to exact versions",
        5,
        lock_score if (manifests or repo.source_files) else None,
        [f"lockfiles: {short(locks)}", f"fully pinned requirements: {short(pinned_reqs)}", f"unpinned requirements: {short(unpinned_reqs)}"],
        for_language(
            repo,
            {
                "py": "Commit a lockfile: `uv lock` writes uv.lock (or pin every requirement with `pip-compile`).",
                "js": "Commit the lockfile of your package manager: package-lock.json, pnpm-lock.yaml or yarn.lock.",
                "": "Commit the lockfile your package manager writes (Cargo.lock, go.sum, …).",
            },
        ),
    )

    env = repo.find(*ENV_PINS)
    c.add(
        "rep.environment",
        "Runtime and toolchain versions pinned",
        3,
        min(1.0, len(env) / 2),
        short(env),
        for_language(
            repo,
            {
                "py": "Add .python-version with the Python you use, and a Dockerfile or .devcontainer for the rest of the environment.",
                "js": "Add .nvmrc with the Node version you use, and a Dockerfile or .devcontainer for the rest of the environment.",
                "rust": "Add rust-toolchain.toml, and a Dockerfile or .devcontainer for the rest of the environment.",
                "": "Pin the language version in a version file, and add a Dockerfile or .devcontainer for the rest of the environment.",
            },
        ),
    )

    runner = repo.find(*ENTRYPOINTS)
    pp, pkg = repo.read("pyproject.toml"), repo.read("package.json")
    if re.search(r'"scripts"\s*:', pkg):
        runner.append("package.json scripts")
    if "[project.scripts]" in pp or "[tool.poe" in pp or "[tool.hatch.envs" in pp:
        runner.append("pyproject scripts / tasks")
    c.add(
        "rep.entrypoints",
        "One-command setup, build and test",
        3,
        bool(runner),
        short(runner),
        "Provide one obvious command per task (`make test`, `just build`, `./start.sh`) so humans and agents run the same steps.",
    )

    docs_files = repo.find("README*", "CONTRIBUTING*", "AGENTS.md", "CLAUDE.md", "docs/*.md")[:40]
    docs = "\n".join(repo.read(f) for f in docs_files)
    repro = sorted({m.group(0).lower() for m in re.finditer(r"\breproduc\w*|\bre-?run\w*|\bdeterministic\w*|\bsame results?\b", docs, re.I)})
    setup = bool(re.search(r"(?im)^#+.*(install|setup|getting started|quick ?start|development)", docs))
    c.add(
        "rep.documented",
        "Reproduction steps documented",
        3,
        1.0 if (repro and setup) else 0.5 if (repro or setup) else 0.0,
        [f"setup section: {setup}", f"reproduction wording: {', '.join(repro[:4]) or 'none'}"],
        "Document how to get from a clean checkout to the same result: setup, exact command, where outputs land, how to compare.",
    )

    return c.items


def _fully_pinned(text: str) -> bool:
    reqs = [ln.split("#")[0].strip() for ln in text.splitlines()]
    reqs = [r for r in reqs if r and not r.startswith(("-", "--"))]
    return bool(reqs) and all("==" in r or " @ " in r for r in reqs)


DIMENSION = Dimension(
    "reproducibility",
    "Reproducibility",
    "Locked dependencies, pinned toolchains, one-command entry points, documented reproduction, provenance of results.",
    assess,
)
