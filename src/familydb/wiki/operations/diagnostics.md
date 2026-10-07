# Diagnostics

`familydb doctor` checks an install, from its files to its keys, and prints a fix under anything wrong; the Status page shows how the bot has been doing; the log says what happened on the server. This page says what each doctor check means and which tool to reach for.

## Which tool to use

| You want to know | Use |
|---|---|
| Is it running, how big is the database, when was the last backup | `maintain.sh status` |
| Is it set up right, and what fixes it | `maintain.sh check`, or `familydb doctor` |
| Do the key and the Telegram token work | `familydb doctor --online` |
| Which value is in force, and where it came from | `familydb config` |
| Row counts, and the last model calls | `familydb db status` |
| What it has cost, who answers, which messages failed | The [Status page](/wiki/controls/status) |
| Why one message went wrong | [Recent activity](/wiki/controls/status/activity) |
| What the server did, or why it would not start | The log, below |

## Running the doctor

```bash
sudo /opt/familydb/scripts/maintain.sh check
```

This runs `familydb doctor` with no options and does not pass its exit status on, so use it to read, not to script. To pass options or get a status, run the doctor as the `familydb` account from the install folder:

```bash
cd /opt/familydb && sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb doctor
```

On Docker, `exec` asks the running container:

```bash
sudo docker compose --project-directory /opt/familydb exec bot familydb doctor
```

The folder matters: the doctor reads `.env` and the database path from where you run it. From anywhere else it finds no `.env`, creates an empty `data/` folder and reports schema 0; delete that folder rather than fixing it.

Each line starts with a mark: `✓` fine, `!` worth a look, `✗` must be fixed, `·` skipped. Checks run in the order of an install, so the first `✗` is usually the cause of the rest. The last line sums up.

| Option | What it does |
|---|---|
| `--online` | Also counts tokens with the company that answers chat (free; OpenAI cannot, and says so), asks Telegram whether the token is live, and tries each outside page the setup links to. Needs the server's outbound network. |
| `--fix` | Sets `.env` and the login key to mode 600 and applies pending database upgrades, then checks again. It touches no key, password or setting, and does not say what it fixed: the line just turns `✓`. |
| `--json` | The findings as JSON: `healthy`, `failures`, `warnings`, and `checks`, each with `check`, `verdict` (`ok`, `warn`, `fail` or `skip`), `detail` and, if there is one, `fix`. |

