# The interface: map and architecture

The skeleton every screen is built on, for the web page on a phone, a big screen and a kitchen tablet. Second draft, October 2026, after the concept work in `CONCEPT.md`, three alternative paradigms weighed against it (section 12), and the family's answers to the questions that decide between them. Where this and the concept disagree, this document wins.

**Where it stands (October 2026):** the web page is built on this skeleton: Now (section 3) with its first day; What about and the eight destinations, a kid's four (sections 4 and 9); every item of section 2's map, a place, a plan, a day, a kid, a list, a reminder, a happening and a memory (section 5); the box with its receipts, her reply over the page and search in the box (sections 3 and 6); her picks made ahead by an hourly job; the phone and big-screen frames, Vera's column carrying the thread's last lines; and the kitchen tablet's board with its faces (section 8). The API of section 11 is built on the same answer functions: every page as data (`/api/<path>`), the box (`/api/say`), every form (`/api/act`) and search (`/api/find`). There is no native app, by the family's decision (section 8, On a phone): the installed page is the phone app. Also built: questions code can answer, answered by code in plain words on every channel (section 6, point 5); a reply pinned to a shelf of the person's own, beside the box and atop Chat (section 8); I'll handle it on a to-do that is everyone's; and who put each thing on a list (section 4). Not built: the plan taking shape on a plan's page (section 5), a kid's additions to a list for a parent to keep or drop (the family has not decided what a kid may do with the lists), and the second pass's other open decisions (section 12). `docs/STYLE.md` records the look; the guide (`/wiki`) says how to use each page.

It is organized from the outside in: what the app is, the map, each level of the map, the Vera layer over all of it, how a person moves, the two platforms, the people, the awkward states, and what the server has to provide. Section 12 records the second pass: what was weighed, what changed, and what still needs a decision.

## 1. What the interface is

Three things, and a person always knows which they want:

- **Vera to tell.** The box is the first thing on every first screen, because an instruction is the most common reason to open the app: "add this restaurant", "remind me Tuesday", "tell Maya yes". It comes back as a one-line receipt with undo.
- **Now, arranged by Vera.** Under the box, her picks for right now and the next day or two, and anything waiting on you. She arranges this part freely each time. It is the answer to the family's daily question, which is improvisational: "what should we do, now or soon?"
- **Destinations to look at.** A short row of screens, each named for a want ("Where should we eat?"), each one tap away, each opening on its answer with nothing to set first. Ranked by code, instant and free. Vera is there too, as a supporting assistant, through the same box scoped to the screen.

Four rules hold everything below:

1. **The box first, always.** On every first screen, on every device, before anything else.
2. **The middle is hers; the edges are fixed.** Vera may rearrange what is between the box and the destination row every time the screen opens. The box and the row never move, so the hand learns the screen even though its content changes.
3. **Names are wants, not nouns.** A destination says what you'd get, not what table it reads.
4. **Three gestures.** Tap to open, chips to narrow, back to go up. The box is the fourth thing, the same everywhere.

## 2. The map

```
FIRST     Now                                        /
          the box · context line · her questions · her picks · today's line
          the destination row

LEVEL 1   Destinations                               path
          Where should we eat?        (Eat out)      /eat
          What could we do?           (Things)       /do
          This week                   (Calendar)     /week
          The kids                                   /kids
          Happening soon                             /soon
          Lists                                      /lists
          What we did                                /did
          (What about… is Now itself, at /about when opened from elsewhere)

LEVEL 2   Items
          a place        /place/57         a kid        /kids/maya
          a plan         /plan/12          a list       /lists/shopping
          a day          /week/2026-10-17  a reminder   /reminder/88
          a happening    /soon/301         a memory     /did/12

VERA      the box (every screen) → her reply (over the screen) → the thread (behind the reply)
          her questions (Now, and in the destination they belong to)
          her notes (on items)
          receipts (under the box, after an instruction)

AVATAR    You · The family · Settings · Status · Guide        /you /family /settings /status /wiki
```

The paths are the deep links. Telegram, push notifications, the tablet and the page added to a phone's home screen all land on the same ones. Now is personal: each person's Now has their questions and picks weighted to their context, read from their own thread and the family's shared things.

## 3. Now

