"""LLM-Zugriff: Client, Tool-Loop, Mock-Modus.

Der Tool-Loop ist das Herz des Agents. Er ruft das Modell, führt die
angeforderten Tools aus, gibt die Ergebnisse zurück und wiederholt das, bis
das Modell final antwortet oder max_rounds erreicht ist.

Ein Detail, das den Unterschied macht: Tools, die nur lesen, laufen
gleichzeitig. Fordert das Modell in einer Runde drei Suchanfragen an
(derselbe Begriff plus Synonym plus englische Variante), kostet das kaum mehr
Zeit als eine. Alles, was schreibt, bleibt sequentiell.

Alle Funktionen sind blockierend. In einem Bot oder Webserver gehören sie in
einen eigenen Thread (asyncio.to_thread).
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from core.config import Config

logger = logging.getLogger(__name__)

# Tools ohne Nebenwirkungen: reines Lesen, in beliebiger Reihenfolge
# wiederholbar. Nur diese dürfen parallel laufen.
PARALLEL_SAFE_TOOLS = {
    "web_search", "read_page", "youtube_transcript",
    "search_notes", "read_note", "read_skill",
}
MAX_PARALLEL_TOOLS = 6
MAX_TOOL_RESULT_CHARS = 8000

# Token-Verbrauch pro Lauf, rein zur Anzeige. Wer das dauerhaft braucht,
# schreibt hier in seine Datenbank statt in ein Dict.
USAGE: dict[str, dict[str, int]] = defaultdict(lambda: {"in": 0, "out": 0, "calls": 0})

_client = None
_client_key: str | None = None


def get_client(config: Config):
    """OpenAI-Client, pro Prozess gecacht."""
    global _client, _client_key
    if _client is None or _client_key != config.openai_api_key:
        from openai import OpenAI

        _client = OpenAI(api_key=config.openai_api_key)
        _client_key = config.openai_api_key
    return _client


def record_usage(config: Config, agent: str, model: str, usage) -> None:
    """Token-Verbrauch verbuchen. Darf nie den Lauf abbrechen.

    Versteht beide OpenAI-Formate: chat.completions (prompt_/completion_tokens)
    und responses (input_/output_tokens).
    """
    if usage is None or config.mock_llm:
        return
    try:
        tokens_in = int(getattr(usage, "prompt_tokens", 0) or getattr(usage, "input_tokens", 0) or 0)
        tokens_out = int(getattr(usage, "completion_tokens", 0) or getattr(usage, "output_tokens", 0) or 0)
        entry = USAGE[f"{agent}:{model}"]
        entry["in"] += tokens_in
        entry["out"] += tokens_out
        entry["calls"] += 1
    except Exception:
        logger.exception("Token-Tracking fehlgeschlagen")


def usage_summary() -> str:
    """Einzeiler für die Konsole am Ende eines Laufs."""
    if not USAGE:
        return "kein Verbrauch erfasst"
    return " | ".join(
        f"{key}: {v['calls']} Aufrufe, {v['in']} in / {v['out']} out"
        for key, v in USAGE.items()
    )


def _run_tool(handlers: dict | None, name: str, args: dict) -> str:
    """Ein Tool ausführen. Fehler gehen als Text zurück ans Modell, nie als Crash.

    Wichtig fürs Verhalten: Das Modell soll auf einen kaputten Abruf reagieren
    können (andere Quelle nehmen), statt dass der ganze Lauf stirbt.
    """
    handler = (handlers or {}).get(name)
    if handler is None:
        return f"Fehler: unbekanntes Tool '{name}'"
    try:
        return handler(**args)
    except Exception as e:
        logger.exception("Tool '%s' fehlgeschlagen", name)
        return f"Fehler in {name}: {e}"


def run_tool_loop(
    config: Config,
    model: str,
    system: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    handlers: dict[str, Callable[..., str]] | None = None,
    max_rounds: int = 8,
    agent: str = "agent",
) -> str:
    """Chat-Completion mit Function-Calling-Schleife.

    `handlers` bildet Tool-Namen auf Python-Funktionen ab. Deren Rückgabe
    (String) geht als Tool-Ergebnis zurück ans Modell, bis es final antwortet.
    """
    if config.mock_llm:
        return f"[Mock] Antwort von {model} auf: {messages[-1]['content'][:80]}"

    client = get_client(config)
    convo = [{"role": "system", "content": system}, *messages]

    for _ in range(max_rounds):
        response = client.chat.completions.create(
            model=model,
            messages=convo,
            tools=tools or None,
        )
        record_usage(config, agent, model, getattr(response, "usage", None))
        msg = response.choices[0].message

        if not msg.tool_calls:
            return (msg.content or "").strip()

        convo.append(
            {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
            }
        )
        calls = []
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            logger.info("Tool-Aufruf: %s(%s)", tc.function.name, tc.function.arguments)
            calls.append((tc, tc.function.name, args))

        parallel = (len(calls) > 1
                    and all(name in PARALLEL_SAFE_TOOLS for _, name, _ in calls))
        if parallel:
            with ThreadPoolExecutor(max_workers=min(len(calls), MAX_PARALLEL_TOOLS)) as pool:
                results = list(pool.map(lambda c: _run_tool(handlers, c[1], c[2]), calls))
        else:
            results = [_run_tool(handlers, name, args) for _, name, args in calls]

        # Reihenfolge bleibt die der tool_calls, sonst passen die IDs nicht.
        for (tc, _, _), result in zip(calls, results):
            convo.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": str(result)[:MAX_TOOL_RESULT_CHARS],
            })

    return ("Ich habe zu viele Arbeitsschritte gebraucht und breche hier ab. "
            "Formuliere die Aufgabe bitte kleiner.")


def tool(name: str, description: str, params: dict, required: list[str] | None = None) -> dict:
    """Kurzschreibweise für ein OpenAI-Function-Tool-Schema."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": params,
                "required": required or [],
            },
        },
    }
