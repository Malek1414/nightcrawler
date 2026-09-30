---
name: web-scraping
description: Extract data from websites rather than prose, via open datasets, JSON embedded in HTML, hidden endpoints, and pagination, while respecting the limits of the tools.
agents: research
source: patterns based on dumkydewilde "Ultimate Web Scraping" (Gist) and Scrapfly "How to Scrape Hidden APIs", rewritten and adapted to this agent's tools
---
# Web Scraping

Use this when you need DATA from a website (lists, prices, dates, addresses)
rather than running text. The ground rule: **don't parse HTML as long as there
is a structured route.** Almost every modern site fetches its own content as
JSON. If you find that JSON, you get cleaner data, fewer fetches, and no
selectors that break tomorrow.

Order, always from easy to hard:

1. Is the data officially available?
2. Is the JSON already in the delivered HTML?
3. Is there an endpoint you can simply call?
4. Only then: parse the visible text.

## 1. Is the data officially available?

Spend 30 seconds checking whether someone publishes it voluntarily. Faster,
more complete, and cleaner than any scrape.

- **CKAN portals**: `<portal>/api/3/action/package_search?q=<term>` returns
  datasets including download URLs. Runs on a great many government and
  research portals.
- **Socrata portals**: `https://api.us.socrata.com/api/catalog/v1?q=<term>`
  searches all Socrata portals at once. A single dataset is then available via
  `<domain>/resource/<id>.json`.
- **Government agencies** almost always have an API or at least CSV. Run one
  targeted search for "<agency> API" or "<topic> dataset csv".

One dataset beats a hundred scraped pages. If you find one, say so in the
answer, even if you also scraped.

## 2. Is the JSON already in the HTML?

The most common win. The complete dataset is often in the delivered HTML, just
in a script tag instead of the visible text.

| Framework | Marker in the HTML | Where the data is |
|---|---|---|
| Next.js | `<script id="__NEXT_DATA__" type="application/json">` | `props.pageProps` |
| Nuxt | `window.__NUXT__=` or `<script id="__NUXT_DATA__">` | directly |
| Remix | `window.__remixContext =` | `state.loaderData` |
| SvelteKit | `<script type="application/json" data-sveltekit-fetched>` | directly |
| Gatsby | `/*! gatsby-page-data */`, plus `/page-data/<path>/page-data.json` | `result.data` |
| Vue SSR | `window.__INITIAL_STATE__=` | directly |
| Angular | `<script id="serverApp-state" type="application/json">` | directly |
| any | `<script type="application/ld+json">` | JSON-LD, typed |

JSON-LD is the underrated case: Event, Product, Article, Recipe,
Organization, opening hours, prices. SEO data is clean, structured data that
the site owner maintains themselves.

**Use raw mode for this:** read_page normally returns rendered text via
Jina, which discards script tags. Call `read_page(url, raw=true)` instead: it
fetches the HTML directly and puts every JSON-LD block and every
`window.__X__ =` / `__NEXT_DATA__` blob under "Embedded data" at the top,
followed by the page text. If raw mode shows no embedded data, go via step 3.

## 3. Endpoints that almost always exist

Try them directly with read_page. Costs one fetch, saves twenty if it works.

| Platform | Endpoint | Telltale sign |
|---|---|---|
| WordPress | `/wp-json/wp/v2/posts?per_page=100&_fields=title,date,link` | `<link rel="https://api.w.org/">`, `/wp-content/` |
| WordPress | `/wp-json/wp/v2/pages`, `/wp-json/wp/v2/categories` | same |
| Shopify | `/products.json?limit=250`, `/collections/all/products.json` | `cdn.shopify.com` in the source |
| Drupal | `/jsonapi/node/article?page[limit]=50` | `/sites/default/files/` |
| Ghost | `/ghost/api/content/posts/?key=<key>` | `ghost` in the source |
| Squarespace | any URL plus `?format=json` | `squarespace` in the source |
| Wix | paths under `/_api/` | `wix.com` in the source |
| Next.js | `/_next/data/<buildId>/<path>.json` | `__NEXT_DATA__` in the HTML |
| general | `/api/`, `/api/v1/`, `/ajax/`, `/json/`, `/feed`, `/rss` | paths in the page text and in links |

`_fields=` on WordPress is gold: you fetch the three fields you need instead
of the full article content every time.

**Probe pagination and limits** instead of pulling twenty pages one by one:

- Patterns: `?page=2`, `?offset=20&limit=20`, `?cursor=...`, `?per_page=100`
- Probe the limit: 50, then 100, then 250. Most APIs cap somewhere and quietly
  return fewer results instead of complaining. So count.
- The end of the list is an empty array or an error object. Both are a clean
  stop signal; don't guess.
- `total`, `count`, or `X-WP-TotalPages` tells you in advance how much there
  is. If it says 4000 entries and you need 20, fetch 20.

**Verify an endpoint before you trust it:** compare two or three values against
the visible page. If you get HTML instead of JSON, it's an error page, not an
endpoint. If the response is suspiciously short, the bot protection answered.

## 4. Only then: visible text

The slowest and most brittle route, not the first. `.ics` feeds (marker
`BEGIN:VCALENDAR`) are the cleanest route to events; look on the page for
"ical", "ics", "subscribe to calendar". You can't read `.xml.gz`, it's
compressed.

## Limits of your tool, and what you say then

read_page does a plain GET. No POST, no custom headers, no JavaScript.
Specifically:

- **GraphQL** (`/graphql`, `/api/graphql`) almost always needs POST with a query body.
- **Algolia, Elastic, and similar** need an app ID and API key in the header.
- **Endpoints with required headers** (Referer, X-Token, Cookie) respond with
  401, 403, or an empty list.
- **Infinite scroll without a recognizable endpoint** needs a real browser.

Then don't use tricks, don't guess, don't invent anything. Say in one sentence
which endpoint it would be, why it fails, and what the best manual route is
(developer tools, Network tab, filter by XHR). A precise pointer is worth more
than an invented dataset.

## Robustness

- Spot-check results against the visible page.
- Number formats: 1.200,50 (German and other European formats) is not 1200.50
  (English format). For dates, 03.04. or 03/04 can be April 3 or March 4,
  depending on the site.
- Values that are suspiciously round or identical across many records are
  usually a parsing error, not a finding.
- For recurring data sources: say that a permanent integration is worth it
  instead of scraping every time.

## Etiquette

- Respect robots.txt and terms of use. Whatever is excluded there, you don't
  fetch, even if it were technically possible.
- No circumventing bot protection, logins, or paywalls.
- A few targeted requests, no series of requests against the same domain.
- Don't collect personal data that the task doesn't need, even if the API
  returns it.

## When this isn't enough

- You need many pages from the same domain, not one: skill `site-index`.
- The page is dead, blocked, or has changed: skill `archive-research`.
- You can't find the right page in the first place: skill `search-operators`.
