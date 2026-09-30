"""LLM access: Claude client, tool loop, mock mode.

The tool loop is the heart of the agent. It calls the model, runs the
requested tools, sends the results back, and repeats until the model gives a
final answer or max_rounds is reached.

What this loop does beyond a plain agentic loop:

- Read-only tools run concurrently. Three searches in one turn cost about as
  much wall-clock time as one. Anything that writes stays sequential.
- Old tool results are cleared server-side (context editing), so a long run
  that reads dozens of pages does not overflow the context window.
- A quality gate: before a final answer is accepted, `gate` may push back once
  (for example "you only read 2 pages"). The rules live in agent.py, the
  mechanism lives here.
- Hitting max_rounds does not throw the research away. The model gets one
  last turn without tools to write up what it has.

All functions block. In a bot or web server, run them in a thread
(asyncio.to_thread).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from core.config import Config

logger = logging.getLogger(__name__)

# Side-effect-free tools: pure reads, repeatable in any order. Only these may
# run in parallel.
PARALLEL_SAFE_TOOLS = {
    "web_search", "read_page", "youtube_transcript",
    "search_notes", "read_note", "read_skill", "geo_distance", "score_opportunity",
}
MAX_PARALLEL_TOOLS = 6
MAX_TOOL_RESULT_CHARS = 30000
MAX_TOKENS = 64000   # thinking is always on and counts toward this

BETAS = [
    "server-side-fallback-2026-07-01",   # re-run a declined request on a fallback model
    "context-management-2025-06-27",     # clear old tool results as the context grows
]
CONTEXT_MANAGEMENT = {"edits": [{
    "type": "clear_tool_uses_20250919",
    "trigger": {"type": "input_tokens", "value": 120000},
    "keep": {"type": "tool_uses", "value": 12},
}]}

# Token usage per run, for display only.
USAGE: dict[str, dict[str, int]] = defaultdict(
    lambda: {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0, "calls": 0})

_TRUNCATED = ("Your previous reply ran out of output tokens and was discarded. "
              "Think less and act: either make the next tool calls, or write the "
              "final answer concisely.")

# A gate looks at the draft final answer and returns None (accept) or a
# message that sends the model back to work.
Gate = Callable[[str], "str | None"]

_client = None


def get_client():
    """Anthropic client, cached per process. Credentials come from the
    environment (ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, or `ant auth login`)."""
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic()
    return _client


def record_usage(config: Config, agent: str, model: str, usage) -> None:
    """Book token usage. Must never abort the run."""
    if usage is None or config.mock_llm:
        return
    try:
        entry = USAGE[f"{agent}:{model}"]
        entry["in"] += int(getattr(usage, "input_tokens", 0) or 0)
        entry["out"] += int(getattr(usage, "output_tokens", 0) or 0)
        entry["cache_read"] += int(getattr(usage, "cache_read_input_tokens", 0) or 0)
        entry["cache_write"] += int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
        entry["calls"] += 1
    except Exception:
        logger.exception("Token tracking failed")


def usage_summary() -> str:
    """One line for the console at the end of a run."""
    if not USAGE:
        return "no usage recorded"
    return " | ".join(
        # input_tokens excludes cached tokens, so the total input is the sum.
        f"{key}: {v['calls']} calls, "
        f"{v['in'] + v['cache_read'] + v['cache_write']} in "
        f"({v['cache_read']} cache reads, {v['cache_write']} cache writes) / {v['out']} out"
        for key, v in USAGE.items()
    )


def _run_tool(handlers: dict | None, name: str, args: dict) -> tuple[str, bool]:
    """Run one tool. Errors go back to the model as text, never as a crash,
    so it can react to a broken fetch (try another source) instead of the
    whole run dying. Returns (result, is_error)."""
    handler = (handlers or {}).get(name)
    if handler is None:
        return f"Error: unknown tool '{name}'", True
    try:
        return str(handler(**args)), False
    except Exception as e:
        logger.exception("Tool '%s' failed", name)
        return f"Error in {name}: {e}", True


def _add_assistant(convo: list[dict], content) -> None:
    """Append an assistant turn. A response that follows a pause_turn continues
    the SAME turn, so it extends the last assistant message instead of
    stacking a second one."""
    if convo and convo[-1]["role"] == "assistant":
        convo[-1] = {"role": "assistant", "content": [*convo[-1]["content"], *content]}
    else:
        convo.append({"role": "assistant", "content": list(content)})


def _text(response) -> str:
    return "\n".join(b.text for b in response.content if b.type == "text").strip()


def run_tool_loop(
    config: Config,
    model: str,
    system: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    handlers: dict[str, Callable[..., str]] | None = None,
    max_rounds: int = 8,
    agent: str = "agent",
    gate: Gate | None = None,
) -> str:
    """Messages API with a manual tool-use loop.

    `handlers` maps tool names to Python functions. Their string return value
    goes back to the model as the tool result until it answers.
    """
    if config.mock_llm:
        return f"[Mock] Answer from {model} to: {messages[-1]['content'][:80]}"

    client = get_client()
    convo = list(messages)
    gate_used = False

    def call(tool_choice: dict | None = None):
        kwargs = dict(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=convo,
            tools=tools or [],
            thinking={"type": "adaptive"},
            output_config={"effort": config.effort},
            cache_control={"type": "ephemeral"},
            context_management=CONTEXT_MANAGEMENT,
            fallbacks="default",
            betas=BETAS,
        )
        if tool_choice:
            kwargs["tool_choice"] = tool_choice
        # Streaming avoids HTTP timeouts on long thinking turns.
        with client.beta.messages.stream(**kwargs) as stream:
            response = stream.get_final_message()
        record_usage(config, agent, model, response.usage)
        return response

    for _ in range(max_rounds):
        response = call()

        if response.stop_reason == "refusal":
            return "The model declined this request, and the fallback model declined too."

        if response.stop_reason == "pause_turn":
            # Resend so the model continues the same turn.
            _add_assistant(convo, response.content)
            continue

        if response.stop_reason == "max_tokens":
            # Cut off mid-turn (often while thinking): any tool_use block may be
            # incomplete and there may be no text. Drop the truncated turn and
            # ask for a shorter one instead of returning an empty answer.
            logger.warning("Response hit max_tokens, asking for a shorter turn")
            convo.append({"role": "user", "content": _TRUNCATED})
            continue

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        _add_assistant(convo, response.content)

        if not tool_uses:
            answer = _text(response)
            if gate and not gate_used:
                objection = gate(answer)
                if objection:
                    gate_used = True
                    logger.info("Quality gate pushed back: %s", objection)
                    convo.append({"role": "user", "content": objection})
                    continue
            return answer

        for tu in tool_uses:
            logger.info("Tool call: %s(%s)", tu.name, tu.input)

        parallel = (len(tool_uses) > 1
                    and all(tu.name in PARALLEL_SAFE_TOOLS for tu in tool_uses))
        if parallel:
            with ThreadPoolExecutor(max_workers=min(len(tool_uses), MAX_PARALLEL_TOOLS)) as pool:
                results = list(pool.map(
                    lambda tu: _run_tool(handlers, tu.name, dict(tu.input or {})), tool_uses))
        else:
            results = [_run_tool(handlers, tu.name, dict(tu.input or {})) for tu in tool_uses]

        # All results go back in ONE user message, in tool_use order.
        convo.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": tu.id,
             "content": result[:MAX_TOOL_RESULT_CHARS], "is_error": is_error}
            for tu, (result, is_error) in zip(tool_uses, results)
        ]})

    # Out of rounds: keep the research, just stop calling tools.
    logger.warning("max_rounds (%d) reached, asking for a final write-up", max_rounds)
    convo.append({"role": "user", "content": (
        "You have reached the step limit. Do not call any more tools. Write the "
        "final answer now from what you have, and list clearly what is still "
        "open or unverified.")})
    response = call(tool_choice={"type": "none"})
    answer = _text(response)
    if response.stop_reason == "max_tokens" and answer:
        answer += "\n\n[Answer cut off at the output limit.]"
    return answer or "Stopped at the step limit without a usable answer."


def tool(name: str, description: str, params: dict, required: list[str] | None = None) -> dict:
    """Shorthand for a Claude tool definition."""
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": params,
            "required": required or [],
        },
    }
