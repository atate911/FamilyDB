# Upgrade and rollback

```bash
sudo /opt/familydb/scripts/maintain.sh upgrade
```

That is the whole upgrade. It takes a backup first, moves to the newer code, applies any
new database migrations, restarts, and prints the commands to go back. This page covers
what it does, what it needs, what to do if it stops partway, and how to roll back.
**Do not use `git pull`:** after an upgrade the checkout sits on a detached commit, where it
fails, and it would skip the backup and the dependency install.

## If something has gone wrong

Do these in order, and **do not run `upgrade` again**: after a failed upgrade it can say
"Already up to date" and do nothing (see [If the upgrade stops partway](#if-the-upgrade-stops-partway)).

1. Find the backup the upgrade took. Its path was printed near the top ("Write a backup to ..."), and is in the log: `sudo grep -B1 'so a bad upgrade can be undone' /var/log/familydb-maintain.log`.
2. Stop the bot: `sudo systemctl stop familydb` (Docker: `sudo docker compose --project-directory /opt/familydb stop bot`).
3. Run the three commands under [Rolling back](#rolling-back).

## What an upgrade does

It tells you its plan and asks before it starts (it needs a terminal to ask, or `--yes`).
Then, in order:

1. **Takes a backup** (see [Backup and restore](/wiki/operations/backup-and-restore)), so a bad upgrade can be undone. It does this even if it then finds nothing to upgrade to.
2. **Fetches the newest code** from the git remote.
3. **Chooses a version** (below), and stops if you already have it.
4. **Checks out** that version, stops the bot, and reinstalls the dependencies at their locked versions. On Docker it rebuilds the image instead, which can take minutes. The bot is down from the stop until the start.
5. **Applies new migrations** and starts the bot.
6. Prints how to go back, then runs `familydb doctor`.

Read to the bottom. The three rollback commands are printed **above** the doctor's report,
and "Done" does not prove the bot is running: look for "It came back up".

Your `.env`, your keys and the family's data are not removed. **Migrations change the
database's layout, and sometimes rewrite rows in it, and they cannot be undone.** They are
applied in order, once each, and also run every time the bot starts. The only way back past
one is the backup, which is why rolling back restores it. If a stored setting no longer
fits after an upgrade, the log says "stored settings are not usable", names it, and the bot
keeps running on `.env`; read it with `maintain.sh logs`, then fix or empty that setting on
the Settings page.

## Which version it moves to

It follows the changelog. While the newest `CHANGELOG.md` heading says "in progress", the
install follows the default branch. Once a version heading carries a date, it follows the
newest release tag (`v…`).

- If the new version is the same as yours, older, or already contained in yours, it says "Already up to date" and stops, changing nothing else.
- If the two histories have split apart, it refuses with "… moving to it would go backwards" and changes nothing else. That happens after a force-push, for example.
- To move to a particular version, use the rollback steps below with that commit in place of the old one, and restore a backup from before you ran the newer code. A bare `git checkout` is not enough: it does not reinstall the dependencies, migrate, or restart.

## The fetch needs a credential

The code is in a private repository, so the fetch has to prove it may read it. Which case
you are in depends on how the code first got onto the server. If a fetch fails, `upgrade`
explains what to do (for a deploy key or a token; a copy you made yourself has nothing to
fetch from, and it says so briefly).

| Installed with | What happens |
|---|---|
| A deploy key (the default) | Already wired up. It works while the key file stays where the installer put it, `/root/familydb_deploy`, and the key has no passphrase. It does not expire on its own; deleting it on GitHub ends the access |
| A token | The installer deliberately did not keep it. Give it for each upgrade: `read -rs GITHUB_TOKEN && export GITHUB_TOKEN`, then `sudo --preserve-env=GITHUB_TOKEN /opt/familydb/scripts/maintain.sh upgrade`. It is used for that fetch only and never written down. Tokens expire |
| A copy you made yourself | Nothing to fetch. Unpack a new archive over the install (`.env` and `data/` are not in it), rerun `install.sh`, restart. `docs/INSTALL.md`, "Day to day", has the steps |

To stop needing a token, make a deploy key and point the checkout at it once
(`docs/INSTALL.md` shows the three commands). A failed fetch changes nothing about the
install, though the backup from step 1 stays behind.

## If the upgrade stops partway

If it stops with an error after "Checking out", the bot is stopped and the new code is
already in place, and **running `upgrade` again will say "Already up to date" and do
nothing**. Either finish it by hand, or go back:

- *Finish it:* fix what the error names, then `sudo uv sync --frozen --no-dev --project /opt/familydb` (Docker: `sudo docker compose --project-directory /opt/familydb build`), then `sudo /opt/familydb/scripts/maintain.sh restart`. A migration that failed leaves the bot stopped, with the migrations before it already applied.
- *Go back:* the three commands below. The old commit is in the log, and in `git -C /opt/familydb reflog`, on the first "moving from X to …" line for the upgrade.

## Rolling back

When an upgrade finishes it prints three commands, with this machine's real values filled
in. They go back to what was installed, **database and all**. Stop the bot first
(otherwise code and dependencies change under a running service), then run them in this
order:

```bash
sudo git -C /opt/familydb checkout --quiet --detach <the commit that was installed>
sudo uv sync --frozen --no-dev --project /opt/familydb          # Docker: docker compose build
sudo /opt/familydb/scripts/maintain.sh restore <the backup the upgrade took>
```

The order matters. The old code goes back first, then its dependencies, because the restore
itself runs on the code that is checked out: it validates the backup with the virtualenv's
Python and migrates with `familydb`. The restore comes last because it also restarts the
bot. The database has to go back too, and not only the code, because the upgrade's
migrations have run and the older code would be looking at a database newer than it knows.
The restore asks for confirmation at a terminal.

Everything told to the bot since the upgrade's backup is missing from the restored
database. The database you replaced is kept as a safety backup, named at the end of the
restore, though it is in the new layout and is pruned after about two weeks like any other
backup. **Use the backup the upgrade took, not just the newest file** in the folder: a
nightly backup or a second `upgrade` run may be newer and already hold the new layout.

## After an upgrade

`maintain.sh status` shows the new version, and `maintain.sh check` repeats the doctor.
Read the `CHANGELOG.md` entry for what changed, since settings and pages can move between
versions, open the Status page, and send one message to see that it answers. A Docker install
that kept Caddy's certificate in `data/caddy` should move it to `caddy/`; `RUNBOOK.md`
section 8 explains.

`RUNBOOK.md` section 8 has the same procedure in short.
