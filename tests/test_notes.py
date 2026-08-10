"""Notiz-Ordner: suchen, lesen, anlegen, und die Pfad-Sperre."""

from __future__ import annotations

import pytest

from integrations import notes
from integrations.notes import NotesError


def test_ohne_konfigurierten_ordner_klare_meldung(config):
    with pytest.raises(NotesError, match="NOTES_DIR"):
        notes.read_note(config, "irgendwas.md")


def test_suche_findet_dateiname_und_inhalt(config_with_notes):
    root = config_with_notes.notes_dir
    (root / "Zielgruppe.md").write_text("Positivliste: Fachbetriebe", encoding="utf-8")
    (root / "Sonstiges.md").write_text("Hier steht Fachbetriebe im Text", encoding="utf-8")

    treffer = notes.search_notes(config_with_notes, "zielgruppe")
    assert treffer[0]["path"] == "Zielgruppe.md"
    assert treffer[0]["match"] == "Dateiname"

    inhalt = notes.search_notes(config_with_notes, "Fachbetriebe")
    assert {t["path"] for t in inhalt} == {"Zielgruppe.md", "Sonstiges.md"}


def test_pfad_ausserhalb_wird_geblockt(config_with_notes):
    """Ein Modell darf keinen Pfad erfinden, der aus dem Ordner herausführt."""
    with pytest.raises(NotesError, match="außerhalb"):
        notes.read_note(config_with_notes, "../../geheim.md")


def test_create_note_ueberschreibt_nie(config_with_notes):
    notes.create_note(config_with_notes, "Recherche X", "erste Fassung", folder="Recherchen")
    notes.create_note(config_with_notes, "Recherche X", "zweite Fassung", folder="Recherchen")

    ordner = config_with_notes.notes_dir / "Recherchen"
    namen = sorted(p.name for p in ordner.glob("*.md"))
    assert namen == ["Recherche X 2.md", "Recherche X.md"]
    assert "erste Fassung" in (ordner / "Recherche X.md").read_text(encoding="utf-8")


def test_create_note_entschaerft_den_titel(config_with_notes):
    ergebnis = notes.create_note(config_with_notes, "Leads: Berlin/Brandenburg", "Inhalt")
    assert "/" not in ergebnis.split(": ", 1)[1].split("/")[-1]
    assert (config_with_notes.notes_dir / "Inbox").exists()
