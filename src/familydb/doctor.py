"""One command that answers "is this install right, and if not what is wrong?"

Each check gives a verdict, what was found and, when wrong, the one thing to do. Ordered as an
install goes, so the first failure is usually the cause of the rest. Nothing reaches the network
unless `online` is set: a first install is often done before any key exists, and a check that
hangs on a firewall is worse than none.
"""

from __future__ import annotations

import shutil
import socket
import sqlite3
import stat
import subprocess
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from familydb import happening
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
from familydb.store import db, members

OK = "ok"
WARN = "warn"
FAIL = "fail"
SKIP = "skip"
TODO = "todo"

MARKS = {OK: "✓", WARN: "!", FAIL: "✗", SKIP: "·", TODO: "→"}
NEW_INSTALL_STEPS = {"family": "Add yourself", "model key": "Connect an AI model"}
FREE_MB_WANTED = 500


@dataclass
class Check:
    name: str
    verdict: str
    detail: str
    fix: str = ""
    corrected: str = ""

    def as_dict(self) -> dict[str, Any]:
        out = {"check": self.name, "verdict": self.verdict, "detail": self.detail}
        if self.fix:
            out["fix"] = self.fix
        if self.corrected:
            out["corrected"] = self.corrected
        return out


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)

    def add(self, name: str, verdict: str, detail: str, fix: str = "") -> Check:
        check = Check(name, verdict, detail, fix)
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
        report.add("database", FAIL, f"could not open {path}: {exc}", "Check the file's owner")
        return None

    current = db.schema_version(conn)
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
        elif check.name == "login key" and "mode" in check.detail:
            from familydb.web.keys import secret_path

            try:
                secret_path(app.settings).chmod(0o600)
            except OSError as exc:
                check.corrected = f"could not change the mode: {exc}"
            else:
                check.corrected = "made the login key readable only by its owner"


def run(app: App, *, online: bool = False) -> Report:
    report = Report()
    check_settings(app, report)
    conn = check_database(app, report)
    try:
        check_family(conn, report, telegram=bool(app.settings.telegram_bot_token))
        check_provider(app, report, online=online)
        check_added_companies(app, report, online=online)
        check_channels(app, report, online=online)
        check_integrations(app, report)
        check_web(app, report, conn)
        check_backups(app, report, conn)
        if online:
            check_links(report)
        check_service(report)
    finally:
        if conn is not None:
            conn.close()
    return report


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
