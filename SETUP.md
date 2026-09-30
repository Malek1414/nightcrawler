# Setting up Nightcrawler

This guide is a recipe. Work through it yourself or hand the whole thing to a
coding agent (Claude Code, Cursor, Codex). Every step ends with a
**checkpoint**: only move on once it passes.

It is built in layers. After step 2 you have a working agent. Everything after
that is optional and switches itself off as long as the matching values in
`.env` are missing.

---

## For the coding agent

If you are an agent working through this, follow these rules:

1. **No secrets in code.** All credentials go into `.env`, never into a `.py`
   file, never into a commit. If someone asks you to hardcode a key, point
   that out and put it in `.env`.
2. **You cannot obtain keys.** API keys must be created by the human in their
   browser. Say clearly which value you need and where it comes from, then wait.
3. **Keep the order.** Get step 1 running before step 2.
4. **Test after every step**, not at the end. The checkpoint says how.
5. **Never commit what is in `.gitignore`.** Before every commit, check that
   neither `.env`, `profile.toml`, nor the notes folder is in the diff.

---

## What you need

| What | For | Cost |
|---|---|---|
| Python 3.11 or newer | Everything | free |
| Anthropic API access | The thinking | pay per use; a thorough run is typically well under $1 on Sonnet, more on Opus |
| Optional: Tavily account | More reliable search and page reading | free tier, then credits |
| Optional: yt-dlp | YouTube transcripts | free |
| Optional: a notes folder | Your own rules, and a place for results | free |

No server needed. It runs on any laptop.

---

## Step 0: Set up the project

```bash
cd nightcrawler
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

**Checkpoint:** `.venv/bin/python -m pytest` passes, all green. The tests need
neither network nor an API key, so this must already work.

---

## Step 1: Run it for free

```bash
.venv/bin/python main.py --mock "Test"
.venv/bin/python main.py --skills
.venv/bin/python main.py --prompt
```

**Checkpoint:** `--mock` prints `[Mock] Answer from ...`, `--skills` lists
eight skills, and `--prompt` shows the system prompt with the skill index at
the end.

---

## Step 2: Research for real

Either put a key into `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

or leave it empty and log in once with the Anthropic CLI (`ant auth login`);
the SDK picks that up automatically.

```bash
.venv/bin/python main.py "What does a cargo bike subscription cost in Amsterdam?"
```

**Checkpoint:** the log on stderr shows several `web_search` calls in the
first round, then several `read_page` calls, and the answer ends with sources.
The last stderr line shows token usage.

To save money, set `AGENT_MODEL=claude-sonnet-5` or `EFFORT=medium`.

---

## Step 3: Tell it who you are (recommended)

This is what turns a generic scraper into your scout.

```bash
cp examples/profile.example.toml profile.toml
```

Edit `profile.toml`: home city, goals, interests, budget, how far you travel,
and how much each factor should count. It stays local (`profile.toml` is in
`.gitignore`).

```bash
.venv/bin/python main.py --profile
```

**Checkpoint:** `--profile` prints your profile with coordinates next to your
city (it geocodes the city once via OpenStreetMap).

Location options (`LOCATION_SOURCE` in `.env`):

- `profile` (default): only the city from your profile is used.
- `ip`: approximate location from your public IP via ip-api.com. Opt-in,
  because it sends your IP to a third party.

Then try:

```bash
.venv/bin/python main.py "Free or cheap AI meetups and pitch nights I can reach in the next 6 weeks"
```

---

## Step 4: Better search (optional)

Get a key at https://tavily.com and put it in `.env` as `TAVILY_API_KEY`.

**Checkpoint:** the log no longer shows `continuing with Exa` warnings.

---

## Step 5: YouTube transcripts (optional)

`yt-dlp` is in `requirements.txt`. If it is missing, the agent says so
instead of crashing.

---

## Step 6: Connect notes (optional)

Set `NOTES_DIR` to an absolute path of a folder of Markdown files (an
Obsidian vault works as is). The agent can then search and read your notes
and save research as new notes. It never overwrites or edits existing ones.

**Checkpoint:** `--prompt` now mentions `read_note` and `save_research`.

---

## Step 7: Target audience for lead research (optional)

Copy `examples/target-audience.example.md` into your notes folder as
`target-audience.md` (or set `LEADS_TARGET_NOTE`) and fill in the Include,
Exclude, Signals on the page, and Edge cases sections.

---

## Step 8: Add your own methods

Drop a Markdown file into `skills/` with frontmatter (`name`, `description`,
`agents: research`). It appears in the index on the next run.

**Checkpoint:** `.venv/bin/python -m pytest tests/test_skills.py` stays green
(it checks frontmatter, descriptions, length, and cross-references).

---

## When something does not work

| Symptom | Cause |
|---|---|
| `authentication_error` / 401 | No `ANTHROPIC_API_KEY` and no `ant auth login`. For testing, use `--mock` |
| Only one search instead of three | Model too weak or effort too low. Raise `AGENT_MODEL` or `EFFORT` |
| Answer ends with "open or unverified" and feels unfinished | The run hit `MAX_ROUNDS`. Raise it or narrow the task |
| `Notes folder not configured` | `NOTES_DIR` missing or pointing to a path that does not exist |
| Pages come back empty | Jina is blocked or the page needs a login. With a Tavily key, the second stage runs |
| `distance unknown` in scores | No home location. Set `[home] city` in `profile.toml` |
| Answer without sources | The fallback kicked in. Look for `Tool loop failed` in the log |
