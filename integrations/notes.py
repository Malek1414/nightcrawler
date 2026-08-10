"""Notiz-Ordner: suchen, lesen, neu anlegen.

Das ist bewusst ein simpler Ordner mit Markdown-Dateien. Ein Obsidian-Vault
ist genau das, also funktioniert der ohne Anpassung. Genauso gut geht ein
beliebiger Ordner, ein iCloud-Ordner oder ein geclontes Git-Repo.

Wofür der Agent das braucht, in dieser Reihenfolge:
1. Lesen, damit deine eigenen Vorgaben die Recherche steuern (Zielgruppe,
   Kriterien, frühere Recherche zum selben Thema). Was du schon entschieden
   hast, soll der Agent nicht neu erfinden.
2. Schreiben, damit aufwendige Ergebnisse nicht im Chat verloren gehen.

Sicherheitsprinzip: Es werden NUR neue Dateien angelegt. Bestehende Notizen
werden nie überschrieben oder verändert. Und jeder Pfad wird gegen den
Wurzelordner geprüft, damit ein "../../.ssh/id_rsa" nicht durchkommt.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

from core.config import Config

logger = logging.getLogger(__name__)

_SKIP_DIRS = {".obsidian", ".trash", ".git", "node_modules"}


class NotesError(Exception):
    pass


def _root(config: Config) -> Path:
    if not config.notes_dir or not config.notes_dir.exists():
        raise NotesError(
            "Notiz-Ordner nicht konfiguriert oder Pfad existiert nicht (NOTES_DIR in der .env)."
        )
    return config.notes_dir


def _iter_notes(root: Path):
    for path in root.rglob("*.md"):
        if not any(part in _SKIP_DIRS for part in path.parts):
            yield path


def search_notes(config: Config, query: str, limit: int = 10) -> list[dict]:
    """Sucht in Dateinamen und Inhalten (ohne Groß-/Kleinschreibung).
    Dateinamen-Treffer zuerst, die sind fast immer die gemeinten."""
    root = _root(config)
    q = query.strip().lower()
    name_hits, content_hits = [], []
    for path in _iter_notes(root):
        rel = str(path.relative_to(root))
        if q in path.stem.lower():
            name_hits.append({"path": rel, "match": "Dateiname"})
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        idx = text.lower().find(q)
        if idx != -1:
            start = max(0, idx - 60)
            excerpt = re.sub(r"\s+", " ", text[start: idx + 120]).strip()
            content_hits.append({"path": rel, "match": f"…{excerpt}…"})
        if len(name_hits) >= limit:
            break
    return (name_hits + content_hits)[:limit]


def read_note(config: Config, rel_path: str, max_chars: int = 6000) -> str:
    root = _root(config)
    path = (root / rel_path).resolve()
    if not str(path).startswith(str(root.resolve())):
        raise NotesError("Pfad liegt außerhalb des Notiz-Ordners.")
    if not path.exists():
        raise NotesError(f"Notiz nicht gefunden: {rel_path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:max_chars] + ("\n…[gekürzt]" if len(text) > max_chars else "")


def create_note(config: Config, title: str, content: str, folder: str = "Inbox") -> str:
    """Legt eine NEUE Notiz an (überschreibt nie)."""
    root = _root(config)
    safe_title = re.sub(r'[\\/:*?"<>|]', "-", title).strip() or "Notiz"
    target_dir = (root / folder).resolve()
    if not str(target_dir).startswith(str(root.resolve())):
        raise NotesError("Ordner liegt außerhalb des Notiz-Ordners.")
    target_dir.mkdir(parents=True, exist_ok=True)

    path = target_dir / f"{safe_title}.md"
    n = 2
    while path.exists():  # nie überschreiben, notfalls "Titel 2.md" und so weiter
        path = target_dir / f"{safe_title} {n}.md"
        n += 1

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    path.write_text(f"{content.rstrip()}\n\n---\n*Angelegt vom Recherche-Agent, {stamp}*\n",
                    encoding="utf-8")
    rel = path.relative_to(root)
    logger.info("Notiz angelegt: %s", rel)
    return f"Notiz angelegt: {rel}"
