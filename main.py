"""Einstiegspunkt: einen Rechercheauftrag von der Kommandozeile laufen lassen.

    python main.py "Was kostet ein Lastenrad-Abo in Berlin?"
    python main.py --skills
    python main.py --prompt
    echo "Auftrag" | python main.py

Der Agent selbst hängt an keinem Kanal. Wer ihn in einen Bot, ein Web-Backend
oder einen anderen Agent einbaut, ruft agent.run(config, auftrag) auf und
bekommt den fertigen Text zurück. Der Aufruf blockiert, also gehört er in
einem async-Programm in einen Thread (asyncio.to_thread).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

import agent
from core import skills
from core.config import ConfigError, load_config
from core.llm import usage_summary


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    # httpx loggt jeden Request auf INFO, das übertönt sonst alles Eigene.
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main() -> int:
    parser = argparse.ArgumentParser(description="Recherche- und Scraping-Agent")
    parser.add_argument("task", nargs="*", help="Der Auftrag. Ohne Angabe wird stdin gelesen.")
    parser.add_argument("--skills", action="store_true",
                        help="Verfügbare Skills auflisten und beenden")
    parser.add_argument("--prompt", action="store_true",
                        help="Den fertigen System-Prompt ausgeben und beenden")
    parser.add_argument("--mock", action="store_true",
                        help="Ohne API-Aufruf durchlaufen (Verdrahtung testen)")
    args = parser.parse_args()

    if args.skills:
        entries = skills.for_agent(agent.AGENT)
        if not entries:
            print("Keine Skills gefunden. Liegen .md-Dateien in skills/?")
            return 1
        for s in entries:
            print(f"{s['name']:<18} {s['description']}")
        return 0

    # Vor dem Laden setzen, sonst scheitert die Prüfung auf den fehlenden Key,
    # bevor --mock überhaupt greifen kann.
    if args.mock:
        os.environ["MOCK_LLM"] = "true"

    try:
        config = load_config()
    except ConfigError as e:
        print(f"Konfiguration unvollständig: {e}", file=sys.stderr)
        return 2

    _setup_logging(config.log_level)

    if args.prompt:
        print(agent.build_system_prompt(config))
        return 0

    task = " ".join(args.task).strip() or sys.stdin.read().strip()
    if not task:
        parser.print_help()
        return 2

    answer = agent.run(config, task)
    print(answer)
    if not config.mock_llm:
        print(f"\n[{usage_summary()}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
