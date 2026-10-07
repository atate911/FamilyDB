# Upgrade and rollback

## Overview

Upgrading is one command, and it is built so that a bad upgrade can be undone. It
takes a backup first, moves to the newer code, applies any new database migrations,
restarts, and prints the exact commands to go back. This page covers what it does,
what it needs, how to read its output, and how to roll back.

```bash
sudo /opt/familydb/scripts/maintain.sh upgrade
```

**Do not use `git pull`.** After an upgrade the checkout sits on a detached commit, where
`git pull` fails, and it would skip the backup and the dependency install.

## What an upgrade does

It tells you its plan and asks before it starts. Then, in order:

1. **Takes a backup** (see [Backup and restore](/wiki/operations/backup-and-restore)), kept so a bad upgrade can be undone.
2. **Fetches the newest code** from the git remote.
3. **Chooses a version** (below), and does nothing if you already have it.
4. **Checks out** that version, stops the bot, and reinstalls the dependencies at their locked versions (on Docker, rebuilds the image).
5. **Applies new migrations** and starts the bot.
6. Runs `familydb doctor`, and prints how to go back.

Your `.env`, your keys and everything the family has told it are not touched. Migrations
are applied in order and are only ever added, never edited once applied, and they also run
on every start. After an upgrade, a setting that no longer validates is named in one line
in the log.

## Which version it moves to

It follows the changelog. While the newest `CHANGELOG.md` heading says "in progress", the
install follows the default branch and an upgrade moves along it. Once a version heading
carries a date, installs and upgrades follow the newest release tag.

An upgrade only **moves forward**. If the target does not contain everything that is
installed, it refuses with "moving to it would go backwards" and changes nothing. The
reason is the database: a release older than what is installed would take the code back
past migrations the database has already run. To choose a version by hand, check it out
yourself with `sudo git -C /opt/familydb checkout NAME`, with the caution that this is
your responsibility.

## The fetch needs a credential

The code is in a private repository, so the fetch needs to prove it may read it. Which
case you are in depends on how the code first got onto the server. If a fetch fails,
`upgrade` says all of this itself and changes nothing.

| Installed with | What happens |
|---|---|
| A deploy key (the default) | Already wired up. It works as long as the key file stays at `/root/familydb_deploy` |
| A token | The installer deliberately did not keep it. Give it for each upgrade: `read -rs GITHUB_TOKEN && export GITHUB_TOKEN`, then `sudo --preserve-env=GITHUB_TOKEN /opt/familydb/scripts/maintain.sh upgrade`. It is used for that fetch only and never written down. Tokens expire, so to stop needing one, make a deploy key and point the checkout at it |
| A copy you made yourself | There is nothing to fetch from. Back up, make a new archive, unpack it over the install (`.env` and `data/` are not in the archive), rerun `install.sh`, and restart. `docs/INSTALL.md`, "Day to day", has the steps |

A deploy key never expires, which is why it is the default.

## Rolling back

When an upgrade finishes it prints three commands, with this machine's real values filled
in. They go back to what was installed, **database and all**, in this order:

```bash
sudo git -C /opt/familydb checkout --quiet --detach <the commit that was installed>
sudo uv sync --frozen --no-dev --project /opt/familydb          # Docker: docker compose build
sudo /opt/familydb/scripts/maintain.sh restore <the backup the upgrade took>
```

The order is the point. The code goes back first, then its dependencies, and the restore
comes last because it restarts the bot on whatever code is checked out. The restore is
needed, and not only the code, because the upgrade may have run migrations: the older code
would be looking at a database newer than it knows. Everything the family told the bot
between the upgrade and the rollback is lost with the restore, so decide quickly.

Keep the output of the upgrade until you are happy with the new version. If you lose it,
the commit that was installed is in `git -C /opt/familydb reflog`, and the backup is the
newest `familydb-*.sqlite3` in `/opt/familydb/backups/` from just before the upgrade.

## After an upgrade

- Look at `maintain.sh status` for the new version and `maintain.sh check` for anything the doctor flags. The upgrade already runs the doctor at the end.
- Read the `CHANGELOG.md` entry for what changed. Settings and pages can move between versions.
- Open the Status page and send one message to see that it answers.

## Why it is built this way

- **Backup first, with the rollback printed**, because the usual reason to roll back is something noticed an hour later, when nobody remembers what to type.
- **Forward only** protects the database. Going back is a deliberate, three-step act that includes restoring, not a single checkout that quietly leaves a newer database under older code.
- **A detached commit and locked dependencies** mean the code on the server is exactly a commit you can name, and the same libraries that were tested.
- **Nothing in `.env` or the data folder is touched**, so an upgrade is the program changing and the family's information staying put.

`RUNBOOK.md` section 8 has the same procedure in short.
