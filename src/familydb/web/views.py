"""Turning stored records into what the templates show: pure functions, no database, no Flask.
The model's view of an idea is `agent/render.py`, which must not change for a page's sake."""

from __future__ import annotations

import calendar as months
import difflib
import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from itertools import islice, pairwise
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

from markupsafe import Markup, escape

from familydb import alerts, happening, presents, windows
from familydb.agenda import Entry
from familydb.agent.providers import catalog, companies, prices
from familydb.availability import happening_search_available, ticketmaster_available
from familydb.config import Settings
from familydb.dates import clock_time, hour_words
from familydb.integrations.geocode import estimate_travel
from familydb.memory import words
from familydb.store.ideas import Idea, ages_text
from familydb.store.members import Member
from familydb.store.memories import Memory
from familydb.store.messages import VOICE_PREFIX, WORDS_GONE, Message, as_said
from familydb.store.outcomes import Outcome
from familydb.store.places import Place
from familydb.store.plans import Plan
from familydb.store.tasks import Task
from familydb.suggest.shortlist import fmt_minutes
from familydb.tools.places import DAYS, checked_days_ago, format_ranges, is_stale, open_on
from familydb.tools.urls import clean_url

DAY_NAMES = {
    "mon": "Monday",
    "tue": "Tuesday",
    "wed": "Wednesday",
    "thu": "Thursday",
    "fri": "Friday",
    "sat": "Saturday",
    "sun": "Sunday",
}
SETTINGS = {"indoor": "indoor", "outdoor": "outdoor", "either": "indoor or outdoor"}
WEATHER = {"dry": "needs a dry day", "warm": "needs a warm day", "snow": "needs snow"}
DETAILS = {
    "pending": "details not looked up yet",
    "done": "details filled in",
    "failed": "details could not be found",
    "skipped": "not one place to look up",
}
# The product's name, not the page's title, which the family may change.
FOOTER = "FamilyDB © 2026 by Andrew Tate. Version v{version}. All rights reserved."
# The Status tile's light (status.light): a mark, never colour alone, and its words for a screen
# reader.
STATUS_LIGHTS = {
    "bad": ("■", "not answering"),
    "warn": ("▲", "needs a look"),
}
# The guide page for each settings page (`fields.SECTIONS`), by section name; the guide's own page
# names differ from two of them, and the change history has no page of its own.
GUIDE_FOR_SETTINGS = {
    "model": "controls/settings/ai-model",
    "security": "controls/settings/sign-in",
    "history": "controls/settings",
}
# Without the version, for a kid.
FOOTER_PLAIN = "FamilyDB © 2026 by Andrew Tate. All rights reserved."
# What each may do is decided in familydb/roles.py.
ROLE_WORDS = {
    "admin": "looks after it: the settings, setup, and who is on the family list. There is "
    "always at least one.",
    "parent": "uses all the rest: chat, ideas, plans and things to do, and answers the kids' "
    "wishes.",
    "kid": "is in the plans; with a password, reads the ideas and plans, talks to the bot and "
    "keeps her own wish lists, sees only her own things to do, within the number of messages a "
    "day set under Spending.",
}
GENDER_WORDS = {"female": "Female", "male": "Male"}
# By the permission needed; {name} is the persona in force.
REFUSALS = {
    "manage": (
        "For an admin",
        "Settings, setting up and the family list are changed by an admin. Ask one if "
        "something here needs to change.",
    ),
    "chat": ("Not yet", "Talking to {name} here is not part of your role yet. Ask an admin."),
    "browse": ("For a parent", "This page is for the grown-ups. Ask a parent if you need it."),
    "wish": (
        "Not yet",
        "Keeping a list is not part of your role. Ask an admin.",
    ),
    "decide": ("For a parent", "Answering the kids' lists is a parent's job."),
    "change": (
        "Not yet",
        "Changing ideas, plans and things to do is not part of your role yet. Ask an admin.",
    ),
    "own_tasks": (
        "Not yet",
        "Ticking off your things to do is not part of your role yet. Ask an admin.",
    ),
}


def admin_only(admins: list[str], *, grown_up: bool) -> tuple[str, str, str]:
    """What is said where somebody who is not an admin opens Settings, setup or the family list:
    the heading, the words, and who to ask. A kid is told there is nothing she need do."""
    asking = join_or(admins) if admins else "an admin"
    if admins:
        who = (
            admins[0] + " is the admin"
            if len(admins) == 1
            else presents.join_names(admins) + " are the admins"
        )
        line = f"{who} in this family."
    else:
        line = ""
    if grown_up:
        title, why = REFUSALS["manage"]
        return title, why, line
    return (
        "This part is for grown-ups",
        "Settings, setting up and the family list are changed by an admin. There\u2019s nothing "
        f"here you need to do: ask {asking} if something here needs to change.",
        line,
    )


def join_or(names: list[str]) -> str:
    """ "Sam", "Sam or Alex", "Sam, Alex or Jo"."""
    if len(names) < 2:
        return "".join(names)
    return f"{', '.join(names[:-1])} or {names[-1]}"


MAP_URL = "https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=17/{lat}/{lon}"
MAP_SEARCH = "https://www.openstreetmap.org/search?query={query}"


def duration_text(idea: Idea) -> str | None:
    if idea.duration_min and idea.duration_max and idea.duration_max != idea.duration_min:
        return f"{fmt_minutes(idea.duration_min)} to {fmt_minutes(idea.duration_max)}"
    span = idea.duration_min or idea.duration_max
    return f"about {fmt_minutes(span)}" if span else None


def cost_text(level: int | None) -> str | None:
    if level is None:
        return None
    return "free" if level == 0 else "$" * level


def participants_text(idea: Idea) -> str:
    return ", ".join(idea.participants) if idea.participants else "anyone"


def on_text(idea: Idea) -> str | None:
    """When a dated idea is on: "Wed 18 Nov 2026, 20:00", "Thu 1 Oct to Sat 31 Oct 2026",
    "from Thu 1 Oct 2026". None for an idea tied to no date."""
    first, last = idea.first_day, idea.last_day
    if first is None:
        return None
    time = (
        f", {clock_time(idea.happens_from)}"
        if idea.happens_from and "T" in idea.happens_from
        else ""
    )
    if last is None:
        return f"from {first:%a} {first.day} {first:%b %Y}{time}"
    if last == first:
        return f"{first:%a} {first.day} {first:%b %Y}{time}"
    year = "" if first.year == last.year else f" {first.year}"
    return f"{first:%a} {first.day} {first:%b}{year}{time} to {last:%a} {last.day} {last:%b %Y}"


def rating_text(idea: Idea) -> str | None:
    if not idea.times_done:
        return None
    times = "once" if idea.times_done == 1 else f"{idea.times_done} times"
    if idea.avg_rating is None:
        return f"done {times}"
    return f"done {times}, rated {idea.avg_rating:g}/10"


STATUS_WORDS = {"idea": "An idea", "planned": "Planned", "done": "Done", "dropped": "Dropped"}


def filter_words(kind: str, who: str, status: str) -> str:
    """What the ideas filter holds, in words, for the fold's summary: "Any kind, anyone, any but
    dropped"."""
    return ", ".join(
        [
            kind_text(kind).capitalize() if kind else "Any kind",
            who or "anyone",
            STATUS_WORDS.get(status, status).lower() if status else "any but dropped",
        ]
    )


def went_text(idea: Idea) -> str | None:
    """ "Went Thu 1 Oct" for an idea the family has done, by its last time."""
    if not idea.times_done or not idea.last_done_at:
        return None
    try:
        return f"Went {day_short(date.fromisoformat(idea.last_done_at[:10]))}"
    except ValueError:
        return None


def original_by(message: Any, people: Sequence[Any], tz: ZoneInfo) -> str:
    """Who said the thought an idea came from, and when: "Maya, Sun 20 Sep"."""
    name = next((p.display_name for p in people if p.id == message.member_id), None)
    day = day_short(date.fromisoformat(local_day(message.received_at, tz)))
    return f"{name}, {day}" if name else day


def kind_name(kind: str) -> str:
    """A kind as a label: "Day trip", and "Gift idea" for a present."""
    if kind.strip().lower() == "gift":
        return "Gift idea"
    return kind_text(kind).capitalize()


def kind_text(kind: str) -> str:
    """`day_trip` as "day trip"."""
    return kind.replace("_", " ")


def details_text(idea: Idea) -> str:
    return DETAILS.get(idea.enrichment, idea.enrichment)


def local_day(value: str, tz: ZoneInfo) -> str:
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value[:10]
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(tz).date().isoformat()


# The picture beside a kind of idea (the new sprite's names); anything else gets a spark.
KIND_GLYPHS = {
    "restaurant": "utensils",
    "activity": "sparkle",
    "outing": "sparkle",
    "day_trip": "mountain",
    "trip": "suitcase",
    "show": "ticket",
    "event": "star",
    "seasonal": "leaf",
}


def glyph_for(kind: str | None, *, gift: bool = False) -> str:
    """A gift is a gift whatever kind it is; otherwise the kind's own picture."""
    if gift:
        return "gift"
    return KIND_GLYPHS.get((kind or "").lower().replace(" ", "_"), "sparkle")


