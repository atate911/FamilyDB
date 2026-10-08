"""One command that answers "is this install right, and if not what is wrong?"

Each check gives a verdict, what was found and, when wrong, the one thing to do. Ordered as an
install goes, so the first failure is usually the cause of the rest. Nothing reaches the network
unless `online` is set: a first install is often done before any key exists, and a check that
hangs on a firewall is worse than none.
"""

from __future__ import annotations

import os
import shutil
import socket
import sqlite3
import stat
import subprocess
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from familydb import happening, health, privacy
from familydb.agent.providers import companies
from familydb.app import App
from familydb.availability import (
    calendar_available,
    digest_configured,
    happening_available,
    weather_available,
    web_is_public,
    web_tools_available,
)
from familydb.dates import utc_iso
from familydb.store import alerts as alert_store
from familydb.store import db, members, problems

OK = "ok"
WARN = "warn"
FAIL = "fail"
SKIP = "skip"
TODO = "todo"

MARKS = {OK: "✓", WARN: "!", FAIL: "✗", SKIP: "·", TODO: "→"}
NEW_INSTALL_STEPS = {"family": "Add yourself", "model key": "Connect an AI model"}
FREE_MB_WANTED = 500
# A message that has waited this long for an answer is not being answered: the retry job comes
# round every few minutes.
WAITING = timedelta(minutes=10)
UNSENT = timedelta(minutes=15)
GAVE_UP = timedelta(days=7)
_RESTORE = "Put the newest backup back: sudo scripts/maintain.sh restore FILE (RUNBOOK section 7)"
# Troubles the hourly upkeep notes that the doctor reads for itself, and ones that are news, not
# trouble.
NOT_TROUBLE = frozenset({"new", "advice", "calendars", "backup", "disk"})


@dataclass
class Check:
    name: str
    verdict: str
    detail: str
    fix: str = ""
    corrected: str = ""
    group: str = ""

    def as_dict(self) -> dict[str, Any]:
        out = {"check": self.name, "verdict": self.verdict, "detail": self.detail}
        if self.group:
            out["group"] = self.group
        if self.fix:
            out["fix"] = self.fix
        if self.corrected:
            out["corrected"] = self.corrected
        return out


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)
    group: str = ""  # what the next checks are filed under: the headings of the printed report

    def add(self, name: str, verdict: str, detail: str, fix: str = "") -> Check:
        check = Check(name, verdict, detail, fix, group=self.group)
        self.checks.append(check)
        return check

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if c.verdict == FAIL]

    @property
    def warnings(self) -> list[Check]:
        return [c for c in self.checks if c.verdict == WARN]

    @property
    def healthy(self) -> bool:
        return not self.failures

    def as_dict(self) -> dict[str, Any]:
        return {
            "healthy": self.healthy,
            "failures": len(self.failures),
            "warnings": len(self.warnings),
            "checks": [c.as_dict() for c in self.checks],
        }


def _free_mb(path: Path) -> int | None:
    target = path if path.exists() else path.parent
    try:
        return int(shutil.disk_usage(target).free / (1024 * 1024))
    except OSError:
        return None


def _mode(path: Path) -> int | None:
    try:
        return stat.S_IMODE(path.stat().st_mode)
    except OSError:
        return None


def _port_answers(host: str, port: int, timeout: float = 1.0) -> bool:
    reachable = "127.0.0.1" if host in {"", "0.0.0.0", "::"} else host
    try:
        with socket.create_connection((reachable, port), timeout=timeout):
            return True
    except OSError:
        return False


# Read by the shell scripts or by Docker, not by the settings: still names in .env that are meant.
OTHER_OPTIONS = frozenset({"COMPOSE_PROFILES", "TZ", "WEB_DOMAIN", "WEB_PUBLIC_PORT"})


def _option_names() -> set[str]:
    """Every name .env may set that FamilyDB reads, from the settings themselves and from the
    example that ships beside them."""
    import re

    from pydantic import AliasChoices

    from familydb.config import Settings

    names = set(OTHER_OPTIONS)
    for setting, info in Settings.model_fields.items():
        alias = info.validation_alias
        if isinstance(alias, AliasChoices):
            names.update(str(choice).upper() for choice in alias.choices)
        elif isinstance(alias, str):
            names.add(alias.upper())
        names.add(setting.upper())
    example = Path(".env.example")
    if example.exists():
        names.update(re.findall(r"^#?\s*([A-Za-z][A-Za-z0-9_]+)=", example.read_text(), re.M))
    return {name.upper() for name in names}


