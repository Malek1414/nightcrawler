---
name: search-operators
description: Narrow search queries when the search fan returns only ads and blog noise, using domain filters, file types, and exact phrases.
agents: research
---
# Search Operators

The search fan from the prompt gives you breadth. This gives you depth: what to
do when three phrasings bring back the same noise. Symptoms: only comparison
sites, only SEO copy, only ads, not a single primary source.

## The strongest lever: the `domains` field

web_search has a `domains` parameter. It filters server-side and is more
reliable than any operator in the query text:

    web_search(query="rent index methodology", domains="europa.eu, oecd.org")

When to use it:

- **Official sources**: `europa.eu`, `oecd.org`, `un.org`, national statistics
  offices (`census.gov`, `ons.gov.uk`, `destatis.de`), legislation portals, and
  the sites of ministries, regional agencies, and chambers.
- **Academic**: `pubmed.ncbi.nlm.nih.gov`, `arxiv.org`, `doaj.org`,
  `scholar.archive.org`.
- **The company itself**: if you want to know what a company says, query its
  domain, not the press coverage about it. For the cross-check you then need
  the opposite: a domain that is NOT theirs.

Important: this means you searched one-sidedly. A result that comes from a
single domain does not satisfy the cross-check. The filter is a tool for
getting a specific perspective, not for picking one.

## Operators in the query text

The classic Google operators work to varying degrees depending on the provider.
They are not a contract, just an attempt. If the attempt brings nothing, it was
the wrong approach, not the wrong syntax.

- `"exact phrase"` finds technical terms and quotes that would otherwise be
  split up.
- `-word` excludes. `-shop -"price comparison" -buy` cleans up product
  questions immediately.
- `filetype:pdf` is the direct route to studies, expert reports, annual reports,
  and government papers. The full text behind a PDF is usually the primary
  source everyone else only writes about.
- `filetype:xlsx`, `filetype:csv` leads to raw data instead of articles about
  raw data.
- `inurl:press`, `inurl:annual-report` hits structural pages.
- `intitle:` requires the term in the title, not just anywhere in the text.
- Adding the year (`rent index 2026`) is often more effective than any date
  filter.

## An important caveat

Not every search provider works with keywords. Semantic search engines
understand the meaning of your query and partly ignore operators. There,
something else works much better: **speak the language of the source you want
to find.**

- Looking for a study? Phrase it like an abstract, not like a question.
- Looking for a government page? Use the administrative term, not the everyday
  term.
- Looking for a company? Use its product name.

That is the real trick, and it works with every provider.

## Order

1. Search fan as in the prompt, three phrasings, broad.
2. Compare the result lists. Is there a usable lead? Then refine and you're
   done; this skill isn't needed.
3. Only if everything is noise: narrow down. First `domains` for the source
   type you want. Then `filetype:` if you're looking for a document. Then
   exclusions.
4. Still nothing: maybe the question can't be answered with a web search. Say
   so instead of starting the tenth attempt. State what you tried and where the
   answer probably lies (register, agency, database, contact person).

## When you've found raw data

A `filetype:csv` hit or a data portal is a finding, not an intermediate step.
How to get at such datasets systematically is covered in skill `web-scraping`,
section "Is the data officially available?".
