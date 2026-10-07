# Building blocks

FamilyDB is built from a short list of ordinary, well-known parts, and this page names each one, says what it is there for and says what that costs you to know when you run the server. [How it is built](/wiki/overview/how-its-built) shows how the parts fit into one process.

## What it is built from

| Part | Used for | Why this one |
|---|---|---|
| Python (3.11 or newer) and uv | The language, and the tool that builds the virtualenv from `uv.lock` | Each model company and Google ship an official Python library, Telegram has a mature one, and SQLite comes with Python. uv installs the exact locked versions, so the server runs what was tested |
| Flask (`>=3.1,<4`) and its Jinja2 templates | The web page and this guide | Pages are built on the server, so a phone browser needs nothing else. Jinja2 escapes text by default, which matters because titles come from chat and summaries from fetched pages |
| waitress (`>=3.0,<4`) | Serving the page | Flask's own server is for development. waitress is a production server that also decides which proxy headers to believe |
| SQLite, with its FTS5 search | All the data, and the search over ideas | One file on your machine is easy to back up, and a family has no need for a database server. FTS5 (SQLite's full-text search) backs the ideas search |
| APScheduler (`>=3.11,<4`) | The timer that runs the [jobs](/wiki/behavior/jobs) | It runs inside the process, so there is no cron entry or second service to keep running |
| python-telegram-bot (`>=22.8,<23`) | The Telegram connection | It asks Telegram for messages (long polling), so the server needs no open port for it |
| `anthropic` (`>=1.7,<2`), `openai` (`>=2.54,<4`) and `google-genai` (`>=2.24,<3`) | Talking to the three [model companies](/wiki/boundaries/model-companies) | Each company's own library speaks its API correctly. Only the modules in `agent/providers/` import them |
| google-api-python-client (`>=2.190,<3`) and google-auth (`>=2.30,<3`) | Google Calendar, through a service account | The bot holds a key for its own account and no one's sign-in |
| pydantic (`>=2.9,<3`) and pydantic-settings (`>=2.15,<3`) | Reading settings from the environment and `.env`; checking each tool's input; the records the database returns | A bad value is refused at the edge, with a sentence naming it |
| typer (`>=0.27,<1`) | The `familydb` command and its help | See [the command line](/wiki/controls/command-line) |
| markdown (`>=3.7,<4`) | Showing this guide | The guide is Markdown files in the package, rendered when a page is first viewed and kept until the file changes |
| tzdata | The time-zone database | So Python can read the family's time zone on any machine, which is how "this weekend" gets the right days |
| Caddy | HTTPS in front of the page | It gets and renews the certificate and passes the page through to the bot. nginx works instead if it is already on the server |
| systemd or Docker | Starting `familydb run` and restarting it | One of the two keeps the process up and brings it back after a reboot |

The ranges are from `pyproject.toml`. `pytest` (tests) and `ruff` (style checks) are in the development group only, and the server's install leaves them out.

## What it does not use

- **No message broker or task queue.** There is no Redis, RabbitMQ or Celery. Jobs run on the in-process timer, and work that must survive a crash, such as a stored reply, waits in the database.
- **No ORM.** By convention the code writes SQL by hand, one module per table.
- **No JavaScript framework and no build step.** There is no `package.json`, bundler or Node in the repository, CI or installer. The page is server-rendered HTML, a few stylesheets and a few small scripts in `static/`, served as they are. Fonts and icons are bundled files, so nothing loads from another site.
- **No separate worker or database process.** There is one process, `familydb run`, and Docker runs one container for it. Caddy is a separate program in front, if you turn HTTPS on.
- **No HTTP client library of its own choosing.** Weather, geocoding and the price lists use `urllib.request` from the standard library. `httpx` is imported by `gemini.py` and `doctor.py`, but it arrives as a dependency of the model companies' libraries and is not in `pyproject.toml`.
- **No model library outside `agent/providers/`.** Nothing else in the code imports Anthropic's, OpenAI's or Google's model library, so the rest of the program cannot depend on one company.

## What each costs you to know

**Upgrades install what was tested.** `maintain.sh upgrade` backs up and moves to the newest version. On a virtualenv install it then installs the locked package versions with `uv sync --frozen --no-dev`; on Docker it rebuilds the image, which does the same. It applies any new migrations before it restarts the bot. You do not run `pip` or edit `pyproject.toml`. [Upgrade and rollback](/wiki/operations/upgrade-and-rollback) has the steps.

**Dependency updates are monthly.** The repository's Dependabot settings open a pull request each month for Python packages (minor and patch releases together, a major release on its own), GitHub Actions and Docker images. CI tests it, and it is reviewed like any change. It reaches your server only with a release you upgrade to.

**The floors are the tested versions.** The lower bound on a library in `pyproject.toml` is the version the code is tested with, and the upper bound holds back a new generation until the code is checked against it. A model company can also change what it offers or charges, which is a different matter from a library update; [Models and prices](/wiki/controls/status/models-and-prices) shows what the daily check found.

**Python.** CI tests 3.11 and 3.12, and the Docker image runs 3.12. On a virtualenv install, if the system's Python is older than 3.11, uv fetches a suitable one.

**The parts you look after yourself.** Caddy comes from your system's packages or Caddy's own repository and is updated with the rest of the operating system, and a FamilyDB upgrade does not fetch a newer Caddy image on Docker. [The server](/wiki/operations/host) says what to keep current. The database is one file plus its `-wal` and `-shm` companions, so use the backup job rather than copying it while the bot runs; see [Backup and restore](/wiki/operations/backup-and-restore).

Developer docs: `pyproject.toml` (`dependencies`, `dependency-groups`), `uv.lock`, `Dockerfile`, `.github/dependabot.yml`, `.github/workflows/ci.yml`, `src/familydb/web/wiki.py`; `docs/DESIGN.md`, "Decisions" (the Language and Web page stack rows); `CLAUDE.md`, "Commands".
