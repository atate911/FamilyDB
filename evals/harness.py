"""Run one case through the real pipeline in a throwaway database, then grade what happened."""

from __future__ import annotations

import json
import re
import tempfile
import unicodedata
from collections.abc import Callable, Mapping
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tests.fakes import FakeCalendar, FakeForecast

from evals.household import FORECAST, NOW, TZ, Household, calendar_events, seed
from familydb import personas
from familydb.app import App
from familydb.channels.base import IncomingMessage
from familydb.clock import FixedClock
from familydb.config import Settings, apply_overrides
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
    cost: float = 0.0
    model_calls: int = 0
    input_tokens: int = 0  # every input token its calls sent, from the cache or not
    persona: str = ""  # the persona setting it ran under

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


# Who sends a case's messages unless it says otherwise: Sam, by his Telegram id (household.py).
SAM = "1001"
# The family's group chat on Telegram (a group's id is negative), where the turn says who else
# reads the reply.
GROUP = "-1001234567890"


@dataclass(frozen=True)
class Case:
    name: str
    says: tuple[str, ...]  # what the family sends, in order
    checks: tuple[Check, ...]
    why: str = ""
    sender: str = SAM  # who sends it, by Telegram id
    chat: str | None = None  # where, by chat id; None is the sender's own, a private chat
    # Settings of the case's own, laid over settings_for's.
    settings: Mapping[str, Any] = field(default_factory=dict)


# Every case is also held to these: the bot never names a number that does not exist, never
# writes something the message did not ask for (each case lists what it may write), and keeps it
# short and plain whoever she is: one emoji at most (the spec's own rule), no "as an AI" filler,
# and no more than two exclamation marks.
MAX_REPLY = 900
MAX_EMOJI = 1
MAX_EXCLAMATIONS = 2
FILLER = re.compile(
    r"\bas\s+(?:an\s+ai|an\s+artificial\s+intelligence|a\s+language\s+model)\b", re.IGNORECASE
)
# The blocks emoji are drawn from: Miscellaneous Technical (the watch, the alarm clock),
# Miscellaneous Symbols and Dingbats (the sun, the heart, the tick), Miscellaneous Symbols and
# Arrows (the star), and U+1F000 to U+1FAFF (faces, food, animals, flags).
PICTOGRAPHIC = ((0x2300, 0x23FF), (0x2600, 0x27BF), (0x2B00, 0x2BFF), (0x1F000, 0x1FAFF))
JOINER = "\u200d"
# The regional indicators A to Z: a country's flag is two of them.
REGIONAL = ("\U0001f1e6", "\U0001f1ff")


def emoji_in(text: str) -> int:
    """How many emoji `text` holds, for the spec's "one emoji at most".

    An emoji here is a symbol (Unicode category So) in one of the blocks above, counted once
    however it is built. A sequence joined by U+200D (a family, a rainbow flag) is one. A skin
    tone or U+FE0F changes the one before it without adding another, since neither is a symbol.
    A pair of regional indicators is one flag. Symbols outside those blocks, such as the degree
    sign, the copyright sign and the arrows from U+2190, are not counted, so "21°C" has none.
    """
    count = 0
    joined = False  # the code point before was the joiner, so this one is part of the last emoji
    half_flag = False  # the emoji counted last is the first of a flag's two indicators
    for char in text:
        regional = REGIONAL[0] <= char <= REGIONAL[1]
        if _pictographic(char) and not joined and not (regional and half_flag):
            count += 1
            half_flag = regional
        else:
            half_flag = False
        joined = char == JOINER
    return count


def _pictographic(char: str) -> bool:
    point = ord(char)
    return unicodedata.category(char) == "So" and any(
        low <= point <= high for low, high in PICTOGRAPHIC
    )


def universal(run: Run) -> list[str]:
    wrong = []
    for number in {int(n) for n in re.findall(r"#(\d+)", run.reply)}:
        if number not in run.ids:
            wrong.append(f"names #{number}, which does not exist")
    if len(run.reply) > MAX_REPLY:
        wrong.append(f"reply is {len(run.reply)} characters, over {MAX_REPLY}")
    if not run.reply.strip():
        wrong.append("no reply")
    if (count := emoji_in(run.reply)) > MAX_EMOJI:
        wrong.append(f"reply has {count} emoji, over {MAX_EMOJI}")
    if filler := FILLER.search(run.reply):
        wrong.append(f"says {filler.group(0)!r}, which is filler")
    if (count := run.reply.count("!")) > MAX_EXCLAMATIONS:
        wrong.append(f"reply has {count} exclamation marks, over {MAX_EXCLAMATIONS}")
    return wrong


def under_persona(base: Settings, choice: str) -> tuple[str, Settings]:
    """What to call `choice` in the results, and `base` with it chosen.

    A persona's key, or none, is that persona as she ships: the family's rewrites of her, their
    notes and the name they gave her, if `base` carries any, are dropped. Anything else names a
    file, whose text is used as the default persona's rewrite, set as the Personality page sets
    `persona_text` and held to the same limit.
    """
    key = personas.key_for(choice)
    shipped = {"persona_text": {}, "persona_notes": "", "persona_name": ""}
    if key in (*personas.available(), personas.NONE):
        return key, apply_overrides(base, {"persona": key, **shipped})
    path = Path(choice)
    if not path.is_file():
        choices = ", ".join((*personas.available(), personas.NONE))
        raise ValueError(f"{choice!r} is not a persona ({choices}) or a file")
    text = path.read_text("utf-8")
    if not text.strip():
        raise ValueError(f"{choice} is empty, which would be the default persona as she ships")
    rewrite = {personas.DEFAULT: {"text": text}}
    return choice, apply_overrides(
        base, {"persona": personas.DEFAULT, **shipped, "persona_text": rewrite}
    )


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
        if case.settings:
            # Validated as the settings page would, so a misspelt setting fails the run loudly
            # rather than being carried along unread.
            settings = apply_overrides(settings, dict(case.settings))
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
            run = Run(house=seed(conn), persona=settings.persona)
            chat = case.chat or case.sender
            for number, text in enumerate(case.says, start=1):
                out = handle_incoming(
                    app,
                    IncomingMessage("telegram", f"{case.name}-{number}", chat, case.sender, text),
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
            # Input counts whether it was new, written to the cache or read from it. Each
            # provider module splits what a call was sent into these three columns, taking the
            # cached tokens out of the total where the vendor counts them inside it (OpenAI and
            # Gemini do), so the sum counts every token sent once. A NULL column counts as 0.
            spent = conn.execute(
                "SELECT coalesce(sum(cost_usd), 0), count(*), "
                "coalesce(sum(input_tokens), 0) + coalesce(sum(cache_creation_input_tokens), 0) "
                "+ coalesce(sum(cache_read_input_tokens), 0) FROM llm_calls"
            ).fetchone()
            run.cost, run.model_calls, run.input_tokens = (
                float(spent[0]),
                int(spent[1]),
                int(spent[2]),
            )
    return run


def grade(case: Case, run: Run) -> list[str]:
    """Everything wrong with a run: the case's own checks, then the universal ones."""
    wrong = [problem for check in case.checks if (problem := check(run))]
    return wrong + universal(run)
