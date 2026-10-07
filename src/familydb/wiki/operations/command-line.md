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
| `status` | Shows whether FamilyDB is running, its version, the database size, free disk and the newest backup. Changes nothing |
| `check` | Runs the doctor and prints every finding with its fix. See [Diagnostics](/wiki/operations/diagnostics) |
| `backup` | Takes a backup now. See [Backup and restore](/wiki/operations/backup-and-restore) |
| `restore FILE` | Stops FamilyDB, puts that backup in place, starts it again |
| `upgrade` | Takes a backup, moves to the newer code, migrates, restarts. See [Upgrade and rollback](/wiki/operations/upgrade-and-rollback) |
| `logs [N]` | Shows the last N lines (50 by default) and then follows the log until you press Ctrl-C |
| `restart` | Restarts FamilyDB and says whether it came back |
| `schedule-backups` | Puts the nightly backup in root's crontab; `--keep-days N` sets how long backups are kept |
| `https [DOMAIN]` | Puts the web page on HTTPS and gets the certificate. `--port N` or `--port random` moves it. See [HTTPS and the firewall](/wiki/operations/https-and-firewall) |
| `port N` | Moves FamilyDB's own port (8080 unless moved). See [HTTPS and the firewall](/wiki/operations/https-and-firewall#move-the-public-port) |
| `password [NAME]` | Makes a new starting password and prints it once. See [Recovery](/wiki/operations/recovery) |

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

The `familydb` program must run as the `familydb` account from the install folder, so it reads the same `.env` and database as the service. On a virtualenv install:

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
| `familydb doctor [--online] [--fix] [--json]` | Checks the install end to end and prints a fix under anything wrong; exits with status 1 when something must be fixed. `--online` is free: it counts tokens on Anthropic or Gemini, asks Telegram whether the token is live and checks that the pages the setup links to answer. `--fix` makes `.env` and the login key owner-only and applies pending migrations |
| `familydb config` | Every setting with secrets masked, and where each value came from: **set on the settings page**, **from the environment**, or no mark for a default |
| `familydb db status` | The schema version, row counts and the last few model calls |
| `familydb members list [--all]` | The family list; `--all` includes people switched off |
| `familydb ideas list [--all] [--json]` | The ideas, one line each. Unlike the assistant's list it includes presents; `--all` adds dropped ideas |
| `familydb debug cost [--days N]` | What each message costs before anyone types, and what the last N days (30 by default) cost per purpose and model |
| `familydb debug prompt [TEXT] [--as NAME] [--kind KIND] [--idea N]` | The exact request that would be sent, without sending it. `--kind` is chat, digest, retry or enrich |
| `familydb tool --list` | The tools, whether each is available and which write |
| `familydb google events [--days N]` | The next 7 days (or N) on the family calendar, as a connection test |
| `familydb debug validate-tools` | Asks the API to validate the tool definitions. It needs an Anthropic or Gemini key and fails on OpenAI |

## Change something now

These act on the real data. None of them asks a model.

| Command | What it does |
|---|---|
| `familydb password [NAME]` | Makes a new starting password and prints it once. With no name it resets the oldest admin who can sign in; if the family still shares one password, it replaces that one for everyone. See [Recovery](/wiki/operations/recovery) |
| `familydb db backup DEST` | Copies the database with SQLite's online backup. For a backup you keep, use `maintain.sh backup`, which also makes the file owner-only; on Docker `DEST` is inside the container |
| `familydb db migrate` | Applies pending [migrations](/wiki/reference/glossary#migration). The service and `maintain.sh upgrade` do it for you |
| `familydb members add NAME [--role admin\|parent\|kid]` | Adds a person, a parent unless `--role` says otherwise. It skips the Family page's checks, so use the [Family page](/wiki/controls/family) for anyone but the first admin |
| `familydb google connect KEY_FILE CALENDAR_ID` | Connects the calendar from the server. It tests the key by reading the calendar and by making and deleting a one-day test event, then saves it. The calendar must be shared with edit rights |
| `familydb follow-ups [--now]` | Shows the schedule; with `--now`, sends the how-did-it-go message for each finished plan. No model call |
| `familydb tool NAME --json '{...}' [--as NAME]` | Runs one tool with no model. Tools marked writing change the real data, and the calendar tools change the real Google calendar. For testing, ideally on a copy of the data |

## Commands that cost money

Each model call goes through the same daily spending limit as the rest.

| Command | What it does |
|---|---|
| `familydb chat TEXT [--as NAME] [--fresh]` | Talks to the assistant in its console chat. Everything it does is real: it saves messages and may add ideas, things to do or calendar events |
| `familydb repl [--as NAME] [--fresh]` | The same, as an interactive session |
| `familydb db retry-failed [--reset]` | Asks again about messages whose answer failed and sends the replies. `--reset` first makes given-up messages eligible again, including ones given up on purpose |
| `familydb digest [--now]` | Shows the weekend ideas schedule; with `--now`, sends them to the chat chosen under Messages, once a day at most |
| `familydb enrich [--idea N] [--limit N]` | Looks pending ideas up on the web now; `--idea` redoes one. It needs lookups turned on and a model key |
| `familydb suggest [--window W] [--as NAME] [--discover]` | Runs the suggestion engine for a window (now, today, this-weekend, next-weekend, someday, or START..END as dates). It is free unless you add `--discover`, which searches the web |

## Run the service

| Command | What it does |
|---|---|
| `familydb run` | The long-running service: it applies migrations, then starts the jobs, the web page and Telegram. The systemd unit runs exactly this. Never start a second one beside it: that repeats the jobs and the Telegram polling |
| `familydb web [--host H] [--port N]` | Serves only the web page, with no jobs and no Telegram, for trying it. If the service is running, pass a different `--port` |
