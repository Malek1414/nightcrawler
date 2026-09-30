"""Central configuration: every value comes from the .env.

Principle: no keys, paths, or names in the code. Anything missing switches
the matching feature off instead of blocking startup. Without NOTES_DIR the
agent works without notes; without TAVILY_API_KEY it uses only the free
search routes; without a profile it ranks opportunities without personal
context and says so.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


class ConfigError(Exception):
    """Missing or invalid configuration."""


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError as e:
        raise ConfigError(f"{name} must be a whole number, got '{raw}'") from e


@dataclass(frozen=True)
class Config:
    # --- LLM ---
    agent_model: str
    effort: str
    mock_llm: bool
    max_rounds: int

    # --- Persona (prompt only, not logic) ---
    owner_name: str
    agent_name: str
    answer_language: str
    answer_style: str

    # --- Research ---
    tavily_api_key: str
    min_pages: int
    min_domains: int

    # --- User context ---
    # A TOML file describing who the agent works for: home base, budget,
    # travel limits, goals. See examples/profile.example.toml.
    profile_path: Path | None
    # "profile" = only what the profile says. "ip" = approximate location from
    # the public IP (sends your IP to ip-api.com; opt-in only).
    location_source: str

    # --- Notes (optional) ---
    # A folder of Markdown files. An Obsidian vault is exactly that.
    notes_dir: Path | None
    research_folder: str
    target_group_note: str

    # --- Misc ---
    timezone: str
    log_level: str


def load_config() -> Config:
    """Read and validate the .env. Raises only when nothing could work."""
    load_dotenv()
    notes_raw = os.getenv("NOTES_DIR", "").strip()
    profile_raw = os.getenv("PROFILE_PATH", "profile.toml").strip()
    profile_path = Path(profile_raw).expanduser() if profile_raw else None
    if profile_path is not None and not profile_path.is_absolute():
        profile_path = ROOT / profile_path

    config = Config(
        agent_model=os.getenv("AGENT_MODEL", "claude-opus-5").strip(),
        effort=os.getenv("EFFORT", "high").strip().lower(),
        mock_llm=_parse_bool(os.getenv("MOCK_LLM", "false")),
        max_rounds=_int("MAX_ROUNDS", 25),
        owner_name=os.getenv("OWNER_NAME", "").strip(),
        agent_name=os.getenv("AGENT_NAME", "Nightcrawler").strip(),
        answer_language=os.getenv("ANSWER_LANGUAGE", "English").strip(),
        answer_style=os.getenv("ANSWER_STYLE", "concise").strip(),
        tavily_api_key=os.getenv("TAVILY_API_KEY", "").strip(),
        min_pages=_int("MIN_PAGES", 6),
        min_domains=_int("MIN_DOMAINS", 4),
        profile_path=profile_path,
        location_source=os.getenv("LOCATION_SOURCE", "profile").strip().lower(),
        notes_dir=Path(notes_raw).expanduser() if notes_raw else None,
        research_folder=os.getenv("NOTES_RESEARCH_FOLDER", "Research").strip() or "Research",
        target_group_note=os.getenv("LEADS_TARGET_NOTE", "target-audience.md").strip(),
        timezone=os.getenv("TIMEZONE", "UTC").strip(),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
    )

    if config.effort not in ("low", "medium", "high", "xhigh", "max"):
        raise ConfigError(f"EFFORT must be low/medium/high/xhigh/max, got '{config.effort}'")
    if config.location_source not in ("profile", "ip"):
        raise ConfigError("LOCATION_SOURCE must be 'profile' or 'ip'")
    # The Anthropic SDK also resolves ANTHROPIC_AUTH_TOKEN and `ant auth login`
    # profiles, so a missing ANTHROPIC_API_KEY is not necessarily an error.
    return config
