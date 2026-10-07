# The .env file

The `.env` file in the install folder holds what only the server can decide: how the web page is reached, where the data lives, and the shared password. Everything else is a setting on the [Settings page](/wiki/controls/settings), and `.env` is only where it starts from.

Commands written as `familydb <command>` run as in [How to run it](/wiki/operations/command-line#how-to-run-it).

## How the file is read

The file is `/opt/familydb/.env`. FamilyDB reads the `.env` in its working directory when it starts and never again, so a change takes effect at the next restart. A missing file stops the systemd service from starting. On Docker, Compose reads the file on the host and passes the values in; the container has no `.env`.

- Write one `KEY=value` per line, with the key in capitals. A line starting with `#` is a comment.
- Quote any value with a space or a `#`, in single quotes: `WEB_PASSWORD='two words # three'`. Unquoted, python-dotenv and Compose drop a ` #` and what follows, while systemd keeps it, so one line can mean two things.
- An empty value, such as `HOME_LAT=`, means not set, so the default applies. A few settings, such as the worker model and company and the home area, treat empty as a real answer.
- A key FamilyDB does not know is ignored without a word, so a misspelled name does nothing.
- A key given twice takes the last line. A real environment variable of the same name beats the file.

## How it relates to the Settings page

What was saved on the web page wins over `.env`, which wins over the built-in default; [How a setting gets its value](/wiki/controls/settings#how-a-setting-gets-its-value) explains how, and `familydb config` shows each value and its source ([Diagnostics](/wiki/operations/diagnostics#reading-familydb-config)). A `.env` line that does nothing is almost always a setting saved on the web page. Keys that are Settings-page settings are not listed here.

A key typed on the web page is in every [backup](/wiki/operations/backup-and-restore); a key in `.env` is not.

## Keys only .env sets

| Key | Default | What it does |
|---|---|---|
| `WEB_ENABLED` | `false` | Whether `familydb run` serves the web page. The installer sets `true` |
| `WEB_HOST` | `127.0.0.1` | The address the web page listens on. A loopback address keeps it to this machine; any other, `0.0.0.0` included, opens it to the network and needs a password unless `WEB_ALLOW_NO_PASSWORD` waives it |
| `WEB_PORT` | `8080` | The port it listens on. The installer and `maintain.sh port` allow 1025 to 65535, because the service is unprivileged |
| `WEB_PASSWORD` | empty | The shared password, the first way in. Changing it signs out everyone who signed in with it |
| `WEB_SECRET_KEY` | empty | Signs the login cookie. Empty, one is generated into `data/web_secret` |
| `WEB_ALLOW_NO_PASSWORD` | `false` | Lets a web page open to the network run with no password. Ignored behind a proxy |
| `WEB_TRUST_PROXY` | `false` | Believes the forwarding headers of one proxy hop (the visitor's address and HTTPS) and marks the login cookie Secure. Set it only with Caddy or nginx in front |
| `FAMILYDB_PATH` | `data/familydb.sqlite3` | The database, relative to the install folder; the session key is kept beside it. Leave it: the unit, Compose and `maintain.sh` assume `data/` |
| `GOOGLE_KEY_PATH` | `data/google_key.json` | Where the calendar's key file is kept. The Connections page writes it |
| `ANTHROPIC_FALLBACKS` | `true` | Anthropic only: lets Anthropic re-run a declined request on its own fallback model, for the models that support it. Set only here, with no box on the Settings page |
| `CONSOLE_MEMBER` | empty | Whom the command line acts as when `--as` is not given. Empty is the first admin on the family list |
| `GEOCODER_CONTACT` | empty | An email address or web page sent with each OpenStreetMap place lookup, as its usage policy asks. Empty sends none |
| `WEB_DOMAIN` | empty | For the scripts, not the program: the name (on a virtualenv install, the address) Caddy gets a certificate for |
| `WEB_PUBLIC_PORT` | empty, meaning 443 | For the scripts and Compose: the port the web page is served on over HTTPS |
| `COMPOSE_PROFILES` | not set | For Compose: `tls` makes `docker compose up -d` start Caddy too |

Set `WEB_SECRET_KEY` when more than one process serves the web page. While it is set, **Sign everyone out** cannot replace it: change the value and restart. Outside Docker, keep `WEB_HOST=127.0.0.1` with `WEB_TRUST_PROXY=true`, or the web page believes every client's forwarding headers. With `WEB_TRUST_PROXY` off and the web page open to the network, every visitor shares one lockout.

> **Anyone who can reach the web page can use all of it, Settings included,** when `WEB_ALLOW_NO_PASSWORD` is `true` and `WEB_HOST` is open to the network.

### When a password is required

The web page refuses to start without one when `WEB_HOST` is not a loopback address (unless `WEB_ALLOW_NO_PASSWORD` is `true`), and when `WEB_TRUST_PROXY` is `true`. It needs at least 12 characters. A [shared password](/wiki/reference/glossary#shared-password) chosen on the Settings page, or an admin's own password, meets the rule, so `WEB_PASSWORD` can then be empty. When the rule fails, `familydb web` stops, while `familydb run` logs `the web page is not serving` and carries on with Telegram and the jobs. `familydb doctor` tests the rule; `familydb config` does not.

### What differs on Docker

Compose sets `FAMILYDB_PATH`, `GOOGLE_KEY_PATH` and `WEB_HOST` itself, so those lines in `.env` have no effect there. The web page binds `0.0.0.0` inside the container, so by the rule above Docker needs a password, though Compose publishes the port to this machine only. To open it to the local network, drop `127.0.0.1:` from the `ports` line in `docker-compose.yml`.

## What the installer writes

The installer copies `.env.example` to `.env` with mode 600, so every uncommented line of the example is in your file at its default. It then writes `WEB_ENABLED=true`, `WEB_HOST`, `WEB_PORT` and `WEB_PASSWORD` (made up or the one you gave). With HTTPS in front it adds `WEB_DOMAIN`, `WEB_TRUST_PROXY` and, on Docker, `COMPOSE_PROFILES=tls`; `WEB_PUBLIC_PORT` appears only for a port other than 443. It also gives `FAMILYDB_TZ`, `WEB_TOOLS_ENABLED=true` and `DIGEST_CHAT_ID=web` starting values, unless you gave others. Running it again keeps an existing `.env`; if you ask it to start over, it saves the old file as `.env.<timestamp>.bak`.

## Changing it safely

1. Keep a copy, since `.env` is not in the backups:

```bash
sudo cp -p /opt/familydb/.env /root/familydb.env.before
```

2. Edit it, for example with `sudo nano /opt/familydb/.env`, then check `ls -l /opt/familydb/.env`. On a virtualenv install it should read `-rw-------` and `familydb familydb`. If an editor changed that, run:

```bash
sudo chown familydb:familydb /opt/familydb/.env && sudo chmod 600 /opt/familydb/.env
```

3. Check that it loads, so a wrong value stops here and not the service. It checks values only; `doctor` also tests the password rule.

On a virtualenv install:

```bash
cd /opt/familydb && sudo -u familydb env HOME=/opt/familydb .venv/bin/familydb config
```

On Docker:

```bash
sudo docker compose --project-directory /opt/familydb run --rm -T bot familydb config
```

4. Restart, then check. On Docker, `restart` stops the container and runs `docker compose up -d`; a plain `docker compose restart` does not re-read `.env`.

```bash
sudo /opt/familydb/scripts/maintain.sh restart
sudo /opt/familydb/scripts/maintain.sh check
```

## Who can read it

> **Anyone who can read `.env` can sign in with `WEB_PASSWORD`, forge logins with `WEB_SECRET_KEY` (together with the database) and spend on any key kept there.** `familydb doctor` warns when group or others can read it, and `--fix` sets mode 600.

[The server](/wiki/operations/host#everything-the-install-put-on-the-server) lists the other files and their owners.

## When a value is wrong

Every `familydb` command that reads the settings, `doctor` and `config` included, stops with this and exit status 1:

```text
a setting will not do:
  web_port: Input should be less than or equal to 65535

  Fix it in .env or on the settings page, then run this again.
  `familydb config` prints every setting and where it came from.
```

The service exits the same way and systemd or Docker starts it again, so the journal repeats the message until the file is right. Other messages:

| You see | It means |
|---|---|
| `stored settings are not usable, keeping the ones in the environment` | A value saved on the web page no longer fits, often after an upgrade. FamilyDB keeps running on `.env`; fix or empty that box on the Settings page |
| `the web page is not serving: ...` | The password rule above. FamilyDB keeps running without the web page |

Developer docs: src/familydb/config.py; .env.example; docker-compose.yml; deploy/familydb.service; RUNBOOK.md, "The web page".
