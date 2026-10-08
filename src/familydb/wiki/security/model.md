# Trust and threat model

FamilyDB defends the family's plans, messages and spending with a sign-in for each person, and leaves the server and the choice of admins to you. Who may do what is in [Roles and permissions](/wiki/model/family-and-roles#roles-and-permissions). Before you put the page on the internet, read the [checklist](#checklist-for-a-public-install) at the end.

## What a sign-in guards

A password is the only lock on the page, and there is no second factor. What a stolen one gives depends on whose it is.

| If this password is lost | The holder can |
|---|---|
| A kid's | Read ideas and plans (not presents hidden from kids), keep their own wishes and things to do, and chat. Chat reaches more than the pages do, as explained below the table |
| A parent's | All of that, plus change ideas, plans and things to do on the pages, read what the assistant remembers, Status and every kid's conversation, and answer wishes. Spending is only by asking questions, up to the daily limit |
| An admin's | All of that, plus Settings (spending limit, which model company answers, keys, the Telegram token), Family (let a Telegram account talk to the assistant, take somebody off for good) and Recent activity, which shows every message and tool call in full. An admin can also make a starting password for anybody, a way into that person's account |
| The shared password | Almost everything an admin can (not making other people's passwords), as nobody in particular, so the change log names no one. It stops working once an admin has a password of their own |

The forms that change things are closed to a kid, and so are the assistant's tools that edit an idea, record how a plan went, or make, move or cancel a plan or calendar event. A kid can still ask the assistant to add an idea or remember something. Code also holds back lookups, other people's things to do and wishes; the other brakes are the model's judgment and the daily limits. See [Chat tools check only some roles](/wiki/reference/known-limits#chat-tools-check-only-some-roles).

Most of what a parent changes stays visible: an idea is dropped, not deleted, and every tool call is logged. An admin can do what cannot be undone, such as taking somebody off the list for good. Keep admins few.

## What protects the page

In short: every page needs a sign-in, every form proves it came from the page, and the page runs no script that is not its own.

- Every request passes a sign-in gate. Only sign-in, sign-out, the health check, the home-screen manifest and static files are open. Each part of the page then needs a permission, read from the database on every request, so a role change applies at once. With no password at all, nobody signs in and the gate lets everyone through.
- A form that changes something must pass an Origin check (the browser names the address that sent the form) and carry the session's CSRF token (a one-time proof that the form came from this page, not another site), on top of a `SameSite=Lax` cookie. Sign-in and sign-out have no token and rely on Origin and `SameSite`.
- The `Referrer-Policy` is `same-origin`. A stricter policy makes browsers post `Origin: null`, which the check refuses, and nobody could sign in.
- Templates escape output by default, and a link from chat or a fetched page is kept only if it is `http` or `https`.
- A strict content security policy lets scripts, styles and fonts load only from the page itself, images from it or `data:`, and forms post only back to it. Nothing can frame the page, and there is no inline script. Pages are `no-store`, and HSTS goes out over HTTPS.
- Writes go through four doors, pinned by tests. Idea, plan, thing to do, memory and wish forms run the same tool the model would; Family, Settings and chat each have one door of their own. No page module touches a table.
- A settings form can write only the names on a whitelist. How the page is served (bind address, proxy trust, signing key, database path) is in `.env`, out of every form's reach.
- Keys are write-only. They are stored, never drawn into a form and never put in the change log. When the page has a password, a key is shown only after you retype the one you signed in with. With no password on the page, anyone who reaches it can show a key.
- The family list is not a tool, so no model turn can change who may message the assistant or who signs in.
- Wrong guesses are slowed: see [Lockouts](/wiki/security/passwords-and-sessions#lockouts).
- A double click acts once, using a once-only token kept in memory and lost on a restart. That is a correctness feature, not a defense.

## What text the assistant reads can and cannot do

The assistant reads text nobody on the family list wrote: a forwarded message, a pasted page, the words in a photo, a page a lookup opens. Its instructions tell it to treat that text as information, but that is a request, not a guarantee. The guarantees are in what the code lets a model do.

The chat model never gets the web tools. Its tool list is the same on every turn, dispatch refuses any tool not declared for the turn, and inputs are validated. A successful injection into a chat can do what the chat tools do, for anyone who can chat:

- add or change ideas, record outcomes, and remember facts that go into later prompts;
- create, move or delete calendar events and plans;
- add or change things to do, including one owned by another family member, whose reminder is then sent to them;
- keep wishes (limited by the role checks above), ask for lookups now, or run a suggestion that may search the web, which costs money within the daily limit.

No chat tool changes or reveals the settings, the family list, passwords, keys, the spending limit or which model answers.

A lookup is a separate turn that may search the web. An idea lookup has two tools, `save_place` and `skip_place`, and dispatch refuses any call for an idea other than its own. A hostile page can still write wrong text into that idea's place record: name, summary, hours, address, phone, links. The chat model later reads saved places, so a poisoned record can mislead an answer. A discovery lookup has one tool, `report_finds`. Neither can send a message or change the family list, the settings or a key.

The judgment job is a third kind of model call, off unless an admin turns on **Ask a stronger model when a change needs judgment**. It may read a company's pricing page. Code accepts only a price a public list agrees with, and switches a model by itself only at about the same cost.

Voice notes and photos are read by models with no tools, and their words reach the chat model like anything typed.

On Telegram, a message from an id not on the family list gets a short line and no model call (in a group, only when it is addressed to the assistant), and a stranger's voice note is not downloaded.

In short, a hostile message or page can make the assistant save something wrong, or spend a little, and the family can see and fix it. It cannot change who may sign in or touch the settings.

## What is not protected

- Whoever controls the server has everything. The database is a plain SQLite file, keys in it are plain text, and `.env` holds the shared password. Files are owner-only, which keeps other accounts out, not root.
- A stolen backup holds the keys in plain text, and every message and every password hash. Hashes are scrypt (N=16384, r=8, p=1) and can be guessed offline, where lockouts do nothing, so length matters. The page asks for 12 characters at least.
- A Telegram link is a bearer token: whoever opens it first is taken for that person.
- While the family shares one password, whoever first chooses a password of their own can pick which admin to become. That gives no more power than the shared password already had.
- A session cannot be revoked singly. The cookie is signed, not stored; [what ends one](/wiki/security/passwords-and-sessions#what-ends-a-session) is on the passwords page.
- A stranger who finds the assistant gets an answer that tells them their Telegram id, and a knock is recorded on [Family](/wiki/controls/family#link-a-telegram).
- An admin can read every conversation, a kid's included, and Recent activity does not hide a present from the admin it is for.

## The default network posture

The page listens on `127.0.0.1` only. The installer puts Caddy in front, which holds the HTTPS certificate and passes requests to that port, and sets `WEB_TRUST_PROXY` so the page believes one forwarding hop. HTTPS is in front unless you pass `--local-only`, which leaves the page to an SSH tunnel, or you install on Docker without a domain, where the page stays on the machine. The installer opens ports 80 and 443 in `ufw` only if it is already on.

FamilyDB needs nothing inbound: it reaches Telegram by long polling and calls the other services itself. What the installer puts on the server is listed in [The server](/wiki/operations/host#everything-the-install-put-on-the-server); the HTTPS and firewall steps are in [HTTPS and the firewall](/wiki/operations/https-and-firewall).

## Checklist for a public install

> **Binding the page to every interface outside Docker while `WEB_TRUST_PROXY` is on lets a guesser pose as many addresses.** Dropping `127.0.0.1` from the compose `ports` line does the same: the page then believes forwarding headers from anyone.

1. Keep HTTPS in front of the page and `WEB_TRUST_PROXY` true.
2. Give every person their own password, yours first, so the shared one ends. The page asks for 12 characters or more; use long ones.
3. Keep one or two admins.
4. Set a daily spending limit you could lose in a bad day (US$2.00 unless changed), and leave **Tell admins on Telegram** on. Set a spending limit with the model company too: FamilyDB's is an estimate, and 0 turns it off.
5. If backups leave the server, consider keeping model keys in `.env`, which a backup does not hold. See [Backup and restore](/wiki/operations/backup-and-restore).
6. Send Telegram links to one person, privately.
7. Keep root and SSH access tight, and learn how to [recover](/wiki/operations/recovery) before you need to.

Developer docs: docs/DESIGN.md, "Security" and "Decisions"; docs/AI_CALLS.md, "What may it do?".
