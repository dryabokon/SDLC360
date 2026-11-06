"""Render the single-file HTML: static mode (report embedded) or app mode (data fetched from the local server)."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

TEMPLATE = Path(__file__).with_name("template.html")


def _template() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def _embed(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")


def render_html(report: dict) -> str:
    return _template().replace("__TITLE__", escape(f"SDLC 360° · {report['repo']['source']}")).replace("/*__REPORT__*/null", _embed(report))


def render_app() -> str:
    return _template().replace("__TITLE__", "SDLC 360°").replace('/*__MODE__*/"static"', '"app"')
