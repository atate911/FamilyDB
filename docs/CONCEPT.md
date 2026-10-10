# FamilyDB: a concept for the page

First draft, October 2026. One vision for how the family meets Vera on the web page and in Telegram, drawn from five rounds of brainstorming and a clean slate. Nothing here is final. It is the shot, not the rulebook.

## 1. What it is, in one breath

Vera is the family's own assistant. You tell her things in passing. She keeps them, works on them, and brings them back when they are useful. The page is where you see what she has kept and what she proposes, in whichever way suits what you are doing.

Four principles hold the whole design:

- **Talk in, see out.** Saying something is how it gets in. Looking is how it comes back. Forms are rare, and small adjustments are taps.
- **Pencil until agreed.** Anything Vera proposes is drawn in pencil and worded as a question. Only a person's yes inks it.
- **Fade unless repeated.** What nobody brings up again goes quiet on its own. The collection stays the size of the family's real interest.
- **Depth one tap down.** What decides a choice is on the card. Everything else is one tap away.

## 2. The ladder, kept backstage

Everything the family says to Vera is one of two things: something to do together (a place, an outing, a trip, a wish for an experience) or something to keep track of (a reminder, a list item, a wish for a thing). Things to do together climb a ladder. Things to keep track of sit beside it.

| Rung | What it means | What the family reads |
|---|---|---|
| Mentioned | Said in passing. Vera filed it. | "Quinn mentioned this on Tuesday" |
| An idea | Worth keeping. Details filled in. | "Something we could do" |
| Taking shape | A plan with open questions. | "Could do Saturday · time? · who?" |
| Planned | A person said yes. On the calendar. | "Saturday: tide pools. Leave 9:30." |
| A memory | It happened. One line on how it went. | "Last Saturday. Worth doing again." |

The family never learns these names. They read the words in the right column. The ladder shapes how a card looks and what it offers, never where it sits.

## 3. The places

Four places, one bar. Nothing else in the main navigation.

```
PHONE                                BIG SCREEN
┌──────────────────────────┐         ┌──────┬──────────────────────┬──────────────┐
│                          │         │ Home │                      │ Vera         │
│   the current place      │         │ Ideas│   the current place  │ (your thread,│
│                          │         │ Cal  │                      │  or the thing│
│                          │         │ Lists│                      │  you opened) │
├──────────────────────────┤         │      │                      │              │
│ ▸ Tell Vera, or find…    │         │ ●you │                      │ ▸ Tell Vera… │
├──────────────────────────┤         └──────┴──────────────────────┴──────────────┘
│ Home   Ideas   Cal   Lists│
└──────────────────────────┘
```

**The bar** sits on every page. Typing filters whatever you are looking at, live and free. Sending goes to Vera. A small chip says what you are talking about ("about: Saturday plan") and can be dismissed to talk generally. On a phone the thread rises as a half sheet so you can watch the page change while she works. On a big screen it is the right column, and it narrows to one thing when you open one.

