"""Acceptance criteria: how each expectation is judged, in plain language.

One markdown file per aspect in assessment/acceptance-criteria/. They hold the "how checked / when met" texts shown
next to the evidence, and the published basis (assessment/references/) that justifies each expectation:

    ## sec.no_secrets: No secrets are committed.

    **How we check.** what the scanner looks at

    - **Met:** ...
    - **Partially met:** ...
    - **Not met:** ...
    - **Not applicable:** ...                       (optional)

    **What the check cannot see.** limits of the rule
    **Known flaw.** where the rule does not yet check what the expectation says   (optional)

    **Why we expect it.**

    > verbatim quote
    >
    > — [nist-ssdf](../references/nist-ssdf/), PW.1.3, p. 20 · direct

    **Our convention.** why we expect it without a published basis (instead of quotes)
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CRITERIA = ROOT / "assessment" / "acceptance-criteria"
REFERENCES = ROOT / "assessment" / "references"

PARAGRAPHS = {
    "how we check": "looks_at",
    "what the check cannot see": "limits",
    "known flaw": "known_gap",
    "our convention": "convention",
    "why we expect it": "basis",
}
VERDICTS = {"met": "met_when", "partially met": "partial_when", "not met": "not_met_when", "not applicable": "na_when"}
HEADING_RE = re.compile(r"^## ([\w.-]+):\s*(.*)$")
PARAGRAPH_RE = re.compile(r"^\*\*([A-Za-z ]+)\.\*\*\s*(.*)$")
VERDICT_RE = re.compile(r"^- \*\*([A-Za-z ]+):\*\*\s*(.*)$")
CITATION_RE = re.compile(r"^>\s*— \[([\w.-]+)\]\([^)]*\),?\s*(.*?)\s*·\s*(direct|supporting)\s*$")


@lru_cache(maxsize=1)
def references() -> dict[str, dict]:
    """<folder> -> {id, title, publisher, published, url, license, ...} from assessment/references/<folder>/README.md."""
    out = {}
    for md in sorted(REFERENCES.glob("*/README.md")):
        meta: dict[str, str] = {"folder": md.parent.name}
        text = md.read_text(encoding="utf-8")
        front = text.split("---", 2)[1] if text.startswith("---") else ""
        for line in front.splitlines():
            m = re.match(r"^(\w+):\s*(.+)$", line)
            if m and m.group(1) != "files":
                meta[m.group(1)] = m.group(2).strip()
        out[md.parent.name] = meta
    return out


def parse(text: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    cur: dict | None = None
    field: str | None = None
    quote: list[str] = []
    for line in text.splitlines():
        h = HEADING_RE.match(line)
        if h:
            cur = {"basis": [], "expectation": h.group(2).strip()}
            out[h.group(1)] = cur
            field, quote = None, []
            continue
        if cur is None:
            continue
        if line.startswith(">"):
            c = CITATION_RE.match(line)
            if c:
                cur["basis"].append({"source": c.group(1), "locator": c.group(2).strip(), "strength": c.group(3), "quote": " ".join(quote)})
                quote = []
            elif line[1:].strip():
                quote.append(line[1:].strip())
            field = None
            continue
        p = PARAGRAPH_RE.match(line)
        v = VERDICT_RE.match(line)
        if p and p.group(1).lower() in PARAGRAPHS:
            field = PARAGRAPHS[p.group(1).lower()]
            if field != "basis":
                cur[field] = p.group(2).strip()
        elif v and v.group(1).lower() in VERDICTS:
            field = VERDICTS[v.group(1).lower()]
            cur[field] = v.group(2).strip()
        elif line.strip() and field and field != "basis":
            cur[field] = (cur.get(field, "") + " " + line.strip()).strip()  # wrapped continuation line
        elif not line.strip() and field and not field.endswith("_when"):
            field = None
    return out


@lru_cache(maxsize=1)
def criteria() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for md in sorted(CRITERIA.glob("*.md")):
        out.update(parse(md.read_text(encoding="utf-8")))
    return out


def method_for(check_id: str) -> dict:
    """Acceptance block for a check, with basis entries resolved to their reference metadata."""
    c = dict(criteria().get(check_id, {}))
    refs = references()
    c["basis"] = [
        dict(b, title=refs.get(b["source"], {}).get("title", b["source"]), url=refs.get(b["source"], {}).get("url", "")) for b in c.get("basis", [])
    ]
    c.setdefault("looks_at", "")
    c.setdefault("met_when", "")
    return c
