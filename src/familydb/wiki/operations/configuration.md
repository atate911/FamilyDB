# The .env file

The `.env` file in the install folder holds what only the server can decide: how the page is reached, where the data lives, and the first password. Everything else is a setting on the [Settings page](/wiki/controls/settings), and `.env` is only where it starts from.

## How the file is read

The file is `/opt/familydb/.env`. The program reads the `.env` in its working directory when it starts and never again, so a change takes effect at the next restart. The systemd unit sets that directory and names the file as its `EnvironmentFile` without the optional marker, so a missing file stops the service from starting. On Docker, Compose reads the file on the host and passes the values in; the container has no `.env` of its own.

- Write one `KEY=value` per line, with the key in capitals, which is all the scripts look for. A line starting with `#` is a comment.
- Put single quotes around a value with a space or a `#`, as in `WEB_PASSWORD='two words # three'`. Unquoted, everything from the `#` is dropped.
- An empty value, such as `HOME_AREA=`, means not set, so the default applies.
- A key the program does not know is ignored without a word, so a misspelt name does nothing.
- A key given twice takes the last line, and a real environment variable of the same name beats the file.

## How it relates to the Settings page

A setting's value comes from the built-in default, then `.env`, then what was saved on the page, and the last one wins. Emptying a box on the page removes what it saved, so the value falls back to `.env`, then to the default. `familydb config` shows each value and where it came from ([Diagnostics](/wiki/operations/diagnostics#reading-familydb-config)). A line in `.env` that seems to do nothing is almost always a setting saved on the page. [How a setting gets its value](/wiki/controls/settings#how-a-setting-gets-its-value) has the rest.

This page lists only the keys that are not Settings-page settings. The model companies and their keys, Telegram, hours, limits, the time zone and the log level are on the Settings pages. A key typed on the page lives in the database and so in every [backup](/wiki/operations/backup-and-restore); a key in `.env` does not.

## Keys only `.env` sets

### The page

