# Recovery: when somebody cannot sign in

## Overview

Almost every "I can't get in" is solved the same way, on the server: make a new
starting password for that person. The person signs in with it, chooses their own,
and the old one stops working at once. This page says which command to use in each
case, what it does to the person's other sessions, and what to check when the
problem is something else.

You need to be able to run commands on the server. That is deliberate: whoever can
run them is let back in, which makes access to the server the root of trust for the
whole family. Keep root and SSH access to it tight. If a person is locked out of the
page, this guide cannot be read either, since it sits behind the same sign-in, so it
is worth knowing where these steps are before you need them.

## Somebody forgot their password

If you can still sign in as an admin, you do not need the server: on the Family page, make
the person a new starting password (it is shown once, for you to pass on). They are signed
out everywhere and, on signing in with it, are taken to a page to choose their own.

If the **only admin** forgot theirs, use the server:

```bash
sudo /opt/familydb/scripts/maintain.sh password            # the first admin who can sign in
sudo /opt/familydb/scripts/maintain.sh password "Sam"      # a particular person, by their name on the family list
```

(`familydb password [NAME]` does the same where you run `familydb` by hand.) It prints
the new password once. Copy it then; it cannot be shown again, only replaced by making
another. The person signs in with their own name and that password, chooses a new one,
and is signed out wherever they were signed in.

## The family still shares one password

Until an admin has chosen a password of their own, the page takes a password the family
shares (the one the installer printed, or one chosen on the Settings page). In that
state:

- `maintain.sh password` with no name **replaces the shared password** and signs everyone out. It prints the new one.
- With the name of an admin, it makes that admin a starting password, so they can sign in as themselves.
- It refuses to give a starting password to anybody who is not an admin: the first person to sign in as themselves must be an admin, so that the family list and the settings always have someone who can change them.

The first admin's own password ends the shared one for good, and from then on the last
admin who can sign in can never be removed, so this cannot quietly come back.

## "Too many tries"

After five wrong passwords from one address, that address is kept waiting for fifteen
minutes. After fifty wrong guesses across the whole site, everyone is kept waiting for
fifteen minutes, except browsers that have signed in before, which carry a signed mark
and are spared the site-wide limit so that guessers elsewhere cannot lock the family out.
The counts are kept in memory, not in the database, so restarting FamilyDB clears them:

```bash
sudo /opt/familydb/scripts/maintain.sh restart
```

Do that only if you are sure it is a slip and not an attack, since it also clears the
count against a real guesser. Waiting fifteen minutes does the same without the risk.

## A lost phone, or a sign-in that is too wide

- **One person's phone:** make them a new starting password, as above. It signs them out everywhere, including the lost phone.
- **Everybody:** "Sign everyone out" on the Sign-in and security page (it asks for your password again) replaces the session key and ends every sign-in on every device, yours included. It cannot be used while `WEB_SECRET_KEY` is set in `.env`; change that value and restart instead.
- A new password, switching someone off, taking their password away, or changing a role so it may not sign in, each ends that person's sessions on their own, because every session carries a mark of the password it was opened with.

## When a secret has been exposed

Recovery of access is not the same as recovery from exposure. If a key or token may have
been seen by someone else:

| Secret | What to do |
|---|---|
| An API key | Revoke it in the company's console, make a new one, and enter it on the Settings page or in `.env` |
| The Telegram token | `/revoke` in BotFather makes a new one and kills the old; paste it on the Settings page, which picks it up within seconds |
| A person's password | A new starting password, as above |
| The whole server | The database holds everything the family said. Rotate every one of the above and assume anything stored on the Settings page was read |

A key saved on the Settings page is in every [backup](/wiki/operations/backup-and-restore),
so a leaked backup is a leaked key.

## If none of that is it

- Check that the service is running: `maintain.sh status`. A page that does not open at all is a server problem, not a password one, and `maintain.sh check` says what is wrong.
- Sign-in loops and other symptoms are in `RUNBOOK.md` section 13.
- If you can sign in but a page refuses you, that is the person's role: some pages are for admins only, and a few for any grown-up. [Security and trust](/wiki/security) has the table.

## Why it is built this way

Passwords are stored only as hashes, so nobody, including you, can look one up, and there
is nothing on the server to edit to "reset" one. A new starting password is the single
recovery tool, and it is the same one an admin uses on the Family page, so there is one
rule for how a password begins: made up, shown once, replaced by the person.
