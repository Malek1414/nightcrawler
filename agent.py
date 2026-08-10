"""Der Recherche- und Scraping-Agent: System-Prompt, Tools, Handler.

Aufbau in drei Teilen, die man getrennt anfassen kann:

1. _SYSTEM      Die Arbeitsweise. Hier steht, WIE gearbeitet wird (Suchfächer,
                Mindestzahl gelesener Seiten, Gegencheck als Pflicht). Das ist
                der Teil, an dem sich die Qualität entscheidet, nicht der Code.
2. _TOOLS       Was der Agent kann. Jedes Tool ist ein JSON-Schema fürs Modell.
3. _handlers()  Welche Python-Funktion hinter jedem Tool-Namen steckt.

Die ausführlichen Methoden stehen NICHT im Prompt, sondern als Skills in
skills/*.md. Der Agent sieht im Prompt nur den Index und lädt den passenden
Skill über read_skill selbst nach. Neue Methode hinzufügen heißt: neue
Markdown-Datei anlegen, nichts hier ändern.

Fällt der Tool-Loop komplett aus, greift die eingebaute Websuche des Modells
als Fallback, damit Recherche nie ganz ausfällt.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from core import skills
from core.config import Config
from core.llm import run_tool_loop, tool
from integrations import notes, reach, web_search

logger = logging.getLogger(__name__)

AGENT = "research"

_SYSTEM = """Du bist ein Recherche-Agent{owner_suffix}. Aktuelle Zeit: {now} ({tz}).

Arbeitsweise (proaktiv und mehrstufig, nicht nach dem ersten Treffer aufhören):
- Du fragst NIE nach, ob du recherchieren sollst, und lässt dir den Auftrag nie
  bestätigen. Ist etwas unklar, triffst du die naheliegende Annahme, schreibst
  sie in einem Halbsatz in die Antwort und recherchierst los.
- Starte mit einem Suchfächer statt einer Einzelsuche: mindestens 3
  web_search-Aufrufe im SELBEN Zug (sie laufen gleichzeitig, kosten also kaum
  mehr Zeit als einer). Variante 1 = der Begriff des Auftrags wörtlich,
  Variante 2 = Synonym oder Fachbegriff, Variante 3 = englische Übersetzung.
- Danach die Trefferlisten vergleichen: Welche Formulierung liefert frische,
  offizielle, konkrete Quellen? Mit dieser Spur arbeitest du weiter und
  verfeinerst sie. Formulierungen, die nur Werbung und Blograuschen bringen,
  wiederholst du nicht.
- Lies mindestens 6 Treffer mit read_page, aus mindestens 4 verschiedenen
  Domains, und rufe sie ebenfalls mehrere pro Zug auf. Snippets allein sind kein
  Beleg. Steht in einer Seite ein Link, der die Frage besser beantwortet: folge
  ihm mit read_page.
- Gegenprüfen ist Pflicht, nicht Kür: Jede Zahl, jedes Datum, jeder Preis, jeder
  Termin und jeder Name muss vor der Antwort gegen eine ZWEITE, unabhängige
  Quelle laufen (nicht dieselbe Domain, nicht dieselbe Pressemitteilung). Was
  nur an einer Quelle hängt, kennzeichnest du als [unbestätigt]. Widersprechen
  sich zwei Quellen, nennst du beide Werte mit Quelle, statt dir einen
  auszusuchen.
- Aufhören darfst du erst, wenn eine weitere Suchrunde nur noch Bekanntes
  bringt, nicht schon wenn du eine plausible Antwort hast.
- YouTube-Link oder Fragen zu einem Video: youtube_transcript nutzen.
- Gründliche Aufträge ("recherchier das mal richtig", Referat, Hausarbeit):
  ZUERST den Skill deep-research laden. Geht es um Zitate, Literatur oder
  Quellenangaben: den Skill quellenarbeit laden. Geht es darum, strukturierte
  Daten aus einer Website zu ziehen (Listen, Preise, Termine): den Skill
  web-scraping laden.
- Brauchst du nicht eine Seite, sondern viele von derselben Domain (alle
  Pressemitteilungen, alle Standorte, alle Stellen): den Skill seiten-index
  laden, statt dich durch die Navigation zu klicken.
- Bringt der Suchfächer nur Werbung und Vergleichsportale: nicht dieselbe
  Suche nochmal, sondern den Skill such-operatoren laden und verengen.
- Scheitert read_page (404, blockiert, Seite geändert) oder brauchst du einen
  früheren Stand einer Seite: den Skill archiv-recherche laden, statt die
  Quelle aufzugeben.
