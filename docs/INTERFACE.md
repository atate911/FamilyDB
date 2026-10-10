# The interface: map and architecture

The skeleton every screen is built on, for the web page and an iOS app. First full draft, October 2026, after the concept work in `CONCEPT.md` and the rounds of thinking that followed it. Where the two disagree, this document wins.

It is organized from the outside in: what the app is, the map, each level of the map, the Vera layer over all of it, how a person moves, the two platforms, the people, the awkward states, and what the server has to provide. Section 12 records the second pass: what was weighed, what changed, and what still needs a decision.

## 1. What the interface is

Two things, and a person always knows which they want:

- **Destinations to look at.** A short set of screens, each named for a want ("Where should we eat?"), each one tap away, each opening on its answer with nothing to set first. Ranked by code, so they are instant and free.
- **Vera to ask.** One box, on every screen, for any question or instruction in the person's own words. She has the family's database and answers completely in her own voice, then points to a screen only if it adds something. She never defers.

Four rules hold everything below:

1. **Names are wants, not nouns.** A tile says what you'd get, not what table it reads.
2. **Every screen opens on its answer.** No date, filter or person to choose before anything shows.
3. **Three gestures.** Tap to open, chips to narrow, back to go up. The box is the fourth thing, and it is the same everywhere.
4. **Two levels of depth, then a page.** Home, a destination, an item. Nothing is further than two taps.

## 2. The map

```
LEVEL 0   Home
          status · the box · her questions (when any) · the tiles

LEVEL 1   Destinations                              path
          Where should we eat?        (Eat out)     /eat
          What could we do?           (Things)      /do
          What about…                 (Her picks)   /about
          This week                   (Calendar)    /week
          The kids                                  /kids
          Happening soon                            /soon
          Lists                                     /lists
          What we did                               /did

LEVEL 2   Items
          a place        /place/57         a kid        /kids/maya
          a plan         /plan/12          a list       /lists/shopping
          a day          /week/2026-10-17  a reminder   /reminder/88
          a happening    /soon/301         a memory     /did/12

VERA      the box (every screen) → her reply (over the screen) → the thread (behind the reply)
          her questions (Home, and in the destination they belong to)
          her notes (on items)
          receipts (under the box, after an instruction)

AVATAR    You · The family · Settings · Status · Guide        /you /family /settings /status /wiki
```

The paths are the deep links. Telegram, push notifications, widgets and the iOS app all land on the same ones, so one place has one address everywhere.

## 3. Home

Home is the launcher. Its job is to show what the app can tell you, and to take whatever you want to say.

```
┌──────────────────────────────────────┐
│ FamilyDB                         (S) │
│                                      │
│ Nothing needs you.                   │  status, always the first line
│                                      │
│ ┌──────────────────────────────────┐ │
│ │ Ask Vera anything, or tell her…  │ │  the box
│ └──────────────────────────────────┘ │
│                                      │
│ Maya asked for the trampoline park.  │  her questions, only when any
│ Saturday morning is free.            │
│ Plan it · Later                      │
│                                      │
│ ┌───────────────┐ ┌───────────────┐  │
│ │ Where should  │ │ What could    │  │  four large tiles
│ │ we eat?       │ │ we do?        │  │
│ │ Kenji's       │ │ 3 fit         │  │  each with a live hint
│ │ tonight       │ │ Saturday      │  │
│ └───────────────┘ └───────────────┘  │
│ ┌───────────────┐ ┌───────────────┐  │
│ │ This week     │ │ The kids      │  │
│ │ Free Sat pm   │ │ 1 waiting     │  │
│ └───────────────┘ └───────────────┘  │
│                                      │
│ What about…  Happening soon          │  four small tiles
│ Lists        What we did             │
│                                      │
│ Search places, plans and people      │
└──────────────────────────────────────┘
```

- **Status** is one line and is always there: "Nothing needs you", "2 things are waiting on you", "Vera can't answer right now, but everything else works."
- **The box** takes a question or an instruction. A question comes back as her reply over Home. An instruction comes back as a receipt under the box. Its placeholder teaches what it is for and changes now and then: "A place you heard about, a reminder, or a question."
- **Her questions** are the only thing on Home that comes and goes. Each is one or two sentences with its origin, and one or two buttons. They are the same questions that reach Telegram as pushes.
- **The tiles** never change order. The hints under them change, read from the database at view time, cheap. The four large tiles are the four most used. The small ones are a row.
- **Search** finds by name across places, plans, people, lists and happenings, and opens the item. It is for "where's Kenji's?", which should not need Vera.

**On a big screen** the tiles become the left rail, always visible, with the same names and hints. Home's center is then status, the box, her questions, and the What about tiles, because a wide screen has room for the richest view and a person at a desk is usually deciding something. The right column is Vera's.

**A kid's Home** is the same page with four tiles: My week, My list, What could we do, What about. Status reads "Nothing new for you." Her questions to a kid are invitations ("Which do you want most?"), never chores.

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

The one destination where Vera chooses. Six to eight tiles, one of each kind, picked for this moment across the family's own material and her finds, each with a reason.

