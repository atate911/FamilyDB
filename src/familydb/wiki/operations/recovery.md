# Recovery: when somebody cannot sign in

> **If nobody can sign in:** run this on the server. It prints a new starting password once; copy it, pass it on and clear the terminal.
>
> ```bash
> sudo /opt/familydb/scripts/maintain.sh password "Sam"
> ```
>
> - **A named person** (use their name on the family list): they sign in with the password and choose their own.
> - **The sign-in page has no name box**, because the family still shares one password. With no name, the command replaces the shared password and signs everyone out. See [The family still shares one password](#the-family-still-shares-one-password).
> - **The only admin forgot theirs:** leave the name out. The command resets the oldest admin who can sign in, meaning the admin who was added to the family list first among those who can sign in.

> **If the page does not open at all, or the program is not running:** `sudo /opt/familydb/scripts/maintain.sh rescue locked-out` shows what it can see, switches the page on if it is off, restarts the bot (which clears "Too many tries"), makes a new password and shows the way in by an SSH tunnel when the address will not open. See [Break glass](/wiki/operations/break-glass#nobody-can-get-in).

This guide needs a sign-in, so a locked-out admin cannot read it. When the page is unreachable, read `/opt/familydb/RUNBOOK.md` on the server.

A new starting password is the whole fix for almost every "I can't get in". The old password stops working at once, and the person is signed out everywhere. Passwords are stored only as hashes, so nobody can look one up, and a new starting password is the only recovery tool there is.

## Somebody forgot their password

An admin signed in as themselves makes a new starting password on [Family](/wiki/controls/family#passwords) for anybody else. It is shown once, for you to pass on. A parent cannot, and nobody can do it for themselves. The person signs in with it and can reach only the page where they choose their own.

If the only admin forgot theirs, use the server command above. Give the name when there is more than one admin: with no name it resets the oldest admin, who may be fine and is signed out. The password cannot be shown again, only replaced by making another.

Whoever can run this on the server is let back in, so root and SSH access are what the whole family trusts. Keep them tight.

## The family still shares one password

Until an admin has a password of their own, the page takes the shared password: the one the installer printed, or one chosen on the Settings page. The sign-in page then asks for a password and no name.

- `maintain.sh password` with no name replaces the shared password and signs everyone out. It prints the new one.
- With an admin's name, it makes that admin a starting password. **From that moment the shared password opens nothing, and everyone signed in with it is signed out.** Give the admin their password first, then tell the family to sign in with their names.
- It refuses to make a starting password for anybody who is not an admin. The first person to sign in as themselves must be an admin, so the family list and the settings always have someone who can change them.

Once an admin has signed in as themselves, the shared password cannot come back through the page, and the last admin who can sign in cannot be removed from the list. Restoring an older [backup](/wiki/operations/backup-and-restore) brings the shared state back, because it is read from the database.

## Too many tries

**Symptom:** the sign-in page says "Too many tries. Wait a quarter of an hour and try again." Even the right password is refused, and making a new one does not clear it.

**Wait 15 minutes.** The limits, and why one address can lock out everyone behind a proxy, are in [Lockouts](/wiki/security/passwords-and-sessions#lockouts).

**Restart if somebody truly cannot wait.** The counts live in memory, so this clears them at once:

```bash
sudo /opt/familydb/scripts/maintain.sh restart
```

A restart interrupts the assistant if it is mid-answer, and it clears the count against a real guesser as well. Use it only when you know nobody is guessing.

## A lost phone, or a sign-in that is too wide

- **One person's phone:** make them a new starting password. It signs them out everywhere, including the lost phone.
- **Everybody:** use **Sign everyone out** on the Sign-in and security page. It asks for your password again, replaces the session key and ends every sign-in on every device, yours included. It cannot be used while `WEB_SECRET_KEY` is set in `.env`; change that value and restart instead.
- A new password, switching someone off, or taking their password away each end that person's sessions on their next click.

## When a secret has been exposed

Getting back in is not the same as recovering from exposure. If somebody else may have seen a key or token:

| Secret | What to do |
|---|---|
| A model company's key | Revoke it in the company's console, make a new one, and enter it on the Settings page (it applies on the next message) or in `.env` and restart |
| The Telegram token | Send `/revoke` to BotFather to get a new token and kill the old one; paste it on the Settings page |
| A person's password | Make a new starting password, as above |
| The session signing key (`data/web_secret`, or `WEB_SECRET_KEY`) | Whoever has it together with the database or `.env` can forge a sign-in. Use **Sign everyone out**, or change `WEB_SECRET_KEY` and restart |
| The Google Calendar key | Make a new key for the service account and connect the calendar again |
| The whole server | The database keeps everything the family said. Rotate every secret above and assume anything stored on the Settings page was read |

A key saved on the Settings page is in every backup, so a leaked backup is a leaked key.

## If none of that is it

- A page that does not open at all is a server problem. Run `maintain.sh check`, then see [Troubleshooting](/wiki/operations/troubleshooting).
- If you can sign in but a page refuses you, that is the person's role. [Roles and permissions](/wiki/model/family-and-roles#roles-and-permissions) says who may open what.
- Sign-in loops and other symptoms are in the runbook, `/opt/familydb/RUNBOOK.md`.
