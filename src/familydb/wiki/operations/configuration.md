# The .env file

The `.env` file in the install folder holds what only the server can decide: how the page is reached, where the data lives, and the first password. Everything else is a setting on the [Settings page](/wiki/controls/settings), and `.env` is only where it starts from.

## How the file is read

The file is `/opt/familydb/.env`. The program reads the `.env` in its working directory when it starts and never again, so a change takes effect at the next restart. The systemd unit names the file as its `EnvironmentFile` without the optional marker, so a missing file stops the service from starting. On Docker, Compose reads the file on the host and passes the values in; the container has no `.env`.

- Write one `KEY=value` per line, with the key in capitals, which is all the scripts look for. A line starting with `#` is a comment.
- Put single quotes around a value with a space or a `#`, as in `WEB_PASSWORD='two words # three'`. Unquoted, everything from the `#` is dropped.
- An empty value, such as `HOME_AREA=`, means not set, so the default applies.
- A key the program does not know is ignored without a word, so a misspelt name does nothing.
- A key given twice takes the last line, and a real environment variable of the same name beats the file.

## How it relates to the Settings page

A setting's value comes from the built-in default, then `.env`, then what was saved on the page, and the last wins. Emptying a box on the page removes what it saved, so the value falls back to `.env`, then to the default. `familydb config` shows each value and where it came from ([Diagnostics](/wiki/operations/diagnostics#reading-familydb-config)). A line in `.env` that seems to do nothing is almost always a setting saved on the page. Every key that is a Settings-page setting is explained from [Settings](/wiki/controls/settings#how-a-setting-gets-its-value), so this page does not list it. A key typed on the page lives in the database and so in every [backup](/wiki/operations/backup-and-restore); a key in `.env` does not.

## Keys only `.env` sets