Now is the first screen. It is not a menu and not a dashboard: it is the box, then whatever Vera thinks matters for this person at this moment, then the way to everything else.

```
┌──────────────────────────────────────┐
│ FamilyDB                         (S) │
│ ┌──────────────────────────────────┐ │
│ │ Tell Vera…                       │ │  the box, first, always
│ └──────────────────────────────────┘ │
│ Friday 5 pm · dry through Sunday     │  one line of context
│                                      │
│ Maya asked for the trampoline park.  │  her questions, when any
│ Saturday morning is free.            │
│ Plan it · Later                      │
│                                      │
│ What about…         chosen at 4 pm   │  her picks for now and soon
│ ┌───────────────┐ ┌───────────────┐  │
│ │ TONIGHT       │ │ SAT MORNING   │  │
│ │ Kenji's Ramen │ │ Sky High      │  │
│ │ Open till 9,  │ │ Maya's pitch, │  │
│ │ 12 min.       │ │ and it's dry. │  │
│ └───────────────┘ └───────────────┘  │
│ ┌───────────────┐ ┌───────────────┐  │
│ │ SUNDAY        │ │ SOMETHING NEW │  │
│ │ Powell Butte  │ │ Pumpkin       │  │
│ │ kites         │ │ carving, free │  │
│ └───────────────┘ └───────────────┘  │
│          Different ones              │
│                                      │
│ Swim lesson 4:30 · Night Market Sat  │  today and tomorrow, one line
├──────────────────────────────────────┤
│ Eat · Do · Week · Kids · Lists · Did │  the destination row, fixed
└──────────────────────────────────────┘
```

**Fixed:** the box at the top, the destination row at the bottom, and the first line under the box, which says the time and the one fact that shapes the picks.

**Hers:** everything between. She decides what leads. An hour before a set plan, the plan leads with its leave-by time. At the store, the shopping list leads. On Friday afternoon, the weekend picks lead. On a quiet Tuesday morning, the screen is the box, the context line, "Nothing needs you", and the row. She may show six picks or two or none. The one promise is that anything waiting on this person is never pushed below the picks.

**The picks** are the What about set described in section 4: one of each kind for this moment, each with a reason, made ahead and refreshed on open when stale (more than a few hours old and the budget allows). "Different ones" is a call made on purpose. Tapping a pick opens the thing with Plan it ready; swiping it away is "not now".

**Her questions** are the only interruption: a kid's pitch, a plan to set, how an outing went. Each with its origin and its buttons. The same ones reach Telegram.

**Today's line** is the coordination that fits in one line. The week is one tap away in the row.

**Search** is inside the box: typing a name shows matches above the keyboard before anything is sent.

**On a big screen** the destination row becomes the left rail, Now fills the center, and Vera's reply and thread are the right column. **On the kitchen tablet** Now becomes the board (section 8). **A kid's Now** is in section 9.

## 4. The destinations

### The shared skeleton

Every destination is built in this order, so one learned is all learned:

1. **Title:** the question it answers.
2. **Summary line:** the one thing to know. "Kenji's tonight: open till 9, 12 min." "Free Saturday afternoon." "Nothing waiting on you."
3. **Chips** to narrow, always in the same place. A person's name is a chip on every destination that has people.
4. **The answer**, opened on its best default.
5. **The box**, scoped to this screen, with a chip naming the scope that can be dismissed.

Nothing else appears on a destination. Her picks and her finds are marked as hers; everything else is the family's own.

### Where should we eat? (`/eat`)

- **Opens on:** a top pick for the next meal, then every saved restaurant.
- **The pick:** chosen by code: open at the meal time, not done recently, how it was rated, drive time, weather for a patio. Its line says why: "Open till 9, 12 min, you haven't been."
- **Chips:** Open now · Close · Just us · With the kids · New · Cuisines that exist in the pile · Each person.
- **Each row:** name, cuisine, one fact that decides (open till, how far, cost band), who suggested it, done before or not.
- **Empty:** "No restaurants yet. Tell Vera one you've heard about."
- **Kid:** the same list without cost bands or "just us".

### What could we do? (`/do`)

