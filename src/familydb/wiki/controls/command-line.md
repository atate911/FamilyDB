# The command line

The command line is for the admin who looks after the server. Everything the family does day to day is on
the page or in Telegram; the command line is for checking the install, doing something at once that a job
would do later, and the few things the page cannot do, such as making a password for someone locked out.
`familydb --help` lists every command, `familydb <command> --help` its options, and `familydb --version` the
version.

## How to run it

The program is `familydb`, run as the `familydb` account from the install folder, so it reads the same `.env`
and database as the service:

```bash
cd /opt/familydb
sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb doctor
```

On Docker, run it in a container instead:

```bash
sudo docker compose --project-directory /opt/familydb run --rm -T bot familydb doctor
```

The examples below show just `familydb ...`. `maintain.sh` wraps `check` (the doctor), `backup` and `password` and
works out the right form for the install, so prefer it for those; `restore` and `status` have no `familydb` form.
See [Running it over time](/wiki/operations).

## Look at things

These show things and send nothing. On a database that has never been opened, or one from an older version, most of
them first create or upgrade it, which is harmless. `doctor --fix` is the exception: it changes things.

| Command | What it shows |
|---|---|
| `familydb doctor [--online] [--fix] [--json]` | Checks the install end to end and prints a fix under anything wrong; it exits with status 1 when something must be fixed. `--online` costs nothing: it counts tokens on Anthropic or Gemini (OpenAI cannot, and says so), asks Telegram whether the token is live, and checks that the pages the setup links to answer. `--fix` makes `.env` and the login key owner-only and applies pending database upgrades. `--json` is for scripts. Run it from the install folder, since it finds `.env` there |
| `familydb config` | Every setting, secrets masked. A value saved on the page is marked "set on the settings page", one that differs from the default because of `.env` or the environment is marked "from the environment", and a plain default has no mark |
| `familydb db status` | The database's schema version, row counts, and the last few model calls with their cache figures |
| `familydb members list [--all]` | The family list. `--all` includes people switched off |
| `familydb ideas list [--all] [--json]` | The ideas, one line each, exactly as the model sees them |
| `familydb debug cost [--days N]` | What each message pays for before anyone types, and what the last N days (30 by default) cost per purpose and model |
| `familydb debug prompt [TEXT] [--as NAME] [--chat ID] [--kind KIND] [--idea N]` | The exact request that would be sent, without sending it. `--kind` is chat, digest, retry or enrich |
| `familydb tool --list`, `familydb tool NAME --schema` | The tools, whether each is available and which write, and one tool's definition |
| `familydb google events [--days N]` | The upcoming events on the family calendar (7 days by default), as a connection test |
| `familydb debug validate-tools` | Asks the API to validate the tool definitions. Needs an Anthropic or Gemini key: with OpenAI, the default, it fails, since OpenAI cannot check without generating |

## Change something now

These act on the real data. None of them asks a model.

| Command | What it does |
|---|---|
| `familydb password [NAME]` | Makes a new starting password for the page and prints it once. With a name it is that person's; if the family still shares one password, it also ends the shared one for everyone. With more than one admin, give the name: with none it resets the oldest admin. [Recovery](/wiki/operations/recovery) covers each state |
| `familydb db backup DEST` | Copies the database with SQLite's online backup. For a backup you will keep, use `maintain.sh backup`, which also makes the file owner-only. On Docker use `maintain.sh backup` too, since `DEST` would be inside the container |
| `familydb db migrate` | Creates or upgrades the database layout. The service and `maintain.sh upgrade` do this for you |
| `familydb members add NAME [--role admin\|parent\|kid] [--channel C --channel-user-id ID]` | Adds a person, a parent unless `--role` says otherwise. It does not apply the Family page's checks (a number for the Telegram id, a clear message for a duplicate or switched-off name), so for anyone but the first admin use the Family page, which is also where to give someone a password or a Telegram link |
| `familydb google connect KEY_FILE CALENDAR_ID` | Connects the calendar from the server, as the Connections page does. It tries the key by reading the calendar and by making and deleting a one-day test event, so the calendar must be shared with edit rights, and only if that works does it save the key and the calendar id |
| `familydb follow-ups [--now]` | Without `--now`, shows the schedule. With it, sends the how-did-it-go message now for each finished plan, in the chat it was made in. No model call |
| `familydb tool NAME --json '{...}' [--stdin] [--as NAME]` | Runs one tool directly, with no model. Tools that `tool --list` marks as writing really change the family's data, and the calendar tools change the real Google calendar. It acts as the first admin unless you pass `--as`. For testing and scripting, ideally on a copy of the data |

## Calls a model, and so costs money

Each model call goes through the same daily spending limit as the rest.

| Command | What it does |
|---|---|
| `familydb chat TEXT [--as NAME] [--fresh]` | Talks to the bot in its own console chat (`--fresh` starts a new one). Everything it does is real: it saves messages and may add ideas, things to do or calendar events |
| `familydb repl [--as NAME] [--fresh]` | The same, as an interactive session. On Docker use `docker compose exec -it bot familydb repl`, since `run -T` has no terminal |
| `familydb db retry-failed [--reset]` | Asks the model again about messages whose answer failed, and sends the replies. `--reset` first makes messages that ran out of tries eligible again. The running service does this every 5 minutes by default |
| `familydb digest [--now]` | Shows the weekend digest's schedule, or with `--now` sends it to the chat chosen under Messages now. It needs a digest chat set, and sends once a day at most |
| `familydb enrich [--idea N] [--limit N]` | Looks pending ideas up on the web now; `--idea` redoes one, even if done. Needs lookups turned on and a model key |
| `familydb suggest [--window W] [--as NAME] [--discover] [--json]` | Runs the suggestion engine and prints its verdicts for a window (now, today, this-weekend, next-weekend, someday, or START..END as dates). It is free unless you add `--discover`, which searches the web and needs lookups turned on |

## Run the service

| Command | What it does |
|---|---|
| `familydb run` | The long-running service: applies migrations, then starts the scheduler, the web page when it is enabled, and Telegram when a token is set. The `familydb` service in systemd runs exactly this. Never start a second one beside it, which would repeat the jobs and the Telegram polling |
| `familydb web [--host H] [--port N]` | Serves only the page, with no jobs and no Telegram, until interrupted, for trying it. If the service is running, pass a different `--port` |

Developer docs: `README.md`, "Commands", and `RUNBOOK.md`.
