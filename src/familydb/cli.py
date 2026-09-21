"""Command-line interface for FamilyDB."""

from __future__ import annotations

import json
import logging
import signal
import sqlite3
import sys
import threading
from contextlib import closing
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import typer

from familydb import __version__
from familydb.agent.history import load_history
from familydb.agent.prompt import build_messages, build_system_blocks
from familydb.agent.providers.base import Message, TurnRequest
from familydb.agent.render import render_idea_line, render_user_turn
from familydb.app import App, build_app
from familydb.availability import (
    digest_configured,
    enrichment_available,
    web_available,
    web_tools_available,
)
from familydb.channels.console import DEFAULT_CHAT, one_shot, run_repl
from familydb.config import Settings, apply_overrides, load_settings
from familydb.dates import utc_iso
from familydb.errors import FamilyDBError
from familydb.integrations import google_calendar
from familydb.store import calls, db, ideas, members, messages
from familydb.store import settings as settings_store
from familydb.store.members import Member
from familydb.tools import ToolContext

app = typer.Typer(
    name="familydb",
    help="FamilyDB: a private family planning assistant.",
    no_args_is_help=True,
    add_completion=False,
)
db_app = typer.Typer(help="Database maintenance.", no_args_is_help=True)
members_app = typer.Typer(help="Family members.", no_args_is_help=True)
ideas_app = typer.Typer(help="The ideas list.", no_args_is_help=True)
app.add_typer(db_app, name="db")
app.add_typer(members_app, name="members")
app.add_typer(ideas_app, name="ideas")
debug_app = typer.Typer(help="Inspection commands.", no_args_is_help=True)
app.add_typer(debug_app, name="debug")
google_app = typer.Typer(help="Google Calendar setup.", no_args_is_help=True)
app.add_typer(google_app, name="google")

log = logging.getLogger(__name__)

COUNTED_TABLES = ("members", "ideas", "places", "plans", "outcomes", "messages", "tool_calls")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"familydb {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show the version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """FamilyDB command-line interface."""


def _ready(application: App) -> sqlite3.Connection:
    """A migrated connection for a CLI command, with the stored settings already in force.

    A command should show the family what the bot is doing, not what a file says it would do if
    nothing had ever been changed from the page.
    """
    application.migrate()
    conn = application.connect()
    application.refresh(conn)
    return conn


FROM_PAGE = "set on the settings page"
FROM_ENV = "from the environment"


def stored_settings(settings: Settings) -> dict[str, Any]:
    """The overrides saved in the database, or nothing when there is no database yet."""
    try:
        with closing(db.connect(settings.familydb_path)) as conn:
            return settings_store.overrides(conn)
    except sqlite3.Error:
        return {}


@app.command()
def config() -> None:
    """Print the resolved settings, secrets masked, and say where each one came from."""
    base = load_settings()
    stored = stored_settings(base)
    try:
        settings = apply_overrides(base, stored)
    except Exception as exc:  # a stored value that no longer validates must not hide the rest
        typer.echo(f"stored settings are not usable, showing the environment's: {exc}", err=True)
        settings, stored = base, {}
    defaults = {
        name: field.get_default(call_default_factory=True)
        for name, field in Settings.model_fields.items()
    }
    for key, value in settings.masked().items():
        if key in stored:
            note = f"  # {FROM_PAGE}"
        elif key in defaults and getattr(base, key) != defaults[key]:
            note = f"  # {FROM_ENV}"
        else:
            note = ""
        typer.echo(f"{key}={value}{note}")


@db_app.command("migrate")
def db_migrate() -> None:
    """Create or upgrade the database schema."""
    application = build_app()
    applied = application.migrate()
    typer.echo(f"database: {application.settings.familydb_path}")
    typer.echo("applied: " + (", ".join(map(str, applied)) if applied else "up to date"))


@db_app.command("status")
def db_status() -> None:
    """Schema version, row counts and the most recent model calls."""
    application = build_app()
    with closing(_ready(application)) as conn:
        typer.echo(f"database: {application.settings.familydb_path}")
        typer.echo(f"schema version: {db.schema_version(conn)}")
        counts = db.table_counts(conn, COUNTED_TABLES)
        typer.echo(" | ".join(f"{table}: {count}" for table, count in counts.items()))
        recent = calls.recent_llm_calls(conn, limit=5)
    if recent:
        typer.echo("recent model calls:")
        for row in recent:
            typer.echo(
                f"  {row['created_at']} {row['served_model'] or row['model']} "
                f"stop={row['stop_reason']} in={row['input_tokens']} "
                f"cache_read={row['cache_read_input_tokens']} "
                f"cache_write={row['cache_creation_input_tokens']} out={row['output_tokens']}"
            )


@db_app.command("backup")
def db_backup(dest: Path = typer.Argument(..., help="Path of the backup file to write.")) -> None:
    """Copy the database with SQLite's online backup API (safe while the bot runs)."""
    application = build_app()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with closing(application.connect()) as conn, closing(sqlite3.connect(str(dest))) as target:
        conn.backup(target)
    typer.echo(f"backup written to {dest}")


