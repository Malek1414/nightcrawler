"""Notes folder: search, read, create new.

Deliberately a plain folder of Markdown files. An Obsidian vault is exactly
that, so it works without changes. Any folder, an iCloud folder, or a cloned
Git repo works just as well.

What the agent needs it for, in this order:
1. Reading, so your own rules steer the research (target audience, criteria,
   earlier research on the same topic). What you already decided, the agent
   should not reinvent.
2. Writing, so expensive results do not get lost in the chat.

Safety principle: ONLY new files are created. Existing notes are never
overwritten or changed. Every path is checked against the root folder, so a
"../../.ssh/id_rsa" does not get through.
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
            "Notes folder not configured or path does not exist (NOTES_DIR in .env)."
        )
    return config.notes_dir.resolve()


def _inside(root: Path, path: Path) -> bool:
    # is_relative_to compares path components, so "/notes-evil" is not
    # mistaken for a child of "/notes" (a plain startswith check would be).
    return path == root or path.is_relative_to(root)


def _iter_notes(root: Path):
    for path in root.rglob("*.md"):
        if not any(part in _SKIP_DIRS for part in path.parts):
            yield path


def search_notes(config: Config, query: str, limit: int = 10) -> list[dict]:
    """Searches file names and contents (case-insensitive).
    File name hits come first; they are almost always the ones meant."""
    root = _root(config)
    q = query.strip().lower()
    name_hits, content_hits = [], []
    for path in _iter_notes(root):
        rel = str(path.relative_to(root))
        if q in path.stem.lower():
            name_hits.append({"path": rel, "match": "file name"})
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


def read_note(config: Config, rel_path: str, max_chars: int = 12000) -> str:
    root = _root(config)
    path = (root / rel_path).resolve()
    if not _inside(root, path):
        raise NotesError("Path is outside the notes folder.")
    if not path.exists():
        raise NotesError(f"Note not found: {rel_path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:max_chars] + ("\n…[truncated]" if len(text) > max_chars else "")


def create_note(config: Config, title: str, content: str, folder: str = "Inbox") -> str:
    """Creates a NEW note (never overwrites)."""
    root = _root(config)
    safe_title = re.sub(r'[\\/:*?"<>|]', "-", title).strip() or "Note"
    target_dir = (root / folder).resolve()
    if not _inside(root, target_dir):
        raise NotesError("Folder is outside the notes folder.")
    target_dir.mkdir(parents=True, exist_ok=True)

    path = target_dir / f"{safe_title}.md"
    n = 2
    while path.exists():  # never overwrite; fall back to "Title 2.md" and so on
        path = target_dir / f"{safe_title} {n}.md"
        n += 1

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    path.write_text(f"{content.rstrip()}\n\n---\n*Created by Nightcrawler, {stamp}*\n",
                    encoding="utf-8")
    rel = path.relative_to(root)
    logger.info("Note created: %s", rel)
    return f"Note created: {rel}"
