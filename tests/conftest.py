"""Shared fixtures: build throw-away git repositories from a {path: content} map."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

GIT = ["git", "-c", "user.name=sdlc360-test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false"]


def _git(root: Path, *args: str) -> None:
    subprocess.run([*GIT, *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def make_repo(tmp_path: Path) -> Callable[..., Path]:
    def build(files: dict[str, str], name: str = "repo") -> Path:
        root = tmp_path / name
        root.mkdir()
        _git(root, "init", "-q", "-b", "main")
        for rel, text in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8", newline="\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "fixture", "--allow-empty")
        return root

    return build
