"""Fallback: Claude's server-side web search.

Only an emergency exit: if the tool loop fails completely (network error,
broken reply, rate limit), the user still gets an answer with sources instead
of a traceback. The real work happens in agent.py.
"""

from __future__ import annotations

import logging

from core.config import Config
from core.llm import get_client, record_usage

logger = logging.getLogger(__name__)

_INSTRUCTIONS = (
    "You are a research assistant. Answer the question with current, precise "
    "information. End with the most important sources as links (max. 5). Be concise."
)


def search(config: Config, query: str) -> str:
    if config.mock_llm:
        return f"[Mock] Web search for: {query}"

    client = get_client()
    messages = [{"role": "user", "content": query}]
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 8}]
    # Server-side tools can pause a long turn. Each paused turn is appended
    # (never replaced) so the model keeps its earlier search results, and the
    # text of every part is kept for the answer.
    texts: list[str] = []
    for _ in range(4):
        with client.messages.stream(model=config.agent_model, max_tokens=16000,
                                    system=_INSTRUCTIONS, messages=messages,
                                    tools=tools) as stream:
            response = stream.get_final_message()
        record_usage(config, "research-fallback", config.agent_model, response.usage)
        if response.stop_reason == "refusal":
            raise RuntimeError("Fallback web search was declined by the model")
        texts += [b.text for b in response.content if b.type == "text"]
        if response.stop_reason != "pause_turn":
            break
        if messages[-1]["role"] == "assistant":   # second pause: extend the same turn
            messages[-1] = {"role": "assistant",
                            "content": [*messages[-1]["content"], *response.content]}
        else:
            messages.append({"role": "assistant", "content": list(response.content)})
    return "".join(texts).strip()
