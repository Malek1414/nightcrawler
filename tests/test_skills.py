"""Skills: Frontmatter parsen, Index bauen, Inhalt nachladen."""

from __future__ import annotations

from core import skills


def test_alle_skills_haben_frontmatter():
    """Eine .md ohne sauberes Frontmatter fällt still raus. Das soll auffallen."""
    dateien = sorted(skills.SKILLS_DIR.glob("*.md"))
    geladen = {s["name"] for s in skills.load_all()}
    assert dateien, "keine Skill-Dateien gefunden"
    assert len(geladen) == len(dateien), (
        f"{len(dateien)} Dateien, aber nur {len(geladen)} geparst: "
        "irgendwo fehlt der ----Block oder das Feld name"
    )


def test_jeder_skill_hat_beschreibung():
    """Ohne description taucht der Skill im Index als Leerzeile auf."""
    for s in skills.load_all():
        assert s["description"], f"Skill '{s['name']}' hat keine description"


def test_index_enthaelt_nur_passende_skills():
    index = skills.index_block("research")
    assert "web-scraping" in index
    assert "read_skill" in index
    assert skills.index_block("gibt-es-nicht") == ""


def test_read_skill_liefert_body_ohne_frontmatter():
    body = skills.read_skill("web-scraping")
    assert body.startswith("# Web-Scraping")
    assert "description:" not in body.splitlines()[0]


def test_read_skill_unbekannt_nennt_die_vorhandenen():
    antwort = skills.read_skill("gibt-es-nicht")
    assert "gibt es nicht" in antwort
    assert "web-scraping" in antwort


def test_kein_skill_wird_still_abgeschnitten():
    """read_skill kappt bei MAX_SKILL_CHARS, ohne etwas zu sagen. Ein zu
    langer Skill verliert dann genau die Abschnitte am Ende, in denen bei uns
    die Grenzen und der Anstand stehen. Das darf nicht still passieren."""
    for s in skills.load_all():
        assert len(s["body"]) <= skills.MAX_SKILL_CHARS, (
            f"Skill '{s['name']}' ist {len(s['body'])} Zeichen lang, "
            f"read_skill liefert nur {skills.MAX_SKILL_CHARS}. Aufteilen."
        )


def test_querverweise_zeigen_auf_echte_skills():
    """Skills verweisen aufeinander ("Skill `seiten-index`"). Ein Tippfehler
    schickt das Modell auf einen Skill, den es nicht gibt, und es merkt es
    erst mitten in der Aufgabe."""
    import re

    bekannt = {s["name"] for s in skills.load_all()}
    muster = re.compile(r"Skills?\s+`([^`]+)`")
    for s in skills.load_all():
        for verweis in muster.findall(s["body"]):
            assert verweis in bekannt, (
                f"Skill '{s['name']}' verweist auf '{verweis}', den es nicht gibt. "
                f"Vorhanden: {sorted(bekannt)}"
            )


def test_kein_skill_verweist_auf_sich_selbst():
    import re

    muster = re.compile(r"Skills?\s+`([^`]+)`")
    for s in skills.load_all():
        assert s["name"] not in muster.findall(s["body"]), (
            f"Skill '{s['name']}' schickt das Modell zu sich selbst"
        )


def test_tool_spec_ist_gueltiges_schema():
    spec = skills.tool_spec()
    assert spec["function"]["name"] == "read_skill"
    assert spec["function"]["parameters"]["required"] == ["name"]
