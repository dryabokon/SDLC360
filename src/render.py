"""Render the single-file HTML: static mode (report embedded) or app mode (data fetched from the local server)."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from .acceptance import criteria, sources

TEMPLATE = Path(__file__).with_name("template.html")


def _sources() -> list[dict]:
    """Bundled sources with how many acceptance blocks cite each, for the How it works tab."""
    cited: dict[str, int] = {}
    for block in criteria().values():
        for b in block.get("basis", []):
            cited[b["source"]] = cited.get(b["source"], 0) + 1
    keys = ("title", "publisher", "published", "url")
    return [{"id": sid, **{k: m.get(k, "") for k in keys}, "cited": cited.get(sid, 0)} for sid, m in sources().items()]


def _template() -> str:
    return TEMPLATE.read_text(encoding="utf-8").replace("/*__SOURCES__*/[]", _embed(_sources()))


def _embed(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")


def render_html(report: dict) -> str:
    return _template().replace("__TITLE__", escape(f"SDLC 360° · {report['repo']['source']}")).replace("/*__REPORT__*/null", _embed(report))


def render_app() -> str:
    return _template().replace("__TITLE__", "SDLC 360°").replace('/*__MODE__*/"static"', '"app"')
