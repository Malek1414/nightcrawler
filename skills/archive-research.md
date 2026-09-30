---
name: archive-research
description: Retrieve dead, changed, or unreachable pages from the Internet Archive and compare older versions against the current one.
agents: research
---
# Archive Research

Three situations where research would otherwise stop, but the archive rescues it:

1. **The page is gone.** A source links to something that returns 404.
2. **The page has changed.** The price, the figure, or the commitment used to
   say something different. That change is often the real story.
3. **The page won't let you in.** The fetch fails, but the archive holds a copy.

So the archive is not just a fallback. It is a research tool in its own right:
it makes the timeline visible.

## Tool 1: Which snapshots exist?

The CDX index is a normal URL and works with read_page:

```
https://web.archive.org/cdx/search/cdx?url=<url>&output=json&fl=timestamp,original,statuscode&collapse=timestamp:6&limit=50
```

- `fl=` selects the fields. Available: `urlkey`, `timestamp`, `original`,
  `mimetype`, `statuscode`, `digest`, `length`.
- `collapse=timestamp:4` groups by year, `:6` by month, `:8` by day.
  Without it you get hundreds of nearly identical entries.
- `collapse=digest` shows only snapshots where the content actually changed.
  This is the trick when you want to know WHEN something was rewritten.
- `from=2023&to=2024` narrows the time range, format `yyyyMMddhhmmss`,
  truncation allowed.
- `filter=statuscode:200` drops failed captures.
- `limit=-5` returns the five MOST RECENT snapshots instead of the oldest.

The `timestamp` looks like `20240317114532`: year, month, day, time.

## Tool 2: Read a snapshot

```
https://web.archive.org/web/<timestamp>/<url>
```

For example `https://web.archive.org/web/20240317114532/https://example.com/pricing`.

Shortcuts that save you computing a timestamp:

- `.../web/2023/<url>` jumps to the snapshot closest to 2023.
- `.../web/2/<url>` takes the oldest available one.

## Procedure

1. Try the live URL first. The archive is the second route, not the first.
2. If it fails or you need the timeline: query CDX and look at the snapshots.
3. Read the right snapshot with read_page.
4. ALWAYS label it in the answer: "Internet Archive snapshot from
   YYYY-MM-DD". An archived snapshot is never the current state, and
   presenting it as current is an error, not a detail.

## For cross-checking

When two sources give different figures, the most common explanation is not
that one is lying but that they are from different dates. The archive settles
this:

- If the old value appears in an old snapshot and the new value in a newer one,
  you have no contradiction but a dated change. Report it that way.
- If a value was changed silently, without the page showing an update date,
  that is exactly the claim you can document.
- `collapse=digest` shows you when changes happened without reading every
  snapshot individually.

## Limits you must know and state

- Not everything is archived. Small sites often not at all, dynamic content
  usually only partially.
- Pages that rely heavily on JavaScript are often archived as an empty shell.
  Little text in the result does not mean the page was empty.
- Some site owners have their pages removed from the archive after the fact.
  Then there is nothing, and that is an answer, not an error.
- Other archives exist too (archive.today, library and government archives).
  If the Internet Archive has nothing, a targeted search there is worth a try
  before you give up.

## What you don't do

- Don't bypass paywalls through the archive. If the archived snapshot is a
  paid article, don't cite it as freely accessible.
- Don't cite a version you haven't actually opened.
- Don't put an archive snapshot in the answer without its date.