**Behind your picture:** you (what Vera knows about you, your look, your password), the family (each person, and for parents each kid's thread and list), and for admins the back office: settings, status, keys and costs. The back office is dense on purpose and is not part of this concept.

### Home

Home answers "anything I should know?" It is short, it has a fixed order, and it ends.

1. **Her line.** One sentence in her voice. "Dry weekend ahead, and Theo's library books are due Wednesday."
2. **Today.** Set plans and reminders for the day, drawn solid. These always appear. Vera curates nothing here.
3. **Needs you.** At most three things waiting on a person: a plan to set, a kid's pitch, how Saturday went. Absent when empty.
4. **One idea.** A single glimpse for the next free stretch, with its reason. Never more than one.
5. **Just caught.** What she filed from recent mentions, each with keep, fix or drop. Only the ones she was unsure about.
6. **The end.** "That's all for today." On a quiet day Home is three lines and the end.

In the evening Home turns to tomorrow, and if something happened today it asks once: how was it, with three faces and room for a photo.

On a big screen Home gains a small "coming up" column and nothing else. More room never means more demands.

### Ideas

Ideas answers "what could we do?" It is the pile, and it is the family's.

**At a glance:** four plain entrances (Eat · Go out · Stay in · Trips), then shelves Vera keeps fresh: "Ends soon", "Good for a rainy day", "Been meaning to", "Vera found". The family's own things come before her finds, and every card says where it came from: "Maya's idea", "You liked somewhere like this", "Vera found this for the long weekend".

**Sifting:** three chips, not filters. *How long* (an hour, an afternoon, a day), *energy* (easy, up for something, make a day of it), *who's in* (everyone, just us, me and one kid). And one button, **Surprise us**, which returns exactly one thing with its reason.

**Views:** cards by default. **Map** draws drive time as rings from home; places the family has been are solid and the rest of the map is faint, so the family's own territory shows. **Season** places ideas in the months they suit, so "someday" comes round instead of sitting still.

**One tap deeper:** a thing's page. The glimpse, the facts that matter (open today, drive, cost, booking), what Vera filled in and when she checked it, who said it and their exact words, and the bar scoped to this thing ("Plan it for Friday", "Good for the kids?", "Drop it"). "Edit by hand" is a quiet link at the bottom.

**Fading:** a card untouched for six weeks goes paler. At three months Vera asks once, "still want this?" Unanswered, it rests: out of view, still findable by search, and back the moment anyone mentions it again.

### Calendar

Calendar answers "what are we doing, and when are we free?" It is a lens on the calendar the family already keeps.

**At a glance on a phone:** an agenda with a week strip above it. Free time is drawn as real space, not absence. Month is one tap away for orientation.

**At a glance on a big screen:** the week or month on the left, the selected day on the right.

**Pencil and ink:** set plans are solid and reminders are small marks. A plan taking shape appears in pencil only once the family is considering a time. Vera may pencil one idea into a free weekend stretch, never more. Tapping a free stretch asks her for two or three glimpses that would fit it.

**One tap deeper:** a day page. For a plan taking shape it leads with the open questions. For a set plan it leads with when to leave, who is coming and what to bring. After the day it holds the memory: a photo, a line, the faces, and "Again?", which puts the place back among the ideas.

### Lists

Lists answers "what do we need?" It is deliberately the most ordinary page in the app.

**At a glance:** the live lists with counts, the one in use on top. Shopping. Reminders. Each kid's wish list. Packing lists that belong to a plan and go when it does.

**One tap deeper:** a fast checklist with big targets. Ticking milk is a tap and never a conversation. Context sits behind each item: who asked, the photo of the exact thing, which plan it belongs to.

**Reminders** carry an owner. Anyone can say "I'll handle it", and Vera tells whoever asked when it is done. A reminder can wait for a date, for a condition ("when it rains", "when we're near the bakery") or for a window ("some Saturday morning"), and Vera brings it up when the window comes round free.

**Wishes** are a kid's own list in their own order. A parent sees the same list with three quiet states: wanted, being considered, done. Being considered never looks like a promise. A wish for an experience ("I want to go ice skating") joins the ideas with the kid's name on it.

## 4. One card, everywhere

A thing looks the same in every place. It has three sizes: a line, a card, a page. Tapping grows it. That is the only gesture to learn.

| | Taking shape | Planned |
|---|---|---|
| Outline | Dashed, light | Solid, filled |
| Voice | A question. "Saturday could go like this…" | A statement. "Saturday: tide pools. Leave 9:30." |
| Content | The glimpse: how the day would go, in two sentences | Logistics: when to leave, what to bring, what is booked |
| Facts on the card | Cost, drive, the one thing that might stop it | Time, place, who |
| Actions | Yes · Not this one · Change something | Tap for the day page |
| In words | "Could do", "proposed by Vera" | "Planned", with who said yes |

A plan sets piece by piece. "Saturday ✓ · 10 am ✓ · who?" The dashes are the to-do list. When the last one goes solid, it is on the calendar. If nobody sets it by its decide-by, it dissolves and its ideas go back unharmed.

Tentative is never carried by color alone. The outline, the words and the actions all say it.

## 5. The glimpse

Every proposal from Vera opens with two sentences of how the day would go, written as if it already happened. "You got there before the crowd and the tide pools were full of crabs. Theo found a starfish and nobody wanted to leave." The logistics come under it.

This is where her character lives. It costs nothing extra: the words come from the same call that chose the suggestion. Confirmations, lists and anything used in a hurry stay literal.

## 6. How she behaves

**She works on things, and shows it on the thing.** Hours checked, a rain backup found, a cheaper night spotted: each appears on the card it belongs to, not in a feed. Her line on Home sums up what changed since you last looked.

**She has a budget.** One idea on Home. One weekly note with the weekend's picks, dealt as a few cards to keep or pass. Pushes only for hard dates, last chances and direct replies. Her quiet is what makes a suggestion worth reading.

**She looks things up lightly, then properly.** When something is saved she fills in the basics within minutes and says nothing. When a plan is taking shape she checks what matters today: hours, tickets, the forecast. The card says which it is: "saved in March" or "checked this morning".

**She leaves a chair empty.** Every plan she builds keeps one slot open, labeled "something we find on the way" or a kid's name. She does not fill it.

**She proposes, then earns more.** She never writes to the real calendar on her own. After the family has accepted the same kind of thing several times, she asks whether to just do it next time.

**She notices repeats.** "Third rainy Sunday at the noodle place. Make it a tradition?" One tap gives it a name and a rhythm.

**She can keep a secret.** A parent can seal a plan. The kids see a countdown, when to leave and what to wear, and the card opens on the day. The same mechanism keeps a present from the person it is for.

**She says goodbye.** Nothing disappears silently. A fading idea goes pale, gets one last call, and then rests where search can still find it.

## 7. Kids

A kid opens the same app and finds less in it, worded for them. Home, Ideas, Calendar and Lists, each showing what is theirs and the family's. Time is in words: "after school", "tomorrow morning", "in 23 days". Nothing about costs, models, limits or how things work. A message count, said gently.

Their agency is three verbs:

- **Wish.** Whatever they tell Vera is theirs, carries their name, and never fades silently.
- **Pitch.** Vera helps them make the case for a plan. It lands in a parent's "needs you" with the kid's face on it, and it always gets an answer: yes, not yet, or let's shape it.
- **Choose.** When she offers options for a family afternoon, their vote counts and shows. A kid's yes is a vote. A parent's yes is a commitment.

The design is drawn for a reader of about eight to twelve. A younger kid uses the mic on a parent's lap. A teenager can be given the grown-up view, without the back office, by one switch on their page.

## 8. In Telegram

Telegram is where Vera may interrupt. The page is where she waits.

In the chat app she writes short and links to the exact thing on the page. A proposal is its two sentences and two buttons: yes, not this one. A reminder has done and snooze. A sealed plan is a message that opens on the day. A photo of a flyer comes back as an event, a deadline and a thing to bring, each accepted with one tap. The same things have the same short names in both places, so "the Saturday plan" means one object everywhere.

Each person talks to Vera in their own thread. What they capture is shared with the family unless they say "just for me" or "surprise, hide it from Theo". Parents can read a kid's thread, and the kid sees a line saying so. The family group on Telegram stays as it is: a place everyone talks, and a thread of its own on the page.

## 9. A week in it

- **Tuesday.** Maya photographs a poster at school. Vera replies with a card: "Sky High Trampolines, with the kids, Maya's idea", and asks nothing. Twenty minutes later the card has hours and a drive time.
- **Thursday evening.** Her weekly note deals three cards for the weekend. The trampoline park is one, with its glimpse. Sam keeps two and passes one.
- **Friday.** The two kept cards are a plan taking shape on Home: "Saturday · morning? · who?". Alex says "morning, all of us" to the bar. The dashes go solid and the plan is on the calendar. Vera checks the park's Saturday hours and leaves a chair empty: "lunch somewhere we find".
- **Saturday 8:40.** Telegram: "Leave by 9:15. Bring socks." On the page, Home is the plan.
- **Sunday morning.** Home asks how it went. Three faces and a photo. Maya's card now reads "we did it", with her name on it. Vera asks one more thing: what made it good? Alex taps "early start" and "short".
- **A month later.** A free Saturday morning. The one idea on Home is a glimpse of a climbing gym Vera found, with its reason: "Short, early, and you loved the trampoline park."

## 10. The first days

- Vera asks each person one thing: a place you'd happily go back to tomorrow. That seeds favorites and taste at once.
- The backlog goes in all at once: screenshots, saved map pins, old notes. She sorts them overnight.
- Each kid's first act is a pitch. They have a card with their face on it within a minute.
- She stays quiet for a fortnight except for hard dates, until she has something worth saying.
- Google Calendar is connected when it unlocks something concrete, not as a setup step.

## 11. What is deliberately out

- A whole-app metaphor: a house, a garden, her room, a game board. Charming once, slow forever.
- A separate app for kids. Same house, different windows.
- The ladder as a layout. Columns of commitment look like work.
- Counts as goals: ideas done, outings a month, streaks. Every one becomes a guilt meter.
- Judgments on shared cards. "Theo tolerated it" never appears where Theo reads. Credit is public, taste is private.
- Scale badges for kids. "Special occasion" is a promise and a budget judgment in one word.
- A chat thread as the home page. A thread never ends, so Home could never be short.
- Any recording of the household.

## 12. Decisions the family makes

These are set by the family, not by the design.

- **Owners on reminders.** Whether "I'll handle it" is a thing in this house.
- **The golden ticket.** One pick a month each that cannot be refused. Off unless the family wants it.
- **Whether parents read the kids' threads.** Yes today, and the kids are told.
- **What leaves the house.** A gift page for grandparents or a sitter's link for the day would be the first things to. Nothing does until the family says so.
- **Who may set a plan.** Any adult. Kids propose and second.

## 13. What this costs to run

Nothing on this page asks a model when it is viewed. Glimpses come from the call that makes the suggestion. Fading, the map, free time, the week strip and the fixed order of Home are all code. The new calls are the ones the family would expect to pay for: her weekly note, shaping a plan, and the deeper check when a plan is taking shape.

## 14. What to build first

1. **Home in its fixed order, and the bar.** Most of the feel is here.
2. **One card, three sizes, pencil and ink.** The visual rule everything else uses.
3. **The plan taking shape**, with its dashes and its decide-by.
4. **Calendar with free time drawn** and one pencilled idea at most.
5. **Ideas with entrances, shelves, chips and fading.**
6. **Lists with owners, and wishes with their three states.**
7. **The glimpse, the empty chair, sealed plans, traditions.** The character, once the bones stand.
