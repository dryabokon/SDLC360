"""Profiles: validation, overrides of the catalog, thresholds in the rules and in the acceptance texts."""

import json

import pytest

from src import profiles
from src.acceptance import method_for
from src.profiles import PARAMS, checklist, fill, validate
from src.repo import Repo
from src.runner import rerender, run_scan
from src.scanner import scan


@pytest.fixture
def tmp_profiles(tmp_path, monkeypatch):
    """Write profiles into a temporary folder; the bundled ones are copied so `load` still finds them."""
    d = tmp_path / "profiles"
    d.mkdir()
    for f in profiles.PROFILES.glob("*.json"):
        (d / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(profiles, "PROFILES", d)
    return d


def test_bundled_profiles_are_valid():
    ids = [p["id"] for p in profiles.list_profiles()]
    assert ids[0] == "standard" and "prototype" in ids
    for pid in ids:
        assert checklist(pid)["items"]


def test_standard_profile_is_the_catalog():
    cl = checklist("standard")
    assert cl["params"] == profiles.defaults()
    assert sum(len(v) for v in cl["items"].values()) == 71


def test_profile_switches_off_reprioritises_and_adds_own_capabilities(tmp_profiles):
    profiles.save(
        "team",
        {
            "name": "Team",
            "capabilities": {
                "arch.adr": {"enabled": False},
                "test.coverage": {"priority": "critical"},
                "doc.readme": {"params": {"target_words": 100}},
            },
            "custom": [
                {"aspect": "security", "text": "Keys are rotated quarterly.", "priority": "nice", "met_when": "A rotation in the last 90 days."}
            ],
        },
    )
    cl = checklist("team")
    ids = {i["id"]: i for its in cl["items"].values() for i in its}
    assert "arch.adr" not in ids
    assert ids["test.coverage"]["priority"] == "critical"
    assert ids["custom.security.keys-are-rotated-quarterly"]["met_when"] == "A rotation in the last 90 days."
    assert cl["params"]["doc.readme"] == {"target_words": 100}


def test_validate_rejects_bad_input():
    with pytest.raises(ValueError, match="between"):
        validate({"name": "x", "capabilities": {"doc.readme": {"params": {"target_words": -5}}}})
    with pytest.raises(ValueError, match="number"):
        validate({"name": "x", "capabilities": {"doc.readme": {"params": {"target_words": "many"}}}})
    with pytest.raises(ValueError, match="name"):
        validate({"name": " "})
    with pytest.raises(ValueError, match="aspect"):
        validate({"name": "x", "custom": [{"aspect": "nope", "text": "t"}]})
    clean = validate(
        {"name": "x", "capabilities": {"no.such": {"enabled": False}, "doc.readme": {"priority": "urgent", "params": {"target_words": 400}}}}
    )
    assert clean["capabilities"] == {}  # unknown ids, unknown priorities and default values are not stored


def test_standard_is_read_only_and_ids_are_safe(tmp_profiles):
    with pytest.raises(ValueError, match="cannot be changed"):
        profiles.save("standard", {"name": "Standard"})
    with pytest.raises(ValueError, match="Bad profile id"):
        profiles.save("../evil", {"name": "x"})
    with pytest.raises(ValueError, match="cannot be deleted"):
        profiles.delete("standard")


def test_fill_states_the_thresholds_in_force():
    assert fill("{target*0.85} or more (target: {target})", {"target": 3}) == "3 or more (target: 3)"
    assert fill("ratio {target_ratio*0.35}", {"target_ratio": 0.4}) == "ratio 0.14"
    assert fill("{unknown} stays", {"target": 3}) == "{unknown} stays"
    assert "about 80 days" in method_for("doc.freshness")["met_when"]
    assert "at least 170 words" in method_for("doc.readme", {"target_words": 200})["met_when"]


def test_every_parameter_is_used_by_its_rule_and_its_text():
    """A parameter that no rule reads or no text states would make the settings tab lie."""
    from pathlib import Path

    rules = "".join(p.read_text(encoding="utf-8") for p in Path("src/dimensions").glob("*.py"))
    for cid, ps in PARAMS.items():
        block = json.dumps(method_for(cid, {p.key: p.default for p in ps}))
        assert "{" + ps[0].key not in block, f"{cid}: placeholder not filled"
        for p in ps:
            assert f'"{cid}", "{p.key}"' in rules, f"{cid}.{p.key} is not read by any rule"


def test_threshold_changes_the_verdict(make_repo):
    root = make_repo({"README.md": "word " * 120, "app/main.py": "x = 1\n"})
    strict, lenient = Repo(root), Repo(root)
    s = scan(strict, only=["docs"])
    cl = checklist("standard")
    cl["params"]["doc.readme"] = {"target_words": 100}
    lenient_report = scan(lenient, only=["docs"], checklist=cl)

    def status(r):
        return next(c["status"] for d in r["dimensions"] for c in d["checks"] if c["id"] == "doc.readme")

    assert status(s) == "fail" and status(lenient_report) == "pass"


def test_rerender_applies_a_profile_without_rescanning(make_repo, tmp_path, tmp_profiles):
    run = run_scan(str(make_repo({"README.md": "hello\n"})), history_points=0, runs_dir=tmp_path / "runs", cache_dir=tmp_path / "c")
    profiles.save(
        "relaxed",
        {"name": "Relaxed", "capabilities": {"doc.readme": {"enabled": False, "params": {}}, "test.ratio": {"params": {"target_ratio": 1}}}},
    )
    rerender(run, profile="relaxed")
    rep = json.loads((run / "report.json").read_text(encoding="utf-8"))
    ids = [c["id"] for d in rep["dimensions"] for c in d["checks"]]
    assert "doc.readme" not in ids
    assert rep["checklist"]["profile"]["id"] == "relaxed"
    assert rep["thresholds_changed"] == ["test.ratio"]  # needs a re-scan; the run still shows the thresholds it used
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["options"]["profile"] == "standard" and "--profile standard" in manifest["reproduce"]