- **Opens on:** the saved pile, the best fits for the next free stretch on top, then everything newest first. Restaurants are not here; they have their own door.
- **Chips:** Outing · Day trip · Stay in · With the kids · Just us · Free · Close · Each person · Dropped.
- **Each row:** name, kind, where or how far, who said it, a mark if it is closing soon or fading.
- **Fading:** untouched things go paler after six weeks; at three months the row asks "still want this?" with keep and let go. Rested things are under the Dropped chip, never gone.
- **Empty:** "Nothing saved yet. When someone says 'we should try…', it lands here."
- **Kid:** her things and the family's, plain rows, nothing paler, no Dropped.

### What about… (`/about`)

The picks on Now, as a destination of their own for a big screen, a deep link, or "What now?" asked from anywhere. The one place in the app where Vera chooses: six to eight tiles, one of each kind, picked for this moment across the family's own material and her finds, each with a reason.

- **Opens on:** the current set, with a header saying what drove it ("Dry Saturday, free from noon. Maya's been asking.") and when it was chosen.
- **A tile:** kind · when it fits · name · one sentence of why. Tap opens the thing with Plan it ready. Swipe away is "not now". Hold offers "not this" and "not for me".
- **The slots** are decided by code for this moment: tonight, the weekend, something new, with the kids, just the parents, a day trip, something in, from a kid's wish. The model fills each from the dossier; code verifies every pick is real before it shows.
- **Made ahead,** then refreshed on open when stale: each morning, Thursday evening for the weekend, when the context moves (forecast, a plan set, a wish arrives), and on opening Now when the set is more than a few hours old and the month's choosing budget has room. "Different ones" and "What now?" are deliberate calls and say so.
- **Empty:** on a new install, "I don't know you yet. Tell me a few places you like and I'll have ideas by tomorrow." If she can't answer, the last set stays with its date.
- **Kid:** her own set, weighted to her wishes and age, nothing about who is away.

### This week (`/week`)

- **Opens on:** today, the week around it, free time drawn as space, the forecast on each day, reminders as small marks on their day.
- **On your plate:** a strip that stays on screen whatever week is showing. Everything with no date yet ("some Saturday morning", "when it rains", "next free moment") and anything overdue, each with its owner or "I'll handle it". Nothing dateless can be lost by scrolling.
- **Pencil:** a plan taking shape appears in pencil on the day being considered, once a day is being considered. At most one of Vera's own suggestions sits on a free stretch, and only on weekends; tapping a free stretch asks for more.
- **Chips:** Each person · Month · Past.
- **A day** (`/week/<date>`): everything on it, the free stretches, and after the day, how it went.
- **Empty:** without a calendar connected, the plans made here; a line says so and offers the connection to an admin.
- **Kid:** her days and the family's, in words ("after school"), no pencil, no plate.

### The kids (`/kids`)

- **Opens on:** each kid as a section, unanswered requests first.
- **A request:** what she asked, when, in her words, with a scale in words rather than money where it helps ("needs planning", "could do at home"). Buttons: Yes · Not yet · Let's talk, and a note field that appears only on Not yet.
- **Her lists:** every day, birthday, holiday, in her order, each item marked wanted, being considered, done. Being considered never looks like a promise. Her pitches for outings show their state: pitched, shaped, waiting on a parent, planned.
- **Chips:** each kid, and Unanswered.
- **Hidden:** no kid sees this screen. Only parents and admins may `decide`.
- **With no kids on the list, the tile is not shown.** With one, it carries her name.

### Happening soon (`/soon`)

- **Opens on:** dated possibilities by date: what she found near home, the family's own things with a closing date, her weekend picks. "Vera found" is marked on hers.
- **Chips:** This weekend · Free · With the kids · Each source.
- **Each row:** name, date, how far, cost, where it came from. Yes puts it in pencil on the day; Not this one teaches her.
- **Finds fade out** the day after their date, kept only if someone said yes.
- **Empty:** "Nothing found yet" with, for admins, the settings that turn finding on.
- **Kid:** the same, without sources.

### Lists (`/lists`)

- **Opens on:** the list in use (shopping by default), big targets, ticks that need no conversation.
- **Other lists** are chips: Costco, a packing list that belongs to a plan, anything created by naming it ("add sunscreen to the camping list" makes the list).
- **Behind each item:** who asked, the photo of the exact thing if there was one, which plan it belongs to.
- **A kid's additions** arrive with her face on them for a parent to keep or drop.
- **Empty:** "Nothing on the list. Tell Vera 'we're out of milk'."

