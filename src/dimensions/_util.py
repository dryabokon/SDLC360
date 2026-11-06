"""Helpers shared by dimension modules."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import PurePosixPath

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
    broken = []
    all_files = set(repo.files) | set(repo.on_disk) if repo.is_git else set(repo.files)
    all_dirs = repo.dirs
    for r in refs:
        r_clean = r.rstrip("/")
        candidates = [str(PurePosixPath(base, r_clean)), r_clean.lstrip("./")]
        ok = False
        for c in candidates:
            c = _normalize(c)
            if c in all_files or c.lower() in all_dirs or (repo.root / c).exists():
                ok = True
                break
        if not ok and "/" in r_clean and not r_clean.startswith("."):
            # paths written relative to a package root ("transport/x.py" for src/pkg/transport/x.py)
            suffix = "/" + _normalize(r_clean).lower()
            ok = any(f.lower().endswith(suffix) for f in all_files) or any(d.endswith(suffix) for d in all_dirs)
        if not ok:
            broken.append(r)
    return len(refs), sorted(broken)


def _normalize(p: str) -> str:
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


def headings(text: str) -> list[str]:
    return [m.group(2).strip().lower() for m in re.finditer(r"^(#{1,4})\s+(.+)$", text, re.M)]
