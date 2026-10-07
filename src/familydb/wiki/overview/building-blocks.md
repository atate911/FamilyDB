# Building blocks

FamilyDB is built from ordinary, widely used parts, and none of them needs attention day to day. `pyproject.toml` holds the version ranges, and `uv.lock` pins the exact versions the server runs. [How it is built](/wiki/overview/how-its-built) shows how the parts fit into one process.

## What it is built from

| Part | Used for | Why this one |
|---|---|---|
| Python (3.11 or newer) and uv | The language, and the tool that builds the virtualenv from `uv.lock` | Each model company and Google ship an official Python library, Telegram has a mature one, and SQLite comes with Python. uv installs the locked versions, so the server runs what was tested |
| Flask and its Jinja2 templates | The web page and this guide | Pages are built on the server, so a phone browser needs nothing else. Jinja2 escapes text by default, which matters because titles come from chat and summaries from fetched pages |
| waitress | Serving the page | Flask's own server is for development. waitress is a production server that also decides which proxy headers to believe |
| One database file ([SQLite](/wiki/reference/glossary#sqlite)) | All the data, and the search over ideas | One file on your machine is easy to back up, and a family has no need for a database server |
| APScheduler | The timer that runs the [jobs](/wiki/behavior/jobs) | It runs inside the process, so there is no cron entry or second service to keep running |
| python-telegram-bot | The Telegram connection | It asks Telegram for messages (long polling), so the server needs no open port for it |
| The Anthropic, OpenAI and Google libraries | Talking to the three [model companies](/wiki/boundaries/model-companies) | Each company's own library speaks its API correctly |
| Google's API client and auth libraries | Google Calendar, through a service account | FamilyDB holds a key for its own account and nobody's sign-in |
| pydantic | Reading settings from the environment and `.env`; checking each tool's input; the records the database returns | A bad value is refused at the edge, with a sentence naming it |
| typer | The `familydb` command and its help | See [The command line](/wiki/operations/command-line) |
| markdown | Showing this guide | The guide is Markdown files in the package, rendered when a page is first viewed and kept until the file changes |
| tzdata | The time-zone database | Python can then read the family's time zone on any machine, which is how "this weekend" gets the right days |
| Caddy | HTTPS in front of the page | It gets and renews the certificate and passes the page through to FamilyDB. nginx works instead if it is already on the server |
| systemd or Docker | Starting `familydb run` and restarting it | One of the two keeps the process up and brings it back after a reboot |

`pytest` (tests) and `ruff` (style checks) are in the development group only, and the server's install leaves them out.

## What it does not use

- No message broker, task queue or separate worker or database process. Jobs run on the in-process timer, and work that must survive a crash, such as a stored reply, waits in the database.
- No ORM. The code writes SQL by hand, one module per table.
- No JavaScript framework and no build step. The page is server-rendered HTML with a few stylesheets and small scripts in `static/`, and fonts and icons are bundled, so nothing loads from another site.

## What you look after

- **Upgrades.** `maintain.sh upgrade` installs the locked package versions (`uv sync --frozen --no-dev` on a virtualenv install, an image rebuild on Docker) and applies new migrations before it restarts FamilyDB. You do not run `pip` or edit `pyproject.toml`. [Upgrade and rollback](/wiki/operations/upgrade-and-rollback) has the steps.
- **Python.** Tests run on 3.11 and 3.12, and the Docker image runs 3.12. If the system's Python is older than 3.11, uv fetches a suitable one.
- **Caddy.** It comes from your system's packages or Caddy's own repository and is updated with the rest of the operating system. A FamilyDB upgrade does not fetch a newer Caddy image on Docker. [The server](/wiki/operations/host) says what to keep current.
- **Model companies.** A company can change what it offers or charges without any library changing. [Models and prices](/wiki/controls/status/models-and-prices) shows what the daily check found.

Developer docs: `pyproject.toml`, `uv.lock`, `Dockerfile`, `src/familydb/web/wiki.py`; `docs/DESIGN.md`, "Decisions"; `CLAUDE.md`, "Commands".
