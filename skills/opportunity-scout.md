---
name: opportunity-scout
description: Find events, jobs and gigs, grants and competitions, clients, and investor-heavy rooms that fit the user, then rank them by payoff against the real cost of getting there
agents: research
---
# Opportunity Scout

For any task like "what should I go to", "find me events / meetups /
hackathons", "any grants or competitions I can enter", "where can I meet
investors", "find gigs or roles for me", "where are my next clients". The goal
is not a long list. It is a short list the user can act on this week, with
the cheapest way in for each item.

## Step 1: Start from the person, not the topic

Read the user profile in the system prompt before searching. Derive:

- **What they are trying to achieve** (from goals). That decides the category
  mix: raising money points to investor rooms and competitions, finding
  clients points to industry events and lead lists, a career move points to
  jobs, meetups, and hiring events.
- **Where and when**: home base, travel limit, and the time window in the task
  (default: the next 90 days).
- **What they can spend**: fee cap and all-in budget.

If there is no profile, make the obvious assumption, state it in half a
sentence, and continue.

## Step 2: Search where opportunities are listed, not where they are discussed

Use the search fan from the system prompt, but aim it at aggregators and
primary listings. By category:

- **Events and meetups:** Meetup, Luma (lu.ma), Eventbrite, city startup
  calendars, university and incubator event pages, conference sites.
- **Jobs and gigs:** company career pages, Wellfound, Hacker News "Who is
  hiring", niche job boards for the field, freelance platforms.
- **Grants and competitions:** government and EU funding portals, foundation
  sites, accelerator application pages, Devpost and similar for hackathons,
  university prize pages.
- **Leads and clients:** load skill `lead-research` and follow it.
- **Investor-heavy rooms:** demo days, pitch competitions, angel network
  events, VC office hours, family office and wealth forums, startup
  conference investor tracks, accelerator batch showcases.

Official listing pages are directories: read them once, get ten items. For
many pages of one site, load skill `site-index`. For event pages, load
skill `web-scraping` and use `read_page(url, raw=true)`: most event pages
carry JSON-LD `Event` data with date, place, and price.

## Step 3: For every candidate, find the cheapest way in

This is where most value hides. Before you rank anything, check:

- A free tier, community ticket, or livestream.
- Student, startup, early-bird, or under-30 discounts.
- Volunteer, speaker, mentor, or press applications (usually free entry,
  often better access than a paid ticket).
- Travel grants, diversity scholarships, or sponsor-paid places.
- A smaller satellite event, side event, or afterparty of a big conference
  that is free and has the same people.

Write down the price you found and the source. Never invent a discount.

## Step 4: Score, do not eyeball

Call `score_opportunity` for every candidate that survives the basic filter
(right field, date not passed, not in the profile's "avoid" list). Give it:

- `payoff` 1-5 with a one-line reason you will repeat in the answer
  (5 = could directly bring money, funding, or a job; 1 = nice to know).
- `fit` 1-5 against the goals and interests.
- `fee` as found, `location` as a real place name, or `online=true`.
- `investor_presence` 0-3 (0 none, 1 some, 2 investors listed as
  attendees or judges, 3 dedicated investor event).
- `deadline` as YYYY-MM-DD for application-based items.

Run several `score_opportunity` calls in the same turn. The tool does the
distance, travel estimate, and budget math. Do not override its numbers; if
you think a number is wrong, say why next to it.

## Step 5: Verify before you recommend

The top items must pass the cross-check from the system prompt: date, place,
price, and deadline confirmed on the official page plus one other source.
What rests on one source gets `[unverified]`.

## Step 6: Deliver

One table, best score first, at most 10 rows:

| Score | What | When | Where | All-in cost | Cheapest way in | Why it pays off | Link |

"All-in cost" comes from the tool (fee plus travel estimate). "Why it pays
off" is one sentence tied to a goal from the profile.

Then two short lines:

- **Skipped:** how many and why, grouped ("9 skipped: 5 over budget, 3 past
  deadline, 1 wrong field").
- **Next action:** the single most time-sensitive step (an application
  deadline, an early-bird cutoff).

Ten or more items, or recurring value: save with `save_research`, title
"Opportunities <topic> <month year>".

## What you do not do

- No item without a real listing page you have read.
- No guessing prices, dates, or who attends. "Investors attend" needs a
  named investor, a judges list, or the organizer saying so.
- No collecting personal data about attendees. Public organizer and speaker
  names from the event page are fine; private contact details are not.
- No mass fetches against one site; a few targeted reads are enough.
