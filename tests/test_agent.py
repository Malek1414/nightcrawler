"""The agent itself: prompt, tool list, wiring, quality gate. No API calls."""

from __future__ import annotations

import re

import agent
from integrations import profile as prof


def test_every_tool_has_a_handler(config_with_notes):
    """The most common wiring bug: tool declared, handler forgotten.

    The model then calls it and gets 'unknown tool' back.
    """
    names = {t["name"] for t in agent._tools(config_with_notes)}
    handlers = set(agent._handlers(config_with_notes))
    assert names == handlers, f"no handler: {names - handlers}, no tool: {handlers - names}"


def test_tools_use_claude_schema(config):
    for t in agent._tools(config):
        assert set(t) == {"name", "description", "input_schema"}
        assert t["input_schema"]["type"] == "object"


def test_no_note_tools_without_notes_folder(config):
    names = {t["name"] for t in agent._tools(config)}
    assert "read_note" not in names and "save_research" not in names
    assert {"web_search", "read_page", "youtube_transcript", "read_skill",
            "score_opportunity", "geo_distance"} <= names


def test_parallel_list_covers_all_read_tools(config_with_notes):
    """Read tools must be allowed to run concurrently, or the search fan from
    the prompt turns into a queue."""
    from core.llm import PARALLEL_SAFE_TOOLS

    reading = {"web_search", "read_page", "youtube_transcript", "search_notes",
               "read_note", "read_skill", "geo_distance", "score_opportunity"}
    assert reading <= PARALLEL_SAFE_TOOLS
    assert "save_research" not in PARALLEL_SAFE_TOOLS


def test_prompt_contains_the_method(config):
    prompt = agent.build_system_prompt(config)
    assert "search fan" in prompt
    assert "SECOND, independent" in prompt
    assert "at least 6 results" in prompt
    assert "web-scraping" in prompt          # skill index is appended


def test_prompt_is_english():
    assert not re.search(r"[äöüÄÖÜß]", agent._SYSTEM + agent._NOTES_BLOCK)


def test_prompt_has_no_timestamp(config):
    """The system prompt must be byte-stable between runs, or the prompt cache
    never hits. The time goes into the user message instead."""
    assert agent.build_system_prompt(config) == agent.build_system_prompt(config)
    assert "Current time" not in agent.build_system_prompt(config)


def test_prompt_mentions_note_tools_only_when_they_exist(config, config_with_notes):
    assert "read_note" not in agent.build_system_prompt(config)
    assert "read_note" in agent.build_system_prompt(config_with_notes)


def test_prompt_names_only_existing_skills(config):
    """The prompt says things like "load the skill archive-research". If one
    of those points nowhere, the model searches in vain mid-task."""
    from core import skills

    known = {s["name"] for s in skills.load_all()}
    named = set(re.findall(r"load the\s+skill\s+([a-z][a-z0-9-]*)",
                           agent.build_system_prompt(config)))
    assert named, "the prompt no longer names any skill"
    assert named <= known, f"do not exist: {named - known}"


def test_prompt_includes_profile(config):
    user = prof.Profile(home_city="Lisbon, Portugal", goals=("raise pre-seed",))
    prompt = agent.build_system_prompt(config, user)
    assert "Lisbon, Portugal" in prompt and "raise pre-seed" in prompt


def test_prompt_without_profile_says_so(config):
    assert "none configured" in agent.build_system_prompt(config, None)


def test_read_page_handler_counts_evidence(config, monkeypatch):
    monkeypatch.setattr(agent.reach, "read_page", lambda url, **kw: "text")
    ev = agent._Evidence(2, 2)
    handlers = agent._handlers(config, None, ev)
    handlers["read_page"](url="https://www.a.com/x")
    handlers["read_page"](url="https://a.com/y")
    assert len(ev.urls) == 2 and ev.domains == {"a.com"}
    assert ev.gate("draft") is not None           # 2 pages but only 1 domain
    handlers["read_page"](url="https://b.org/z")
    assert ev.gate("draft") is None


def test_failed_read_does_not_count(config, monkeypatch):
    def boom(url, **kw):
        raise RuntimeError("403")
    monkeypatch.setattr(agent.reach, "read_page", boom)
    ev = agent._Evidence(1, 1)
    try:
        agent._handlers(config, None, ev)["read_page"](url="https://a.com")
    except RuntimeError:
        pass
    assert not ev.urls


def test_score_handler_returns_json(config):
    import json

    out = agent._handlers(config)["score_opportunity"](
        title="Demo Day", payoff=5, fit=4, fee=0, online=True, investor_presence=3)
    data = json.loads(out)
    assert data["title"] == "Demo Day" and 0 <= data["score"] <= 100


def test_run_in_mock_mode_calls_nothing_outside(config):
    answer = agent.run(config, "Test the wiring")
    assert answer.startswith("[Mock]")
