# Diagnostics

`maintain.sh check` looks at an install from the disk it sits on to the keys it uses, and prints a fix under anything wrong; it only reads. It works when the program will not start, which is when it is wanted. `maintain.sh doctor` does the same look and then explains what is wrong and fixes what it can: see [Break glass](/wiki/operations/break-glass#the-doctor). Status shows how the assistant has been doing, and the log says what happened on the server.

## Which tool to use

| You want to know | Use |
|---|---|
| Is it running, and when was the last backup | `maintain.sh status` |
| Is it set up right, and what fixes it | `maintain.sh check` |
| Why the page will not come up, or it is badly broken, and fix it | `maintain.sh doctor` ([Break glass](/wiki/operations/break-glass#the-doctor)) |
| Do the Telegram token and the key work (OpenAI: send a message) | `maintain.sh check --online`, or `familydb doctor --online` |
| Only the program's own settings and data, with its options | `familydb doctor` |
| Which value is in force, and where it came from | `familydb config` |
| What it has cost, who answers, which messages failed | [Status](/wiki/controls/status) |
| Why one message went wrong | [Recent activity](/wiki/controls/status/activity) |
| Recent warnings and errors, and what a model was sent and said | The [Troubleshooting card](/wiki/controls/settings/troubleshooting) on the Settings page |
| What the server did, or why it would not start | The log, below |
| Whether it is down right now | [Know when it is down](#know-when-it-is-down) |

## Running the check

```bash
sudo /opt/familydb/scripts/maintain.sh check
```

It makes two looks and prints one report. The first is of the machine and does not use the program, so it still works when the program cannot start: it reads files and who owns them, asks git, systemd, Docker, Caddy, the firewall and the page itself, and uses Python only to read the packages and the database file. The second is the program's own check, `familydb doctor`, which knows what is set up: the family, the model, Telegram, the jobs and the messages. A name is reported once, and the machine's word wins: if both look at the service, you read the machine's.

| Section | What it looks for |
|---|---|
| Files | The service account exists; the code is not writable by others; no page, style or migration is missing; `.env` is there, private and readable by the service; the data folder is writable by the service account and owns nothing it cannot write; the backup folder is writable |
| Git | The checkout opens (no "dubious ownership"), no tracked file is missing or changed, the history is whole, the remote and the deploy key are usable and carry no password, and an upgrade did not stop part-way |
| Config | `.env` parses (a line that is not `NAME=value`, an unclosed quote, a byte-order mark, Windows line ends, an option set twice), the port is one the service may bind, and a switched-off page is said |
| Python | The interpreter runs and is 3.11 or newer, `uv` is installed, every dependency is installed at the version `uv.lock` names, and `familydb --help` loads |
| Database file | It exists, its owner and mode are right (and its journal files', since root-owned ones are what makes SQLite say "attempt to write a readonly database"), SQLite finds it sound, and its migration matches the code's |
| Service | The unit file points at things that exist and its sandbox lets the database be written; systemd has read it; the service is running and starts at boot; restarts, how it last exited (killed for memory, too many failed starts) and a second copy running under Docker. On Docker: the daemon, the compose file, each container's state, health, restarts and memory |
| Web server | Something of the right kind listens on the port, `/healthz` answers, the front page is drawn (a page that crashes when drawn looks well at `/healthz`), it carries its content-security policy, and its styles are served |
| HTTPS | Only with a domain: it resolves, Caddy runs and accepts its Caddyfile and passes the page to the right port, the certificate is valid for 14 days or more, the address answers from this machine, and the firewall lets 80 and the public port through |
| Host | Free space and free file slots (a bar for the space), memory and swap, the clock, a read-only file system, a writable temp folder, and errors in the service's log in the last day |
| Backups | The newest backup is under 36 hours old (a bar), and a nightly one is scheduled |

Then the program's own sections: Settings, Database, Family, Model, Connections, Web page and Running, described [below](#what-the-programs-own-check-looks-at).

### Reading the report

A section with nothing wrong is folded into one line that names what it looked at, so a healthy install is a short screen. A section with something wrong opens with a count (`2/4`) and lists what is not fine, each with the command that fixes it, then says how many of its rows were fine. `--all` lists every row. `--online` adds the checks that need the internet: the git remote, the model company's key, Telegram, and the pages the setup links to.

The marks are `✓` fine, `!` worth a look, `✗` must be fixed and `○` not checked. A bar under the report is cut in those colours. **Start here** names the first `✗` in the order a page comes up, from the files through the service to the settings, so fix that one first: the ones after it often follow from it. When something must be fixed, the report ends with **Break glass**, the ways out of [Break glass](/wiki/operations/break-glass) that suit what it found.

The exit status is 1 when any check is `✗`, otherwise 0, warnings included, so a script can read it. A check that cannot run is a row and never the end of the report.

### The program's check alone

`maintain.sh check` runs `familydb doctor` for you, with `--online` when you pass it. To pass the other options, or to run only that part, run it yourself from the install folder.

On the server:

```bash
cd /opt/familydb && sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb doctor --online
```

On Docker, use `exec` to check the running container:

```bash
sudo docker compose --project-directory /opt/familydb exec -T bot familydb doctor --online
```

`maintain.sh check` uses `run --rm -T`, a one-off container in which nothing is listening. Run the doctor from the install folder: from anywhere else it finds no `.env`, creates an empty `data/` folder and database, and reports the schema at migration 0. Delete only a `data/` that run created, and never run `--fix` there.

Its output is grouped under `▸ Name` headings, each line starting with `✓` fine, `!` worth a look, `✗` must be fixed or `·` skipped.

| Option | What it does |
|---|---|
| `--online` | Also asks Telegram whether the token is live, counts tokens with the company that answers chat (free; OpenAI cannot), and tries each outside page the setup links to |
| `--fix` | Sets `.env`, the login key and the database files to mode 600 and applies pending database upgrades, then checks again. It touches no key, password or setting, and does not print what it fixed: the line just turns `✓` (see [The doctor does not print what it fixed](/wiki/reference/known-limits#the-doctor-does-not-print-what-it-fixed)) |
| `--json` | The findings as JSON, each with `check`, `group`, `verdict` (`ok`, `warn`, `fail` or `skip`), `detail` and `fix` |

The exit status is 1 when any check is `✗`, otherwise 0, warnings included. A bad value in `.env` stops everything before the first check: `maintain.sh check` then shows it as **its own check** with the first lines of what the program said, and [the .env file](/wiki/operations/configuration#when-a-value-is-wrong) explains the rule.

## What the program's own check looks at

A `!` on the optional parts is normal on a new install; [Setup](/wiki/controls/setup) walks through them.

| Check | Shows when | What to do |
|---|---|---|
| `env file` `!` | No `.env` in the folder you ran from, or group or others can read it | Run from the install folder. For the mode, make `.env` owner-only (`--fix` does) |
| `env options` `!` | A name in `.env` that FamilyDB does not read, so a value set under it never takes effect (it says the name it is close to) | Correct the name; `.env.example` lists them all |
| `time zone` `!` | No time zone was chosen and the server's is UTC, so reminders, the digest and "this weekend" follow the wrong clock | Choose it on [General](/wiki/controls/settings/general) |
| `disk space` `!` | Under 500 MB free where the database lives | Free some space: see [The server](/wiki/operations/host#disk-and-memory), or `maintain.sh rescue space` |
| `database` `✗` | The data folder or file cannot be created or opened | Check the owner of `data/` and `FAMILYDB_PATH` |
| `schema` `✗` or `!` | The database is older (`✗`) or newer (`!`) than the code | Older: apply the pending upgrades (`--fix` does). Newer, which copying a file in by hand can cause (`restore` refuses a newer backup): [upgrade the code](/wiki/operations/upgrade-and-rollback) first |
| `integrity` `✗` | SQLite's own check of the file found damage, or the file could not be read at all | [Break glass](/wiki/operations/break-glass#the-database-is-damaged): it checks the backups and restores the newest sound one |
| `data files` `!` | The database, its journal files or the Google key can be read by other users | Make them owner-only (`--fix` does) |
| `database writable` `✗` | A test write failed | Another user owns the data, for example after a command run as root. Give it back with the first command below the table |
| `family` `✗` or `!` | Nobody on the family list, or no admin | Nobody: add yourself on [Family](/wiki/controls/family); setup opens on it. No admin: make a member one there |
| `family on a channel` `!` | A Telegram token is set but nobody has a Telegram id | Each person messages the Telegram bot; its reply gives the id to type on Family |
| `model key`, `models` `✗` or `!` | No key for any model company, or the chosen one has none and another answers; or the models could not be built (`models`) | Add a key on [AI model](/wiki/controls/settings/ai-model) |
| `spending today` `!` | The day's estimated spending has reached the limit, so the model answers nothing more until midnight | Raise the limit on [Spending](/wiki/controls/settings/spending) if that was not meant |
| `model reachable` `·` or `✗` | `·` when not asked, and for OpenAI. With `--online`, `✗` means the company refused the key or the account cannot pay | Check the key and the account |
| `telegram`, `telegram live` `!` or `✗` | No token, or one not shaped like BotFather's. With `--online`: Telegram rejected it (`✗`), or could not be reached (`!`, no fix) | [Connections](/wiki/controls/settings/connections). For a rejected token, send `/revoke` to BotFather and paste the new one |
| `google calendar`, `weather`, `web lookups`, `weekend digest` `!` | Calendar not connected (or an id with no key file), no home coordinates, lookups off, no weekend ideas chat | [Connections](/wiki/controls/settings/connections), [General](/wiki/controls/settings/general), [Lookups](/wiki/controls/settings/lookups), [Messages](/wiki/controls/settings/messages) |
| `web page` `!` or `✗` | `WEB_ENABLED` is off (`!`), or the password rule fails (`✗`) | See [the .env file](/wiki/operations/configuration#when-a-password-is-required) |
| `web page behind a proxy` `!` | The page faces the network with `WEB_TRUST_PROXY` off | [HTTPS and the firewall](/wiki/operations/https-and-firewall) |
| `login key` `!` | `data/web_secret` is readable by others, or does not exist yet | Make it owner-only (`--fix` does). "None yet" is normal before the page first starts |
| `web page answering` `!` | Nothing is listening on `WEB_PORT` | FamilyDB is not running. Start it, then read the log |
| `links` `!` | `--online` only: an outside page the setup links to did not answer or has moved | Check the server's outbound network. The fix it prints names a source file; ignore it, because nothing is wrong with your install |
| `service` `·` or `!` | No systemd unit (Docker, or by hand), or it is installed but not running | Enable and start the service with the second command below the table, then read the log |
| `scheduled jobs` `·` or `✗` | `·` when the scheduler never ran or was stopped on purpose. `✗` when it is quiet for over 15 minutes, so no reminder, digest or retry is going out | Is it running? Restart it, then read the log |
| `waiting messages`, `unsent replies`, `given-up messages` `!` | A message has waited over 10 minutes for an answer; a reply is stored but was never delivered; or a message was given up on this week (not counting people removed from the family) | Run `familydb db retry-failed`; check the Telegram token; fix the cause the row names, then `familydb db retry-failed --reset` |
| `alerts` `!` | A trouble the admins were told about is still standing | The [Status](/wiki/controls/status) page lists each with what to do |
| `logged errors` `!` | Errors in the program's own problem log in the last day | The [Troubleshooting card](/wiki/controls/settings/troubleshooting) lists each with its detail |

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

The first is systemd, the second Docker. `sudo /opt/familydb/scripts/maintain.sh logs 200` shows the last 200 lines and then follows the log until you press Ctrl-C. A line reads `2026-10-07 10:04:24,207 WARNING familydb.app: message`: time, severity, part of the program, message. **What the server writes** on the [Troubleshooting card](/wiki/controls/settings/troubleshooting#how-much-is-logged) sets the lowest severity.

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
