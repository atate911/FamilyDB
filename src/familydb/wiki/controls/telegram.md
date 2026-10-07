# Telegram: commands and buttons

Chat is the main thing on Telegram: say what you want, in your own words, and the assistant answers. This page
covers the parts that are not chat: five commands, and the buttons under some messages. Commands and button taps are
done by code, with no model call, so they still answer when the model is down or the day's spending limit is used up.
(`/lookup` is the one exception in spirit: it only queues lookups, and those are paid model work that waits if the
model is down or the limit is spent.)

## Who may use it

Only people on the family list. Anyone else who writes to the bot is recorded as a "knock" and gets a short line that
includes their Telegram id. Their message is never sent to a model, and in a group a stranger is answered only when they
address the bot directly. Someone else who taps a button gets a private "Only the family can use these" and is not
recorded.

A knock shows under "Waiting to be let in" on the Family page and in the setup, with the person's name, handle and
Telegram id and how many times they wrote (never what they wrote). An admin adds them from there with a name and a role.
Knocks are kept for 30 days, and one disappears once the person is added. In a group, a stranger's message that is not
addressed to the bot is recorded only when "answer only when mentioned" is off.

## Commands

The five commands are in Telegram's command menu, which the bot sets up for itself; `/today@BotName` works in a group as
well as `/today`. Each command and its answer are stored as messages, so a later conversation knows what was shown. The
heading above each answer is one of the assistant's lines, which the family can reword on the
[Personality and family](/wiki/controls/settings/personality#what-she-says-unasked) page.

| Command | What it answers |
|---|---|
| `/today` | What is on today, in time order: calendar events (or the saved plans, with a note saying so, if Google Calendar is not connected or did not answer) and the reminders and due times of this chat's things to do that fall today. It leaves out overdue items |
| `/week` | The next seven days, one line a day, from the calendar or saved plans only; no things to do |
| `/tasks` | The open things to do asked for in this chat, with their numbers, owner, next reminder, due time, repeat and preferred window. The first 12; a note says how many more are on the To do page |
| `/now` | What could start right now: up to five ideas that fit the time, the forecast, opening hours and travel, with the reason for each ("maybe" on uncertain ones), up to three that are ruled out and why, a "Travel from …" line only when it is not counted from home (for example from a shared location), and a "Not checked: …" line naming any check it skipped. It uses what is already known and searches the web for nothing |
| `/lookup` | Asks for the ideas waiting to be looked up to be looked up on the next run, in a few minutes, and not in the evening. It says if lookups are off or if none are waiting. Only parents and admins can use it: for a kid it replies that nothing is waiting, and their ideas are looked up in the evening as usual |
| `/start` | The assistant's introduction (not in the menu, and not stored) |

`/today` and `/tasks` show the things to do that were asked for in this chat, and a reminder may go to its owner's own chat
instead (see below). Things to do about a present are left out of both, and `/now` never offers a present. `/today` and
`/week` list calendar entries and plans as they are, including a plan made for a present idea.

If you send a sticker, GIF, video, contact, poll or a file that is not an image with no words, the assistant says it cannot
open that kind of message; in a group it says so only when the message is sent to the bot. With words it is treated as a
normal message, and images go to the photo handler. When someone on the family list adds the bot to a group, it introduces
itself there; if it was added by someone who is not on the list, it says nothing.

### Linking a person's Telegram

An admin can make a one-time link on the person's page on Family. It needs the bot connected, is shown once, is valid for 24
hours, works once, and replaces any earlier link. The person opens it on their phone, and pressing Start in a private chat
with the bot links their Telegram to their place on the list. A used or expired link, or one for someone switched off, says
"That link no longer works" (and is a knock if the person is a stranger); a Telegram that is already on the list is told whose
it is.

## Buttons

Some messages the bot sends unasked carry buttons. A tap does what saying so in the chat would, as the person who tapped,
with no model. When it does something, the message gains a note saying who did what and loses its buttons. A tap that is
refused, or a Later, only shows the person who tapped a short pop-up, and the buttons stay.

| Under | Buttons | What each does |
|---|---|---|
| A reminder, or a nudge to do something kept for a part of the week | **✓ Done**, **In an hour**, **Tomorrow** | Done marks the thing done (a repeating one comes round again, and the note says when). The other two move the reminder to an hour, or 24 hours, after the tap. A kid can tap only on their own things to do |
| A follow-up on a plan that was made for an idea | **Yes, again**, **Not again**, **Didn't go** | Yes, again and Not again record how it went and whether the family would do it again. Didn't go records nothing about how it went and puts the idea back on the list |
| A kid's ask, sent privately to each parent | **Yes!**, **Not this time**, **Later** | Only a parent can answer. Yes! grants it and Not this time declines it. Later does nothing but show "left for later", and the buttons stay. It is sent when an ask is flagged as inappropriate, or when the kid presses Ask a parent |

A tap is checked before anything happens: the person must be on the family list, and what the button sends back must be a
known action on a real thing. The same tap delivered twice is done once, and a tap on something already dealt with does
nothing and says so. A tap that goes ahead is kept as a message, so what it changed can be traced; refused and stale taps and
Later are not.

## Where each message goes

With "Send what's for one person to their own chat" on (it is by default), a reminder, a note or a follow-up that is for one
person goes to that person's own chat with the bot once they have written to it there, and not to the group. A plain "saved" in
a group is a 👌 reaction that buzzes nobody, or a silent ✓ reply where reactions are off. How the bot behaves in groups, and
the pause before it answers, are settings on the [Connections](/wiki/controls/settings/connections) page.

Developer docs: `src/familydb/commands.py` and `src/familydb/buttons.py` (their module notes), and `docs/DESIGN.md`, "Group vs
DM".
