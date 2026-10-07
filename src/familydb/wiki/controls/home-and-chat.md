# Home and Chat

Home is where you ask the assistant something and see what is coming up, what is left to do and what
was added lately. Chat is the conversation itself, where the answers arrive. They share one
conversation: a message sent from Home's box lands in Chat, and the page takes you there. Reading either
page makes no model call. Nearly every message you send does, and it is paid for.

## Who sees what

Everyone signed in sees Home and may chat. Who may do the rest is in
[who may do what](/wiki/security#who-may-do-what).

- **Admins and parents** share one family conversation, and Home shows the whole household.
- **A kid** has a shorter Home (the box, Next up for you, My list and My to-dos) and their own chat, which
  grown-ups can read; the box says who. A kid cannot see the family conversation, and a grown-up cannot
  write in a kid's.
- **Under the [shared password](/wiki/reference/glossary#shared-password)** nobody is signed in as
  themselves, so the box asks "From" and you pick your name.
- **An admin** is sent from Home to [Setup](/wiki/controls/setup) until an admin is on the family list and a
  model is connected.

## Home, top to bottom

On a wide screen the cards sit in two columns, left then right; on a phone they stack. Admins and parents
see all of these.

| Card | What it shows |
|---|---|
| Greeting | Your name and the day, then one sentence: the next plan, and how many things to do are late |
| The box | Ask, save an idea or set a reminder. Under it, a note while an answer is on its way, or the assistant's last line if it is under a day old, with a link into Chat |
| Next up | The next plan with its time, drive and who it is for, then up to three after it, from the next 60 days. A note says when they come from the saved plans because Google Calendar is not connected or did not answer |
| Just added to Ideas | The four newest ideas, a link to the restaurants, and Add an idea |
| The kids' lists | Each kid's list at a glance, with a count of wishes waiting on you |
| To do | The first four open things to do, with a late count |
| Finish setting up | The steps left, until all are done (admins only) |
| How did it go? | The oldest plan from the last two weeks that nobody has rated, with three faces: Loved it, OK, Not great |
| Vera today | What was spent today, your limit and a usual day, with the assistant's state (not on a phone) |

A kid's Next up shows only plans that name them or everyone, and their To do only their own things.

The pill in the side bar (the top bar on a phone) says how the assistant stands and links to
[Status](/wiki/controls/status). The side bar shows the long wording, the phone the short:

| Shown | Means |
|---|---|
| Ready | It can answer |
| Writing back | A reply is being written in your chat |
| Resting until midnight | The [spending limit](/wiki/reference/glossary#spending-limit) for the day is used up |
| Can't answer right now | A model company is out of credit or refusing its key |
| Can't answer yet | Setup is not finished |

The faces under "How did it go?" run the tool the assistant uses to record how a plan went
([Plans and things to do](/wiki/controls/plans-and-tasks)). The figures under "Vera today" are an
estimate, not your bill ([Spending](/wiki/controls/settings/spending)).

## Chat, top to bottom

1. The title: Chat with the assistant (just Chat when no persona is chosen).
2. For admins and parents, if there are kids, a list of conversations: the family's and each kid's. A
   kid's shows when they last wrote, not what they said. Opening one shows the conversation with no box.
   A kid sees one entry, their own.
3. The room's header and, for admins and parents, whether Telegram is connected.
4. The thread: the latest 60 messages, the day marked where it changes, and "Earlier messages" to go
   back. Under the assistant's answers, admins and parents see what the turn tried to change ("Saved an
   idea", "Remembered something"), even if it was refused. [What Vera knows](/wiki/controls/memory) lists
   what was kept.
5. The box.

Telegram conversations are separate and do not appear here.

## Send a message

1. Type in the box. Enter starts a new line; Ctrl or Cmd with Enter sends.
2. Press Send. The page takes you to Chat and shows your message at once.
3. Wait for the answer, or leave: it is written to the thread either way.

A message may be up to 4,000 characters. By default each goes with the chat's last 20 messages from the last
6 hours, within about 1,500 tokens, so the assistant follows the thread ([Spending](/wiki/controls/settings/spending)).
Slash commands, buttons and voice notes are Telegram's ([Telegram](/wiki/controls/telegram)); the page has
none. A form on the page, such as adding an idea, runs the tool the assistant would, with no model call.

The tab keeps a half-typed message and puts it back when you return. When you are signed in as yourself it
is forgotten once the message arrives; under the shared password the sent words may come back into the
box. It is also forgotten when the tab closes.

## While an answer is being written

The chat answers one message at a time. The box closes, a bubble says the assistant is thinking, and the
page asks again after 3 seconds, then 5, then every 10, up to seven looks. "Check for her answer" is
always there, with "Stop updating this page" beside it while the page is still looking. Anyone else writing in the
same chat gets "Still thinking about the last message" until the answer is in. A kid's chat is their own, so
it never waits on anyone else's.

## When a message fails

Every message that fails shows a red edge and "This one didn't go through".

- With a passing trouble at the model, the message is kept and the answer says it will try again. The retry
  job tries every 5 minutes, up to 3 times by default, and the answer appears when one works
  ([Messages settings](/wiki/controls/settings/messages#when-a-message-cannot-be-answered)).
- If the server restarts mid-answer, the page says the message was interrupted and will be tried again. The
  box stays open and the page rechecks every 30 seconds while you are not typing. Once the retries are used
  up (about 25 minutes at the latest, by default) it says so and puts your words back in the box.
- Some failures are not retried, for example no model key, the day's limit used up, a kid's limit or a turn
  that runs out of steps.

## Limits for kids

A kid has two limits ([Spending](/wiki/controls/settings/spending)). The message count (none by default) counts
only messages a model answered; Home and Chat then say how many are left, and past it the kid is told the
number and to ask tomorrow. The daily share (US$0.25 by default, on from the start) is not shown: when it
is used up, the kid is told kindly to come back tomorrow, with no mention of money.

## Share where I am

Tick **Share where I am with this message** (shown where the browser offers a position). It is off the
first time, then stays as you left it for this browser session, so it may be ticked when you arrive and ask
your phone for its position at once. The position goes with the message and a free map service
(OpenStreetMap) is sent the coordinates to name the place. For the next 3 hours the assistant sees the name and
coordinates with each message you send, here or on Telegram, for "near here" and "open now". A cleanup job
deletes it after a day at most. **The coordinates also go to the model company.** If the browser gives
no position, suggestions start from home.

## The mic

Where the browser has speech recognition and dictation is on, a mic sits beside the box. The words appear in the
box and send nothing until you press Send. The browser sends the sound to its maker, not through
FamilyDB, and it costs nothing. An admin turns it off under [General](/wiki/controls/settings/general).

## What an admin needs to know

- If a message goes unanswered, start at [Status](/wiki/controls/status), which says what is wrong; an admin can open each turn's calls under [Recent activity](/wiki/controls/status/activity).
- Reminders appear in the chat while FamilyDB is running, and in Telegram when it is connected. They are not phone notifications.
- The assistant's name and wording are on [Personality](/wiki/controls/settings/personality).

Developer docs: `src/familydb/web/chat.py`, `src/familydb/channels/web.py`, `src/familydb/web/routes.py` (`home`), and `docs/STYLE.md`, "Page by page".
