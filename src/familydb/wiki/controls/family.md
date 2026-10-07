# Family

The Family page is where an admin says who the bot talks to and who signs in to the page: add somebody, change their role, link their Telegram, give them a starting password, switch them off or take them off for good. Only admins reach it. Anyone else is shown a page that names the admins. The bot also cannot change this list: there is no tool for it.

## What is on the page

- **The list.** One line a person: role, age (if a birthday is set), and how the bot knows them ("Telegram" with the id, "Known on" another channel, "Named in ideas and plans" for a kid who does not sign in, or "Web page and console only"). Tags say **Switched off**, **Signs in** or **Starting password**. While a daily message count is set on [Spending](/wiki/controls/settings/spending), a kid's line also says "3 of 20 messages today".
- **Waiting to be let in.** Appears only when somebody not on the list has written to the bot on Telegram.
- **Add somebody**, and **What each role does**.
- A note, while the family still shares one password, that this page cannot tell who is who.

Open a person for their own page: **About**, **Signing in**, **Linking their Telegram** and, folded away, **Take off the list for good** (not on your own page).

## Roles

| Role | In short |
|---|---|
| Admin | Looks after FamilyDB: settings, setup and this list. The page keeps at least one |
| Parent | Everything else a grown-up does, including answering the kids' [wish lists](/wiki/controls/wish-lists) |
| Kid | Signs in, chats within the daily number, keeps their own wishes and sees only their own things to do |

The full table is in [Security and trust](/wiki/security#who-may-do-what), and the terms are in the [glossary](/wiki/reference/glossary#admin-parent-kid).

## Add or change somebody

1. Choose **Add somebody**, or open a person from the list.
2. Give a name (1 to 80 characters), a role, and optionally a Telegram id. The role starts as Admin on an empty list and Parent after that.
3. On a person's page you can also set a birthday (only the age goes to the model, never the date; blank removes it), male or female (kids only, which shapes how the bot speaks to them), and **On the list**.
4. Choose **Add** or **Save**.

| What you see | Why |
|---|---|
| "There is already somebody called …" | A name belongs to one person, whatever its case |
| "… is on the list but switched off. Switch them back on instead of adding them again." | The switched-off person keeps the name |
| "That Telegram id is already …'s." | One Telegram, one person, switched-off people included |
| "A Telegram id is a number." | The id must be a number |
| "… was changed since you opened this." | Somebody changed this person since you opened the page (a link just used counts); make your change again |
| "The bot is answering … right now." | Nobody is changed mid-answer; try again in a moment |
| "A birthday is a date, such as 2017-03-14." or "not a day that has been" | The date is malformed, in the future or before 1900 |

Clearing a person's Telegram id removes the link.

## Link a Telegram

| Way | How it works |
|---|---|
| An id | Type the number into the Telegram id box (a leading minus is fine, as group ids use). A stranger who writes to the bot is told their id |
| A knock | Under **Waiting to be let in**, the stranger's Telegram name, id, where they wrote from and when are listed, newest first (the last 20, forgotten after a month). Fill in the name, pick a role (Parent unless changed) and choose **Let them in**. Only who and when are kept, never what they said |
| A link | On the person's page choose **Make a link for <name>**. They open it in a private chat on their phone and press Start. It works once, for 24 hours; a new link replaces the last; only a hash of its code is kept |

A link needs the Telegram bot connected, a person who is switched on, and a private chat with the bot. The link is shown once, like the password. To somebody not on the list, a used or old link answers "That link no longer works"; somebody already on the list gets the normal greeting, and a link opened from a Telegram that is already somebody else's changes nothing and says whose it is.

**Using a link currently clears the person's birthday and male/female.** Set them again on their page afterwards. The setup's "That's me" button does not.

**A link works for whoever opens it first, and that person is taken for the one it was made for.** Send it to them alone.

## Passwords

Each person signs in with their name and a password of their own. See [Recovery](/wiki/operations/recovery) for lockouts and forgotten passwords.

1. Open the person and choose **Make a starting password**.
2. Copy the password shown. It is 16 characters and the page shows it once: reload, wait over ten minutes or restart the server and it is gone. The password itself keeps working until they choose their own, and you can make another.
3. Send it to them. They sign in, are taken to **Your password**, and can reach nothing else until they choose their own (at least 12 characters). The starting one then stops working.

A new starting password signs the person out everywhere, so it is also the answer to a lost phone. **Take their password away** signs them out and stops them signing in.

You are refused:

- a starting password, or taking a password away, for yourself (use Your password);
- either one while the family still shares one [password](/wiki/reference/glossary#shared-password), since the page does not know who you are ("Choose your own password first, as an admin");
- a starting password for a person who is switched off;
- taking away a password somebody does not have, or the only admin who can sign in.

The shared password ends when an admin chooses their own on Your password; after that every other person needs a starting password from here.

## Switch off, or take off for good

| | Switch off | Take off for good |
|---|---|---|
| Sign-in | Ends on their next click | Gone |
| Telegram | Answered as a stranger | Link gone |
| Messages | Waiting ones are given up; all kept | Waiting ones are given up; the rest stay, with no name |
| Undo | Switch them back on | Not possible |

**Taking somebody off for good cannot be undone.** Their name, password, Telegram link and any pending link, where they last were, what the bot remembers about them, and a kid's wish lists are deleted. Open things to do and reminders in their own chat are cancelled, plans made there stop following up there, and anything queued for it is not sent.

What they said and did stays with no name on it: messages, ideas they suggested, plans they made, outcomes they recorded, suggestions they asked for, memories they told the bot, other things to do they added or owned, their changes in the settings log, and a parent's answers on other kids' wishes.

## Rules that keep an admin who can sign in

- The page keeps at least one active admin: "… is the only admin. Make somebody else one first."
- Once any admin has their own password, one stays who can: "… is the only admin who can sign in to the page. Give another admin a password first." This applies to switching off, a role change, taking off and taking their password away.
- You cannot take yourself off ("Another admin can"); under the shared password the page does not know who you are, so only the two rules above apply.
- Taking off needs the box ticked ("Tick the box to say you are sure first"), an unchanged form, and nobody being answered right now.

From the server, `familydb members list --all` shows everyone and `familydb password "<name>"` makes a starting password. See [The command line](/wiki/controls/command-line).

Developer docs: `src/familydb/family.py` (module notes), `store/members.py` (`POINTING_AT`), `store/knocks.py`, `docs/DESIGN.md`, "Taking somebody off", "Linking Telegram" and "Family list".