The exit status is 1 when any check is `✗`, otherwise 0, warnings included. A bad value in `.env` stops everything before the first check: see [the .env file](/wiki/operations/configuration#when-a-value-is-wrong).

## What the doctor checks

A `!` on the optional parts (Telegram, calendar, weather, lookups, digest) is normal on a new install; the page's [setup](/wiki/controls/setup) walks through them.

| Check | Shows when | What to do |
|---|---|---|
| `env file` `!` | No `.env` in the folder you ran from, or group or others can read it. | Run from the install folder. For the mode, `chmod 600 .env` or `--fix`. |
| `disk space` `!` | Under 500 MB free where the database lives. | Free some space ([Troubleshooting](/wiki/operations/troubleshooting)). |
| `database` `✗` | No database at the path, or it cannot be opened. | In the install folder, `familydb db migrate` creates one. If it exists, check its owner and `FAMILYDB_PATH`. |
| `schema` `✗` or `!` | The database is older (`✗`) or newer (`!`) than the code. | Older: `familydb db migrate` or `--fix`. Newer, which a restore can cause: [upgrade the code](/wiki/operations/upgrade-and-rollback) first. |
| `database writable` `✗` | A test write failed. | Another user owns the data, usually after a command run as root: `sudo chown -R familydb:familydb /opt/familydb/data` (on Docker, `1000:1000`). |
| `family` `✗` or `!` | Nobody on the family list, or no admin. | Add yourself on the [Family page](/wiki/controls/family); setup opens on it. |
| `family on a channel` `!` | A Telegram token is set but nobody has a Telegram id. | Each person messages the bot; its reply gives the id to type on the Family page. |
| `model key` `✗` or `!` | No key for any model company, or the chosen one has none and another answers. Keys saved on the page count. | Add one on the [AI model](/wiki/controls/settings/ai-model) page. |
| `models` `✗` | The models for chat, the digest and lookups could not be built. | Read the detail; `familydb config`. |
| `model reachable` `✗` or `·` | `--online` only. The company refused the key or the account cannot pay (`✗`); or OpenAI, which has nothing free to ask (`·`). | Check the key and the account. For OpenAI, send a real message. |
| `telegram`, `telegram live` `!` or `✗` | No token, or one not shaped like BotFather's; with `--online`, Telegram rejected it (`✗`) or could not be reached. | The [Connections](/wiki/controls/settings/connections) page. For a rejected token, `/revoke` in BotFather and paste the new one. |
| `google calendar`, `weather`, `web lookups`, `weekend digest` `!` | Calendar not connected (or an id with no key file), no home coordinates, lookups off, no digest chat. | Connections, [General](/wiki/controls/settings/general), [Lookups](/wiki/controls/settings/lookups), [Messages](/wiki/controls/settings/messages). |
| `web page` `!` or `✗` | `WEB_ENABLED` is off (`!`), or the password rule fails (`✗`). | See [the .env file](/wiki/operations/configuration#when-a-password-is-required). |
| `web page behind a proxy` `!` | The page is open to the network with `WEB_TRUST_PROXY` off. | `maintain.sh https` puts Caddy in front and sets it. |
| `login key` `!` | `data/web_secret` is readable by others, or does not exist yet. | `chmod 600` on it, or `--fix`. "None yet" is normal before the page first starts. |
| `web page answering` `!` | Nothing is listening on `WEB_PORT`. | The bot is not running. Start it, then read the log. |
| `links` `!` | `--online` only. An outside page the setup links to did not answer or has moved. | Usually the server's outbound network; not urgent. |
| `service` `·` or `!` | No systemd unit (Docker, or by hand), or it is installed but not running. | `sudo systemctl enable --now familydb`, then the log. |

On Docker, some lines mislead. The container has no `.env`, so `env file` warns. The page is bound to every interface inside it, so `web page` says "the network" and `web page behind a proxy` can warn although Compose keeps the port on this machine. The `database writable` fix names the wrong owner. `maintain.sh check` runs a separate container where nothing is listening, so `web page answering` warns even when the page works; `exec` avoids that.

## Reading `familydb config`

```text
daily_spend_limit=3.0  # from the environment
openai_api_key=****  # from the environment
family_tz=America/Vancouver  # set on the settings page
```

Names are in lower case and a key is shown as `****`. `# set on the settings page` is a value saved there, which wins. `# from the environment` is a value from `.env` or a real environment variable that differs from the default; it cannot say which, and a `.env` value equal to the default has no mark. No mark is the default. The last line, `tz=`, is the time zone in force. When a `.env` change does nothing, look for the page mark.

## Status commands

- `maintain.sh status` changes nothing. It shows the version, whether the service runs and starts at boot (on Docker, the containers), the database size, free disk, the newest backup and whether a nightly one is scheduled. It does not judge health; `check` does.
- `familydb db status` shows the schema version, row counts, and the five latest model calls with their tokens and `cache_read`. Like most commands it first creates or upgrades the database.
- `curl -s http://127.0.0.1:8080/healthz` prints `ok` with no sign-in, for a monitor. Use your `WEB_PORT`.

The doctor looks at the server; the [Status page](/wiki/controls/status) looks at how the bot has been doing, and makes no model or network call.

## Logs

Nothing in FamilyDB writes a log file. systemd sends the output to the journal, and Docker keeps five files of 10 MB per container. The install scripts keep transcripts in `/var/log/familydb-bootstrap.log`, `-install.log`, `-maintain.log` and `-uninstall.log`.

```bash
sudo journalctl -u familydb -n 100 --no-pager
sudo /opt/familydb/scripts/maintain.sh logs 200
```

The second follows the log from its last 200 lines. On Docker:

```bash
sudo docker compose --project-directory /opt/familydb logs --tail 100 bot
```

A line reads `2026-10-07 10:04:24,207 WARNING familydb.app: message`: time, level, part of the program, message. The level is the log detail on [General](/wiki/controls/settings/general). A Telegram token in a line is replaced by `bot<token>`.

| You see | It means |
|---|---|
| `familydb <version> starting: db=..., answering on <model> via <company>` | A normal start, naming the model and time zone in force. |
| `the web page is not serving: ...`, `could not serve the web page on ...` | The page refused to start, or its port is taken. The bot keeps running. |
| `stored settings are not usable, keeping the ones in the environment` | A value saved on the page no longer fits. Fix or empty it there. |
| `agent error on message 42: ... (retryable=True)` | A model call failed. The retry job tries again; with `False` it gives up. |
| `<company> has no credentials; asking <other> instead` | The backup company answered. Check the key on the AI model page. |
| `noted for an admin: ...` | A trouble only an admin can fix is now on Status and sent on Telegram. |
| `could not store a web session key ...` | `data/` is not writable, so logins will not survive a restart. Fix the owner, or set `WEB_SECRET_KEY`. |
| `unexpected error on message 42`, `tool <name> failed`, with a traceback | A bug, not a setting. Open the message in Recent activity. |

Developer docs: `src/familydb/doctor.py` (each `check_*`, `correct`, `verdict`), `src/familydb/cli.py` (`doctor`, `config`, `db_status`), `scripts/maintain.sh` (`cmd_status`, `cmd_check`, `cmd_logs`), `src/familydb/app.py` (`configure_logging`), and `RUNBOOK.md`, "Troubleshooting".
