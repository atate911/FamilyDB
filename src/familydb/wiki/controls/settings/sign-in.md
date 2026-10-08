# Sign-in and security

The Sign-in and security card sets how long a sign-in lasts, shows a saved key on request, and signs everyone out. Who may do what is in [Roles and permissions](/wiki/model/family-and-roles#roles-and-permissions); how sign-in is guarded is in [Passwords and sessions](/wiki/security/passwords-and-sessions). For a forgotten password or a lockout, see [Recovery](/wiki/operations/recovery).

## Signing in

Once an admin has chosen their own password, everybody signs in as themselves. The card then points to **Your password** (to change yours) and to Family (to give somebody a starting password, or take theirs away). The best course is to give each person a password of their own, starting with your own as an admin.

The card shows a different form before that, depending on what the web page has:

- **The family shares one password.** The card is a form for that [shared password](/wiki/reference/glossary#shared-password), saying whether it is still the installer's or one you chose.
- **No password at all.** Anyone who can reach the web page is in, and the card offers to choose one.

A shared password needs 12 to 200 characters. Changing it asks for the one in force, except for the first choice within 60 minutes of signing in with the installer's. A new one signs every other browser out.

Once an admin signs in as themselves, the shared password ends for good, and it can no longer be changed here, unless you restore an older backup.

### Staying signed in

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Days a sign-in lasts (`web_session_days`) | 30 | How many days a phone or computer can go unused before it asks for the password again; each visit starts the count afresh. A change applies to every sign-in at once, so lowering it also signs out phones idle longer than the new value. | 1 to 3650 |

### How long messages are kept

| Label (`key`) | Default | What it does | Range last |
|---|---|---|---|
| Days a message keeps its words (`keep_messages_days`) | 0 (for good) | Each night at 03:30 FamilyDB empties the words of every message older than this. The message keeps its place in the conversation, so replies, reminders and the assistant's records that point at it still work. Anything under 30 is treated as 30. | 0 to 36500 (0 keeps them for good) |

What the assistant remembers, the ideas, the plans and the things to do are kept whatever this says. The kept words of model calls on [Troubleshooting](/wiki/controls/settings/troubleshooting#the-models-own-words) are kept no longer than the messages' words, if that is sooner than their own limit.

## See a key

A saved key or token is never drawn into a form. To read one, choose it and type your own password again (or the family's, while it is shared). It is shown once, on that page, and never put in the address bar. With no password on the web page, a key is shown to anyone who can reach it, which is one more reason to set one.

## Sign everyone out

This ends every sign-in on every phone and computer, this one included, and makes every browser a stranger again. Use it for a lost phone or a password shared too widely, and change the password too if the password is what got out.

With a password on the web page, the button asks for yours first (or the family's, while it is shared), then replaces the key that signs the login cookie. If `WEB_SECRET_KEY` is set in `.env` or the environment, the button stays but refuses and changes nothing: change that value on the server and restart FamilyDB instead.