- **Opens on:** the current set, with a header saying what drove it ("Dry Saturday, free from noon. Maya's been asking.") and when it was chosen.
- **A tile:** kind · when it fits · name · one sentence of why. Tap opens the thing with Plan it ready. Swipe away is "not now". Hold offers "not this" and "not for me".
- **The slots** are decided by code for this moment: tonight, the weekend, something new, with the kids, just the parents, a day trip, something in, from a kid's wish. The model fills each from the dossier; code verifies every pick is real before it shows.
- **Made ahead,** never at view time: each morning, Thursday evening for the weekend, and when the context moves (forecast, a plan set, a wish arrives). "Different ones" is a deliberate call and says so. Inside the existing monthly choosing budget.
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

- **Persistent controls, two:** Home and the box. In the same place on every screen.
- **Tap** opens. **Chips** narrow, always in the same place. **Back** goes up one level, and from a destination it goes to Home.
- **No tab bar on a phone.** Home is the menu. Two menus showing different subsets of the same places is what made the current page confusing.
- **Deep links** are the paths in section 2. A push, a Telegram link, a widget and the iOS app all land on them. Opening a deep link from outside shows the item with a Home button, never a dead end.
- **Scoped box state** is per screen: leaving a destination clears its scope.
- **A reply over a screen** never navigates on its own. Only its pointer does, and only when tapped.
- **The status line** on Home is the only global signal. No badges on tiles beyond their hint.

## 8. Platforms

### Web, phone width

The map as drawn: Home as the launcher, the box and Home button fixed at the bottom, her reply as a sheet. Installable to the home screen (the manifest exists), with Web Push for her questions (it exists). This is the first platform and the reference layout.

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

The rail is the launcher, with the same names and hints. Selecting an item narrows the right column to it. The frame grows in steps as today, never by stretching words.

### iOS

**Recommendation: the installed web app first, a native app second, and the native app only for what the web can't do.** The web app already runs on a phone, installs to the home screen, and can push. A native app earns its cost with four things: the share sheet, widgets, Siri and App Intents, and reliable push through APNs.

- **The share sheet is the best capture there is.** A link, a screenshot or a photo shared to Vera from any app is the "I just heard about this" moment with zero typing. This alone may justify going native.
- **Widgets:** This week (small: today and tomorrow), On your plate, and the status line. Read-only, from cached answers.
- **App Intents:** "Tell Vera…" and "Ask Vera…" from Siri and Shortcuts, routed to the same box endpoint.
- **Push:** her questions, with their buttons as notification actions, so a parent can say yes from the lock screen.

**Navigation on iOS** is the same map: a navigation stack from Home, no tab bar, the box as a bottom bar (the way a search bar sits), her reply as a sheet. Universal links map to the paths in section 2. Back is the platform's back.

**Offline:** the last answers for each destination are cached and shown with their age. The box queues instructions and sends them when back online, with the receipt arriving then.

**What the native app needs from the server** is in section 11.

### Telegram

Telegram stays the place where Vera may interrupt and where most capture happens. Instructions are sentences and receipts. Questions get complete answers in words and a link to the destination. Her questions arrive with buttons. The commands map to destinations: /today and /week to This week, /now to What about, /lookup to a place. The same short names are used in both places, so "the Saturday plan" is one object everywhere.

## 9. People

| | Parent | Admin | Kid |
|---|---|---|---|
| Home tiles | all eight | all eight | My week · My list · What could we do · What about |
| The kids | yes | yes | no; her own things are on My list |
| Costs, models, settings, status | no | behind the avatar | never |
| The box | general and scoped | same | general and scoped, with a daily message count said gently |
| Her questions | pitches, plans, ratings | same, plus admin alerts | invitations and choices |
| Items | full | full, plus Edit by hand on people | her own and the family's, no fading, no sources, presents for her hidden |
| Threads | her own; reads each kid's | same | her own, told that parents can read it |

A teenager can be given the parent's tiles without the avatar's back office, by one switch on her page in The family.

## 10. States that have to be right

- **The first day.** Home is the status line "Hi, I'm Vera" and the box with "A place your family would happily go back to". Tiles appear as they get something to show; the first is This week once the calendar is connected or a plan is made. Nothing is empty-with-chrome.
- **A new tile's empty state** is one sentence and the box. Never a diagram of what will be here.
- **Vera can't answer** (no key, out of credit, the company is down). The status line says so in plain words. Every destination still works, because they are code. The box still accepts instructions: they are kept as scraps and filed when she is back, and the receipt says "Kept. I'll sort it when I'm back." Nothing a person types is ever lost.
- **No calendar connected.** This week shows the plans made here and says so once.
- **No kids.** The kids tile is absent. The kid chips are absent everywhere.
- **Offline (iOS).** Cached answers with their age; the box queues.
- **A wrong guess.** The receipt is the fix, Undo is on every receipt, and "that's wrong" said to the box corrects the thing it was said about.
- **A deep link to something gone.** "That plan was set for last Saturday; here's how it went." Never a 404 for a thing that existed.

