"""Gemeinsame Test-Fixtures.

Alle Tests laufen ohne Netz und ohne API-Key. Was nach draußen gehen würde,
läuft im Mock-Modus oder wird gar nicht erst aufgerufen.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import Config  # noqa: E402


def make_config(**overrides) -> Config:
    base = dict(
        openai_api_key="",
        agent_model="test-model",
        mock_llm=True,
        max_rounds=5,
        owner_name="",
        agent_name="Recherche-Agent",
        answer_language="Deutsch",
        answer_style="kompakt",
        tavily_api_key="",
        notes_dir=None,
        research_folder="Recherchen",
        target_group_note="Zielgruppe.md",
        timezone="Europe/Berlin",
        log_level="INFO",
    )
    base.update(overrides)
    return Config(**base)


@pytest.fixture
def config() -> Config:
    return make_config()


@pytest.fixture
def config_with_notes(tmp_path) -> Config:
    return make_config(notes_dir=tmp_path)
