# The command line

Use `maintain.sh` for looking after the server and `familydb` for everything else the web page cannot do: checking the install, running now what a job would run later, and making a password for somebody locked out. Everything the family does day to day is on the web page or in Telegram.

| Family | What it is | Use it for |
|---|---|---|
| `maintain.sh` | A script in `/opt/familydb/scripts`. It works the same on a virtualenv and a Docker install | Status, backups, upgrades, logs, restarts, HTTPS, ports, passwords |
| `familydb` | The program itself. Run it as described in [How to run it](#how-to-run-it) | Checks, inspecting data, running a job by hand |
| Telegram commands | What a family member types in Telegram | See [Telegram: commands and buttons](/wiki/controls/telegram) |

## The maintain.sh commands

Every command is `sudo /opt/familydb/scripts/maintain.sh <command>`. `--dry-run` says what would happen and changes nothing; `--yes` skips the questions. `maintain.sh --help` lists them all.

| Command | What it does |
|---|---|
| `status` | One screen: a verdict first (running and well, or what needs attention), then the version, the service, whether the page answers, the address, the database, the disk and the newest backup with its schedule, and the commands that put right anything that is not well. Changes nothing |
| `check` | Looks at everything that has to be right for the page to come up, the machine first and then the program's own check, and prints what is wrong with its fix. It only reads. `--all` lists every row, `--online` adds the checks that need the internet. See [Diagnostics](/wiki/operations/diagnostics) |
| `doctor` | For "it is broken and I do not know why": looks, says what is wrong and why, shows what it will do, does the safe steps on one Enter, looks again and says what came right. `--dry-run` shows the plan only. See [The doctor](/wiki/operations/break-glass#the-doctor) |
| `rescue [WHAT]` | The ways out when the usual fixes are not enough: `locked-out`, `wont-start`, `rollback`, `database`, `space`, or a menu. See [Break glass](/wiki/operations/break-glass) |
| `backup` | Takes a backup now. See [Backup and restore](/wiki/operations/backup-and-restore) |
| `restore FILE` | Stops FamilyDB, puts that backup in place, starts it again. Refuses a backup from a newer version before stopping anything |
| `upgrade` | Takes a backup, moves to the newer code, migrates, restarts. See [Upgrade and rollback](/wiki/operations/upgrade-and-rollback) |
| `logs [N]` | Shows the last N lines (50 by default) and then follows the log until you press Ctrl-C |
| `restart` | Restarts FamilyDB and says whether it came back |
| `schedule-backups` | Puts the nightly backup in root's crontab; `--keep-days N` sets how long backups are kept |
| `https [DOMAIN]` | Puts the web page on HTTPS and gets the certificate. `--port N` or `--port random` moves it. See [HTTPS and the firewall](/wiki/operations/https-and-firewall) |
| `port N` | Moves FamilyDB's own port (8080 unless moved). See [HTTPS and the firewall](/wiki/operations/https-and-firewall#move-the-public-port) |
| `password [NAME]` | Makes a new starting password and prints it once. See [Recovery](/wiki/operations/recovery) |

## Reading what it prints

A run shows what is different this time and what it is doing, and leaves out what you already know and anything that is as expected:

1. **A title bar**, like the top of an old DOS window: the command on the left, the install and how it runs on the right. With `--dry-run` a `[ DRY RUN ]` badge follows, and nothing below it is done.
2. **What this run changes**, where there is something to say. `upgrade` fetches first and shows the commits, the pull requests and the changelog, and, only when they change, the new migrations, the packages that move and the new settings, as a pull request would: no line means nothing changed. `restore` shows the backup and what it replaces; `port` and `https` show the port before and after. Then it asks, and **Enter is yes** (`[Y/n]`). Only `restore`, which cannot undo itself, has Enter as no (`[y/N]`). `--yes` skips the question.
3. **The steps that tell you something**: a line each for the backup, what was installed, the migrations applied, how long the bot was away and the check. A step that goes as expected has no line; one that fails stops with the command that ran, its exit code, what it said, what that usually means and what to try, and a failure after the code has moved also says how to go back or finish. A step that takes time shows a line that redraws itself, with the classic `| / - \` spinner: on a command with fixed steps (`upgrade`, `restore`, `restart`) a bar of how many are done, the one under way pulsing, with its percent and `4/8`; on a wait with a limit (the page answering after a restart) a bar filling toward it; otherwise the seconds so far.
4. **The foot of the window and a last line.** The foot is the run's bar with its percent, full when every step ran, and short and red where a run that stopped got to; a step that fails shows it too, above what went wrong. The last line is a badge, `[ OK ]`, `[WARN]` or `[FAIL]`, and how long it took. A warning count is in the line, and each warning is listed again under **Warnings**, since they scroll past. For an upgrade it carries where it was and where it is (`v0.2.0+137 → v0.3.0+4`), what moved and how long the bot was away, so it can be read alone in a log, and the rule above it is the run's bar: full when every step ran, short and red where a run that stopped got to.

The exit status is 0, or 1 when the last line says `[FAIL]`: the bot did not come back after an upgrade, restore or restart, `check` found something that must be fixed (and said which first, and which way out to try), or `status` found it not running or something red. A monitor or a cron job can read that instead of the words. A problem that was there before an upgrade does not fail it: the check is run before and after, and only what is new is the upgrade's.

The marks differ in shape as well as colour (`✓` fine, `!` worth a look, `✗` must be fixed, `·` skipped, `○` not done because of `--dry-run`), so a screen with no colour reads the same. Commands you would type are in cyan, and their `# comments` are dim. Commit hashes are yellow, pull request numbers cyan, `+` green and `-` red, as git draws them; the first word of a step is bold, and how long a slow step took sits at the right edge. Colour is for a terminal: nothing is coloured in a pipe or a log, `NO_COLOR=1` turns it off anywhere, and `FORCE_COLOR=1` turns it on for `| less -R`. `FAMILYDB_ASCII=1` draws it in plain characters, which a terminal whose locale is not UTF-8 is given without being asked (`FAMILYDB_UNICODE=1` says otherwise). On a terminal that can follow links, a pull request number or a commit hash in the upgrade screen opens it on GitHub; `FAMILYDB_NO_LINKS=1` turns that off, and a pipe or a log never has them. The redrawing line is only drawn at a terminal where nothing can stop to ask for a password over it, never in a dry run, and `FAMILYDB_NO_LIVE=1` turns it off; in a pipe or from cron, each step prints one line when it is done.

Everything a run prints is also kept, without colour, in `/var/log/familydb-maintain.log`: send that file when asking for help.

There is no `maintain.sh` command to stop or start FamilyDB on its own. Use these:

On a virtualenv install:

```bash
sudo systemctl stop familydb
sudo systemctl start familydb
```

On Docker:

```bash
sudo docker compose --project-directory /opt/familydb stop bot
sudo docker compose --project-directory /opt/familydb start bot
```

On Docker, `https` only moves the port of a web page that is already on HTTPS; the other commands work as written.

## How to run it

The `familydb` program must run as the `familydb` account (or the name given with `--user` at install) from the install folder, so it reads the same `.env` and database as the service. On a virtualenv install:

```bash
cd /opt/familydb && sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb <command>
```

On Docker, run it in a fresh container:

```bash
sudo docker compose --project-directory /opt/familydb run --rm -T bot familydb <command>
```

Two commands read better inside the running container, because a fresh one has no terminal and nothing listening on the web page's port. Use `exec` for `doctor` and `repl`:

```bash
sudo docker compose --project-directory /opt/familydb exec bot familydb doctor
sudo docker compose --project-directory /opt/familydb exec -it bot familydb repl
```

The container has no `.env` file, only the values Compose passes in, so the doctor always warns `no .env` there. `maintain.sh check` uses the fresh container, so its report also warns `nothing is listening on port 8080` on Docker. Neither warning means anything is wrong.

The other pages write these commands as `familydb <command>` and link here. `familydb --help` lists every command, `familydb <command> --help` its options and `familydb --version` the version.

## Look at things

These show things and send nothing. On a database that has never been opened, or one from an older version, most of them first create or upgrade it, which is harmless. `doctor --fix` is the exception: it changes things.

| Command | What it shows |
|---|---|
| `familydb doctor [--online] [--fix] [--json]` | Checks the install end to end and prints a fix under anything wrong; exits with status 1 when something must be fixed. `--online` is free: it asks Telegram whether the token is live, counts tokens on Anthropic or Gemini and checks the setup's links. `--fix` makes `.env` and the login key owner-only and applies pending migrations |
| `familydb config` | Every setting with secrets masked, and where each value came from: **set on the settings page**, **from the environment**, or no mark for a default |
| `familydb db status` | The schema version, row counts and the last few model calls |
| `familydb members list [--all]` | The family list; `--all` includes people switched off |
| `familydb ideas list [--all]` | The ideas, one line each, presents included; `--all` adds dropped ideas |
| `familydb debug cost [--days N]` | What the last N days (30 by default) cost per purpose and model |
| `familydb debug prompt [TEXT] [--as NAME] [--kind KIND] [--idea N]` | The exact request that would be sent, without sending it. `--kind` is chat, digest, retry or enrich |
| `familydb tool --list` | The tools, whether each is available and which write |
| `familydb google events [--days N]` | The next 7 days (or N) on the family calendar, as a connection test |
| `familydb debug validate-tools` | Asks the API to validate the tool definitions. It needs an Anthropic or Gemini key and fails on OpenAI |

## Status commands

`maintain.sh status` prints the version, whether the service is running (on Docker, the container list), the database path and size, free disk, the newest backup with its date, and whether a nightly backup is scheduled. It warns when there is no database or no backup, and it does not judge health. `maintain.sh check` runs the doctor and prints every finding with its fix. `familydb db status` prints the schema version, row counts and the last few model calls, and upgrades an older database first. For the doctor on a running Docker install, use the `exec` form under [How to run it](#how-to-run-it).

## Change something now

These act on the real data. None of them asks a model.

| Command | What it does |
|---|---|
| `familydb password [NAME]` | Makes a new starting password and prints it once. With no name it resets the oldest admin who can sign in; if the family still shares one password, it replaces that one for everyone. See [Recovery](/wiki/operations/recovery) |
| `familydb db backup DEST` | Copies the database with SQLite's online backup. For a backup you keep, use `maintain.sh backup`, which also makes the file owner-only; on Docker `DEST` is inside the container |
| `familydb db migrate` | Applies pending [migrations](/wiki/reference/glossary#migration). The service and `maintain.sh upgrade` do it for you |
| `familydb members add NAME [--role admin\|parent\|kid]` | Adds a person, a parent unless `--role` says otherwise. It skips the Family page's checks, so use the [Family page](/wiki/controls/family) for anyone but the first admin |
| `familydb google connect KEY_FILE CALENDAR_ID` | Connects the calendar from the server. It tests the key by reading the calendar and making and deleting a one-day test event, then saves it |
| `familydb follow-ups [--now]` | Shows the schedule; with `--now`, sends the how-did-it-go message for each finished plan. No model call |
| `familydb tool NAME --json '{...}' [--as NAME]` | Runs one tool with no model. Tools marked writing change the real data, and the calendar tools the real Google calendar |

## Commands that cost money

Each model call goes through the same daily spending limit as the rest.

| Command | What it does |
|---|---|
| `familydb chat TEXT [--as NAME] [--fresh]` | Talks to the assistant in its console chat. Everything it does is real: it saves messages and may add ideas, things to do or calendar events |
| `familydb repl [--as NAME] [--fresh]` | The same, as an interactive session |
| `familydb db retry-failed [--reset]` | Asks again about failed messages and sends the replies. `--reset` first makes given-up messages eligible again, including ones given up on purpose |
| `familydb digest [--now]` | Shows the weekend ideas schedule; with `--now`, sends them to the chat chosen under Messages, once a day at most |
| `familydb enrich [--idea N] [--limit N]` | Looks pending ideas up on the web now; `--idea` redoes one. It needs lookups turned on and a model key |
| `familydb suggest [--window W] [--as NAME] [--discover]` | Runs the suggestion engine for a window (now, today, this-weekend, next-weekend, someday, or START..END as dates). It is free unless you add `--discover`, which searches the web |

## Run the service

| Command | What it does |
|---|---|
| `familydb run` | The long-running service: it applies migrations, then starts the jobs, the web page and Telegram. The systemd unit runs exactly this. Never start a second one beside it: that repeats the jobs and the Telegram polling |
| `familydb web [--host H] [--port N]` | Serves only the web page, with no jobs and no Telegram, for trying it. If the service is running, pass a different `--port` |
