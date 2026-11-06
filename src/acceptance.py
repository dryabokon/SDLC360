"""Acceptance criteria: how each expectation is judged, in plain language (checklists/acceptance.md).

The file is the single source of truth for "how checked / when met" texts shown next to the evidence, and for the
external basis (docs/sources/) that justifies each expectation.

    ## security
    ### sec.no_secrets
    - **Checks:** what the scanner looks at
    - **Met:** …          - **Partially met:** …     - **Not met:** …
    - **Not applicable:** …  (optional)
    - **Limits:** what the heuristic cannot see
    - **Basis:**
      - S09 · PW.1.3 · "verbatim quote"
    - **Convention:** why we expect it without an external basis (instead of Basis)
    - **Known gap:** where the scanner does not yet check what the expectation says
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACCEPTANCE = ROOT / "checklists" / "acceptance.md"
SOURCES = ROOT / "docs" / "sources"

FIELDS = {
    "checks": "looks_at",
    "met": "met_when",
    "partially met": "partial_when",
    "not met": "not_met_when",
    "not applicable": "na_when",
    "limits": "limits",
    "convention": "convention",
    "known gap": "known_gap",
}
FIELD_RE = re.compile(r"^- \*\*([A-Za-z ]+):\*\*\s*(.*)$")
BASIS_RE = re.compile(r"^\s+- (S\d\d) · ([^·]+?) · (.+)$")


@lru_cache(maxsize=1)
def sources() -> dict[str, dict]:
    """S01.. -> {id, title, publisher, published, url, license} from docs/sources/<NN-slug>/SOURCE.md frontmatter."""
    out = {}
    for md in sorted(SOURCES.glob("[0-9][0-9]-*/SOURCE.md")):
        meta: dict[str, str] = {"folder": md.parent.name}
        text = md.read_text(encoding="utf-8")
        front = text.split("---", 2)[1] if text.startswith("---") else ""
        for line in front.splitlines():
            m = re.match(r"^(\w+):\s*(.+)$", line)
            if m and m.group(1) != "files":
                meta[m.group(1)] = m.group(2).strip()
        out["S" + md.parent.name[:2]] = meta
    return out


def parse(text: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    cur: dict | None = None
    field: str | None = None
    for line in text.splitlines():
        if line.startswith("### "):
            cur = {"basis": []}
            out[line[4:].split()[0]] = cur
            field = None
            continue
        if cur is None or line.startswith("## "):
            cur = None if line.startswith("## ") else cur
            continue
        m = FIELD_RE.match(line)
        if m:
            label, value = m.group(1).strip().lower(), m.group(2).strip()
            field = "basis" if label == "basis" else FIELDS.get(label)
            if field and field != "basis":
                cur[field] = value
            continue
        b = BASIS_RE.match(line)
        if b and field == "basis":
            cur["basis"].append({"source": b.group(1), "locator": b.group(2).strip(), "quote": b.group(3).strip()})
        elif line.startswith("  ") and line.strip() and field and field != "basis":
            cur[field] = (cur.get(field, "") + " " + line.strip()).strip()  # wrapped continuation line
    return out


@lru_cache(maxsize=1)
def criteria() -> dict[str, dict]:
    return parse(ACCEPTANCE.read_text(encoding="utf-8")) if ACCEPTANCE.exists() else {}


def method_for(check_id: str) -> dict:
    """Acceptance block for a check, with basis entries resolved to their source metadata."""
    c = dict(criteria().get(check_id, {}))
    src = sources()
    c["basis"] = [
        dict(b, title=src.get(b["source"], {}).get("title", b["source"]), url=src.get(b["source"], {}).get("url", "")) for b in c.get("basis", [])
    ]
    c.setdefault("looks_at", "")
    c.setdefault("met_when", "")
    return c
