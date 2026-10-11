# Upgrade and rollback

```bash
sudo /opt/familydb/scripts/maintain.sh upgrade
```

That is the whole upgrade. It stops FamilyDB, takes a backup, moves to the newer code, applies any new database [migrations](/wiki/reference/glossary#migration), starts FamilyDB again. It prints the commands to go back before the code moves, and a failure before the migrations puts the old code back and starts FamilyDB again by itself. Do not use `git pull`: after an upgrade the checkout sits on a [detached commit](/wiki/reference/glossary#detached-commit), where it fails, and it would skip the backup and the dependency install.

## Before you upgrade

- Read the entry for the new version in the repository's `CHANGELOG.md`: settings and pages can move between versions.
- Run `sudo /opt/familydb/scripts/maintain.sh status` and note the `Version` row. It shows only the version you have installed, not whether a newer one exists.
- Check free disk: the upgrade needs room for a backup (the database plus 50 MB) and the new dependencies. On Docker it rebuilds the image.
- Copy a recent backup off the server if you have not lately; see [Backup and restore](/wiki/operations/backup-and-restore#keep-a-copy-off-the-server).
- Put any change you made to a file that ships with FamilyDB somewhere the upgrade leaves alone. It refuses to run, before it asks, while such a file is changed, naming the file: an upgrade would overwrite it. A change to `docker-compose.yml` belongs in `docker-compose.override.yml`, which Compose reads on top of the shipped file. For anything else, keep a copy and put the shipped file back: `sudo git -C /opt/familydb checkout -- FILE`.

## What an upgrade does

It fetches first, which changes nothing the bot runs, so it can tell you what this upgrade would do. The screen reads like the top of a pull request, and shows only what is not routine:

- **Installed** and **Upgrading**, one above the other: each as the release it is built on and the commits since (`v0.2.0+137`), with its hash and date, and what it follows (`on main, where v0.3.0 is in progress`). Where you stand and where you are going, side by side;
- one line of numbers (how many commits and from which pull requests, how many files and lines), then git's own `++++----` bars for the parts of the code that change most, drawn to scale, each with its counts;
- the newest commits, and what the changelog says is new;
- **Database**, only when there are new migrations: they are named, with a reminder that some rewrite what is in the database, so the backup is what goes back;
- **Packages**, only when `uv.lock` moves: each from what to what;
- **Settings**, only when `.env.example` has new options, and **Service file**, only when `deploy/familydb.service` changed: the installed one is updated to match when it is as the installer wrote it, with a copy kept beside it, and left as it is when it was edited by hand.

A part that does not change is not mentioned: no `Database` line means no new migrations. Then it asks `Upgrade now? [Y/n]`: Enter says yes. It needs a terminal to ask, or `--yes`; `--dry-run` shows all of it and does none of it.

After a yes it checks the install as it is (so that what the check says afterwards is about the upgrade), checks there is room, stops FamilyDB, takes a backup and prints the commands to go back, with this run's commit and backup in them. While it works, one line shows what it is doing: a bar of how many of the eight steps are done (the one under way pulsing), its percent, `5/8`, the step and the seconds. The wait for the page fills a bar toward its 30 seconds instead. The steps are: the first check, stopping FamilyDB, the backup, checking the new version out, reinstalling the dependencies at their locked versions, applying the new migrations, starting FamilyDB and waiting up to 30 seconds for the page to answer, and running the doctor. FamilyDB is stopped before the code moves because a running one would pick up new files as they land, and the backup is taken once it is stopped so that nothing said to it meanwhile is missed. On Docker the order differs: the new image is built from the new code while the old containers keep running (which takes minutes), and only then are they stopped, for the backup, the migrations and the start. If the scripts themselves changed in the new version, the `maintain.sh` that came with it finishes the upgrade, so a release can change these steps. A step that goes as expected has no line of its own; what is shown is the backup, the packages and migrations it applied, how long FamilyDB was away, and the check, which lists only what must be fixed (`✗`) and counts the rest, with what the counts were before when they changed. A problem that was already there is shown and marked `(the same before the upgrade)`, and is not blamed on the upgrade; only a new one makes it `[WARN]`. A step that fails stops the run with what it said. If it fails before the migrations, the upgrade puts back what it changed, the code, its packages, the service file and on Docker the image, starts FamilyDB again and says so under the error: nothing in the database has changed, and there is nothing to finish.

If you already have the newest version and the upgrade is finished, it shows the **Installed** row and says `Already up to date`, takes no backup and changes nothing. If FamilyDB is not running at that point, which is how an upgrade whose restart failed leaves things, it says so as `[WARN]` and names `restart`.

The last line stands alone, for a log or a mail: `[ OK ] Upgraded v0.2.0+137 → v0.3.0+4 · 14 commits · 2 migrations · 3 packages · down 14s (48s)`, or `[WARN] … but the check found 2 new problems`, or `[FAIL] … but FamilyDB did not start` (and the exit status is 1); any warnings are listed again under it. Above it is the run's bar, full when every step ran, and short and red where a run that stopped got to.

On a terminal that can follow links, the pull request numbers and commit hashes open on GitHub. The commands to go back are printed again below only when something went wrong. How to read the rest of the screen is in [Reading what it prints](/wiki/operations/command-line#reading-what-it-prints).

Your `.env`, your keys and the family's data are not removed. A migration changes the database's layout, and some rewrite what is in it, so none can be undone. They run in order, once each, and also on every start. The backup taken first covers them, and the only way back past one is restoring it, which is why a rollback does. If a saved setting no longer fits after an upgrade, FamilyDB keeps running on `.env`; see [When a value is wrong](/wiki/operations/configuration#when-a-value-is-wrong).

## Which version it moves to

`upgrade` moves to the newest commit on the default branch, whether or not a release has been tagged for it. Work merged there arrives on the next upgrade; it does not wait for a version number. The `Upgrading` row says which branch it follows and, while the newest `CHANGELOG.md` heading says "in progress", which version is being built there.

- If the new version is the same as yours, older, or already contained in yours, and no earlier upgrade is unfinished and the database is migrated, `upgrade` says `Already up to date`, takes no backup and changes nothing else. Otherwise it finishes the earlier upgrade; see [If it goes wrong](#if-it-goes-wrong).
- If the two histories have split, which happens after a force-push, it refuses with `moving to it would go backwards` and changes nothing else.

To see the newest release, fetch and list the tags, then compare with the `Version` row from `status`:

```bash
sudo git -C /opt/familydb fetch --tags origin
sudo git -C /opt/familydb tag -l 'v*' --sort=-v:refname | head -1
```

To move forward to a particular tag yourself, take a backup, then check it out, reinstall the dependencies and restart, which migrates. No restore is needed. The next `upgrade` leaves the tag and follows the branch again, so a tag is a place to stop for now, not a setting.

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

A fetch that fails says what git said and what it means: the network or GitHub not answering (try again later), a credential this checkout lacks (the table above), a remote that is gone, or a checkout git will not read because somebody else owns it (the doctor puts the ownership right). It never waits for a password to be typed.

With a token, run these. The last line keeps the token from staying in your shell:

```bash
read -rs GITHUB_TOKEN && export GITHUB_TOKEN
sudo --preserve-env=GITHUB_TOKEN /opt/familydb/scripts/maintain.sh upgrade
unset GITHUB_TOKEN
```

To stop needing a token, make a deploy key and point the checkout at it once; `docs/INSTALL.md` shows the three commands. A failed fetch changes nothing about the install, though the backup from step 1 stays behind.

## If it goes wrong

The upgrade prints the commands to go back before it checks out the new code, and prints them again at the foot of any failure after the migrations began, together with the command to finish. Copy them from the terminal. A failure before the checkout, such as a failed fetch, changes nothing. A failure after it but before the migrations, such as the packages not installing, is undone by the upgrade itself: the old code, packages, service file and image are put back and FamilyDB started again, and the screen says so. In both cases, fix the cause and run `upgrade` again.

If it stops after the checkout, the code is new but the dependencies, migrations or restart may not all be done, and FamilyDB may be stopped. You have two ways out.

To finish, fix what the error names and run `upgrade` again:

```bash
sudo /opt/familydb/scripts/maintain.sh upgrade
```

An upgrade writes `/var/lib/familydb-install/upgrade-pending` when it moves the code and removes it once the dependencies and migrations are done. While that file exists, or the database is behind the code's newest migration, a second run says what is unfinished and finishes it instead of saying `Already up to date`. It keeps the first run's rollback point, the commit and backup from before the upgrade.

The simplest way back, whether the upgrade stopped or finished and turned out badly, is one command that does those steps for you:

```bash
sudo /opt/familydb/scripts/maintain.sh rescue rollback
```

`upgrade` records what it moved from and to, so this works after the upgrade finished too. It puts only the code back when no migration ran (nothing saved is lost), and the database from before the upgrade too when one did, after a typed `yes`. [Break glass](/wiki/operations/break-glass#an-upgrade-broke-it) describes it. To do it by hand instead, run the three commands the upgrade printed, in that order:

```bash
sudo git -C /opt/familydb checkout --quiet --detach <the commit that was installed>
sudo env UV_CACHE_DIR=/opt/familydb/.cache/uv UV_PYTHON_INSTALL_DIR=/opt/familydb/.local/share/uv/python uv sync --frozen --no-dev --project /opt/familydb
sudo /opt/familydb/scripts/maintain.sh restore <the backup the upgrade took>
```

The two variables on the second line keep uv's cache and Python inside the install, where the installer put them and where the `familydb` account can run it; without them, a uv that has to build the virtualenv again on a server whose own Python is too old fetches a Python into root's home and builds on that, which the service cannot start. The upgrade prints the line with them in.

On Docker, the second command is:

```bash
sudo docker compose --project-directory /opt/familydb build
```

The order matters. The old code goes back first, then its dependencies, because the restore runs on the code that is checked out. The restore comes last because it also restarts FamilyDB. The database goes back too, because the upgrade's migrations have run and the older code would be looking at a database newer than it knows. The restore asks for confirmation at a terminal.

> **Everything told to FamilyDB since the upgrade's backup is lost.** The database you replaced is kept as a [safety backup](/wiki/reference/glossary#safety-backup), named at the end of the restore. It is in the new layout and is pruned after about two weeks like any other backup.

Use the backup the upgrade took, not just the newest file in the folder: a nightly backup or a second `upgrade` may be newer and already hold the new layout.

If you have lost the printed commands, find them again. The maintain log names the backup; take the last line:

```bash
sudo grep 'so a bad upgrade can be undone' /var/log/familydb-maintain.log | tail -1
```

The path follows `Write a backup to`. The commit is the word after `moving from` in the newest line of:

```bash
sudo git -C /opt/familydb reflog | grep 'moving from' | head -3
```

## After an upgrade

Run the check and confirm the version:

```bash
sudo /opt/familydb/scripts/maintain.sh check
sudo /opt/familydb/scripts/maintain.sh status
```

You should see no `✗` in the check and the new version on the `Version` row. Then open Status and send one message to see that FamilyDB answers.

A Docker install whose Caddy kept its certificate in `data/caddy` should move it to `caddy/`; the runbook explains.
