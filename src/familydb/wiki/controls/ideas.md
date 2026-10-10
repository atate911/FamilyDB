# Eat and Do

Two destinations read the family's saved [ideas](/wiki/reference/glossary#idea). **Eat** answers "Where should we eat?" from the restaurants, and **Do** answers "What could we do?" from everything else. Each opens on its answer, ranked by code with no model call, and narrows with chips. A parent or admin adds, fixes, drops and rates ideas on a place's own page, and asks for one to be looked up again. The box on either page is about it: "anything cheaper?" sent from Eat is a question about restaurants.

## Who sees what

| Who | What they get |
|---|---|
| Admin, parent | Everything here, and all the forms |
| Kid | The same rows without the cost, the people's marks, the search or the map. A place's page shows no cost, no number, a one-line lookup status and no buttons. Eat is not in her row, but opens if she follows a link to it |
| Anyone on the shared password | Everything. The forms that record a person (add an idea, record how it went, plan it) ask who is acting |

Who may change what is in [Roles and permissions](/wiki/model/family-and-roles#roles-and-permissions). Presents are kept from kids and from the grown-up they are for ([Presents](/wiki/model/ideas-and-places#presents)); a parent changes who a present is hidden from with the **Hidden from** boxes on the edit form.

## Eat

The line under the question is the pick for the next meal (lunch from 11, tonight from 2 pm), chosen by code from what is open for that meal and how far it is. Then every restaurant that is not dropped, the pick on top, with one fact line each: open till when, the drive, the cost band, who suggested it, been or not. A kid is told nothing of cost.

The chips narrow the list: **Open today**, **Close** (about 20 minutes' drive or less), **New to us**, **Just us**, **With the kids**, and each person, for what is theirs. **Add a place by hand** is at the foot, for whoever may change things.

## Do

The line under the question says what fits the next free stretch, and that idea leads the list. Then everything that is not a restaurant, newest first; an idea nobody has touched for six weeks is drawn faded, for a grown-up, so the pile shows what is going quiet. The chips are the kinds in the pile (Outing, Activity, Day trip, Trip, Show, Event, Seasonal, Stay in), **With the kids**, **Just us**, **Free**, **Close**, each person, and **Dropped**, which is the only way a dropped idea shows. **Search** matches whole words, any of them, in the title, description, tags and the Where box; chips and search apply together. At most 200 show, and the page says when it cuts the list.

**The map** sits under the list for grown-ups: home in the middle, north up, rings at 15 minutes, 30 minutes, 1 hour, 2 hours and 3 hours, not evenly spaced, and each idea with a position a dot. Drive times are estimates, not routes ([Places](/wiki/model/ideas-and-places#places)). It needs a home position, appears only when an idea is more than 15 minutes away, and follows the chips. **Add an idea by hand** is at the foot.

## A place's page

Open a row for the place's own page, in the order a person decides in:

- The kind, the number (`#57` is how you name it in chat; a kid sees no number), the title, and its state in words (An idea, Planned for Saturday, Done twice, Dropped).
- The facts that exist, and only those: open today, from home, the cost (not for a kid), booking, who it is for, ages, how long, indoor or out, the weather, when it is on, how it has gone so far.
- Where it came from: who said it, when, in their words, or who added it by hand and when.
- What the assistant found, marked as hers and dated: her summary, the address and a map link, the site, booking and phone, the opening hours folded, where she read it, and when she checked. Parents and admins see why a lookup failed; admins get **How it was looked up**, the calls behind it.
- What is planned, each a link to the plan, and how it went.
- The box, about this place, with three quick sentences under it that fill the box ("Plan it for this weekend", "Is it good for the kids?", "What else is near it?"). Nothing is sent until you press Send.
- **Plan it**, **Drop it** (or **Bring it back**), **Look it up now**, **Record how it went by hand**, and **Edit by hand**, last.

## Add an idea

Choose **Add an idea by hand** on Do (**Add a place by hand** on Eat), give a title and a kind (the rest is folded under "Everything else"), and choose **Add it**. If a very similar title is on the list, nothing is added and you land on that idea. Telling the assistant is the usual way: "save Kenji's Ramen on Division, Jess says get the spicy miso".

## Change an idea

Open it, choose **Edit by hand**, then **Save changes**. Changing the place does not look it up again.

## Drop an idea, or bring it back

Open it and choose **Drop it** or **Bring it back**. Dropping sets the status to Dropped: the idea leaves the list, the picks, suggestions and lookups, and keeps its outcomes and place. Bringing it back sets it to "An idea". The page cannot delete an idea.

## Plan it

Open **Plan it** on the place's page, give when (or all day) and where, and save. The plan links to the place and the idea becomes Planned; it shows on [Week](/wiki/controls/plans-and-tasks) and has a page of its own.

## Record how it went

Open the place, open **Record how it went by hand**, set the day (not in the future), a score out of ten and whether the family would go again, and choose **Record it**. That marks the idea done, counts the visit and updates its average rating. An idea can have many outcomes. The faces on Now and [Did](/wiki/controls/plans-and-tasks#did) record the same thing with one tap. Recording how it went on a dropped idea marks it Done again.

## Ask for a lookup

Open the place and choose **Look it up now** (**Look it up again** once it was looked up). It runs on the next lookups job run, every 2 minutes by default ([Lookups](/wiki/controls/settings/lookups)), and the button is gone until it has. By default other ideas wait for the evening and are looked up together. A lookup counts toward [the daily limit](/wiki/controls/settings/spending). With lookups off, the buttons are hidden and the page says so. Details older than the stale setting on Lookups are marked "may be out of date".

## Rules for these pages

- If someone changed the idea while you had the edit form open, FamilyDB refuses your save and reloads the form with their version. A double click or a resent form does its work once while FamilyDB runs.
- A number you set cannot be emptied from the page. Cost, the two durations and the booking lead time can be changed, but an empty box means "leave it". Text boxes can be emptied.
- An end date already past is refused.

## The same from chat or the server

Every form here runs the same tool the assistant runs, so you can ask for any of this in chat, from the box on any page. `/lookup` on [Telegram](/wiki/controls/telegram) asks for everything waiting. On the server, `familydb enrich --idea <number>` redoes one (run as in [The command line](/wiki/operations/command-line#how-to-run-it)).

How ideas, places and lookups work is on [Ideas and places](/wiki/model/ideas-and-places).
