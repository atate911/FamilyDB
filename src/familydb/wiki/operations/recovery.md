# Recovery: when somebody cannot sign in

Make a new starting password for them. That is the whole fix for almost every "I can't get
in": the person signs in with it, chooses their own, and the old one stops working at once.
This page says how, in each situation, and what to check when it is something else.

Most of it needs a command on the server. This guide sits behind the same sign-in as the
page, so a locked-out admin cannot read it: keep a copy of the commands below somewhere you
can reach.

## First: does the sign-in page ask for a name?

- **Yes, a name and a password.** People sign in as themselves. Use the sections below.
- **No, only a password.** The family still shares one password. Skip to
  [The family still shares one password](#the-family-still-shares-one-password).

## Somebody forgot their password

**An admin signed in as themselves can make one from the Family page**, for anybody else:
the new starting password is shown once, for you to pass on. (A parent cannot, and nobody
can do it for themselves.) It signs the person out everywhere. On signing in with it they
are taken to a page to choose their own, and can reach nothing else until they have.

**If the only admin forgot theirs, use the server:**

```bash
sudo /opt/familydb/scripts/maintain.sh password "Sam"     # a person, by their name on the family list
sudo /opt/familydb/scripts/maintain.sh password           # no name: the oldest admin who can sign in
```

(`familydb password [NAME]` does the same where you run `familydb` by hand.) **Always give the
name if there is more than one admin:** with no name it resets the oldest admin, who may be
fine and who is signed out. It prints the new password once, so copy it then, pass it on,
and clear the terminal afterwards (it stays in the scrollback). It cannot be shown again,
only replaced by making another.

Whoever can run this on the server is let back in, which makes access to the server the
root of trust for the whole family. Keep root and SSH access to it tight.

## The family still shares one password

Until an admin has a password of their own, the page takes a password the whole family
shares: the one the installer printed, or one chosen on the Settings page.

- `maintain.sh password` with no name **replaces the shared password** and signs everyone out. It prints the new one.
- With an admin's name, it makes that admin a starting password. **The moment any admin has a password of their own, even a starting one, the shared password stops opening anything and everyone signed in with it is signed out.** Give the admin their password first, and tell the family to sign in with their names afterwards.
- It refuses to make a starting password for anybody who is not an admin: the first person to sign in as themselves has to be an admin, so the family list and the settings always have someone who can change them.

Once an admin has signed in as themselves, the shared password cannot come back through
the page, and the last admin who can sign in cannot be removed from it. (Restoring an
older [backup](/wiki/operations/backup-and-restore) can bring the shared state back, since
it is read from the database.)

## "Too many tries"

After five wrong passwords from one address, that address is kept waiting for fifteen
minutes. After fifty wrong guesses across the whole site, everyone is kept waiting until
fifteen minutes after the first of them, except browsers that have signed in before, which
are spared that site-wide limit so that guessers elsewhere cannot lock the family out. A
known browser is still stopped by the per-address limit, and loses its "known" mark when
that person's password changes. Behind a proxy that is not passing the visitor's address on
(`WEB_TRUST_PROXY` off), every visitor looks like one address, and five wrong guesses lock
everyone out; the installer sets this up correctly.

**While the wait lasts, even the right password is refused, and making a new password does
not clear it.** Wait the fifteen minutes. If somebody truly cannot, the counts are kept in
memory, so `maintain.sh restart` clears them at once. It also interrupts the bot if it is
mid-answer, and clears the count against a real guesser, so use it only when you know nobody
is guessing.

## A lost phone, or a sign-in that is too wide

- **One person's phone:** make them a new starting password, as above. It signs them out everywhere, including the lost phone.
- **Everybody:** "Sign everyone out" on the Sign-in and security page (it asks for your password again) replaces the session key and ends every sign-in on every device, yours included. It cannot be used while `WEB_SECRET_KEY` is set in `.env`; change that value and restart instead.
- A new password, switching someone off, or taking their password away each end that person's sessions on their next click.

## When a secret has been exposed

Getting back in is not the same as recovering from exposure. If a key or token may have been
seen by someone else:

| Secret | What to do |
|---|---|
| An AI company's key | Revoke it in the company's console, make a new one, and enter it on the Settings page (immediate), or in `.env` and restart |
| The Telegram token | `/revoke` in BotFather makes a new one and kills the old; paste it on the Settings page, which picks it up within seconds |
| A person's password | A new starting password, as above |
| The session signing key (`data/web_secret`, or `WEB_SECRET_KEY`) | Whoever has it can forge a sign-in. Use "Sign everyone out", or change `WEB_SECRET_KEY` and restart |
| The Google calendar key | Make a new key for the service account and connect the calendar again |
| The whole server | The database holds everything the family said. Rotate every one of the above and assume anything stored on the Settings page was read |

A key saved on the Settings page is in every backup, so a leaked backup is a leaked key.

## If none of that is it

- Check that the service is running with `maintain.sh status`. A page that does not open at all is a server problem, not a password one, and `maintain.sh check` says what is wrong.
- Sign-in loops and other symptoms are in `RUNBOOK.md` section 13.
- If you can sign in but a page refuses you, that is the person's role: some pages are for admins only, and a few for any grown-up. [Security and trust](/wiki/security) has the table.

Passwords are stored only as hashes, so nobody can look one up and there is nothing on the
server to edit to reset one. A new starting password is the single recovery tool, and it
is the same one an admin uses on the Family page.
