# The family and roles

The family list is the root of who may do what in FamilyDB: it says who the bot talks to, who signs in to the page, and which role each person has. This page explains the rules behind the list. To change it, use the [Family page](/wiki/controls/family).

## What a member is

| Part | What it holds |
|---|---|
| Name | 1 to 80 characters. One person per name, ignoring case |
| Role | Admin, parent or kid |
| Channel | A Telegram id, one per person. The page and the console know people by name |
| Switched on or off | A switched-off person is on the list but is treated as a stranger |
| Birthday | Optional. Code works out the age from it |
| Male or female | Optional, set by an admin, used only for kids |

The model never sees a birthday. Code turns it into an age, and the age reaches the model only in a kid's own message (see [Kids](#kids)). Code also uses the birthday to find the next one, for example when a "not this time" on a birthday wish list ends. Every request carries each active member's name and role in the cached family block.

## Who may message the bot

Only somebody on the list, switched on, with a matching id. On Telegram that is the sender's own Telegram id, so each person in a group is checked, not the group. On the page, the chat acts as whoever is signed in, never as a name a form sends.

Anyone else is a stranger. No model is called and the message is not stored. The bot answers in one line that includes their id, so they can pass it to an admin, and records a knock: Telegram name, id, chat and how many times, never what they said. Knocks are kept 30 days, at most 200, and an admin can turn one into a member.

## Roles and permissions

There are three roles. What each may do is one table of permissions in `familydb/roles.py`: sign in, chat, change, own tasks, browse, wish, decide and manage. The table is on [Security and trust](/wiki/security#who-may-do-what); this page does not repeat it.

The idea is that pages ask for a permission, never a role. Each part of the page names the permission it needs, and a template hides what a visitor may not use while the gate refuses it anyway, so a new limit is one change to the table. The bot's tools use the same table. The bot cannot grant a kid's wish on a kid's behalf, because answering needs "decide", and a lookup asked for now is refused to anybody without "change", so a kid's lookups wait for the evening.

## Who signs in

A person signs in if they are switched on, their role may sign in, and they have a password. Passwords are kept as hashes apart from the member record, so a hash never reaches a prompt. An admin gives each other person a starting password, shown once, to replace on first sign-in; until an admin has their own, the family shares one. [Passwords and sessions](/wiki/security/passwords-and-sessions) has the details.

## Why the list is not a tool

A Telegram id on the list is permission to talk to the bot. If a tool could change the list, one message, or a fetched web page talking the model round, could let somebody in. So no tool touches it. The list changes only from the Family page or the command line, through one module of rules, `familydb/family.py`, and by a one-time link an admin makes for one person.

## Rules that keep an admin who can sign in

`family.py` refuses any change that would leave the family without one:

- The list keeps at least one active admin.
- Once any admin has their own password, one active admin who can sign in stays. This is what stops the shared password from coming back. It covers switching off, changing a role, taking off and taking a password away.
- Nobody takes themselves off the list.
- A form drawn before somebody else saved is refused, and so is any change to a person while the bot is answering them.
- A name and a Telegram id each belong to one person, switched-off people included.

## Switch off and take off

Switching somebody off keeps everything. Their sign-in ends at their next click, their Telegram messages are answered as from a stranger, and messages still waiting are given up. Their memories stay in force and their wish lists stay. An admin can switch them back on.

**Taking somebody off for good cannot be undone.** Their name, password, Telegram link, last-known location, memories about them and a kid's wish lists are deleted. What they said and did stays with no name on it: messages, ideas, plans, outcomes, and other things to do. Their private chat is closed down: open things to do and reminders there are cancelled and anything queued for it is not sent.

## Kids

A kid can sign in, read the ideas and plans, chat, keep their own wish lists and tick off their own things to do. A kid does not see the household's pages (memory, Status, this guide, everybody's things to do), settings or the family list, and presents are hidden from every kid.

**The kid line.** Each message from a kid carries one line built by code: name, "a girl", "a boy" or "a kid", and an age if a birthday is set. Code sends age and male or female only in this line. See [Kids' wish lists](/wiki/model/wishes).

**Two limits.** A kid's messages are limited by `kid_daily_messages`, a count of messages a model answered (none by default), and by `kid_daily_spend`, a dollar share of the day (25 cents by default). Each is checked before the model is asked. Past one, the message is kept, given up rather than retried, and answered by a line from code. No model is asked. Both are on [Spending](/wiki/controls/settings/spending).

**Kids never see the workings.** This is the family's decision. Where a kid reads, a line about a key, a model, a dollar limit, an admin, the settings or the logs is said in one of three plain lines: can't answer now, try tomorrow, or type it for me. Where a kid reads means a kid's own chat and any group while a kid is on the list, since code cannot see who is in a group. Admins are still told the cause, and the page hides the workings from anybody without "browse".

**The audience line.** Separately, one line in the current turn tells the model who reads the reply. In a Telegram group, or the page's shared conversation, it says everyone there reads the reply, adding "kids among them" when an active kid is on the list. A private chat gets none. The line is cautious: a kid talks in their own conversation on the page, yet the shared one still carries the note. Staying suitable for kids is an instruction in the product spec, which the evals check.

Developer docs: `src/familydb/family.py` (module notes), `roles.py`, `audience.py`, `store/members.py` (`POINTING_AT`), `store/knocks.py`, `pipeline.py` (`_stranger`, `_over_daily_number`), `voice.py` (`PLAIN`), and `docs/DESIGN.md`, "Decisions" (the rows "Family list", "Taking somebody off" and "What a kid sees of the workings") and "Security".
