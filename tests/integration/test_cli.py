"""The CLI end to end: scan -> list -> render, the way README.md documents it."""

import json

import pytest

from src.cli import main

pytestmark = pytest.mark.integration


def test_scan_list_render(make_repo, tmp_path, capsys):
    root = make_repo({"README.md": "# x\n", "app/main.py": "print(1)\n"}, name="cli-demo")
    runs, cache = str(tmp_path / "runs"), str(tmp_path / "cache")

    assert main(["scan", str(root), "--no-history", "--runs-dir", runs, "--cache-dir", cache]) == 0
    (run_dir,) = (tmp_path / "runs").iterdir()
    assert run_dir.name.endswith("_cli-demo")

    assert main(["list", "--runs-dir", runs]) == 0
    assert "cli-demo" in capsys.readouterr().out

    review = {"dimensions": {"docs": {"adjust": 5, "notes": ["checked by hand"]}}}
    (run_dir / "review.json").write_text(json.dumps(review), encoding="utf-8")
    assert main(["render", str(run_dir)]) == 0
    docs = next(d for d in json.loads((run_dir / "report.json").read_text(encoding="utf-8"))["dimensions"] if d["id"] == "docs")
    assert docs["adjust"] == 5 and docs["review_notes"] == ["checked by hand"]


def test_scan_rejects_bad_target(tmp_path):
    with pytest.raises((ValueError, SystemExit)):
        main(["scan", str(tmp_path / "missing"), "--no-history", "--runs-dir", str(tmp_path / "runs")])
