---
name: site-index
description: Find all relevant URLs of a website at once instead of clicking through it, using robots.txt, sitemaps, and the Wayback index.
agents: research
---
# Site Index

Use this when you don't need ONE page but need to know what exists on a domain
at all: every press release, every location, every job posting, every article
on a topic. Don't click through the navigation. Websites publish their table of
contents voluntarily, because search engines need it.

## Step 1: Read robots.txt

`<domain>/robots.txt` is the cheapest fetch of the whole research and gives you
two things:

- **`Sitemap:` lines** with the complete tables of contents. Large sites have
  several, often split by topic (news, videos, archive, premium).
- **`Disallow:` lines** incidentally reveal the site structure, including
  internal paths like `/api/` or `/search/`. Whatever is excluded there, you
  don't fetch. Reading it is allowed; ignoring it is not.

## Step 2: Get the sitemap

If there is no `Sitemap:` line, try the usual paths directly:

- `/sitemap.xml`, `/sitemap_index.xml`, `/sitemap-index.xml`
- `/wp-sitemap.xml` (WordPress 5.5 and later), `/sitemap_index.xml` (Yoast)
- `/news-sitemap.xml`, `/sitemaps/news-en.xml` (news sites; the language code varies)

What you get:

- A **sitemap index file** points to further sitemaps. Take the ones whose name
  matches your question, not all of them.
- A **regular sitemap** lists URLs, often with `<lastmod>`. That shows you what
  changed most recently without a single additional fetch.
- A **news sitemap** only contains roughly the last 48 hours, but with title
  and publication date. The fastest route to "what did X publish this week".

**Limit:** you can't read `.xml.gz`, it's compressed. Go via step 3 instead, or
try the uncompressed variant without `.gz`.

## Step 3: Wayback as a full index

If a site has no usable sitemap, the Internet Archive still has a list of every
URL it has ever seen. The CDX index is an ordinary URL you can fetch with
read_page:

```
https://web.archive.org/cdx/search/cdx?url=<domain>/*&output=json&fl=original&collapse=urlkey&limit=500
```

- `url=<domain>/*` takes everything under the domain, `url=<domain>/press/*`
  only one path. The latter is usually what you want.
- `collapse=urlkey` removes duplicates; otherwise you get every capture of every
  page separately.
- Always set `limit=`. Without a limit the response can get huge.
- `filter=urlkey:.*press.*` narrows further when the path isn't cleanly
  separated.

This is also the route to pages that no longer exist. How to read them is
covered in skill `archive-research`.

## Step 4: Read selectively from the index

Now you have a list. Don't read all of it.

- Sort by what answers the question: date, path pattern, title.
- Read five to ten pages with read_page, several per turn.
- If the list is very long: say in the answer how many URLs there are in total
  and which criterion you used to select. A selection without a stated
  criterion reads like completeness, and it isn't.

## When this is worth it

- Directories, member lists, location lists
- Press rooms and newsrooms ("what has X published since January")
- Job postings
- Anything where you'd otherwise click "next" twenty times

## When not

- A single concrete question. A normal search is faster.
- Sites that don't put their content in the sitemap at all (many shops,
  login areas). Then go via skill `web-scraping`.
