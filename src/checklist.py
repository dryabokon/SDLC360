"""Capability catalog: a markdown file mapping capabilities to automated checks (assessment/capabilities.md).

    ## <aspect-id>
    - [check.id] critical: capability text     -> scored by the scanner
    - [ ] important: capability text           -> your own; judged by a reviewer via review.json

Priorities are categorical on purpose (no false precision). Their numeric weights and the `critical` gate
live here, in one place. Profiles (src/profiles.py) adjust the catalog per use.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOG = PROJECT_ROOT / "assessment" / "capabilities.md"
REPO_CHECKLIST = (".sdlc360/capabilities.md", ".sdlc360/expectations.md")  # the second: name before 0.4

PRIORITIES = ("critical", "important", "nice")
PRIORITY_WEIGHT = {"critical": 5.0, "important": 3.0, "nice": 1.0}
# critical gate: an aspect cannot score above these caps while a critical capability is not / partially met
CRITICAL_CAP = {"fail": 49.0, "partial": 74.0}

ITEM_RE = re.compile(r"^\s*[-*]\s*\[([^\]]*)\]\s*(?:(critical|important|nice)\s*:\s*)?(.+?)\s*$", re.I)
SECTION_RE = re.compile(r"^##\s+([\w-]+)")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48]


def priority_from_weight(w: float) -> str:
    """For scanner checks not mentioned in a checklist."""
    return "critical" if w >= 4 else "important" if w >= 2 else "nice"


def parse(text: str) -> dict[str, list[dict]]:
    """Return {dimension_id: [{id, text, priority, weight, custom}]} in file order."""
    out: dict[str, list[dict]] = {}
    section = None
    for line in text.splitlines():
        m = SECTION_RE.match(line)
        if m:
            section = m.group(1).lower()
            out.setdefault(section, [])
            continue
        m = ITEM_RE.match(line)
        if not (m and section):
            continue
        ref, prio, body = m.group(1).strip(), (m.group(2) or "important").lower(), m.group(3)
        custom = ref in ("", "x", "X")
        out[section].append(
            {
                "id": f"custom.{section}.{_slug(body)}" if custom else ref,
                "text": body,
                "priority": prio,
                "weight": PRIORITY_WEIGHT[prio],
                "custom": custom,
            }
        )
    return out
