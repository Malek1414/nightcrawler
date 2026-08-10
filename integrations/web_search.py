"""Fallback-Websuche über die eingebaute Websuche des Modells (Responses API).

Nur als Notausgang gedacht: Wenn der Tool-Loop komplett scheitert (Netzfehler,
kaputte Antwort, Rate-Limit), bekommt der Nutzer wenigstens eine Antwort mit
Quellen statt eines Tracebacks. Die eigentliche Arbeit macht agent.py.
"""

from __future__ import annotations

import logging

from core.config import Config
from core.llm import get_client, record_usage

logger = logging.getLogger(__name__)

_INSTRUCTIONS = (
    "Du bist ein Recherche-Assistent. Beantworte die Frage aktuell und präzise. "
    "Nenne am Ende die wichtigsten Quellen als Links (max. 5). Antworte kompakt."
)


def search(config: Config, query: str) -> str:
    if config.mock_llm:
        return f"[Mock] Websuche zu: {query}"

    client = get_client(config)
    last_error: Exception | None = None
    # Tool-Name variiert je nach API-Version, beide probieren.
    for tool_type in ("web_search", "web_search_preview"):
        try:
            response = client.responses.create(
                model=config.agent_model,
                tools=[{"type": tool_type}],
                instructions=_INSTRUCTIONS,
                input=query,
            )
            record_usage(config, "research-fallback", config.agent_model,
                         getattr(response, "usage", None))
            return response.output_text.strip()
        except Exception as e:
            last_error = e
            logger.warning("Websuche mit tool '%s' fehlgeschlagen: %s", tool_type, e)
    raise RuntimeError(f"Websuche fehlgeschlagen: {last_error}")