| Key | Default | What it does |
|---|---|---|
| `WEB_ENABLED` | `false` | Whether `familydb run` serves the page. The installer sets `true`. |
| `WEB_HOST` | `127.0.0.1` | The address the page listens on. A loopback address keeps it to this machine; any other, `0.0.0.0` included, opens it to the network and needs a password. |
| `WEB_PORT` | `8080` | The port the page listens on. The program accepts 1 to 65535, but the service is unprivileged, so use 1025 or above. `maintain.sh port` moves it together with Caddy or Docker. |
| `WEB_PASSWORD` | empty | The shared password, the first way in. Changing it signs out everyone who signed in with it. |
| `WEB_SECRET_KEY` | empty | Signs the login cookie. Empty, one is generated into `data/web_secret`. Set it when more than one process serves the page, so a login works against either. While set, "Sign everyone out" cannot replace it: change the value and restart. |
| `WEB_ALLOW_NO_PASSWORD` | `false` | Lets a page open to the network run with no password. Ignored behind a proxy. |
| `WEB_TRUST_PROXY` | `false` | Believes the forwarding headers of one proxy hop (the visitor's address and HTTPS) and marks the login cookie Secure. Set it only with Caddy or nginx in front, as the installer does. Off, with the page open to the network, every visitor shares one lockout. |

**Anyone who can reach the page can use every part of it, Settings included,** when `WEB_ALLOW_NO_PASSWORD` is `true` and `WEB_HOST` is open to the network. Keep that for a home network you trust.

### When a password is required

The page refuses to start without one when `WEB_HOST` is not a loopback address (unless `WEB_ALLOW_NO_PASSWORD` is `true`), and always when `WEB_TRUST_PROXY` is `true`. It must have at least 12 characters. A [shared password](/wiki/reference/glossary#shared-password) chosen on the Settings page, or an admin's own password, meets the rule, so `WEB_PASSWORD` can then be empty. When the rule fails, `familydb web` stops, while `familydb run` logs `the web page is not serving` and carries on with Telegram and the jobs.

### Data and the rest

| Key | Default | What it does |
|---|---|---|
| `FAMILYDB_PATH` | `data/familydb.sqlite3` | The database, relative to the install folder; the session key is kept beside it. Leave it: the unit, Compose and `maintain.sh` all assume the install's `data/` folder. |
| `GOOGLE_KEY_PATH` | `data/google_key.json` | Where the calendar's key file is kept. The Connections page writes it. |
| `ANTHROPIC_FALLBACKS` | `true` | Claude only: lets Anthropic re-run a declined request on its own fallback model. |
| `CONSOLE_MEMBER` | empty | Whom `familydb chat` and `repl` speak as without `--as`. Empty is the first admin. |
| `GEOCODER_CONTACT` | empty | An email address or web page sent to OpenStreetMap's place lookup in the User-Agent, as its usage policy asks. Empty sends none. |
| `WEB_DOMAIN` | empty | Read by the scripts, not the program: the name (on a virtualenv install, the server's address) Caddy gets a certificate for. |
| `WEB_PUBLIC_PORT` | empty, meaning 443 | Read by the scripts and Compose: the port the page is served on over HTTPS. `maintain.sh https --port` sets it. |
| `COMPOSE_PROFILES` | not set | Read by Compose: `tls` makes `docker compose up -d` start Caddy as well. |

### What differs on Docker

Compose sets `FAMILYDB_PATH`, `GOOGLE_KEY_PATH` and `WEB_HOST` (`0.0.0.0`, inside the container) itself, so those three lines in `.env` have no effect there. `WEB_PORT` moves the page inside the container and out. Compose publishes the page to this machine's loopback only; to open it to the local network, drop `127.0.0.1:` from the `ports` line in `docker-compose.yml` and set a password.

## What the installer writes

The installer copies `.env.example` to `.env` with mode 600, so every line of the example is in your file at its default, and then sets these. Running it again keeps an existing `.env` (the install block always does); at its prompt you can start over, and it saves the old file as `.env.<timestamp>.bak`, which holds the same keys.

| Keys | Written | Why |
|---|---|---|
| `WEB_ENABLED` | `true` | The page is where everything else is set. |
| `WEB_HOST`, `WEB_PORT` | `127.0.0.1` (`0.0.0.0` on Docker) and `8080`, unless given | The page stays on this machine; Caddy or Compose carries it out. |
| `WEB_PASSWORD` | made up, or the one you gave | The first way in; the page then asks for your own. |
| `WEB_DOMAIN`, `WEB_TRUST_PROXY`, and on Docker `COMPOSE_PROFILES=tls` | when HTTPS is put in front | Caddy needs the name, the page must believe Caddy about who is visiting, and Compose must start Caddy. |
| `WEB_PUBLIC_PORT` | only if you asked for a port other than 443 | |
| `FAMILYDB_TZ`, `WEB_TOOLS_ENABLED`, `DIGEST_CHAT_ID` | the detected zone, `true`, `web`, unless given | Starting values for page settings: the right clock, lookups on, the digest going to the page's chat. |
| the model company, keys, `TELEGRAM_BOT_TOKEN`, home | only when set in the installer's environment | For scripted installs; otherwise the page's setup asks. |

`maintain.sh https` and `port` later edit single lines in place, keeping the file's owner and mode.

## Changing it safely

1. Keep a copy, since `.env` is not in the backups: `sudo cp -p /opt/familydb/.env /root/familydb.env.before`.
2. Edit it, for example with `sudo nano /opt/familydb/.env`. Then check `ls -l /opt/familydb/.env`: on a systemd install it should read `-rw-------` and `familydb familydb`. If an editor changed that, run `sudo chown familydb:familydb /opt/familydb/.env && sudo chmod 600 /opt/familydb/.env`.
3. Check that it loads. A wrong value stops here, before the service is touched:

   ```bash
   cd /opt/familydb && sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb config
   ```

   On Docker:

   ```bash
   sudo docker compose --project-directory /opt/familydb run --rm -T bot familydb config
   ```
4. Restart. It briefly interrupts an answer in progress. On Docker it stops the container and runs `docker compose up -d`, as `maintain.sh` does itself after editing `.env`.

   ```bash
   sudo /opt/familydb/scripts/maintain.sh restart
   ```
5. Run `sudo /opt/familydb/scripts/maintain.sh check` and look for the line you changed.

## Who can read it

**Anyone who can read `.env` can sign in with `WEB_PASSWORD`, forge logins with `WEB_SECRET_KEY` and spend on any key kept there.** Keep it owner-only and out of chats and tickets. `familydb doctor` warns when `.env` or the login key is readable by group or others, and `--fix` sets both to mode 600. `data/` is mode 700. Every command and the service run with umask 077, and `familydb run` and `familydb web` tighten the database, its `-wal`, `-shm` and `-journal` files, the Google key and `data/web_secret` if an older version left them readable. On Docker the container never opens `.env`.

## When a value is wrong

Every `familydb` command that reads the settings, `doctor` and `config` included, stops with this and exit status 1:

```text
a setting will not do:
  web_port: Input should be less than or equal to 65535

  Fix it in .env or on the settings page, then run this again.
  `familydb config` prints every setting and where it came from.
```

Each line names a setting and what it wanted. The service exits the same way, and systemd (`Restart=on-failure`) or Docker (`restart: unless-stopped`) starts it again every few seconds, so the journal fills with the same message until the file is right.

| You see | It means |
|---|---|
| `stored settings are not usable, keeping the ones in the environment` | A value saved on the page no longer fits, often after an upgrade. The bot keeps running on `.env`; fix or empty that box on the Settings page. |
| `the web page is not serving: ...` | The password rule above. The bot keeps running without the page. |
| `could not serve the web page on <address>: ...` | The port is taken or the address cannot be bound. `maintain.sh port` moves FamilyDB's port. |
| `familydb could not start: ... Permission denied: '.env'` | You ran it as a user who cannot read the file. Run it as `familydb`, from the install folder. |
| `the database could not be opened` | `FAMILYDB_PATH` names a folder this user cannot write to or reach. |

Developer docs: `src/familydb/config.py` (`Settings`, `load_settings`), `.env.example`, `scripts/install.sh` (`set_env`), `docker-compose.yml`, `deploy/familydb.service`, and `RUNBOOK.md`, "The web page".