### What we did (`/did`)

- **Opens on:** recent outings, newest first: what, when, who went, the face each gave it, a photo if one was added.
- **Each memory** offers "Again?", which puts the place back among the things to do, and "What made it good?", a few chips (early start, a friend came, short, cheap) that become what she remembers.
- **Chips:** Loved · Each person · This time last year · Favorites.
- **Rating** happens here, on Telegram, and on Home as her question the morning after. One of those, never all three nagging.
- **Kid:** what she went to, with her own face on it.

## 5. Items

### The shared skeleton

Every item page reads in this order:

1. **Name and kind**, and its state in words ("An idea", "Could do Saturday", "Planned for Saturday 10 am", "Last Saturday").
2. **The facts that decide:** open now, how far, cost, booked, who's coming. Only the ones that exist.
3. **Where it came from:** who said it, when, their exact words, the photo or voice note if there was one.
4. **What Vera found,** marked as hers and dated: "checked this morning" or "saved in March".
5. **What's planned or how it went.**
6. **The box, scoped to this thing,** with two or three quick sentences as chips ("Plan it for Friday", "Good for the kids?", "Drop it").
7. **Edit by hand**, a quiet link, last.

### The item types

| Item | Reached from | What is special about it |
|---|---|---|
| **A place** | Eat out, Things to do, What about, search, a receipt | Hours, drive, cost, booking, kid-friendly, map. Plan it. |
| **A plan** | This week, her questions, What about, a place | Two states on one page: taking shape (dashed open questions, Set the plan) and set (leave-by, who, what to bring, Plan B, one open chair). Sealed, it shows a countdown and what to wear until the day. After the day it becomes a memory. Dissolves at its decide-by if never set, and its ideas go back. |
| **A day** | This week | Everything on it, free stretches, pencil, and afterwards the memories. |
| **A kid** | The kids | Her requests, her lists, her pitches, and for a parent her thread to read along. An admin sees the role and password forms here too. |
| **A list** | Lists | The checklist itself is the page. |
| **A reminder** | This week, On your plate, a receipt | When or on what condition, owner, repeats, delivery rules in words. |
| **A happening** | Happening soon | Date, source, the original listing, Yes in pencil. |
| **A memory** | What we did, a day | Faces, photo, what made it good, Again?. |

## 6. The Vera layer

Vera has no tile. She is the box, her reply, her questions, her notes, and her receipts.

**The box** is in the same place on every screen and always works. On Home it is general. On a destination or an item it is scoped, and a chip says so ("about: Eat out", "about: Kenji's"). Dismissing the chip makes it general. It takes typing, the mic, and a photo. A photo of a flyer comes back as its event, deadline and thing to bring, each accepted with a tap.

**Her reply** rises over the screen you are on (a sheet on a phone, the right column on a big screen). The screen underneath does not change, so nobody loses their place. The reply answers the question completely, in her words, in rich pieces where they fit (the days of the week as rows, three picks with reasons, the matching places). It ends with at most one pointer, which is a tap that navigates. "Earlier" opens the thread. Dismissing returns to where you were.

**Her answering contract:**

1. She answers from the family's database, and from the world when the question needs it, and says which.
2. The answer is complete. "What's this week?" gets the week, in sentences. "What did we save for date night?" gets the places. "Did Alex do the library thing?" gets yes or no and when. Never "look under Lists".
3. One pointer at most, and only when a screen adds what the reply can't hold.
4. When she can't fully know, she still answers with what she has and says what would make it better.
5. Code and model both speak as her. "What's this week?" is answered by code, free and instant, the way the Telegram commands already are. The fuzzy tail goes to the model with the database in hand. The person can't tell which, and needn't.

**An instruction** comes back as a receipt under the box: one line saying what she did and where it went, with Undo. If the kind is wrong, the receipt is the fix: the kind is a word you tap. If she can't guess something she needs, she asks exactly one thing, inline, with buttons. "Trampoline park Saturday" could be a save or a plan; she takes the cheaper reversible reading, saves it, and offers the next step.