- Leads, Adressen, Einrichtungen oder Ansprechpartner ("wen können wir
  anschreiben", "such mir Anbieter in X", "Liste für den Outreach"): ZUERST den
  Skill lead-recherche laden und danach arbeiten.{notes_block}

Antworte {style} auf {language}. Verwende NIE Gedankenstriche („–" oder „—")
und keine Emojis. Nenne am Ende die wichtigsten Quellen als Links (max. 3);
bei Quellenarbeit stattdessen vollständige Quellenangaben nach dem Skill."""

# Wird nur eingesetzt, wenn ein Notiz-Ordner konfiguriert ist. Ohne Ordner
# darf im Prompt auch nichts davon stehen, sonst halluziniert das Modell Tools.
_NOTES_BLOCK = """
  Und IMMER vorher die Zielgruppe aus den Notizen lesen:
  read_note("{target_note}"). Diese Notiz entscheidet, was in die Liste kommt.
  Was dort ausgeschlossen ist, landet nie ungefragt in der Liste. Die Notiz ist
  aber keine Denkverbotstafel: Fällt dir eine Kategorie auf, die fehlt, oder
  findest du einen echten Grund gegen einen Ausschluss, dann sag es. Getrennt
  von der Liste, am Ende, als Vorschlag mit Begründung und der Frage, ob das
  aufgenommen werden soll.
- Steht in den Notizen eine Vorgabe zu dem, was du recherchieren sollst
  (Zielgruppe, Kriterien, frühere Recherche zum selben Thema): erst
  search_notes bzw. read_note, dann ins Web. Was dort schon entschieden wurde,
  recherchierst du nicht neu.
- Bei "speichere das" / "merk dir die Recherche" oder wenn das Ergebnis
  erkennbar aufwendig und wiederverwendbar ist: save_research aufrufen."""


# --------------------------------------------------------------------- Tools

def _tools(config: Config) -> list[dict]:
    """Tool-Liste. Notiz-Tools nur, wenn ein Ordner konfiguriert ist."""
    tools = [
        tool("web_search", "Websuche: findet aktuelle Seiten und Artikel zum Thema. "
             "Liefert je nach Anbieter zusätzlich eine kurze Zusammenfassung.",
             {"query": {"type": "string", "description": "Suchanfrage"},
              "num_results": {"type": "integer", "description": "Anzahl Treffer, 1-10 (Standard 5)"},
              "domains": {"type": "string", "description": "Optional: nur diese Domains "
                          "durchsuchen, kommagetrennt, z.B. 'destatis.de, bund.de'. "
                          "Für gezielte Suche in amtlichen oder fachlichen Quellen."}},
             required=["query"]),
        tool("read_page", "Eine Webseite als Text lesen (Artikel, Event-Seite, Doku, "
             "Verzeichnis). Auch der Weg, um an strukturierte Daten zu kommen.",
             {"url": {"type": "string", "description": "Vollständige URL"}},
             required=["url"]),
        tool("youtube_transcript", "Untertitel/Transkript eines YouTube-Videos holen.",
             {"url": {"type": "string", "description": "YouTube-URL"}},
             required=["url"]),
    ]
    if config.notes_dir:
        tools += [
            tool("search_notes", "In den eigenen Notizen suchen (Dateiname und Inhalt). "
                 "Dafür da, vorhandene Vorgaben zu finden, bevor du ins Web gehst.",
                 {"query": {"type": "string", "description": "Suchbegriff"}},
                 required=["query"]),
            tool("read_note", "Eine Notiz lesen (Pfad relativ zum Notiz-Ordner, z.B. "
                 "'Zielgruppe.md'). Vor jeder Lead-Recherche Pflicht.",
                 {"rel_path": {"type": "string", "description": "Pfad relativ zum Notiz-Ordner"}},
                 required=["rel_path"]),
            tool("save_research", "Rechercheergebnis als Notiz ablegen.",
                 {"title": {"type": "string", "description": "Kurzer, sprechender Titel"},
                  "content": {"type": "string",
                              "description": "Fertige Markdown-Notiz inkl. Quellen am Ende"}},
                 required=["title", "content"]),
        ]
    return tools + [skills.tool_spec()]


# ------------------------------------------------------------------ Handler

def _save_research(config: Config, title: str, content: str) -> str:
    try:
        return notes.create_note(config, title, content, folder=config.research_folder)
    except Exception as e:
        return f"Konnte die Notiz nicht speichern: {e}"


def _handlers(config: Config) -> dict:
    handlers = {
        "web_search": lambda query, num_results=5, domains="":
            reach.web_search(query, num_results, config.tavily_api_key, domains),
        "read_page": lambda url: reach.read_page(url, tavily_key=config.tavily_api_key),
        "youtube_transcript": lambda url: reach.youtube_transcript(url),
        "read_skill": lambda name: skills.read_skill(name),
    }
    if config.notes_dir:
        handlers.update({
            "search_notes": lambda query: json.dumps(
                notes.search_notes(config, query), ensure_ascii=False),
            "read_note": lambda rel_path: notes.read_note(config, rel_path),
            "save_research": lambda title, content: _save_research(config, title, content),
        })
    return handlers


# --------------------------------------------------------------------- Lauf

def build_system_prompt(config: Config) -> str:
    now = datetime.now(ZoneInfo(config.timezone))
    notes_block = (_NOTES_BLOCK.format(target_note=config.target_group_note)
                   if config.notes_dir else "")
    return _SYSTEM.format(
        owner_suffix=f" für {config.owner_name}" if config.owner_name else "",
        now=now.strftime("%A, %d.%m.%Y %H:%M"),
        tz=config.timezone,
        notes_block=notes_block,
        style=config.answer_style,
        language=config.answer_language,
    ) + skills.index_block(AGENT)


def run(config: Config, task: str) -> str:
    """Einen Rechercheauftrag durchlaufen lassen und die fertige Antwort geben."""
    system = build_system_prompt(config)
    try:
        return run_tool_loop(
            config, config.agent_model, system,
            [{"role": "user", "content": task}],
            _tools(config), _handlers(config),
            # Mehr Runden als bei einfachen Agents: Suchfächer, 6 und mehr
            # gelesene Seiten und der Gegencheck brauchen Platz, sonst bricht
            # der Loop mittendrin ab.
            max_rounds=config.max_rounds, agent=AGENT,
        )
    except Exception:
        logger.exception("Tool-Loop fehlgeschlagen, Fallback auf die eingebaute Websuche")
        return web_search.search(config, task)
