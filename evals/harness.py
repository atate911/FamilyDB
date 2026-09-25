"""Run one case through the real pipeline in a throwaway database, then grade what happened."""

from __future__ import annotations

import json
import re
import tempfile
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tests.fakes import FakeCalendar, FakeForecast

from evals.household import FORECAST, NOW, TZ, Household, calendar_events, seed
from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.clock import FixedClock
from familydb.config import Settings
from familydb.pipeline import handle_incoming
from familydb.store import calls, db

WRITES = frozenset(
    {
        "add_idea",
        "update_idea",
        "record_outcome",
        "create_event",
        "update_event",
        "delete_event",
        "add_task",
        "update_task",
    }
)


@dataclass(frozen=True)
class Call:
    name: str
    input: dict[str, Any]
    ok: bool


@dataclass
class Run:
    """What one case did: the calls it made, what it said, what it left behind, what it cost."""

    house: Household
    replies: list[str] = field(default_factory=list)
    calls: list[Call] = field(default_factory=list)
    ids: set[int] = field(default_factory=set)  # every idea, plan and task number that exists
    counts: dict[str, int] = field(default_factory=dict)
    statuses: dict[int, str] = field(default_factory=dict)  # each idea's status at the end
    cost: float = 0.0
    model_calls: int = 0

    @property
    def reply(self) -> str:
        return self.replies[-1] if self.replies else ""

    def named(self, *names: str) -> list[Call]:
        return [c for c in self.calls if c.name in names and c.ok]

    @property
    def writes(self) -> list[Call]:
        return [c for c in self.calls if c.name in WRITES and c.ok]


# A check reads a run and returns what is wrong, or None when it holds.
Check = Callable[[Run], str | None]


@dataclass(frozen=True)
class Case:
    name: str
    says: tuple[str, ...]  # what the family sends, in order, as Sam in a private chat
    checks: tuple[Check, ...]
    why: str = ""


# Every case is also held to these: the bot never names a number that does not exist, never
# writes something the message did not ask for (each case lists what it may write), and keeps it
# short.
MAX_REPLY = 900


def universal(run: Run) -> list[str]:
    wrong = []
    for number in {int(n) for n in re.findall(r"#(\d+)", run.reply)}:
        if number not in run.ids:
            wrong.append(f"names #{number}, which does not exist")
    if len(run.reply) > MAX_REPLY:
        wrong.append(f"reply is {len(run.reply)} characters, over {MAX_REPLY}")
    if not run.reply.strip():
        wrong.append("no reply")
    return wrong


def settings_for(base: Settings, folder: Path, *, limit: float = 1.0) -> Settings:
    token = folder / "google_token.json"
    token.write_text("{}")
    return base.model_copy(
        update={
            "familydb_path": folder / "eval.sqlite3",
            "google_calendar_id": "eval@group.calendar.google.com",
            "google_token_path": token,
            "home_lat": 45.63,
            "home_lon": -122.67,
            "home_area": "Vancouver, WA",
            "family_tz": "America/Vancouver",
            # No web searches: they cost, and what the web says today is not what it says
            # tomorrow. Lookups and discovery are for their own cases, later.
            "web_tools_enabled": False,
            # The bot's own limit, checked before every call: what is left of the run's budget.
            "daily_spend_limit": limit,
            "digest_chat_id": None,
        }
    )


def run_case(case: Case, base: Settings, *, api: Any = None, limit: float = 1.0) -> Run:
    """One case from a fresh household, spending at most `limit` (and the one call that crosses
    it). `api` stands in for the vendor, for testing this file."""
    if limit <= 0:
        raise ValueError("a limit of 0 would turn the spending limit off")
    with tempfile.TemporaryDirectory(prefix="familydb-eval-") as tmp:
        settings = settings_for(base, Path(tmp), limit=limit)
        calendar = FakeCalendar(TZ)
        calendar_events(calendar)
        app = App(
            settings,
            FixedClock(NOW, TZ),
            calendar=calendar,
            weather=FakeForecast(list(FORECAST)),
        )
        with closing(app.connect()) as conn:
            db.migrate(conn)
            run = Run(house=seed(conn))
            for number, text in enumerate(case.says, start=1):
                out = handle_incoming(
                    app,
                    IncomingMessage("telegram", f"{case.name}-{number}", "1001", "1001", text),
                    api=api,
                    conn=conn,
                )
                run.replies.append(out.text if out else "")
                if out is not None and out.in_message_id is not None:
                    for row in calls.tool_calls_for_message(conn, out.in_message_id):
                        run.calls.append(
                            Call(
                                row["tool_name"],
                                json.loads(row["input"]) if row["input"] else {},
                                not row["is_error"],
                            )
                        )
            for table in ("ideas", "plans", "tasks"):
                run.counts[table] = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                run.ids |= {r[0] for r in conn.execute(f"SELECT id FROM {table}")}
            run.statuses = {r[0]: r[1] for r in conn.execute("SELECT id, status FROM ideas")}
            spent = conn.execute(
                "SELECT coalesce(sum(cost_usd), 0), count(*) FROM llm_calls"
            ).fetchone()
            run.cost, run.model_calls = float(spent[0]), int(spent[1])
    return run


def grade(case: Case, run: Run) -> list[str]:
    """Everything wrong with a run: the case's own checks, then the universal ones."""
    wrong = [problem for check in case.checks if (problem := check(run))]
    return wrong + universal(run)
