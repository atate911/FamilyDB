# Ideas

The Ideas page lists every [idea](/wiki/reference/glossary#idea) the family has mentioned wanting to try, with search and filters and a page for each one. It is where a parent or admin adds, fixes, drops and rates ideas, and asks for one to be looked up again.

## Who sees what

| Who | What they get |
|---|---|
| Admin, parent | Everything here, and all the forms |
| Kid | Plain cards (kind, title, where or when). No search, filters, count, tabs or radar, and nothing about how an idea was looked up. A kid can open an idea but has no buttons on it |
| Anyone on the shared password | Everything, and each form asks who is acting |

Who may change what is in [the roles table](/wiki/security#who-may-do-what). A present (an idea of kind `gift`) is hidden from every kid and from the grown-up it is for, in the list, the counts, the radar and by direct link. Under the shared password nothing is hidden.

## The list

From the top: **Add an idea**; the tabs **All ideas** and **Restaurants**, each with a count (dropped ideas are not counted); **Search** and **Narrow by kind, person or status**; the cards; **Save a thought for later**; and the radar.

A card shows the kind, title, who it is for, how far away it is (or "Not looked up yet"), and tags for Planned, the date it is on, when it was last done, and Dropped. Cards run newest first, or best match first while you search. **Save a thought for later** sends your words to the assistant, which organizes them in the chat. That is a message to a model, so it is paid for like any other.

- Search matches **any** of your words in the title, description, tags and place.
- Kind, For and Status apply together. **For** must match one of the names in an idea's "who it's for" box exactly, ignoring capitals.
- Status starts at "Any but dropped". A dropped idea shows only when you choose Dropped.
- At most 200 ideas show, and the page says when it cuts the list.

## One idea's page

The kind and number (`#57` is how you name it in chat), title, status and who suggested it, then the description and, folded, the **original thought** it came from. Below: **On the calendar** (its plans), **The place** (address, phone, links, prices, opening hours, sources), **How it went**, and the forms. Beside them: **At a glance** and **Looking it up**.

## What you can do

1. **Add an idea.** Choose **Add an idea**, give a title and a kind (the rest is folded under "Everything else"), and choose **Add it**. If a very similar title is on the list, nothing is added and you land on that idea.
2. **Change an idea.** Open it, choose **Edit**, then **Save changes**. Changing the place does not look it up again.
3. **Drop it, or bring it back.** Open it and choose **Drop it** or **Bring it back**.
4. **Record how it went.** Open it, open **Record how it went**, set the day (not in the future), a score out of ten and whether the family would go again, and choose **Record it**. That marks the idea done, counts the visit and updates its average rating. An idea can have many outcomes.
5. **Ask for a lookup.** Open it and choose **Look it up now** (**Look it up again** once it was looked up). It runs on the next check, within a few minutes, and the button is gone until it has.

## The rules that matter

**Nothing is deleted.** Dropping sets the status to Dropped. The idea leaves the list, suggestions and lookups, and keeps its outcomes and place. Bringing it back sets it to "An idea". The page cannot delete one.

**A stale form is refused, not merged.** The edit form carries the idea as it was when drawn. If someone changed it meanwhile, your save is refused and the form reloads with their version.

**A number you set cannot be emptied from the page.** Cost, the two durations and the booking lead time can be changed, but an empty box means "leave it". Text boxes can be emptied. An end date already past is refused.

**Forms work once.** A double click or a resent form does its work once.

**A lookup costs a little.** It is a separate, bounded model turn with web search, at most three searches per idea, counted toward [the daily limit](/wiki/controls/settings/spending). By default ideas wait for the evening and are looked up together. A gift idea with no place, or a home idea with no place or link, is skipped with no model call. Details older than the setting on [Lookups](/wiki/controls/settings/lookups) are marked "Details may be out of date". With lookups off, the buttons are hidden and the page says so.

## The Restaurants tab

Every restaurant idea, newest first, with no search or filters. A card shows the cost, today's opening hours, a summary, the drive, who it is for, the rating, and links to the idea, the restaurant's site, booking and a map.

## The radar

Home is in the middle, north is up, and rings mark 15 minutes, 30 minutes, 1 hour, 2 hours and 3 hours. Each idea on the list with a looked-up place is a dot.

**The drive times are estimates**, not routes: straight-line distance times a detour factor, at an average speed, both set on [General](/wiki/controls/settings/general). The radar needs a home position, appears only when an idea is more than 15 minutes away, follows your filters, and says how many ideas have no drive time yet.

## Telegram and chat

The forms run the tools the assistant runs (`add_idea`, `update_idea`, `record_outcome`, `look_up_now`), so you can ask for any of this in chat. `/lookup` on [Telegram](/wiki/controls/telegram) asks for everything waiting.

## For admins

Parents and admins see why a lookup failed in brackets under **Looking it up**; admins also get **How it was looked up**, the model and tool calls behind it. Turn lookups on, and choose when they run, under [Lookups](/wiki/controls/settings/lookups). On the server, `familydb enrich --idea <number>` redoes one lookup (see [the command line](/wiki/controls/command-line)).

Developer docs: `src/familydb/web/routes.py` (`ideas`, `idea`, `restaurants`), `src/familydb/web/edits.py`, `src/familydb/tools/ideas.py`, `src/familydb/presents.py`, and `docs/DESIGN.md`, "Enrichment: filling in the details".