@members_app.command("add")
def members_add(
    name: str = typer.Argument(..., help="Display name, e.g. Sam."),
    role: str = typer.Option("member", "--role", help="admin, member or kid."),
    channel: str | None = typer.Option(None, "--channel", help="e.g. telegram"),
    channel_user_id: str | None = typer.Option(
        None, "--channel-user-id", help="The person's id on that channel."
    ),
) -> None:
    """Add a family member. Kids need no channel; they can still be named as participants."""
    if role not in members.ROLES:
        raise typer.BadParameter(f"role must be one of {', '.join(members.ROLES)}")
    application = build_app()
    with closing(_ready(application)) as conn:
        try:
            with db.transaction(conn):
                member = members.add(
                    conn,
                    name,
                    role,  # type: ignore[arg-type]
                    channel=channel,
                    channel_user_id=channel_user_id,
                    now=utc_iso(application.clock.now()),
                )
        except sqlite3.IntegrityError as exc:
            raise typer.BadParameter(f"could not add {name!r}: {exc}") from exc
    typer.echo(f"added #{member.id} {member.display_name} ({member.role})")


@members_app.command("list")
def members_list(
    include_inactive: bool = typer.Option(False, "--all", help="Include inactive members."),
) -> None:
    """List family members."""
    application = build_app()
    with closing(_ready(application)) as conn:
        rows = members.list_all(conn, active_only=not include_inactive)
    if not rows:
        typer.echo("no members yet; add one with: familydb members add NAME --role admin")
        return
    for member in rows:
        where = f"{member.channel}:{member.channel_user_id}" if member.channel else "no channel"
        flag = "" if member.active else " (inactive)"
        typer.echo(f"#{member.id} {member.display_name} [{member.role}] {where}{flag}")


@ideas_app.command("list")
def ideas_list(
    include_dropped: bool = typer.Option(False, "--all", help="Include dropped ideas."),
    as_json: bool = typer.Option(False, "--json", help="Print JSON records instead of lines."),
) -> None:
    """List ideas, one line each, exactly as the model sees them."""
    application = build_app()
    with closing(_ready(application)) as conn:
        rows = ideas.list_all(conn, include_dropped=include_dropped)
    if as_json:
        typer.echo("[" + ",\n".join(idea.model_dump_json() for idea in rows) + "]")
        return
    if not rows:
        typer.echo("(no ideas yet)")
        return
    for idea in rows:
        typer.echo(render_idea_line(idea))


def _acting_member(application: App, conn: sqlite3.Connection, name: str | None) -> Member | None:
    """Who a CLI action is attributed to: --as NAME, CONSOLE_MEMBER, else the first admin."""
    wanted = name or application.settings.console_member
    if wanted:
        member = members.find_by_name(conn, wanted)
        if member is None:
            raise typer.BadParameter(f"no family member called {wanted!r}")
        return member
    admins = [m for m in members.list_all(conn) if m.role == "admin"]
    return admins[0] if admins else None


