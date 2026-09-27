# claude-skill-research-agent

A research skill plus a spawnable researcher subagent for Claude Code. No fixed step list: the agent picks depth, channels and order to fit the question. It comes with a channel and fallback map (`references/tools.md`) and a stdlib-only source ledger with a verify gate (`references/sources.py`). The skill text itself is in German.

## Setup

1. Copy `skills/research-agent/` to `~/.claude/skills/research-agent/`.
2. Copy `agents/researcher.md` to `~/.claude/agents/researcher.md`. It becomes visible in the next session.
3. Optional: copy `skills/research-agent/.env.example` to a `.env` and fill in the free-tier keys you want (Jina, Exa, Serper, Parallel, Tavily). Without a key, that channel is skipped.
4. Optional: install agent-reach as the platform router. Without it, the agent falls back to WebSearch, WebFetch and curl.

## Usage

The skill triggers on words like "recherchier", "finde raus", "such mal", "vergleich", "marktscan". Manually: `/research-agent`. For broad scans, spawn the `researcher` agent in waves of at most five; a subagent never spawns further subagents.

Source ledger:

- `python3 sources.py add <url>` gives a source a number `[sNN]`.
- `python3 sources.py quote <id> --from page.txt --text "..."` stores a quote only if it literally appears on the page.
- `python3 sources.py verify draft.md` fails if any cited `[sNN]` lacks a verified quote.

## Customizing

- `references/tools.md` holds everything that goes stale (limits, endpoints, blocked sites). Add one line whenever a run teaches you something.
- The browser fallback assumes a local browser MCP. Without one, drop that step.
