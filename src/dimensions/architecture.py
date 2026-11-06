"""Architecture: is the design written down, diagrammed, decided-on-record, and reflected in the structure?"""

from __future__ import annotations

from ..model import Checks, Dimension, short
from ..repo import Repo
from ._util import freshness_score


def assess(repo: Repo):
    c = Checks()
    arch = repo.find("ARCHITECTURE*", "DESIGN.md", "docs/*architecture*", "docs/*design*", "doc/*architecture*", "docs/*overview*", "docs/arc42/*")
    arch = [f for f in arch if f.lower().endswith((".md", ".mdx", ".rst", ".adoc", ".txt"))]
    c.add(
        "arch.doc",
        "Architecture document",
        3,
        min(1.0, len(arch) / 1) if arch else 0.0,
        short(arch),
        "Write ARCHITECTURE.md (or docs/architecture.md): components, data flow, boundaries, key dependencies.",
    )

    md = [f for f in repo.files if f.lower().endswith((".md", ".mdx"))][:400]
    mermaid = repo.any_match(r"```\s*(mermaid|plantuml|d2|dot|graphviz)", md)
    diagram_files = repo.find("*.puml", "*.plantuml", "*.drawio", "*.excalidraw", "*.d2", "*.mmd", "*.dsl", "*.c4")
    total = len(mermaid) + len(diagram_files)
    c.add(
        "arch.diagrams",
        "Diagrams as code (Mermaid / PlantUML / C4 / draw.io)",
        2,
        min(1.0, total / repo.param("arch.diagrams", "target")),
        [f"markdown with diagrams: {short(mermaid, 3)}", f"diagram files: {short(diagram_files, 3)}"],
        "Add a Mermaid/C4 context + container diagram in the architecture doc so it renders on GitHub and diffs in PRs.",
    )

    adr_dirs = repo.find_dirs("*adr", "*adrs", "*decisions", "*decision-records", "docs/architecture/decisions")
    adrs = [f for f in repo.files if any(f.lower().startswith(d + "/") for d in adr_dirs) and f.lower().endswith(".md")]
    c.add(
        "arch.adr",
        "Design decision records",
        2,
        min(1.0, len(adrs) / repo.param("arch.adr", "target")),
        f"{len(adrs)} decision records in {short(adr_dirs, 2)}" if adrs else "no design-decisions folder",
        "Record significant design decisions, one file each (docs/design-decisions/NN-title.md: context, decision, consequences).",
    )

    top = sorted({f.split("/")[0] for f in repo.source_files if "/" in f})
    root_src = [f for f in repo.source_files if "/" not in f]
    max_root = repo.param("arch.structure", "max_root_files")
    organized: float | None = 1.0 if (top and len(root_src) <= max_root) else (0.6 if len(root_src) <= 3 * max_root else 0.3)
    if not repo.source_files:
        organized = None
    c.add(
        "arch.structure",
        "Source organized into modules (not a flat root)",
        1.5,
        organized,
        [f"top-level code dirs: {short(top, 8)}", f"source files at root: {len(root_src)}"],
        "Group code into packages by responsibility (src/<pkg>/…, apps/, libs/) and keep the root clean.",
    )

    boundaries = repo.find(
        ".importlinter", "importlinter.ini", ".dependency-cruiser.*", "nx.json", "turbo.json", "pnpm-workspace.yaml", "go.work", "lerna.json", "*.sln"
    )
    pyproject = repo.read("pyproject.toml") if repo.exists("pyproject.toml") else ""
    if "importlinter" in pyproject or "tach" in pyproject:
        boundaries.append("pyproject.toml (import rules)")
    archunit = repo.grep(r"ArchUnit|ArchRule|NetArchTest|deptry", files=repo.test_files[:500], max_hits=1)
    c.add(
        "arch.boundaries",
        "Module boundaries are explicit / enforced",
        1,
        min(1.0, 0.5 * len(boundaries) + (0.5 if archunit else 0))
        if len(repo.source_files) > repo.param("arch.boundaries", "min_source_files")
        else None,
        short(boundaries) if boundaries else "no workspace/boundary tooling",
        "Enforce layering with import-linter / dependency-cruiser / ArchUnit, or a workspace tool.",
    )

    if arch:
        fs, msg = freshness_score(
            repo.last_modified(arch),
            repo.last_modified(repo.source_files[:2000]),
            repo.param("arch.fresh", "grace_days"),
            repo.param("arch.fresh", "max_lag_days"),
        )
        c.add(
            "arch.fresh",
            "Architecture doc maintained with the code",
            1.5,
            fs,
            msg,
            "Review the architecture doc when adding/removing modules; date it and link the design decisions.",
        )
    else:
        c.add("arch.fresh", "Architecture doc maintained with the code", 1.5, 0.0, "no architecture doc")
    return c.items


DIMENSION = Dimension(
    "architecture", "Architecture", "Architecture docs, diagrams-as-code, decision records, modular structure, enforced boundaries.", assess
)
