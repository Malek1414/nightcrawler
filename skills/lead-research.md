---
name: lead-research
description: Find leads and check them against your own target-audience note so that nothing unsuitable ends up on the list.
agents: research
---
# Lead Research

For any task that involves finding addresses, organizations, companies, or contacts: "find me leads", "who can we reach out to", "find providers in X", "list for outreach".

## Step 1: Load the target audience from the notes, always first

Before you run a single search:

    read_note("target-audience.md")

The exact path is set in the .env under `LEADS_TARGET_NOTE`. This note is the source of truth. It has the sections "Include", "Exclude", "Signals on the page", "Edge cases", and "Open suggestions". It gets changed without anyone touching code, so never rely on your memory and never on this skill alone.

If there is a separate note on the region or on timing (such as time windows, seasons, trade fair dates), read it as well. When to reach out often matters more than who.

If you can't find the note, search with `search_notes("target-audience")`. If it really doesn't exist, work from the description in the task, say so in one sentence at the end, and suggest creating the note.

## Step 2: Search narrowly, not broadly

Search with the terms from the "Include" section, not with generic terms. A generic term attracts exactly the results you'll have to filter out later; a specific industry term doesn't.

- Good: the industry's own term plus place plus service
- Bad: "companies in Chicago", "organizations for X"
- Directories and overview pages are worth more than single hits: associations, chambers of commerce, industry directories, official registers. Read such pages with `read_page` and you get ten leads instead of one. How to get at the data is covered in skill `web-scraping`, and if you want the whole directory at once, in skill `site-index`.

## Step 3: Check every hit before it goes on the list

**Hard exclusion by name.** If the name contains one of the words listed under "Exclude" in the target-audience note, the hit is dropped immediately, without opening the page. This saves most fetches.

**Check on the page.** For everything that gets through and isn't an obvious fit, run `read_page` on the website and look for the signals listed under "Signals on the page" (services, audience, age ranges, opening hours, prices).

When in doubt: **leave it out rather than put it in.** A short clean list is worth more than a long one that has to be re-sorted by hand afterwards. Don't discard edge cases; mark them as edge cases, especially those the note lists under "Edge cases".

## Step 3b: Push back when you have a reason

The target-audience note reflects today's thinking, not a ban on thinking. You are the one who actually saw the results, so you may know better than the list. Two cases:

- **Something is missing.** You come across a type of organization or company that clearly fits but doesn't appear in "Include" (such as an association or a platform through which you can reach many at once).
- **An exclusion doesn't hold.** You find concrete evidence that contradicts a rule under "Exclude". The rule isn't wrong, but this case doesn't fall under it.

This is how you handle it, and only this way:

1. **Don't add it to the list.** No quietly slipping it in, not even "just this one". The list stays clean according to the note.
2. **At the end, write a separate "Suggestion" block.** What you would add, why, with the evidence from the page, and roughly how many additional leads it would bring.
3. **Ask directly** whether it should be added. One question, not three.
4. If yes: this agent cannot edit the note (it can only create new ones). So say in one sentence that the entry belongs under "Open suggestions" in the target-audience note. You can then do the follow-up research right away.

Restraint: at most two suggestions per research run, and only ones you can back up with a concrete case. "You could also try X" without a finding is not a suggestion, it's noise.

## Step 4: Copy contact details, never guess them

Email addresses and phone numbers come from the imprint, legal notice, or contact page of the actual website. Never invent a pattern like info@something.com. If you find no contact, write "no contact found" in the row and keep the lead anyway, with the URL.

## Step 5: Deliver the result

A table, one lead per row:

| Name | Type | Place | Contact | Website | Why it fits |

"Why it fits" is ONE sentence with evidence from the page, not your guess.

Then two lines that must never be missing:

- **Excluded:** how many and why, grouped by category, for example "14 excluded: 11 wrong audience, 3 outside the region". This makes the filtering visible, and it shows when the filter is too strict.
- **Edge cases:** the marked cases, one sentence each, so a decision can be made.

Add the block from step 3b if you have one.

From about ten leads, or when the research took a lot of effort: store the result with `save_research`, title format "Leads <audience> <place> <date>". In the answer, give only the summary plus a pointer to where the full list is.

## What you don't do

- No list without first reading the target-audience note.
- Don't add anything on your own that the note excludes, however good your reason. The reason belongs in the suggestion, not in the table.
- Conversely, don't stay silent when you notice something. A silent list that misses an obvious opportunity is also a mistake.
- No addresses from memory or from search snippets alone. Whatever is on the list, you have seen on a page.
- No bulk fetching against the same domain; a few targeted requests are enough.
- No finished outreach messages unless asked. Your job here is the list.
