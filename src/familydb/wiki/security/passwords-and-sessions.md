# Passwords and sessions

Each person signs in with their own name and password, and the page remembers them with a signed cookie until a password change, a switch-off or the `web_session_days` limit ends it. This page says what you can rely on; the steps are in [Sign-in and security settings](/wiki/controls/settings/sign-in) and, for somebody who cannot get in, [Recovery](/wiki/operations/recovery).

## Each person's password

A password is 12 to 200 characters. FamilyDB keeps it only as a [hash](/wiki/reference/glossary#hash) (a one-way scramble: the server can check a typed password but cannot read it back), apart from the member record so a hash never travels into a prompt. Names are matched ignoring case and spacing.

A name that matches nobody, or somebody who is switched off or has no password, is refused in the same time and with the same words as a wrong password. The page does not reveal who is on the list.

## Starting passwords

An admin makes a starting password for another person on [Family](/wiki/controls/family#passwords), or you make one on the server. It is 16 characters from a set that leaves out look-alikes, stored hashed and flagged temporary. It is shown once: the server keeps it in memory for 10 minutes for the one page that shows it, never in the cookie. Making one signs that person out everywhere.

Whoever signs in with a starting password can reach only the page where they choose their own; every other page redirects there and other forms are refused. On Family an admin cannot make one for themselves, for somebody switched off, or while the family still shares a password.

## The shared password

Until an admin has a password of their own, the page takes the shared password: the one the installer printed (it stays in `.env` in plain text), or one chosen on the Settings page, which is stored hashed and replaces the one in `.env`. A session opened with it does everything, as nobody in particular, and the sign-in page has no name box.

**It ends for good, unless you restore an older backup, when any admin has a password of their own, even a starting one.** From then on it opens nothing, and sessions opened with it end at their next request. It does not come back because the page refuses to take the last admin who can sign in off the list, switch them off, change their role or take their password away.

FamilyDB checks its configuration only when the page starts. The page will not start without a password in two cases:

- it is behind a proxy (`WEB_TRUST_PROXY`), where nothing can waive the rule;
- it is reachable from other machines and `WEB_ALLOW_NO_PASSWORD` is not set. With that set, no password is needed and any length is accepted.

Any of these meets the rule: a shared password of 12 or more characters in `.env`, one chosen on the page, or an admin with a password of their own.

Under `familydb run`, only the page fails to start; the Telegram connection carries on. With no password at all on a page reachable only from the server, nobody signs in and anyone who can reach the page is in.

## Ending the shared password

On a new install, the first person to sign in with the shared password opens Your password (or the Setup password step), picks which active admin they are and chooses that admin's password. No current password is asked if they signed in with the installer's password within the last 60 minutes. That ends the shared password and signs them in as that admin. Then give everybody else a starting password on Family.

Anyone who holds the shared password can make this pick. Give the installer's password to one person, and replace it quickly.

## What ends a session

| What happens | Whose sessions end |
|---|---|
| Somebody chooses a new password of their own | Every other browser signed in as them; the one that changed it stays |
| An admin makes somebody a new starting password | All of that person's browsers |
| Their password is taken away, they are switched off or they are taken off the list | That person's |
| The shared password is changed | Every session opened with it, except the browser that changed it |
| An admin chooses a password of their own | Every session opened with the shared password |
| **Sign everyone out** | Every session and every known-browser mark. It replaces the signing key, so it needs your password again and is refused while `WEB_SECRET_KEY` is set; see [Sign everyone out](/wiki/controls/settings/sign-in#sign-everyone-out) |
| Sign out | That browser's only |
| Nobody visits for `web_session_days` | That browser's |

Each takes effect on the next click. A role change does not end a session but applies at the next click too. There is no list of sessions to revoke one by one.

A session lasts `web_session_days`, 30 unless changed, and each visit starts the count again, so there is no absolute maximum.

## Lockouts

| Scope | Limit | What it does |
|---|---|---|
| One address | 5 wrong passwords | Refuses that address for 15 minutes, even with the right password. The count clears on a right one and otherwise does not fade |
| The whole site | 50 wrong passwords in 15 minutes | Refuses every address until 15 minutes after the first of them, except known browsers |

A known browser is a browser that has signed in before (it carries a second cookie, below). It is still held by the per-address limit. Showing a key and signing everyone out share one count per address, and changing a password (your own, or the shared one) shares another, so a slip there never locks anybody out of signing in. All of them add to the site-wide count and obey it.

The counts are in memory in one process, so a restart clears them. The address is the connection's, which is correct behind a proxy only with `WEB_TRUST_PROXY` on. With it off, every visitor looks like one address and five wrong guesses lock the family out. With it on and the page bound to every interface outside Docker, a visitor can name any address, so the limit can be dodged. Wrong guesses are written to the service log as warnings with the address. [Recovery](/wiki/operations/recovery#too-many-tries) says how to wait one out.

## The session signing key

The key is `WEB_SECRET_KEY` when that is set, and otherwise 32 random bytes in a file beside the database (`data/web_secret` by default), made on the first start with owner-only permissions. If the file cannot be written, a temporary key is used, sign-ins do not survive a restart, and the log says so. The same key signs the session cookie, the known-browser cookie and the marks below.

A forger needs the key together with a stored password hash, which anyone with the database or `.env` has. The key is not in the backups, so a restore on a new machine only signs everyone out. Replacing the key signs everyone out. Another process serving the page keeps the old key until it restarts.

## How it works

After a good sign-in, the browser holds a signed cookie named `session`. It is signed, not encrypted: the person can read what is in it but cannot change it. It holds the form token, the time of sign-in, any messages waiting to be shown and, for a person, their member id and a mark of their password. A session opened with the shared password holds a `signed_in` flag and the shared password's mark instead.

A mark is an HMAC (a keyed fingerprint) of the member id and the stored hash, cut to 16 hex characters. On every request the page reloads the person from the database and checks the mark, so nothing about sessions is stored on the server. A new password changes the mark, which is how it signs the old sessions out.

| Cookie flag | Value |
|---|---|
| `HttpOnly` | always on |
| `SameSite` | `Lax` |
| `Secure` | on when `WEB_TRUST_PROXY` is on, read when the page starts |

A second cookie, `familydb_device`, marks a browser that has signed in before. It is signed, lasts 365 days from when it was set, has the same flags, and holds the member and a mark of their password. It signs nobody in. It only spares the browser the site-wide lockout.

Behind the refusals above sit three details. Passwords are hashed with scrypt, using a random salt for each one. A name that matches nobody is checked against a decoy hash, so a refusal takes as long as a wrong password. Past 4,096 tracked addresses, every one not currently locked out is forgotten, and if more than 4,096 are locked, all are.

Developer docs: `docs/DESIGN.md`, "Security".
