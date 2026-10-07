# Family

Family is where you say who the assistant talks to and who signs in to the web page: add somebody, change their role, link their Telegram, give them a starting password, switch them off or take them off for good. Only admins reach it; anyone else is shown a page that names the admins. The assistant cannot change this list, because there is no tool for it ([why](/wiki/model/family-and-roles#why-the-list-is-not-a-tool)).

## What is on the page

- **The list.** One line a person: role, age (if a birthday is set), how the assistant knows them, and tags: **Switched off**, **Signs in** or **Starting password**. While a daily message count is set on [Spending](/wiki/controls/settings/spending), a kid's line also says "3 of 20 messages today".
- **Waiting to be let in.** Appears only when somebody not on the list has written to the assistant on Telegram.
- **Add somebody**, and **What each role does** ([Roles and permissions](/wiki/model/family-and-roles#roles-and-permissions) has the table).
- A note, while the family still shares one password, that this page cannot tell who is who.

A person's own page has **About**, **Signing in to this page**, **Linking their Telegram** and, folded away, **Take off the list for good** (not on your own page).

## Add or change somebody

1. Choose **Add somebody**, or open a person from the list.
2. Give a name (1 to 80 characters), a role, and optionally a Telegram id. The role starts as Admin on an empty list and Parent after that.
3. On a person's page you can also set a birthday (only the age goes to the model, never the date; blank removes it), male or female (kids only), and **On the list**.
4. Choose **Add** or **Save**.

Clearing a person's Telegram id removes the link. If the page refuses a change, it says why:

| What you see | Why |
|---|---|
| "There is already somebody called …" or "That Telegram id is already …'s." | A name and a Telegram id each belong to one person, switched-off people included |
| "… was changed since you opened this." | Somebody changed this person since you opened the page, and a link just used counts; make your change again |
| "The bot is answering … right now." | Nobody is changed mid-answer; try again once the reply is sent |

## Link a Telegram

There are three ways to connect a person to their Telegram. To create the Telegram bot itself, use [Connections](/wiki/controls/settings/connections#telegram).

| Way | How it works |
|---|---|
| An id | Type the number into the Telegram id box (a leading minus is fine, as group ids use). A stranger who writes to the assistant is told their id |
| A knock | Under **Waiting to be let in**, the stranger's Telegram name, id, where they wrote from and when are listed, newest first. Fill in the name, pick a role (Parent unless changed) and choose **Let them in** |
| A link | On the person's page choose **Make a link for <name>**. They open it in a private chat on their phone and press Start. It works once, within 24 hours; a new link replaces the last; only a hash of its code is kept |

A knock keeps only who and when, never what the stranger said. Knocks are kept 30 days, at most 200, and the page shows the last 20 ([Known limits](/wiki/reference/known-limits#knocks-and-links-are-cleared-late) says when old ones go).

### Before you send a link

- The Telegram bot must be connected and the person switched on, and they must open the link in a private chat with the bot. The link is shown once, like a starting password.
- A used or old link answers "That link no longer works". A link opened from a Telegram that is already somebody else's changes nothing and says whose it is.
- Using a link clears the person's birthday and male or female. Enter them again on their page afterwards ([Known limits](/wiki/reference/known-limits#a-telegram-link-clears-birthday-and-gender)).

> **A link works for whoever opens it first, and that person is taken for the one it was made for.** Send it to them alone.

## Passwords

If somebody has lost their password, make them a new starting password. [Recovery](/wiki/operations/recovery) covers lockouts and the case where nobody can sign in.

1. Open the person and choose **Make a starting password**.
2. Copy the password shown. It is 16 characters, and the page keeps its copy in memory for 10 minutes, so reloading, waiting or restarting the server makes it disappear from the page. The password itself keeps working until they choose their own, and you can make another.
3. Send it to them. They sign in, are taken to **Your password**, and can reach nothing else until they choose their own (12 characters at least). The starting one then stops working.

A new starting password signs the person out everywhere, so it is also the answer to a lost phone. **Take their password away** signs them out and stops them signing in.

The page refuses both for yourself (use **Your password**) and while the family still shares one [password](/wiki/reference/glossary#shared-password), since it does not know who you are ("Choose your own password first, as an admin"). It also refuses a starting password for somebody switched off, and taking away a password somebody does not have or the only admin who can sign in.

The shared password ends when an admin chooses their own on **Your password**. After that every other person needs a starting password from here.

## Switch off, or take off for good

| | Switch off | Take off for good |
|---|---|---|
| Sign-in | Ends on their next click | Gone |
| Telegram | Answered as a stranger | Link gone |
| Messages | Waiting ones are given up; all kept | Waiting ones are given up; the rest stay, with no name |
| Undo | Switch them back on | Not possible, unless you restore an older backup |

> **Taking somebody off for good cannot be undone** unless you restore an older backup. Their name, password, Telegram link and any pending link, where they last were, the memories about them, and a kid's wish lists are deleted. Open things to do and reminders in their own chat are canceled, plans made there stop following up there, and anything queued for that chat is not sent.

What they said and did stays with no name on it: messages, ideas, plans, outcomes, suggestions, memories they told the assistant, other things to do, their changes in the settings log, and a parent's answers on other kids' wishes. A name typed inside any of them stays.

## Rules that keep an admin who can sign in

The page refuses these, with the message in quotes:

- Leaving no active admin: "… is the only admin. Make somebody else one first."
- Leaving no admin who can sign in, once any admin has their own password: "… is the only admin who can sign in to the page. Give another admin a password first." This covers switching off, a role change, taking off and taking their password away.
- Taking yourself off ("Another admin can"). Under the shared password only the first two rules apply, since the page does not know who you are.
- Taking somebody off without ticking the box ("Tick the box to say you are sure first").

From the server, `familydb members list --all` shows everyone. Run it as in [The command line](/wiki/operations/command-line#how-to-run-it).