**Her questions** are the only thing that interrupts: a pitch to answer, a plan to set, how an outing went. They sit on Home between the box and the tiles, in the destination they belong to, and go out as pushes. Each has its origin and its buttons. When she has none, nothing is there. She asks once, once more a week later, then lets it go.

**Her notes** live on items: hours found, a rain backup, a cheaper night, dated. Never a feed.

**Her budget:** at most one of her own suggestions on a free weekend stretch, the What about set, one weekly note, and pushes only for her questions, hard dates and last chances. Her quiet is what makes the rest worth reading.

**Cost:** no screen asks a model when it is viewed. Hints, rankings, the week, the lists and search are code. What about is made ahead. Vera's model calls are the box (a question or an instruction), "Different ones", the weekly note, shaping a plan, and the deeper check when a plan is taking shape.

## 7. Moving around

- **Persistent controls, two:** the box at the top and the destination row at the bottom. In the same place on every screen. The row's first item is Now.
- **Tap** opens. **Chips** narrow, always in the same place. **Back** goes up one level, and from a destination it goes to Now.
- **The row is the only menu.** Seven short names and Now. There is no second menu anywhere, because two menus showing different subsets of the same places is what made the current page confusing.
- **Deep links** are the paths in section 2. A push, a Telegram link, the tablet and the installed page all land on them. Opening a deep link from outside shows the item with the row beneath it, never a dead end.
- **Scoped box state** is per screen: leaving a destination clears its scope.
- **A reply over a screen** never navigates on its own. Only its pointer does, and only when tapped.
- **Her questions** are the only global signal, and they are on Now. The row carries no badges.

## 8. Platforms

### Web, phone width

The reference layout and the one most used. Now as drawn in section 3, the box at the top, the destination row at the bottom, her reply as a sheet. Installable to the home screen (the manifest exists), with Web Push for her questions (it exists). "What now?" is one tap from anywhere.

### Web, big screen

```
┌──────────┬─────────────────────────────────┬──────────────────┐
│ FamilyDB │                                 │ Vera             │
│          │                                 │                  │
│ Eat      │   the current destination,      │ her reply, then  │
│ Do       │   or Home's center:             │ the thread       │
│ About    │   status · box · her questions  │                  │
│ Week     │   · What about tiles            │                  │
│ Kids     │                                 │                  │
│ Soon     │                                 │                  │
│ Lists    │                                 │                  │
│ Did      │                                 │                  │
│          │                                 │                  │
│ (S) Sam  │                                 │ ▸ Ask or tell…   │
└──────────┴─────────────────────────────────┴──────────────────┘
```

The rail is the destination row with hints, Now fills the center, and the right column is Vera's: her reply as a live object, the thread behind it, and a reply can be pinned to the rail as a shelf of this person's own. Selecting an item narrows the right column to it. The frame grows in steps as today, never by stretching words. This is also where the admin works, with the back office behind the avatar.

### The kitchen tablet

A shared screen on the wall, signed in as the family. Now becomes **the board**: one surface, arranged by Vera, where what matters soonest is largest and nearest the middle, related things sit near each other, and what nobody has touched shrinks toward the edges and then rests. The weekend is big on Thursday. A kid's pitch sits beside the day it asks for. The shopping list hangs at one edge, always.

```
┌──────────────────────────────────────────────────────────┐
│  Ask Vera… ▸                                   (S)(A)(M)(T)│
│                                                           │
│   [Shopping ·6]      ┌───────────────────┐    [Maya:      │
│                      │ SATURDAY          │     Sky High?] │
│      [Kenji's        │ free from noon    │                │
│       tonight]       │ Night Market 5 pm │  [Sun: kites?] │
│                      └───────────────────┘                │
│   [library Wed]   [pumpkin carving · ends Sun]            │
│        · coast, someday ·        · pottery ·              │
└──────────────────────────────────────────────────────────┘
```

