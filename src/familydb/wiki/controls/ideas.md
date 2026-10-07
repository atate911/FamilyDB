# Ideas

The Ideas page lists every [idea](/wiki/reference/glossary#idea) the family has mentioned wanting to try, with search, filters and a page for each one. A parent or admin adds, fixes, drops and rates ideas here, and asks for one to be looked up again.

## Who sees what

| Who | What they get |
|---|---|
| Admin, parent | Everything here, and all the forms |
| Kid | Plain cards (kind, title, where or when), with no search, filters, tabs or radar. An idea's page shows a one-line lookup status, no failure reason and no buttons. The Restaurants tab is not linked for them, but opens if they type the address |
| Anyone on the shared password | Everything. The forms that record a person (add an idea, record how it went, plan it, add a plan, save a thought) ask who is acting |

Who may change what is in [Roles and permissions](/wiki/model/family-and-roles#roles-and-permissions). Presents are kept from kids and from the grown-up they are for ([Presents](/wiki/model/ideas-and-places#presents)); a parent changes who a present is hidden from with the **Hidden from** boxes on the edit form.

## What is on the page

- **The list.** Top to bottom: **Add an idea**, the tabs **All ideas** and **Restaurants** (counts leave out dropped ideas), **Search** and **Narrow by kind, person or status**, the cards, **Save a thought for later**, and the radar. A card shows the kind, title, who it is for, how far away it is (or "Not looked up yet"), and tags such as Planned and Dropped. Cards run newest first, or best match first while you search. At most 200 show, and the page says when it cuts the list.
- **Search and filters.** Search matches whole words, any of them, in the title, description, tags and the Where box. **For** lists what has been typed in the "who it's for" boxes, and an idea matches when one entry is exactly that, ignoring capitals. Kind, For and Status apply together. Status starts at "Any but dropped"; a dropped idea shows only when you choose Dropped.
- **Save a thought for later.** It sends your words to the assistant, which is a model call paid for like any other.
- **One idea's page.** The kind and number (`#57` is how you name it in chat), title, status and who suggested it, the description, and, folded, the **original thought** it came from. Below, when there is something to show: **On the calendar**, **The place** and **How it went**. Beside them: **At a glance**, **Looking it up** and **Plan it**.
- **The Restaurants tab.** Every restaurant idea that is not dropped, newest first, up to 200, with no search or filters. A card shows the cost, today's opening hours, a summary, the drive, who it is for, the rating, and links to the idea, site, booking and a map.
- **The radar.** Home is in the middle and north is up. Rings mark 15 minutes, 30 minutes, 1 hour, 2 hours and 3 hours, not evenly spaced. Each idea on the list with a position is a dot. Drive times are estimates, not routes ([Places](/wiki/model/ideas-and-places#places)). The radar needs a home position, appears only when an idea is more than 15 minutes away, and follows your filters.

## Add an idea

Choose **Add an idea**, give a title and a kind (the rest is folded under "Everything else"), and choose **Add it**. If a very similar title is on the list, nothing is added and you land on that idea.

## Change an idea

Open it, choose **Edit**, then **Save changes**. Changing the place does not look it up again.

## Drop an idea, or bring it back

Open it and choose **Drop it** or **Bring it back**. Dropping sets the status to Dropped: the idea leaves the list, suggestions and lookups, and keeps its outcomes and place. Bringing it back sets it to "An idea". The page cannot delete an idea.

## Record how it went

Open the idea, open **Record how it went**, set the day (not in the future), a score out of ten and whether the family would go again, and choose **Record it**. That marks the idea done, counts the visit and updates its average rating. An idea can have many outcomes. Recording how it went on a dropped idea marks it Done again.

## Ask for a lookup

Open the idea and choose **Look it up now** (**Look it up again** once it was looked up). It runs on the next lookups job run, every 2 minutes by default ([Lookups](/wiki/controls/settings/lookups)), and the button is gone until it has. By default other ideas wait for the evening and are looked up together. A lookup counts toward [the daily limit](/wiki/controls/settings/spending). With lookups off, the buttons are hidden and the page says so. Details older than the stale setting on Lookups are marked "Details may be out of date".

Parents and admins see why a lookup failed under **Looking it up**. Admins also get **How it was looked up**, the calls behind it.

## Rules for this page

- If someone changed the idea while you had the edit form open, FamilyDB refuses your save and reloads the form with their version. A double click or a resent form does its work once while FamilyDB runs.
- A number you set cannot be emptied from the page. Cost, the two durations and the booking lead time can be changed, but an empty box means "leave it". Text boxes can be emptied.
- An end date already past is refused.

## The same from chat or the server

Every form here runs the same tool the assistant runs, so you can ask for any of this in chat. `/lookup` on [Telegram](/wiki/controls/telegram) asks for everything waiting. On the server, `familydb enrich --idea <number>` redoes one (run as in [The command line](/wiki/operations/command-line#how-to-run-it)).

How ideas, places and lookups work is on [Ideas and places](/wiki/model/ideas-and-places).
