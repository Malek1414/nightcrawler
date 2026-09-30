"""Nightcrawler: system prompt, tools, handlers, quality gate.

Four parts you can change independently:

1. _SYSTEM       The working method: HOW to research (search fan, minimum
                 pages read, mandatory cross-check). This is where quality is
                 decided, not in the code.
2. _tools()      What the agent can do. Each tool is a JSON schema for the model.
3. _handlers()   Which Python function sits behind each tool name.
4. _Evidence     Counts what was actually read, so the "read at least N pages
                 from M domains" rule is checked in code, not just requested.

The detailed methods are NOT in the prompt but in skills/*.md. The prompt
carries only the index; the agent loads the right skill with read_skill.
New method = new Markdown file, nothing here.

The user's profile (profile.toml) goes into the system prompt, so the agent
knows who it works for: where they are, what they want, what they can spend.

If the tool loop fails completely, Claude's built-in web search answers as a
fallback, so research never fails outright.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from core import skills
from core.config import Config
from core.llm import run_tool_loop, tool
from integrations import notes, profile as prof, reach, web_search

logger = logging.getLogger(__name__)

AGENT = "research"

_SYSTEM = """You are {agent_name}, a research and scraping agent{owner_suffix}.

How you work (proactive and multi-step; never stop at the first hit):
- You NEVER ask whether you should research, and never ask for the task to be
  confirmed. If something is unclear, make the obvious assumption, state it in
  half a sentence in the answer, and start.
- Know why you are searching before you search. From the task and the user
  profile below, decide what would actually be useful to this person, and aim
  the searches at that instead of collecting everything on the topic.
- Start with a search fan instead of a single search: at least 3 web_search
  calls in the SAME turn (they run concurrently, so they cost barely more time
  than one). Variant 1 = the task's own words, variant 2 = a synonym or
  technical term, variant 3 = the phrasing a local or official source would use
  (for example the local language of the place in question).
- Then compare the result lists: which phrasing brings fresh, official,
  concrete sources? Continue with that track and refine it. Phrasings that
  bring only ads and blog noise are not repeated.
- Read at least {min_pages} results with read_page, from at least {min_domains}
  different domains, several per turn. Snippets alone are not evidence. If a
  page links to something that answers the question better, follow it.
- Cross-checking is mandatory, not optional: every number, date, price,
  deadline, and name must be checked against a SECOND, independent source
  before the answer (not the same domain, not the same press release).
  Anything resting on one source is marked [unverified]. If two sources
  disagree, give both values with their sources instead of picking one.
- You may stop only when another search round brings nothing new, not as
  soon as you have a plausible answer.
- YouTube link or questions about a video: use youtube_transcript.
- Thorough tasks ("research this properly", a report, a paper): load the
  skill deep-research FIRST. Quotes, literature, or citations: load the skill
  citations. Pulling structured data from a website (lists, prices, dates):
  load the skill web-scraping.
- Need many pages from one domain (all press releases, all locations, all
  jobs): load the skill site-index instead of clicking through navigation.
- The search fan brings only ads and comparison sites: do not repeat the
  search, load the skill search-operators and narrow down.
- read_page fails (404, blocked, page changed) or you need an earlier version
  of a page: load the skill archive-research instead of giving up the source.
- Events, meetups, jobs, gigs, grants, competitions, investor events, or
  "what should I go to / apply for": load the skill opportunity-scout FIRST
  and rank with score_opportunity. Always look for the cheapest way in (free
  tickets, volunteer or speaker slots, discounts, travel grants).
- Leads, addresses, organisations, or contacts ("who can we reach out to",
  "find me providers in X", "a list for outreach"): load the skill
  lead-research FIRST and work by it.{notes_block}

Answer {style} in {language}. No emojis. End with the most important sources
as links (max. 5); for citation work, full references per the skill instead."""

# Only inserted when a notes folder is configured. Without a folder the prompt
# must not mention these tools, or the model hallucinates them.
_NOTES_BLOCK = """
  And ALWAYS read the target audience from the notes first:
  read_note("{target_note}"). That note decides what goes into the list.
  Whatever it excludes never lands in the list unasked. The note is not a
  ban on thinking, though: if you notice a missing category or find a real
  reason against an exclusion, say so. Separately from the list, at the end,
  as a suggestion with a reason and the question whether to add it.
