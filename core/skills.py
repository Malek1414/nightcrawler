"""Skills: nachladbare Anleitungen für den Agent.

Jede Datei in skills/ ist ein Skill: Markdown mit Frontmatter (name,
description, agents). Nach dem Prinzip der Anthropic Agent Skills bekommt der
Agent im System-Prompt nur den Index (Name plus Einzeiler); den vollen Inhalt
lädt er bei Bedarf selbst über das read_skill-Tool. So bleibt der Prompt klein,
egal wie viele Skills dazukommen, und das Modell liest nur, was zur Aufgabe passt.

Neuen Skill hinzufügen heißt: eine .md-Datei nach dem Muster ablegen. Kein Code.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from core.llm import tool

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
MAX_SKILL_CHARS = 8000

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def _parse(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        logger.exception("Skill nicht lesbar: %s", path)
        return None
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    meta: dict = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(":")
        if value:
            meta[key.strip().lower()] = value.strip()
    agents = [a.strip() for a in meta.get("agents", "").split(",") if a.strip()]
    return {
        "name": meta.get("name") or path.stem,
        "description": meta.get("description", ""),
        "agents": agents,          # leer = Skill steht allen Agents zur Verfügung
        "body": m.group(2).strip(),
    }


def load_all() -> list[dict]:
    if not SKILLS_DIR.is_dir():
        return []
    out = []
    for path in sorted(SKILLS_DIR.glob("*.md")):
        skill = _parse(path)
        if skill:
            out.append(skill)
    return out


def for_agent(agent: str) -> list[dict]:
    return [s for s in load_all() if not s["agents"] or agent in s["agents"]]


def index_block(agent: str) -> str:
    """Skill-Index für den System-Prompt (nur Name und Beschreibung)."""
    entries = for_agent(agent)
    if not entries:
        return ""
    lines = [
        "",
        "Skills (ausführliche Anleitungen, ladbar über das read_skill-Tool).",
        "Passt ein Skill zur Aufgabe, lade ihn ZUERST und arbeite dann danach:",
    ]
    lines += [f"- {s['name']}: {s['description']}" for s in entries]
    return "\n" + "\n".join(lines)


def read_skill(name: str) -> str:
    wanted = str(name).strip().lower()
    for s in load_all():
        if s["name"].lower() == wanted:
            return s["body"][:MAX_SKILL_CHARS]
    known = ", ".join(s["name"] for s in load_all()) or "keine"
    return f"Skill '{name}' gibt es nicht. Vorhanden: {known}"


def tool_spec() -> dict:
    return tool(
        "read_skill",
        "Einen Skill (ausführliche Anleitung) laden. Nutze das, BEVOR du eine "
        "Aufgabe aus dem Gebiet eines Skills angehst.",
        {"name": {"type": "string", "description": "Skill-Name aus der Liste im Prompt"}},
        required=["name"],
    )