## 11. What the server provides

The current page is server-rendered. The web keeps that; the iOS app needs the same answers as data. One rule makes both cheap to keep in step: **every destination and item is one answer function that returns data, and the web template and the API both read it.** The view-model builders in `web/` already return dictionaries; this makes that the contract.

- **Answers:** `GET /api/<path>` for every path in section 2, returning what the screen shows, including the chips available and the hints. Cheap, code only, cached a minute where it is already.
- **The box:** `POST /api/say` with text, an optional scope, an optional photo and position. Returns either a receipt (what she did, with the undo token) or a reply (her answer, its rich pieces, its one pointer). The same endpoint the web form posts to.
- **Buttons:** `POST /api/act` for every tap that is a tool call: Yes, Not now, Done, Snooze, I'll handle it, Set the plan, a face. No model call. Returns the updated item.
- **Her questions:** part of the Home answer, and delivered as pushes (Web Push today; APNs for the native app) carrying the deep link and the button actions.
- **Search:** `GET /api/find?q=` by name across item types.
- **Auth:** the session cookie for the web; a token for the native app, issued by the same sign-in, carrying the same role.
- **Made-ahead sets:** What about is written by a job into its own table with its context and chosen-at, read by the answer function.

Everything in this section is read-only or a tool call except the box, which is the one model call a person makes on purpose.

## 12. The second pass

What was weighed again after the first draft, and what changed.

**Tested against the question inventory.** Every question in the inventory lands on a destination, in search, on an item, in the status line, or in the box. The two that land nowhere on Home are "what does Vera know about Theo" and the admin questions; both are behind the avatar on purpose.

**Tested against the intents.** The four most frequent encounters (say something, remind me, answer her, just looking) are served entirely by Home: box, receipt, her questions, status line. Nothing on Home serves any other intent, which is what keeps it short. The weekly encounters each have a tile. The rare ones (fix, tidy, settings) are behind an item's Edit by hand or the avatar.

**Changed: Eat out and Things to do are separate doors.** The first draft had restaurants inside the pile. Eating is the most frequent decision, has its own ranking (open at meal time, cuisine) and its own question, so it earns its door.

**Changed: reminders moved onto This week, with the plate strip.** A separate Reminders tile was a second door to the same things. The strip is what keeps the dateless ones from being lost.

**Changed: What about is made ahead.** The first instinct was to choose at view time. That breaks the no-model-call-per-view rule and makes the screen slow. Made ahead, it is instant, cheap, and has a date on it that reads as honesty.

**Changed: no tab bar on the phone.** Weighed against the platform convention and chosen deliberately: the launcher is the menu, and the hint under each tile is more useful than a tab icon. If use shows people wanting faster access to one destination, the fix is a "pin to bottom" choice per person, not a second menu.

**Changed: desktop Home shows the What about tiles.** On a phone, Home must be short. On a wide screen the same content leaves most of the screen empty, and the person at a desk is usually deciding. The tiles are the richest thing in the app, so the center shows them. The rail still names Home as the launcher, so nothing is lost.

**Kept: What we did as its own tile.** It was the weakest tile, and folding it into This week's past was tempting. It stays because ratings, favorites and "have we been?" need a place a person would look, and because the memory end of the ladder is where she learns taste.

**Kept: no chat page.** The thread exists behind her reply, as a record. Making it a destination would make it the place people live, and a thread never ends, which is the one thing Home must never be.

**Weighed: a kid's tab bar.** Four tiles fit a tab bar, and a kid might like one. Rejected for consistency: her app is the parents' app with less in it, and learning a different navigation from her parents is a cost for a family that shares devices.

**Weighed: iOS native now.** Rejected for now. The web app on a phone covers the map. Go native when the share sheet, widgets or lock-screen actions are wanted, and build the API in section 11 first, since the web benefits from it too.

**Still needs a decision from the family:**

1. Whether reminders carry owners ("I'll handle it"). On by default here; it is the family's call.
2. Whether a kid may set a plan, or only propose and second. Here: propose and second.
3. Which kid the kid's screens are drawn for first. Here: a reader of about eight to twelve.
4. Whether anything leaves the house: a gift page for grandparents, a sitter's link. Here: nothing until asked.
5. Whether the What about set is also sent to Telegram on Thursday as the weekly note, or only shown. Here: sent, as the digest already is.

## 13. Build order

1. **The answer functions and the API** (section 11). Everything else reads them, and they are the first thing both platforms share.
2. **Home**: status, box, receipts, her questions, tiles with hints, search.
3. **The destination skeleton**, then This week and Eat out, the two with the clearest answers.
4. **The item skeleton**, then a place and a plan, including the plan taking shape.
5. **Her reply over a screen**, and the answering contract for the questions code can answer.
6. **What about**, made ahead by the choosing job.
7. **The kids, Lists, Happening soon, What we did.**
8. **The kid's Home and roles.**
9. **The big-screen frame.**
10. **iOS**, starting with the installed web app, then native when the share sheet is wanted.
