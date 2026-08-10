"""Der Agent selbst: Prompt, Tool-Liste, Verdrahtung. Kein API-Aufruf."""

from __future__ import annotations

import agent


def test_jedes_tool_hat_einen_handler(config_with_notes):
    """Der häufigste Verdrahtungsfehler: Tool deklariert, Handler vergessen.

    Das Modell ruft es dann auf und bekommt 'unbekanntes Tool' zurück.
    """
    namen = {t["function"]["name"] for t in agent._tools(config_with_notes)}
    handler = set(agent._handlers(config_with_notes))
    assert namen == handler, f"ohne Handler: {namen - handler}, ohne Tool: {handler - namen}"


def test_ohne_notiz_ordner_keine_notiz_tools(config):
    namen = {t["function"]["name"] for t in agent._tools(config)}
    assert "read_note" not in namen and "save_research" not in namen
    assert {"web_search", "read_page", "youtube_transcript", "read_skill"} <= namen


def test_parallel_liste_deckt_alle_lesenden_tools_ab(config_with_notes):
    """Lesende Tools müssen gleichzeitig laufen dürfen, sonst wird der
    Suchfächer aus dem Prompt zur Warteschlange."""
    from core.llm import PARALLEL_SAFE_TOOLS

    lesend = {"web_search", "read_page", "youtube_transcript",
              "search_notes", "read_note", "read_skill"}
    assert lesend <= PARALLEL_SAFE_TOOLS
    assert "save_research" not in PARALLEL_SAFE_TOOLS


def test_prompt_enthaelt_die_arbeitsweise(config):
    prompt = agent.build_system_prompt(config)
    assert "Suchfächer" in prompt
    assert "ZWEITE, unabhängige" in prompt
    assert "web-scraping" in prompt          # Skill-Index ist angehängt


def test_prompt_erwaehnt_notiz_tools_nur_wenn_es_sie_gibt(config, config_with_notes):
    assert "read_note" not in agent.build_system_prompt(config)
    assert "read_note" in agent.build_system_prompt(config_with_notes)


def test_prompt_nennt_nur_skills_die_es_gibt(config):
    """Im Prompt stehen Ladebefehle wie "den Skill archiv-recherche laden".
    Zeigt einer davon ins Leere, sucht das Modell mitten in der Aufgabe
    vergeblich."""
    import re

    from core import skills

    bekannt = {s["name"] for s in skills.load_all()}
    genannt = set(re.findall(r"Skill ([a-z][a-z0-9-]*) laden",
                             agent.build_system_prompt(config)))
    assert genannt, "der Prompt nennt gar keinen Skill mehr"
    assert genannt <= bekannt, f"gibt es nicht: {genannt - bekannt}"


def test_run_im_mock_modus_ruft_nichts_nach_draussen(config):
    antwort = agent.run(config, "Teste die Verdrahtung")
    assert antwort.startswith("[Mock]")
