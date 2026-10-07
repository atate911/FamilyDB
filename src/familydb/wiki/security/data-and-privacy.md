# What is stored and for how long

FamilyDB keeps everything the family says in one SQLite file on your server, and a few keys in plain files beside it. Nothing removes messages, so the database only grows. What leaves the server is on [What leaves the house](/wiki/security/what-leaves-the-house).

## What is stored

| What | Where it is kept | How long | Who can see it |
|---|---|---|---|
| Messages, both ways, with a voice note's words and a photo's description marked as such, and commands and button taps | The database | No setting, job or command removes them | The Family conversation on the page: parents and admins. A kid's own page conversation: that kid, every parent and every admin. Telegram chats: whoever is in them. Admins can open any message in full on [Recent activity](/wiki/controls/status/activity) |
| Each tool call, with its input and result | The database | Same | Admins on Recent activity. Parents and admins see only the tools' names under an answer |
| Each model call: model, token counts, estimated cost, what it was for. Not the prompt or the reply | The database | Same | Parents and admins see totals on Status; admins see each call |
| Ideas, places, plans, outcomes, things to do, reminders | The database | Kept; an idea is dropped, not deleted | Signed-in people by role. A kid sees only their own things to do |
| Wish lists | The database | Kept | The kid who wrote them, parents and admins, not another kid |
| What the assistant remembers, with a quote of the message it came from | The database | A forgotten or replaced memory keeps its words. See [What Vera knows](/wiki/controls/memory) | Parents and admins on the page. The model is sent every Must with each message, and other memories up to about 1,600 characters |
| The family: name, role, Telegram id, birthday, male or female for a kid, page look | The database | Until the person is taken off | Admins on Family. Names and roles go to the model with every message |
| Password hashes | The database | Until changed, taken away, or the person is taken off | Nobody through the page. A starting password is shown once to the admin who made it |
| Settings, and model and Telegram keys as plain text | The database | Until changed or removed | Admins. A key is shown only after you retype your password, if the page has one |
| The shared password, the Google key and the session signing key | `.env` (and its `.env.*.bak` copies), `data/google_key.json` and `data/web_secret`: plain text, owner-only | Until you change or delete them | Whoever can read the server. None is in a backup |
| The change log: who, from where, old and new values, except keys and the shared password | The database | No removal | Admins on Settings |
| Where somebody is: coordinates and a place name | The database | Deleted within a day. See [Shared location](/wiki/model/location) | No page shows the row; admins can read the place name on Recent activity |
| Strangers who wrote to the assistant: name, id, chat, count, never the words | The database | Pruned when the next stranger writes. See [Link a Telegram](/wiki/controls/family#link-a-telegram) | Admins on Family |
| A Telegram link | A hash of its code | Expires, and goes when somebody makes or uses a link | Nobody |
| Troubles for admins | The database | Until the trouble clears; rows unseen for 7 days go when the next is noted | Parents and admins on Status |
| Questions asked of a stronger model | The database | 60 days, pruned only while **Ask a stronger model when a change needs judgment** is on; a refusal question filed while it is off stays | Parents and admins on Status |
| A voice recording or a photo | Not stored. It is in memory while it is sent, then dropped; the words stay as a message | None | Not applicable |
| Safety backups and nightly backups | The backups folder (`/opt/familydb/backups` on an install) | 14 days if the nightly schedule is on; otherwise until you delete them | Root and the owner. The database and everything in it |

A stolen backup holds every message, every key you saved on the Settings page in plain text, and every password hash; see [What is not protected](/wiki/security/model#what-is-not-protected).

The place name outlives the coordinates: the confirmation message for a shared position is an ordinary message, and the suggestion tool's "travel from" line is in the tool log. See [A place name outlives the coordinates](/wiki/reference/known-limits#a-place-name-outlives-the-coordinates).

A present is hidden on the pages and in chat, not in the data. Recent activity, the database and a backup do not hide it. See [Presents](/wiki/model/ideas-and-places#presents).

The service log records page sign-ins and changes with the visitor's address, password and link changes (never the password), and errors. At `log_level` `DEBUG` it also records traffic to Telegram and the model companies. FamilyDB sets no retention for it; the host keeps it.

## A kid's data

A kid's data is kept like anybody's, with two additions: the assistant is told their age and whether they are recorded as a girl or a boy, never their birthday, and their wish lists are not shown to another kid. [Kids](/wiki/model/family-and-roles#kids) has the rest.

## Taking somebody off the family list

Switching a person off deletes nothing. Taking them off for good deletes what was theirs alone and leaves what they said and did with nobody's name on it. The words stay as written, so a name inside a message, a plan or a memory stays, and earlier backups still hold the person. [Family](/wiki/controls/family#switch-off-or-take-off-for-good) has the full list and the steps.

## Deleting everything

There is no setting, job or command that removes messages one at a time or by age. You can take a person off the family list, or remove the whole install and its database.

> **Removing the install deletes the database, which is the only copy of what the family said.** `--purge` first writes one backup to `/var/backups/familydb` (or the folder you give with `--backup-to`), and that backup stays until you delete it. `--from-zero` keeps no backup unless you give `--backup-to`. The steps are on [Taking it off again](/wiki/operations/host#taking-it-off-again).

Things outside the server stay: that `--purge` backup, which nothing prunes, Telegram's copy of every chat, the events written to your Google calendar, whatever each model company keeps, and the keys, which work until you revoke them.

Developer docs: `docs/DESIGN.md`, "Decisions" and "Security"; `docs/AI_CALLS.md`.
