# Sign-in and security settings

Passwords, how long a sign-in lasts, seeing a saved key, and signing everyone out. For who may do what,
and how sign-in is guarded, see [Security and trust](/wiki/security).

## Signing in

Once an admin has chosen their own password, everybody signs in as themselves. The card then points to
**Your password** (to change yours) and to the Family page (to give somebody a starting password, or take
theirs away).

While the family still shares one password, the card is a form for that password instead, saying whether it is
still the installer's or one you chose. If the page has no password at all, anyone who can reach it is in, and the
card offers to choose one. The shared password needs at least 12 and at most 200 characters, changing it asks for the
one in force (except for the first choice soon after signing in with the installer's), and it signs every other
browser out. Once an admin signs in as themselves, the shared password can no longer be changed here. The better course is to give each person
a password of their own, starting with your own as an admin. [Recovery](/wiki/operations/recovery) covers
forgotten passwords and lockouts.

### Staying signed in

| Setting | Default | What it does |
|---|---|---|
| Days a sign-in lasts (`web_session_days`) | 30 | How many days a phone or computer can go unused before it asks for the password again; each visit starts the count afresh. A change applies to every sign-in at once, so lowering it also signs out phones idle longer than the new value. Between 1 and 3650 |

## See a key

A saved key or token is never drawn into a form. To read one, choose it and type your own password again (or the
family's, while it is shared). It is shown once, on that page, and never put in the address bar. With no password on
the page, a key is shown to anyone who can reach it, which is one more reason to set one.

## Sign everyone out

Ends every sign-in on every phone and computer, this one included, and makes every browser a stranger again. Use it
for a lost phone or a password shared too widely, and change the password too if the password is what got out. With a
password on the page it asks for yours first (or the family's, while it is shared), then replaces the key that signs
the login cookie. If `WEB_SECRET_KEY` is set (in `.env` or the environment), the button stays but refuses and changes
nothing: change that value on the server and restart instead.
