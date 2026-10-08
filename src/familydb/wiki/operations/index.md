# Running the server

Install FamilyDB, back it up, upgrade it, get somebody back in, and find out what is wrong. [Install and first run](/wiki/operations/install) is the start; the installer puts the page on HTTPS unless you pass `--local-only`, or on Docker without a domain ([HTTPS and the firewall](/wiki/operations/https-and-firewall)).

## When something is wrong

| You are in this spot | Go to |
|---|---|
| Something is broken | [Troubleshooting](/wiki/operations/troubleshooting) |
| Somebody is locked out | [Recovery: when somebody cannot sign in](/wiki/operations/recovery) |
| You need to go back after an upgrade | [Upgrade and rollback](/wiki/operations/upgrade-and-rollback) |

This guide needs a sign-in, so a locked-out admin cannot read it. The runbook is on the server at `/opt/familydb/RUNBOOK.md`.

## A care routine

| How often | What to do | Why |
|---|---|---|
| Weekly | Run `sudo /opt/familydb/scripts/maintain.sh status` and read the line "Last backup" | The nightly backup runs at 03:15 by itself, and nothing alerts you when it stops |
| Monthly | Copy a backup off the server | A backup on the same disk is lost with the disk; see [Backup and restore](/wiki/operations/backup-and-restore) |
| Before an upgrade | Read the newest entry in `CHANGELOG.md` | It says what changes and whether anything needs your hand |
| After an upgrade | Run `sudo /opt/familydb/scripts/maintain.sh check` | It runs the full doctor and names anything that is wrong; see [Upgrade and rollback](/wiki/operations/upgrade-and-rollback) |

The rest of the section: [The command line](/wiki/operations/command-line), [The server](/wiki/operations/host), [The .env file](/wiki/operations/configuration), [Diagnostics](/wiki/operations/diagnostics) and [Cost](/wiki/operations/cost).