def check_env_options(env_file: Path, report: Report) -> None:
    """A name in .env that FamilyDB does not read is silently ignored, so a typo means the value
    never takes effect: the commonest reason a setting "does nothing"."""
    import difflib
    import re

    try:
        text = env_file.read_text(encoding="utf-8-sig")
    except OSError:
        return
    known = _option_names()
    unknown: list[str] = []
    for line in text.splitlines():
        match = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        if match and match.group(1).upper() not in known and match.group(1) not in unknown:
            unknown.append(match.group(1))
    if not unknown:
        return
    said = []
    for name in unknown[:5]:
        close = difflib.get_close_matches(name.upper(), sorted(known), n=1, cutoff=0.75)
        said.append(f"{name} (did you mean {close[0]}?)" if close else name)
    report.add(
        "env options",
        WARN,
        f"{', '.join(said)}{' and more' if len(unknown) > 5 else ''}: not options FamilyDB reads, "
        "so a value set under that name never takes effect",
        "Correct the name in .env (the list is in .env.example), or delete the line",
    )


def check_settings(app: App, report: Report) -> None:
    settings = app.settings
    report.add(
        "settings",
        OK,
        f"loaded; timezone {settings.tz}, database {settings.familydb_path}",
    )
    env_file = Path(".env")
    if not env_file.exists():
        report.add(
            "env file",
            WARN,
            f"no .env in {Path.cwd()}, so the settings come from the environment alone",
            "Settings are read from the working directory, so run this from the install: "
            "cd /opt/familydb && familydb doctor",
        )
        return
    mode = _mode(env_file)
    if mode is not None and mode & 0o077:
        report.add(
            "env file",
            WARN,
            f".env is mode {mode:03o}, so other users on this machine can read your keys",
            "chmod 600 .env",
        )
    else:
        report.add("env file", OK, ".env is readable only by its owner")
    check_env_options(env_file, report)


def check_database(app: App, report: Report) -> sqlite3.Connection | None:
    path = Path(app.settings.familydb_path)
    free = _free_mb(path)
    if free is not None and free < FREE_MB_WANTED:
        report.add(
            "disk space",
            WARN,
            f"{free} MB free where the database lives",
            "Free some space, or move FAMILYDB_PATH to a larger disk",
        )
    else:
        report.add("disk space", OK, f"{free} MB free" if free is not None else "checked")

    if not path.exists():
        report.add(
            "database",
            FAIL,
            f"no database at {path.resolve()}",
            "familydb db migrate",
        )
        return None
    try:
        conn = app.connect()
    except sqlite3.Error as exc:
        unreadable = "not a database" in str(exc) or "malformed" in str(exc)
        report.add(
            "database",
            FAIL,
            f"could not open {path}: {exc}",
            _RESTORE if unreadable else "Check the file's owner",
        )
        return None

    try:
        current = db.schema_version(conn)
    except sqlite3.Error as exc:
        # A file SQLite opens but cannot read: the case the doctor is most wanted for.
        conn.close()
        report.add("database", FAIL, f"could not read {path}: {exc}", _RESTORE)
        return None
    latest = max((version for version, _n, _s in db.list_migrations()), default=0)
    if current < latest:
        report.add(
            "schema",
            FAIL,
            f"database is at migration {current}, the code expects {latest}",
            "familydb db migrate",
        )
    elif current > latest:
        report.add(
            "schema",
            WARN,
            f"database is at migration {current}, newer than this code's {latest}",
            "This checkout is older than the database; upgrade the code",
        )
    else:
        report.add("schema", OK, f"up to date at migration {current}")

    try:
        with closing(app.connect()) as probe:
            probe.execute("CREATE TABLE IF NOT EXISTS _doctor_write_probe (x INTEGER)")
            probe.execute("DROP TABLE _doctor_write_probe")
        report.add("database writable", OK, "a write succeeded")
    except sqlite3.Error as exc:
        report.add(
            "database writable",
            FAIL,
            f"cannot write: {exc}",
            f"Give {path.parent} to the user that runs the bot: "
            f"sudo chown -R familydb:familydb {path.parent}",
        )
    return conn


