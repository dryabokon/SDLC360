"""Documentation: presence, completeness and freshness relative to the code."""

from __future__ import annotations

import re

from ..model import Checks, Dimension, short
from ..repo import Repo
from ._util import broken_refs, freshness_score, headings


def assess(repo: Repo):
    c = Checks()
    readmes = [f for f in repo.find("README*") if "/" not in f]
    readme = readmes[0] if readmes else None
    text = repo.read(readme) if readme else ""
    words = len(re.findall(r"\w+", text))
    c.add(
        "doc.readme",
        "README present and substantial",
        3,
        0.0 if not readme else min(1.0, words / 400),
        f"{readme}: {words} words" if readme else "no root README",
        "Write a README with purpose, quick start, usage, configuration, testing and contribution sections.",
    )

    hs = " | ".join(headings(text)) + " " + text.lower()[:30000]
    sections = {
        "install/setup": r"install|setup|getting started|quick ?start|prerequisite",
        "usage": r"usage|example|how to|running|run ",
        "testing": r"\btest",
        "configuration": r"config|environment|\.env|settings",
        "architecture/overview": r"architect|overview|design|how it works|structure",
        "contributing": r"contribut|development|develop",
    }
    hit = [k for k, p in sections.items() if re.search(p, hs)]
    c.add(
        "doc.readme_sections",
        "README covers setup, usage, testing, config, overview",
        2,
        len(hit) / len(sections) if readme else 0.0,
        [f"covers: {', '.join(hit) or 'none'}", f"missing: {', '.join(k for k in sections if k not in hit) or '-'}"],
        "Add the missing README sections (or link to docs/ pages for each).",
    )

    docs = [f for f in repo.find("docs/*", "doc/*", "documentation/*", "website/docs/*") if f.lower().endswith((".md", ".mdx", ".rst", ".adoc"))]
    c.add(
        "doc.docs_dir",
        "Dedicated docs folder",
        1.5,
        min(1.0, len(docs) / 3),
        f"{len(docs)} doc pages" + (f": {short(docs, 3)}" if docs else ""),
        "Create docs/ with guides beyond the README (architecture, operations, decisions).",
    )

    std = {
        "LICENSE": ["LICENSE*", "COPYING*"],
        "CONTRIBUTING": ["CONTRIBUTING*", ".github/CONTRIBUTING*"],
        "CHANGELOG": ["CHANGELOG*", "CHANGES*", "HISTORY*", "RELEASES*"],
    }
    have = [k for k, pats in std.items() if repo.find(*pats)]
    c.add(
        "doc.standard_files",
        "LICENSE, CONTRIBUTING, CHANGELOG",
        1,
        len(have) / len(std),
        f"present: {', '.join(have) or 'none'}",
        "Add the missing standard community files.",
    )

    md = [f for f in repo.files if f.lower().endswith(".md") and not f.lower().startswith(("node_modules/", "vendor/"))][:300]
    n_refs, broken = 0, []
    for f in md:
        n, b = broken_refs(repo, f)
        n_refs += n
        broken += [f"{f} -> {x}" for x in b]
    c.add(
        "doc.links",
        "Docs reference files that exist (no stale paths)",
        2,
        1.0 if not n_refs else 1 - min(1.0, 3 * len(broken) / n_refs),
        [f"{n_refs - len(broken)}/{n_refs} intra-repo references resolve"] + broken[:6],
        "Fix or remove references to renamed/deleted files; add a link checker (lychee / markdown-link-check) to CI.",
    )

    doc_files = ([readme] if readme else []) + docs
    fs, msg = freshness_score(repo.last_modified(doc_files), repo.last_modified(repo.source_files[:2000]))
    c.add(
        "doc.freshness",
        "Docs updated alongside code",
        2,
        fs if doc_files else 0.0,
        msg,
        "Update docs in the same PR as behaviour changes; add a PR-template checkbox for docs.",
    )

    src = repo.source_files
    py = [f for f in src if f.endswith(".py")][:400]
    if py:
        n_def = n_doc = 0
        for f in py:
            t = repo.read(f)
            for m in re.finditer(r"^\s*(?:async\s+)?(?:def|class)\s+[A-Za-z]\w*[^\n]*:\s*\n(\s*)(\"\"\"|''')?", t, re.M):
                n_def += 1
                n_doc += bool(m.group(2))
        c.add(
            "doc.inline",
            "Inline API docs (docstrings / doc comments)",
            1,
            min(1.0, (n_doc / n_def) / 0.6) if n_def else None,
            f"{n_doc}/{n_def} Python defs have docstrings",
            "Document public modules, classes and functions.",
        )
    else:
        js = [f for f in src if f.endswith((".ts", ".tsx", ".js", ".go", ".rs", ".java", ".cs", ".kt"))][:400]
        if js:
            n_doc = sum(1 for f in js if re.search(r"/\*\*|^\s*///|^\s*//\s*[A-Z]\w+ ", repo.read(f), re.M))
            c.add(
                "doc.inline",
                "Inline API docs (doc comments)",
                1,
                min(1.0, (n_doc / len(js)) / 0.5),
                f"{n_doc}/{len(js)} files contain doc comments",
                "Add JSDoc/TSDoc/GoDoc/rustdoc on public APIs.",
            )
    return c.items


DIMENSION = Dimension("docs", "Documentation", "README depth, docs folder, standard files, link integrity and freshness vs. code.", assess)
