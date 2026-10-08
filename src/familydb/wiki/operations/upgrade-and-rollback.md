# Upgrade and rollback

```bash
sudo /opt/familydb/scripts/maintain.sh upgrade
```

That is the whole upgrade. It takes a backup first, moves to the newer code, applies any new database [migrations](/wiki/reference/glossary#migration), restarts FamilyDB and prints the commands to go back. Do not use `git pull`: after an upgrade the checkout sits on a [detached commit](/wiki/reference/glossary#detached-commit), where it fails, and it would skip the backup and the dependency install.

## Before you upgrade

- Read the entry for the new version in the repository's `CHANGELOG.md`: settings and pages can move between versions.
- Run `sudo /opt/familydb/scripts/maintain.sh status` and note the `Version:` line. It shows only the version you have installed, not whether a newer one exists.
- Check free disk: the upgrade needs room for a backup (the database plus 50 MB) and the new dependencies. On Docker it rebuilds the image.
- Copy a recent backup off the server if you have not lately; see [Backup and restore](/wiki/operations/backup-and-restore#keep-a-copy-off-the-server).

## What an upgrade does

It tells you its plan and asks `Upgrade now?` before it starts. It needs a terminal to ask, or `--yes`. Then, in order, it:

1. takes a backup, even if it then finds nothing to upgrade to;
2. fetches the newest code from the git remote;
3. chooses a version (below) and stops if you already have it;
4. checks out that version, stops FamilyDB and reinstalls the dependencies at their locked versions. On Docker it rebuilds the image instead, which takes minutes. FamilyDB is down from the stop until the start;
5. applies new migrations and starts FamilyDB;
6. prints how to go back, then runs the doctor.

Read to the bottom. The three rollback commands are printed above the doctor's report, and `Done` does not prove FamilyDB is running: look for `It came back up.`

Your `.env`, your keys and the family's data are not removed. A migration changes the database's layout, and some rewrite rows, so none can be undone. They run in order, once each, and also on every start. The only way back past one is the backup, which is why a rollback restores it. If a saved setting no longer fits after an upgrade, FamilyDB keeps running on `.env`; see [When a value is wrong](/wiki/operations/configuration#when-a-value-is-wrong).

## Which version it moves to

> **While the newest `CHANGELOG.md` heading says "in progress", `upgrade` installs unreleased code.** To stay on a release, move to a tag yourself, as below.

`upgrade` follows the changelog of the code it has just fetched. While the newest heading says "in progress", it follows the default branch. Once a version heading carries a date, it follows the newest release tag (`v…`). The installed copy shows which rule applied to the version you have:

```bash
grep -m1 '^## v' /opt/familydb/CHANGELOG.md
```

- If the new version is the same as yours, older, or already contained in yours, `upgrade` says `Already up to date` and changes nothing else.
- If the two histories have split, which happens after a force-push, it refuses with `moving to it would go backwards` and changes nothing else.

To see the newest release, fetch and list the tags, then compare with the `Version:` line from `status`:

```bash
sudo git -C /opt/familydb fetch --tags origin
sudo git -C /opt/familydb tag -l 'v*' --sort=-v:refname | head -1
```

To move forward to a particular tag yourself, take a backup, then check it out, reinstall the dependencies and restart, which migrates. No restore is needed.

```bash
sudo /opt/familydb/scripts/maintain.sh backup
sudo git -C /opt/familydb checkout --quiet --detach <tag>
sudo uv sync --frozen --no-dev --project /opt/familydb
sudo /opt/familydb/scripts/maintain.sh restart
```

On Docker, replace the `uv sync` line with:

```bash
sudo docker compose --project-directory /opt/familydb build
```

A bare `git checkout` is not enough: it does not reinstall the dependencies, migrate or restart. Moving backward is the rollback below, which loses what was told since the backup.

## The fetch needs a credential

The code is in a private repository, so the fetch has to prove it may read it. Which case you are in depends on how the code first reached the server. If a fetch fails, `upgrade` says what to do.

| Installed with | What happens |
|---|---|
| A [deploy key](/wiki/reference/glossary#deploy-key), the default | Already wired up. It works while the key file stays at `/root/familydb_deploy` and has no passphrase. It does not expire; deleting it on GitHub ends the access |
| A token | The installer did not keep it. Give it for each upgrade; it is used for that fetch only and never written down. Tokens expire |
| A copy you made yourself | There is nothing to fetch. Unpack a new archive over the install, rerun `install.sh` and restart; `docs/INSTALL.md`, "Day to day", has the steps |

With a token, run these. The last line keeps the token from staying in your shell:

```bash
read -rs GITHUB_TOKEN && export GITHUB_TOKEN
sudo --preserve-env=GITHUB_TOKEN /opt/familydb/scripts/maintain.sh upgrade
unset GITHUB_TOKEN
```

To stop needing a token, make a deploy key and point the checkout at it once; `docs/INSTALL.md` shows the three commands. A failed fetch changes nothing about the install, though the backup from step 1 stays behind.

## If it goes wrong

If `upgrade` failed before it checked out the new code, as a failed fetch does, nothing changed: fix the cause and run it again. If it stopped after that, stop FamilyDB, then roll back or finish by hand, and do not run `upgrade` again: the new code is already in place, so a second run says `Already up to date` and does nothing. A failed upgrade also prints no rollback commands, so you find the two values yourself.

1. Find the backup the upgrade took. The log lists every past upgrade, so take the last line:

```bash
sudo grep 'so a bad upgrade can be undone' /var/log/familydb-maintain.log | tail -1
```

The line looks like this, and the path follows `Write a backup to`:

```text
03:15:07 change: Write a backup to /opt/familydb/backups/familydb-20261007031507123456789.sqlite3 :: so a bad upgrade can be undone
```

2. Find the commit that was installed:

```bash
sudo git -C /opt/familydb reflog | grep 'moving from' | head -3
```

The newest line is the upgrade. Copy the word after `moving from`, here `3b2a1c0`:

```text
9d8e7f6 HEAD@{0}: checkout: moving from 3b2a1c0 to origin/main
```

3. Stop FamilyDB. On a virtualenv install:

```bash
sudo systemctl stop familydb
```

On Docker:

```bash
sudo docker compose --project-directory /opt/familydb stop bot
```

4. Finish the upgrade or go back, as below.

To finish it, fix what the error names, reinstall the dependencies (the `uv sync` or `build` line above) and run `sudo /opt/familydb/scripts/maintain.sh restart`. A migration that failed leaves FamilyDB stopped, with the migrations before it already applied.

To go back, database and all, run these three commands in this order, with your two values. A successful upgrade prints the same three with the values filled in.

```bash
sudo git -C /opt/familydb checkout --quiet --detach <the commit that was installed>
sudo uv sync --frozen --no-dev --project /opt/familydb
sudo /opt/familydb/scripts/maintain.sh restore <the backup the upgrade took>
```

On Docker, the second command is:

```bash
sudo docker compose --project-directory /opt/familydb build
```

The order matters. The old code goes back first, then its dependencies, because the restore runs on the code that is checked out. The restore comes last because it also restarts FamilyDB. The database goes back too, because the upgrade's migrations have run and the older code would be looking at a database newer than it knows. The restore asks for confirmation at a terminal.

> **Everything told to FamilyDB since the upgrade's backup is lost.** The database you replaced is kept as a [safety backup](/wiki/reference/glossary#safety-backup), named at the end of the restore. It is in the new layout and is pruned after about two weeks like any other backup.

Use the backup the upgrade took, not just the newest file in the folder: a nightly backup or a second `upgrade` may be newer and already hold the new layout.

## After an upgrade

Run the check and confirm the version:

```bash
sudo /opt/familydb/scripts/maintain.sh check
sudo /opt/familydb/scripts/maintain.sh status
```

You should see no `✗` in the check and the new version on the `Version:` line. Then open Status and send one message to see that FamilyDB answers.

An upgrade does not rewrite the service file; see [Known limits](/wiki/reference/known-limits#an-upgrade-does-not-rewrite-the-service-file). A Docker install whose Caddy kept its certificate in `data/caddy` should move it to `caddy/`; the runbook explains.
