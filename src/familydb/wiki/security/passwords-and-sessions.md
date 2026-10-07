# Passwords and sessions

This page explains how sign-in works in detail: how passwords are stored and chosen, what the session cookie holds, what ends a session, and how wrong guesses are slowed. For the settings, see [Sign-in and security settings](/wiki/controls/settings/sign-in); for somebody who cannot get in, see [Recovery](/wiki/operations/recovery). Those pages hold the steps and this one does not repeat them.

## Each person's password

Each person signs in with their name and a password of their own. The password is kept only as an scrypt hash with its own random salt, in `member_logins`, apart from the member record so a hash never travels into a prompt. A password is 12 to 200 characters. Names are matched ignoring case and spacing.

A name that matches nobody, or somebody who is switched off or has no password, is checked against a decoy hash. It takes as long to refuse as a wrong password and gets the same answer, so the page does not reveal who is on the list. Comparisons are constant-time.

## Starting passwords

An admin makes a starting password for another person on the Family page, or you make one on the server. It is 16 characters from 49 chosen to avoid look-alikes, drawn with Python's `secrets`, and stored hashed with a flag that says it is temporary. It is shown once: the server holds it in memory for ten minutes for the one page that shows it, never in the cookie. Making one signs that person out everywhere.

Whoever signs in with a starting password is sent to Your password and can reach nothing else until they choose their own: other pages redirect there, and other form posts are refused. On the Family page an admin cannot make one for themselves, for somebody switched off, or while the family still shares a password.

## The shared password

Until an admin has a password of their own, the page takes a password the family shares. It is either the installer's first password, which stays in `.env` in plain text, or one chosen on the Settings page, which is stored hashed. Once one is chosen on the page, the one in `.env` stops working. A session opened with it does everything, as nobody in particular. The sign-in page then has no name box.

**It ends when any admin has a password of their own, even a starting one.** From then on it opens nothing and sessions opened with it end at their next request. It does not come back, because the page refuses to take the last admin who can sign in off the list, switch them off, change their role or take their password away.

Until people have their own passwords, a page reachable from other machines will not start without a shared one of at least 12 characters in `.env`, unless `WEB_ALLOW_NO_PASSWORD` is set on purpose. Behind a proxy a password is always required. With no password at all on a loopback-only page, nobody signs in, and anyone who can reach the page is in.

## The first admin's password

On a new install, the first person to sign in with the shared password can open Your password (or the setup's password step), pick which active admin they are and choose that admin's password. No current password is asked, because the shared one has just let them in. That ends the shared password and signs them in as that admin. Then give everybody else a starting password on the Family page. The pick is open to whoever holds the shared password, which is why the installer's first password should go to one person and be replaced quickly.

## Sessions

After a good sign-in, the browser holds a signed cookie. It is signed, not encrypted: the person can read what is in it but cannot change it. It holds the member's id, a mark of the password it was opened with, this session's form token and the time of sign-in.

The mark is an HMAC, under the signing key, of the member id and the stored hash. On every request the page reloads the person from the database and checks the mark, so nothing about sessions is stored on the server.

| Flag | Value |
|---|---|
| `HttpOnly` | always on |
| `SameSite` | `Lax` |
| `Secure` | on when `WEB_TRUST_PROXY` is on, read when the page starts |
| Lifetime | `web_session_days`, 30 unless changed, counted from the last visit |

A second cookie, `familydb_device`, marks a browser that has signed in before. It is signed, lasts 365 days, has the same flags, and holds the member and a mark of their password. It signs nobody in. It only spares the browser the site-wide lockout below.

## What ends a session

| What happens | Whose sessions end |
|---|---|
| Somebody's password changes, their own or a new starting one | Every other browser signed in as them; the one that changed it stays |
| Their password is taken away, they are switched off or they are taken off the list | That person's |
| The shared password is changed | Every session opened with it, except the browser that changed it |
| An admin chooses a password of their own | Every session opened with the shared password |
| "Sign everyone out" | Every session and known-browser mark |
| Sign out | That browser's only |
| Nobody visits for `web_session_days` | That browser's |

Each of these takes effect on the next click. A role change does not end a session but applies at the next click too. There is no list of sessions to revoke one by one.

## Lockouts

| Scope | Limit | What it does |
|---|---|---|
| One address | 5 wrong passwords | Refuses that address for 15 minutes, even with the right password. The count clears on a right one and otherwise does not fade |
| The whole site | 50 wrong passwords in 15 minutes | Refuses every address until 15 minutes after the first of them, except known browsers |

A known browser is still held by the per-address limit. Showing a key, signing everyone out and changing a password keep their own count for each address, so a slip there never locks anybody out of signing in. They share the site-wide count, and obey it.

The counts are in memory in one process, so a restart clears them. Past 4,096 tracked addresses, every one not currently locked out is forgotten. The address is the connection's, correct behind a proxy only with `WEB_TRUST_PROXY` on. With it off, every visitor looks like one address and five wrong guesses lock the family out. With it on and the page bound to every interface outside Docker, a visitor can name any address, so the limit can be dodged. Wrong guesses are written to the service log as warnings with the address.

## The session signing key

The key is `WEB_SECRET_KEY` when that is set, and otherwise 32 random bytes in a file beside the database (`data/web_secret` by default), made on the first start with owner-only permissions. If the file cannot be written, a temporary key is used and sign-ins do not survive a restart, and the log says so. The same key signs the session cookie, the known-browser cookie and the marks. A forger needs it and the stored password hash, which anyone with the server has. It is not in the backups, so a restore on a new machine only signs everyone out.

"Sign everyone out" replaces `data/web_secret` and the running page's key, after you retype your password. Another process serving the page keeps the old key until it restarts. With `WEB_SECRET_KEY` set, the button refuses; change the value and restart instead.

## The Origin check and Referrer-Policy

Every form post that changes something is checked in two steps. When the request carries an `Origin` header, it must equal the page's own scheme and host; with none, the request is taken for a non-browser client, which `SameSite` already covers. Then the form's token must match the session's. Sign-in and sign-out check `Origin` only. Behind a proxy, scheme and host come from forwarding headers that waitress believes from one trusted hop only, so the proxy must pass them on. If every sign-in says "That request did not come from this page", a proxy that does not pass the original host and protocol is the usual cause.

The page sends `Referrer-Policy: same-origin`, not `no-referrer`. Under `no-referrer` a browser posts with `Origin: null`, the check refuses it, and nobody can sign in. Only a real browser shows this: the test client sends no `Origin` at all.

## What the server commands do

`familydb password [NAME]` makes a starting password for the person named, or for the first admin who can sign in when there is no name. While the family still shares a password and no name is given, it replaces the shared one with a new 20-character password and signs everyone out. It refuses to make a first password for anyone but an admin. It prints the password once, and nothing is asked first: **whoever can run it on the server is let in,** so the server is the root of trust. `maintain.sh password` does the same on an installed server. `familydb members add` puts somebody on the family list from the server.

Developer docs: `src/familydb/web/auth.py` (module notes, `Lockout`), `src/familydb/passwords.py`, `src/familydb/family.py` (`claim`, `give_starting_password`), `src/familydb/store/logins.py`, `src/familydb/web/keys.py`, `src/familydb/web/__init__.py` (`security_headers`) and `docs/DESIGN.md`, "Security" and "Web page access".
