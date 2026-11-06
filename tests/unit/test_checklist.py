from pathlib import Path

from src.checklist import DEFAULT_CHECKLIST, PRIORITY_WEIGHT, parse, priority_from_weight, resolve
from src.methods import METHODS

SAMPLE = """
# title
text outside a section is ignored
- [sec.no_secrets] critical: No secrets.
## security
- [sec.no_secrets] critical: No secrets.
- [sec.policy] A SECURITY.md exists.
- [ ] nice: Keys rotate quarterly.
## docs
* [x] important: Onboarding takes under an hour.
"""


def test_parse_sections_priorities_and_custom_items():
    items = parse(SAMPLE)
    assert list(items) == ["security", "docs"]
    sec = items["security"]
    assert [i["id"] for i in sec] == ["sec.no_secrets", "sec.policy", "custom.security.keys-rotate-quarterly"]
    assert sec[0]["priority"] == "critical" and sec[0]["weight"] == PRIORITY_WEIGHT["critical"]
    assert sec[1]["priority"] == "important"  # default when omitted
    assert sec[2]["custom"] and sec[2]["priority"] == "nice"
    assert items["docs"][0]["custom"]


def test_priority_from_weight():
    assert [priority_from_weight(w) for w in (5, 4, 3, 2, 1, 0.5)] == ["critical", "critical", "important", "important", "nice", "nice"]


def test_resolve_prefers_explicit_then_repo_file_then_default(tmp_path: Path):
    assert resolve(tmp_path)["origin"] == "default"
    (tmp_path / ".sdlc360").mkdir()
    (tmp_path / ".sdlc360" / "expectations.md").write_text("## docs\n- [doc.readme] critical: README\n", encoding="utf-8")
    assert resolve(tmp_path)["origin"] == "repository"
    explicit = tmp_path / "mine.md"
    explicit.write_text("## docs\n", encoding="utf-8")
    assert resolve(tmp_path, explicit)["origin"] == "explicit"


def test_default_checklist_is_consistent():
    """Every expectation in the bundled checklist names a documented check, once, with 1-2 critical items per aspect."""
    items = parse(DEFAULT_CHECKLIST.read_text(encoding="utf-8"))
    ids = [i["id"] for its in items.values() for i in its]
    assert len(ids) == len(set(ids))
    assert not [i for i in ids if i not in METHODS], "checks without a 'how checked' description"
    for section, its in items.items():
        crit = sum(i["priority"] == "critical" for i in its)
        assert 1 <= crit <= 2, section
