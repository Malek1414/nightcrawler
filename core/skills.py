"""Skills: instructions the agent loads on demand.

Every file in skills/ is a skill: Markdown with frontmatter (name,
description, agents). Following the Anthropic Agent Skills principle, the
system prompt carries only the index (name plus one line); the agent loads the
full text itself through the read_skill tool when a task calls for it. The
prompt stays small no matter how many skills exist, and the model reads only
what fits the task.

Adding a skill means dropping a .md file into skills/. No code.
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
        logger.exception("Skill not readable: %s", path)
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
        "agents": agents,          # empty = available to every agent
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
    """Skill index for the system prompt (name and description only)."""
    entries = for_agent(agent)
    if not entries:
        return ""
    lines = [
        "",
        "Skills (detailed instructions, loadable with the read_skill tool).",
        "If a skill fits the task, load it FIRST and then work by it:",
    ]
    lines += [f"- {s['name']}: {s['description']}" for s in entries]
    return "\n" + "\n".join(lines)


def read_skill(name: str) -> str:
    wanted = str(name).strip().lower()
    for s in load_all():
        if s["name"].lower() == wanted:
            return s["body"][:MAX_SKILL_CHARS]
    known = ", ".join(s["name"] for s in load_all()) or "none"
    return f"Skill '{name}' does not exist. Available: {known}"


def tool_spec() -> dict:
    return tool(
        "read_skill",
        "Load a skill (detailed instructions). Use this BEFORE starting a task "
        "that falls in a skill's area.",
        {"name": {"type": "string", "description": "Skill name from the list in the prompt"}},
        required=["name"],
    )
