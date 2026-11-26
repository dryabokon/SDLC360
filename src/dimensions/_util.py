"""Helpers shared by dimension modules."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path, PurePosixPath

from ..repo import Repo

INSTRUCTION_FILES = ("CLAUDE.md", "AGENTS.md", "GEMINI.md", ".github/copilot-instructions.md", ".cursorrules", ".windsurfrules", "CLAUDE.local.md")


def frontmatter(text: str) -> dict[str, str] | None:
    """Minimal YAML frontmatter reader (top-level `key: value` pairs, folded values joined)."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    data: dict[str, str] = {}
    key = None
    for line in text[3:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if m and not line.startswith((" ", "\t")):
            key = m.group(1)
            data[key] = m.group(2).strip().strip("'\"").lstrip(">|").strip()
        elif key:
            data[key] = (data[key] + " " + line.strip()).strip()
    return data


LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
CODE_PATH_RE = re.compile(r"`((?:\.{0,2}/)?[\w.-]+(?:/[\w.-]+)+/?)`")


def broken_refs(repo: Repo, md_file: str) -> tuple[int, list[str]]:
    """Return (#refs checked, broken refs) for relative links and backticked paths in a markdown file."""
    found, broken = resolve_refs(repo, md_file)
    return len(found) + len(broken), broken


def resolve_refs(repo: Repo, md_file: str) -> tuple[list[str], list[str]]:
    """(the repository path each resolving link or backticked path of a markdown file points at, one per ref, the refs
    that resolve to nothing). A path is a file or a folder, relative to the repository root."""
    text = repo.read(md_file)
    base = PurePosixPath(md_file).parent
    refs = set()
    for m in LINK_RE.finditer(text):
        target = m.group(1).split("#")[0]
        if target and not re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) and not target.startswith(("<", "/", "~")):
            refs.add(target)
    for m in CODE_PATH_RE.finditer(text):
        cand = m.group(1)
        # only treat as path if it looks like one (has an extension or ends with /) and isn't a URL/package
        if (
            "://" not in cand and (re.search(r"\.\w{1,6}$", cand) or cand.endswith("/")) and not cand.startswith(("@", "/", "~"))
        ):  # absolute paths point at the runtime host, not the repo
            refs.add(cand)
    found: list[str] = []
    broken = []
    all_files = set(repo.files) | set(repo.on_disk) if repo.is_git else set(repo.files)
    all_dirs = repo.dirs
    for r in refs:
        r_clean = r.rstrip("/")
        candidates = [str(PurePosixPath(base, r_clean)), re.sub(r"^(\./)+", "", r_clean)]
        hit = None
        for c in candidates:
            c = normalize_path(c)
            if c and (c in all_files or c.lower() in all_dirs or (repo.root / c).exists()):
                hit = c
                break
        if hit is None and "/" in r_clean and not r_clean.startswith("."):
            # paths written relative to a package root ("transport/x.py" for src/pkg/transport/x.py)
            suffix = "/" + normalize_path(r_clean).lower()
            hit = next((f for f in sorted(all_files) if f.lower().endswith(suffix)), None) or next(
                (d for d in sorted(all_dirs) if d.endswith(suffix)), None
            )
        if hit is None:
            broken.append(r)
        else:
            found.append(hit)
    return sorted(found), sorted(broken)


def normalize_path(p: str) -> str:
    parts: list[str] = []
    for seg in p.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if parts:
                parts.pop()
            continue
        parts.append(seg)
    return "/".join(parts)


def days_between(a: datetime | None, b: datetime | None) -> float | None:
    if a is None or b is None:
        return None
    return (b - a).total_seconds() / 86400


def reach(value: float, accepted_from: float) -> float:
    """Score of a measure against its acceptance threshold: exactly 0.85 (Met) at the threshold, 0.35 (Partially met) at 41% of it."""
    return min(1.0, 0.85 * value / accepted_from) if accepted_from > 0 else 1.0


