# Research and Scraping Agent (Skeleton)

An agent that takes a question, searches the web, actually reads pages,
pulls structured data out of them, and returns a sourced answer. It does
not stop at the first hit, and it checks every number against a second
source before stating it.

This is the **skeleton**: the complete logic and all methods, without anyone's
data. You put your own credentials into a `.env` and it runs on your machine.

> **New here?** The step-by-step setup is in
> **[SETUP.md](SETUP.md)**, written as a recipe you can also hand directly to a
> coding agent (Claude Code, Cursor, Codex).

---

## How it works

The special part is not in the code but in the working method, which is laid
down in the system prompt and in the skills:

**Search fan instead of a single search.** For every question, at least three
search queries go out at once: the term verbatim, a synonym or technical
term, the English variant. Then it compares which phrasing brings fresh and
official sources. Only that track gets refined.

**Reading instead of collecting snippets.** At least six hits from at least
four domains are read in full text. A search snippet is not evidence.

**Cross-checking is mandatory.** Every number, every date, every price, and
every name is run against a second, independent source. Whatever rests on a
single source is marked `[unbestätigt]`. If two sources contradict each other,
both values appear in the answer instead of the agent picking one.

**Stopping criterion.** It is only done when another round yields nothing but
known material, not as soon as a plausible answer is on the page.

---

## Architecture

A job always takes the same path:

```
main.py            CLI, or your own caller (bot, web backend, another agent)
      |
  agent.py         system prompt (the working method) + tool definitions
      |
 core/llm.py       tool loop: query the model, run tools, repeat
      |            reading tools run concurrently, writing tools sequentially
      |
      +-- core/skills.py         loads skills/*.md on demand
      +-- integrations/reach.py  search, read pages, YouTube transcripts
      +-- integrations/notes.py  read and write a Markdown folder
```

| File / folder | What lives there |
|---|---|
| `main.py` | Entry point from the command line |
| `agent.py` | System prompt, tool schemas, handlers. The place where behavior changes |
| `core/llm.py` | Tool loop, parallel execution of reading tools, mock mode, token counting |
| `core/skills.py` | Skill loader: parse frontmatter, build the index, provide `read_skill` |
| `core/config.py` | Read the `.env`. No values in the code |
| `integrations/reach.py` | Tavily, Exa, Jina Reader, yt-dlp. Every function with a fallback |
| `integrations/notes.py` | Notes folder: search, read, create new (never overwrite) |
| `integrations/web_search.py` | Emergency exit in case the tool loop fails completely |
| `skills/*.md` | The detailed methods. New method = new file, no code |
| `beispiele/` | Template for the target-audience note |
| `tests/` | Runs without network and without an API key |

---

## Tools

| Tool | What it does | Falls back to |
|---|---|---|
| `web_search` | Web search with a short summary, optionally narrowed to specific domains | Tavily (filters domains server-side), then Exa (free, no key, gets `site:` added to the query) |
| `read_page` | Page as clean text | Jina Reader, then Tavily Extract, then raw fetch with HTML stripping |
| `youtube_transcript` | Subtitles of a video, including auto-subs | yt-dlp locally. If it is missing, the agent says so instead of crashing |
| `search_notes` | Search your own notes | only active with `NOTES_DIR` |
| `read_note` | Read a note | only active with `NOTES_DIR` |
| `save_research` | Store a result as a Markdown note | only active with `NOTES_DIR` |
| `read_skill` | Load a method on demand | always there |

No function depends on a single service. Without a Tavily key, everything runs
over the free routes, just a bit shakier.

---

## Skills

Skills are the reason the prompt stays small. The system prompt contains only
the index (name plus one sentence). The agent loads the full text itself via
`read_skill` when the task calls for it. Following the principle of the
Anthropic Agent Skills.

| Skill | What for |
|---|---|
| `web-scraping` | Data instead of prose: open datasets (CKAN, Socrata), JSON in the HTML (`__NEXT_DATA__` and relatives, JSON-LD), endpoints (`/wp-json/`, `/products.json`), probing pagination, limits of the tool |
| `seiten-index` | All URLs of a domain at once: robots.txt, sitemaps, news sitemaps, Wayback index |
| `archiv-recherche` | Fetch dead, blocked, or changed pages via the Internet Archive and compare versions |
| `such-operatoren` | Narrow down when the search fan brings only noise: domain filters, `filetype:`, exact phrase |
| `deep-research` | Break the question apart, keep a source register, look for the counter-thesis, provide evidence |
| `quellenarbeit` | Complete source citations for school and university, quotation versus paraphrase |
| `lead-recherche` | Search for leads and filter them against your own target-audience note |

