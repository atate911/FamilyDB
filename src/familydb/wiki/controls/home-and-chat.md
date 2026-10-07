# Home and Chat

Home is where you ask the assistant something and see what is coming up and what is left to do. Chat is the conversation itself, where the answers arrive. They share one conversation: a message sent from Home's box lands in Chat. Reading either page makes no model call. Nearly every message you send does, and it is paid for.

## Who sees what

Everyone signed in sees Home and may chat ([Roles and permissions](/wiki/model/family-and-roles#roles-and-permissions)).

- **Admins and parents** share one family conversation, and Home shows the whole household.
- **A kid** has a shorter Home (the box, Next up for you, My list and My to-dos) and their own chat, which grown-ups can read; the box says who. A kid cannot see the family conversation, and a grown-up cannot write in a kid's.
- **Under the [shared password](/wiki/reference/glossary#shared-password)** nobody is signed in as themselves, so the box asks "From" and you pick your name.
- **An admin** is sent from Home to [Setup](/wiki/controls/setup) until an admin is on the family list and a model is connected.

## Home, top to bottom

Cards sit in two columns on a wide screen and stack on a phone. Admins and parents see all of these.

| Card | What it shows |
|---|---|
| Greeting | Your name and the day, then the next plan and how many things to do are late |
| The box | Ask, save an idea or set a reminder. Under it, a note while an answer is on its way, or the assistant's last line if it is under a day old |
| Next up | The next plan with its time, drive and who it is for, then up to three after it, from the next 60 days. A note says when they come from saved plans because Google Calendar is not connected or did not answer |
| Just added to Ideas | The four newest ideas, a link to the restaurants, and Add an idea |
| The kids' lists | Each kid's list at a glance, with a count of wishes waiting on you |
| To do | The first four open things to do, with a late count |
| Finish setting up | The steps left (admins only) |
| How did it go? | The oldest plan from the last 2 weeks that nobody has rated, with three faces: Loved it, OK, Not great |
| Vera today | What was spent today (estimated), your limit and a usual day, with the assistant's state (not on a phone). The card carries the assistant's name |

A kid's Next up shows only plans that name them or everyone, and their To do only their own things.

The pill in the side bar (the top bar on a phone) says how the assistant stands and links to Status. Its words are on [Status](/wiki/controls/status#the-pill-and-the-verdict).

## Chat, top to bottom

Chat shows, from the top: a list of conversations (for admins and parents when there are kids: the family's and each kid's), the room's header, the thread and the box. A kid sees one conversation, their own, and the list shows when a kid last wrote, not what they said. Opening a kid's conversation shows their words, with no box, although the list itself withholds them.

The thread holds the latest 60 messages, with the day marked where it changes and "Earlier messages" to go back. Under the assistant's answers, admins and parents see what the message tried to change ("Saved an idea", "Remembered something"), even if it was refused. Telegram conversations are separate and do not appear here.

## Send a message

Type in the box (Enter starts a new line; Ctrl or Cmd with Enter sends) and press Send. The page takes you to Chat and shows your message at once. Wait for the answer, or leave: it is written to the thread either way. A message may be up to 4,000 characters. Each goes with the chat's recent messages ([Spending](/wiki/controls/settings/spending)). Slash commands, buttons and voice notes are Telegram's ([Telegram](/wiki/controls/telegram)). A form on the page, such as adding an idea, runs the tool the assistant would, with no model call.

The tab keeps a half-typed message and puts it back when you return. Signed in as yourself, it is forgotten once the message arrives; under the shared password the sent words may come back into the box. It is also forgotten when the tab closes.

## While an answer is being written

The chat answers one message at a time. The box closes, a bubble says the assistant is thinking, and the page asks again after 3 seconds, then 5, then every 10, up to seven looks. "Check for her answer" is always there, with "Stop updating this page" beside it while the page is still looking. Anyone else writing in the same chat gets "Still thinking about the last message" until the answer is in. A kid's chat never waits on anyone else's.

## When a message fails

A failed message shows a red edge and "This one didn't go through". The page has no retry link: the retry job tries again by itself ([When a message cannot be answered](/wiki/controls/settings/messages#when-a-message-cannot-be-answered)).

- After a passing trouble at the model, the answer says it will try again, and appears when a retry works.
- If the server restarts mid-answer, the page says the message was interrupted and will be tried again. The box stays open, and the page rechecks every 30 seconds while you are not typing. When the retries are used up, it says so and puts your words back in the box.
- No model key, the day's limit used up, a kid's limit, or an answer that runs out of steps are not retried.

## Limits for kids

A kid has two limits, a message count and a daily share. What each is, and what a kid is told at each, is on [Kids](/wiki/model/family-and-roles#kids). The values are on [Spending](/wiki/controls/settings/spending#the-daily-limit).

## Share where I am

Tick **Share where I am with this message** to let the assistant use your position for "near here" and "open now". It starts unticked and remembers your last choice while you stay signed in on that browser, so check it before you send. For the next 3 hours the assistant sees the place name and coordinates with each message you send, here or on Telegram. **The coordinates also go to the model company.** If the browser gives no position, suggestions start from home. What is kept, who sees it and how to stop is on [Shared location](/wiki/model/location).

## The mic

Where the browser has speech recognition and dictation is on, a mic sits beside the box. An admin turns it on or off under [General](/wiki/controls/settings/general). The browser sends the sound to its maker, never through FamilyDB.

## What an admin needs to know

- If a message goes unanswered, start at [Status](/wiki/controls/status). Each message's calls are under [Recent activity](/wiki/controls/status/activity).
- Reminders appear in the chat while FamilyDB is running, and in Telegram when it is connected ([How a reminder is delivered](/wiki/model/tasks-and-reminders#how-a-reminder-is-delivered)).
- The assistant's name and wording are on [Personality and family](/wiki/controls/settings/personality).