def idea_row(idea: Idea, tz: ZoneInfo, *, hidden: str | None = None) -> dict[str, Any]:
    """An idea as the pages draw it. `hidden` is who a present is kept from ("Maya and Theo"),
    said on its tag wherever it shows."""
    return {
        "hidden": hidden or None,
        "gift": hidden is not None,
        "id": idea.id,
        "title": idea.title,
        "added": local_day(idea.created_at, tz),
        "added_words": day_short(date.fromisoformat(local_day(idea.created_at, tz))),
        # Links come from chat and fetched pages: anything but an ordinary web address is dropped.
        "url": clean_url(idea.url),
        "kind": kind_text(idea.kind),
        "kind_name": kind_name(idea.kind),
        "status": idea.status,
        "where": idea.location_name,
        "on": on_text(idea),
        "who": participants_text(idea),
        "tags": idea.tags,
        "duration": duration_text(idea),
        "cost": cost_text(idea.cost_level),
        # "6+", "3-8", "up to 10": the page's label says "Ages".
        "ages": (ages_text(idea) or " ").split(" ", 1)[1] or None,
        "rating": rating_text(idea),
        "details": details_text(idea),
        "pending": idea.enrichment == "pending",
    }


# In the order the add form offers them.
MEMORY_KINDS = {
    "food": "food and drink",
    "activities": "things to do",
    "places": "places",
    "health": "health and needs",
    "routine": "routines",
    "other": "anything else",
}
SOURCE_CHARS = 140


