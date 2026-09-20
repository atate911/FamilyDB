# CLAUDE.md

FamilyDB is a family planning chat bot: Python 3.11+, SQLite, Claude through the Anthropic SDK, Telegram as the chat channel (later milestone). The design is `docs/DESIGN.md`; server setup is `RUNBOOK.md`.

## Commands

- `uv sync` installs everything. `uv run familydb --help` lists commands.
- Tests: `uv run pytest -q` (no network; the Anthropic API is faked in `tests/fakes.py`).
- Lint and format: `uv run ruff check . && uv run ruff format .`
- Live checks, need `ANTHROPIC_API_KEY`: `FAMILYDB_LIVE=1 uv run pytest -m live` and `uv run familydb debug validate-tools`.
- Inspect a request without sending it: `uv run familydb debug prompt --as Sam "what should we do?"`.

## Layout

- `src/familydb/pipeline.py`: one inbound message end to end. Channels call `handle_incoming`.
- `src/familydb/agent/`: `prompt.py` builds the cached system blocks, `history.py` rebuilds the chat, `loop.py` is the manual tool loop, `prompts/system.md` is the product spec the model follows.
- `src/familydb/tools/`: `registry.py` declares and dispatches tools; one module per tool group. Stubs stay declared with real input models until their integration lands.
- `src/familydb/store/`: `db.py` (connection, transactions, JSON, migrations), `migrations/*.sql`, one repository module per table returning pydantic records.
- `src/familydb/channels/`: message dataclasses and the console channel. Telegram goes here.

## Rules that keep it working

- Nothing volatile in the cached prompt prefix. Tools, the system prompt, the family context and the idea list must not contain dates, times, the sender, or per-request ids. Those belong in the current user turn (`render_user_turn`).
- Rendering is deterministic: idea lines, JSON (`store.db.to_json`, sorted keys), tool ordering (sorted by name), server tools appended last.
- One SQLite connection per thread. Writes go inside `store.db.transaction`. Tools own their own transactions so partial progress survives a failed turn.
- Migrations are append-only numbered files; never edit one that has been applied. Schema changes to FTS-indexed columns need an FTS rebuild in the migration.
- Every tool is always declared to the model. Availability is checked at dispatch; unavailable tools return `{"available": false, ...}` as a non-error result so the model reports the skipped check instead of retrying.
- Tool input models use `Literal` and handler checks instead of numeric or length constraints; strict schemas strip those.
- The core is synchronous. Async adapters (Telegram) call the pipeline through `asyncio.to_thread`.
- Keep replies short; edit `prompts/system.md` to change behaviour before touching code.
