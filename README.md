# claude-skill-research-agent

[![tests](https://github.com/sami-mag07/claude-skill-research-agent/actions/workflows/tests.yml/badge.svg)](https://github.com/sami-mag07/claude-skill-research-agent/actions/workflows/tests.yml)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![dependencies](https://img.shields.io/badge/runtime%20deps-0-brightgreen)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

A research skill for Claude Code that treats web research like engineering: several search engines behind one interface, parallel agent waves that never duplicate each other's work, and a verify gate that refuses to call a report done while any citation lacks a verbatim quote from its source.

Zero runtime dependencies. Every script is Python stdlib, so there is nothing to `pip install` and nothing to audit beyond the files in this repo.

## Why

Agent-driven research fails in three predictable ways:

1. **One search backend.** The harness search tool hits a shared quota, a rate limit, or simply misses the niche page. The agent then concludes "nothing exists".
2. **Parallel agents step on each other.** Five subagents on one topic return the same ten URLs five times.
3. **Citations that do not hold.** The report cites `[3]`, but the sentence it supports is nowhere on page 3.

Each script here removes one of those failure modes.

## Architecture

```mermaid
flowchart LR
    A[researcher agent<br/>waves of up to 5] -->|queries| S[search.py]
    S -->|fallback or --fan| E1[Tavily] & E2[Exa API] & E3[Serper] & E4[keyless engines<br/>via MCP]
    E1 & E2 & E3 & E4 --> M[merge<br/>canonical URL, rank by<br/>number of engines]
    M --> SEEN[(seen.txt<br/>flock, shared per wave)]
    M --> R[read pages<br/>WebFetch, Jina reader]
    R -->|blocked by bot wall| F[fetch_hard.py<br/>stealth browser,<br/>SSRF guard]
    R & F --> L[sources.py<br/>ledger + verbatim quotes]
    L --> G{verify gate}
    G -->|every citation backed| OK[report]
    G -->|missing quote| X[exit 1: not done]
```

| Component | Lines | What it guarantees |
|---|---:|---|
| `references/search.py` | ~400 | A query always gets answered by the first engine that works. With `--fan`, all engines run in parallel and URLs are merged after canonicalisation (scheme, `www.`, trailing slash, tracking parameters); hits found by several engines rank first. Domain filters are re-applied locally because not every engine honours them. |
| `--seen <file>` | | An `flock`-guarded list shared by one agent wave. Each hit is tagged `[new]` or `[known]`, so agent 4 sees what agents 1 to 3 already found. |
| `references/sources.py` | ~170 | Numbered ledger `[sNN]`. `quote` only stores a quote if it appears verbatim in the fetched page (whitespace and typographic quotes normalised). `verify` exits non-zero until every citation in the draft is backed; `--check-urls` re-fetches and re-checks the quote live. |
| `references/fetch_hard.py` | ~80 | Last-resort reader for Cloudflare-protected pages. Resolves the host first and refuses loopback, private, link-local and metadata addresses, and passes only a fixed set of flags to the browser. |
| `references/tools.md` | | Everything that goes stale: channel limits, fallback chains, public data APIs, search techniques for niches and people. One line added per lesson learned. |
| `agents/researcher.md` | | A subagent with a fresh context that writes sources to disk as it goes and returns only an index, so the main context stays small. |

## Design decisions

- **Freedom over a step list.** The skill describes capabilities and tools, not a 15-step procedure. An earlier version with numbered rules produced rigid, shallow runs. The only hard rule left: a subagent never spawns subagents (one uncapped run went from 3 to 149 agents).
- **Fallback chain order is cost-aware.** Engines with real date and domain filters and a quota go first, keyless engines last. `--status` shows what is available without printing keys.
- **stdlib only.** Research tooling runs with network access and API keys. Every third-party dependency is attack surface, so the scripts use `urllib`, `concurrent.futures` and `fcntl`, nothing else.
- **Fetched content is data, never instructions.** The agent prompt says so explicitly, and `fetch_hard.py` never lets page content or the model choose browser flags.
- **Keys** come from the environment, then from a local `.env` (gitignored). Inline comments in `.env` are stripped, a bug that once sent a comment as an API key.

## Security

Threat model and mitigations are in [SECURITY.md](SECURITY.md): fetched pages are untrusted, the stealth browser cannot reach internal addresses, keys never leave the environment.

## Tests

```
python -m unittest discover -s tests -v
```

18 tests, no network, no keys, under one second. CI runs them on Linux and macOS with Python 3.10, 3.12 and 3.13. Covered: URL canonicalisation, merge ranking, fallback order and error logging, parallel fan-out surviving dead engines, `.env` parsing, eight concurrent writers on one `seen.txt` producing zero duplicates, the full `add / quote / verify` CLI flow including a fabricated quote being rejected, and the SSRF guard against loopback, RFC 1918, IPv6 loopback, cloud metadata and non-HTTP schemes.

## Setup

1. Copy `skills/research-agent/` to `~/.claude/skills/research-agent/`.
2. Copy `agents/researcher.md` to `~/.claude/agents/researcher.md`. It becomes visible in the next session.
3. Optional: copy `skills/research-agent/.env.example` to `.env` and add the free-tier keys you have (Tavily, Exa, Serper, Jina). Missing keys are skipped.
4. Optional: `mcporter` with keyless search MCP servers for the last links of the chain, and `scrapling` as a uv tool for `fetch_hard.py`.

## Usage

```
search.py "student startup grant" "Gründungsstipendium Schüler" --since 90d --lang de --n 15
search.py "accessibility hackathon" --fan --seen research/a11y/seen.txt --json
search.py --status

sources.py add https://example.org/call            # -> [s01]
sources.py quote s01 --from page.txt --text "Deadline: 1 October"
sources.py verify draft.md --check-urls            # exit 1 until every [sNN] is backed
```

The skill triggers on phrases like "research", "find out", "compare", "market scan", or manually via `/research-agent`. For broad scans, spawn `researcher` agents in waves of at most five with one shared `seen.txt`.

## Limits

- The skill text and agent prompt are in German; the scripts and this README are in English.
- `fetch_hard.py` is slow (10 to 30 seconds per page) and meant for the pages nothing else can read.
- The verify gate proves that a quote exists on a page, not that the claim built on it is a fair reading. That part stays with the reviewer.

## License

MIT
