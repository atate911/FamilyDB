# Now and Chat

Now is the first screen: the box to tell the assistant something, then whatever is waiting on you, her picks for right now, and today and tomorrow in one line each. Chat is the conversation behind the box, where every message and answer is kept. Reading either page makes no model call; nearly every message you send does, and it is paid for.

The box is the same on every page of the family's: Now, Eat, Do, Week, Kids, Soon, Lists, Did and each thing's own page. A message sent from any of them lands in your conversation, and the answer comes back to the page you sent it from.

## Who sees what

Everyone signed in sees Now and may chat ([Roles and permissions](/wiki/model/family-and-roles#roles-and-permissions)).

- **Admins and parents** share one family conversation, and Now shows the whole household: what is waiting on a grown-up, everybody's late things, her picks for everyone.
- **A kid** has her own Now (the box, her things to do, My list, her picks and today and tomorrow) and her own conversation, which grown-ups can read; a line under the box says who. A kid cannot see the family conversation, and a grown-up cannot write in a kid's. Her row of pages is Now, Do, My week and My list.
- **Under the [shared password](/wiki/reference/glossary#shared-password)** nobody is signed in as themselves, so the box asks "From" and you pick your name.
- **An admin** is sent from Now to [Setup](/wiki/controls/setup) until an admin is on the family list and a model is connected.

## Now, top to bottom

| Part | What it shows |
|---|---|
| The box | Ask, save an idea or set a reminder. Under it, what the last message brought back (below) |
| The line | The day and the time, then how the day stands: "Free this evening", "Swim lesson 4:30 pm" |
| Finish setting up | The steps left, for admins only, until they are done |
| Her questions | At most three things waiting on you: a plan to rate (Loved it, OK, Not great), a kid's ask to answer (Yes, Not this time), a kid's pitch for an outing (See it, or Later, which rests it for a week) |
| On your plate | What is late or due today, each with its tick; a kid sees all of her own things to do |
| What about… | Her picks, chosen ahead by code, with when they were chosen. "Different ones" asks her for others, which is a message like any other |
| My list | A kid's wishes, with the countdowns to Christmas and her birthday |
| Today, Tomorrow | One line each, linking to the day |

When nothing waits on you, Now says so ("Nothing needs you.") and gets on with the picks.

### Her picks

The picks under **What about…** are made ahead, never while you look: an hourly job chooses up to four for right now and, from Thursday, up to six for the weekend, from the suggestion engine's own ranking (what fits the free time, who is coming, the weather, what rested long enough). The job runs between 8 am and 10 pm and makes no model call. A plan she suggests shows in pencil on This week too. The job can be switched off on [AI model](/wiki/controls/settings/ai-model); on the server, `familydb picks --now` makes a fresh set.

The pill in the menu (behind your picture) says how the assistant stands and links to Status. Its words are on [Status](/wiki/controls/status#the-pill-and-the-verdict).

## What comes back under the box

Send a message and the page you sent it from shows, under the box:

- **On its way.** Her screen and "thinking" while the answer is being written. The page asks again after 3 seconds, then 5, then every 10, up to seven looks, with scripts or without.
- **A receipt**, when the message changed something: one line of what she did ("Saved #12 Kenji's Ramen", "Reminder set for Tuesday"), with **Undo** beside it for the one change the message made, and **Earlier** to the thread.
- **Her reply**, when the message only asked: your words, then hers, on a sheet over the page, with Undo where one applies and a pointer to the page her answer is about.
- **"Vera wrote something"**, on any page, when she has written since you last opened the thread, so somebody who uses only the page knows.

Undo takes back the last change while the record is still as that change left it, once, for whoever made it or may change things.

## The box on a destination

On Eat, Do, Week, Kids, Soon, Lists and Did the box says what it is about ("about: This week") and the message goes to her with that scope in front of it, so "anything cheaper?" on Eat is a question about restaurants. On a thing's own page the box is about that thing, and three quick sentences under it fill the box with the usual asks ("Plan it for this weekend", "Move it to Saturday"); nothing is sent until you press Send.

## Chat, top to bottom

Chat is the thread behind the box. From the top: the conversations (for admins and parents when there are kids: the family's and each kid's, as a row of pills), the room's header, the thread and the box. A kid sees one conversation, her own, and the list shows when a kid last wrote, not what she said. Opening a kid's conversation shows her words, with no box, although the list itself withholds them.

The thread holds the latest 60 messages, with the day marked where it changes and "Earlier messages" to go back. Under the assistant's answers, admins and parents see what the message tried to change ("Saved an idea", "Remembered something"), even if it was refused. Telegram conversations are separate and do not appear here.

## Send a message

Type in the box (Enter starts a new line; Ctrl or Cmd with Enter sends) and press Send. The page shows your message at once. Wait for the answer, or leave: it is written to the thread either way. A message may be up to 4,000 characters. Each goes with the chat's recent messages ([Spending](/wiki/controls/settings/spending)). Slash commands, buttons and voice notes are Telegram's ([Telegram](/wiki/controls/telegram)); the Chat page's box also takes a photo. A form on the page, such as ticking a thing off, runs the tool the assistant would, with no model call.

The tab keeps a half-typed message and puts it back when you return. Signed in as yourself, it is forgotten once the message arrives; under the shared password the sent words may come back into the box. It is also forgotten when the tab closes.

## While an answer is being written

The chat answers one message at a time. The box closes while it does, and anyone else writing in the same chat gets "Still thinking about the last message" until the answer is in. A kid's chat never waits on anyone else's.

## When a message fails

A failed message shows a red edge and "This one didn't go through". The page has no retry link: the retry job tries again by itself ([When a message cannot be answered](/wiki/controls/settings/messages#when-a-message-cannot-be-answered)).

- After a passing trouble at the model, the answer says it will try again, and appears when a retry works.
- If the server restarts mid-answer, the page says the message was interrupted and will be tried again. The box stays open, and the page rechecks every 30 seconds while you are not typing. When the retries are used up, it says so and puts your words back in the box.
- No model key, the day's limit used up, a kid's limit, or an answer that runs out of steps are not retried.

## Limits for kids

A kid has two limits, a message count and a daily share. What each is, and what a kid is told at each, is on [Kids](/wiki/model/family-and-roles#kids). The values are on [Spending](/wiki/controls/settings/spending#the-daily-limit). Her Now says how many messages she has left today.

## Share where I am

Tick **Share where I am with this message** to let the assistant use your position for "near here" and "open now". It starts unticked and remembers your last choice while you stay signed in on that browser, so check it before you send. For the next 3 hours the assistant sees the place name and coordinates with each message you send, here or on Telegram. **The coordinates also go to the model company.** If the browser gives no position, suggestions start from home. What is kept, who sees it and how to stop is on [Shared location](/wiki/model/location).

## The mic

Where the browser has speech recognition and dictation is on, a mic sits in the box. An admin turns it on or off under [General](/wiki/controls/settings/general). The browser sends the sound to its maker, never through FamilyDB.

## What an admin needs to know

- If a message goes unanswered, start at [Status](/wiki/controls/status). Each message's calls are under [Recent activity](/wiki/controls/status/activity).
- Reminders appear in the chat while FamilyDB is running, and in Telegram when it is connected ([How a reminder is delivered](/wiki/model/tasks-and-reminders#how-a-reminder-is-delivered)).
- The assistant's name and wording are on [Personality and family](/wiki/controls/settings/personality).
