# Target Audience

Template. Copy this file into your notes folder (NOTES_DIR) and fill in your
own criteria. The agent reads it before every lead research run and follows
it. The path is set in the .env under `LEADS_TARGET_NOTE`.

The point: whatever is in here, nobody has to change in code and nobody has to
write into every task again. You edit the note, and the next research run
follows it.

## Include

Who are we looking for? As specific as possible, using the industry terms these
providers use to describe themselves. The agent uses exactly these terms as
search queries.

- Example: <industry term> with <service> in <region>
- Example: <association name>, <chamber of commerce>, <industry directory> as an aggregate source
-

## Exclude

Words that lead to immediate exclusion when they appear in the name, without
opening the page. This saves most fetches. Feel free to be strict here.

- Example: <word>, <word>, <word>
-

## Signals on the page

What tells you, when reading the website, whether it fits?

**For:** <service>, <audience>, <technical term>
**Against:** <service that doesn't fit>, <wrong age group>, <wrong region>

## Edge cases

Cases you want to decide yourself. The agent does not put them on the list
but marks them as edge cases.

-

## Open suggestions

Record here what the agent suggested and what you still want to review. The
agent does not write here itself; it may only create new notes, not edit
existing ones.

-
