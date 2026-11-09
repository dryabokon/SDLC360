"""Acceptance criteria: how each capability is judged, in plain language.

One markdown file per aspect in assessment/acceptance-criteria/. They hold the "how checked / when met" texts shown
next to the evidence, and the published basis (assessment/references/) that justifies each capability:

    ## sec.no_secrets: No secrets are committed.

    **Accepted when.** one plain sentence; thresholds as {key} (shown first, edited in the app)

    **How we check.** what the scanner looks at

    - **Met:** ...
    - **Partially met:** ...
    - **Not met:** ...
    - **Not applicable:** ...                       (optional)

    **What the check cannot see.** limits of the rule
    **Known flaw.** where the rule does not yet check what the capability says   (optional)

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

from .profiles import defaults, fill

ROOT = Path(__file__).resolve().parent.parent
CRITERIA = ROOT / "assessment" / "acceptance-criteria"
REFERENCES = ROOT / "assessment" / "references"

PARAGRAPHS = {
    "accepted when": "accepted",
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


FILE_RE = re.compile(r"^\s*-\s+(commit|local)\s+(\S+)\s+([0-9a-f]{64})\s*(\S*)\s*$")


@lru_cache(maxsize=1)
def references() -> dict[str, dict]:
    """<folder> -> {id, title, publisher, published, url, license, ...} from assessment/references/<folder>/README.md.

    Also `files` (the retrieved originals: where they are kept, SHA-256, where they came from) and `key_points`
    (the bullets under "## Key points"). Together they are the reference card the app shows instead of a bare link,
    so a citation stays checkable when the publisher's page moves or changes.
    """
    out = {}
    for md in sorted(REFERENCES.glob("*/README.md")):
        meta: dict = {"folder": md.parent.name, "files": [], "key_points": []}
        text = md.read_text(encoding="utf-8")
        parts = text.split("---", 2) if text.startswith("---") else ["", "", text]
        for line in parts[1].splitlines():
            m = re.match(r"^(\w+):\s*(.+)$", line)
            f = FILE_RE.match(line)
            if f:
                meta["files"].append(
                    {"stored": "in git" if f.group(1) == "commit" else "local copy", "name": f.group(2), "sha256": f.group(3), "from": f.group(4)}
                )
            elif m and m.group(1) != "files":
                meta[m.group(1)] = m.group(2).strip()
        section = ""
        for line in parts[2].splitlines():
            if line.startswith("## "):
                section = line[3:].strip().lower()
            elif section == "key points" and line.startswith("- "):
                meta["key_points"].append(line[2:].strip())
            elif section == "key points" and line.startswith("  ") and line.strip() and meta["key_points"]:
                meta["key_points"][-1] += " " + line.strip()  # wrapped bullet
        out[md.parent.name] = meta
    return out


def reference_cards(source_ids: set[str]) -> dict[str, dict]:
    """The cards of the cited references, embedded in a report so it stays self-contained (also as a static file)."""
    keys = ("title", "publisher", "authors", "published", "kind", "retrieved", "license", "url", "files", "key_points")
    refs = references()
    return {s: {k: refs[s][k] for k in keys if k in refs[s]} for s in sorted(source_ids) if s in refs}


def parse(text: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    cur: dict | None = None
    field: str | None = None
    quote: list[str] = []
    for line in text.splitlines():
        h = HEADING_RE.match(line)
        if h:
            cur = {"basis": [], "capability": h.group(2).strip()}
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


def method_for(check_id: str, params: dict | None = None) -> dict:
    """Acceptance block for a check, thresholds filled in, basis entries resolved to their reference metadata."""
    values = {**defaults().get(check_id, {}), **(params or {})}  # keys unknown to this version (older runs) are ignored by fill()
    c: dict = {k: fill(v, values) if isinstance(v, str) else v for k, v in criteria().get(check_id, {}).items()}
    refs = references()
    c["basis"] = [
        dict(b, title=refs.get(b["source"], {}).get("title", b["source"]), url=refs.get(b["source"], {}).get("url", "")) for b in c.get("basis", [])
    ]
    c.setdefault("looks_at", "")
    c.setdefault("met_when", "")
    return c
