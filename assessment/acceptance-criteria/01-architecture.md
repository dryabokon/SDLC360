# Architecture: how each expectation is judged

Expectations and their priorities are in [expectations.md](../expectations.md).
How to edit this file: [assessment/README.md](../README.md#acceptance-criteria).

## arch.doc: An architecture document describes components, data flow and boundaries.

**How we check.** Files matching `ARCHITECTURE*` or `DESIGN.md` anywhere in the tree, or `docs/*architecture*`, `docs/*design*`, `docs/*overview*`, `doc/*architecture*` or `docs/arc42/*` at any depth. The extension must be `.md`, `.mdx`, `.rst`, `.adoc` or `.txt`.

- **Met:** At least one such file exists.
- **Partially met:** Never.
- **Not met:** No such file.

**What the check cannot see.** Only the file name is checked, so an empty file passes. `docs/design-system/button.md` or a decision record with "design" in its name also passes. An architecture section inside the README is not counted.

**Known flaw.** The checklist says the document describes components, data flow and boundaries. The content is never read.

**Why we expect it.**

> Given a clear architecture document, AI agents can scaffold entire applications, generate consistent patterns across modules, and ensure that new code conforms to established conventions.
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 22 · supporting

> proprietary company data, such as codebases, wikis, architectural diagrams, documentation, and style guides—all of which can be managed through manual and automated context engineering.
>
> — [dora-2025-ai-capabilities-model](../references/dora-2025-ai-capabilities-model/), p. 28 · supporting

## arch.diagrams: Architecture diagrams are kept as code (Mermaid / PlantUML / C4).

**How we check.** The first 400 tracked `.md`/`.mdx` files are searched for a code fence opening with `mermaid`, `plantuml`, `d2`, `dot` or `graphviz`. It also counts `*.puml`, `*.plantuml`, `*.drawio`, `*.excalidraw`, `*.d2`, `*.mmd`, `*.dsl` and `*.c4` files anywhere. The total is the number of markdown files with a fence plus the number of diagram files.

- **Met:** A total of 2 or more.
- **Partially met:** A total of exactly 1.
- **Not met:** Zero.

**What the check cannot see.** A markdown file counts once, however many diagrams it holds. Any `.dsl` file counts, Structurizr or not. Diagrams in `.rst`/`.adoc` and exported PNG/SVG images are not seen. Nothing checks that a diagram shows the architecture.

**Known flaw.** The fence pattern has no word boundary, so a `dotenv` code fence (common in READMEs for env examples) counts as a Graphviz diagram.

**Why we expect it.**

> The AI, using RAG to access the latest API specs, architectural diagrams, and the codebase itself, provides a step-by-step answer
>
> — [dora-2025-ai-capabilities-model](../references/dora-2025-ai-capabilities-model/), p. 32 · supporting

## arch.adr: Significant design decisions are recorded, one file per decision.

**How we check.** Folders whose path or name matches `*adr`, `*adrs`, `*decisions`, `*decision-records` or `docs/architecture/decisions`. It counts the tracked `.md` files beneath them at any depth.

- **Met:** 3 or more markdown files.
- **Partially met:** Exactly 2.
- **Not met:** 0 or 1.

**What the check cannot see.** README and template files in the folder count as decision records, and content is not checked. A folder such as `design-decisions` for something unrelated counts. Records written as `.rst`/`.adoc`, or kept outside such folders, are missed.

**Why we expect it.**

> Maintain records of design decisions, risk responses, and approved exceptions that can be used for auditing and maintenance purposes throughout the rest of the software life cycle.
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218 PW.1.2 Ex.2, p.20 · direct

> The developer's role shifts from writing boilerplate to making and documenting the structural decisions that boilerplate implements.
>
> — [google-new-sdlc](../references/google-new-sdlc/), p. 22 · supporting

> Decisions that aren’t in the repo: which error helper the team settled on, how deploys work, what needs a migration review
>
> — [anthropic-claude-code-best-practices](../references/anthropic-claude-code-best-practices/), Keep CLAUDE.md short · supporting

## arch.structure: Source code is organised into modules, not a flat root.

**How we check.** Source files (by extension, excluding tests, `vendor/`, `third_party/`, `docs/`, `examples/`, `.github/`). It counts how many sit in the repo root and whether any sit in a subfolder.

- **Met:** At least one source file in a subfolder and at most 5 source files in the root.
- **Partially met:** 6 to 15 source files in the root, or all code in the root with at most 15 files.
- **Not met:** More than 15 source files in the root (score 0.3).
- **Not applicable:** No source files at all.

**What the check cannot see.** `.sh` and `.ps1` count as source, so root helper scripts count against the repo. One nested file (for example `scripts/x.sh`) is enough. A flat `src/` holding hundreds of files is Met. Module cohesion is not judged.

**Why we expect it.**

> Folder hierarchies, naming conventions, and timestamps all provide important signals that help both humans and agents understand how and when to utilize information.
>
> — [anthropic-context-engineering](../references/anthropic-context-engineering/), Context retrieval and agentic search · supporting

> Define policies that specify risk-based software architecture and design requirements, such as making code modular to facilitate code reuse and updates
>
> — [nist-ssdf](../references/nist-ssdf/), SP 800-218 PO.1.2 Ex.1, p.14 · supporting

## arch.fresh: The architecture document is maintained alongside the code.

**How we check.** The newest commit touching any arch.doc file is compared with the newest commit touching the first 2,000 source files.

- **Met:** The architecture doc lags the code by no more than about 80 days.
- **Partially met:** A lag of about 81 to 248 days, or unknown dates (scores 0.5).
- **Not met:** A lag of more than about 248 days, or no architecture doc.

**What the check cannot see.** The newest matching file wins. Editing an unrelated `docs/*design*` page or fixing a typo counts as maintenance. Whether the content matches the code is not checked.

**Our convention.** An architecture document that lags the code misleads people and agents more than no document; we use the same staleness rule as for docs.

## arch.boundaries: Module boundaries are explicit and enforced by tooling.

**How we check.** Files anywhere named `.importlinter`, `importlinter.ini`, `.dependency-cruiser.*`, `nx.json`, `turbo.json`, `pnpm-workspace.yaml`, `go.work`, `lerna.json` or `*.sln`. Also a root `pyproject.toml` containing the text "importlinter" or "tach", and `ArchUnit`/`ArchRule`/`NetArchTest`/`deptry` text in up to 500 test files. Score: 0.5 per file found, plus 0.5 for a test hit.

- **Met:** Two or more of those files, or one file plus a test hit.
- **Partially met:** Exactly one file, or only a test hit.
- **Not met:** Nothing found.
- **Not applicable:** 50 or fewer source files.

**What the check cannot see.** Whether the rules are run in CI or actually enforced is not checked. deptry is usually configured in `pyproject.toml`, not tests, so it is rarely seen there.

**Known flaw.** Workspace files (`*.sln`, `nx.json`, `pnpm-workspace.yaml`, `go.work`, `lerna.json`) declare workspaces, they do not enforce boundaries. Two `.sln` files give Met. The "tach" text test also matches "attach", "detach" and so on anywhere in `pyproject.toml`.

**Why we expect it.**

> We need to work within software architectures that give us independence of action—more than ever, we need to be able to develop, test, and deploy software independently.
>
> — [dora-2025-state-of-ai-assisted-development](../references/dora-2025-state-of-ai-assisted-development/), p. 9 · supporting
