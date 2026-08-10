"""Zentrale Konfiguration: alle Werte kommen aus der .env.

Grundsatz: keine Keys, Pfade oder Namen im Code. Was fehlt, schaltet die
zugehoerige Funktion ab, statt den Start zu verhindern. Ohne NOTES_DIR
arbeitet der Agent eben ohne Notiz-Zugriff, ohne TAVILY_API_KEY nutzt er
nur die kostenlosen Wege.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


class ConfigError(Exception):
    """Fehlende oder ungültige Konfiguration."""


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Config:
    # --- LLM ---
    openai_api_key: str
    agent_model: str
    mock_llm: bool
    max_rounds: int

    # --- Auftritt (steckt nur im System-Prompt, nicht in der Logik) ---
    owner_name: str
    agent_name: str
    answer_language: str
    answer_style: str

    # --- Recherche ---
    tavily_api_key: str

    # --- Notizen (optional) ---
    # Ein Ordner mit Markdown-Dateien. Ein Obsidian-Vault ist genau das,
    # also funktioniert der auch, ohne dass hier irgendwas von Obsidian weiß.
    notes_dir: Path | None
    research_folder: str
    target_group_note: str

    # --- Sonstiges ---
    timezone: str
    log_level: str


def load_config() -> Config:
    """.env einlesen und prüfen. Wirft nur, wenn wirklich nichts gehen kann."""
    load_dotenv()
    notes_raw = os.getenv("NOTES_DIR", "").strip()

    config = Config(
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        agent_model=os.getenv("AGENT_MODEL", "gpt-4o").strip(),
        mock_llm=_parse_bool(os.getenv("MOCK_LLM", "false")),
        max_rounds=int(os.getenv("MAX_ROUNDS", "20") or 20),
        owner_name=os.getenv("OWNER_NAME", "").strip(),
        agent_name=os.getenv("AGENT_NAME", "Recherche-Agent").strip(),
        answer_language=os.getenv("ANSWER_LANGUAGE", "Deutsch").strip(),
        answer_style=os.getenv("ANSWER_STYLE", "kompakt").strip(),
        tavily_api_key=os.getenv("TAVILY_API_KEY", "").strip(),
        notes_dir=Path(notes_raw).expanduser() if notes_raw else None,
        research_folder=os.getenv("NOTES_RESEARCH_FOLDER", "Recherchen").strip() or "Recherchen",
        target_group_note=os.getenv("LEADS_TARGET_NOTE", "Zielgruppe.md").strip(),
        timezone=os.getenv("TIMEZONE", "Europe/Berlin").strip(),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
    )

    if not config.mock_llm and not config.openai_api_key:
        raise ConfigError(
            "OPENAI_API_KEY fehlt in der .env. Zum Ausprobieren ohne Kosten: MOCK_LLM=true"
        )
    return config