@app.command("tool")
def tool_cmd(
    name: str | None = typer.Argument(None, help="Tool name, e.g. add_idea."),
    json_input: str | None = typer.Option(None, "--json", help="Input as a JSON object."),
    stdin: bool = typer.Option(False, "--stdin", help="Read the JSON input from stdin."),
    schema: bool = typer.Option(False, "--schema", help="Print the tool's API definition."),
    list_tools: bool = typer.Option(False, "--list", help="List tools and availability."),
    as_member: str | None = typer.Option(None, "--as", help="Act as this family member."),
) -> None:
    """Run one tool directly, without the model. Handy for testing and scripting."""
    application = build_app()
    registry = application.registry
    if list_tools:
        for spec in registry.specs():
            state = "available" if spec.available(application.settings) else "unavailable"
            kind = "writes" if spec.writes else "reads"
            typer.echo(f"{spec.name:16} {state:12} {kind:6} {spec.description[:60]}")
        return
    if not name:
        raise typer.BadParameter("give a tool name, or --list")
    spec = registry.get(name)
    if spec is None:
        raise typer.BadParameter(f"unknown tool {name!r}; see --list")
    if schema:
        typer.echo(json.dumps(spec.api_definition(), indent=2, ensure_ascii=False))
        return
    raw = sys.stdin.read() if stdin else (json_input or "{}")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"input is not valid JSON: {exc}") from exc
    with closing(_ready(application)) as conn:
        ctx = ToolContext(
            conn=conn,
            settings=application.settings,
            clock=application.clock,
            member=_acting_member(application, conn, as_member),
            calendar=application.calendar,
            weather=application.weather,
        )
        result = registry.dispatch(name, payload, ctx)
    typer.echo(result.content, err=result.is_error)
    if result.is_error:
        raise typer.Exit(code=1)


@debug_app.command("prompt")
def debug_prompt(
    text: str = typer.Argument(..., help="The message to build a request for."),
    as_member: str | None = typer.Option(None, "--as", help="Act as this family member."),
    chat_id: str = typer.Option("console", "--chat", help="Chat whose history to include."),
) -> None:
    """Print the exact request that would be sent for TEXT, without calling the API."""
    application = build_app()
    settings = application.settings
    with closing(_ready(application)) as conn:
        member = _acting_member(application, conn, as_member)
        sender = member.display_name if member else "someone"
        system = build_system_blocks(conn, settings)
        history = load_history(
            conn,
            chat_id,
            clock=application.clock,
            limit=settings.history_limit,
            since_hours=settings.history_hours,
        )
        messages = build_messages(history, render_user_turn(sender, text, application.clock))
        provider = application.provider("chat")
        request = provider.payload(
            TurnRequest(
                system=system,
                messages=messages,
                tools=application.registry.tool_defs(),
                model=provider.model_for("chat"),
            )
        )
    typer.echo(json.dumps(request, indent=2, ensure_ascii=False, default=str))


