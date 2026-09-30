"""Shared test fixtures.

All tests run without network and without an API key. Anything that would go
out runs in mock mode, against a fake client, or is never called.
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
        agent_model="test-model",
        effort="high",
        mock_llm=True,
        max_rounds=5,
        owner_name="",
        agent_name="Nightcrawler",
        answer_language="English",
        answer_style="concise",
        tavily_api_key="",
        min_pages=6,
        min_domains=4,
        profile_path=None,
        location_source="profile",
        notes_dir=None,
        research_folder="Research",
        target_group_note="target-audience.md",
        timezone="Europe/Berlin",
        log_level="INFO",
    )
    base.update(overrides)
    return Config(**base)


@pytest.fixture(autouse=True)
def _no_disk_geocode_cache(monkeypatch):
    """Tests must not read or write ~/.cache."""
    from integrations import profile

    monkeypatch.setattr(profile, "GEO_CACHE_FILE", None)


@pytest.fixture
def config() -> Config:
    return make_config()


@pytest.fixture
def config_with_notes(tmp_path) -> Config:
    return make_config(notes_dir=tmp_path)
