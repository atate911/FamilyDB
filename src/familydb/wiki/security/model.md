# The trust and threat model

This page says what FamilyDB defends, what it leaves to you, and what to check before you put the page on the internet. The roles are in the [table on Security and trust](/wiki/security#who-may-do-what); see also [Passwords and sessions](/wiki/security/passwords-and-sessions) and [Data and privacy](/wiki/security/data-and-privacy).

## What a sign-in guards

A password is the only lock on the page, and there is no second factor. What a stolen one gives depends on whose it is.

| If this password is lost | The holder can |
|---|---|
| A kid's | Chat within the limits you set for kids, keep their own wishes and things to do, and read ideas and plans except presents hidden from kids |
| A parent's | All of that, plus change ideas, plans and things to do (plans go on the Google calendar when one is connected), read what the bot remembers, the Status page and every kid's conversation, and answer wishes. Spending is only by asking questions, up to the daily limit |
| An admin's | All of that, plus the Settings page (spending limit, which model company answers, keys, the Telegram token), the Family page (let a Telegram account talk to the bot, take somebody off for good) and the Activity page, which shows every message and tool call in full. An admin can also make a starting password for anybody, which is a way into that person's account |
| The shared password | Almost everything an admin can (not making other people's passwords), as nobody in particular, so the change log names no one. It stops working once an admin has a password of their own |

Most of what a parent changes stays visible: an idea is dropped, not deleted, and every tool call is logged. An admin can do what cannot be undone, such as taking somebody off for good. Keep admins few.

## What protects the page

- **A gate in front of everything.** Every request passes `require_login`. Only sign-in, sign-out, the health check, the home-screen manifest and static files are open. Each part of the page then needs a permission, read from the database on every request, so a role change applies at once.
- **Forms are checked twice.** Every form that changes something carries a per-session CSRF token and passes an Origin check, on top of a `SameSite=Lax` cookie. Sign-in and sign-out check Origin only.
- **Output is escaped.** Templates escape by default, and a link from chat or a fetched page is kept only if it is `http` or `https`.
- **A strict content security policy.** Scripts, styles and fonts load only from the page itself, images from the page or `data:`, nothing can frame it, and forms post only back to it. There is no inline script. Responses also carry `nosniff`, `X-Frame-Options: DENY`, `Cache-Control: no-store` and, over HTTPS, HSTS.
- **Forms are tool calls.** The page has no write path of its own: each form runs a tool the model could also run, and tests pin which parts of the page may write.
- **A form does its work once.** A once-only token makes a double click or resend act once.
- **Settings are a whitelist.** A form can write only the names in `store.settings`. How the page is served (bind address, proxy trust, signing key, the no-password waiver, the database path) is in `.env`, out of every form's reach.
- **Keys are write-only.** Stored, never drawn into a form, never put in the change log, and shown only after you retype the password you signed in with.
- **The family list is not a tool.** No model turn can change who may message the bot or who signs in. That goes through the Family page and `familydb/family.py`.
- **Wrong guesses are slowed.** See [Lockouts](/wiki/security/passwords-and-sessions#lockouts).

## What text the bot reads can and cannot do

The bot reads text nobody on the family list wrote: a forwarded message, a pasted page, the words in a photo, a page a lookup opens. The system prompt tells the model to treat it as information, but that is a request, not a guarantee. The guarantees are in what the code lets a model do.

**The chat model** never gets the web tools. Its tool list is the same on every turn, dispatch refuses any tool not declared for the turn, and inputs are validated. So a successful injection into a chat can do what the chat tools do:

- add or change ideas, record outcomes, and remember facts that go into later prompts;
- create, move or delete calendar events and plans;
- add or change things to do, including one owned by another family member, whose reminder is then sent to them;
- keep wishes, ask for lookups now, or run a suggestion that may search the web (paid, within the daily limit).

No chat tool reads or writes the settings, the family list, passwords, keys, the spending limit or which model answers.

**A lookup** is a separate turn that may search the web. An idea lookup is declared two tools, `save_place` and `skip_place`, and dispatch refuses any call for an idea other than its own. A hostile page can still put wrong text in that idea's place record (summary, hours, address, links). If a place of the same name exists, that record is updated too, even when another idea points at it. Links are filtered to `http` and `https` and pages escape the text, but the chat model later reads saved places in its tool results, so a poisoned record can mislead an answer. A discovery lookup has one tool, `report_finds`, and its finds sit in a memory cache for twelve hours. Neither has a tool that sends a message or changes the family list, settings or a key.

**Voice and photos** are read by models with no tools. Their words become the text of the message and reach the chat model like anything typed.

**Telegram:** a message from an id not on the family list gets a short line and no model call, and a stranger's voice note is not downloaded.

In short, a hostile message or page can make the bot save something wrong, or spend a little, and the family can see and fix it. It cannot change who may sign in or touch the settings.

## What is not protected

- **Whoever controls the server has everything.** The database is a plain SQLite file, keys in it are plain text, and `.env` holds the installer's first password. Files are owner-only (a `077` umask, a `700` data folder, on a non-Docker install a hardened systemd unit), which keeps other accounts out, not root.
- **A stolen backup holds the keys in plain text.** Treat a backup like the key itself.
- **A Telegram link is a bearer token.** Whoever opens it first is taken for that person. It works once, for a day.
- **While the family shares a password, the first person to choose one of their own can pick which admin to become.** That is no more power than the shared password had.
- **A session cannot be revoked singly.** The cookie is signed, not stored. It ends when the person's password changes, they are switched off, or you sign everyone out.
- **A stranger who finds the bot gets an answer** that tells them their Telegram id, and a knock is recorded (name, id, when): up to 200, for 30 days.
- **An admin can read every conversation,** a kid's included, and the Activity page does not hide a present from the admin it is for.

## The default network posture

The page listens on `127.0.0.1` only. In front of it the installer puts Caddy, which holds the HTTPS certificate and passes requests to that port, and sets `WEB_TRUST_PROXY` so the page believes one forwarding hop. On Docker, the compose file publishes the port to the host's loopback. The installer opens ports 80 and 443 in `ufw` only if it is already on; with `--local-only` there is no proxy and you reach the page by SSH tunnel.

The bot needs nothing inbound: it reaches Telegram by long polling and calls the other services itself. [Install and first run](/wiki/operations/install#what-the-installer-changes-and-why) lists what the installer changes.

## Checklist for a public install

1. Keep HTTPS in front of the page and `WEB_TRUST_PROXY` true. **Do not bind the page to every interface outside Docker with that flag on:** the page then believes forwarding headers from anyone, so a guesser can pose as many addresses.
2. Give every person their own password, yours first, so the shared one ends. The page asks for 12 characters or more; use long ones.
3. Keep one or two admins, and pass on starting passwords only over a channel you trust.
4. Set a daily spending limit you could lose in a bad day ($2 unless changed), and leave admin alerts on.
5. If backups leave the server, consider keeping model keys in `.env`, which a backup does not hold. See [Backup and restore](/wiki/operations/backup-and-restore).
6. Send Telegram links to one person, privately, and add only ids you know.
7. Keep root and SSH access tight, learn how to [recover](/wiki/operations/recovery) before you need to, and keep FamilyDB updated.

Developer docs: `docs/DESIGN.md`, "Security" and "Decisions" (Web page access, Family list, Linking Telegram); `docs/AI_CALLS.md`, "What may it do?"; `src/familydb/web/auth.py`, `src/familydb/web/__init__.py` (`security_headers`), `src/familydb/tools/registry.py` (`dispatch`), `src/familydb/store/settings.py`.
