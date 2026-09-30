"""Entry point: run a research task from the command line.

    python main.py "Free AI meetups near me in the next 6 weeks"
    python main.py --skills
    python main.py --prompt
    python main.py --profile
    echo "task" | python main.py

The agent is not tied to any channel. To embed it in a bot, a web backend, or
another agent, call agent.run(config, task) and get the finished text back.
The call blocks, so in an async program it belongs in a thread
(asyncio.to_thread).
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
from integrations import profile as prof


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    # httpx logs every request at INFO, which drowns out everything else.
    for name in ("httpx", "httpx2"):
        logging.getLogger(name).setLevel(logging.WARNING)


def main() -> int:
    parser = argparse.ArgumentParser(description="Nightcrawler: research and scraping agent")
    parser.add_argument("task", nargs="*", help="The task. Without one, stdin is read.")
    parser.add_argument("--skills", action="store_true",
                        help="List the available skills and exit")
    parser.add_argument("--prompt", action="store_true",
                        help="Print the assembled system prompt and exit")
    parser.add_argument("--profile", action="store_true",
                        help="Show the loaded user profile (with resolved location) and exit")
    parser.add_argument("--mock", action="store_true",
                        help="Run without calling the API (tests the wiring)")
    args = parser.parse_args()

    if args.skills:
        entries = skills.for_agent(agent.AGENT)
        if not entries:
            print("No skills found. Are there .md files in skills/?")
            return 1
        for s in entries:
            print(f"{s['name']:<18} {s['description']}")
        return 0

    # Set before loading so that --mock also works without credentials.
    if args.mock:
        os.environ["MOCK_LLM"] = "true"

    try:
        config = load_config()
    except ConfigError as e:
        print(f"Configuration incomplete: {e}", file=sys.stderr)
        return 2

    _setup_logging(config.log_level)

    if args.profile:
        user = agent.load_user(config)
        print(f"Profile file: {config.profile_path}")
        print(prof.render(user).strip())
        return 0

    if args.prompt:
        print(agent.build_system_prompt(config, agent.load_user(config)))
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
