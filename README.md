# Nightcrawler

A research and scraping agent that knows who it works for. It takes a
question, searches the web, actually reads pages, pulls structured data out of
them, and returns a sourced answer. When the question is about opportunities,
such as events, jobs, grants, clients, or rooms full of investors, it ranks
them for you: payoff against what it really costs you to get there, from
where you live, within your budget.

> Setup, step by step: **[SETUP.md](SETUP.md)**. It's written as a recipe you
> can also hand to a coding agent.

Built on [scraping-agent-skeleton](https://github.com/sami-mag07/scraping-agent-skeleton)
by sami-mag07 (MIT). See [What changed](#what-changed-from-the-skeleton).

---

## How it works

**It starts from you, not the topic.** A local `profile.toml` holds your home
base, goals, interests, budget, and travel limit. The agent reads it before
searching. From that it decides what's worth looking for, so it doesn't just
scrape everything on the subject.

**It runs a search fan, not a single search.** Every question sends out at
least three queries at once: the task's own words, a synonym or technical
term, and the phrasing a local or official source would use. The agent keeps
the track that brings fresh, official sources.

**It reads pages instead of collecting snippets.** At least 6 pages from at
least 4 domains are read in full. The code checks this: an answer below the
bar is sent back once, and the model must keep reading or say why fewer
sources are enough.

**Cross-checking is mandatory.** Every number, date, price, and deadline is
checked against a second, independent source. Anything resting on one source
is marked `[unverified]`. When sources disagree, both values appear in the
answer.

**Ranking is arithmetic, not vibes.** For opportunities, the model supplies
what it found (fee, place, deadline) and its estimates (payoff, fit, whether
investors attend). `score_opportunity` then calculates distance, estimated
round-trip travel and lodging, and budget flags, and returns a 0 to 100 score
with the breakdown. The agent also looks for the cheapest way in: free tiers,
volunteer or speaker slots, discounts, and travel grants.

---

## Architecture

```
main.py              CLI, or your own caller (bot, web backend, another agent)
   |
agent.py             system prompt + tools + handlers + evidence gate
   |
core/llm.py          Claude tool loop: parallel reads, context editing,
   |                 quality gate, graceful stop at the round limit
   +-- core/skills.py           loads skills/*.md on demand
   +-- integrations/reach.py    search, read pages (text or raw data), YouTube
   +-- integrations/profile.py  your profile, geocoding, opportunity scoring
   +-- integrations/notes.py    read and write a Markdown folder
```

| Tool | What it does |
|---|---|
| `web_search` | Tavily (optional key), falls back to the free Exa endpoint. Optional domain filter |
| `read_page` | Jina Reader, then Tavily Extract, then a direct fetch. `raw=true` returns JSON-LD / `__NEXT_DATA__` blobs first. Cached per run |
| `youtube_transcript` | Subtitles via yt-dlp |
| `geo_distance` | Distance from your home (or any origin) to a place, via OpenStreetMap |
| `score_opportunity` | 0 to 100 score with cost breakdown, budget, distance, and deadline flags |
| `search_notes` / `read_note` / `save_research` | Your notes folder, only with `NOTES_DIR` |
| `read_skill` | Load a method on demand |

## Skills

| Skill | When |
|---|---|
| `opportunity-scout` | Events, meetups, jobs, gigs, grants, competitions, investor-heavy rooms, ranked for you |
| `lead-research` | Find leads and filter them against your target-audience note |
| `web-scraping` | Data rather than prose: open datasets, JSON in the HTML, endpoints, pagination |
| `site-index` | All URLs of a domain at once: robots.txt, sitemaps, Wayback index |
| `archive-research` | Dead, blocked, or changed pages via the Internet Archive |
| `search-operators` | Narrow down when the search fan brings only noise |
| `deep-research` | Break the question apart, keep a source register, look for the counter-thesis |
| `citations` | Full source citations, quotation vs. paraphrase |

New skill = new `.md` file in `skills/` with `name`, `description`, and
`agents: research` in the frontmatter. No code.

---

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env                              # add ANTHROPIC_API_KEY, or run `ant auth login`
cp examples/profile.example.toml profile.toml     # then make it yours

.venv/bin/python main.py "Pitch competitions and demo days I can reach before December"
```

```bash
.venv/bin/python main.py --profile       # what the agent knows about you
.venv/bin/python main.py --skills        # available methods
.venv/bin/python main.py --prompt        # the assembled system prompt
.venv/bin/python main.py --mock "test"   # run without an API call
.venv/bin/python -m pytest               # tests, no network and no key needed
```

To embed it, call `agent.run(config, task)` and you get the finished text back.
The call blocks, so in async code wrap it in `asyncio.to_thread()`.

---

## Costs

Claude is the only paid part. The default is `claude-opus-5` at `EFFORT=high`.
For routine runs, `claude-sonnet-5` or `EFFORT=medium` costs much less. The
system prompt is byte-stable between runs (the timestamp goes into the user
message), so prompt caching works. Old tool results are cleared server-side
once the context gets large. Usage is printed to stderr after every run.

## Privacy and safety

- Secrets live only in `.env`. `profile.toml` is also gitignored.
- The only personal data that leaves your machine: your home city name, sent
  to OpenStreetMap once for coordinates. With `LOCATION_SOURCE=ip`, your
  public IP also goes to ip-api.com. That setting is opt-in.
- Note paths are checked by path components, so `../../.ssh/id_rsa` and
  sibling folders like `/notes-evil` are rejected. `save_research` only
  creates new files.
- Tool errors go back to the model as text, so it can react to a broken fetch.
- The skills say it explicitly: respect robots.txt, don't get around bot
  protection, don't hammer one domain, and don't collect personal data the
  task doesn't need.

## What changed from the skeleton

| Area | Skeleton | Nightcrawler |
|---|---|---|
| Model | OpenAI `gpt-4o` | Claude (`claude-opus-5`), adaptive thinking, server-side refusal fallback |
| Language | German prompts and skills | English throughout |
| User context | Name, language, timezone | Profile with home, goals, budget, travel limits, and scoring weights; optional IP location |
| Ranking | None | `score_opportunity`: all-in cost, distance, budget, and deadline flags |
| Evidence rules | Prompt only | Checked in code before an answer is accepted |
| Long runs | Could overflow context and crash into a weaker fallback | Server-side context editing clears old tool results |
| Round limit | Threw the research away ("make the task smaller") | Writes up what it has, marks gaps |
| Page limit | 7,000 chars, silent about what was lost | 20,000 chars, and says how much was cut |
| Structured data | Only visible if Jina failed | `read_page(raw=true)` extracts JSON-LD and framework state |
| Repeat fetches | Every time | Cached per run |
| Prompt caching | Timestamp in system prompt broke it | Stable system prompt, cache on |
| Notes path check | `startswith` (sibling-folder bypass) | `is_relative_to` |
| Tests | 29, wiring only | 63, including the tool loop against a fake Claude client |

## Licence

MIT, see [LICENSE](LICENSE). The skeleton this is built on is MIT, by sami-mag07.
Some skills build on prior work by others, each credited in the `source:` line
of the frontmatter.