- **The box is large,** because "let's see what Vera thinks" is the family moment this screen is for. Her reply draws on the board, in the middle, and the family reads it together.
- **Faces along the top.** Tapping yours makes the next thing you say or tap yours: a kid can make a request as herself, a parent can say yes as themselves, on a device nobody signs in to. The choice lapses after a minute.
- **Nothing is typed to navigate.** Tap a card to open it on the board; tap the board to come back. The destinations are available but secondary, as a small row.
- **Guaranteed places:** anything set for today or tomorrow, anything waiting on a person, and the shopping list are always on the board whatever else she arranges. The rest is hers.
- **Resting things fade,** which is the clearest picture the app has of ideas going quiet, and the board is where a family would notice and say "oh, the coast".
- **Costs and admin never appear here.** The board is a kid-safe surface.
- It is the same answer functions as Now, drawn spatially. Built after the phone and the big screen.

### On a phone (no native app)

**Decided (October 2026): no native app.** The page added to the home screen is the phone app: it runs full screen from its own icon, keeps the person signed in, and tells them "Vera has a message" through Web Push (on an iPhone or iPad once it is added to the Home Screen, iOS 16.4 or later). The phone layout is the reference layout (section 3), so nothing in the map waits on an app.

A native app was weighed for four things the web does less well, and none was worth a second codebase, an App Store account and a release cycle for one family:

