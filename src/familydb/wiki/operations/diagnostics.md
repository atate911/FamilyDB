# Diagnostics

The doctor checks an install from its files to its keys and prints a fix under anything wrong. Status shows how the assistant has been doing, and the log says what happened on the server.

## Which tool to use

| You want to know | Use |
|---|---|
| Is it running, and when was the last backup | `maintain.sh status` |
| Is it set up right, and what fixes it | `maintain.sh check`, or `familydb doctor` |
| Do the Telegram token and the key work (OpenAI: send a message) | `familydb doctor --online` |
| Which value is in force, and where it came from | `familydb config` |
| What it has cost, who answers, which messages failed | [Status](/wiki/controls/status) |
| Why one message went wrong | [Recent activity](/wiki/controls/status/activity) |
| What the server did, or why it would not start | The log, below |
| Whether it is down right now | [Know when it is down](#know-when-it-is-down) |

## Running the doctor

`maintain.sh check` runs the doctor with no options and does not pass its exit status on, so use it to read, not to script. To pass options, run the doctor yourself from the install folder.

On the server:

```bash
cd /opt/familydb && sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb doctor --online
```

On Docker, use `exec` to check the running container:

```bash
sudo docker compose --project-directory /opt/familydb exec -T bot familydb doctor --online
```

`maintain.sh check` uses `run --rm -T`, a one-off container in which nothing is listening. Run the doctor from the install folder: from anywhere else it finds no `.env`, creates an empty `data/` folder and database, and reports the schema at migration 0. Delete only a `data/` that run created, and never run `--fix` there.

Each line starts with `✓` fine, `!` worth a look, `✗` must be fixed or `·` skipped. Fix the first `✗` first: later checks depend on it.

| Option | What it does |
|---|---|
| `--online` | Also asks Telegram whether the token is live, counts tokens with the company that answers chat (free; OpenAI cannot), and tries each outside page the setup links to |
| `--fix` | Sets `.env` and the login key to mode 600 and applies pending database upgrades, then checks again. It touches no key, password or setting, and does not print what it fixed: the line just turns `✓` (see [The doctor does not print what it fixed](/wiki/reference/known-limits#the-doctor-does-not-print-what-it-fixed)) |
| `--json` | The findings as JSON, each with `check`, `verdict` (`ok`, `warn`, `fail` or `skip`), `detail` and `fix` |

The exit status is 1 when any check is `✗`, otherwise 0, warnings included. A bad value in `.env` stops everything before the first check: see [the .env file](/wiki/operations/configuration#when-a-value-is-wrong).

## What the doctor checks

A `!` on the optional parts is normal on a new install; [Setup](/wiki/controls/setup) walks through them.

| Check | Shows when | What to do |
|---|---|---|
| `env file` `!` | No `.env` in the folder you ran from, or group or others can read it | Run from the install folder. For the mode, make `.env` owner-only (`--fix` does) |
| `disk space` `!` | Under 500 MB free where the database lives | Free some space: see [The server](/wiki/operations/host#disk-and-memory) |
| `database` `✗` | The data folder or file cannot be created or opened | Check the owner of `data/` and `FAMILYDB_PATH` |
| `schema` `✗` or `!` | The database is older (`✗`) or newer (`!`) than the code | Older: apply the pending upgrades (`--fix` does). Newer, which copying a file in by hand can cause (`restore` refuses a newer backup): [upgrade the code](/wiki/operations/upgrade-and-rollback) first |
| `database writable` `✗` | A test write failed | Another user owns the data, for example after a command run as root. Give it back with the first command below the table |
| `family` `✗` or `!` | Nobody on the family list, or no admin | Nobody: add yourself on [Family](/wiki/controls/family); setup opens on it. No admin: make a member one there |
| `family on a channel` `!` | A Telegram token is set but nobody has a Telegram id | Each person messages the Telegram bot; its reply gives the id to type on Family |
| `model key`, `models` `✗` or `!` | No key for any model company, or the chosen one has none and another answers; or the models could not be built (`models`) | Add a key on [AI model](/wiki/controls/settings/ai-model) |
| `model reachable` `·` or `✗` | `·` when not asked, and for OpenAI. With `--online`, `✗` means the company refused the key or the account cannot pay | Check the key and the account |
| `telegram`, `telegram live` `!` or `✗` | No token, or one not shaped like BotFather's. With `--online`: Telegram rejected it (`✗`), or could not be reached (`!`, no fix) | [Connections](/wiki/controls/settings/connections). For a rejected token, send `/revoke` to BotFather and paste the new one |
| `google calendar`, `weather`, `web lookups`, `weekend digest` `!` | Calendar not connected (or an id with no key file), no home coordinates, lookups off, no weekend ideas chat | [Connections](/wiki/controls/settings/connections), [General](/wiki/controls/settings/general), [Lookups](/wiki/controls/settings/lookups), [Messages](/wiki/controls/settings/messages) |
| `web page` `!` or `✗` | `WEB_ENABLED` is off (`!`), or the password rule fails (`✗`) | See [the .env file](/wiki/operations/configuration#when-a-password-is-required) |
| `web page behind a proxy` `!` | The page faces the network with `WEB_TRUST_PROXY` off | [HTTPS and the firewall](/wiki/operations/https-and-firewall) |
| `login key` `!` | `data/web_secret` is readable by others, or does not exist yet | Make it owner-only (`--fix` does). "None yet" is normal before the page first starts |
| `web page answering` `!` | Nothing is listening on `WEB_PORT` | FamilyDB is not running. Start it, then read the log |
| `links` `!` | `--online` only: an outside page the setup links to did not answer or has moved | Check the server's outbound network. The fix it prints names a source file; ignore it, because nothing is wrong with your install |
| `service` `·` or `!` | No systemd unit (Docker, or by hand), or it is installed but not running | Enable and start the service with the second command below the table, then read the log |

```bash
sudo chown -R familydb:familydb /opt/familydb/data
sudo systemctl enable --now familydb
```

On Docker, give `data/` to `1000:1000` instead. There, `env file` warns (the container has no `.env` file; the settings arrive as environment variables), `web page` says "the network", `web page behind a proxy` can warn (the page binds every interface inside the container, though Compose keeps the port on this machine), and the `database writable` fix names the wrong owner.

## Reading `familydb config`

```text
daily_spend_limit=3.0  # from the environment
openai_api_key=****  # from the environment
family_tz=America/Vancouver  # set on the settings page
```

A key is shown as `****`. `# set on the settings page` is a value saved there, which wins. `# from the environment` is a value from `.env` or the environment that differs from the default, and a `.env` value equal to the default has no mark. No mark is the default. The last line, `tz=`, is the time zone in force. `config` checks values only; the password rule is the doctor's.

## Know when it is down

Nothing outside FamilyDB watches it, and its alerts go out through the assistant itself. A stopped program, a failed nightly backup or a full disk therefore alerts no one. Three checks cover it:

- Point an outside monitor at `https://<address>/healthz`. It prints `ok` with no sign-in while the page runs, and Caddy passes it through like any page. It says nothing about Telegram or a model company.
- Run `maintain.sh status` once a week and read the newest backup's date.
- Look at free disk with `df -h`. The doctor warns under 500 MB, but only when you run it.

An admin without a Telegram id gets nothing on Telegram, so for them Status is the only place a trouble shows.

## Logs

Nothing in FamilyDB writes a log file. systemd sends the output to the journal, and Docker keeps five files of 10 MB for each container. The install scripts keep transcripts in `/var/log/familydb-*.log`.

```bash
sudo journalctl -u familydb -n 100 --no-pager
sudo docker compose --project-directory /opt/familydb logs --tail 100 bot
```

The first is systemd, the second Docker. `sudo /opt/familydb/scripts/maintain.sh logs 200` shows the last 200 lines and then follows the log until you press Ctrl-C. A line reads `2026-10-07 10:04:24,207 WARNING familydb.app: message`: time, severity, part of the program, message. The log detail on [General](/wiki/controls/settings/general) sets the lowest severity.

FamilyDB replaces a Telegram token in a log message with `bot<token>`. It does not do so inside a traceback, so read a log before you paste it anywhere.

| You see | It means |
|---|---|
| `familydb <version> starting: db=..., answering on <model> via <company>` | A normal start |
| `agent error on message 42: ... (retryable=True)` | A model call failed. The retry job tries again every 5 minutes by default, up to 3 retries by default; with `False` it is not retried |
| `<company> has no credentials; asking <other> instead` | The second company answered. Check the key on the AI model page |
| `noted for an admin: ...` | A trouble only an admin can fix is now on Status and, with **Tell admins on Telegram** on, sent to admins with a Telegram id |
| `could not store a web session key ...` | `data/` is not writable, so logins will not survive a restart. Fix the owner, or set `WEB_SECRET_KEY` |
| `unexpected error on message 42`, `tool <name> failed`, with a traceback | A bug, not a setting. See Recent activity |

The lines about the web page and stored settings are in [the .env file](/wiki/operations/configuration#when-a-value-is-wrong).
