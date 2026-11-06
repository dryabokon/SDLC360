"""Code hygiene: linting, formatting, typing, pre-commit and repo conventions."""

from __future__ import annotations

import re

from ..model import Checks, Dimension, short
from ..repo import Repo


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
    lint += [f"pyproject [{t}]" for t in ("tool.ruff", "tool.pylint", "tool.flake8") if f"[{t}" in pp]
    if '"eslint' in pkg or '"@biomejs' in pkg:
        lint.append("package.json (eslint/biome)")
    c.add("hyg.lint", "Linter configured", 2, bool(lint), short(lint), "Configure a linter (ruff / eslint / golangci-lint / clippy).")

    fmt = repo.find(".prettierrc*", "prettier.config.*", "rustfmt.toml", ".rustfmt.toml", ".clang-format", "dprint.json")
    fmt += [f"pyproject [{t}]" for t in ("tool.black", "tool.ruff.format", "tool.isort") if f"[{t}" in pp]
    if repo.find("go.mod"):
        fmt.append("gofmt (Go built-in)")
    if '"prettier' in pkg or '"@biomejs' in pkg or "biome.json" in " ".join(lint):
        fmt.append("prettier/biome")
    if "[tool.ruff" in pp:
        fmt.append("ruff format")
    c.add("hyg.format", "Formatter configured", 1.5, bool(fmt), short(sorted(set(fmt))), "Adopt an auto-formatter and enforce it in CI.")

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
    c.add("hyg.types", "Static typing enforced", 1.5, typed, ev, "Enable mypy/pyright (Python) or `strict: true` TypeScript.")

    pc = repo.find(".pre-commit-config.yaml", ".husky/*", "lefthook.yml", ".lefthook.yml", "lint-staged.config.*", ".lintstagedrc*")
    c.add("hyg.precommit", "Pre-commit hooks", 1.5, bool(pc), short(pc), "Add pre-commit (or husky/lefthook) running format + lint + secret scan.")

    ec = repo.find(".editorconfig", ".gitattributes")
    c.add(
        "hyg.editor",
        ".editorconfig / .gitattributes",
        0.5,
        len(ec) / 2,
        short(ec),
        "Add .editorconfig and .gitattributes (line endings, linguist overrides).",
    )

    tmpl = repo.find(
        ".github/pull_request_template.md", ".github/PULL_REQUEST_TEMPLATE*", ".github/ISSUE_TEMPLATE/*", "docs/pull_request_template.md"
    )
    c.add(
        "hyg.templates",
        "PR / issue templates",
        0.5,
        min(1.0, len(tmpl) / 2),
        short(tmpl),
        "Add PR and issue templates with checklists (tests, docs, changelog).",
    )

    big = []
    for f in repo.source_files[:3000]:
        try:
            n = (repo.root / f).stat().st_size
        except OSError:
            continue
        if n > 60_000:
            big.append(f"{f} ({n // 1000} KB)")
    c.add(
        "hyg.file_size",
        "No oversized source files (>60 KB)",
        1,
        1 - min(1.0, len(big) / max(5, len(repo.source_files) * 0.05)),
        short(big, 4) if big else "none",
        "Split oversized modules — they hurt reviewability and agent context budgets.",
    )
    return c.items


DIMENSION = Dimension("hygiene", "Code Hygiene", "Linters, formatters, type checking, pre-commit, editor config, templates, file size.", assess)
