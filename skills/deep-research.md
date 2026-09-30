---
name: deep-research
description: Thorough multi-stage research with cross-checked sources, for important questions, presentations, and decisions.
agents: research
source: adapted from daymade/claude-code-skills deep-research (MIT)
---
# Deep Research

## 0. Start immediately
- No clarifying questions, no confirming the assignment, no "should I?". Note ambiguities as assumptions and state them in the answer.
- The cross-check (section 4) replaces the clarifying question: better to check twice than to ask once.

## 1. Break down the question
- Split the task into 3 to 5 independent sub-questions (What exactly? Who says what? What are the numbers and facts? What is disputed?).
- For each sub-question, a search fan of 3 queries, all sent in the same turn (they run in parallel): the literal term, a synonym or technical term, and a variant in another language (for example the local language of the topic, or English).
- Compare the result lists before you read: which phrasing brings fresh, official, concrete sources? Refine only that lead; don't repeat the weak phrasings.
- Mark each sub-question: DEEP (read the full text with read_page) or SCAN (search results are enough).

## 2. Collect sources (keep a register)
- Goal: at least 6 to 8 distinct sources from at least 4 different domains, of which at least 6 are actually read with read_page.
- Call read_page several times per turn too, not one page after another.
- No single source may supply most of the evidence.
- Classify each source: official, academic, journalism, community. And note the publication date.
- Downgrade old sources. State the as-of date in the answer ("As of: YYYY-MM-DD").

## 3. Cite
- Every factual claim gets a source number [1], [2], and so on.
- What you cannot support: mark as [unverified], don't drop it and never invent anything.
- NEVER invent URLs. Only give links you actually opened or saw in results during this research.

## 4. Cross-check (mandatory before answering)
- Every number, date, price, deadline, and name is checked against a SECOND, independent source: a different domain, not a copy of the same press release.
- If two sources contradict each other: give both values with their source, don't pick one yourself.
- Formulate the counter-thesis and search for it once, specifically ("criticism of X", "X debunked").
- Claims that rest on only ONE source: find a second source or mark them as [unverified].
- Check: is an important perspective (official body, those affected, experts) missing entirely?
- Stopping criterion: stop only when another round brings nothing new.

## 5. Answer format
- Key finding first (2 to 3 sentences), then details in short paragraphs.
- Numbered source list at the end, with dates.
- With save_research: store the full note with all sources, and give only the summary in the answer plus a pointer to the note.
