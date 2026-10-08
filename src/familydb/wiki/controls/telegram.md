# Telegram: commands and buttons

Chat is the main thing on Telegram: say what you want, in your own words, and the assistant answers. This page covers what is not chat: six commands (five in Telegram's menu, plus `/start`) and the buttons under some messages. To create and connect the Telegram bot, see [Connections](/wiki/controls/settings/connections#telegram). What Telegram receives is on [Telegram as a service](/wiki/boundaries/telegram), and how a message is read is on [Telegram: the message loop](/wiki/behavior/telegram-loop).

Commands and button taps are done by code, with no model call, so they still answer when the model is down or the day's spending limit is used up. `/lookup` only queues lookups, and those are paid model work that waits if the model is down or the limit is spent.

## Who may use it

Only people on the family list. Anyone else who writes to the Telegram bot gets a short line that includes their Telegram id, and their message never reaches a model ([Who may message the bot](/wiki/model/family-and-roles#who-may-message-the-bot)). In a group, a stranger is answered only when they address the bot directly. A stranger who taps a button gets a private "Only the family can use these". An admin adds a stranger from the Family page ([Link a Telegram](/wiki/controls/family#link-a-telegram)).

## Commands

The five menu commands are set up by FamilyDB itself; `/today@BotName` works in a group as well as `/today`. Each command and its answer are stored as messages, so a later conversation knows what was shown. The heading above each answer is one of the assistant's lines, which the family can reword on [Personality and family](/wiki/controls/settings/personality#what-she-says-unasked).

| Command | What it answers |
|---|---|
| `/today` | What is on today, in time order: calendar events (or the saved plans, with a note saying so, if Google Calendar is not connected or did not answer) and the reminders and due times of this chat's things to do that fall today. It leaves out overdue items |
| `/week` | The next seven days, one line a day, from the calendar or saved plans only; no things to do |
| `/tasks` | The open things to do asked for in this chat, with their numbers, owner, next reminder, due time, repeat and preferred window. The first 12; a note says how many more are on the To do page |
| `/now` | What could start right now: up to five ideas that fit the time, the forecast, opening hours and travel, with the reason for each ("maybe" on uncertain ones), up to three that are ruled out and why, a "Travel from ..." line only when it is not counted from home (for example from a [shared location](/wiki/model/location)), and a "Not checked: ..." line naming any check it skipped. It uses what is already known and searches the web for nothing |
| `/lookup` | Asks for the ideas waiting to be looked up to be looked up on the next run, not in the evening. It says if lookups are off or if none are waiting. Only parents and admins can use it: a kid is told that nothing is waiting, and their ideas are looked up in the evening as usual |
| `/start` | The assistant's introduction (not in the menu, and not stored) |

`/today` and `/tasks` show the things to do that were asked for in this chat, and a reminder may go to its owner's own chat instead ([Where each message goes](#where-each-message-goes)). Things to do about a present are left out of both, and `/now` never offers a present. `/today` and `/week` list calendar entries and plans as they are, including a plan made for a present idea ([Telegram commands show presents](/wiki/reference/known-limits#telegram-commands-show-presents)).

A sticker, GIF, video, contact, poll or a file that is not an image, sent with no words, gets "I can't open that kind of message"; in a group the assistant says so only when the message is sent to it. With words it is treated as a normal message, and images go to the photo reader. A voice note in a group follows the same rule as text, and a photo is read only when addressed ([the message loop](/wiki/behavior/telegram-loop)). When someone on the family list adds the Telegram bot to a group, the assistant introduces itself there; if someone not on the list adds it, it says nothing.

To link a person's Telegram, an admin makes a one-time link on [Family](/wiki/controls/family#link-a-telegram).

## Buttons

Some messages FamilyDB sends unasked carry buttons. A tap does what saying so in the chat would, as the person who tapped, with no model. When it does something, the message gains a note saying who did what and loses its buttons. A tap that is refused, or a Later, only shows the person who tapped a short pop-up, and the buttons stay.

| Under | Buttons | What each does |
|---|---|---|
| A reminder, or a nudge to do something kept for a part of the week | **✓ Done**, **In an hour**, **Tomorrow** | Done marks the thing done (a repeating one comes round again, and the note says when). In an hour moves the reminder to 1 hour after the tap, and Tomorrow to 24 hours after the tap, not to tomorrow morning. A kid can tap only on their own things to do |
| A follow-up on a plan that was made for an idea | **Yes, again**, **Not again**, **Didn't go** | Yes, again and Not again record how it went and whether the family would do it again. Didn't go records nothing about how it went and puts the idea back on the list |
| A kid's ask, sent privately to each parent | **Yes!**, **Not this time**, **Later** | Only a parent can answer. Yes! grants it and Not this time declines it. Later does nothing but show "left for later", and the buttons stay. It is sent when an ask is flagged as inappropriate, or when the kid presses Ask a parent |

FamilyDB checks a tap before anything happens: the person must be on the family list, and what the button sends back must be a known action on a real thing. The same tap delivered twice is done once, and a tap on something already dealt with does nothing and says so. A tap that goes ahead is kept as a message, so what it changed can be traced. Refused and stale taps and Later are not kept.

## Where each message goes

With "Send what's for one person to their own chat" (`private_when_personal`) on, which it is by default, a reminder, a note or a follow-up that is for one person goes to that person's own chat with the Telegram bot once they have written to it there, and not to the group. A plain "saved" in a group is a 👌 reaction that buzzes nobody, or a silent ✓ reply where reactions are off. How the assistant behaves in groups, and the pause before it answers, are settings on [Connections](/wiki/controls/settings/connections#in-a-telegram-group).
