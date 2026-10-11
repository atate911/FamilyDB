"""Command-line interface for FamilyDB."""

from __future__ import annotations

import json
import logging
import signal
import sqlite3
import sys
import threading
from contextlib import closing, suppress
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import typer

from familydb import __version__, memory, passwords, privacy
from familydb import family as family_rules
from familydb.agent import uses
from familydb.agent.history import load_history
from familydb.agent.providers import companies
from familydb.agent.providers.base import Message, TurnRequest
from familydb.agent.render import (
    render_audience_line,
    render_idea_line,
    render_memories,
    render_user_turn,
)
from familydb.app import App, build_app
from familydb.availability import (
    digest_configured,
    enrichment_available,
    happening_available,
    web_available,
    web_tools_available,
)
from familydb.base import roles
from familydb.base.config import Settings, apply_overrides, load_settings
from familydb.base.dates import utc_iso
from familydb.base.errors import ConfigError, FamilyDBError
from familydb.channels.console import DEFAULT_CHAT, one_shot, run_repl
from familydb.integrations import google_calendar
from familydb.store import calls, db, ideas, logins, members, messages
from familydb.store import settings as settings_store
from familydb.store.members import Member
from familydb.tools import ToolContext

app = typer.Typer(
    name="familydb",
    help="FamilyDB: a private family planning assistant.",
    no_args_is_help=True,
    add_completion=False,
    # Rich's boxed traceback is unreadable in journalctl and `docker compose logs`, where these are
    # read.
    pretty_exceptions_enable=False,
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
    privacy.private_by_default()


def _ready(application: App) -> sqlite3.Connection:
    """A migrated connection with the stored settings in force: a command shows what the bot is
    doing, not what a file says.
    """
    application.migrate()
    conn = application.connect()
    application.refresh(conn)
    return conn


def _push_key(application: App) -> None:
    """The key that signs pushes to the family's devices, made once at start (push.py), never on
    a page view."""
    from familydb import push
    from familydb.base.dates import utc_iso

    with closing(application.connect()) as conn:
        push.ensure_key(conn, utc_iso(application.clock.now()))


FROM_PAGE = "set on the settings page"
FROM_ENV = "from the environment"
# How much of a long Personality-page text `familydb config` prints: enough to tell which one (a
# rewrite also holds her whole shipped character).
SHOWN_CHARACTERS = 60


def _shown_setting(key: str, value: Any) -> Any:
    """A setting as `familydb config` prints it on one line: long Personality-page texts are cut to
    their start with their real length, and line breaks written as \\n.
    """
    if key not in settings_store.PROFILE:
        return value
    shown = _shortened(value)
    return shown.replace("\r", "\\r").replace("\n", "\\n") if isinstance(shown, str) else shown


def _shortened(value: Any) -> Any:
    if isinstance(value, str) and len(value) > SHOWN_CHARACTERS:
        return f"{value[:SHOWN_CHARACTERS].rstrip()}… ({len(value):,} characters)"
    if isinstance(value, dict):
        return {key: _shortened(item) for key, item in value.items()}
    return value


def stored_settings(settings: Settings) -> dict[str, Any]:
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
    except Exception as exc:
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
        typer.echo(f"{key}={_shown_setting(key, value)}{note}")


@app.command("password")
def password(
    name: str | None = typer.Argument(
        None,
        help="Whose, by the name on the family list. Left out: the first admin who signs in, "
        "or the family password while everybody still shares one.",
    ),
) -> None:
    """A new password for the web page, printed once, for one nobody remembers.

    Once people sign in as themselves it is a starting password for one person, the first admin
    unless a name is given: they sign in with it and choose their own, and are signed out
    wherever they were. While the family still shares one password, it replaces that one and
    signs everyone out. Either way whoever can run this on the server is let back in, and the old
    password stops working at once.
    """
    application = build_app()
    with closing(_ready(application)) as conn:
        personal = logins.admin_can_sign_in(conn)
        if name is None and not personal:
            fresh = passwords.make_up()
            with db.transaction(conn):
                settings_store.set_many(
                    conn,
                    {"web_password_hash": passwords.hash_password(fresh)},
                    source="familydb password",
                )
            typer.echo(f"The family password is now: {fresh}")
            typer.echo("Sign in with it, then choose your own password: the setup page asks.")
            return
        if name is None:
            person: Member | None = logins.admins_signing_in(conn)[0]
        else:
            person = members.find_by_name(conn, name)
        if person is None:
            typer.secho(f"There is nobody called {name} on the family list.", err=True)
            raise typer.Exit(1)
        if not personal and person.role != "admin":
            typer.secho(FIRST_OWN_PASSWORD, err=True)
            raise typer.Exit(1)
        try:
            made = family_rules.give_starting_password(
                conn, person.id, by=None, now=utc_iso(application.clock.now())
            )
        except family_rules.FamilyError as exc:
            typer.secho(str(exc), err=True)
            raise typer.Exit(1) from exc
    typer.echo(f"{person.display_name}'s password is now: {made}")
    typer.echo(
        f"A starting password: {person.display_name} signs in with it, as {person.display_name}, "
        "and chooses their own."
    )


FIRST_OWN_PASSWORD = (
    "Nobody signs in as themselves yet, and the first one to must be an admin: give an admin a "
    "password first (familydb password THEIR_NAME), or leave the name out for a new family "
    "password."
)


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
    source = application.settings.familydb_path
    # Every other command may create the database; a backup may not: run from cron in the wrong
    # directory it would back up a new empty database and report success every night.
    if not source.exists():
        typer.secho(f"no database at {source.resolve()}", fg=typer.colors.RED, err=True)
        typer.secho(
            "  Nothing was written. Run this from the checkout, or set FAMILYDB_PATH to an\n"
            "  absolute path, which is what a backup from cron needs.",
            err=True,
        )
        raise typer.Exit(1)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with closing(application.connect()) as conn, closing(sqlite3.connect(str(dest))) as target:
        conn.backup(target)
        # The copy itself is read back: a backup nobody can restore is no backup.
        verdict = db.quick_check(target)[0]
    ok = verdict == "ok"
    from familydb.store import backups

    try:
        with closing(application.connect()) as conn, db.transaction(conn):
            backups.record(
                conn,
                path=str(dest),
                size=dest.stat().st_size,
                ok=ok,
                detail=None if ok else verdict[:200],
                now=utc_iso(application.clock.now()),
            )
    except sqlite3.OperationalError as exc:  # a database not migrated yet keeps no record
        log.warning("the backup was not recorded: %s", exc)
    if not ok:
        failed = f"the backup at {dest} failed its check: {verdict}"
        typer.secho(failed, fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    typer.echo(f"backup written to {dest}, and checked")


@members_app.command("add")
def members_add(
    name: str = typer.Argument(..., help="Display name, e.g. Sam."),
    role: str = typer.Option("parent", "--role", help="admin, parent or kid."),
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
        signs_in = logins.by_member(conn)
    if not rows:
        typer.echo("no members yet; add one with: familydb members add NAME --role admin")
        return
    for member in rows:
        where = f"{member.channel}:{member.channel_user_id}" if member.channel else "no channel"
        flag = "" if member.active else " (inactive)"
        login = signs_in.get(member.id)
        if login is not None and roles.may(member.role, "sign_in"):
            flag += " (starting password)" if login.temporary else " (signs in)"
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
            source="cli",
        )
        result = registry.dispatch(name, payload, ctx)
    typer.echo(result.content, err=result.is_error)
    if result.is_error:
        raise typer.Exit(code=1)


@debug_app.command("prompt")
def debug_prompt(
    text: str = typer.Argument("", help="The message to build a chat request for."),
    as_member: str | None = typer.Option(None, "--as", help="Act as this family member."),
    chat_id: str = typer.Option(
        "console", "--chat", help="Chat whose history to include, and who reads it."
    ),
    kind: str = typer.Option(
        "chat", "--kind", help="Which kind of call: chat, digest, retry or enrich."
    ),
    idea_id: int | None = typer.Option(None, "--idea", help="For --kind enrich: which idea."),
) -> None:
    """Print the exact request that would be sent, without calling the API.

    Built by the same code that sends it (agent/gateway.py), so what is printed is what goes.
    Discovery is asked from inside a suggestion; `familydb suggest --discover` runs one.
    """
    from familydb.agent import gateway
    from familydb.agent.worker import worker_turn
    from familydb.jobs.enrich import render_enrich_request
    from familydb.jobs.weekend_digest import digest_channel
    from familydb.store import places

    if kind not in gateway.KINDS or kind in ("discover", "places", "scout", "find_feeds"):
        typer.echo("--kind is one of chat, digest, retry or enrich", err=True)
        raise typer.Exit(code=2)
    application = build_app()
    with closing(_ready(application)) as conn:
        settings = application.settings
        if kind == "enrich":
            idea = ideas.get(conn, idea_id) if idea_id is not None else None
            if idea is None:
                typer.echo("--kind enrich needs --idea N, the number of an idea", err=True)
                raise typer.Exit(code=2)
            place = places.get(conn, idea.place_id) if idea.place_id else None
            current = worker_turn(application.clock, render_enrich_request(idea, place, settings))
            history = []
        else:
            member = _acting_member(application, conn, as_member)
            sender = member.display_name if member else "someone"
            history = load_history(
                conn,
                chat_id,
                clock=application.clock,
                limit=settings.history_limit,
                since_hours=settings.history_hours,
            )
            channel = digest_channel(chat_id)
            audience = render_audience_line(channel, chat_id, members.list_all(conn))
            current = render_user_turn(sender, text, application.clock, audience)
            chosen = memory.choose(
                conn,
                text,
                sender_id=member.id if member else None,
                today=application.clock.today(),
            )
            remembered = render_memories(chosen)
            if remembered:
                current.append(remembered)
        provider = gateway.answering(settings, kind)[0]
        request = gateway.build_request(
            kind,
            conn=conn,
            settings=settings,
            registry=application.registry,
            current=current,
            history=history,
        ).request
    typer.echo(json.dumps(provider.payload(request), indent=2, ensure_ascii=False, default=str))


@debug_app.command("cost")
def debug_cost(
    days: int = typer.Option(30, "--days", help="How far back to add up."),
) -> None:
    """What the model has cost lately, and what each message pays for before anyone types."""
    import json as _json

    from familydb.agent import compose, gateway

    application = build_app()
    chat_call = gateway.spec("chat")
    with closing(_ready(application)) as conn:
        settings = application.settings
        blocks, _ = compose.prefix(chat_call, conn, settings)
        tools = compose.tool_defs(chat_call, application.registry)
        since = utc_iso(application.clock.now() - timedelta(days=days))
        rows = calls.usage_since(conn, since=since)
        kinds = calls.usage_by_kind(conn, since=since)
        measured = calls.sections_since(conn, since=since)

    system_tokens = sum(len(block.text) for block in blocks) // 4
    tool_tokens = len(_json.dumps([t.schema for t in tools], ensure_ascii=False)) // 4
    tool_tokens += sum(len(t.name) + len(t.description) for t in tools) // 4
    chat_provider, chat_model = gateway.answering(settings, "chat")
    digest_provider, digest_model = gateway.answering(settings, "digest")
    worker_provider, worker_model = gateway.answering(settings, "enrich")
    typer.echo("Sent with every chat message, and cached between them:")
    typer.echo(f"  system prompt and family context  ~{system_tokens:>6,d} tokens")
    typer.echo(f"  {len(tools)} tool definitions               ~{tool_tokens:>6,d} tokens")
    typer.echo(f"  {'in total':<33}~{system_tokens + tool_tokens:>6,d} tokens")
    levels = {key: uses.resolve(settings, key).level for key in ("chat", "digest", "lookup")}
    typer.echo(f"  chat runs on {chat_model} via {chat_provider.name} ({levels['chat']})")
    if (digest_provider.name, digest_model) != (chat_provider.name, chat_model):
        typer.echo(
            f"  the weekend digest runs on {digest_model} via {digest_provider.name} "
            f"({levels['digest']}), with a prompt cache of its own"
        )
    typer.echo(
        f"  lookups and discovery run on {worker_model} via {worker_provider.name} "
        f"({levels['lookup']})"
    )
    if not gateway.can_ask(settings, "enrich"):
        typer.echo(
            "  but nothing can look things up: the company that would cannot search the web, and "
            "no other that can has a key (or asking another company is off)"
        )
    if ttl := chat_provider.cache_ttl():
        typer.echo(f"  the prefix above is cached for {ttl}")
    spare = application.fallback("chat", chat_provider.name)
    if spare is not None:
        typer.echo(f"  {spare.name} answers when {chat_provider.name} cannot")
    if not rows:
        typer.echo(f"\nNo model calls in the last {days} days.")
        return
    typer.echo(f"\nActually used in the last {days} days:")
    typer.echo(f"  {'what for':<42} {'calls':>6} {'sent':>10} {'out':>8} {'US$':>7}")
    for row in kinds:
        typer.echo(
            f"  {gateway.purpose(row['kind']):<42} {row['calls']:>6,d} {row['sent']:>10,d} "
            f"{row['output_tokens']:>8,d} {row['cost_usd']:>7.2f}"
        )
    typer.echo("")
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
    for kind in gateway.KINDS:
        split = compose.breakdown(row for row in measured if row["kind"] == kind)
        if not split:
            continue
        counted = split[0]["calls"]
        typer.echo(
            f"\nWhere the input of {gateway.purpose(kind)} went, per call "
            f"({counted:,d} call{'' if counted == 1 else 's'}; the real total shared out by size):"
        )
        for part in split:
            typer.echo(f"  {part['label']:<42} ~{part['tokens']:>7,d} tokens  {part['share']:>3d}%")


@debug_app.command("validate-tools")
def debug_validate_tools() -> None:
    """Have the API validate the tool schemas via count_tokens (no generation, needs a key)."""
    from familydb.agent import gateway

    application = build_app()
    with closing(_ready(application)):
        provider, model = gateway.answering(application.settings, "chat")
    everything = application.registry.tool_defs(application.registry.names())
    request = TurnRequest(
        system=[], messages=[Message("user", ["hello"])], tools=everything, model=model
    )
    try:
        tokens = provider.count_tokens(request)
    except Exception as exc:
        typer.echo(f"validation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        f"{len(everything)} tools accepted by {model} "
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
    """Send one message to the bot and print its reply. Needs a key for one of the providers."""
    application = build_app()
    sender = _console_member(application, as_member)
    chat_id = f"console:{uuid4().hex[:8]}" if fresh else DEFAULT_CHAT
    reply = one_shot(application, text, sender, chat_id)
    if reply is None:
        typer.echo("(duplicate message ignored)")
        return
    if reply.out_message_id is not None:
        from familydb.delivery import deliver

        deliver(application, reply.out_message_id, lambda _chat, text: typer.echo(text))
    else:
        typer.echo(reply.text)
    if reply.status in {"failed", "unknown_sender"}:
        if reply.status == "failed" and not application.can_ask("chat"):
            answering = uses.resolve(application.settings, "chat").company
            company = companies.get(answering, application.settings)
            env = f", or set {company.env_name}" if company and company.env_name else ""
            typer.echo(f"hint: no model key: type one on the settings page{env}", err=True)
        raise typer.Exit(code=1)


@app.command()
def repl(
    as_member: str | None = typer.Option(None, "--as", help="Speak as this family member."),
    fresh: bool = typer.Option(False, "--fresh", help="Start a new chat with no history."),
) -> None:
    """Chat with the bot interactively. Needs a key for one of the providers."""
    application = build_app()
    sender = _console_member(application, as_member)
    chat_id = f"console:{uuid4().hex[:8]}" if fresh else DEFAULT_CHAT
    run_repl(application, sender, chat_id)


@app.command()
def doctor(
    online: bool = typer.Option(
        False,
        "--online",
        help="Also ask the model API and Telegram whether the keys work, and the links answer.",
    ),
    fix: bool = typer.Option(
        False, "--fix", help="Put right the few things that can be, such as file permissions."
    ),
    as_json: bool = typer.Option(False, "--json", help="Machine-readable, for a setup script."),
    new_install: bool = typer.Option(
        False,
        "--new-install",
        hidden=True,
        help="As the installer's last word: what the page's setup does next is not a fault.",
    ),
) -> None:
    """Check this install end to end and say what, if anything, is wrong.

    Exits 1 when something must be fixed before the bot can work. Things that are merely not set
    up yet, which is most of a first install, are warnings and do not fail.
    """
    from familydb import doctor as checks

    application = build_app()
    with suppress(Exception):
        application.refresh()
    report = (
        checks.fix(application, online=online) if fix else checks.run(application, online=online)
    )
    if new_install:
        checks.as_new_install(report)
    if as_json:
        typer.echo(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    else:
        typer.echo("\n".join(checks.text(report)))
    if not report.healthy:
        raise typer.Exit(code=1)


@app.command()
def export(
    folder: Path = typer.Argument(..., help="Where to write the four files."),
) -> None:
    """Write the family's data to a folder: plans.ics, ideas.csv, tasks.csv and everything.json,
    with no key, password or device in them (familydb/export.py)."""
    from familydb import export as taking

    application = build_app()
    with closing(_ready(application)) as conn:
        written = taking.write_all(conn, application.settings, folder, application.clock.now())
    for path in written:
        typer.echo(str(path))


@app.command()
def health() -> None:
    """Whether FamilyDB is well: the database answers and the scheduled jobs are running.
    Exits 1 when not, for Docker's HEALTHCHECK or a monitor."""
    from familydb import health as well

    ok, words = well.check(build_app())
    typer.echo(words)
    if not ok:
        raise typer.Exit(code=1)


@app.command()
def run() -> None:
    """Start the bot: apply migrations, then serve the configured channels until stopped."""
    application = build_app()
    application.migrate()
    _push_key(application)
    privacy.tighten(application.settings)
    application.refresh()
    settings = application.settings
    from familydb.agent import gateway

    chat, chat_model = gateway.answering(settings, "chat")
    log.info(
        "familydb %s starting: db=%s answering on %s via %s, effort=%s, tz=%s",
        __version__,
        settings.familydb_path,
        chat_model,
        chat.name,
        settings.effort,
        settings.tz,
    )
    from familydb.jobs.scheduler import build_scheduler

    scheduler = build_scheduler(application)
    scheduler.start()
    from familydb import health

    health.ticked(application)
    stop_web = None
    if web_available(settings):
        from familydb.web.server import serve_in_thread

        stop_web = serve_in_thread(application)
    # Telegram is watched rather than started once, so a changed token takes effect in seconds.
    from familydb.channels.telegram import TelegramSupervisor

    telegram = TelegramSupervisor(application)
    telegram.start()
    try:
        _wait_for_stop(quiet=bool(settings.telegram_bot_token) or stop_web is not None)
    finally:
        telegram.stop()
        if stop_web is not None:
            stop_web()
        scheduler.shutdown(wait=False)
        with suppress(Exception):  # a database gone with the stop is no reason to raise
            health.stopped(application)
    log.info("stopped")


def _wait_for_stop(*, quiet: bool = False) -> None:
    stop = threading.Event()
    received: list[int] = []

    # Only note the signal: it can land mid-write of a log line, and logging from the handler would
    # write to the same stream and raise before the stop is set.
    def _stop(signum: int, _frame: object) -> None:
        received.append(signum)
        stop.set()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    if not quiet:
        log.info(
            "no chat channel yet; waiting. Add a Telegram token or turn the web page on; "
            "meanwhile `familydb chat` and `familydb repl` work."
        )
    # In slices: the kernel may hand SIGTERM to any thread, and Python runs the handler only when
    # the main thread next runs, which an untimed wait never lets it do.
    while not stop.wait(1):
        pass
    log.info("received signal %s, stopping", received[0])


@db_app.command("retry-failed")
def db_retry_failed(
    reset: bool = typer.Option(
        False,
        "--reset",
        help="Give messages that ran out of tries new ones first. Ones given up on purpose "
        "(a person taken off, a kid over the day's limit, no key) stay given up.",
    ),
) -> None:
    """Retry failed messages now (the running bot also does this on a schedule)."""
    from familydb.jobs.retry_failed import run_retries

    application = build_app()
    application.migrate()
    _cli_senders(application)
    if reset:
        with closing(application.connect()) as conn, db.transaction(conn):
            count = messages.reset_retries(
                conn, max_retries=application.settings.retry_max_attempts
            )
        typer.echo(f"reset {count} message(s)")
    recovered = run_retries(application)
    typer.echo(f"recovered {recovered} message(s)")


@google_app.command("connect")
def google_connect(
    key_file: Path = typer.Argument(..., help="The service account's JSON key from Google Cloud."),
    calendar_id: str = typer.Argument(..., help="The family calendar's id, shared with it."),
) -> None:
    """Connect the calendar from the server, as the settings page does: tries the key on the
    calendar, then keeps both."""
    application = build_app()
    try:
        info = google_calendar.service_account_key(key_file.read_text(encoding="utf-8"))
        google_calendar.check_access(info, calendar_id)
    except (OSError, google_calendar.GoogleSetupError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    key_path = Path(application.settings.google_key_path)
    google_calendar.save_key(key_path, json.dumps(info))
    with closing(application.connect()) as conn, db.transaction(conn):
        settings_store.set_many(
            conn, {"google_calendar_id": calendar_id.strip()}, changed_by=None, source="cli"
        )
    typer.echo(f"connected to {calendar_id.strip()}; the key is saved in {key_path}")


@google_app.command("events")
def google_events(days: int = typer.Option(7, "--days", help="How many days ahead.")) -> None:
    """Show upcoming events on the configured family calendar (a connection test)."""
    application = build_app()
    calendar = application.calendar
    if calendar is None:
        typer.echo(
            "Google Calendar is not connected; run `familydb google connect KEY_FILE CALENDAR_ID`.",
            err=True,
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


WINDOWS = {
    "now": "now",
    "today": "today",
    "this-weekend": "this_weekend",
    "next-weekend": "next_weekend",
    "someday": "someday",
}


def _window_payload(window: str) -> dict[str, Any]:
    if window in WINDOWS:
        return {"window": WINDOWS[window]}
    start, sep, end = window.partition("..")
    if sep and start and end:
        return {"window": "dates", "start": start.strip(), "end": end.strip()}
    raise typer.BadParameter(
        "use now, today, this-weekend, next-weekend, someday, or START..END (YYYY-MM-DD)"
    )


def _print_suggestion(data: dict[str, Any]) -> None:
    typer.echo(data["window"]["label"])
    for day in data["days"]:
        free = ", ".join(day["free"]) if day["free"] else "no free time"
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
        "this-weekend",
        "--window",
        help="now, today, this-weekend, next-weekend, someday, or START..END.",
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
    if discover and not web_tools_available(application.settings):
        typer.echo("set WEB_TOOLS_ENABLED=true to look for events on the web", err=True)
        raise typer.Exit(code=1)
    api = None
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
            source="cli",
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
    """Serve the web page in the foreground until interrupted."""
    from familydb.web.server import serve

    overrides: dict[str, Any] = {}
    if host:
        overrides["web_host"] = host
    if port:
        overrides["web_port"] = port
    application = build_app(**overrides)
    application.migrate()
    _push_key(application)
    privacy.tighten(application.settings)
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
    if not application.can_ask("chat"):
        typer.echo("digest not sent: there is no model key yet to write it with")
        return
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


@app.command("happening")
def happening_now(
    everything: bool = typer.Option(
        False, "--now", help="Read every source now, even those read in the last day or week."
    ),
) -> None:
    """Read what is on near home now (the running bot does this hourly, each source when due).

    With --now the weekly search and the lookup for calendars run too, within the month's
    budget for them."""
    from familydb.jobs.happening import run_happening

    application = build_app()
    application.migrate()
    if not happening_available(application.settings):
        typer.echo(
            "nothing to read: add a calendar or a Ticketmaster key, or turn on web lookups, "
            "on the settings page",
            err=True,
        )
        raise typer.Exit(code=1)
    _cli_senders(application)
    counts = run_happening(application, everything=everything)
    typer.echo(", ".join(f"{key}: {value}" for key, value in counts.items()))


@app.command("picks")
def picks_now(
    force: bool = typer.Option(False, "--now", help="Remake every set, fresh or not."),
) -> None:
    """Make her picks for Now (the running bot does this hourly, each set when due). Code only:
    no model call."""
    from familydb.jobs.picks import run_picks

    application = build_app()
    application.migrate()
    made = run_picks(application, force=force)
    typer.echo(", ".join(f"{key}: {value}" for key, value in made.items()))


def _stop(message: str, *detail: str) -> None:
    typer.secho(message, fg=typer.colors.RED, err=True)
    for line in detail:
        typer.secho(f"  {line}" if line else "", err=True)
    raise SystemExit(1)


def run_cli() -> None:
    """The console entry point: a bad setting or unopenable database gets a sentence naming it, not
    a traceback.
    """
    try:
        app()
    except ConfigError as exc:
        _stop(
            str(exc),
            "",
            "Fix it in .env or on the settings page, then run this again.",
            "`familydb config` prints every setting and where it came from.",
        )
    except sqlite3.OperationalError as exc:
        detail = []
        if "unable to open database file" in str(exc):
            detail = ["FAMILYDB_PATH names a folder this user cannot write to, or cannot reach."]
        _stop(f"the database could not be opened: {exc}", *detail)
    except OSError as exc:
        _stop(f"familydb could not start: {exc}")
