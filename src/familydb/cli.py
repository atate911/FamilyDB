"""Command-line interface for FamilyDB."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import typer

from familydb import __version__
from familydb.agent.render import render_idea_line
from familydb.app import App, build_app
from familydb.config import load_settings
from familydb.store import calls, db, ideas, members

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
