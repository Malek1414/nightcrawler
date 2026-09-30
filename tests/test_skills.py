"""Skills: parse frontmatter, build the index, load content."""

from __future__ import annotations

import re

from core import skills

_REF = re.compile(r"[Ss]kills?\s+`([^`]+)`")


def test_all_skills_have_frontmatter():
    """A .md without clean frontmatter drops out silently. That should show."""
    files = sorted(skills.SKILLS_DIR.glob("*.md"))
    loaded = {s["name"] for s in skills.load_all()}
    assert files, "no skill files found"
    assert len(loaded) == len(files), (
        f"{len(files)} files, but only {len(loaded)} parsed: "
        "a --- block or the name field is missing somewhere"
    )


def test_every_skill_has_a_description():
    """Without a description the skill shows up in the index as an empty line."""
    for s in skills.load_all():
        assert s["description"], f"Skill '{s['name']}' has no description"


def test_skills_are_english():
    for path in skills.SKILLS_DIR.glob("*.md"):
        assert not re.search(r"[äöüÄÖÜß]", path.read_text(encoding="utf-8")), path.name


def test_index_contains_only_matching_skills():
    index = skills.index_block("research")
    assert "web-scraping" in index and "opportunity-scout" in index
    assert "read_skill" in index
    assert skills.index_block("does-not-exist") == ""


def test_read_skill_returns_body_without_frontmatter():
    body = skills.read_skill("web-scraping")
    assert body.startswith("# Web Scraping")
    assert "description:" not in body.splitlines()[0]


def test_read_skill_unknown_lists_the_available_ones():
    answer = skills.read_skill("does-not-exist")
    assert "does not exist" in answer
    assert "web-scraping" in answer


def test_no_skill_is_silently_truncated():
    """read_skill cuts at MAX_SKILL_CHARS without saying so. A skill that is
    too long loses exactly the closing sections where the limits and the
    etiquette live. That must not happen silently."""
    for s in skills.load_all():
        assert len(s["body"]) <= skills.MAX_SKILL_CHARS, (
            f"Skill '{s['name']}' is {len(s['body'])} characters, "
            f"read_skill returns only {skills.MAX_SKILL_CHARS}. Split it."
        )


def test_cross_references_point_to_real_skills():
    """Skills reference each other ("skill `site-index`"). A typo sends the
    model to a skill that does not exist, and it only notices mid-task."""
    known = {s["name"] for s in skills.load_all()}
    for s in skills.load_all():
        for ref in _REF.findall(s["body"]):
            assert ref in known, (
                f"Skill '{s['name']}' references '{ref}', which does not exist. "
                f"Available: {sorted(known)}"
            )


def test_no_skill_references_itself():
    for s in skills.load_all():
        assert s["name"] not in _REF.findall(s["body"]), (
            f"Skill '{s['name']}' sends the model to itself"
        )


def test_tool_spec_is_a_valid_schema():
    spec = skills.tool_spec()
    assert spec["name"] == "read_skill"
    assert spec["input_schema"]["required"] == ["name"]
