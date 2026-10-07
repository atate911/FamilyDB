# The command line

The command line is for the admin who looks after the server. Everything the family does day to day is
on the page or in Telegram; the command line is for checking the install, doing something at once that a
job would do later, and the few things the page cannot do (such as making a password for someone locked
out). `familydb --help` lists every command, and `familydb <command> --help` its options.

## How to run it

The program is `familydb`, run as the `familydb` account from the install folder, so it reads the same
`.env` and database as the service:

```bash
cd /opt/familydb
sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb doctor
```

On Docker, run it in a container instead:

```bash
sudo docker compose --project-directory /opt/familydb run --rm -T bot familydb doctor
```

The examples below show just `familydb ...`. For the commands that `maintain.sh` wraps (`check`, `backup`,
`restore`, `password`, `status`), prefer `maintain.sh`: it works out the right form for the install and does
the safe thing around the command. See [Running it over time](/wiki/operations).

## Look, change nothing

| Command | What it shows |
|---|---|
| `familydb doctor [--online] [--fix] [--json]` | Checks the install end to end and prints a fix under anything wrong. `--online` also asks the model companies and Telegram whether the keys work, and whether the pages the setup links to answer. `--fix` puts right the few things that safely can be, such as file permissions. `--json` is for scripts |
| `familydb config` | Every setting, secrets masked, and where each value came from (the default, `.env`, or saved on the page) |
| `familydb db status` | The database's schema version, row counts, and the last few model calls with their cache figures |
| `familydb members list [--all]` | The family list. `--all` includes people switched off |
| `familydb ideas list [--all] [--json]` | The ideas, one line each, exactly as the model sees them |
| `familydb debug cost [--days N]` | What each message pays for before anyone types, and what the last N days (30 by default) cost per purpose and model |
| `familydb debug prompt [TEXT] [--as NAME] [--chat ID] [--kind KIND] [--idea N]` | The exact request that would be sent, without sending it. `--kind` is chat, digest, retry or enrich |
| `familydb tool --list` and `familydb tool NAME --schema` | The tools and whether each is available, and a tool's definition |
| `familydb google events` | The upcoming events on the family calendar, as a connection test |
| `familydb debug validate-tools` | Asks the API to validate the tool definitions. Needs a key, and generates nothing |

## Do something now

These act on the real data. None of them asks a model unless it says so.

| Command | What it does |
|---|---|
| `familydb password [NAME]` | Makes a new starting password for the page and prints it once. With no name it is the first admin who can sign in, or, while the family still shares one password, a new shared password that signs everyone out. [Recovery](/wiki/operations/recovery) says which |
| `familydb db backup DEST` | Copies the database with SQLite's online backup. For a backup you will keep, use `maintain.sh backup`, which also makes the file owner-only |
| `familydb db migrate` | Creates or upgrades the database layout. The service and `maintain.sh upgrade` do this for you |
| `familydb db retry-failed` | Tries again now the messages whose answer failed. The running service also does this every few minutes |
| `familydb members add NAME [--role admin\|parent\|kid] [--channel C --channel-user-id ID]` | Adds a person to the family list. A parent unless the role says otherwise; a kid needs no channel. The Family page does the same, and is where to give someone a password or a Telegram link |
| `familydb google connect KEY_FILE CALENDAR_ID` | Connects the calendar from the server, as the Connections page does: it tries the key on the calendar and then keeps both |
| `familydb tool NAME --json '{...}' [--stdin] [--as NAME]` | Runs one tool directly, with no model, as a family member. It really does what the tool does: use it for testing and scripting, not for fixing data by hand |

## Costs money (a model call)

| Command | What it does |
|---|---|
| `familydb chat TEXT [--as NAME] [--fresh]` | Sends one message and prints the reply, in the console's own chat. It saves what it is told like any other message |
| `familydb repl [--as NAME] [--fresh]` | The same, as an interactive session |
| `familydb suggest [--window W] [--as NAME] [--discover] [--json]` | Runs the suggestion engine and prints its verdicts for a window (now, today, this-weekend, next-weekend, someday, or START..END). `--discover` also searches the web, which is the part that costs |
| `familydb digest [--now]` | Shows the weekend digest's schedule, or with `--now` sends it to the family chat now |
| `familydb follow-ups [--now]` | With `--now`, asks about finished plans now, in the chat each was made in. No model call |
| `familydb enrich [--idea N] [--limit N]` | Looks pending ideas up on the web now. `--idea` redoes one, even if done |

Each model call goes through the same daily spending limit as the rest.

## Run the service

| Command | What it does |
|---|---|
| `familydb run` | The long-running service: applies migrations, then starts the scheduler, the web page when it is enabled, and Telegram when a token is set. The `familydb` service in systemd runs exactly this |
| `familydb web [--host H] [--port N]` | Serves only the page in the foreground until interrupted, for trying it. If the service is running, pass a different `--port` |

Developer docs: `README.md`, "Commands", and `RUNBOOK.md`.