def freshness_score(doc_time: datetime | None, code_time: datetime | None, met_days: float = 80) -> tuple[float, str]:
    """Met (0.85) while the doc lags the code by at most `met_days`. Full score up to 3/8 of that, zero at 4.5625x (30 / 80 / 365 by default)."""
    grace, zero_at = met_days * 30 / 80, met_days * 365 / 80
    lag = days_between(doc_time, code_time)
    if lag is None:
        return 0.5, "freshness unknown (no history)"
    if lag <= grace:
        return 1.0, f"docs updated within {max(lag, 0):.0f} days of last code change"
    s = max(0.0, 1 - (lag - grace) / max(1.0, zero_at - grace))
    return s, f"docs lag code by {lag:.0f} days"


def instruction_files(repo: Repo) -> list[str]:
    out = []
    for name in INSTRUCTION_FILES:
        out += [f for f in repo.find(name) if f.rsplit("/", 1)[-1] == name.rsplit("/", 1)[-1]]  # exact, case-sensitive basename
    out += repo.find(".cursor/rules/*")
    return sorted(set(out))


def in_tooling(f: str) -> bool:
    """A file of the agent tooling or a vendored package (a folder starting with a dot, or skills/), not the project's own."""
    dirs = f.lower().split("/")[:-1]
    return any(d.startswith(".") for d in dirs if d != ".github") or "skills" in dirs or f.lower().startswith(".github/skills/")


def headings(text: str) -> list[str]:
    return [m.group(2).strip().lower() for m in re.finditer(r"^(#{1,4})\s+(.+)$", text, re.M)]


FORGES = ("github", "gitlab", "azure")
AZURE_HOSTS = ("dev.azure.com", "ssh.dev.azure.com", "vs-ssh.visualstudio.com")


def forge(repo: Repo) -> str:
    """Where the project lives, so a step names that platform's settings and files: "github" (the default), "gitlab"
    or "azure". The remote decides (a local folder's own remotes, not those of the copy a scan reads); without one,
    the CI files; `--forge` (repo.forge) overrides both, for a mirror on two platforms."""
    from .. import hosting

    if repo.forge in FORGES:
        return repo.forge

    def host_of(s: str) -> str:
        m = re.match(r"^(?:\w+://)?(?:[^@/]+@)?([\w.-]+)[:/]", s.strip())
        return m.group(1).lower() if m else ""

    hosts = [host_of(repo.source)]
    folders = [repo.root] if hosting.is_remote(repo.source) else [Path(repo.source), repo.root]  # the folder assessed, then the copy read
    for folder in dict.fromkeys(folders):
        try:
            cfg = (folder / ".git" / "config").read_text(encoding="utf-8", errors="replace")
            hosts += [host_of(u) for u in re.findall(r"^\s*url\s*=\s*(\S+)", cfg, re.M)]
        except OSError:
            pass
    hosts = [h for h in hosts if h]
    if any(h in AZURE_HOSTS or h.endswith(".visualstudio.com") for h in hosts):
        return "azure"
    if "github.com" in hosts:
        return "github"
    if any(h in hosting.git_hosts() or "gitlab" in h for h in hosts):
        return "gitlab"
    if repo.workflows:
        return "github"
    if ".gitlab-ci.yml" in repo.files:
        return "gitlab"
    if any("azure-pipelines" in f.lower() for f in repo.other_ci):
        return "azure"
    return "github"


LANGS = {".py": "py", ".ts": "js", ".tsx": "js", ".js": "js", ".jsx": "js", ".go": "go", ".rs": "rust", ".java": "java", ".kt": "java"}


def main_language(repo: Repo) -> str:
    """The language most source files are in: "py", "js", "go", "rust", "java", or "" for another."""
    return next((LANGS[e] for e in repo.languages if e in LANGS), "")


def for_language(repo: Repo, steps: dict[str, str]) -> str:
    """The step for the project's main language; "" is the step for any other."""
    return steps.get(main_language(repo)) or steps[""]


def on(repo: Repo, github: str, gitlab: str, azure: str) -> str:
    """The step for the platform the project lives on: its settings pages and file names, not another platform's."""
    return {"github": github, "gitlab": gitlab, "azure": azure}[forge(repo)]