**Why four skills for scraping and not one or eight:** They are cut by
*trigger*, not by topic. `web-scraping` applies when you are pulling data from
a known page. `seiten-index` when you still have to find the pages first.
`archiv-recherche` when the page is no longer there. `such-operatoren` when
the search yields nothing usable. Four different situations, no overlap, and
the agent loads only the one that fits.

A pure signpost skill that only points to others would, by contrast, be a
wasted tool round: the switch sits for free in the system prompt, which the
model sees anyway. That is why `web-scraping` keeps its details itself.

Three tests hold this together: every cross-reference must point to an
existing skill, no skill may recommend itself, and none may grow beyond
`MAX_SKILL_CHARS` (otherwise `read_skill` silently cuts off exactly the
sections at the end where the limits and the etiquette live).

**Adding a new skill**: drop a `.md` into `skills/`, with frontmatter:

```markdown
---
name: mein-skill
description: Ein Satz, der im Index steht und entscheidet, ob der Agent lädt
agents: research
---
# Mein Skill

Die Anleitung.
```

No code, no restart ritual. On the next run, the skill is in the index.

---

## Quick start

```bash
cp .env.example .env          # then fill in .env (at least OPENAI_API_KEY)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python main.py "Was kostet ein Lastenrad-Abo in Berlin?"
```

More invocations:

```bash
.venv/bin/python main.py --skills            # which methods exist
.venv/bin/python main.py --prompt            # see the assembled system prompt
.venv/bin/python main.py --mock "Testfrage"  # run through without an API call
echo "Auftrag" | .venv/bin/python main.py    # from a pipe
.venv/bin/python -m pytest                   # tests, without network and without a key
```

**Embedding instead of invoking:** The agent is not tied to any channel. If
you put it into a bot or a web backend, call `agent.run(config, auftrag)` and
get the finished text back. The call blocks, so in an async program it belongs
in `asyncio.to_thread()`.

---

## Costs

The only strictly paid service is the LLM API. A Tavily key makes the search
more reliable and costs credits, but it is optional: without a key the search
runs over the free Exa endpoint. Jina Reader and yt-dlp are free.

A thorough research run consumes more tokens than a normal chat, because six
or more pages go through the model in full text. `MAX_ROUNDS` caps that from
above. After every run, the usage is printed to stderr.

## Security

- Secrets live exclusively in the `.env`, never in the code. The `.env` is in
  `.gitignore`. If a key ever does land in the repo, the only fix is:
  generate a new key.
- Note paths are checked against the root folder so that an invented
  `../../.ssh/id_rsa` does not get through.
- `create_note` only creates new files and never overwrites an existing one.
- Errors in tools go back to the model as text instead of as a crash, so that
  the agent can react to a broken fetch.
- The scraping skill says explicitly: respect robots.txt, no circumventing bot
  protection, no fetch barrages against the same domain, no collecting
  personal data that the task does not require.

## Origin

This is the extracted research half of a larger personal assistant,
depersonalized and made runnable on its own. That is why the prompts and
skills are in German: they grew that way, and translating them would water
down the phrasings on which the quality depends. The code is named in English
and usable without knowing German.

Some skills build on prior work by others, each named in the `quelle:` line
in the frontmatter:

- `web-scraping`: patterns after [dumkydewilde, Ultimate Web Scraping](https://gist.github.com/dumkydewilde/97ab8337e30ca09c52b25343adf2aae1)
  and [Scrapfly, How to Scrape Hidden APIs](https://scrapfly.io/blog/posts/how-to-scrape-hidden-apis)
- `deep-research`: adapted from daymade/claude-code-skills (MIT)
- `quellenarbeit`: validation logic adapted from K-Dense-AI/claude-scientific-writer (MIT)
- `archiv-recherche` and `seiten-index`: independent, practically tested
  against the
  [Wayback CDX API](https://github.com/internetarchive/wayback/blob/master/wayback-cdx-server/README.md)

The skill principle itself (index in the prompt, full text loaded on demand)
comes from the Anthropic Agent Skills.

## License

MIT, see [LICENSE](LICENSE).
