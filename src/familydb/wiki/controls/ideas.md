# Ideas

The Ideas page lists every [idea](/wiki/reference/glossary#idea) the family has mentioned wanting to try, with search and filters and a page for each one. It is where a parent or admin adds, fixes, drops and rates ideas, and asks for one to be looked up again.

## Who sees what

| Who | What they get |
|---|---|
| Admin, parent | Everything here, and all the forms |
| Kid | Plain cards (kind, title, where or when), with no search, filters, tabs or radar. An idea's page shows a one-line lookup status, no failure reason and no buttons. The Restaurants page is not linked for them, but opens if they type the address |
| Anyone on the shared password | Everything. The forms that record a person (add an idea, record how it went, plan it, add a plan, save a thought) ask who is acting |

Who may change what is in [the roles table](/wiki/security#who-may-do-what). A present (an idea of kind `gift`) is hidden from every kid and from the grown-up it is for, in the list, the counts, the radar and by direct link. A parent can hide it from other grown-ups too, or change who it is hidden from, with the **Hidden from** boxes on the edit form. Under the shared password nothing is hidden.

## The list

Top to bottom: **Add an idea**, the tabs **All ideas** and **Restaurants** (with counts that leave out dropped ideas), **Search** and **Narrow by kind, person or status**, the cards, **Save a thought for later**, and the radar. A card shows the kind, title, who it is for, how far away it is (or "Not looked up yet"), and tags such as Planned and Dropped. Cards run newest first, or best match first while you search. **Save a thought for later** sends your words to the assistant, a message to a model that is paid for like any other.

- Status is **An idea**, **Planned** (it has a plan), **Done** (how it went was recorded) or **Dropped**. Kinds are free text.
- Search matches whole words, any of them, in the title, description, tags and the Where box.
- **For** lists what has been typed in the "who it's for" boxes. An idea matches when one entry is exactly that, ignoring capitals.
- Kind, For and Status apply together. Status starts at "Any but dropped"; a dropped idea shows only when you choose Dropped.
- At most 200 ideas show, and the page says when it cuts the list.

## One idea's page

The kind and number (`#57` is how you name it in chat), title, status and who suggested it, the description, and, folded, the **original thought** it came from. Below, when there is something to show: **On the calendar**, **The place** and **How it went**. Beside them: **At a glance**, **Looking it up** and **Plan it**.

## What you can do

1. **Add an idea.** Choose **Add an idea**, give a title and a kind (the rest is folded under "Everything else"), and choose **Add it**. If a very similar title is on the list, nothing is added and you land on that idea.
2. **Change an idea.** Open it, choose **Edit**, then **Save changes**. Changing the place does not look it up again.
3. **Drop it, or bring it back.** Open it and choose **Drop it** or **Bring it back**.
4. **Record how it went.** Open it, open **Record how it went**, set the day (not in the future), a score out of ten and whether the family would go again, and choose **Record it**. That marks the idea done, counts the visit and updates its average rating. An idea can have many outcomes.
5. **Ask for a lookup.** Open it and choose **Look it up now** (**Look it up again** once it was looked up). It runs on the next check, within a few minutes, and the button is gone until it has.

## The rules that matter

**Nothing is deleted.** Dropping sets the status to Dropped. The idea leaves the list, suggestions and lookups, and keeps its outcomes and place. Bringing it back sets it to "An idea". **Recording how it went on a dropped idea marks it Done again.** The page cannot delete an idea.

**A stale form is refused, not merged.** If someone changed the idea while you had the edit form open, your save is refused and the form reloads with their version. A double click or a resent form does its work once while FamilyDB runs.

**A number you set cannot be emptied from the page.** Cost, the two durations and the booking lead time can be changed, but an empty box means "leave it". Text boxes can be emptied. An end date already past is refused.

**A lookup costs a little.** It is a separate, bounded model turn with web search, at most three searches per idea, counted toward [the daily limit](/wiki/controls/settings/spending). By default ideas wait for the evening and are looked up together. A gift idea with no place, or a home idea with no place or link, is skipped with no model call. Details older than the setting on [Lookups](/wiki/controls/settings/lookups) are marked "Details may be out of date". With lookups off, the buttons are hidden and the Ideas page says so.

## The Restaurants tab

Every restaurant idea that is not dropped, newest first, up to 200, with no search or filters. A card shows the cost, today's opening hours, a summary, the drive, who it is for, the rating, and links to the idea, site, booking and a map.

## The radar

Home is in the middle and north is up. Rings mark 15 minutes, 30 minutes, 1 hour, 2 hours and 3 hours, not evenly spaced. Each idea on the list with a position on the map is a dot. **The drive times are estimates**, not routes: straight-line distance times a detour factor, at an average speed, both set on [General](/wiki/controls/settings/general). The radar needs a home position, appears only when an idea is more than 15 minutes away, and follows your filters.

## Telegram, chat and admins

The forms run the tools the assistant runs (`add_idea`, `update_idea`, `record_outcome`, `look_up_now`), so you can ask for any of this in chat. `/lookup` on [Telegram](/wiki/controls/telegram) asks for everything waiting.

Parents and admins see why a lookup failed under **Looking it up**; admins also get **How it was looked up**, the calls behind it. Lookups are switched on and timed under [Lookups](/wiki/controls/settings/lookups). On the server, `familydb enrich --idea <number>` redoes one ([command line](/wiki/controls/command-line)).

Developer docs: `src/familydb/web/routes.py` (`ideas`, `idea`, `restaurants`), `src/familydb/web/edits.py`, `src/familydb/tools/ideas.py`, `src/familydb/presents.py`, and `docs/DESIGN.md`, "Enrichment: filling in the details".