def _when(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def _size(path: Path) -> str:
    try:
        size = path.stat().st_size
    except OSError:
        return "?"
    return f"{size / 1024 / 1024:.1f} MB" if size >= 1024 * 1024 else f"{max(size // 1024, 1)} KB"


def _span(delta: timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    if minutes < 90:
        return f"{max(minutes, 1)} min"
    if minutes < 48 * 60:
        return f"{round(minutes / 60)} hours"
    return f"{minutes // (24 * 60)} days"


def check_time_zone(app: App, report: Report) -> None:
    """The family's clock, which every reminder, the digest and "this weekend" follow. A rented
    server starts out on UTC, so a family that never chose one gets its messages at the wrong hour.
    """
    settings = app.settings
    there = app.clock.now().astimezone(settings.tzinfo)
    if settings.family_tz is None and settings.tz == "UTC":
        report.add(
            "time zone",
            WARN,
            "none chosen, so the server's UTC is used: reminders, the digest and 'this weekend' "
            "follow that clock, not the family's",
            "Choose it on the settings page (General), or set FAMILYDB_TZ=Area/City",
        )
    else:
        whose = "" if settings.family_tz else " (the server's)"
        report.add("time zone", OK, f"{settings.tz}{whose}; it is {there:%H:%M} there now")


def check_integrity(app: App, conn: sqlite3.Connection, report: Report) -> None:
    """SQLite's own quick check of the file: a page it cannot read is found here, not by the
    message that happens to need it."""
    path = Path(app.settings.familydb_path)
    try:
        found = [row[0] for row in conn.execute("PRAGMA quick_check").fetchall()]
    except sqlite3.Error as exc:
        report.add("integrity", FAIL, f"the check itself failed: {exc}", _RESTORE)
        return
    if found == ["ok"]:
        report.add("integrity", OK, f"the file is sound ({_size(path)})")
    else:
        report.add(
            "integrity",
            FAIL,
            f"SQLite found {len(found)} problem(s), the first: {found[0] if found else '?'}",
            _RESTORE,
        )


def check_data_files(app: App, report: Report) -> None:
    """The database holds every message and any key typed on the settings page, so only its owner
    reads it (privacy.py makes them so; an older version left some 0644).
    """
    if os.name != "posix":
        return
    files = [
        path
        for path in privacy.sensitive_files(app.settings)
        if path.name != "web_secret" and path.exists()  # the login key has its own check
    ]
    loose = [path for path in files if (_mode(path) or 0) & privacy.OWNER_ONLY]
    if loose:
        report.add(
            "data files",
            WARN,
            f"{', '.join(path.name for path in loose)} can be read by other users on this machine",
            f"chmod 600 {' '.join(str(path) for path in loose)}  (or: familydb doctor --fix)",
        )
    elif files:
        report.add("data files", OK, "the database and its keys are readable only by their owner")


def check_spending(app: App, conn: sqlite3.Connection | None, report: Report) -> None:
    from familydb.agent import spending

    if conn is None:
        return
    settings = app.settings
    try:
        spent = spending.spent_today(conn, settings, app.clock.now())
    except sqlite3.Error:
        report.add("spending today", SKIP, "the database is not up to date yet")
        return
    limit = settings.daily_spend_limit
    if not limit:
        report.add("spending today", OK, f"${spent:.2f} so far (estimated); no daily limit is set")
    elif spent >= limit:
        report.add(
            "spending today",
            WARN,
            f"${spent:.2f} of ${limit:.2f} (estimated): the limit is used up, so the model "
            "answers nothing more until midnight",
            "Raise 'Daily spending limit' on the settings page if that was not meant",
        )
    else:
        report.add(
            "spending today",
            OK,
            f"${spent:.2f} of ${limit:.2f} (estimated), {round(100 * spent / limit)}% of the limit",
        )


def check_jobs(app: App, conn: sqlite3.Connection | None, report: Report) -> None:
    """Whether the scheduler is ticking: it sends the reminders, the digest and the retry of a
    message that failed, so a bot that is up while it is quiet looks well and does none of it.
    """
    from familydb.store import heartbeat

    if conn is None:
        return
    try:
        beat = heartbeat.read(conn)
    except sqlite3.Error:
        report.add("scheduled jobs", SKIP, "the database is not up to date yet")
        return
    if beat is None:
        report.add("scheduled jobs", SKIP, "none has run on this database; it was never started")
    elif beat.stopped_at is not None:
        report.add(
            "scheduled jobs",
            SKIP,
            f"stopped on purpose at {beat.stopped_at[:16].replace('T', ' ')} UTC",
        )
    else:
        quiet = app.clock.now() - _when(beat.jobs_at)
        if quiet > health.QUIET:
            report.add(
                "scheduled jobs",
                FAIL,
                f"last ticked {_span(quiet)} ago, so no reminder, digest or retry of a failed "
                "message is going out",
                "Is it running? sudo systemctl restart familydb, then journalctl -u familydb -n 50",
            )
        else:
            report.add("scheduled jobs", OK, f"ticking; the last was {_span(quiet)} ago")


def check_messages(app: App, conn: sqlite3.Connection | None, report: Report) -> None:
    """Messages that went in and got no answer, answers that never went out, and the ones the bot
    gave up on: the three ways a family notices it is broken before any log does.
    """
    if conn is None:
        return
    now = app.clock.now()
    attempts = app.settings.retry_max_attempts
    try:
        waiting = conn.execute(
            "SELECT count(*) AS n FROM messages WHERE direction = 'in' "
            "AND status IN ('received', 'failed') AND give_up = 0 AND retries < ? "
            "AND received_at < ?",
            (attempts, utc_iso(now - WAITING)),
        ).fetchone()["n"]
        unsent = conn.execute(
            "SELECT count(*) AS n FROM messages WHERE direction = 'out' AND delivered_at IS NULL "
            "AND cancelled_at IS NULL AND received_at < ?",
            (utc_iso(now - UNSENT),),
        ).fetchone()["n"]
        gave_up = conn.execute(
            "SELECT count(*) AS n, max(id) AS newest FROM messages WHERE direction = 'in' "
            "AND status = 'failed' AND (give_up = 1 OR retries >= ?) "
            "AND coalesce(error, '') != 'member_inactive' AND processed_at >= ?",
            (attempts, utc_iso(now - GAVE_UP)),
        ).fetchone()
        why = (
            conn.execute("SELECT error FROM messages WHERE id = ?", (gave_up["newest"],)).fetchone()
            if gave_up["newest"]
            else None
        )
    except sqlite3.Error:
        report.add("messages", SKIP, "the database is not up to date yet")
        return
    if waiting:
        report.add(
            "waiting messages",
            WARN,
            f"{waiting} message(s) have waited over {_span(WAITING)} for an answer; the retry job "
            f"tries again every {app.settings.retry_interval_minutes} min while the bot runs",
            "familydb db retry-failed, and journalctl -u familydb -n 50 for why they fail",
        )
    if unsent:
        report.add(
            "unsent replies",
            WARN,
            f"{unsent} reply(ies) are stored but were never delivered; the channel is refusing "
            "them or is not connected",
            "Check the Telegram token on the settings page; the retry job resends once it works",
        )
    if gave_up["n"]:
        error = ((why["error"] if why else "") or "no reason kept").strip().splitlines()[0][:100]
        report.add(
            "given-up messages",
            WARN,
            f"{gave_up['n']} message(s) in the last week were given up on, the newest because: "
            f"{error}",
            "Fix the cause, then: familydb db retry-failed --reset (the Status page lists them)",
        )
    if not (waiting or unsent or gave_up["n"]):
        report.add("messages", OK, "none waiting, no reply unsent, none given up on this week")


def check_trouble(app: App, conn: sqlite3.Connection | None, report: Report) -> None:
    """What the bot has told the admins it cannot fix, and what it logged at ERROR in the last
    day (the same two lists the Status and Troubleshooting pages show)."""
    from familydb import alerts

    if conn is None:
        return
    now = app.clock.now()
    try:
        standing = [
            one
            for one in alert_store.current(conn, since=utc_iso(now - alerts.KEEP))
            if one.kind not in NOT_TROUBLE
        ]
        counts = problems.counts_since(conn, since=utc_iso(now - timedelta(days=1)))
        latest = [
            row for row in problems.recent(conn, limit=25) if row["level"] in ("ERROR", "CRITICAL")
        ][:1]
    except sqlite3.Error:
        report.add("alerts", SKIP, "the database is not up to date yet")
        return
    if standing:
        named = "; ".join(
            f"{one.kind}{f' ({one.subject})' if one.subject else ''}: {one.detail}"[:90]
            for one in standing[:3]
        )
        more = f", and {len(standing) - 3} more" if len(standing) > 3 else ""
        report.add(
            "alerts",
            WARN,
            f"{len(standing)} standing: {named}{more}",
            "The Status page lists each with what to do about it",
        )
    else:
        report.add("alerts", OK, "nothing the admins were told about is still standing")
    errors = counts.get("ERROR", 0) + counts.get("CRITICAL", 0)
    quiet = counts.get("WARNING", 0)
    if errors:
        newest = ""
        if latest:
            newest = f"; the latest: {latest[0]['source']}: {str(latest[0]['message'])[:90]}"
        report.add(
            "logged errors",
            WARN,
            f"{errors} error(s) and {quiet} warning(s) in the last day{newest}",
            "Settings, Troubleshooting lists each with its detail; or: scripts/maintain.sh logs",
        )
    else:
        report.add("logged errors", OK, f"none in the last day ({quiet} warning(s))")


def check_family(
    conn: sqlite3.Connection | None, report: Report, *, telegram: bool = False
) -> None:
    if conn is None:
        report.add("family", SKIP, "no database to read")
        return
    try:
        everyone = members.list_all(conn)
    except sqlite3.Error as exc:
        report.add(
            "family", FAIL, f"could not read the members table: {exc}", "familydb db migrate"
        )
        return
    admins = [m for m in everyone if m.role == "admin"]
    if not everyone:
        report.add(
            "family",
            FAIL,
            "nobody is in the family yet, so no message can be answered",
            "Add yourself on the web page: its setup opens on it",
        )
        return
    if not admins:
        report.add(
            "family",
            WARN,
            f"{len(everyone)} member(s), none an admin; the digest is sent as the first admin",
            "familydb members add NAME --role admin",
        )
    else:
        report.add("family", OK, f"{len(everyone)} member(s), {len(admins)} admin(s)")
    reachable = [m for m in everyone if m.channel and m.channel_user_id]
    if not reachable and telegram:
        report.add(
            "family on a channel",
            WARN,
            "nobody has a Telegram id yet, so nobody can message the bot from a phone",
            "Have each person message the bot; its reply gives their id to type on the Family page",
        )
    else:
        report.add("family on a channel", OK, f"{len(reachable)} member(s) can message the bot")


def check_provider(app: App, report: Report, *, online: bool) -> None:
    settings = app.settings
    have = [
        slug
        for slug in companies.slugs(settings)
        if (company := companies.get(slug, settings)) and company.key(settings)
    ]
    if not have:
        report.add(
            "model key",
            FAIL,
            "no key for any provider, so the bot can save a message but never answer it",
            "Add one on the web page: its setup says where to get one",
        )
        return
    chosen = settings.provider
    company = companies.get(chosen, settings)
    chosen_env = (
        company.env_name if company else ""
    ) or f"the key of {chosen} on the settings page"
    if company is None or not company.key(settings):
        # Only a company that may stand in answers instead: one the family added does not unless
        # its admin said so.
        instead = [
            slug
            for slug in have
            if (spare := companies.get(slug, settings)) is not None and spare.stands_in
        ]
        if not instead:
            report.add(
                "model key",
                FAIL,
                f"PROVIDER is {chosen} but its key is empty, and no company with a key may stand "
                f"in ({', '.join(have)} must be chosen or allowed to)",
                f"Set {chosen_env}, or choose a company you have a key for",
            )
            return
        report.add(
            "model key",
            WARN,
            f"PROVIDER is {chosen} but its key is empty; {', '.join(instead)} will answer instead",
            f"Set {chosen_env}, or change PROVIDER to one you have a key for",
        )
    else:
        report.add("model key", OK, f"{', '.join(have)} configured; {chosen} answers chat")

    try:
        from familydb.agent import gateway

        chat, chat_model = gateway.answering(app.settings, "chat")
        digest, digest_model = gateway.answering(app.settings, "digest")
        worker, worker_model = gateway.answering(app.settings, "enrich")
        report.add(
            "models",
            OK,
            f"chat on {chat_model} via {chat.name}; "
            f"the digest on {digest_model} via {digest.name}; "
            f"lookups on {worker_model} via {worker.name}",
        )
    except Exception as exc:
        report.add("models", FAIL, f"could not build a provider: {exc}", "familydb config")
        return

    if not online:
        report.add("model reachable", SKIP, "not asked; pass --online to check the key")
        return
    # The same as `debug validate-tools`: counting a full request's tokens validates the key and
    # every tool schema for free.
    from familydb.agent.providers.base import Message, TurnRequest

    everything = app.registry.tool_defs(app.registry.names())
    request = TurnRequest(system=[], messages=[Message("user", ["hello"])], tools=everything)
    try:
        tokens = chat.count_tokens(request)
    except NotImplementedError:
        report.add(
            "model reachable",
            SKIP,
            f"{chat.name} cannot count tokens without generating, so there is nothing free to "
            "ask; the first real message is the check",
        )
    except Exception as exc:
        report.add(
            "model reachable",
            FAIL,
            f"the API refused: {exc}",
            "Check the key, and that the account can pay",
        )
    else:
        report.add(
            "model reachable",
            OK,
            f"{len(everything)} tools accepted; every message starts at {tokens} input tokens",
        )


def check_added_companies(app: App, report: Report, *, online: bool) -> None:
    """Each company the settings define: whether it could answer, and with `online`, what it says
    of the key and the models named for it. No model is asked: a company is tried end to end by
    choosing it and sending a message (`familydb chat`)."""
    from familydb.agent import providers
    from familydb.agent.providers import prices

    settings = app.settings
    for company in companies.added(settings):
        name = f"company {company.slug}"
        one = company.defined
        assert one is not None
        provider = providers.build(company.slug, settings)
        if not provider.configured():
            missing = "its key" if not company.key(settings) and not one.local else "a model"
            report.add(
                name,
                WARN,
                f"{company.label} cannot answer: {missing} is not set",
                "Set it on the AI model settings page, under Other companies",
            )
            continue
        role = (
            "answers the family"
            if settings.provider == company.slug
            else "may stand in"
            if company.stands_in
            else "is added and not used"
        )
        unpriced = [
            model for model in company.known_models() if prices.price(company.slug, model) is None
        ]
        if unpriced:
            report.add(
                f"{name} prices",
                WARN,
                f"{', '.join(unpriced)} cost nothing anyone has said, so the daily limit counts "
                "them at more than any listed model",
                "Type a price on the settings page, or let the daily check read the company's list",
            )
        if not online:
            report.add(name, OK, f"{company.label} {role}; pass --online to ask it")
            continue
        verdict = provider.check_key()
        if verdict == "refused":
            report.add(
                name,
                FAIL,
                f"{company.label} refuses the key",
                "Paste the key again on the AI model settings page",
            )
        elif verdict == "unchecked":
            report.add(name, WARN, f"{company.label} could not be asked just now")
        elif verdict == "unknown_model":
            report.add(
                name,
                WARN,
                f"{company.label} accepts the key but its list has no model called {one.model}",
                "Check the spelling against the company's own list",
            )
        else:
            listed = provider.listed_models()
            missing_models = [
                model
                for model in company.known_models()
                if listed is not None and model.lower() not in {n.lower() for n in listed}
            ]
            detail = f"{company.label} {role}; key accepted"
            if listed is not None:
                detail += f", {len(listed)} models listed"
            if missing_models:
                report.add(
                    name,
                    WARN,
                    f"{detail}; not listed: {', '.join(missing_models)}",
                    "Check the spelling, or whether the company has retired them",
                )
            else:
                report.add(name, OK, detail)


def check_channels(app: App, report: Report, *, online: bool) -> None:
    token = app.settings.telegram_bot_token
    if not token:
        report.add(
            "telegram",
            WARN,
            "no bot token, so the family can only use the web page's chat",
            "Create a bot with @BotFather and paste its token on the settings page",
        )
        return
    shape_ok = ":" in token and token.split(":", 1)[0].isdigit()
    if not shape_ok:
        report.add(
            "telegram",
            WARN,
            "the token does not look like a BotFather token (digits, a colon, then letters)",
            "Check it against what BotFather sent",
        )
    elif not online:
        report.add("telegram", OK, "a token is set; pass --online to ask Telegram if it is live")
    else:
        report.add("telegram", OK, "a token is set")
    if online and shape_ok:
        try:
            import httpx

            answer = httpx.get(
                f"https://api.telegram.org/bot{token}/getMe", timeout=10
            ).json()  # the token is in the URL; never log this
            if answer.get("ok"):
                report.add("telegram live", OK, f"@{answer['result'].get('username')} answers")
            else:
                report.add(
                    "telegram live",
                    FAIL,
                    "Telegram rejected the token",
                    "Get a new one from @BotFather with /revoke",
                )
        except Exception as exc:
            report.add("telegram live", WARN, f"could not reach Telegram: {exc}")


LINK_THERE = frozenset({401, 403, 405})


def check_links(report: Report, fetch: Any = None) -> None:
    """Whether every outside page the web page links to (web/links.py) still answers, and where a
    moved one now is. Online only.
    """
    from urllib.parse import urlparse

    from familydb.web.links import LINKS

    if fetch is None:
        import httpx

        def fetch(url: str) -> tuple[int, str]:
            answer = httpx.get(url, follow_redirects=True, timeout=10)
            return answer.status_code, str(answer.url)

    dead: list[str] = []
    moved: list[str] = []
    for key, url in LINKS.items():
        try:
            status, landed = fetch(url)
        except Exception as exc:
            dead.append(f"{key} ({type(exc).__name__})")
            continue
        if status >= 400 and status not in LINK_THERE:
            dead.append(f"{key} ({status})")
        elif urlparse(landed).hostname != urlparse(url).hostname:
            moved.append(f"{key} now at {landed}")
    if dead or moved:
        report.add(
            "links",
            WARN,
            "; ".join(
                part
                for part in (
                    f"no answer from {', '.join(dead)}" if dead else "",
                    "; ".join(moved),
                )
                if part
            ),
            "Change the address in src/familydb/web/links.py",
        )
    else:
        report.add("links", OK, f"all {len(LINKS)} pages the setup steps link to answer")


def check_integrations(app: App, report: Report) -> None:
    settings = app.settings
    if calendar_available(settings):
        report.add("google calendar", OK, f"calendar {settings.google_calendar_id} with a key")
    elif settings.google_calendar_id:
        report.add(
            "google calendar",
            WARN,
            f"a calendar id is set but no key at {settings.google_key_path}",
            "Connect it again on the settings page (Google Calendar)",
        )
    else:
        report.add(
            "google calendar",
            WARN,
            "not connected, so plans are remembered but never put on a calendar",
            "Connect it on the settings page (Google Calendar)",
        )

    if weather_available(settings):
        report.add("weather", OK, f"home at {settings.home_lat}, {settings.home_lon}")
    else:
        report.add(
            "weather",
            WARN,
            "no coordinates, so suggestions cannot use the forecast",
            "Type the home area on the settings page; it is found on the map",
        )

    if web_tools_available(settings):
        report.add("web lookups", OK, "on: new ideas get an address, hours and a travel estimate")
    else:
        report.add(
            "web lookups",
            WARN,
            "off, so ideas are never filled in and suggestions say 'hours unknown'",
            "Turn on 'Look ideas up on the web' on the settings page",
        )

    if happening_available(settings):
        report.add("near home", OK, f"{happening.NAME} has something to read")
    else:
        report.add(
            "near home",
            WARN,
            f"{happening.NAME} reads nothing, so suggestions know only what was saved",
            "Turn on web lookups, or add a calendar or a Ticketmaster key on the settings page",
        )

    if digest_configured(settings):
        report.add(
            "weekend digest",
            OK,
            f"posts to chat {settings.digest_chat_id} on {settings.digest_day} "
            f"at {settings.digest_hour}:00",
        )
    else:
        report.add(
            "weekend digest",
            WARN,
            "no chat id, so the weekly digest is not sent",
            "Set the digest chat on the settings page: 'web' for the page's own chat, or the "
            "family group's id",
        )


def check_web(app: App, report: Report, conn: sqlite3.Connection | None = None) -> None:
    from familydb.errors import ConfigError
    from familydb.web import check_configuration
    from familydb.web.auth import own_passwords
    from familydb.web.keys import secret_path

    settings = app.settings
    if not settings.web_enabled:
        report.add(
            "web page",
            WARN,
            "off, so there is no page to chat on, edit from, or configure it with",
            "WEB_ENABLED=true, then restart",
        )
        return
    # Asked as the page asks before serving: people with their own passwords need no shared one. A
    # database that cannot say is asked as if nobody had one.
    try:
        personal = conn is not None and own_passwords(conn)
    except sqlite3.Error:
        personal = False
    try:
        check_configuration(settings, own_passwords=personal)
    except ConfigError as exc:
        report.add("web page", FAIL, str(exc), "Set WEB_PASSWORD, or bind to 127.0.0.1")
        return

    where = "this machine only" if not web_is_public(settings) else "the network"
    report.add(
        "web page", OK, f"on at {settings.web_host}:{settings.web_port}, reachable from {where}"
    )

    if web_is_public(settings) and not settings.web_trust_proxy:
        report.add(
            "web page behind a proxy",
            WARN,
            "WEB_TRUST_PROXY is off while the page faces the network: every visitor shares one "
            "lockout and the login cookie is not marked Secure",
            "Put Caddy in front and set WEB_TRUST_PROXY=true (RUNBOOK section 10)",
        )

    secret = secret_path(settings)
    if secret.exists():
        mode = _mode(secret)
        if mode is not None and mode & 0o077:
            report.add(
                "login key",
                WARN,
                f"{secret} is mode {mode:03o}; anyone who reads it can forge a login",
                f"chmod 600 {secret}",
            )
        else:
            report.add("login key", OK, "stored beside the database, owner-only")
    elif settings.web_secret_key:
        report.add("login key", OK, "WEB_SECRET_KEY is set")
    else:
        report.add(
            "login key",
            WARN,
            "none yet; one is written the first time the page starts",
            "",
        )

    if _port_answers(settings.web_host, settings.web_port):
        report.add("web page answering", OK, f"something is listening on port {settings.web_port}")
    else:
        report.add(
            "web page answering",
            WARN,
            f"nothing is listening on port {settings.web_port}; the bot is probably not running",
            "Start it: sudo systemctl start familydb, or docker compose up -d",
        )


def check_backups(app: App, report: Report, conn: sqlite3.Connection | None) -> None:
    """When the last good backup was made (familydb/upkeep.py has the rule)."""
    from familydb import upkeep
    from familydb.store import backups

    if conn is None:
        return
    try:
        good = backups.latest(conn, good=True)
        trouble = upkeep.backup_trouble(conn, app.clock.now())
    except sqlite3.OperationalError:
        report.add("backups", SKIP, "the database is not up to date yet")
        return
    if trouble:
        report.add(
            "backups",
            WARN,
            trouble,
            "sudo crontab -u root -l, then scripts/maintain.sh backup (RUNBOOK section 7)",
        )
    elif good is None:
        report.add(
            "backups",
            WARN,
            "none recorded",
            "sudo scripts/maintain.sh schedule-backups (RUNBOOK section 7)",
        )
    else:
        report.add("backups", OK, f"the last good one {good.made_at[:16].replace('T', ' ')} UTC")


def check_service(report: Report) -> None:
    unit = Path("/etc/systemd/system/familydb.service")
    if not unit.exists():
        report.add(
            "service",
            SKIP,
            "no systemd unit; the bot is started by hand or by Docker",
        )
        return
    if not shutil.which("systemctl"):
        report.add("service", SKIP, "a unit is installed but systemctl is not here")
        return
    try:
        active = subprocess.run(
            ["systemctl", "is-active", "familydb"], capture_output=True, text=True, timeout=10
        ).stdout.strip()
        enabled = subprocess.run(
            ["systemctl", "is-enabled", "familydb"], capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        report.add("service", WARN, f"could not ask systemd: {exc}")
        return
    if active == "active":
        report.add("service", OK, f"running, {enabled} at boot")
    else:
        report.add(
            "service",
            WARN,
            f"installed but {active or 'not running'} ({enabled or 'not enabled'} at boot)",
            "sudo systemctl enable --now familydb, then journalctl -u familydb -n 50",
        )


def correct(app: App, report: Report) -> None:
    """Put right the few things that need no decision. Deliberately narrow: anything needing a key,
    password or judgement is left alone, since a guessing repair is worse than an honest warning.
    """
    for check in report.checks:
        if check.verdict not in (FAIL, WARN):
            continue
        if check.name == "env file" and "mode" in check.detail:
            try:
                Path(".env").chmod(0o600)
            except OSError as exc:
                check.corrected = f"could not change the mode: {exc}"
            else:
                check.corrected = "made .env readable only by its owner"
        elif check.name == "schema" and "expects" in check.detail:
            try:
                applied = app.migrate()
            except Exception as exc:
                check.corrected = f"could not migrate: {exc}"
            else:
                check.corrected = (
                    f"applied migration(s) {applied}" if applied else "nothing to apply"
                )
        elif check.name == "data files" and check.verdict == WARN:
            changed = privacy.tighten(app.settings)
            check.corrected = (
                f"made {', '.join(path.name for path in changed)} readable only by its owner"
                if changed
                else "nothing to change (the files are not owned by this user)"
            )
        elif check.name == "login key" and "mode" in check.detail:
            from familydb.web.keys import secret_path

            try:
                secret_path(app.settings).chmod(0o600)
            except OSError as exc:
                check.corrected = f"could not change the mode: {exc}"
            else:
                check.corrected = "made the login key readable only by its owner"


def fix(app: App, *, online: bool = False) -> Report:
    """Check, put right what `correct` can, and check again: the new report, with what was done."""
    first = run(app, online=online)
    correct(app, first)
    done = {c.name: c.corrected for c in first.checks if c.corrected}
    report = run(app, online=online)
    for check in report.checks:
        if not check.corrected and check.name in done:
            check.corrected = done[check.name]
    return report


def run(app: App, *, online: bool = False) -> Report:
    report = Report()
    report.group = "Settings"
    check_settings(app, report)
    check_time_zone(app, report)
    report.group = "Database"
    conn = check_database(app, report)
    try:
        if conn is not None:
            check_integrity(app, conn, report)
        check_data_files(app, report)
        check_backups(app, report, conn)
        report.group = "Family"
        check_family(conn, report, telegram=bool(app.settings.telegram_bot_token))
        report.group = "Model"
        check_provider(app, report, online=online)
        check_spending(app, conn, report)
        check_added_companies(app, report, online=online)
        report.group = "Connections"
        check_channels(app, report, online=online)
        check_integrations(app, report)
        if online:
            check_links(report)
        report.group = "Web page"
        check_web(app, report, conn)
        report.group = "Running"
        check_service(report)
        check_jobs(app, conn, report)
        check_messages(app, conn, report)
        check_trouble(app, conn, report)
    finally:
        if conn is not None:
            conn.close()
    return report


def text(report: Report) -> list[str]:
    """The report as printed: a heading for each group (`▸ Name`), a line for each check, its fix
    under it, and the verdict last. scripts/lib/common.sh `show_doctor` reads exactly this."""
    lines: list[str] = []
    group = None
    for check in report.checks:
        if check.group and check.group != group:
            group = check.group
            lines.append(f"▸ {group}")
        lines.append(f"{MARKS[check.verdict]} {check.name}: {check.detail}")
        if check.corrected:
            lines.append(f"    fixed: {check.corrected}")
        elif check.fix and check.verdict in (FAIL, WARN, TODO):
            lines.append(f"    → {check.fix}")
    return [*lines, "", verdict(report)]


def as_new_install(report: Report) -> Report:
    """The same findings read as the end of an install: nobody on the list and no model key are the
    page's first setup steps, not faults.
    """
    for check in report.checks:
        if check.verdict == FAIL and check.name in NEW_INSTALL_STEPS:
            check.verdict = TODO
            check.fix = f"next, on the web page: {NEW_INSTALL_STEPS[check.name]}"
    return report


def verdict(report: Report) -> str:
    if not report.failures and any(check.verdict == TODO for check in report.checks):
        return "It is running. The rest is set up on the web page, which walks you through it."
    if report.failures:
        return f"{len(report.failures)} thing(s) must be fixed before this will work" + (
            f", and {len(report.warnings)} worth a look" if report.warnings else ""
        )
    if report.warnings:
        return (
            f"It will run. {len(report.warnings)} thing(s) are not set up yet, "
            "which is normal on a first install."
        )
    return "Everything is set up."