| Key | Default | What it does |
|---|---|---|
| `WEB_ENABLED` | `false` | Whether `familydb run` serves the page. The installer sets `true`. |
| `WEB_HOST` | `127.0.0.1` | The address the page listens on. A loopback address keeps it to this machine; any other, `0.0.0.0` included, opens it to the network and needs a password. |
| `WEB_PORT` | `8080` | The port it listens on. The service is unprivileged, so use 1025 or above. `maintain.sh port` moves it together with Caddy or Docker. |
| `WEB_PASSWORD` | empty | The shared password, the first way in. Changing it signs out everyone who signed in with it. |
| `WEB_SECRET_KEY` | empty | Signs the login cookie. Empty, one is generated into `data/web_secret`. Set it when more than one process serves the page. While set, "Sign everyone out" cannot replace it: change the value and restart. |
| `WEB_ALLOW_NO_PASSWORD` | `false` | Lets a page open to the network run with no password. Ignored behind a proxy. |
| `WEB_TRUST_PROXY` | `false` | Believes the forwarding headers of one proxy hop (the visitor's address and HTTPS) and marks the login cookie Secure. Set it only with Caddy or nginx in front, as the installer does. Off, with the page open to the network, every visitor shares one lockout. |
| `FAMILYDB_PATH` | `data/familydb.sqlite3` | The database, relative to the install folder; the session key is kept beside it. Leave it: the unit, Compose and `maintain.sh` assume the install's `data/` folder. |
| `GOOGLE_KEY_PATH` | `data/google_key.json` | Where the calendar's key file is kept. The Connections page writes it. |
| `ANTHROPIC_FALLBACKS` | `true` | Claude only: lets Anthropic re-run a declined request on its own fallback model. |
| `CONSOLE_MEMBER` | empty | Whom `familydb chat` and `repl` speak as without `--as`. Empty is the first admin. |
| `GEOCODER_CONTACT` | empty | An email address or web page sent with each OpenStreetMap place lookup, as its usage policy asks. Empty sends none. |
| `WEB_DOMAIN` | empty | For the scripts, not the program: the name (on a virtualenv install, the address) Caddy gets a certificate for. |
| `WEB_PUBLIC_PORT` | empty, meaning 443 | For the scripts and Compose: the port the page is served on over HTTPS. |
| `COMPOSE_PROFILES` | not set | For Compose: `tls` makes `docker compose up -d` start Caddy too. |

**Anyone who can reach the page can use every part of it, Settings included,** when `WEB_ALLOW_NO_PASSWORD` is `true` and `WEB_HOST` is open to the network. Keep that for a home network you trust.

### When a password is required

The page refuses to start without one when `WEB_HOST` is not a loopback address (unless `WEB_ALLOW_NO_PASSWORD` is `true`), and always when `WEB_TRUST_PROXY` is `true`. It needs at least 12 characters. A [shared password](/wiki/reference/glossary#shared-password) chosen on the Settings page, or an admin's own password, meets the rule, so `WEB_PASSWORD` can then be empty. When the rule fails, `familydb web` stops, while `familydb run` logs `the web page is not serving` and carries on with Telegram and the jobs.

### What differs on Docker

Compose sets `FAMILYDB_PATH`, `GOOGLE_KEY_PATH` and `WEB_HOST` (`0.0.0.0`, inside the container) itself, so those lines in `.env` have no effect there. It publishes the page to this machine's loopback only; to open it to the local network, drop `127.0.0.1:` from the `ports` line in `docker-compose.yml` and set a password.

## What the installer writes

The installer copies `.env.example` to `.env` with mode 600, so every line of the example is in your file at its default, and then sets these. Running it again keeps an existing `.env`; at its prompt you can start over, and it saves the old file as `.env.<timestamp>.bak`, which holds the same keys.

| Keys | Why |
|---|---|
| `WEB_ENABLED=true`, `WEB_HOST`, `WEB_PORT` | The page is where everything else is set. It stays on this machine (`127.0.0.1`, or `0.0.0.0` on Docker, with port 8080) and Caddy or Compose carries it out. |
| `WEB_PASSWORD` | Made up, or the one you gave: the first way in, until the page asks for your own. |
| `WEB_DOMAIN`, `WEB_TRUST_PROXY`, and on Docker `COMPOSE_PROFILES=tls` | Written when HTTPS is put in front: Caddy needs the name, the page must believe Caddy about who is visiting, and Compose must start Caddy. |
| `WEB_PUBLIC_PORT` | Only if you asked for a port other than 443. |
| `FAMILYDB_TZ`, `WEB_TOOLS_ENABLED=true`, `DIGEST_CHAT_ID=web` | Starting values for page settings, unless you gave others: the right clock, lookups on, the digest going to the page's chat. |

A scripted install can also write the model company, keys, `TELEGRAM_BOT_TOKEN` and home from its environment. Later, `maintain.sh https` and `port` edit single lines in place, keeping the file's owner and mode.

## Changing it safely

1. Keep a copy, since `.env` is not in the backups: `sudo cp -p /opt/familydb/.env /root/familydb.env.before`.
2. Edit it, for example with `sudo nano /opt/familydb/.env`, then check `ls -l /opt/familydb/.env`. On a systemd install it should read `-rw-------` and `familydb familydb`. If an editor changed that, run `sudo chown familydb:familydb /opt/familydb/.env && sudo chmod 600 /opt/familydb/.env`.
3. Check that it loads, so a wrong value stops here and not the service:

   ```bash
   cd /opt/familydb && sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb config
   ```

   On Docker:

   ```bash
   sudo docker compose --project-directory /opt/familydb run --rm -T bot familydb config
   ```
4. Restart, which briefly interrupts an answer in progress, then run `maintain.sh check`. On Docker the restart stops the container and runs `docker compose up -d`, as `maintain.sh` does itself after editing `.env`.

   ```bash
   sudo /opt/familydb/scripts/maintain.sh restart
   sudo /opt/familydb/scripts/maintain.sh check
   ```

## Who can read it

**Anyone who can read `.env` can sign in with `WEB_PASSWORD`, forge logins with `WEB_SECRET_KEY` and spend on any key kept there.** Keep it owner-only and out of chats and tickets. `familydb doctor` warns when `.env` or the login key is readable by group or others, and `--fix` sets both to mode 600. `data/` is mode 700, every command and the service run with umask 077, and `familydb run` and `familydb web` tighten the database, its journal files, the Google key and `data/web_secret` if an older version left them readable.

## When a value is wrong

Every `familydb` command that reads the settings, `doctor` and `config` included, stops with this and exit status 1:

```text
a setting will not do:
  web_port: Input should be less than or equal to 65535

  Fix it in .env or on the settings page, then run this again.
  `familydb config` prints every setting and where it came from.
```

Each line names a setting and what it wanted. The service exits the same way, and systemd (`Restart=on-failure`) or Docker (`restart: unless-stopped`) starts it again every few seconds, so the journal fills with the same message until the file is right. Other messages:

| You see | It means |
|---|---|
| `stored settings are not usable, keeping the ones in the environment` | A value saved on the page no longer fits, often after an upgrade. The bot keeps running on `.env`; fix or empty that box on the Settings page. |
| `the web page is not serving: ...` | The password rule above. The bot keeps running without the page. |
| `familydb could not start: ... Permission denied: '.env'` | You ran it as a user who cannot read the file. Run it as `familydb`, from the install folder. |
| `the database could not be opened` | `FAMILYDB_PATH` names a folder this user cannot write to or reach. |

Developer docs: `src/familydb/config.py` (`Settings`, `load_settings`), `.env.example`, `scripts/install.sh` (`set_env`), `docker-compose.yml`, `deploy/familydb.service`, and `RUNBOOK.md`, "The web page".
