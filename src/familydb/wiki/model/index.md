# The pieces

The things FamilyDB keeps, and the people it keeps them for. This page is the map;
it names each piece and says what it is for. Each piece will get a page of its own
as this guide grows.

## Ideas, plans and things to do

These three are easy to confuse and kept apart on purpose.

- **An idea** is a possibility. There is one `ideas` table, and its *kind* (restaurant, outing, show, "someday") is open text, so a new kind needs no change to the software. Who an idea is for ("with the girls") is recorded, and a place's looked-up facts (address, hours, booking link, source pages) are cached beside it with when they were fetched. An idea is dropped rather than deleted, and each time it is done is an *outcome* with its own rating, so a restaurant can be done five times with five ratings.
- **A plan** is a commitment: an idea tied to an event on the Google Calendar. The calendar is read from Google, so an event added by hand is seen too, and a plan is brought in line with its event before it is acted on, so an event moved or deleted in Google is not undone.
- **A thing to do** is an obligation with a reminder. It may have no date at all ("one of these Saturday mornings") and be brought up when a matching window comes round and the calendar is free. It may repeat on a schedule or counted from when it was last done, in the family's own clock.

## What she remembers

Facts the family tells it about itself are kept as short memories, each about the
person it concerns. A *firm* one (a must) is always sent with every message that
bears on it; a guess only leans. Memory rides on the chat call that was needed
anyway, with no extra model call to remember or to retrieve. A parent can see all of
it on one page and forget any of it, for good. `docs/MEMORY.md` is the design.

## The family

The family list is who the bot talks to and who signs in. Each member has a name,
a role and a way in (Telegram, the page, or both), and each person signs in to the
page with their own password. There are three roles:

- **Admin**: everything a parent may do, plus settings, setting up and the family list.
- **Parent**: chat, change ideas, plans and things to do, browse the household's pages, and answer the kids' wishes.
- **Kid**: sign in, chat (within a daily number the family sets), keep her own wish lists, and tick off her own things to do.

What each role may do is one table (`familydb/roles.py`). [Security and
trust](/wiki/security) says how it is held.

## Wish lists

Each kid keeps her own lists, and the parents answer them. A present is kept from
every kid and from the grown-up it is for. `docs/WISHES.md` has the rules.

## Vera

Vera is the persona: the name, the character and the wording of everything said
unprompted. She changes how things are said, never what is done. The family can
rename her, add notes, rewrite her character or swap her for a shorter Vera or for
none, on the Personality page. `docs/PERSONAS.md` is the design.

## In this section

**Still to come:** one page each for ideas and places, plans and the calendar,
things to do and reminders, what she remembers, the family and roles, wish lists,
and Vera.

Deeper detail: `docs/DESIGN.md` section 7, `docs/MEMORY.md`, `docs/WISHES.md` and `docs/PERSONAS.md`.
