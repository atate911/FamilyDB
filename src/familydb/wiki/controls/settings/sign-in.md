# Sign-in and security settings

Passwords, how long a sign-in lasts, seeing a saved key, and signing everyone out. For who may do what,
and how sign-in is guarded, see [Security and trust](/wiki/security).

## Signing in

Once an admin has chosen their own password, everybody signs in as themselves. The card then points to
**Your password** (to change yours) and to the Family page (to give somebody a starting password, or take
theirs away).

While the family still shares one password, the card is a form for that password instead. If the page has no
password at all, anyone who can reach it is in, and the card offers to choose one. The shared password needs at
least twelve characters, and changing it signs every other browser out. The better course is to give each person
a password of their own, starting with your own as an admin. [Recovery](/wiki/operations/recovery) covers
forgotten passwords and lockouts.

### Staying signed in

| Setting | Default | What it does |
|---|---|---|
| Days a sign-in lasts (`web_session_days`) | 30 | How long a phone or computer stays signed in before it asks again. Between 1 and 3650 |

## See a key

A saved key or token is never drawn into a form. To read one, choose it and type your own password again (or the
family's, while it is shared). It is shown once, on that page, and never put in the address bar. With no password on
the page, a key is shown to anyone who can reach it, which is one more reason to set one.

## Sign everyone out

Ends every sign-in on every phone and computer, this one included, and makes every browser a stranger again. Use it
for a lost phone or a password shared too widely, and change the password too if the password is what got out. It asks
for your password first, and it replaces the key that signs the login cookie. It cannot be used while `WEB_SECRET_KEY`
is set in `.env`; change that value on the server and restart instead.
