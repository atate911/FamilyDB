# Telegram: commands and buttons

Chat is the main thing on Telegram: say what you want, in your own words, and the assistant answers.
This page covers the parts that are not chat: five commands and the buttons under some messages. All
of them are done by code, with **no model call**, so they cost nothing and still work when the model
is down or the day's spending limit is used up.

## Who may use it

Only people on the family list. Anyone else who writes to the bot, or taps a button, gets a short line
and is recorded as a "knock", which shows on the Family and setup pages so an admin can let them in. A
stranger's message is never sent to a model. In a group, a stranger is answered only when they address
the bot directly.

## Commands

The five commands are offered in Telegram's command menu, which the bot sets up for itself. Typing
`/today@BotName` in a group works as well as `/today`. Each command and its answer is stored as a message,
so a later conversation knows what was shown. The heading above each answer is one of the assistant's lines,
which the family can reword on the
[Personality and family](/wiki/controls/settings/personality#what-she-says-unasked) page.

| Command | What it answers |
|---|---|
| `/today` | What is on today, in time order: events from the family calendar (or the saved plans, with a note saying so, if Google Calendar is not connected or did not answer) and the reminders and due times of this chat's things to do |
| `/week` | The next seven days, one line a day |
| `/tasks` | This chat's open things to do, with their numbers, owner, next reminder, due time, repeat and preferred window. The first 12; a note says how many more are on the page's To do list |
| `/now` | What could start right now: up to five ideas that fit the time, the forecast, opening hours and travel, with the reason for each, up to three that are ruled out and why, where travel is counted from, and any check it could not make. It uses what is already known and searches the web for nothing |
| `/lookup` | Asks for the ideas waiting to be looked up to be looked up on the next run, in a few minutes, and not in the evening. It says if lookups are off or if none are waiting. A kid's ideas wait for the evening |
| `/start` | The assistant's introduction. Opened from an admin's link, it first links the sender's Telegram to the person the link was made for (see the Family page) |

A chat sees only the things to do asked for in it, as only it gets their reminders, and presents are
kept from the people they are a surprise for.

If you send a sticker, a file or a video with no words, the assistant says it cannot read it. When someone
on the family list adds the bot to a group, it introduces itself there; if it was added by someone who is
not on the list, it says nothing.

## Buttons

Some messages the bot sends unasked carry buttons. A tap does what saying so in the chat would, as the
person who tapped, with no model, and the message then shows who did what and loses its buttons.

| Under | Buttons | What each does |
|---|---|---|
| A reminder | **✓ Done**, **In an hour**, **Tomorrow** | Done marks the thing done (a repeating one comes round again, and the reply says when). The other two move the reminder by an hour, or by a day, from now |
| A follow-up on a plan | **Yes, again**, **Not again**, **Didn't go** | Records how it went and whether the family would do it again. Didn't go puts the idea back as an idea |
| A kid's ask that the bot turned away | **Yes!**, **Not this time**, **Later** | Only a parent can answer. Yes! grants it and Not this time declines it; Later only leaves a note |

A tap is checked before anything happens: the person must be on the family list, and what the button sends
back must be a known action on a real thing. The same tap delivered twice is done once, and a tap on
something already dealt with does nothing and says so. A tap is kept as a message, so what it changed can
be traced.

## Where each message goes

In a group, a reminder or note that is for one person goes to that person's own chat with the bot once they
have written to it there, and not to the group; a plain "saved" in a group is a 👌 reaction that buzzes nobody.
How the bot behaves in groups, and the pause before it answers, are settings on the
[Connections](/wiki/controls/settings/connections) page.

Developer docs: `src/familydb/commands.py` and `src/familydb/buttons.py` (their module notes), and
`docs/DESIGN.md`, "Group vs DM".