- **The share sheet.** On Android the installed page is already a share target (the manifest's `share_target`): a link or words shared to it wait in the box until Send. On an iPhone, Safari gives an installed page no share target, so a link is copied into the box or sent on Telegram, which takes shares from any app.
- **Widgets.** Not available to a web page. Now on the home screen is one tap away, and the kitchen tablet's board (section 8, The kitchen tablet) is the glanceable surface.
- **Siri and App Intents.** Not available. Telegram's voice notes are the hands-free way to tell her something.
- **Lock-screen buttons on her questions.** Web Push notices say only that she has a message and open the chat, by design (`docs/DESIGN.md` section 16): her questions are answered on Now, Telegram's buttons or the chat.

**What a script needs from the server** is in section 11: the same answers as data, for anything signed in as a person.

### Telegram

Telegram stays the place where Vera may interrupt and where most capture happens. Instructions are sentences and receipts. Questions get complete answers in words and a link to the destination. Her questions arrive with buttons. The commands map to destinations: /today and /week to This week, /now to What about, /lookup to a place. The same short names are used in both places, so "the Saturday plan" is one object everywhere.

## 9. People

| | Parent | Admin | Kid |
|---|---|---|---|
| First screen | Now, personal | Now, personal | A small Now: the box ("I want… / We should…"), her list with the answers on it, what's coming for her, and at most two picks |
| The kids | yes | yes | no; her own things are on My list |
| Costs, models, settings, status | no | behind the avatar | never |
| The box | general and scoped | same | general and scoped, with a daily message count said gently |
| Her questions | pitches, plans, ratings | same, plus admin alerts | invitations and choices |
| Items | full | full, plus Edit by hand on people | her own and the family's, no fading, no sources, presents for her hidden |
| Threads | her own; reads each kid's | same | her own, told that parents can read it |
| Where they meet it | phone, and the tablet for the family moment | the PC for admin, the phone otherwise | the tablet, occasionally a phone; lightly |

Threads are per person. What anyone captures is shared with the family unless they say "just for me" or "keep it from Theo", and a kid's request always reaches a parent's Now as a question. A teenager can be given the parent's destinations without the back office, by one switch on her page in The family. The kids here are eleven and thirteen and use the app lightly, mostly to ask for things; their screens are drawn for that, not for browsing.

## 10. States that have to be right

- **The first day.** Now is the box with "A place your family would happily go back to", one line from Vera introducing herself, and the destination row. No picks until she has something to pick from; she says when she will. Nothing is empty-with-chrome.
- **A new tile's empty state** is one sentence and the box. Never a diagram of what will be here.
- **Vera can't answer** (no key, out of credit, the company is down). The status line says so in plain words. Every destination still works, because they are code. The box still accepts instructions: they are kept as scraps and filed when she is back, and the receipt says "Kept. I'll sort it when I'm back." Nothing a person types is ever lost.
- **No calendar connected.** This week shows the plans made here and says so once.
- **No kids.** The kids tile is absent. The kid chips are absent everywhere.
- **Offline.** The page needs the server, so a phone with no signal shows the browser's own page. What a person typed is not lost: the box keeps an unsent message in the tab (`ask.js`) until it is sent, and Telegram queues on the phone.
- **A wrong guess.** The receipt is the fix, Undo is on every receipt, and "that's wrong" said to the box corrects the thing it was said about.
- **A deep link to something gone.** "That plan was set for last Saturday; here's how it went." Never a 404 for a thing that existed.

## 11. What the server provides

The page is server-rendered, and every destination and item is one answer function that returns data: the view builds what the page shows and hands it to `web/answers.py`'s `answer`, which draws the template, or, when the request came through the API, returns the same view-model as JSON. One function, two readers, so the page and the API cannot disagree. Built October 2026 (`web/api.py`).

- **Answers:** `GET /api/<path>` for every family page at its own address (`/api/now` is Now, then `/api/eat`, `/api/week/2026-10-17`, `/api/place/57`…), returning `page`, `answer` (what the page draws: rows, chips, hints, the forms' fields), `box` (its scope, quick sentences and what the last message brought back) and `row` (the destinations). The page's own permission is asked; what a page's records carry and the page never shows (a Telegram id, a calendar's event id, whom a present is kept from, a birthday, anything named like a secret) is left out. Code only, no model call. The back office (settings, the family list, the guide, Status's forms) is pages, not answers.
- **The box:** `POST /api/say` with `text`, an optional `scope` and `intent`, the `page` it was said from, a photo (in a form) and position (`send_where`, `lat`, `lon`). It answers at once with the message's id and `check`, the page's answer with `?asked=`, which carries the receipt (what she did, with the change Undo takes back) or her reply, as the page shows them under the box. The same framing as the box's form (`chat._framed`), the same turn.
- **Buttons and forms:** `POST /api/act` names any of the page's forms by its view (`finish_task`, `snooze_task`, `change_list`, `record_outcome`, `answer_wish`…), the numbers in its address by name (`task_id`, `idea_id`…) and the rest as its fields. The form's own view does the work, so a tap here is the tool call the button makes, with the same permission and checks (a task's revision, a form's `once`). No model call. It answers with what the page would have said, whether anything changed, and the change Undo takes back.
- **Her questions:** part of the Now answer, and delivered as Web Push notices that say only that she has a message.
- **Search:** `GET /api/find?q=` by name across item types.
- **Auth:** the session cookie, as for the page; there is no other way in. `GET /api` says who is asking, the pages and forms they may use, and the token a write carries in an `X-CSRF-Token` header, from the page's own origin. Signed out, the API answers 401 in JSON rather than sending a script to the sign-in form.
- **Made-ahead sets:** What about is written by a job into its own table with its context and chosen-at, read by the answer function.

Everything in this section is read-only or a tool call except the box, which is the one model call a person makes on purpose.

## 12. The second pass

What was weighed again after the first draft, and what changed.

**Tested against the question inventory.** Every question in the inventory lands on a destination, in search, on an item, in the status line, or in the box. The two that land nowhere on Home are "what does Vera know about Theo" and the admin questions; both are behind the avatar on purpose.

**Tested against the intents.** The four most frequent encounters (say something, remind me, answer her, just looking) are served entirely by Home: box, receipt, her questions, status line. Nothing on Home serves any other intent, which is what keeps it short. The weekly encounters each have a tile. The rare ones (fix, tidy, settings) are behind an item's Edit by hand or the avatar.

**Changed: Eat out and Things to do are separate doors.** The first draft had restaurants inside the pile. Eating is the most frequent decision, has its own ranking (open at meal time, cuisine) and its own question, so it earns its door.

**Changed: reminders moved onto This week, with the plate strip.** A separate Reminders tile was a second door to the same things. The strip is what keeps the dateless ones from being lost.

**Changed: What about is made ahead.** The first instinct was to choose at view time. That breaks the no-model-call-per-view rule and makes the screen slow. Made ahead, it is instant, cheap, and has a date on it that reads as honesty.

**Changed: the destination row instead of a tab bar of icons.** Seven short names in a row, the same on every screen, is one menu. A tab bar would have held four and pushed the rest into a second menu. (In the first draft this was a launcher of tiles with no bar at all; the third pass, below, replaced the launcher with Now and kept the row.)

**Changed: the big screen's center is Now.** The first draft put a launcher there and then, finding it sparse, added the picks. With Now as the first screen on every device, the center is simply Now, and the rail is the row.

**Kept: What we did as its own tile.** It was the weakest tile, and folding it into This week's past was tempting. It stays because ratings, favorites and "have we been?" need a place a person would look, and because the memory end of the ladder is where she learns taste.

**Kept: no chat page.** The thread exists behind her reply, as a record. Making it a destination would make it the place people live, and a thread never ends, which is the one thing Home must never be.

**Weighed: a kid's tab bar.** Four tiles fit a tab bar, and a kid might like one. Rejected for consistency: her app is the parents' app with less in it, and learning a different navigation from her parents is a cost for a family that shares devices.

**Decided: no native app.** The web app on a phone covers the map, and the family does not want a second app to keep (section 8, On a phone). The API of section 11 was built anyway, since the page's own scripts and anything else signed in as a person benefit from it.

### The third pass: three other paradigms, and the family's answers

Before settling, three structurally different paradigms were drawn and weighed against the launcher: **the line of time** (one surface from the past through today to someday, free time and pencil on it), **the workspace** (the conversation as the app, every answer a live object, pins as shelves), and **the board** (one spatial surface of the family's things, arranged by Vera by importance). Each is the best design at one level of the map and a poor design for the whole: the line for This week, the workspace for Vera's column on a big screen, the board for a shared tablet.

The family then answered the questions that decide between them, and the answers moved the skeleton:

- Phones first; Telegram for quick instructions; admin on a PC; kids on a tablet. **So the phone layout is the reference, the big screen carries admin, and the tablet gets the board.**
- The daily plan is improvisational: what to do now or in the next day or two. **So the first screen is Vera's picks, not a menu, and coordination is a destination.**
- The app may rearrange itself freely. **So the middle of Now is hers; only the box and the row are fixed.**
- Vera is the front door for instructions, which are the default; a supporting assistant for questions. **So the box is first on every first screen, and the destinations stand on their own with the box scoped to them.**
- The kids are eleven and thirteen and will mostly ask for things. **So the kid's app is a box, her list and what's coming, and nothing to browse.**
- Threads are per person. **So Now is personal, capture is shared by default, and surprises are a sentence.**
- Cost has some room. **So the picks refresh on open when stale, and "What now?" is a free call to make.**
- A kitchen tablet is wanted, for "let's see what Vera thinks". **So the board is a real layout, built third, with faces along the top.**
- A single Home is not needed, as long as an instruction can be given on first load. **So there is no launcher. There is Now, which is different every time, under a box that never moves.**

What this changed from the first draft: Home the launcher became Now; What about became the first screen's content rather than a tile; the eight tiles became a fixed row of seven; the tablet became a third layout; the kid's app shrank; threads became per person; and the picks may refresh on open.

**Still needs a decision from the family:**

1. Whether reminders carry owners ("I'll handle it"). On by default here, and built: a grown-up takes on a to-do that is everyone's from the plate or a reminder's button; it is the family's call.
2. Whether a kid may set a plan, or only propose and second. Here: propose and second.
3. Which kid the kid's screens are drawn for first. Here: a reader of about eight to twelve.
4. Whether anything leaves the house: a gift page for grandparents, a sitter's link. Here: nothing until asked.
5. Whether the What about set is also sent to Telegram on Thursday as the weekly note, or only shown. Here: sent, as the digest already is.
6. On the tablet, whether a tapped face should lapse after a minute or stay until tapped again. Here: a minute.

## 13. Build order

1. **The answer functions and the API** (section 11). Everything else reads them, and every layout shares them.
2. **Now on the phone**: the box, receipts, the context line, her questions, the picks read from the made-ahead set, today's line, the destination row, search in the box.
3. **The picks made ahead and refreshed on open**, from the choosing job, with "Different ones" and "What now?".
4. **The destination skeleton**, then Eat out and This week.
5. **The item skeleton**, then a place and a plan, including the plan taking shape.
6. **Her reply over a screen**, and the answering contract for the questions code can answer.
7. **The kids, Lists, Happening soon, What we did.**
8. **The kid's Now and roles**, per-person threads on the page.
9. **The big-screen frame** with the rail, Vera's column and pinning.
10. **The kitchen tablet board.**
11. **The phone:** the installed web app. No native app (decided October 2026).