@debug_app.command("cost")
def debug_cost(
    days: int = typer.Option(30, "--days", help="How far back to add up."),
) -> None:
    """What the model has cost lately, and what each message pays for before anyone types."""
    import json as _json

    from familydb.agent.prompt import build_system_blocks

    application = build_app()
    settings = application.settings
    with closing(_ready(application)) as conn:
        blocks = build_system_blocks(conn, settings)
        tools = application.registry.tool_defs()
        since = utc_iso(application.clock.now() - timedelta(days=days))
        rows = calls.usage_since(conn, since=since)

    # Four characters to the token is rough, but enough to show what is large.
    system_tokens = sum(len(block.text) for block in blocks) // 4
    tool_tokens = len(_json.dumps([t.schema for t in tools], ensure_ascii=False)) // 4
    tool_tokens += sum(len(t.name) + len(t.description) for t in tools) // 4
    chat_provider = application.provider("chat")
    worker_provider = application.provider("worker")
    typer.echo("Sent with every chat message, and cached between them:")
    typer.echo(f"  system prompt and family context  ~{system_tokens:>6,d} tokens")
    typer.echo(f"  {len(tools)} tool definitions               ~{tool_tokens:>6,d} tokens")
    typer.echo(f"  {'in total':<33}~{system_tokens + tool_tokens:>6,d} tokens")
    typer.echo(f"  chat runs on {chat_provider.model_for('chat')} via {chat_provider.name}")
    typer.echo(
        f"  lookups and discovery run on {worker_provider.model_for('worker')} "
        f"via {worker_provider.name}"
    )
    if chat_provider.name == "anthropic":
        typer.echo(f"  the prefix above is cached for {settings.anthropic_cache_ttl}")
    spare = application.fallback("chat", chat_provider.name)
    if spare is not None:
        typer.echo(f"  {spare.name} answers when {chat_provider.name} cannot")
    if not rows:
        typer.echo(f"\nNo model calls in the last {days} days.")
        return
    typer.echo(f"\nActually used in the last {days} days:")
    header = f"  {'model':<28} {'calls':>6} {'in':>9} {'cached':>9} {'written':>9} {'out':>8}"
    typer.echo(header)
    for row in rows:
        typer.echo(
            f"  {row['model']:<28} {row['calls']:>6,d} {row['input_tokens']:>9,d} "
            f"{row['cache_read']:>9,d} {row['cache_write']:>9,d} {row['output_tokens']:>8,d}"
        )
    total_in = sum(r["input_tokens"] for r in rows)
    cached = sum(r["cache_read"] for r in rows)
    served = total_in + cached + sum(r["cache_write"] for r in rows)
    share = (cached / served * 100) if served else 0.0
    typer.echo(f"  {share:.0f}% of input tokens came from the cache at a tenth of the price.")