def excerpt(text: str, fact: str, room: int = SOURCE_CHARS) -> str:
    """The part of a message a memory came from, around the first of its words found in it."""
    text = " ".join(text.split())
    if len(text) <= room:
        return text
    lowered = text.casefold()
    found = [lowered.find(word) for word in words(fact)]
    at = min((index for index in found if index >= 0), default=0)
    start = max(0, min(at - room // 3, len(text) - room))
    piece = text[start : start + room]
    if start > 0 and " " in piece:
        piece = "…" + piece.split(" ", 1)[1]
    if start + room < len(text) and " " in piece:
        piece = piece.rsplit(" ", 1)[0] + "…"
    return piece


def rule_text(rule: dict[str, Any] | None) -> str | None:
    """What suggestions are held to by a firm memory's rule (suggest/rules.py), in a few words:
    "held to: a 30 min drive at most, indoors"."""
    if not rule:
        return None
    said = []
    if (minutes := rule.get("max_travel_minutes")) is not None:
        said.append(f"a {minutes} min drive at most")
    if (level := rule.get("max_cost_level")) is not None:
        said.append("free things" if level == 0 else f"{cost_text(level)} at most")
    if setting := rule.get("setting"):
        said.append(f"{setting}s")
    if avoid := rule.get("avoid"):
        said.append("nothing " + " or ".join(avoid))
    return "held to: " + ", ".join(said) if said else None


def memory_row(memory: Memory, today: date, tz: ZoneInfo) -> dict[str, Any]:
    when = day_text(local_day(memory.created_at, tz))
    who = memory.said_by_name
    if memory.source_message_id is None:
        source = f"Added on this page{f' by {who}' if who else ''}, {when}"
        said = None
    else:
        text = as_said(memory.source_text or "")
        if text == WORDS_GONE:  # past the family's keeping (jobs/tidy.py)
            text = ""
        voiced = text.startswith(VOICE_PREFIX)
        source = f"{who or 'Somebody'}, {when}{', in a voice note' if voiced else ''}"
        said = excerpt(text.removeprefix(VOICE_PREFIX), memory.fact) or None
    return {
        "id": memory.id,
        "fact": memory.fact,
        "about": memory.about_name or "The family",
        "kind": MEMORY_KINDS.get(memory.category, memory.category),
        "firm": memory.firm,
        "held": rule_text(memory.rule),
        "guess": memory.inferred,
        "until": day_text(memory.until) if memory.until else None,
        "ended": bool(memory.until and memory.until < today.isoformat()),
        "source": source,
        "said": said,
        "gone": (
            f"forgotten {day_text(local_day(memory.forgotten_at, tz))}"
            + (f" by {memory.forgotten_by_name}" if memory.forgotten_by_name else "")
            if memory.forgotten_at
            else None
        ),
    }


def memory_page(
    memories: list[Memory], people: list[Member], today: date, tz: ZoneInfo
) -> dict[str, Any]:
    """What is remembered, grouped by whom it is about (family first), and what was forgotten."""
    kept = [m for m in memories if m.status == "active"]
    order = [None, *(person.id for person in people)]
    names = {person.id: person.display_name for person in people}
    groups = []
    for member_id in order:
        rows = [memory_row(m, today, tz) for m in kept if m.member_id == member_id]
        if rows:
            groups.append(
                {
                    "who": names.get(member_id, "The family"),
                    "family": member_id is None,
                    "rows": rows,
                }
            )
    strays = [m for m in kept if m.member_id is not None and m.member_id not in names]
    if strays:  # about somebody since off the family list
        groups.append(
            {"who": "Others", "family": False, "rows": [memory_row(m, today, tz) for m in strays]}
        )
    forgotten = [memory_row(m, today, tz) for m in memories if m.status == "forgotten"]
    return {"groups": groups, "forgotten": forgotten}


def is_late(task: Task, tz: ZoneInfo, today: date) -> bool:
    """Whether an open task's day has passed, in the family's own time."""
    if not task.due_at:
        return False
    moment = datetime.fromisoformat(task.due_at.replace("Z", "+00:00")).astimezone(tz)
    return moment.date() < today


def task_brief(task: Task, tz: ZoneInfo, today: date) -> dict[str, Any]:
    due = None
    late = is_late(task, tz, today)
    if task.due_at:
        moment = datetime.fromisoformat(task.due_at.replace("Z", "+00:00")).astimezone(tz)
        day = relative_text(moment.date().isoformat(), today)
        due = f"was due {day}" if late else f"due {day}, {clock_time(moment)}"
    return {
        "id": task.id,
        "title": task.title,
        "owner": task.owner,
        "due": due,
        "late": late,
        "window": task.preferred_window or None,
        "reminder": local_moment(task.reminder.remind_at, tz) if task.reminder else None,
        "revision": task.revision,
    }


# -- Home: the greeting, the one useful line under it, and the people and colours in its rows.

NUMBER_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")
EVERYONE = "Everyone"


_CLOCK = re.compile(r"\d{1,2}(?::\d{2})?\u00a0[ap]m")


def figs(text: Any) -> Markup:
    """Clock times in running text ("6:30 pm") in Fraunces' figures, so no zero is slashed (Atkinson
    Hyperlegible's is). Everything else in the text is escaped as it always is."""
    text = str(text)
    out, last = [], 0
    for found in _CLOCK.finditer(text):
        out += [escape(text[last : found.start()]), Markup('<span class="fig">'), escape(found[0])]
        out += [Markup("</span>")]
        last = found.end()
    out.append(escape(text[last:]))
    return Markup("").join(out)


# The one sentence about where reminders go, said the same on every page that says it.
# Where a reminder goes (routing.py), said the same on every page that sets one.
REMINDERS_SAID = (
    "A reminder goes to whoever it is for: their own Telegram chat once they have started one, "
    "otherwise the chat here."
)


def money_text(dollars: float) -> str:
    """ "$0.00", "$2.00"; under ten cents "4¢", which a dollar figure would round to nothing."""
    if 0 < dollars < 0.1:
        return f"{max(round(dollars * 100), 1)}¢"
    return f"${dollars:.2f}"


def count_words(count: int, one: str, many: str) -> str:
    """ "one to-do", "three to-dos": a small number as a word, a big one as digits."""
    number = NUMBER_WORDS[count] if count <= 10 else str(count)
    return f"{number} {one if count == 1 else many}"


def stuck_message_note(tries: int, given_up: bool) -> str:
    """What became of a message that did not go through: tried again, or given up on."""
    times = f"{tries} {'try' if tries == 1 else 'tries'}"
    if given_up:
        return f"given up on after {times}; the words above were not answered, so send them again"
    return f"{times}, will try again"


def greeting(hour: int, name: str | None) -> str:
    """ "Good morning, Sam"; with the family sharing one password there is no name to say."""
    part = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
    return f"Good {part}, {name}" if name else f"Good {part}"


def slot_map(people: Sequence[Member]) -> dict[str, int]:
    """Each person's colour by name, for the lists that carry only names (an idea's people, a
    to-do's owner, a chat line). Names are matched without regard to case."""
    return {person.display_name.casefold(): person.slot or 0 for person in people}


def slot_of(name: str | None, slots: dict[str, int]) -> int:
    """A person's colour (1 to 8), or 0 for Everyone, nobody, or somebody not on the list."""
    return slots.get((name or "").casefold(), 0)


def person_of(name: str | None, slots: dict[str, int]) -> dict[str, Any]:
    """A name and the colour and letter that go beside it; Everyone is the house, with no letter."""
    if not name or name == EVERYONE:
        return {"name": EVERYONE, "slot": 0, "initial": ""}
    return {"name": name, "slot": slot_of(name, slots), "initial": name[:1].upper()}


def people_for(idea: Idea | None, slots: dict[str, int]) -> list[dict[str, Any]]:
    """Who a plan is for: the people its idea names, or Everyone when it names nobody."""
    names = list(idea.participants) if idea else []
    return [person_of(name, slots) for name in names] or [person_of(None, slots)]


def names_text(people: Sequence[dict[str, Any]]) -> str:
    """ "Maya", "Maya and Theo", "Maya, Theo and Sam"."""
    names = [person["name"] for person in people]
    if len(names) <= 1:
        return "".join(names)
    return f"{', '.join(names[:-1])} and {names[-1]}"


def names_in(people: Sequence[dict[str, Any]], member: Member | None) -> bool:
    """Whether a plan's people include this person, or nobody in particular (so everyone)."""
    if member is None or all(person["slot"] == 0 and not person["initial"] for person in people):
        return True
    return any(person["name"].casefold() == member.display_name.casefold() for person in people)


def day_short(day: date) -> str:
    """ "Sun 27 Sep"."""
    return f"{day:%a} {day.day} {day:%b}"


def late_words(due: date, today: date, *, kid: bool = False) -> str | None:
    """ "6 days late" for a grown-up, "Was due Sun 27 Sep" for a kid; None while it is not late."""
    behind = (today - due).days
    if behind <= 0:
        return None
    if kid:
        return f"Was due {day_short(due)}"
    return f"{behind} day{'' if behind == 1 else 's'} late"


def todo_row(
    task: Task, tz: ZoneInfo, today: date, slots: dict[str, int], *, kid: bool = False
) -> dict[str, Any]:
    """One to-do as the new rows draw it: who, when in words, and how late."""
    due = None
    when = "No date"
    late = None
    if task.due_at:
        moment = datetime.fromisoformat(task.due_at.replace("Z", "+00:00")).astimezone(tz)
        due = moment.date()
        when = day_short(due)
        if (moment.hour, moment.minute) != (0, 0):
            when += f", {clock_time(moment)}"
        late = late_words(due, today, kid=kid)
        if kid and late is None and (ahead := relative_text(due.isoformat(), today)):
            when += f", {ahead}"
    elif task.preferred_window:
        when = task.preferred_window
    return {
        "id": task.id,
        "title": task.title,
        "revision": task.revision,
        "person": person_of(task.owner, slots),
        "when": when,
        "late": late,
        "reminder": local_moment(task.reminder.remind_at, tz) if task.reminder else None,
    }


def reminder_state(task: Task) -> str:
    """Where a task's reminder stands, for a grown-up."""
    if task.reminder is None:
        return ""
    if task.reminder.delivered_at:
        return "Delivered"
    return "Waiting for delivery" if task.reminder.message_id else "Scheduled"


def todo_page_row(
    task: Task,
    tz: ZoneInfo,
    today: date,
    slots: dict[str, int],
    *,
    kid: bool = False,
    nudging: bool = False,
    creator: str | None = None,
    me: str | None = None,
) -> dict[str, Any]:
    """A to-do for the To do page: the short row Home draws, and what the page adds under it. A
    kid's carries "Set by" when somebody else set it, and none of how reminders get there."""
    row = todo_row(task, tz, today, slots, kid=kid)
    nudge = nudge_words(task, tz, today) if nudging and not kid else None
    set_by = creator if creator and creator.casefold() != (me or "").casefold() else None
    return {
        **row,
        "status": task.status,
        "notes": task.notes,
        "window": task.preferred_window or None,
        "repeats": None if kid else repeat_text(task, tz),
        "nudge": nudge,
        "dated": bool(task.due_at),
        "set_by": f"Set by {set_by}" if set_by else None,
        # How a reminder is getting there is the workings: a kid sees only when it is.
        "reminder_state": None if kid or not task.reminder else reminder_state(task),
    }


def home_line(
    coming: Sequence[dict[str, Any]],
    late: int,
    *,
    plans_href: str,
    todo_href: str,
    kid: bool = False,
    others: str = "",
    yes: tuple[str, str] | None = None,
) -> list[dict[str, str | None]]:
    """The sentence under the greeting, as parts so the plan and the to-dos can be links: "Roller
    rink tomorrow, and three to-dos are late." `coming` are plan rows; `yes` is a kid's latest yes,
    (who said it, the wish), told in her sentence instead of what is late."""
    parts: list[dict[str, str | None]] = []

    def say(text: str, href: str | None = None) -> None:
        parts.append({"text": text, "href": href})

    plan = coming[0] if coming else None
    if plan:
        label = plan["title"] + (f" {plan['relative']}" if plan["relative"] else "")
        say(label, plans_href)
        if kid and others:
            say(f" with {others}")
    if kid:
        if yes:
            who, wish = yes
            say(", and " if plan else "")
            say(f"{who} said yes to ")
            say(wish, todo_href)
            say("!")
        elif plan:
            say(".")
        else:
            say("Nothing is planned yet.")
        return parts
    if late:
        text = count_words(late, "to-do", "to-dos")
        say(", and " if plan else "")
        if not plan:
            text = text[0].upper() + text[1:]
        say(text, todo_href)
        say(f" {'is' if late == 1 else 'are'} late.")
    elif plan:
        say(".")
    else:
        say("Nothing is planned yet, and nothing is late.")
    return parts


def home_summary(
    coming: Sequence[dict[str, Any]], open_count: int, late: int, *, todo_href: str
) -> list[dict[str, str | None]]:
    """A grown-up's quiet line under the day: how things stand, without repeating Next up. "5 to-dos
    open, 1 late · next plan in 2 days". What is late is a link to the to-dos (docs/STYLE.md,
    "The page header")."""
    parts: list[dict[str, str | None]] = []
    if open_count:
        noun = "to-do" if open_count == 1 else "to-dos"
        parts.append({"text": f"{open_count} {noun} open", "href": None})
        if late:
            parts.append({"text": ", ", "href": None})
            parts.append({"text": f"{late} late", "href": todo_href})
    else:
        parts.append({"text": "Nothing to do", "href": None})
    plan = coming[0] if coming else None
    if plan:
        nxt = f"next plan {plan['relative']}" if plan["relative"] else f"next plan {plan['when']}"
    else:
        nxt = "nothing planned yet"
    parts.append({"text": " · " + nxt, "href": None})
    return parts


# Ways to start, under the box on Home and in an empty chat; never asked of a model.
WEEKEND_QUESTION = "What should we do this weekend?"
TODAY_QUESTION = "What should we do today?"
STARTERS = ("Remind me to ", "We should try ")


def starters(today: date, *, kid: bool = False) -> list[dict[str, str]]:
    """The suggestions under the box: what each puts in it, and its label. None for a kid
    (docs/STYLE.md, "A kid's screen")."""
    if kid:
        return []
    question = TODAY_QUESTION if today.weekday() >= 5 else WEEKEND_QUESTION
    return [
        {"say": text, "label": text.rstrip() + ("…" if text.endswith(" ") else "")}
        for text in (question, *STARTERS)
    ]


# "every:unit" and its words.
REPEATS = (
    ("", "Doesn't repeat"),
    ("1:day", "Every day"),
    ("1:week", "Every week"),
    ("2:week", "Every 2 weeks"),
    ("1:month", "Every month"),
    ("3:month", "Every 3 months"),
    ("6:month", "Every 6 months"),
    ("1:year", "Every year"),
)


def repeat_text(task: Task, tz: ZoneInfo) -> str | None:
    """How often a task comes round, in words: "Every 2 weeks · last done Sun 20 Sep"."""
    if not task.repeats:
        return None
    unit = (
        task.repeat_unit if task.repeat_every == 1 else f"{task.repeat_every} {task.repeat_unit}s"
    )
    words = f"Every {unit}"
    if task.repeat_from == "done":
        words += ", counted from when it is done"
    if task.last_done_at:
        done = datetime.fromisoformat(task.last_done_at).astimezone(tz)
        words += f" · last done {done:%a %d %b}"
    return words


def list_title(name: str) -> str:
    """A list as the page names it: "Shopping list", "Hardware list"."""
    return f"{name[:1].upper()}{name[1:]} list"


# What a list's form says it did (edits.change_list), by what was asked.
LIST_SAID = {
    "add": "Added to the {list}: {items}.",
    "tick": "Got: {items}.",
    "untick": "Back on the {list}: {items}.",
    "remove": "Taken off the {list}: {items}.",
    "clear_ticked": "Cleared what was got from the {list}.",
}
LIST_ALREADY = "Already on it: {items}."


# Notifications on this device (/you, static/push.js): what the section says as it stands.
PUSH_WORDS = {
    "is_on": "On for this device: a notice says when {name} has written.",
    "is_off": "Off for this device.",
    "unable": "This browser cannot show notices from a page. On an iPhone or iPad, add this page "
    "to the Home Screen (Share, then Add to Home Screen) and open it from there; it needs iOS 16.4 "
    "or later.",
    "refused": "The browser was told not to show notices from this page; that is changed in its "
    "settings for the site.",
    "failed": "That did not work. Try again in a moment.",
}


# Where a change came from (tool_calls.source), as the history line under an idea or task says it.
CHANGED_FROM = {
    "chat": "through {name}",
    "tap": "with a button",
    "page": "on the page",
    "command": "with a command",
    "job": "by {name} on her own",
    "worker": "by a lookup",
    "cli": "on the server",
}


def changed_line(row: Any, tz: ZoneInfo, *, assistant: str) -> str | None:
    """The last change to an idea or task, for a grown-up: "Changed by Sam on the page, Tue 6 Oct
    09:10". None when nothing is known (made before changes were kept by whom)."""
    if row is None or row["source"] is None:
        return None
    verb = "Added" if str(row["tool_name"]).startswith(("add_", "create_")) else "Changed"
    who = f" by {row['who']}" if row["who"] else ""
    where = CHANGED_FROM.get(row["source"], "").format(name=assistant)
    when = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")).astimezone(tz)
    return f"{verb}{who} {where}, {when:%a} {when.day} {when:%b %H:%M}".replace("  ", " ")


def nudge_words(task: Task, tz: ZoneInfo, today: date) -> dict[str, str] | None:
    """For an open task kept for a window (jobs/nudges.py): `on`, "a free Saturday morning", and
    `last`; or `unread` when the window cannot be read (or "this weekend" is over). None for a
    task not waiting on one."""
    if task.status != "open" or task.repeats or not task.preferred_window:
        return None
    window = windows.read(task.preferred_window, until=task.until, today=today)
    if window is None:
        return {"unread": "yes"}
    said = {"on": window.words("free")}
    if task.nudged_at:
        last = datetime.fromisoformat(task.nudged_at).astimezone(tz)
        said["last"] = f"{last:%a %d %b}"
    return said


def task_row(task: Task, tz: ZoneInfo, today: date, *, nudging: bool = False) -> dict[str, Any]:
    """One task on the tasks page. `nudging` is the `task_nudges` setting."""
    choice = f"{task.repeat_every}:{task.repeat_unit}" if task.repeats else ""
    options = list(REPEATS)
    if choice and choice not in dict(REPEATS):  # set in chat to something the list lacks
        options.insert(1, (choice, f"Every {task.repeat_every} {task.repeat_unit}s (as it is)"))
    return {
        "task": task,
        "due_input": (
            datetime.fromisoformat(task.due_at).astimezone(tz).strftime("%Y-%m-%dT%H:%M")
            if task.due_at
            else ""
        ),
        "reminder_time": local_moment(task.reminder.remind_at, tz) if task.reminder else None,
        "repeats": repeat_text(task, tz),
        "repeat_choice": choice,
        "repeat_options": options,
        # So saving changes the repeat only when it changed.
        "repeat_was": f"{choice}:{task.repeat_from}" if choice else "",
        "nudge": nudge_words(task, tz, today) if nudging else None,
    }


def hours_rows(place: Place | None) -> list[dict[str, str]]:
    """Monday to Sunday, with closed and unknown told apart."""
    hours = (place.hours if place else None) or {}
    rows = []
    for key in DAYS:
        ranges = hours.get(key)
        if ranges is None:
            text = "not known"
        elif not ranges:
            text = "closed"
        else:
            text = format_ranges(ranges, spoken=True) or "closed"
        rows.append({"day": DAY_NAMES[key], "hours": text})
    return rows


def travel_text(place: Place | None) -> str | None:
    if place is None or place.travel_minutes is None:
        return None
    distance = f", {place.travel_km:g} km" if place.travel_km is not None else ""
    return f"about {place.travel_minutes} min away{distance} (estimate)"


def map_url(place: Place | None) -> str | None:
    if place is None:
        return None
    if place.lat is not None and place.lon is not None:
        return MAP_URL.format(lat=place.lat, lon=place.lon)
    if place.address:
        return MAP_SEARCH.format(query=quote(place.address))
    return None


def freshness_text(place: Place | None, now: datetime, stale_days: int) -> str | None:
    if place is None:
        return None
    days = checked_days_ago(place, now)
    if days is None:
        return "never checked"
    when = "checked today" if days == 0 else f"checked {days} day{'s' if days != 1 else ''} ago"
    return f"{when}, may be out of date" if is_stale(place, now, stale_days) else when


def phone_href(phone: str | None) -> str | None:
    """A tel: link for a number a place has, or None where it is not one a phone could dial."""
    digits = re.sub(r"[^\d+]", "", phone or "")
    return f"tel:{digits}" if len(digits.lstrip("+")) >= 7 else None


def hours_today(place: Place | None, today: date) -> str | None:
    """ "open today 11:30 am to 9 pm", "closed today", or None where the hours are not known."""
    state, ranges = open_on(place, today)
    words = TODAY_HOURS[state]
    return words.format(ranges=format_ranges(ranges, spoken=True) or "").strip() if words else None


def place_panel(
    place: Place | None, now: datetime, stale_days: int, today: date | None = None
) -> dict[str, Any] | None:
    if place is None:
        return None
    return {
        "today": hours_today(place, today) if today else None,
        "name": place.name,
        "summary": place.summary,
        "address": place.address,
        "phone": place.phone,
        "phone_href": phone_href(place.phone),
        "website": clean_url(place.website),
        "booking_url": clean_url(place.booking_url),
        "price_note": place.price_note,
        "travel": travel_text(place),
        "map_url": map_url(place),
        "hours": hours_rows(place),
        "has_hours": bool(place.hours),
        "sources": [url for url in (clean_url(s) for s in place.source_urls) if url],
        "freshness": freshness_text(place, now, stale_days),
        "stale": is_stale(place, now, stale_days),
    }


TODAY_HOURS = {"open": "open today {ranges}", "closed": "closed today", "unknown": None}


def restaurant_card(
    idea: Idea, place: Place | None, today: date, now: datetime, stale_days: int
) -> dict[str, Any]:
    return {
        "id": idea.id,
        "title": idea.title,
        "summary": (place.summary if place else None) or idea.description,
        "where": (place.address if place else None) or idea.location_name,
        "who": participants_text(idea),
        "cost": cost_text(idea.cost_level) or (place.price_note if place else None),
        "tags": idea.tags,
        "rating": rating_text(idea),
        "today": hours_today(place, today),
        "travel": travel_text(place),
        "website": clean_url(place.website if place else idea.url),
        "booking_url": clean_url(place.booking_url) if place else None,
        "map_url": map_url(place),
        "pending": idea.enrichment == "pending",
        "details": details_text(idea),
        "stale": is_stale(place, now, stale_days) if place else False,
    }


def day_text(value: str) -> str:
    """A stored date or datetime as 'Saturday 26 September', with the time if there is one."""
    stamp = value.strip()
    try:
        if len(stamp) <= 10:
            day = date.fromisoformat(stamp)
            return f"{day:%A} {day.day} {day:%B}"
        moment = datetime.fromisoformat(stamp)
    except ValueError:
        return stamp
    return f"{moment:%A} {moment.day} {moment:%B}, {clock_time(moment)}"


def date_chip(value: str) -> dict[str, Any] | None:
    """The day in three parts for the tear-off date: Sat, 26, Sep."""
    try:
        day = date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None
    return {"weekday": f"{day:%a}", "day": day.day, "month": f"{day:%b}"}


def relative_text(value: str, today: date) -> str | None:
    """'today', 'tomorrow', 'in 3 days', '2 weeks ago'. None when the date will not parse."""
    try:
        when = date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None
    days = (when - today).days
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    if days == -1:
        return "yesterday"
    ahead = days > 0
    count = abs(days)
    unit = f"{count} days" if count < 14 else f"{count // 7} weeks"
    return f"in {unit}" if ahead else f"{unit} ago"


def plan_row(plan: Plan, today: date) -> dict[str, Any]:
    return {
        "id": plan.id,
        "idea_id": plan.idea_id,
        "title": plan.title,
        "when": day_text(plan.start) if not plan.all_day else day_text(plan.start[:10]),
        "relative": relative_text(plan.start, today),
        "chip": date_chip(plan.start),
        "all_day": plan.all_day,
        # A datetime-local box wants "2026-09-26T18:30", with no offset (it shows nothing with one):
        # plans are stored in the family's own time, so that is the first sixteen characters.
        "start_value": plan.start[:16] if len(plan.start) > 10 else f"{plan.start[:10]}T09:00",
        "location": plan.location,
        "notes": plan.notes,
        "status": plan.status,
    }


def entry_row(
    entry: Entry,
    today: date,
    *,
    people: Sequence[dict[str, Any]] | None = None,
    away: Away | None = None,
) -> dict[str, Any]:
    days = entry.days()
    when = day_text(entry.start[:10] if entry.all_day else entry.start)
    if entry.all_day and len(days) > 1:
        first, last = days[0], days[-1]
        if (first.year, first.month) == (last.year, last.month):
            # "Saturday 3 to Sunday 4 October": the month once.
            when = f"{first:%A} {first.day} to {day_text(last.isoformat())}"
        else:
            when = f"{day_text(first.isoformat())} to {day_text(last.isoformat())}"
    return {
        "id": entry.plan_id,
        "idea_id": entry.idea_id,
        "title": entry.title,
        "when": when,
        "time": None if entry.all_day else clock_time(entry.start),
        "relative": "now" if days[0] < today <= days[-1] else relative_text(entry.start, today),
        "chip": date_chip(entry.start),
        "on_today": days[0] <= today <= days[-1],
        "all_day": entry.all_day,
        "location": entry.location,
        "notes": entry.notes,
        "status": entry.status,
        # Made elsewhere: shown, not movable here.
        "from_google": entry.plan_id is None,
        "start_value": entry.start[:16] if not entry.all_day else f"{entry.start[:10]}T09:00",
        # Who it is for (each with their colour; Everyone when nobody is named) and how far.
        "people": list(people) if people is not None else [person_of(None, {})],
        "who": names_text(people) if people is not None else EVERYONE,
        "away": away.words if away else None,
        "day": days[0].isoformat(),
        "end": days[-1].isoformat(),
        "short": day_short(days[0]),
    }


LANES = 3
MORE_LANE = LANES + 1


def _event_slot(row: dict[str, Any]) -> int:
    """An event wears one person's colour; with several people, or everyone, it is neutral."""
    people = row["people"]
    return people[0]["slot"] if len(people) == 1 else 0


def _spoken(day: date, rows: list[dict[str, Any]], unrated: set[int]) -> str:
    """What a day's cell says to a screen reader, as there is no room to write it: "Sun 4 Oct:
    Oaks Park roller rink, 13:00, for Maya and Theo"."""
    parts = []
    for row in rows:
        said = f"{row['title']}, {row['time']}, " if row["time"] else f"{row['title']}, "
        said += f"for {row['who'] if row['who'] != EVERYONE else 'everyone'}"
        if row["id"] in unrated:
            said += ". Not rated yet"
        parts.append(said)
    return f"{day_short(day)}: " + "; ".join(parts)


def month_calendar(
    rows: list[dict[str, Any]], first: date, today: date, unrated: set[int] | None = None
) -> list[dict[str, Any]]:
    """A month as whole weeks, Monday first. Each week carries its seven days and the events that
    touch it, each placed by the column it starts in, how many days it runs inside the week and
    which of three lanes it sits in (an event over three deep is counted on its days instead). A
    plan that crosses a week is cut: one bar to each week, `to` where it goes on and `before` where
    it came from. `rows` are plan rows (`entry_row`)."""
    unrated = unrated or set()
    grid = months.Calendar(firstweekday=0).monthdatescalendar(first.year, first.month)
    weeks = []
    for number, week in enumerate(grid):
        start, end = week[0], week[-1]
        spans = [
            (date.fromisoformat(row["day"]), date.fromisoformat(row["end"]), row) for row in rows
        ]
        inside = [one for one in spans if one[0] <= end and one[1] >= start]
        inside.sort(key=lambda one: (one[0], -(one[1] - one[0]).days, one[2]["title"]))
        taken: list[list[tuple[int, int]]] = [[] for _ in range(LANES)]
        events: list[dict[str, Any]] = []
        overflow = [0] * 7
        for began, ended, row in inside:
            left = (max(began, start) - start).days + 1
            right = (min(ended, end) - start).days + 1
            lane = next(
                (
                    n
                    for n, used in enumerate(taken, 1)
                    if all(right < a or left > b for a, b in used)
                ),
                None,
            )
            if lane is None:
                for column in range(left, right + 1):
                    overflow[column - 1] += 1
                continue
            taken[lane - 1].append((left, right))
            events.append(
                {
                    **row,
                    "column": left,
                    "lane": lane,
                    "length": right - left + 1,
                    "to": ended > end,
                    "before": began < start,
                    "slot": _event_slot(row),
                    "past": ended < today,
                    "unrated": row["id"] in unrated,
                }
            )
        days = []
        for index, day in enumerate(week):
            today_rows = [r for b, e, r in spans if b <= day <= e]
            days.append(
                {
                    "date": day,
                    "iso": day.isoformat(),
                    "number": day.day,
                    "month": f"{day:%b}" if day.day == 1 or (number == 0 and index == 0) else None,
                    "current": day.month == first.month,
                    "today": day == today,
                    "weekend": day.weekday() >= 5,
                    # One dot for each person a plan is for, so two people never read as the house.
                    "dots": [
                        {**person, "past": day < today}
                        for r in today_rows
                        for person in (r["people"] or [people_dot()])
                    ][:3],
                    "label": _spoken(day, today_rows, unrated) if today_rows else None,
                    # The first plan that day still to be rated, so the day links to its faces.
                    "rate": next((r["id"] for r in today_rows if r["id"] in unrated), None),
                }
            )
        weeks.append(
            {
                "days": days,
                "events": events,
                "more": [
                    {"column": column + 1, "count": count}
                    for column, count in enumerate(overflow)
                    if count
                ],
            }
        )
    return weeks


def people_dot() -> dict[str, Any]:
    """The marker for a plan that is for everyone: the house."""
    return {"name": EVERYONE, "slot": 0, "initial": ""}


# The ideas map: home at the middle, north up. A drive of this many minutes lies this share of the
# way out; the first half hour gets 70% of the radius, so the places a family really goes spread.
MAP_RINGS = (
    (15, "15 min", 0.40),
    (30, "30 min", 0.70),
    (60, "1 h", 0.80),
    (120, "2 h", 0.90),
    (180, "3 h", 1.0),
)
COMPASS = ("north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west")


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Degrees clockwise from north that the second point lies from the first."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlmb = math.radians(lon2 - lon1)
    east = math.sin(dlmb) * math.cos(phi2)
    north = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlmb)
    return math.degrees(math.atan2(east, north)) % 360


def drive_text(minutes: int) -> str:
    """A drive as people say it: "25 min", "1 h 35 min" (past an hour, to five minutes)."""
    if minutes < 60:
        return f"{minutes} min"
    hours, rest = divmod(5 * round(minutes / 5), 60)
    return f"{hours} h {rest} min" if rest else f"{hours} h"


@dataclass(frozen=True)
class Away:
    """Where a saved place lies from home: the estimated drive and which way."""

    minutes: int
    degrees: float

    @property
    def near(self) -> bool:
        return self.minutes < 5

    @property
    def text(self) -> str:
        """For a card: "about 25 min north-east of home (estimate)"."""
        if self.near:
            return "under 5 min from home (estimate)"
        way = COMPASS[round(self.degrees / 45) % 8]
        return f"about {drive_text(self.minutes)} {way} of home (estimate)"

    @property
    def words(self) -> str:
        """For a plan or an idea in a list: "27 min drive, south"."""
        if self.near:
            return "under 5 min from home"
        return f"{drive_text(self.minutes)} drive, {COMPASS[round(self.degrees / 45) % 8]}"


def away_from_home(place: Place | None, settings: Settings) -> Away | None:
    """How far and which way a place is from home; None unless both are on the map."""
    if place is None or place.lat is None or place.lon is None:
        return None
    if settings.home_lat is None or settings.home_lon is None:
        return None
    estimate = estimate_travel(settings, place.lat, place.lon)
    if estimate is None:
        return None
    return Away(estimate[0], bearing(settings.home_lat, settings.home_lon, place.lat, place.lon))


def map_share(minutes: float) -> float:
    """How far from home, as a share of the map's radius, a drive of this many minutes shows."""
    stops = [(0.0, 0.0)] + [(float(m), share) for m, _, share in MAP_RINGS]
    for (near_min, near), (far_min, far) in pairwise(stops):
        if minutes <= far_min:
            return near + (far - near) * (max(minutes, 0) - near_min) / (far_min - near_min)
    return 1.0


# The two drawings of the map: a wide one for the desktop (names 15 px, drawn at 1:1) and a narrow
# one for the phone (names 14 px). (width, height, centre x, centre y, radius, name size, gap).
MAP_SIZES = {
    "wide": (860, 440, 430, 220, 200.0, 15, 12),
    "narrow": (360, 400, 180, 196, 160.0, 14, 10),
}
# The words that say what an idea is, not where: left off a short name ("Silver Falls hike").
KIND_WORDS = frozenset(
    {"day", "trip", "hike", "weekend", "night", "roller", "rink", "walk", "visit"}
)
NAME_JOINS = (" at ", " in ", " for ", " with ", " to ", " on ")


def short_name(title: str) -> str:
    """What names an idea's dot on the map: "Pumpkin patch at Bi-Mart farm" is "Pumpkin patch",
    "Oaks Park roller rink" is "Oaks Park". The card beside it has the whole title."""
    text = " ".join(title.split())
    lowered = text.lower()
    for join in NAME_JOINS:
        at = lowered.find(join)
        if at > 0:
            head = text[:at]
            if len(head.split()) >= 2 or len(head) >= 8:
                text = head
            break
    words = text.split()[:3]
    while len(words) > 1 and words[-1].lower() in KIND_WORDS:
        words.pop()
    return " ".join(words)


Box = tuple[float, float, float, float]


def _meets(one: Box, other: Box) -> bool:
    return one[0] < other[2] and other[0] < one[2] and one[1] < other[3] and other[1] < one[3]


def _label(
    x: float, y: float, name: str, size: str, taken: list[Box]
) -> tuple[float, float, str, Box]:
    """Where a dot's name goes: beside it on the side with room, above or below at the very edge
    where it would meet the compass letters, and anywhere else that clears the other dots and
    names (`taken`, which the caller adds this one to). Returns its x, y, anchor and box."""
    width, _, cx, cy, radius, text_size, gap = MAP_SIZES[size]
    room = len(name) * text_size * 0.52
    left = x < cx
    beside_left = (x - gap, y + 5, "end")
    beside_right = (x + gap, y + 5, "start")
    candidates = [beside_left, beside_right] if left else [beside_right, beside_left]
    above = [(x - 8, y - 18, "end"), (x + 8, y - 18, "start")]
    below = [(x + 8, y + 22, "start"), (x - 8, y + 22, "end")]
    if abs(x - cx) > radius - 40 and abs(y - cy) < 16:
        # Out at the end of the west-east axis, where the compass letter is: above, or below.
        candidates = above[:1] + below[:1] if left else above[1:] + below[1:]
        if left and x - gap - room < 8:
            candidates = [(x - 12, y + 22, "start")]
        elif not left and x + gap + room > width - 8:
            candidates = [(x + 12, y + 22, "end")]
    else:
        candidates += above + below

    def box(spot: tuple[float, float, float | str]) -> Box:
        lx, ly, anchor = spot[0], spot[1], spot[2]
        left_edge = lx - room if anchor == "end" else lx
        return (left_edge, ly - text_size * 0.8, left_edge + room, ly + text_size * 0.3)

    def fits(spot: tuple[float, float, str]) -> bool:
        one = box(spot)
        return one[0] >= 4 and one[2] <= width - 4 and not any(_meets(one, t) for t in taken)

    chosen = next((c for c in candidates if fits(c)), None)
    if chosen is None:
        chosen = next(
            (c for c in candidates if box(c)[0] >= 4 and box(c)[2] <= width - 4), candidates[0]
        )
    one = box(chosen)
    taken.append(one)
    return round(chosen[0], 1), round(chosen[1], 1), chosen[2], one


def places_map(placed: list[tuple[Idea, Away]]) -> dict[str, Any] | None:
    """The map of how far each idea is from home, drawn at both sizes; None when there is nothing
    to show (no idea has a drive time, or every one is inside the first ring, where the cards say
    all there is to say)."""
    if not placed or max(away.minutes for _, away in placed) <= MAP_RINGS[0][0]:
        return None
    ordered = sorted(placed, key=lambda pair: (pair[1].degrees, pair[1].minutes, pair[0].id))
    plots = {}
    for size, (width, height, cx, cy, radius, _, _) in MAP_SIZES.items():
        rings = [
            {
                "r": round(radius * share, 1),
                "name": name,
                "x": cx + (6 if index % 2 == 0 else -6),
                "y": round(cy - radius * share + 15, 1),
                "anchor": "start" if index % 2 == 0 else "end",
            }
            for index, (_, name, share) in enumerate(MAP_RINGS)
        ]
        dots: list[dict[str, Any]] = []
        for idea, away in ordered:
            reach = radius * map_share(away.minutes)
            degrees = away.degrees
            for _ in range(6):  # ideas in the same direction are spread a few degrees apart
                angle = math.radians(degrees)
                x, y = cx + reach * math.sin(angle), cy - reach * math.cos(angle)
                if all(math.hypot(x - one["x"], y - one["y"]) >= 26 for one in dots):
                    break
                degrees += 5
            dots.append({"x": round(x, 1), "y": round(y, 1), "name": short_name(idea.title)})
        # What a name must stay clear of: home, its name, the compass letters and every dot.
        taken: list[Box] = [
            (cx - 8, cy - 8, cx + 8, cy + 8),
            (cx - 22, cy + 8, cx + 22, cy + 26),
            (cx - 12, cy - radius - 20, cx + 2, cy - radius - 2),
            (cx - 12, cy + radius + 2, cx + 2, cy + radius + 20),
            (cx - radius - 20, cy - 6, cx - radius - 2, cy + 10),
            (cx + radius + 2, cy - 6, cx + radius + 20, cy + 10),
        ]
        taken += [(d["x"] - 9, d["y"] - 9, d["x"] + 9, d["y"] + 9) for d in dots]
        for dot in dots:
            dot["label_x"], dot["label_y"], dot["anchor"], _ = _label(
                dot["x"], dot["y"], dot["name"], size, taken
            )
        plots[size] = {
            "width": width,
            "height": height,
            "cx": cx,
            "cy": cy,
            "radius": radius,
            "rings": rings,
            "axis": f"M{cx} {cy - radius:g}V{cy + radius:g}M{cx - radius:g} {cy}H{cx + radius:g}",
            "compass": [
                ("N", cx - 6, cy - radius - 5, "end"),
                ("S", cx - 6, cy + radius + 15, "end"),
                ("W", cx - radius - 8, cy + 5, "end"),
                ("E", cx + radius + 8, cy + 5, "start"),
            ],
            "dots": dots,
        }
    return {"wide": plots["wide"], "narrow": plots["narrow"], "count": len(ordered)}


AGENDA_NOTES = {
    "google": "From Google Calendar, including anything added there directly.",
    "saved": (
        "Google Calendar is not connected, so these are the plans kept here. They go on it once "
        "it is."
    ),
    "unavailable": (
        "Google Calendar did not answer, so these are the plans as FamilyDB last saw them. "
        "Times may have moved since."
    ),
}


def outcome_row(outcome: Outcome) -> dict[str, Any]:
    repeat = None
    if outcome.would_repeat is not None:
        repeat = "would go again" if outcome.would_repeat else "would not go again"
    return {
        "when": day_text(outcome.happened_on),
        "rating": f"{outcome.rating}/10" if outcome.rating is not None else None,
        "repeat": repeat,
        "notes": outcome.notes,
    }


FAILED_WORDS = "this one did not go through"


def chat_line(
    message: Message,
    names: dict[int, str],
    tz: ZoneInfo,
    *,
    did: list[str],
    waiting: bool,
    assistant: str,
    slots: dict[str, int] | None = None,
) -> dict[str, Any]:
    """One message in the chat. `did` is the turn's tool calls, which the log stores against the
    question but which belong under the answer. `waiting` (nothing has replied yet) is a fact about
    the thread, so the caller works it out. Every line she sends is `assistant`'s."""
    from_bot = message.direction == "out"
    trouble = None
    if not from_bot:
        if message.status == "failed":
            trouble = FAILED_WORDS
        elif waiting:
            trouble = "waiting for an answer"
    who = assistant if from_bot else names.get(message.member_id or -1, "someone")
    return {
        "id": message.id,
        "who": who,
        "from_bot": from_bot,
        "text": message.text,
        "when": local_moment(message.received_at, tz),
        # The family's own date, for the lines that say when the day changed.
        "day": local_day(message.received_at, tz),
        "clock": local_clock(message.received_at, tz),
        "slot": 0 if from_bot else slot_of(who, slots or {}),
        "initial": "" if from_bot else who[:1].upper(),
        "trouble": trouble,
        "failed": trouble == FAILED_WORDS,
        "did": did if from_bot else [],
    }


def handed_line(
    who: str, text: str, now: datetime, tz: ZoneInfo, slots: dict[str, int] | None = None
) -> dict[str, Any]:
    """A message just sent that the log does not hold yet, drawn as it will be."""
    stamp = now.astimezone(UTC).isoformat()
    return {
        "id": None,
        "who": who,
        "from_bot": False,
        "text": text,
        "when": local_moment(stamp, tz),
        "day": local_day(stamp, tz),
        "clock": local_clock(stamp, tz),
        "slot": slot_of(who, slots or {}),
        "initial": who[:1].upper(),
        "trouble": "waiting for an answer",
        "failed": False,
        "did": [],
    }


# What a turn did, in words, for each tool that changes something; the ones that only look
# something up are not said. A tool name is how it works, which is for the logs, not the page.
DID_WORDS = {
    "add_idea": "Saved an idea",
    "update_idea": "Changed an idea",
    "add_task": "Added a to-do",
    "update_task": "Changed a to-do",
    "create_event": "Added a plan",
    "update_event": "Changed a plan",
    "delete_event": "Canceled a plan",
    "remember": "Remembered something",
    "record_outcome": "Recorded how it went",
    "look_up_now": "Asked for a lookup",
    "add_wish": "Added a wish",
    "update_wish": "Changed a wish",
    "turn_away": "Turned down a request",
}


def tools_used(actions: Any) -> list[str]:
    """What a turn changed, in order, said once each, from the tools it ran (failures included)."""
    seen: list[str] = []
    for action in actions or []:
        name = action.get("tool") if isinstance(action, dict) else None
        words = DID_WORDS.get(name or "")
        if words and words not in seen:
            seen.append(words)
    return seen


# By alert kind (familydb/alerts.py).
ALERT_TITLES = {
    "credit": "{company} is out of credit",
    "key": "{company} refused its key",
    "limit": "The day's spending limit was used up",
    "calendar": "Google Calendar refused the bot's key, or it has none",
    "calendar_access": "Google Calendar is no longer showing the bot its calendar",
    "model": "A model in use is going, or has gone",
    "price": "The price of a model in use changed",
    "prices": "The price lists need a look",
    "new": "New models to choose from",
    "shift": "What the calls cost or do moved",
    "api": "A company stopped taking part of a request",
    "refused": "{company} is refusing requests",
    "advice": "A judgment on the models",
    "happening": "A place read for what is on near home could not be read",
    "calendars": "Event calendars found near home",
    "backup": "The backups need a look",
    "disk": "The server's disk is nearly full",
    "telegram": "Telegram refused the bot's token",
}
SAID_IN_DETAIL = frozenset(
    {
        "model",
        "price",
        "prices",
        "new",
        "shift",
        "api",
        "refused",
        "advice",
        "happening",
        "backup",
        "disk",
    }
)


def alert_row(alert: Any, tz: ZoneInfo, *, telling: bool, admins: int) -> dict[str, Any]:
    title = ALERT_TITLES.get(alert.kind, alert.kind).format(company=companies.named(alert.subject))
    seen = f"since {local_moment(alert.first_at, tz)}"
    if alert.times > 1:
        seen += f", {alert.times} times, last {local_moment(alert.last_at, tz)}"
    if alert.kind in alerts.NOT_ON_TELEGRAM:
        told = "shown here only, since Telegram cannot carry it"
    elif alert.told_at:
        told = f"admins told on Telegram {local_moment(alert.told_at, tz)}"
    elif not telling:
        told = "telling admins is switched off (Settings, Messages)"
    elif not admins:
        told = "no admin has a Telegram id to be told on"
    else:
        told = "admins are told on Telegram within a minute"
    detail = f"{seen}; {told}."
    if alert.kind in SAID_IN_DETAIL and alert.detail:
        detail = f"{alert.detail}. {detail[:1].upper()}{detail[1:]}"
    return {"label": title, "detail": detail, "on": False}


SOURCE_WORDS = {
    "litellm": "LiteLLM's price list",
    "openrouter": "OpenRouter's price list",
}
CHANGE_WORDS = {
    "new": "new, {after}",
    "gone": "no longer offered to the key",
    "back": "offered to the key again",
    "price": "{before} → {after} a million tokens",
    "retiring": "goes on {after}",
}


def source_row(source: Any, tz: ZoneInfo) -> dict[str, Any]:
    """Where the daily check reads, as a light: when, and how it went."""
    company = companies.named(source.source) if companies.get(source.source) else None
    label = SOURCE_WORDS.get(source.source) or f"{company or source.source}'s list for the key"
    when = local_moment(source.checked_at, tz)
    if source.ok:
        return {"label": label, "detail": f"Read {when}: {source.note}.", "on": True}
    running = f", {source.failures} checks running" if source.failures > 1 else ""
    detail = f"Could not be read {when}{running}: {source.note}."
    return {"label": label, "detail": detail, "on": False}


def find_row(find: Any, today: date) -> dict[str, Any]:
    """One thing near home as its page lists it."""
    first = date.fromisoformat(find.starts_at[:10])
    last = date.fromisoformat(find.ends_at[:10]) if find.ends_at else first
    if "T" in find.starts_at:
        when = find.starts_at[11:16]
    elif last > first:
        when = f"until {last:%a} {last.day} {last:%b}" if first <= today else "all day"
    else:
        when = "all day"
    who = (
        happening.host(find.url)
        if find.kind == happening.WEB and find.url
        else happening.source_name(find.source)
    )
    summary = find.summary or ""
    return {
        "when": when,
        "title": find.title,
        "url": find.url if find.url and find.url.startswith(("https://", "http://")) else None,
        "where": find.venue or find.address,
        "price": find.price_note,
        "summary": summary if len(summary) <= 160 else summary[:159].rstrip() + "…",
        "who": who,
    }


def happening_days(found: Sequence[Any], today: date) -> list[dict[str, Any]]:
    """What is on near home, by the day it starts, soonest first; what began before today and is
    still on goes under today."""
    days: dict[date, list[dict[str, Any]]] = {}
    for find in found:
        day = max(date.fromisoformat(find.starts_at[:10]), today)
        days.setdefault(day, []).append(find_row(find, today))
    return [
        {
            "label": "Today" if day == today else f"{day:%A} {day.day} {day:%B}",
            "today": day == today,
            "rows": sorted(rows, key=lambda row: (row["when"][0].isdigit(), row["when"])),
        }
        for day, rows in sorted(days.items())
    ]


def find_source_row(source: Any, tz: ZoneInfo) -> dict[str, Any]:
    """A place read for what is on near home, as a light: when, and how it went."""
    label = happening.source_name(source.source)
    if happening.source_kind(source.source) == happening.FEED:
        label = f"Calendar at {label}"
    label = label[0].upper() + label[1:]
    when = local_moment(source.checked_at, tz)
    if source.ok:
        return {"label": label, "detail": f"Read {when}: {source.note}.", "on": True}
    running = f", {source.failures} days running" if source.failures > 1 else ""
    detail = f"Could not be read {when}{running}: {source.note}."
    return {"label": label, "detail": detail, "on": False if source.failures > 1 else None}


JUDGEMENT_TITLES = {
    "replacement": "Which model should take {model}'s place",
    "refused": "What {company}'s refusal means",
    "lineup": "Which {company} models belong at each level",
    "price": "What {model} really costs",
}


def judgement_row(question: Any, tz: ZoneInfo, live: Any) -> dict[str, Any]:
    """One judgement question for the Status page: what, when, the answer, and the settings its
    buttons save: `waiting` while not in force, `undo` while what it changed still is."""
    facts = question.facts
    title = JUDGEMENT_TITLES.get(question.kind, question.kind).format(
        model=facts.get("model", ""),
        company=companies.named(facts.get("company", "")),
    )
    if question.answered_at is None:
        when = "asked with the evening's lookups" if not question.urgent else "being asked"
        return {"label": title, "detail": f"Filed {local_moment(question.asked_at, tz)}; {when}."}
    answer = question.answer or {}

    def in_force(values: dict[str, str]) -> bool:
        return all(str(getattr(live, key, "") or "") == value for key, value in values.items())

    waiting = answer.get("waiting") or {}
    undo = answer.get("undo") or {}
    put_in = {key: getattr(live, key, "") for key in undo}
    said = f"{question.outcome}." + (f" Why: {question.reason}" if question.reason else "")
    return {
        "label": title,
        "detail": f"{local_moment(question.answered_at, tz)}: {said}",
        "on": True,
        "waiting": waiting if waiting and not in_force(waiting) else {},
        # Put back only while what it put in is still what is in force.
        "undo": undo if undo and all(put_in.values()) and in_force(put_in) else {},
    }


def model_change_row(change: Any, tz: ZoneInfo) -> dict[str, str]:
    what = CHANGE_WORDS.get(change.what, change.what)
    return {
        "when": local_moment(change.at, tz),
        "company": companies.named(change.provider),
        "model": change.model,
        "what": what.format(before=change.before or "?", after=change.after or "?"),
    }


# Each kind of message she sends unasked, for the Messages page: the group where it is switched
# (none for reminders, which somebody asked for), its cost, its lines (voice.EVENTS or "digest").
AUTOMATIC = (
    ("weekend", "weekend", "Weekend ideas", "one model call a week", ("digest",)),
    ("reminders", "", "Reminders", "free", ("reminder", "reminder_late")),
    ("follow_ups", "others", "How did it go?", "free", ("follow_up",)),
    (
        "checks",
        "others",
        "Tomorrow's plans, checked",
        "free",
        ("plan_rain", "plan_rain_today", "plan_closed", "plan_closed_today", "plan_backup"),
    ),
    ("nudges", "others", "A task brought up", "free", ("nudge",)),
    # The morning message is one message; each part is counted as its own (store/mornings.py).
    ("morning_agenda", "morning", "The day ahead, each morning", "free", ("morning:agenda",)),
    ("chase_missed", "morning", "A reminder nobody acted on", "free", ("morning:chase",)),
    ("deadline_heads_up", "morning", "What is due tomorrow", "free", ("morning:deadlines",)),
    ("forgotten_roundup", "morning", "What has waited a week", "free", ("morning:roundup",)),
    (
        "lookups",
        "others",
        "What a lookup found",
        "free to send; each lookup is a small model call",
        ("lookup_done", "lookups_done"),
    ),
    (
        "alerts",
        "admins",
        "What needs fixing, to admins",
        "free",
        tuple(f"alert_{kind}" for kind in alerts.KINDS),
    ),
    ("kids_asks", "", "A kid's ask, to the parents", "free", ("kid_flagged", "kid_asks_parent")),
    ("kids_answers", "", "A parent's answer, to a kid", "free", ("wish_granted", "wish_declined")),
)
AUTOMATIC_BY_EVENT = {event: title for _, _, title, _, events in AUTOMATIC for event in events}
AUTOMATIC_BY_EVENT["morning"] = "The morning message"


def chat_words(conn_chat: str, member_name: str | None) -> str:
    if conn_chat == "web":
        return "the chat on this page"
    if conn_chat.startswith("-"):
        return "a Telegram group"
    return f"Telegram, {member_name}" if member_name else "Telegram"


# The history page cuts a tool's input or answer here; the log keeps it whole.
MAX_SHOWN = 4000
ASKED_WORDS = 90


def pretty_json(text: str | None) -> str:
    if not text:
        return ""
    try:
        shown = json.dumps(json.loads(text), indent=2, ensure_ascii=False, sort_keys=True)
    except ValueError:
        shown = text
    return shown if len(shown) <= MAX_SHOWN else shown[:MAX_SHOWN] + "\n…"


def asked_line(text: str, who: str) -> str:
    """A message as a line of the history: who, and the start of what they said."""
    words = " ".join(as_said(text).split())
    if len(words) > ASKED_WORDS:
        words = words[: ASKED_WORDS - 1].rstrip() + "…"
    return f"{who}: {words}"


def found_by_lookup(tool: dict[str, Any]) -> dict[str, Any] | None:
    """What a lookup saved (save_place) or why it gave up (skip_place)."""
    try:
        given = json.loads(tool.get("input") or "{}")
    except ValueError:
        return None
    if tool.get("tool_name") == "skip_place":
        return {"idea_id": given.get("idea_id"), "skipped": given.get("reason") or "no reason"}
    if tool.get("tool_name") != "save_place":
        return None
    hours = [
        f"{row.get('day')} {row.get('open')}-{row.get('close')}"
        for row in given.get("hours") or []
        if isinstance(row, dict)
    ]
    return {
        "idea_id": given.get("idea_id"),
        "name": given.get("name"),
        "summary": given.get("summary"),
        "address": given.get("address"),
        "website": clean_url(given.get("website")),
        "booking_url": clean_url(given.get("booking_url")),
        "phone": given.get("phone"),
        "hours": hours,
        "closed": given.get("closed_days") or [],
        "price_note": given.get("price_note"),
        "sources": [url for url in (clean_url(s) for s in given.get("source_urls") or []) if url],
        "saved": not tool.get("is_error"),
    }


def happening_state(settings: Any) -> str:
    """The settings list's line for things near home: what it reads."""
    feeds = len(happening.feed_urls(settings))
    parts = [f"{feeds} calendar{'' if feeds == 1 else 's'}"] if feeds else []
    if ticketmaster_available(settings):
        parts.append("Ticketmaster")
    if happening_search_available(settings):
        parts.append("a weekly search")
    if not parts:
        return "Nothing read yet: turn on web lookups, or add a calendar or a Ticketmaster key."
    listed = ", ".join(parts[:-1]) + " and " + parts[-1] if len(parts) > 1 else parts[0]
    return f"Reads {listed}."


def lookups_when(settings: Any) -> str:
    if settings.lookups_when == "asap":
        return "as soon as each is added"
    return f"together at {hour_words(settings.lookup_hour)} each evening"


def local_clock(value: str, tz: ZoneInfo) -> str:
    """A stored time as the family's clock reads it: "19:48"."""
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return clock_time(moment.astimezone(tz))


def day_heading(day: str, today: date) -> str:
    """The line that says the day changed in a chat: "Today", "Yesterday", "Sunday 27 September"."""
    try:
        when = date.fromisoformat(day)
    except ValueError:
        return day
    if when == today:
        return "Today"
    if when == today - timedelta(days=1):
        return "Yesterday"
    return f"{when:%A} {when.day} {when:%B}" + (f" {when.year}" if when.year != today.year else "")


def snippet(message: Message | None, assistant: str, names: dict[int, str], room: int = 60) -> str:
    """The last thing said in a conversation, short, for the list of conversations."""
    if message is None:
        return ""
    who = assistant if message.direction == "out" else names.get(message.member_id or -1, "")
    text = " ".join(message.text.split())
    text = text if len(text) <= room else text[: room - 1].rstrip() + "…"
    return f"{who}: {text}" if who else text


def local_moment(value: str, tz: ZoneInfo) -> str:
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    here = moment.astimezone(tz)
    return f"{here.day} {here:%b}, {clock_time(here)}"


def setting_text(value: str | None) -> str:
    """A stored JSON value; nothing stored reads as the default."""
    if value is None:
        return "—"
    try:
        loaded = json.loads(value)
    except ValueError:
        return value
    if loaded is None:
        return "default"
    if isinstance(loaded, bool):
        return "yes" if loaded else "no"
    return str(loaded)


def price_text(price: prices.Price | None) -> str | None:
    """US dollars per million tokens read and written, or per minute for a hearing model."""
    if price is None:
        return None
    if price.minute and not (price.input or price.output):
        return f"${price.minute:.3f} a minute"
    return f"${price.input:.2f} in, ${price.output:.2f} out"


def model_offer(provider: str, name: str) -> str:
    """A model name as a box offers it: lineup place, cost and the daily check's note."""
    known = catalog.known(provider, name)
    said = f"{known.label}, {known.level}" if known else ""
    cost = price_text(prices.price(provider, name))
    return " · ".join(part for part in (said, cost, prices.note(provider, name)) if part)


def level_choice(level: str, provider: str, name: str) -> str:
    known = catalog.known(provider, name)
    cost = price_text(prices.price(provider, name))
    said = f"{level}: {known.label if known else name}"
    return f"{said} ({cost})" if cost else said


def model_text(provider: str, name: str, level: str) -> str:
    """A model's name, with its level if not everyday and a note if it does not think first."""
    known = catalog.known(provider, name)
    notes = [] if level == catalog.EVERYDAY else [level]
    if known is not None and not known.thinks:
        notes.append("without thinking first")
    return f"{name} ({', '.join(notes)})" if notes else name


LONG_SETTINGS = frozenset(
    {"persona_text", "persona_notes", "about_family", "voice_lines", "companies"}
)
# Unchanged lines shown either side of a change. A character is paragraphs one to a line with a
# blank between, so one line of context would be only the blank.
CHANGE_CONTEXT = 2


def line_changes(before: str, now: str) -> list[dict[str, str]]:
    """What changed between two texts, as a unified diff. Each line keeps its +, - or space mark
    and a kind the stylesheet colours, so a change never rests on colour alone. Headers and line
    numbers are left out and its parts are parted by an ellipsis."""
    shown: list[dict[str, str]] = []
    diff = difflib.unified_diff(
        before.splitlines(), now.splitlines(), lineterm="", n=CHANGE_CONTEXT
    )
    for line in islice(diff, 2, None):  # past the two headers naming what was compared
        if line.startswith("@@"):
            if shown:
                shown.append({"kind": "same", "text": "…"})
            continue
        shown.append({"kind": {"+": "added", "-": "removed"}.get(line[:1], "same"), "text": line})
    return shown


def change_row(line: dict[str, Any], tz: ZoneInfo) -> dict[str, Any]:
    """One line of the settings history; a key's value is never in it."""
    return {
        "when": local_moment(line["changed_at"], tz),
        "key": line["key"],
        "secret": bool(line["secret"]),
        # Too long to show twice in a list.
        "long": line["key"] in LONG_SETTINGS,
        "old": setting_text(line["old_value"]),
        "new": setting_text(line["new_value"]),
        "who": line.get("changed_by_name"),
        "source": line["source"],
    }


# The time zone dropdown's region headings, in order; a zone named for no region (UTC) goes last.
ZONE_REGIONS = {
    "Africa": "Africa",
    "America": "Americas",
    "Antarctica": "Antarctica",
    "Asia": "Asia",
    "Atlantic": "Atlantic",
    "Australia": "Australia",
    "Europe": "Europe",
    "Indian": "Indian Ocean",
    "Pacific": "Pacific",
}
ZONE_OTHERS = "Other"


def utc_offset(zone: str, now: datetime) -> str:
    """How far a zone is from UTC now, daylight saving included: "UTC-07:00"."""
    offset = now.astimezone(ZoneInfo(zone)).utcoffset() or timedelta(0)
    total = round(offset.total_seconds() / 60)
    hours, minutes = divmod(abs(total), 60)
    return f"UTC{'-' if total < 0 else '+'}{hours:02d}:{minutes:02d}"


def zone_label(zone: str, now: datetime) -> str:
    """A zone as the dropdown offers it, place first so typing a city finds it, then its offset
    now: "Vancouver · UTC-07:00", "Buenos Aires, Argentina · UTC-03:00", "UTC"."""
    rest = zone.partition("/")[2]
    if not rest:
        return zone
    place = ", ".join(reversed(rest.replace("_", " ").split("/")))
    return f"{place} · {utc_offset(zone, now)}"


ZoneGroups = tuple[tuple[str, tuple[tuple[str, str], ...]], ...]


def zone_groups(zones: Sequence[str], now: datetime) -> ZoneGroups:
    """Time zones for a dropdown, under their regions, each as (zone, how it reads). Cached per
    hour: offsets move only as clocks change and there are nearly five hundred."""
    hour = now.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    return _zone_groups(tuple(zones), hour)


@lru_cache(maxsize=2)
def _zone_groups(zones: tuple[str, ...], hour: datetime) -> ZoneGroups:
    grouped: dict[str, list[tuple[str, str]]] = {}
    for zone in zones:
        region, _, rest = zone.partition("/")
        heading = ZONE_REGIONS.get(region, ZONE_OTHERS) if rest else ZONE_OTHERS
        grouped.setdefault(heading, []).append((zone, zone_label(zone, hour)))
    order = [*ZONE_REGIONS.values(), ZONE_OTHERS]
    return tuple(
        (heading, tuple(sorted(grouped[heading], key=lambda row: row[1].casefold())))
        for heading in order
        if heading in grouped
    )


def knock_row(knock: Any, tz: Any) -> dict[str, Any]:
    """Somebody who messaged the bot and is not on the family list."""
    words = (knock.name or "").split()
    name = " ".join(word for word in words if not word.startswith("@"))
    handle = next((word for word in words if word.startswith("@")), "")
    group = (knock.chat_id or "").startswith("-")
    return {
        "telegram_id": knock.channel_user_id,
        "name": name,
        "handle": handle,
        "when": local_moment(knock.last_at, tz),
        "times": knock.times,
        "where": "in a group" if group else "in a private chat",
    }


def footer(version: str, *, plain: bool = False) -> str:
    """The foot of every page; `plain` leaves the version out (roles.py `browse`)."""
    return FOOTER_PLAIN if plain else FOOTER.format(version=version)


# -- the kids' wish lists (docs/WISHES.md) --------------------------------------------------------

WISH_LISTS = (
    (None, "Every day", "What you'd like any time."),
    ("christmas", "Christmas", "For Christmas: no daily limit."),
    ("birthday", "Birthday", "For your birthday: no daily limit."),
)
CONCERN_WORDS = {
    "rule": "a house rule",
    "sibling": "about a sister or brother",
    "inappropriate": "not OK",
    "too_many": "too many in one day",
}
# As the kid it happened to reads it: what to do next, not a verdict.
KID_CONCERN_WORDS = {
    "rule": "a house rule: ask a parent",
    "sibling": "about a sister or brother",
    "inappropriate": "not one for your list",
    "too_many": "one for another day",
}
# By wish_service's result.
WISH_SAID = {
    "added": "On your list: {title}.",
    "duplicate": "Already on your list: {title}.",
    "locked": "Not yet: {title} was a not this time. You can ask again after {again}, or put it "
    "on your Christmas or birthday list.",
    "too_many": "That's a lot to ask for in one day. Let's keep some for tomorrow.",
    "list_full": "That list is full. Take something off it first.",
}
WISH_MOVED = "Moved."
WISH_WITHDRAWN = "Taken off your list."
WISH_ANSWERED = {
    "granted": "Yes to {title}. She has been told.",
    "declined": "Not this time: {title}. She has been told, kindly.",
}
ASKED_A_PARENT = "Sent to a parent."


def day_words(iso: str | None, today: date) -> str:
    """A day as the kids read it: "4 October", the year only when not this one."""
    if not iso:
        return ""
    day = date.fromisoformat(iso[:10])
    return f"{day.day} {day:%B}" + (f" {day.year}" if day.year != today.year else "")


def wish_row(wish: Any, today: date) -> dict[str, Any]:
    return {
        "id": wish.id,
        "title": wish.title,
        "notes": wish.notes,
        "rank": wish.rank,
        "occasion": wish.occasion,
        "status": wish.status,
        "note": wish.answer_note,
        "again": day_words(wish.locked_until, today) if wish.status == "declined" else "",
        "concern": CONCERN_WORDS.get(wish.concern or ""),
        "concern_kid": KID_CONCERN_WORDS.get(wish.concern or ""),
        "review": wish.parent_review,
        # Waits on a parent: she asked, or it was turned away as not OK (told them at once).
        "to_decide": wish.status == "turned_away"
        and (wish.parent_review == "asked" or wish.concern == "inappropriate"),
        "answered_by": wish.answered_by,
        "answered_at": wish.answered_at,
    }


def countdown(days: int | None) -> str | None:
    if days is None:
        return None
    if days == 0:
        return "Today!"
    return "Tomorrow!" if days == 1 else f"In {days} days"


def task_saved(result: dict[str, Any]) -> str:
    """The notice after a to-do is added on the page: what it is, in words (no number: that is
    the workings), and where its reminder will arrive (routing.for_task, as add_task worked it
    out), when it has one."""
    task = result["task"]
    said = f"Added to your to-dos: {task['title']}."
    if task.get("reminder") and result.get("reminder_destination"):
        said += f" Its reminder goes to {result['reminder_destination']}."
    return said
