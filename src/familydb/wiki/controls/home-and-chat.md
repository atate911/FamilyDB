# Home and Chat

Home is where you ask the assistant something and see what is coming up, what is left to do and what
was added lately. Chat is the conversation itself, where the answers arrive. They share one
conversation: a message sent from Home's box lands in Chat, and the page takes you there. Nothing
you read on either page makes a model call, but every message you send does, and it is paid for.

## Who sees what

Everyone signed in sees Home and may chat. Who may do the rest is in
[who may do what](/wiki/security#who-may-do-what).

- **Admins and parents** share one family conversation, and Home shows the whole household.
- **A kid** has a shorter Home: their own plans, wish list and things to do, and a box that
  goes to their own chat with the assistant. The kid's box says who can read that chat. A kid
  cannot see the family conversation, and a grown-up cannot write in a kid's.
- **Under the [shared password](/wiki/reference/glossary#shared-password)** nobody is signed in as
  themselves, so the box asks "From" and you pick your name.
- **An admin** is sent from Home to [Setup](/wiki/controls/setup) until somebody is on the
  family list and a model is connected.

## Home, top to bottom

On a wide screen the cards sit in two columns, left then right; on a phone they stack.

| Card | What it shows |
|---|---|
| Greeting | Your name and the day, then one sentence: the next plan, and how many things to do are late |
| The box | Ask, save an idea or set a reminder. Under it, a note while an answer is on its way, or the assistant's last line if it is under a day old, with a link into Chat |
| Next up | The next plan with its time, drive and who it is for, then up to three after it, from the next 60 days. A note says when they come from the saved plans rather than Google Calendar |
| Just added to Ideas | The four newest ideas, a link to the restaurants, and Add an idea (if you may change things) |
| The kids' lists | Each kid's list at a glance, with a count of wishes waiting on you (admins and parents) |
| To do | The first four open things to do, with a late count. A kid sees only their own |
| Finish setting up | The steps left, until they are all done (admins) |
| How did it go? | The oldest plan from the last two weeks that nobody has rated, with three faces: Loved it, OK, Not great |
| Vera today | What was spent today, your limit and a usual day, with the assistant's state (not on a phone) |

The pill in the side bar (the top bar on a phone) says how the assistant stands, and links to
[Status](/wiki/controls/status):

| Shown | Means |
|---|---|
| Ready | She can answer |
| Writing back | A reply is being written in your chat |
| Resting until midnight | The [spending limit](/wiki/reference/glossary#spending-limit) for the day is used up |
| Can't answer right now | A model company is out of credit or refusing its key |
| Can't answer yet | Setup is not finished |

The faces under "How did it go?" run the same tool the assistant uses to record how a plan went
([Plans and things to do](/wiki/controls/plans-and-tasks)). The figures under "Vera today" are an
estimate, not your bill ([Spending](/wiki/controls/settings/spending)).

## Chat, top to bottom

1. The title: Chat with the assistant (just Chat when no persona is chosen).
2. If there are kids, a list of conversations: the family's and each kid's. A kid's shows when
   they last wrote, not what they said. Opening one shows the conversation with no box.
3. The room's header, with whether Telegram is connected.
4. The thread: the latest 60 messages, with the day marked where it changes and "Earlier messages"
   to go back. Under the assistant's answers, a grown-up sees what the turn did ("Saved an idea",
   "Remembered something", which [What Vera knows](/wiki/controls/memory) lists).
5. The box, with "Writing as" your name.

Telegram conversations are separate and do not appear here.

## Send a message

1. Type in the box. Enter starts a new line; Ctrl or Cmd with Enter sends.
2. Press Send. The page takes you to Chat and shows your message at once.
3. Wait for the answer, or leave: it is written to the thread either way.

A message may be up to 4,000 characters. Each one goes with the last 20 messages of this chat from the
last 6 hours, so the assistant follows the thread. Slash commands, buttons and voice notes are Telegram's
([Telegram](/wiki/controls/telegram)); the page has none. A form on the page, such as adding an idea, runs
the same tool the assistant would. Sending is the only thing here that asks a model.

If you leave a message half typed, the tab keeps it and puts it back when you return. It is forgotten
once the message arrives or the tab closes.

## While an answer is being written

The chat answers one message at a time. The box closes, a bubble says she is thinking, and the page asks for
the answer again after 3 seconds, then 5, then every 10, and stops after seven looks, leaving a link,
"Check for her answer". Anyone else writing in the same chat gets "Still thinking about the last message" until the
answer is in. A kid's chat is their own, so it never waits on anyone else's.

## When a message fails

- If the model has a passing trouble, the message is kept, the answer says it will try again, and the
  message shows a red edge and "This one didn't go through". The retry job tries again every 5 minutes, up
  to 3 times, and its answer appears when one works
  ([Messages settings](/wiki/controls/settings/messages#when-a-message-cannot-be-answered)).
- If the server restarts mid-answer, the page says the message was interrupted and will be tried again. If
  nothing has answered after about 25 minutes with the defaults, the page says so and puts your
  words back in the box to send again.
- Some failures are not retried, for example no model key, the day's limit used up, or a turn that runs
  out of steps.

## Kids and limits

A kid's message count for the day is set on [Spending](/wiki/controls/settings/spending) (0, no limit, by
default). Home and Chat then say how many are left. Past it, the kid is told the number and to ask
tomorrow. Only messages a model answered count.

## Share where I am

Tick **Share where I am with this message** (shown only where the browser offers a position; off until you
tick it). Your phone's position goes with that message, a free map service names the place, and for the next 3
hours the assistant sees the name and coordinates with each message you send, here or on Telegram. A
cleanup job deletes it after a day at most. **The coordinates go to the model company with your message.** If
the browser gives no position, suggestions start from home.

## The mic

Where the browser has speech recognition, a mic sits beside the box. The words appear in the box and send
nothing until you press Send. The browser sends the sound to its maker, not through FamilyDB, and it costs
nothing. An admin turns it off under [General](/wiki/controls/settings/general).

## What an admin needs to know

- If a message goes unanswered, start at [Status](/wiki/controls/status), where you can open each turn's calls.
- Reminders appear in the chat while FamilyDB is running, and in Telegram when it is connected. They are not phone notifications.
- The assistant's name and wording are on [Personality](/wiki/controls/settings/personality).

Developer docs: `src/familydb/web/chat.py`, `src/familydb/channels/web.py`, `src/familydb/web/routes.py` (`home`), and `docs/STYLE.md`, "Page by page".