@debug_app.command("validate-tools")
def debug_validate_tools() -> None:
    """Have the API validate the tool schemas via count_tokens (no generation, needs a key)."""
    application = build_app()
    provider = application.provider("chat")
    everything = application.registry.tool_defs(application.registry.names())
    request = TurnRequest(system=[], messages=[Message("user", ["hello"])], tools=everything)
    try:
        tokens = provider.count_tokens(request)
    except (FamilyDBError, NotImplementedError) as exc:
        typer.echo(f"validation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # whatever the SDK raises for a rejected schema
        typer.echo(f"validation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        f"{len(everything)} tools accepted by {provider.model_for('chat')} "
        f"via {provider.name}; prompt would be {tokens} input tokens"
    )


def _console_member(application: App, as_member: str | None) -> str:
    with closing(_ready(application)) as conn:
        member = _acting_member(application, conn, as_member)
    if member is None:
        raise typer.BadParameter(
            "no family members yet; add one with: familydb members add NAME --role admin"
        )
    return member.display_name


@app.command()
def chat(
    text: str = typer.Argument(..., help="The message to send."),
    as_member: str | None = typer.Option(None, "--as", help="Speak as this family member."),
    fresh: bool = typer.Option(False, "--fresh", help="Start a new chat with no history."),
) -> None:
    """Send one message to the bot and print its reply. Needs an Anthropic API key."""
    application = build_app()
    sender = _console_member(application, as_member)
    chat_id = f"console:{uuid4().hex[:8]}" if fresh else DEFAULT_CHAT
    reply = one_shot(application, text, sender, chat_id)
    if reply is None:
        typer.echo("(duplicate message ignored)")
        return
    typer.echo(reply.text)
    if reply.status in {"failed", "unknown_sender"}:
        if reply.status == "failed" and not application.settings.anthropic_api_key:
            typer.echo("hint: ANTHROPIC_API_KEY is not set (see .env.example)", err=True)
        raise typer.Exit(code=1)


@app.command()
def repl(
    as_member: str | None = typer.Option(None, "--as", help="Speak as this family member."),
    fresh: bool = typer.Option(False, "--fresh", help="Start a new chat with no history."),
) -> None:
    """Chat with the bot interactively. Needs an Anthropic API key."""
    application = build_app()
    sender = _console_member(application, as_member)
    chat_id = f"console:{uuid4().hex[:8]}" if fresh else DEFAULT_CHAT
    run_repl(application, sender, chat_id)


@app.command()
def run() -> None:
    """Start the bot: apply migrations, then serve the configured channels until stopped."""
    application = build_app()
    application.migrate()
    application.refresh()  # before anything reads a setting, including the scheduler
    settings = application.settings
    chat = application.provider("chat")
    log.info(
        "familydb %s starting: db=%s answering on %s via %s, effort=%s, tz=%s",
        __version__,
        settings.familydb_path,
        chat.model_for("chat"),
        chat.name,
        settings.effort,
        settings.tz,
    )
    from familydb.jobs.scheduler import build_scheduler

    scheduler = build_scheduler(application)
    scheduler.start()
    stop_web = None
    if web_available(settings):
        from familydb.web.server import serve_in_thread

        stop_web = serve_in_thread(application)
    try:
        if settings.telegram_bot_token:
            from familydb.channels.telegram import TelegramChannel

            channel = TelegramChannel(application)
            log.info("starting the Telegram channel (long polling)")
            channel.run()
        else:
            _wait_for_stop()
    finally:
        if stop_web is not None:
            stop_web()
        scheduler.shutdown(wait=False)
    log.info("stopped")


def _wait_for_stop() -> None:
    stop = threading.Event()

    def _stop(signum: int, _frame: object) -> None:
        log.info("received signal %s, stopping", signum)
        stop.set()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    log.info("no chat channel configured; waiting. Use `familydb chat` or `familydb repl`.")
    stop.wait()


@db_app.command("retry-failed")
def db_retry_failed(
    reset: bool = typer.Option(
        False, "--reset", help="Make exhausted messages eligible again first."
    ),
) -> None:
    """Retry failed messages now (the running bot also does this on a schedule)."""
    from familydb.jobs.retry_failed import run_retries

    application = build_app()
    application.migrate()
    _cli_senders(application)
    if reset:
        with closing(application.connect()) as conn, db.transaction(conn):
            count = messages.reset_retries(conn)
        typer.echo(f"reset {count} message(s)")
    recovered = run_retries(application)
    typer.echo(f"recovered {recovered} message(s)")


@google_app.command("auth")
def google_auth(
    client_secrets: Path = typer.Option(
        ..., "--client-secrets", help="OAuth desktop-app credentials JSON from Google Cloud."
    ),
) -> None:
    """Sign in once on a machine with a browser. Saves the token to GOOGLE_TOKEN_PATH."""
    application = build_app()
    token_path = Path(application.settings.google_token_path)
    if not client_secrets.exists():
        raise typer.BadParameter(f"{client_secrets} does not exist")
    google_calendar.run_auth_flow(client_secrets, token_path)
    typer.echo(f"token saved to {token_path}")
    typer.echo("If this is not the server, copy that file into the server's data folder.")


@google_app.command("calendars")
def google_calendars() -> None:
    """List the calendars the signed-in account can see, with their ids."""
    application = build_app()
    try:
        creds = google_calendar.load_credentials(Path(application.settings.google_token_path))
        rows = google_calendar.list_calendars(creds)
    except FamilyDBError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    for row in rows:
        flags = row["access"] or ""
        if row["primary"]:
            flags += ", primary"
        typer.echo(f"{row['id']}    {row['summary']}    ({flags})")


@google_app.command("events")
def google_events(days: int = typer.Option(7, "--days", help="How many days ahead.")) -> None:
    """Show upcoming events on the configured family calendar (a connection test)."""
    application = build_app()
    calendar = application.calendar
    if calendar is None:
        typer.echo(
            "Google Calendar is not configured; set GOOGLE_CALENDAR_ID and run auth.", err=True
        )
        raise typer.Exit(code=1)
    now = application.clock.now()
    try:
        events = calendar.list_events(now, now + timedelta(days=days))
    except FamilyDBError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    if not events:
        typer.echo("no events in that window")
    for event in events:
        when = event.start.isoformat() if event.all_day else event.start.strftime("%a %d %b %H:%M")
        typer.echo(f"{when}  {event.title}" + (f"  @ {event.location}" if event.location else ""))


def _cli_senders(application: App) -> None:
    """Let a one-off command deliver replies the way the running bot would."""
    token = application.settings.telegram_bot_token
    if token:
        from familydb.channels.telegram import send_once

        application.senders["telegram"] = lambda chat_id, text: send_once(token, chat_id, text)


WINDOWS = {"this-weekend": "this_weekend", "next-weekend": "next_weekend", "someday": "someday"}


def _window_payload(window: str) -> dict[str, Any]:
    if window in WINDOWS:
        return {"window": WINDOWS[window]}
    start, sep, end = window.partition("..")
    if sep and start and end:
        return {"window": "dates", "start": start.strip(), "end": end.strip()}
    raise typer.BadParameter("use this-weekend, next-weekend, someday, or START..END (YYYY-MM-DD)")


def _print_suggestion(data: dict[str, Any]) -> None:
    typer.echo(data["window"]["label"])
    for day in data["days"]:
        free = ", ".join(day["free"]) if day["free"] else "no free block"
        if not day["free_known"]:
            free += " (calendar not checked)"
        weather = day.get("forecast") or "no forecast"
        if day.get("rain_chance_pct") is not None:
            weather += f", {day['rain_chance_pct']}% rain"
        typer.echo(f"  {day['weekday']} {day['date']}: free {free} · {weather}")
    for candidate in data["candidates"]:
        reasons = "; ".join(candidate.get("reasons", [])) or "nothing against it"
        typer.echo(
            f"{candidate['verdict']:<9} #{candidate['idea_id']} {candidate['title']}: {reasons}"
        )
    if data.get("not_shown"):
        typer.echo(f"          ... and {data['not_shown']} more, ranked below these")
    for find in data.get("web_finds", []):
        when = f" ({find['dates']})" if find.get("dates") else ""
        typer.echo(f"web       {find['title']}{when}: {find['url']}")
    if data.get("skipped_checks"):
        typer.echo("skipped: " + "; ".join(data["skipped_checks"]))


@app.command()
def suggest(
    window: str = typer.Option(
        "this-weekend", "--window", help="this-weekend, next-weekend, someday, or START..END."
    ),
    as_member: str | None = typer.Option(None, "--as", help="Ask as this family member."),
    discover: bool = typer.Option(
        False, "--discover", help="Also look for time-bound events on the web (calls the API)."
    ),
    json_output: bool = typer.Option(False, "--json", help="Print the full result as JSON."),
) -> None:
    """Run the suggestion engine directly and print its verdicts, without the chat model."""
    application = build_app()
    payload = _window_payload(window)
    payload["question"] = f"what should we do {window.replace('-', ' ')}?"
    payload["discover"] = discover
    api = None
    if discover:
        if not web_tools_available(application.settings):
            typer.echo("set WEB_TOOLS_ENABLED=true to look for events on the web", err=True)
            raise typer.Exit(code=1)
        api = None  # the settings decide which provider runs discovery
    with closing(_ready(application)) as conn:
        ctx = ToolContext(
            conn=conn,
            settings=application.settings,
            clock=application.clock,
            member=_acting_member(application, conn, as_member),
            calendar=application.calendar,
            weather=application.weather,
            geocoder=application.geocoder,
            api=api,
            discover_cache=application.discover_cache,
        )
        result = application.registry.dispatch("suggest", payload, ctx)
    if result.is_error:
        typer.echo(result.content, err=True)
        raise typer.Exit(code=1)
    if json_output:
        typer.echo(result.content)
        return
    _print_suggestion(json.loads(result.content))


@app.command()
def web(
    host: str | None = typer.Option(None, "--host", help="Override WEB_HOST for this run."),
    port: int | None = typer.Option(None, "--port", help="Override WEB_PORT for this run."),
) -> None:
    """Serve the read-only web page in the foreground until interrupted."""
    from familydb.web.server import serve

    overrides: dict[str, Any] = {}
    if host:
        overrides["web_host"] = host
    if port:
        overrides["web_port"] = port
    application = build_app(**overrides)
    application.migrate()
    try:
        serve(application)
    except FamilyDBError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except (OSError, ValueError) as exc:
        typer.echo(f"could not serve the page: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except KeyboardInterrupt:
        typer.echo("stopped")


@app.command()
def digest(
    now: bool = typer.Option(False, "--now", help="Send the weekend digest to the chat now."),
) -> None:
    """Show the digest schedule, or send it now with --now (the running bot sends it weekly)."""
    from familydb.jobs.weekend_digest import digest_channel, run_digest

    application = build_app()
    settings = application.settings
    if not digest_configured(settings):
        typer.echo("set DIGEST_CHAT_ID to the family chat to enable the weekend digest", err=True)
        raise typer.Exit(code=1)
    chat_id = settings.digest_chat_id or ""
    if not now:
        typer.echo(
            f"digest goes to {digest_channel(chat_id)} chat {chat_id} every {settings.digest_day} "
            f"at {settings.digest_hour:02d}:00 {settings.tz}; add --now to send it now"
        )
        return
    application.migrate()
    _cli_senders(application)
    application.senders["console"] = lambda _chat_id, text: typer.echo(text)
    reply = run_digest(application)
    if reply is None:
        typer.echo("digest not sent: already sent today, or no sender or admin (see the log)")
        raise typer.Exit(code=1)
    if reply.status != "ok":
        typer.echo(f"digest turn ended {reply.status}: {reply.text}", err=True)
        raise typer.Exit(code=1)
    if digest_channel(chat_id) != "console":
        typer.echo(f"sent the digest to {chat_id}")


@app.command("follow-ups")
def follow_ups(
    now: bool = typer.Option(False, "--now", help="Ask about finished plans now."),
) -> None:
    """Ask how recent plans went (the running bot does this daily at FOLLOW_UP_HOUR)."""
    from familydb.jobs.follow_ups import run_follow_ups

    application = build_app()
    settings = application.settings
    if not now:
        typer.echo(
            f"follow-ups go out daily at {settings.follow_up_hour:02d}:00 {settings.tz} to the "
            "chat each plan was made in; add --now to ask now"
        )
        return
    application.migrate()
    _cli_senders(application)
    application.senders["console"] = lambda _chat_id, text: typer.echo(text)
    typer.echo(f"asked about {run_follow_ups(application)} plan(s)")


@app.command()
def enrich(
    idea_id: int | None = typer.Option(None, "--idea", help="Look up this one idea, even if done."),
    limit: int | None = typer.Option(None, "--limit", help="How many pending ideas to process."),
) -> None:
    """Look up place details for pending ideas now (the running bot does this on a schedule)."""
    from familydb.jobs.enrich import run_enrichment

    application = build_app()
    application.migrate()
    if not enrichment_available(application.settings):
        typer.echo("set WEB_TOOLS_ENABLED=true to look ideas up on the web", err=True)
        raise typer.Exit(code=1)
    _cli_senders(application)
    counts = run_enrichment(application, idea_id=idea_id, limit=limit)
    typer.echo(", ".join(f"{key}: {value}" for key, value in counts.items()))
