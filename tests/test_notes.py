"""Notes folder: search, read, create, and the path lock."""

from __future__ import annotations

import pytest

from integrations import notes
from integrations.notes import NotesError


def test_clear_message_without_configured_folder(config):
    with pytest.raises(NotesError, match="NOTES_DIR"):
        notes.read_note(config, "anything.md")


def test_search_finds_file_name_and_content(config_with_notes):
    root = config_with_notes.notes_dir
    (root / "target-audience.md").write_text("Include: specialist firms", encoding="utf-8")
    (root / "Misc.md").write_text("specialist firms appear in the text", encoding="utf-8")

    hits = notes.search_notes(config_with_notes, "target-audience")
    assert hits[0]["path"] == "target-audience.md"
    assert hits[0]["match"] == "file name"

    content = notes.search_notes(config_with_notes, "specialist firms")
    assert {h["path"] for h in content} == {"target-audience.md", "Misc.md"}


def test_path_outside_is_blocked(config_with_notes):
    """A model must not be able to invent a path that leads out of the folder."""
    with pytest.raises(NotesError, match="outside"):
        notes.read_note(config_with_notes, "../../secret.md")


def test_sibling_folder_with_same_prefix_is_blocked(tmp_path):
    """/notes-evil starts with the string "/notes" but is not inside it.
    The original startswith check let this through."""
    from tests.conftest import make_config

    root = tmp_path / "notes"
    root.mkdir()
    evil = tmp_path / "notes-evil"
    evil.mkdir()
    (evil / "secret.md").write_text("secret", encoding="utf-8")
    cfg = make_config(notes_dir=root)
    with pytest.raises(NotesError, match="outside"):
        notes.read_note(cfg, "../notes-evil/secret.md")
    with pytest.raises(NotesError, match="outside"):
        notes.create_note(cfg, "x", "y", folder="../notes-evil")


def test_create_note_never_overwrites(config_with_notes):
    notes.create_note(config_with_notes, "Research X", "first draft", folder="Research")
    notes.create_note(config_with_notes, "Research X", "second draft", folder="Research")

    folder = config_with_notes.notes_dir / "Research"
    names = sorted(p.name for p in folder.glob("*.md"))
    assert names == ["Research X 2.md", "Research X.md"]
    assert "first draft" in (folder / "Research X.md").read_text(encoding="utf-8")


def test_create_note_sanitises_the_title(config_with_notes):
    result = notes.create_note(config_with_notes, "Leads: Berlin/Brandenburg", "content")
    assert "/" not in result.split(": ", 1)[1].split("/")[-1]
    assert (config_with_notes.notes_dir / "Inbox").exists()
