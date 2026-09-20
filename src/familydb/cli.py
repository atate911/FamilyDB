"""Command-line interface for FamilyDB."""

from __future__ import annotations

import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import anthropic
import typer

from familydb import __version__
from familydb.agent.client import request_params
from familydb.agent.history import load_history
from familydb.agent.prompt import build_messages, build_system_blocks
from familydb.agent.render import render_idea_line, render_user_turn
from familydb.app import App, build_app
from familydb.config import load_settings
from familydb.store import calls, db, ideas, members
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
    """A migrated connection for a CLI command."""
    application.migrate()
    return application.connect()


@app.command()
def config() -> None:
    """Print the resolved settings with secrets masked."""
    settings = load_settings()
    for key, value in settings.masked().items():
        typer.echo(f"{key}={value}")


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
                    now=application.clock.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
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
        request = {
            **request_params(settings),
            "system": system,
            "tools": application.registry.api_tools(settings),
            "messages": messages,
        }
    typer.echo(json.dumps(request, indent=2, ensure_ascii=False, default=str))


@debug_app.command("validate-tools")
def debug_validate_tools() -> None:
    """Have the API validate the tool schemas via count_tokens (no generation, needs a key)."""
    application = build_app()
    settings = application.settings
    tools = application.registry.api_tools(settings)
    try:
        result = application.client.beta.messages.count_tokens(
            model=settings.anthropic_model,
            tools=tools,
            messages=[{"role": "user", "content": "hello"}],
        )
    except anthropic.APIError as exc:
        typer.echo(f"validation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        f"{len(tools)} tools accepted by {settings.anthropic_model}; "
        f"prompt would be {result.input_tokens} input tokens"
    )
