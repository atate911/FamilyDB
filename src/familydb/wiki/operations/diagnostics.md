# Diagnostics

`familydb doctor` checks an install, from its files to its keys, and prints a fix under anything wrong; the Status page shows how the bot has been doing; the log says what happened on the server. This page says what each doctor check means and which tool to reach for.

## Which tool to use

| You want to know | Use |
|---|---|
| Is it running, and when was the last backup | `maintain.sh status` |
| Is it set up right, and what fixes it | `maintain.sh check`, or `familydb doctor` |
| Do the Telegram token and the key work (OpenAI: send a message) | `familydb doctor --online` |
| Which value is in force, and where it came from | `familydb config` |
| What it has cost, who answers, which messages failed | The [Status page](/wiki/controls/status) |
| Why one message went wrong | [Recent activity](/wiki/controls/status/activity) |
| What the server did, or why it would not start | The log, below |

## Running the doctor

`sudo /opt/familydb/scripts/maintain.sh check` runs `familydb doctor` with no options and does not pass its exit status on, so use it to read, not to script. To pass options or get a status, run `familydb doctor` as [The command line](/wiki/controls/command-line#how-to-run-it) shows, from the install folder. On Docker, use `exec` to check the running container; `run --rm -T`, which `maintain.sh check` uses, starts a one-off container in which nothing is listening.

Run it from the install folder: from anywhere else it finds no `.env`, creates an empty `data/` folder and reports schema 0. Delete only a `data/` that run created (just `familydb.sqlite3` and its journal files), and never run `--fix` there.

Each line starts with `✓` fine, `!` worth a look, `✗` must be fixed or `·` skipped. Checks run in the order of an install, so the first `✗` is usually the cause of the rest.

| Option | What it does |
|---|---|
| `--online` | Also asks Telegram whether the token is live, counts tokens with the company that answers chat (free; OpenAI cannot, and says so), and tries each outside page the setup links to. Needs the server's outbound network. |
| `--fix` | Sets `.env` and the login key to mode 600 and applies pending database upgrades, then checks again. It touches no key, password or setting, and does not say what it fixed: the line just turns `✓`. |
| `--json` | The findings as JSON, each with `check`, `verdict` (`ok`, `warn`, `fail` or `skip`), `detail` and `fix`. |

The exit status is 1 when any check is `✗`, otherwise 0, warnings included. A bad value in `.env` stops everything before the first check: see [the .env file](/wiki/operations/configuration#when-a-value-is-wrong).

## What the doctor checks

A `!` on the optional parts (Telegram, calendar, weather, lookups, digest) is normal on a new install; the page's [setup](/wiki/controls/setup) walks through them.

| Check | Shows when | What to do |
|---|---|---|
| `env file` `!` | No `.env` in the folder you ran from, or group or others can read it. | Run from the install folder. For the mode, `chmod 600 .env` or `--fix`. |
| `disk space` `!` | Under 500 MB free where the database lives. | Free some space ([Troubleshooting](/wiki/operations/troubleshooting)). |
| `database` `✗` | The data folder or file cannot be created or opened. | Check the owner of `data/` and `FAMILYDB_PATH`. |
| `schema` `✗` or `!` | The database is older (`✗`) or newer (`!`) than the code. | Older: `familydb db migrate` or `--fix`. Newer, which a restore can cause: [upgrade the code](/wiki/operations/upgrade-and-rollback) first. |
| `database writable` `✗` | A test write failed. | Another user owns the data, usually after a command run as root: `sudo chown -R familydb:familydb /opt/familydb/data` (on Docker, `1000:1000`). |
| `family` `✗` or `!` | Nobody on the family list, or no admin. | Nobody: add yourself on the [Family page](/wiki/controls/family); setup opens on it. No admin: make a member one there, or `familydb members add NAME --role admin`. |
| `family on a channel` `!` | A Telegram token is set but nobody has a Telegram id. | Each person messages the bot; its reply gives the id to type on the Family page. |
| `model key`, `models` `✗` or `!` | No key for any model company, or the chosen one has none and another answers; or the models for chat, the digest and lookups could not be built (`models`). | Add one on the [AI model](/wiki/controls/settings/ai-model) page. |
| `model reachable` `·` or `✗` | `·` when not asked, and for OpenAI, which has nothing free to ask. With `--online`, `✗` means the company refused the key or the account cannot pay. | Check the key and the account. |
| `telegram`, `telegram live` `!` or `✗` | No token, or one not shaped like BotFather's. With `--online`: Telegram rejected it (`✗`), or could not be reached (`!`, no fix). | The [Connections](/wiki/controls/settings/connections) page. For a rejected token, `/revoke` in BotFather and paste the new one. |
| `google calendar`, `weather`, `web lookups`, `weekend digest` `!` | Calendar not connected (or an id with no key file), no home coordinates, lookups off, no digest chat. | Connections, [General](/wiki/controls/settings/general), [Lookups](/wiki/controls/settings/lookups), [Messages](/wiki/controls/settings/messages). |
| `web page` `!` or `✗` | `WEB_ENABLED` is off (`!`), or the password rule fails (`✗`). | See [the .env file](/wiki/operations/configuration#when-a-password-is-required). |
| `web page behind a proxy` `!` | The page is open to the network with `WEB_TRUST_PROXY` off. | `maintain.sh https`. On Docker, set `WEB_DOMAIN`, `WEB_TRUST_PROXY=true` and `COMPOSE_PROFILES=tls` in `.env`, then `docker compose up -d`. |
| `login key` `!` | `data/web_secret` is readable by others, or does not exist yet. | `chmod 600` on it, or `--fix`. "None yet" is normal before the page first starts. |
| `web page answering` `!` | Nothing is listening on `WEB_PORT`. | The bot is not running. Start it, then read the log. |
| `links` `!` | `--online` only. An outside page the setup links to did not answer or has moved. | Usually the server's outbound network; not urgent. |
| `service` `·` or `!` | No systemd unit (Docker, or by hand), or it is installed but not running. | `sudo systemctl enable --now familydb`, then the log. |

On Docker, `env file` warns (the container has no `.env`), `web page` says "the network" and `web page behind a proxy` can warn (the page binds every interface inside the container, though Compose keeps the port on this machine), and the `database writable` fix names the wrong owner.

## Reading `familydb config`

```text
daily_spend_limit=3.0  # from the environment
openai_api_key=****  # from the environment
family_tz=America/Vancouver  # set on the settings page
```

Names are in lower case and a key is shown as `****`. `# set on the settings page` is a value saved there, which wins. `# from the environment` is a value from `.env` or a real environment variable that differs from the default; it cannot say which, and a `.env` value equal to the default has no mark. No mark is the default. The last line, `tz=`, is the time zone in force. `config` checks values only; the password rule is the doctor's.

## Status commands

- `maintain.sh status` changes nothing: version, whether the service runs, database size, free disk and newest backup. It does not judge health; `check` does.
- `familydb db status` shows the schema version, row counts and the five latest model calls, and first upgrades the database.
- `curl -s http://127.0.0.1:8080/healthz` prints `ok` with no sign-in, for a monitor. Use your `WEB_PORT`.

The doctor looks at the server; the [Status page](/wiki/controls/status) looks at how the bot has been doing, with no model or network call.

## Logs

Nothing in FamilyDB writes a log file. systemd sends the output to the journal, and Docker keeps five files of 10 MB per container. The install scripts keep transcripts in `/var/log/familydb-*.log`.

```bash
sudo journalctl -u familydb -n 100 --no-pager
sudo docker compose --project-directory /opt/familydb logs --tail 100 bot
```

The first is systemd, the second Docker. `sudo /opt/familydb/scripts/maintain.sh logs 200` shows the last 200 lines and then follows the log until you press Ctrl-C. A line reads `2026-10-07 10:04:24,207 WARNING familydb.app: message`: time, severity, part of the program, message. The log detail on [General](/wiki/controls/settings/general) sets the lowest severity written. A Telegram token in a line is replaced by `bot<token>`.

| You see | It means |
|---|---|
| `familydb <version> starting: db=..., answering on <model> via <company>` | A normal start, naming the model and time zone in force. |
| `agent error on message 42: ... (retryable=True)` | A model call failed. It is retried every `RETRY_INTERVAL_MINUTES`, up to `RETRY_MAX_ATTEMPTS` times; with `False` it is not retried. |
| `<company> has no credentials; asking <other> instead` | The backup company answered. Check the key on the AI model page. |
| `noted for an admin: ...` | A trouble only an admin can fix is now on Status and, with admin alerts on, sent to admins with a Telegram id. |
| `could not store a web session key ...` | `data/` is not writable, so logins will not survive a restart. Fix the owner, or set `WEB_SECRET_KEY`. |
| `unexpected error on message 42`, `tool <name> failed`, with a traceback | A bug, not a setting. See Recent activity. |

The lines about the web page and stored settings are in [the .env file](/wiki/operations/configuration#when-a-value-is-wrong).

Developer docs: `src/familydb/doctor.py` (each `check_*`, `correct`, `verdict`), `src/familydb/cli.py` (`doctor`, `config`, `db_status`), `scripts/maintain.sh` (`cmd_status`, `cmd_check`, `cmd_logs`), `src/familydb/app.py` (`configure_logging`), and `RUNBOOK.md`, "Troubleshooting".
