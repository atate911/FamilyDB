# The family and roles

The family list says who the assistant talks to, who signs in to the web page, and which role each person has. Everything else about who may do what follows from it. To change the list, use [Family](/wiki/controls/family).

## What a member is

A member is a name (1 to 80 characters, one person per name, ignoring case) and a role: admin, parent or kid. A member may also have a Telegram id (one per person), a birthday and, for a kid only, male or female, which an admin sets. A person who is switched off stays on the list but is treated as a stranger.

The model never sees a birthday. Code turns it into an age, and the age reaches the model only in a kid's own message (see [Kids](#kids)). Code also uses the birthday to find the next one, for example when a "not this time" on a birthday wish ends. Every request carries each active member's name and role in the fixed start of the request.

## Who may message the bot

Only somebody on the list, switched on, with a matching id. On Telegram that is the sender's own Telegram id, so each person in a group is checked, not the group. On the web page, the chat acts as whoever is signed in, never as a name a form sends.

Anyone else is a stranger. No model is asked and the message is not stored. FamilyDB answers in one line that includes their id, so they can pass it to an admin, and records a knock: Telegram name, id, chat and how many times, never what they said. An admin can turn a knock into a member; [Family](/wiki/controls/family#link-a-telegram) says how long knocks are kept.

## Who signs in

A person signs in if they are switched on, their role may sign in, and they have a password. Passwords are kept as [hashes](/wiki/reference/glossary#hash) apart from the member record, so a hash never reaches a prompt. An admin gives each other person a starting password, shown once, to replace on first sign-in. Until an admin has their own, the family shares one. [Passwords and sessions](/wiki/security/passwords-and-sessions) has the details.

## Roles and permissions

There are three roles and one table of permissions. Each part of the web page names the permission it needs, a template hides what a visitor may not use, and the gate refuses it anyway. A new limit is one change to the table, never a check on a role.

| Permission | What it allows | Admin | Parent | Kid |
|---|---|---|---|---|
| sign in | Sign in, and read the ideas and plans | yes | yes | yes |
| chat | Talk to the assistant on the web page | yes | yes | yes |
| change | Add and change ideas, plans and things to do | yes | yes | no |
| own tasks | Tick off or change your own things to do | yes | yes | yes |
| browse | The household's pages: What Vera knows, Status, this guide, everybody's things to do | yes | yes | no |
| wish | Keep your own wish lists | yes | yes | yes |
| decide | See every kid's wishes and answer them | yes | yes | no |
| manage | Settings, Setup and Family | yes | no | no |

The table covers the web page's forms. In chat, a kid can add ideas and remember things, and keep their own wishes and things to do. Editing an idea, saying how a plan went, and making, moving or cancelling a plan or calendar event need the change permission in chat too, and are refused to a kid. Lookups on demand and other people's things to do are held back as well. What a stolen sign-in gives away is on [Trust and threat model](/wiki/security/model#what-a-sign-in-guards), and the plain statement is under [Known limits](/wiki/reference/known-limits#chat-tools-check-only-some-roles).

## Why the list is not a tool

A Telegram id on the list is permission to talk to the assistant. If a tool could change the list, one message, or a fetched web page talking the model round, could let somebody in. So no tool touches it. The list changes only on Family, from the command line, or by a one-time link an admin makes for one person. Using that link clears the person's birthday and male or female ([Known limits](/wiki/reference/known-limits#a-telegram-link-clears-birthday-and-gender)).

## Rules that keep an admin who can sign in

The list always keeps one active admin. Once any admin has their own password, one active admin who can sign in stays, which is what stops the shared password from coming back. Nobody takes themselves off. [Family](/wiki/controls/family#rules-that-keep-an-admin-who-can-sign-in) lists the refusals.

## Switch off and take off

Switching somebody off keeps everything, so an admin can undo it. Taking somebody off for good deletes what belonged to that person alone and leaves what the family said and did with no name on it, so plans and history stay whole. [Family](/wiki/controls/family#switch-off-or-take-off-for-good) has both lists and the steps.

## Kids

A kid is a member with the kid role. The family's decision is that a kid uses FamilyDB but never sees how it works.

| What a kid can | What happens |
|---|---|
| Sign in and read | Ideas and plans, except presents, which are hidden from every kid ([Presents](/wiki/model/ideas-and-places#presents)) |
| Chat | In their own conversation, within the two limits below |
| Keep wish lists | Their own three lists; a parent answers ([Wish-list rules](/wiki/model/wishes)) |
| Keep things to do | Only their own, on the page and by asking |
| Open household pages | None: What Vera knows, Status, this guide, Settings, Family and everybody's things to do are not shown |
| Look and password | Their own, like everyone ([Look and your password](/wiki/controls/look-and-password)) |

**Two limits.** A kid's messages are limited by a count of messages a model answered in a day, and by a dollar share of the day. Each is checked before the model is asked. Past one, the message is kept, not retried, and answered by a line from code; no model is asked. The values and defaults are on [Spending](/wiki/controls/settings/spending#the-daily-limit).

**Plain lines instead of workings.** Where a kid reads, a line about a key, a model, a dollar limit, an admin, the settings or the logs is said as one of three plain lines: "can't answer now", "try tomorrow" or "type it for me". A kid reads in their own chat, in their Telegram chat, and in any group while a kid is on the list, since code cannot see who is in a group. Admins are still told the cause (see [Needs a look](/wiki/controls/settings/messages#when-something-needs-fixing)), and the page hides the workings from anybody without "browse".

**The audience line.** Separately, one line in the current turn tells the model who reads the reply. In a Telegram group, or the shared conversation on the page, it says everyone there reads the reply, adding "kids among them" when a kid is on the list. A private chat gets none. Staying suitable for kids is an instruction in the product spec, which the evals check. Each kid's message also carries one line with their name, "a girl", "a boy" or "a kid", and an age if a birthday is set. Code sends age and male or female nowhere else.

**A kid's own data.** Parents and admins can read a kid's conversation on Chat, and the wish lists. What a kid says can become a memory that every chat carries ([How memory works](/wiki/model/memory)). Taking a kid off the list deletes their wish lists and memories about them; [Family](/wiki/controls/family#switch-off-or-take-off-for-good) has the full list.

Developer docs: docs/DESIGN.md, "Decisions" and "Security"; docs/WISHES.md, "Permissions".