- If the notes contain rules for what you are researching (audience,
  criteria, earlier research on the same topic): search_notes or read_note
  first, then the web. What was already decided there is not re-researched.
- On "save this" / "remember this research", or when the result is clearly
  expensive and reusable: call save_research."""


# --------------------------------------------------------------------- Tools

def _tools(config: Config) -> list[dict]:
    """Tool list. Note tools only when a folder is configured."""
    tools = [
        tool("web_search", "Web search: finds current pages and articles on a topic. "
             "Depending on the provider, also returns a short summary.",
             {"query": {"type": "string", "description": "Search query"},
              "num_results": {"type": "integer", "description": "Number of results, 1-10 (default 5)"},
              "domains": {"type": "string", "description": "Optional: search only these "
                          "domains, comma-separated, e.g. 'europa.eu, oecd.org'. "
                          "For targeted searches in official or specialist sources."}},
             required=["query"]),
        tool("read_page", "Read a web page as text (article, event page, docs, "
             "directory). With raw=true: fetch the HTML directly and return the "
             "embedded structured data (JSON-LD, __NEXT_DATA__ etc.) first; use "
             "that for scraping prices, dates, and lists.",
             {"url": {"type": "string", "description": "Full URL including https://"},
              "raw": {"type": "boolean", "description": "Return embedded data blobs "
                      "plus stripped text instead of rendered Markdown (default false)"}},
             required=["url"]),
        tool("youtube_transcript", "Get the subtitles/transcript of a YouTube video.",
             {"url": {"type": "string", "description": "YouTube URL"}},
             required=["url"]),
        tool("geo_distance", "Straight-line distance in km between the user's home "
             "(from the profile) or a given origin and a place. Uses OpenStreetMap.",
             {"place": {"type": "string", "description": "Destination, e.g. 'Station F, Paris'"},
              "origin": {"type": "string", "description": "Optional origin; defaults to the user's home"}},
             required=["place"]),
        tool("score_opportunity", "Score one opportunity 0-100 for THIS user: payoff "
             "and fit against the real all-in cost (fee plus estimated travel and "
             "lodging from their home), their budget, travel limit, and deadline. "
             "Returns the breakdown and warning flags. Call it for every candidate "
             "before ranking; several calls per turn are fine.",
             {"title": {"type": "string", "description": "Name of the event/job/grant"},
              "payoff": {"type": "integer", "description": "1-5: what it could be worth "
                         "to this user (5 = money, funding, or a job directly)"},
              "fit": {"type": "integer", "description": "1-5: match with the user's goals"},
              "fee": {"type": "number", "description": "Cheapest entry fee you found, "
                      "in the profile currency (0 if free)"},
              "location": {"type": "string", "description": "Venue city or address; "
                           "omit if online"},
              "online": {"type": "boolean", "description": "true if it can be attended online"},
              "investor_presence": {"type": "integer", "description": "0-3: 0 none, 1 some, "
                                    "2 investors named as attendees/judges, 3 investor event"},
              "deadline": {"type": "string", "description": "Application/registration "
                           "deadline as YYYY-MM-DD, if any"}},
             required=["title", "payoff", "fit"]),
    ]
    if config.notes_dir:
        tools += [
            tool("search_notes", "Search your own notes (file names and content). "
                 "Use this to find existing rules before going to the web.",
                 {"query": {"type": "string", "description": "Search term"}},
                 required=["query"]),
            tool("read_note", "Read a note (path relative to the notes folder, e.g. "
                 "'target-audience.md'). Mandatory before any lead research.",
                 {"rel_path": {"type": "string", "description": "Path relative to the notes folder"}},
                 required=["rel_path"]),
            tool("save_research", "Store a research result as a note.",
                 {"title": {"type": "string", "description": "Short, descriptive title"},
                  "content": {"type": "string",
                              "description": "Finished Markdown note, sources at the end"}},
                 required=["title", "content"]),
        ]
    return tools + [skills.tool_spec()]


# ------------------------------------------------------------ Quality gate

class _Evidence:
    """Counts pages actually read in this run (successful read_page calls).

    The prompt asks for N pages from M domains. Models skip that silently
    when a plausible answer shows up early. The gate turns the rule into a
    check: a final answer below the bar is sent back once, and the model must
    either keep reading or say in one line why fewer sources are enough.
    """

    def __init__(self, min_pages: int, min_domains: int):
        self.min_pages, self.min_domains = min_pages, min_domains
        self.urls: set[str] = set()
        self._lock = threading.Lock()

    def add(self, url: str) -> None:
        with self._lock:
            self.urls.add(url)

    @property
    def domains(self) -> set[str]:
        return {urlparse(u).netloc.removeprefix("www.") for u in self.urls}

    def gate(self, _answer: str) -> str | None:
        pages, domains = len(self.urls), len(self.domains)
        if pages >= self.min_pages and domains >= self.min_domains:
            return None
        return (f"Before you finish: you have read {pages} page(s) from {domains} "
                f"domain(s); the method asks for at least {self.min_pages} pages from "
                f"{self.min_domains} domains, with numbers, dates, and prices "
                "cross-checked. Keep researching, or, if the task genuinely needs "
                "fewer sources (a simple lookup, a single given URL), give the final "
                "answer again with one line saying why.")


# ------------------------------------------------------------------ Handlers

def _save_research(config: Config, title: str, content: str) -> str:
    try:
        return notes.create_note(config, title, content, folder=config.research_folder)
    except Exception as e:
        return f"Could not save the note: {e}"


def _read_page(config: Config, evidence: _Evidence | None, cache: reach.PageCache | None,
               url: str, raw: bool = False) -> str:
    text = reach.read_page(url, tavily_key=config.tavily_api_key, raw=raw, cache=cache)
    if evidence is not None:
        evidence.add(url)
    return text


def _geo_distance(user: prof.Profile | None, place: str, origin: str = "") -> str:
    if origin:
        lat1, lon1, _ = prof.geocode(origin)
        lat2, lon2, name = prof.geocode(place)
        km = prof.haversine_km(lat1, lon1, lat2, lon2)
    else:
        km = prof.distance_from_home(user, place)
        name = place
    return f"{km:.0f} km (straight line) to {name}"


def _handlers(config: Config, user: prof.Profile | None = None,
              evidence: _Evidence | None = None,
              cache: reach.PageCache | None = None) -> dict:
    handlers = {
        "web_search": lambda query, num_results=5, domains="":
            reach.web_search(query, num_results, config.tavily_api_key, domains),
        "read_page": lambda url, raw=False: _read_page(config, evidence, cache, url, raw),
        "youtube_transcript": lambda url: reach.youtube_transcript(url),
        "geo_distance": lambda place, origin="": _geo_distance(user, place, origin),
        "score_opportunity": lambda **kw: json.dumps(
            prof.score_opportunity(user, **kw), ensure_ascii=False),
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


# ----------------------------------------------------------------------- Run

def load_user(config: Config) -> prof.Profile | None:
    """Profile plus resolved home coordinates. Never fatal."""
    try:
        user = prof.load_profile(config.profile_path)
    except prof.ProfileError as e:
        logger.warning("%s", e)
        user = None
    if config.mock_llm:
        return user  # no network in mock mode
    return prof.with_location(user, config.location_source)


def build_system_prompt(config: Config, user: prof.Profile | None = None) -> str:
    """Everything here is stable between runs, so it stays in the prompt
    cache. The current time goes into the user message instead."""
    notes_block = (_NOTES_BLOCK.format(target_note=config.target_group_note)
                   if config.notes_dir else "")
    return _SYSTEM.format(
        agent_name=config.agent_name,
        owner_suffix=f" working for {config.owner_name}" if config.owner_name else "",
        min_pages=config.min_pages,
        min_domains=config.min_domains,
        notes_block=notes_block,
        style=config.answer_style,
        language=config.answer_language,
    ) + prof.render(user) + skills.index_block(AGENT)


def run(config: Config, task: str) -> str:
    """Run one research task and return the finished answer."""
    user = load_user(config)
    system = build_system_prompt(config, user)
    now = datetime.now(ZoneInfo(config.timezone))
    evidence = _Evidence(config.min_pages, config.min_domains)
    message = f"Current time: {now:%A, %Y-%m-%d %H:%M} ({config.timezone}).\n\n{task}"
    try:
        return run_tool_loop(
            config, config.agent_model, system,
            [{"role": "user", "content": message}],
            _tools(config), _handlers(config, user, evidence, reach.PageCache()),
            max_rounds=config.max_rounds, agent=AGENT, gate=evidence.gate,
        )
    except Exception:
        logger.exception("Tool loop failed, falling back to built-in web search")
        return web_search.search(config, task)
