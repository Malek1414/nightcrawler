# Security model

This skill gives an LLM agent network access, API keys and a headless browser. The threat model assumes that any fetched page may be hostile.

| Threat | Mitigation | Where |
|---|---|---|
| Prompt injection from fetched pages | Page content and tool output are treated as data, never as instructions. The agent prompt states this; no script executes or evaluates page content. | `agents/researcher.md` |
| SSRF through the stealth browser | The host is resolved before fetching. Loopback, RFC 1918, link-local (incl. cloud metadata `169.254.169.254`), reserved, multicast and unspecified addresses are refused, as are non-HTTP schemes. | `fetch_hard.py`, tested in `tests/test_fetch_hard.py` |
| Browser flag injection | Only a fixed flag set reaches the browser. `executable_path`, `cdp_url`, `proxy`, `additional_args` and `real_chrome` are never passed through, whatever the page or model asks for. | `fetch_hard.py` |
| Key leakage | Keys come from the environment or a gitignored `.env`. `--status` reports presence only, never values. Keys are never written to reports, ledgers or the seen list. | `search.py`, `.gitignore` |
| Supply chain | Runtime code is Python stdlib only. Optional external tools (keyless search MCP servers, Scrapling) live outside this repo, are called as CLIs rather than imported, and should be installed pinned to a vetted version and hash. CI actions are pinned to commit SHAs. | `README.md`, `.github/workflows/tests.yml` |
| Fabricated citations | A quote is stored only if it appears verbatim in the fetched text; `verify` fails the report otherwise. | `sources.py`, tested in `tests/test_sources.py` |
| Runaway agent fan-out | A subagent never spawns subagents; waves are capped at five agents. | `SKILL.md`, `agents/researcher.md` |

## Known limits

- DNS rebinding between the check and the browser's own lookup is not prevented. Run `fetch_hard.py` on a machine without sensitive internal services, or behind an egress proxy.
- The verify gate proves a quote exists, not that the claim drawn from it is fair.

## Reporting

Please open a private security advisory on this repository rather than a public issue.
