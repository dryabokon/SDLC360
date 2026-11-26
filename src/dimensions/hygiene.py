"""Code hygiene: linting, formatting, typing, pre-commit and repo conventions."""

from __future__ import annotations

import re

from ..model import Checks, Dimension, short
from ..repo import Repo
from ._util import for_language, forge, in_tooling, on


def assess(repo: Repo):
    c = Checks()
    pp = repo.read("pyproject.toml")
    pkg = repo.read("package.json")
    lint = repo.find(
        "ruff.toml",
        ".ruff.toml",
        ".flake8",
        ".pylintrc",
        "pylintrc",
        ".eslintrc*",
        "eslint.config.*",
        "biome.json*",
        ".golangci.y*ml",
        "clippy.toml",
        ".rubocop.yml",
        "detekt.yml",
        ".editorconfig",
        "stylecop.json",
        ".swiftlint.yml",
        "deno.json",
    )
    lint = [f for f in lint if not in_tooling(f)]  # e.g. a linter skill's own ruff.toml for the code it generates
    lint += [f"pyproject [{t}]" for t in ("tool.ruff", "tool.pylint", "tool.flake8") if f"[{t}" in pp]
    if '"eslint' in pkg or '"@biomejs' in pkg:
        lint.append("package.json (eslint/biome)")
    c.add(
        "hyg.lint",
        "Linter configured",
        2,
        bool(lint),
        short(lint),
        for_language(
            repo,
            {
                "py": "Add ruff: a `[tool.ruff]` section in pyproject.toml, and run `ruff check .` in CI.",
                "js": "Add ESLint (eslint.config.js) and run `npx eslint .` in CI.",
                "go": "Add golangci-lint (.golangci.yml) and run it in CI.",
                "rust": "Run `cargo clippy -- -D warnings` in CI.",
                "java": "Add Checkstyle or SpotBugs to the build and run it in CI.",
                "": "Configure the linter of your language and run it in CI.",
            },
        ),
    )

    fmt = repo.find(".prettierrc*", "prettier.config.*", "rustfmt.toml", ".rustfmt.toml", ".clang-format", "dprint.json")
    fmt = [f for f in fmt if not in_tooling(f)]
    fmt += [f"pyproject [{t}]" for t in ("tool.black", "tool.ruff.format", "tool.isort") if f"[{t}" in pp]
    if repo.find("go.mod"):
        fmt.append("gofmt (Go built-in)")
    if '"prettier' in pkg or '"@biomejs' in pkg or "biome.json" in " ".join(lint):
        fmt.append("prettier/biome")
    if "[tool.ruff" in pp:
        fmt.append("ruff format")
    c.add(
        "hyg.format",
        "Formatter configured",
        1.5,
        bool(fmt),
        short(sorted(set(fmt))),
        for_language(
            repo,
            {
                "py": "Format with `ruff format` and check it in CI with `ruff format --check .`.",
                "js": "Add Prettier and check it in CI with `npx prettier --check .`.",
                "rust": "Check the format in CI with `cargo fmt --check`.",
                "java": "Add Spotless to the build and check it in CI.",
                "": "Add the formatter of your language and check it in CI.",
            },
        ),
    )

    langs = repo.languages
    typed = None
    ev = "no dynamically-typed code"
    if any(e in langs for e in (".py",)):
        tcfg = [f"pyproject [{t}]" for t in ("tool.mypy", "tool.pyright", "tool.basedpyright") if f"[{t}" in pp] + repo.find(
            "mypy.ini", "pyrightconfig.json", ".mypy.ini"
        )
        py = [f for f in repo.source_files if f.endswith(".py")][:300]
        hinted = sum(1 for f in py if re.search(r"def \w+\([^)]*:\s*\w|->\s*\w", repo.read(f)))
        typed = 0.5 * bool(tcfg) + 0.5 * min(1.0, (hinted / max(1, len(py))) / 0.7)
        ev = f"type checker: {short(tcfg) if tcfg else 'none'}; {hinted}/{len(py)} files use annotations"
    elif any(e in langs for e in (".js", ".jsx", ".ts", ".tsx")):
        ts = repo.find("tsconfig*.json")
        strict = any(re.search(r'"strict"\s*:\s*true', repo.read(f)) for f in ts)
        typed = 0.6 * bool(ts) + 0.4 * strict
        ev = f"tsconfig: {short(ts)}; strict: {strict}"
    c.add(
        "hyg.types",
        "Static typing enforced",
        1.5,
        typed,
        ev,
        for_language(
            repo,
            {
                "py": "Add a `[tool.mypy]` section to pyproject.toml and run `mypy` in CI, then annotate the files that have no types yet.",
                "js": 'Set `"strict": true` in tsconfig.json and run `tsc --noEmit` in CI.',
                "": "Turn on the type checker of your language and run it in CI.",
            },
        ),
    )

    pc = repo.find(".pre-commit-config.yaml", ".husky/*", "lefthook.yml", ".lefthook.yml", "lint-staged.config.*", ".lintstagedrc*")
    c.add(
        "hyg.precommit",
        "Pre-commit hooks",
        1.5,
        bool(pc),
        short(pc),
        for_language(
            repo,
            {
                "py": "Add .pre-commit-config.yaml with ruff, ruff-format and gitleaks, and run `pre-commit install` once.",
                "js": "Add husky with lint-staged running ESLint and Prettier on the staged files.",
                "": "Add pre-commit (or lefthook) running the formatter, the linter and a secret scan before each commit.",
            },
        ),
    )

    ec = repo.find(".editorconfig", ".gitattributes")
    c.add(
        "hyg.editor",
        ".editorconfig / .gitattributes",
        0.5,
        len(ec) / 2,
        short(ec),
        "Add "
        + " and ".join(f for f in (".editorconfig", ".gitattributes") if f not in ec)
        + ": .editorconfig fixes indentation and line endings in every editor, .gitattributes fixes line endings in git.",
    )

    tmpl = repo.find(
        ".github/pull_request_template.md",
        ".github/PULL_REQUEST_TEMPLATE*",
        ".github/ISSUE_TEMPLATE/*",
        "docs/pull_request_template.md",
        ".gitlab/merge_request_templates/*",
        ".gitlab/issue_templates/*",
        ".azuredevops/pull_request_template*",
        ".azuredevops/pull_request_template/*",
        ".vsts/pull_request_template*",
    )
    need = 1 if forge(repo) == "azure" else 2  # Azure Repos has no issue templates in the repository: the PR one is all
    c.add(
        "hyg.templates",
        "PR / issue templates",
        0.5,
        min(1.0, len(tmpl) / need),
        short(tmpl),
        on(
            repo,
            "Add .github/pull_request_template.md with a short checklist (tests, docs, changelog) and an issue template in .github/ISSUE_TEMPLATE/.",
            "Add .gitlab/merge_request_templates/Default.md with a short checklist (tests, docs, changelog) and an issue template "
            "in .gitlab/issue_templates/.",
            "Add .azuredevops/pull_request_template.md with a short checklist (tests, docs, changelog).",
        ),
    )

    max_kb = repo.param("hyg.file_size", "max_kb")
    big = []
    for f in repo.source_files[:3000]:
        try:
            n = (repo.root / f).stat().st_size
        except OSError:
            continue
        if n > max_kb * 1000:
            big.append(f"{f} ({n // 1000} KB)")
    c.add(
        "hyg.file_size",
        f"No oversized source files (>{max_kb:g} KB)",
        1,
        1 - min(1.0, len(big) / max(5, len(repo.source_files) * 0.05)),
        short(big, 4) if big else "none",
        "Split these files by responsibility: a reviewer cannot read them in one go, and an agent spends its context on them.",
        todo=big[:5],
    )
    return c.items


DIMENSION = Dimension("hygiene", "Code Hygiene", "Linters, formatters, type checking, pre-commit, editor config, templates, file size.", assess)
