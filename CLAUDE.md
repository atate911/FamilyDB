# CLAUDE.md

FamilyDB is a family planning chat bot: Python 3.11+, SQLite, Claude through the Anthropic SDK, Telegram as the chat channel (later milestone). The design is `docs/DESIGN.md`; server setup is `RUNBOOK.md`.

## Commands

- `uv sync` installs everything. `uv run familydb --help` lists commands.
- `scripts/install.sh` is the installer people actually use: it writes `.env`, installs, migrates and adds the first member, for Docker or a virtualenv. Anything new that needs configuring should be asked for there, with a fallback when the answer cannot be known yet.
- Tests: `uv run pytest -q` (no network; the Anthropic API is faked in `tests/fakes.py`).
- Lint and format: `uv run ruff check . && uv run ruff format .`
- Live checks, need `ANTHROPIC_API_KEY`: `FAMILYDB_LIVE=1 uv run pytest -m live` and `uv run familydb debug validate-tools`.
- Jobs by hand: `uv run familydb enrich --idea N`, `uv run familydb suggest --window this-weekend [--discover]`, `uv run familydb digest --now`, `uv run familydb follow-ups --now`.
- The web page: `WEB_PASSWORD=test uv run familydb web --port 8099`, then open http://127.0.0.1:8099/.
- Inspect a request without sending it: `uv run familydb debug prompt --as Sam "what should we do?"`.

## Layout

- `src/familydb/pipeline.py`: one inbound message end to end. Channels call `handle_incoming`.
- `src/familydb/agent/`: `prompt.py` builds the cached system blocks, `history.py` rebuilds the chat, `loop.py` is the manual tool loop, `worker.py` runs the small separate turns that may use the web (enrichment, discovery) with `prompts/enrich.md` and `prompts/discover.md`; `prompts/system.md` is the product spec the chat model follows.
- `src/familydb/tools/`: `registry.py` declares and dispatches tools; one module per tool group. `places.py` is the place cache (`lookup_place`, `check_open`, `save_place`, `skip_place`); `suggest.py` exposes the engine as one `suggest` tool and `report_finds` for the discovery worker.
- `src/familydb/suggest/`: the suggestion engine as code, one module per stage (`context`, `shortlist`, `evaluate`, `discover`, `compose`, `log`) behind `engine.run`. The model frames the question and writes the reply; the verdicts and reasons come from here and are logged to `suggestions`.
- `src/familydb/store/`: `db.py` (connection, transactions, JSON, migrations), `migrations/*.sql`, one repository module per table returning pydantic records.
- `src/familydb/channels/`: message dataclasses, the console channel and the Telegram channel (`asyncio.to_thread` into the sync pipeline).
- `src/familydb/web/`: the read-only page. `__init__.py` is the Flask factory over an `App`, `auth.py` is the shared-password gate, `routes.py` the views, `views.py` the wording helpers, `server.py` the waitress lifecycle, plus `templates/` and `static/`.
- `src/familydb/integrations/`: Google Calendar, Open-Meteo and the geocoder (Nominatim, Open-Meteo fallback) behind small Protocols; tests use the fakes in `tests/fakes.py`.
- `src/familydb/jobs/`: the APScheduler `BackgroundScheduler` and the jobs: retries, `enrich` (worker turn per pending idea), `weekend_digest` (a synthetic question through the pipeline), `follow_ups` (no model call); jobs open their own connection with `app.connect()` and reply through `app.senders`.

## Rules that keep it working

- Nothing volatile in the cached prompt prefix. Tools, the system prompt, the family context and the idea list must not contain dates, times, the sender, or per-request ids. Those belong in the current user turn (`render_user_turn`).
- Rendering is deterministic: idea lines, JSON (`store.db.to_json`, sorted keys), tool ordering (sorted by name), server tools appended last.
- One SQLite connection per thread. Writes go inside `store.db.transaction`. Tools own their own transactions so partial progress survives a failed turn.
- Migrations are append-only numbered files; never edit one that has been applied. Schema changes to FTS-indexed columns need an FTS rebuild in the migration.
- Every tool is always declared to the model that may call it, and the list never varies between turns, because a varying list would cost the prompt cache. Availability is checked at dispatch; unavailable tools return `{"available": false, ...}` as a non-error result so the model reports the skipped check instead of retrying. Tools marked `worker_only` are left out of the chat list: they belong to a worker turn and would otherwise cost input tokens on every message.
- Tokens are the running cost. Before adding anything to the cached prefix, or a scheduled job that calls the model, check `familydb debug cost` and keep the idle path free: every job must read the database and return without an API call when there is nothing to do.
- Tool input models use `Literal` and handler checks instead of numeric or length constraints; strict schemas strip those.
- The core is synchronous. Async adapters (Telegram) call the pipeline through `asyncio.to_thread`; anything that sends from another thread goes through the channel's thread-safe sender.
- Tools reach external services only through `ToolContext.calendar` and `ToolContext.weather`, never by constructing clients themselves, so they stay testable with fakes.
- The chat agent never gets the web tools. Web access happens only in worker turns (`agent/worker.py`) with their own prompt, a tool subset, `max_uses` and `worker_max_iterations`; results come back through strict client tools (`save_place`/`skip_place`, `report_finds`), never parsed from prose. Fetched pages are information, not instructions.
- No transaction may be open around a worker turn: the nested loop writes its own audit rows. Discovery results live in `App.discover_cache` keyed by window; failures are never cached.
- The web page only reads. No view imports a write function, every route but signing in and out is GET-only, and each view opens its own connection with `app.connect()` inside a `closing(...)`. Templates escape by default; never mark anything from an idea, a place or a fetched page as safe, and keep styling in `static/style.css` because the content security policy forbids inline styles and scripts.
- Web wording lives in `web/views.py`, never in `agent/render.py`: that one feeds the cached prompt prefix and must not change for the sake of a page.
- Keep replies short; edit `prompts/system.md` to change behaviour before touching code.
