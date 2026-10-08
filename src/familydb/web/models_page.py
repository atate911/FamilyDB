"""The AI model page's numbers and the form that saves its choices (`/settings/model`).

Reading only: nothing here writes a setting (`web/settings.py` is the door). No page view is a model
call: every figure is the last 30 days of `llm_calls`, re-priced at each model the family could
choose (`prices.cost`, the sums the daily limit uses), so a change shows what it would have cost
before it is saved. A use with no calls yet is priced at a typical month's (`TYPICAL_MONTH`) and
says so.

The browser gets one JSON document (`Built.data`): for each use its options with a cost for each of
the 30 days, how its default follows the others, and the companies. `static/models.js` adds sums
and differences and does no pricing of its own, so the page and the daily limit never disagree.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any

from familydb.agent import gateway, providers, spending, uses
from familydb.agent.providers import catalog, companies, prices
from familydb.config import CompanyOptions, Settings
from familydb.dates import parse_datetime, utc_iso
from familydb.store import calls
from familydb.store import model_watch as model_store
from familydb.web import fields, views

WINDOW_DAYS = 30
OTHER = "__other"  # a model typed in, whatever the list offers
# How long a voice note is counted at: the recording is never kept, so its length is not known.
NOTE_SECONDS = 20
EFFORTS = (
    ("low", "Low"),
    ("medium", "Medium"),
    ("high", "High"),
    ("xhigh", "Extra high"),
    ("max", "Most"),
)
# The uses that think, and the setting each takes its thinking from when the page said nothing.
THINKS = {
    "chat": "effort",
    "digest": "effort",
    "choose": "effort",
    "lookup": "worker_effort",
    "onnear": "worker_effort",
}
# The plain settings that belong to one use: read as every other settings box is read.
EXTRAS = {"hear": ("voice_max_minutes",), "judge": ("judgement_acts",)}
# A cap drawn on another page (its box is there, and a setting is on one page only): this page
# shows it and says where.
CAP_ELSEWHERE = {"onnear": "happening"}
# The setting that is each use's monthly cap.
CAPS = {"choose": "choose_budget", "onnear": "happening_budget", "judge": "judgement_budget"}
# The most a company's own limit box takes, so a typo is not a fortune.
MOST_LIMIT = 100_000.0
TIERS = catalog.LEVELS

# A month of use for a family of four, per kind: calls, then each call's uncached and cached
# input tokens, output tokens and web searches. A use with no calls in the last 30 days is priced
# at this, so the comparison means something on a young install.
TYPICAL_MONTH: dict[str, tuple[int, int, int, int, float]] = {
    "chat": (891, 1800, 7200, 260, 0),
    "retry": (12, 1800, 7200, 260, 0),
    "digest": (12, 4000, 6000, 700, 0),
    "choose": (10, 9000, 0, 1500, 0),
    "enrich": (28, 3500, 0, 600, 2.5),
    "discover": (8, 3500, 0, 700, 3),
    "places": (2, 3500, 0, 700, 3),
    "price_check": (2, 2500, 0, 300, 2),
    "scout": (5, 4000, 0, 1200, 4),
    "find_feeds": (1, 3000, 0, 800, 5),
    "look": (9, 1600, 0, 120, 0),
    "judge": (1, 2500, 0, 400, 0),
    gateway.LISTEN: (22, 0, 0, 0, 0),
}

# Presets fill the table by strength: for each use `""` is its default, "off" switches it off, and
# a strength is that strength at the company the use is on.
PRESETS = {
    "thrifty": {"chat": "everyday", "choose": "off", "lookup": "everyday", "hear": "everyday"},
    "balanced": {},
    "quality": {"chat": "better"},
}

SEES = {
    "chat": "the family's words, what she remembers, ideas and plans",
    "digest": "the family's words, what she remembers, ideas and plans",
    "choose": "the family's words, memories, ratings, the weeks around, what was picked lately",
    "lookup": "the idea's title, the home area, the day's hours. Never a message",
    "onnear": "the home area and the next four weeks. Never a message",
    "hear": "the recording, which is not kept, and the family's names",
    "look": "the photo, which is not kept, and the family's names",
    "judge": "model names, prices and error messages. Never the family",
}
KNOW = {
    "chat": [
        "Cached input is read at a tenth of the input price, so for most messages the output "
        "price counts for most of the difference between models.",
        "A turn may move to the stand-in company only on its first call, before any tool has "
        "run, so a write is never repeated.",
    ],
    "digest": ["Once a week, so even the dearest model adds little to the month."],
    "choose": [
        "Follows the chat company unless chosen otherwise: its input is the family's own words, "
        "so choosing another company for it sends them there too, and the row says so.",
        "Off, over its monthly cap or failing, the engine's own order stands and nobody is told.",
    ],
    "lookup": [
        "The model only copies hours and addresses from a page it is shown, and code reads each "
        "find. A search costs about a cent whichever model runs it."
    ],
    "onnear": [
        "Has its own monthly cap, counted inside the daily limit. Reading the calendars and "
        "Ticketmaster is code and costs nothing."
    ],
    "hear": [
        "Claude takes no recordings, so only OpenAI and Google models can be picked.",
        "A note longer than the longest set under Voice notes is not heard at all, since every "
        "minute is paid for. Costs here count a note at about 20 seconds.",
    ],
    "look": ["Posters are the hardest thing it reads. A stronger model costs a little more."],
    "judge": [
        "It may put in a model costing about 10% more by itself; anything dearer waits for an "
        "admin.",
        "A refusal is asked at once; everything else together, after the evening's lookups.",
    ],
}
EVALS = {
    "chat": "The family's own requests, graded by code on what was called, saved and said. A few "
    "cents a run.",
    "digest": "Shares chat's cases; none is specific to the digest.",
    "choose": "The planning cases are graded on whether the reply leads with the pick.",
}
EVALS_NONE = "No eval cases for this yet."
UNITS = {"hear": ("note", "notes"), "look": ("photo", "photos")}
PURPOSES = {gateway.LISTEN: gateway.LISTEN_PURPOSE, gateway.LOOK: gateway.LOOK_PURPOSE}

NOT_A_CHOICE = "That is not a choice."
MOST_NAME = 120
NAME_SHAPE = "A model's name has no spaces and is not very long. Check what was pasted."
NEEDS_NAME = "Type the model's name, exactly as the company writes it."
CANNOT = "{company} cannot do that: {what}."
NO_SUCH_MODEL = "{company} says it has no model called {name}. Check the spelling."
BAD_LIMIT = "Type a number of dollars, or leave it empty for no limit."


@dataclass
class Tally:
    """What some calls used."""

    calls: int = 0
    fresh: int = 0
    cached: int = 0
    written: int = 0
    out: int = 0
    searches: float = 0

    def take(self, row: dict[str, Any]) -> None:
        self.calls += 1
        self.fresh += row["input_tokens"]
        self.cached += row["cache_read_input_tokens"]
        self.written += row["cache_creation_input_tokens"]
        self.out += row["output_tokens"]
        self.searches += row["web_searches"]

    def add(self, other: Tally) -> None:
        self.calls += other.calls
        self.fresh += other.fresh
        self.cached += other.cached
        self.written += other.written
        self.out += other.out
        self.searches += other.searches

    def usage(self) -> dict[str, float]:
        return {
            "input_tokens": self.fresh,
            "cache_read_input_tokens": self.cached,
            "cache_creation_input_tokens": self.written,
            "output_tokens": self.out,
            "web_searches": self.searches,
        }

    @property
    def sent(self) -> int:
        return self.fresh + self.cached + self.written


def summed(days: list[Tally]) -> Tally:
    total = Tally()
    for day in days:
        total.add(day)
    return total


def typical(kinds: tuple[str, ...]) -> Tally:
    total = Tally()
    for kind in kinds:
        n, fresh, cached, out, searches = TYPICAL_MONTH.get(kind, (0, 0, 0, 0, 0))
        total.calls += n
        total.fresh += n * fresh
        total.cached += n * cached
        total.out += n * out
        total.searches += n * searches
    return total


def window(settings: Settings, now: datetime) -> tuple[list[date], str]:
    """The last 30 days in the family's time, oldest first, and when the first began as the UTC
    timestamp calls are stored under."""
    today = now.astimezone(settings.tzinfo).date()
    days = [today - timedelta(WINDOW_DAYS - 1 - i) for i in range(WINDOW_DAYS)]
    return days, utc_iso(datetime.combine(days[0], time(), tzinfo=settings.tzinfo))


def tallies(
    conn: sqlite3.Connection, settings: Settings, now: datetime
) -> tuple[list[date], dict[str, list[Tally]]]:
    """Each use's calls, a Tally for each of the 30 days."""
    days, since = window(settings, now)
    place = {day: i for i, day in enumerate(days)}
    found = {use.key: [Tally() for _ in days] for use in uses.USES}
    for row in calls.usage_rows(conn, since=since):
        use = uses.BY_KIND.get(row["kind"])
        slot = place.get(parse_datetime(row["created_at"], settings.tzinfo).date())
        if use is not None and slot is not None:
            found[use.key][slot].take(row)
    return days, found


# -- models ---------------------------------------------------------------------------------------


def label_of(company: str, model: str) -> str:
    known = catalog.known(company, model)
    return known.label if known else model


def models_for(use: uses.Use, company: companies.Company, settings: Settings) -> list[str]:
    """The models this company can be chosen for this use with, cheapest first, the ones the
    family named for it always among them; none when it cannot do the use at all."""
    if use.needs == "hear":
        listed: list[str] = []
        if company.slug == "openai":
            listed = list(prices.hearing_suggestions("openai"))
        elif company.slug == "gemini":
            listed = list(prices.suggestions("gemini"))
        own = providers.build(company.slug, settings).listener()
        return listed if not own or own in listed else [*listed, own]
    if use.needs in ("search", "look") and not company.built_in:
        return []  # an added company has no hosted search, and nothing that reads a picture
    names = list(prices.suggestions(company.slug))
    names += [m.name for m in catalog.lineup(company.slug)]
    names += [
        company.chat_model(settings),
        company.worker_model(settings),
        company.level_model(settings, "better"),
        company.level_model(settings, "best"),
        *company.known_models(),
    ]
    seen: dict[str, None] = {}
    for name in names:
        if name:
            seen.setdefault(name, None)

    def dear(name: str) -> tuple[float, str]:
        listed = prices.price(company.slug, name)
        return (listed.output if listed else float("inf"), name)

    return sorted(seen, key=dear)


def lineup_of(use: uses.Use, company: companies.Company, settings: Settings) -> dict[str, str]:
    """The model this company answers with at each strength, for this use."""
    if use.needs == "hear":
        listed = models_for(use, company, settings)
        if not listed:
            return {}
        # What hears by default, then the dearest of those listed for the strengths above it.
        everyday = providers.build(company.slug, settings).listener() or listed[0]
        return {"everyday": everyday, "better": listed[-1], "best": listed[-1]}
    provider = providers.build(company.slug, settings)
    surface = "chat" if use.surface == "chat" else "worker"
    return {level: providers.model_at(provider, surface, level) for level in TIERS}


class Pricer:
    """What one use costs at any model: its last 30 days, or a typical month when it has none."""

    def __init__(self, use: uses.Use, days: list[Tally], cache_ttl: str = "1h") -> None:
        self.use = use
        self.days = days
        self.cache_ttl = cache_ttl  # what Claude charges to write its cache depends on it
        self.total = summed(days)
        self.real = self.total.calls > 0
        self.usual = None if self.real else typical(use.kinds or (gateway.LISTEN,))

    def _one(self, company: str, model: str, tally: Tally) -> float:
        if self.use.needs == "hear":
            return tally.calls * spending.estimate_hearing(company, model, NOTE_SECONDS)
        return prices.cost(company, model, tally.usage(), cache_ttl=self.cache_ttl)[0]

    def month(self, company: str, model: str) -> float:
        # Cost is a sum over the calls, so the month is the month's tally priced once.
        return self._one(company, model, self.usual if self.usual is not None else self.total)

    def daily(self, company: str, model: str) -> list[float]:
        if not self.real:
            return []  # nothing happened on any day; the page reads a missing list as zeros
        return [round(self._one(company, model, day), 5) for day in self.days]


# -- the page -------------------------------------------------------------------------------------


def money(v: float) -> str:
    return "<$0.01" if 0 < v < 0.005 else f"${v:,.2f}"


def calls_said(use: uses.Use, n: int) -> str:
    if n == 0:
        return "none in 30 days"
    one, many = UNITS.get(use.key, ("call", "calls"))
    return f"{n} {one if n == 1 else many}"


def _k(n: float) -> str:
    return f"{n / 1000:.0f}k" if n >= 10000 else f"{n / 1000:.1f}k" if n >= 1000 else f"{n:.0f}"


def _stored_choice(settings: Settings, key: str) -> str:
    """What is stored for a use, normalised; empty when nothing is."""
    choice = uses.parse(settings.model_choices.get(key))
    if choice.form == "model" and companies.get(choice.company, settings) is None:
        return ""  # a company taken away: the use is at its default, as `uses.resolve` reads it
    return str(choice)


def _defaults_by_company(
    settings: Settings, use: uses.Use, every: tuple[companies.Company, ...], default: str
) -> dict[str, str]:
    """For a use whose default follows another's company (choosing suggestions follows chat's), the
    default if that company were each of them, so the page can move it with the chat before
    anything is saved. Empty for a use that follows nobody's company."""
    if not use.anchor or default.startswith(("same:", "off")):
        return {}
    anchor = uses.BY_KEY[use.anchor]
    surface = "chat" if anchor.surface == "chat" else "worker"
    found = {}
    for company in every:
        model = providers.model_at(providers.build(company.slug, settings), surface, "everyday")
        pretend = settings.model_copy(
            update={
                "model_choices": {**settings.model_choices, anchor.key: f"{company.slug}:{model}"}
            }
        )
        found[company.slug] = uses.default_choice(pretend, use.key)
    return found


def _stats(use: uses.Use, days: list[Tally], figures: dict[str, dict[str, Any]]) -> list[list[str]]:
    total = summed(days)
    if not total.calls:
        return [["Calls", "none in the last 30 days"]]
    if use.needs == "hear":
        rows = [
            ["Notes", f"{total.calls}"],
            ["Audio", f"about {total.calls * NOTE_SECONDS / 60:.1f} minutes"],
        ]
    else:
        share = total.cached / total.sent if total.sent else 0
        said = f"{_k(total.sent / total.calls)} in"
        said += f" ({share:.0%} cached)" if share >= 0.01 else ""
        said += f" · {_k(total.out / total.calls)} out"
        said += f" · {total.searches:.0f} searches" if total.searches else ""
        rows = [["Calls", f"{total.calls}"], ["Tokens a call", said]]
    bad = sum(figures.get(kind, {}).get("bad", 0) for kind in use.kinds)
    rows.append(["Trouble", "none" if not bad else f"{bad} ended badly"])
    return rows


def _advice(use: uses.Use, ladder: list[float]) -> str:
    """One sentence on what choosing dearer costs for this use, from the numbers on the page."""
    if len(ladder) != 3 or (ladder[0] <= 0 and ladder[2] <= 0):
        return ""
    if use.key == "chat" and ladder[0] > 0:
        return (
            "Most messages are small chores: a plan, a reminder, a question. Better costs about "
            f"{ladder[1] / ladder[0]:.0f} times everyday and best about "
            f"{ladder[2] / ladder[0]:.0f} times. Worth trying if replies start to feel off."
        )
    return f"Everyday to best adds {money(ladder[2] - ladder[0])} a month at this use."


SHORT = {"chat": "chat", "lookup": "lookups"}


def short_of(key: str) -> str:
    """A use as a phrase inside a sentence: "same as chat"."""
    return SHORT.get(key) or uses.BY_KEY[key].label.lower()


def default_text(default: str) -> str:
    """A default choice in words: "GPT-6 Luna (everyday)", "same as chat", "off"."""
    choice = uses.parse(default)
    if choice.form == "same":
        return "same as " + short_of(choice.follows)
    if choice.form == "off":
        return "off"
    if choice.form != "model":
        return "nothing"
    known = catalog.known(choice.company, choice.model)
    label = label_of(choice.company, choice.model)
    return f"{label} ({known.level})" if known and known.level != "" else label


def _company_row(
    company: companies.Company,
    settings: Settings,
    stored: dict[str, Any],
    spent: float,
) -> dict[str, Any]:
    keyed = providers.has_credentials(company.slug, settings)
    if not company.built_in:
        source = "saved here" if keyed else "not saved yet"
    elif company.key_setting in stored:
        source = "saved here"
    else:
        source = "from the server's .env file" if keyed else "not saved yet"
    return {
        "id": company.slug,
        "name": company.label,
        "named": company.named,
        "added": not company.built_in,
        "haskey": keyed,
        "keysource": source,
        "allowed": companies.allowed(company.slug, settings),
        "standin": companies.may_stand_in(company.slug, settings),
        "limit": companies.monthly_limit(company.slug, settings),
        "spent": round(spent, 4),
    }


def _extras(use: uses.Use, settings: Settings, stored: dict[str, Any]) -> list[dict[str, Any]]:
    """The few plain settings that belong to one use, drawn in its row beside the rest."""
    found = []
    for key in EXTRAS.get(use.key, ()):
        one = fields.BY_KEY[key]
        found.append(
            {
                "key": key,
                "label": one.label,
                "note": one.note,
                "value": "" if key not in stored else str(stored[key]),
                "default": fields.placeholder(one, getattr(settings, key)),
                "choices": [(choice, one.word(choice)) for choice in one.choices],
            }
        )
    return found


def _use_view(
    use: uses.Use,
    settings: Settings,
    conn: sqlite3.Connection,
    every: tuple[companies.Company, ...],
    days: list[Tally],
    figures: dict[str, dict[str, Any]],
    month_since: str,
    set_here: dict[str, Any],
) -> dict[str, Any]:
    pricer = Pricer(use, days, settings.anthropic_cache_ttl)
    stored = _stored_choice(settings, use.key)
    default = uses.default_choice(settings, use.key)
    resolved = uses.resolve(settings, use.key)
    opts: list[dict[str, Any]] = []
    lineup: dict[str, dict[str, str]] = {}
    vendors: list[str] = []
    for company in every:
        names = models_for(use, company, settings)
        if not names:
            continue
        vendors.append(company.slug)
        lineup[company.slug] = lineup_of(use, company, settings)
        for name in names:
            listed = prices.price(company.slug, name)
            known = catalog.known(company.slug, name)
            shown = listed or prices.UNLISTED
            opts.append(
                {
                    "c": company.slug,
                    "n": name,
                    "l": label_of(company.slug, name),
                    "t": known.level if known and use.needs != "hear" else "",
                    "tn": known.level if known else catalog.EVERYDAY,
                    "m": round(pricer.month(company.slug, name), 4),
                    "d": pricer.daily(company.slug, name),
                    "pr": [shown.input, shown.output, shown.cached],
                    "pm": round(spending.estimate_hearing(company.slug, name, 60), 4)
                    if use.needs == "hear"
                    else None,
                    "fixed": known is not None and not known.thinks,
                    "listed": listed is not None,
                    "note": prices.note(company.slug, name) or "",
                }
            )
    usual = pricer.usual or summed(days)
    unlisted = (
        usual.calls * spending.estimate_hearing("", "unlisted", NOTE_SECONDS)
        if use.needs == "hear"
        else prices.cost("", "unlisted", usual.usage())[0]
    )
    total = summed(days)
    cap = None
    if use.key in CAPS:
        cap = {
            "setting": CAPS[use.key],
            "value": getattr(settings, CAPS[use.key]),
            "used": round(calls.spent_on(conn, use.kinds, since=month_since), 4),
            "elsewhere": CAP_ELSEWHERE.get(use.key, ""),
        }
    effort = None
    if use.key in THINKS:
        effort = {
            "default": getattr(settings, THINKS[use.key]),
            "stored": settings.use_effort.get(use.key, ""),
        }
    on = resolved.company if not resolved.off else None
    now_month = (
        round(pricer.month(on, resolved.model), 4) if on is not None and resolved.model else 0.0
    )
    ladder = [
        pricer.month(resolved.company, m.name)
        for m in catalog.lineup(resolved.company or "")
        if use.needs not in ("hear",)
    ]
    return {
        "id": use.key,
        "name": use.label,
        "short": short_of(use.key),
        "blurb": use.line,
        "group": use.group,
        "usage_label": calls_said(use, total.calls),
        "hearing": use.needs == "hear",
        "search": use.needs == "search",
        "family": use.key in ("chat", "digest", "choose"),
        "stored": stored,
        "stored_listed": stored in ("", uses.OFF)
        or stored.startswith(uses.SAME + ":")
        or any(f"{o['c']}:{o['n']}" == stored for o in opts),
        "default": default,
        "default_text": default_text(default),
        "by_company": _defaults_by_company(settings, use, every, default),
        "deflevel": str(getattr(settings, use.level_setting)),
        "anchor": use.anchor,
        "hassame": bool(use.exact and use.anchor),
        "hasoff": bool(use.off),
        "offnote": use.off,
        "vendors": vendors,
        "lineup": lineup,
        "opts": opts,
        "unlisted": round(unlisted, 4),
        "typical": not pricer.real,
        "calls": [d.calls for d in days],
        "tin": [d.sent for d in days],
        "tcached": [d.cached for d in days],
        "tout": [d.out for d in days],
        "tsearch": [round(d.searches) for d in days],
        "effort": effort,
        "cap": cap,
        "now": {
            "company": resolved.company,
            "model": resolved.model,
            "off": resolved.off,
            "month": now_month,
            "followed": resolved.followed,
        },
        "extras": _extras(use, settings, set_here),
        "advice": _advice(use, ladder),
        "sees": SEES[use.key],
        "know": KNOW[use.key],
        "evals": EVALS.get(use.key, EVALS_NONE),
        "stats": _stats(use, days, figures),
        "kinds": [
            {
                "label": (PURPOSES.get(kind) or gateway.KINDS[kind].purpose).capitalize(),
                "n": figures.get(kind, {}).get("calls", 0),
            }
            for kind in use.kinds
        ],
    }


# What the browser needs of a use; the rest is for the template.
DATA_KEYS = (
    "id",
    "name",
    "short",
    "stored",
    "default",
    "by_company",
    "deflevel",
    "anchor",
    "hassame",
    "hasoff",
    "offnote",
    "vendors",
    "lineup",
    "opts",
    "unlisted",
    "typical",
    "calls",
    "tin",
    "tcached",
    "tout",
    "tsearch",
    "hearing",
    "search",
    "family",
    "cap",
)


@dataclass
class Built:
    data: dict[str, Any]
    uses: list[dict[str, Any]]
    groups: list[tuple[str, list[dict[str, Any]]]]
    companies: list[dict[str, Any]]
    head: dict[str, Any]
    lineup: list[dict[str, Any]]
    checked: dict[str, Any]
    names: dict[str, str]
    efforts: tuple[tuple[str, str], ...] = EFFORTS
    presets: dict[str, dict[str, str]] = field(default_factory=lambda: PRESETS)


def lineup_rows(settings: Settings, base: Settings, stored: dict[str, Any]) -> list[dict[str, Any]]:
    """The everyday, better and best models of each company that has a module of its own, as
    boxes: what is set, what it falls back to, what is offered."""
    rows = []
    for company in companies.BUILT_IN:
        offered = [
            (name, label_of(company.slug, name)) for name in prices.suggestions(company.slug)
        ]
        cells = []
        for head, setting, level in (
            ("Everyday", company.chat_setting, "everyday"),
            ("Everyday, lookups", company.worker_setting, ""),
            ("Better", company.better_setting, "better"),
            ("Best", company.best_setting, "best"),
        ):
            built = getattr(base, setting, "") or (
                catalog.at(company.slug, level).name
                if level and catalog.at(company.slug, level)
                else ""
            )
            current = stored.get(setting) or ""
            cells.append(
                {
                    "setting": setting,
                    "head": head,
                    "value": current,
                    "default": built,
                    "default_label": label_of(company.slug, built) if built else "this version's",
                    "offers": offered
                    if not current or current in dict(offered)
                    else [*offered, (current, current)],
                }
            )
        rows.append({"id": company.slug, "name": company.label, "cells": cells})
    return rows


def _picked(
    typed: Any,
    views_: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    lineup: list[dict[str, Any]],
    checked: dict[str, Any],
) -> None:
    """What each box shows: what was saved, or, where the page is drawn again with a complaint,
    what was typed, so nothing else the person had changed is lost."""
    asked = typed if typed else {}
    for one in views_:
        key = one["id"]
        one["picked"] = asked.get(f"choice_{key}", one["stored"])
        one["other"] = asked.get(f"other_{key}", "")
        picked = uses.parse(one["picked"])
        one["picked_label"] = (
            label_of(picked.company, picked.model) if picked.form == "model" else one["picked"]
        )
        one["picked_listed"] = (
            one["picked"] in ("", uses.OFF)
            or one["picked"].startswith(uses.SAME + ":")
            or one["picked"].endswith(":" + OTHER)
            or any(f"{o['c']}:{o['n']}" == one["picked"] for o in one["opts"])
        )
        if one["effort"]:
            one["effort"]["picked"] = asked.get(f"effort_{key}", one["effort"]["stored"])
        if one["cap"]:
            one["cap"]["picked"] = asked.get(one["cap"]["setting"], one["cap"]["value"])
        for extra in one["extras"]:
            extra["picked"] = asked.get(extra["key"], extra["value"])
    drawn = "company" in asked
    for row in rows:
        slug = row["id"]
        row["allowed_now"] = f"allow_{slug}" in asked if drawn else row["allowed"]
        row["standin_now"] = f"standin_{slug}" in asked if drawn else row["standin"]
        saved = "" if row["limit"] is None else row["limit"]
        row["limit_now"] = asked.get(f"limit_{slug}", saved)
    for row in lineup:
        for cell in row["cells"]:
            cell["picked"] = asked.get(cell["setting"], cell["value"])
    checked["picked"] = ("model_watch" in asked) if "model_watch_seen" in asked else checked["on"]


def build(app: Any, conn: sqlite3.Connection, typed: Any = None) -> Built:
    """Everything the page draws, from the settings in force and the last 30 days of calls."""
    from familydb.store import settings as settings_store

    settings: Settings = app.settings
    now = app.clock.now()
    days, per_day = tallies(conn, settings, now)
    since, until = window(settings, now)[1], utc_iso(now + timedelta(days=1))
    figures = calls.figures_between(conn, since=since, until=until)
    month_since = spending.month_start(settings, now)
    stored = settings_store.overrides(conn)
    every = companies.every(settings)
    views_ = [
        _use_view(use, settings, conn, every, per_day[use.key], figures, month_since, stored)
        for use in uses.USES
    ]
    rows = [
        _company_row(
            company, settings, stored, spending.company_spent(conn, settings, now, company.slug)
        )
        for company in every
    ]
    for row in rows:
        mine = [
            one for one in views_ if one["now"]["company"] == row["id"] and not one["now"]["off"]
        ]
        row["answers"] = [one["name"] for one in mine]
        row["cost"] = round(sum(one["now"]["month"] for one in mine), 4)
    saved_days = [0.0] * WINDOW_DAYS
    for one in views_:
        now_ = one["now"]
        match = next(
            (o for o in one["opts"] if o["c"] == now_["company"] and o["n"] == now_["model"]), None
        )
        if match and match["d"] and not now_["off"]:
            saved_days = [a + b for a, b in zip(saved_days, match["d"], strict=True)]
    total = sum(saved_days)
    month = sum(one["now"]["month"] for one in views_)
    head = {
        "total": round(total, 4),
        "month": round(month, 4),
        "busiest": round(max(saved_days), 4),
        "limit": settings.daily_spend_limit,
        "real": any(not one["typical"] for one in views_),
    }
    grouped: dict[str, list[dict[str, Any]]] = {}
    for one in views_:
        grouped.setdefault(one["group"], []).append(one)
    changes = model_store.changes_since(conn, since=utc_iso(now - timedelta(days=7)))
    last = model_store.stamp(conn)
    checked = {
        "on": settings.model_watch,
        "last": views.local_moment(last, settings.tzinfo) if last else None,
        "changes": len(changes),
    }
    data = {
        "days": [f"{d:%a} {d.day} {d:%b}" for d in days],
        "limit": settings.daily_spend_limit,
        "companies": rows,
        # The order a stand-in is looked for in: the same one every time.
        "order": list(companies.slugs(settings)),
        "uses": [{k: one[k] for k in DATA_KEYS} for one in views_],
        "presets": PRESETS,
    }
    lineup = lineup_rows(settings, app.base_settings, stored)
    _picked(typed, views_, rows, lineup, checked)
    return Built(
        data=data,
        uses=views_,
        groups=list(grouped.items()),
        companies=rows,
        head=head,
        lineup=lineup,
        checked=checked,
        names={c.slug: c.label for c in every},
    )


# -- the form -------------------------------------------------------------------------------------


@dataclass
class Reading:
    """What a posted form says to store, and what is wrong with it."""

    values: dict[str, Any] = field(default_factory=dict)
    problems: dict[str, str] = field(default_factory=dict)


def _choice(
    use: uses.Use,
    raw: str,
    typed: str,
    settings: Settings,
    every: tuple[companies.Company, ...],
) -> tuple[str, str | None]:
    """One use's posted choice as it is stored, or the sentence on what is wrong with it."""
    raw = raw.strip()
    if not raw:
        return "", None
    head, _, rest = raw.partition(":")
    if raw == uses.OFF:
        return (raw, None) if use.off else ("", NOT_A_CHOICE)
    if head == uses.SAME:
        # A use may follow the one it follows by default, and no other.
        return (raw, None) if use.exact and rest == use.anchor else ("", NOT_A_CHOICE)
    company = next((c for c in every if c.slug == head), None)
    if company is None or not rest:
        return "", NOT_A_CHOICE
    if rest == OTHER:
        rest = typed.strip()
        if not rest:
            return "", NEEDS_NAME
        if len(rest) > MOST_NAME or any(character.isspace() for character in rest):
            return "", NAME_SHAPE
    listed = models_for(use, company, settings)
    if not listed:
        what = {
            "search": "it has no web search",
            "hear": "it hears nothing",
            "look": "it reads no pictures",
        }.get(use.needs, "it cannot")
        return "", CANNOT.format(company=company.label, what=what)
    return f"{company.slug}:{rest}", None


def read_form(form: Any, live: Settings, base: Settings, stored: dict[str, Any]) -> Reading:
    """The posted page as settings to store. A part the form did not carry is left alone."""
    reading = Reading()
    every = companies.every(live)
    # The plain boxes: the budgets and the lineup, read as every other settings page reads them.
    values, problems = fields.read_form(form)
    # A box that says what the server already does is not an override.
    for key, value in values.items():
        if value is not None and value == getattr(base, key, None):
            values[key] = None
    reading.values.update(values)
    reading.problems.update(problems)

    choices: dict[str, str] = {}
    saw_choices = False
    for use in uses.USES:
        name = f"choice_{use.key}"
        if name not in form:
            continue
        saw_choices = True
        text, why = _choice(use, form[name], form.get(f"other_{use.key}", ""), live, every)
        if why:
            reading.problems[name] = f"{use.label}: {why}"
        elif text:
            choices[use.key] = text
    if saw_choices:
        # Stored only when it is not what the use already does: a choice that is the default is
        # the default, and goes on following whatever it follows.
        trial = live.model_copy(update={"model_choices": choices})
        choices = {
            key: text for key, text in choices.items() if text != uses.default_choice(trial, key)
        }
        reading.values["model_choices"] = choices or None

    efforts: dict[str, str] = {}
    saw_efforts = False
    for use in uses.USES:
        name = f"effort_{use.key}"
        if name not in form:
            continue
        saw_efforts = True
        given = form[name].strip()
        if given and given not in dict(EFFORTS):
            reading.problems[name] = f"{use.label}, thinking: {NOT_A_CHOICE}"
        elif given:
            efforts[use.key] = given
    if saw_efforts:
        reading.values["use_effort"] = efforts or None

    drawn = form.getlist("company")
    if drawn:
        options = dict(live.company_options)
        for slug in drawn:
            if slug not in {c.slug for c in every}:
                continue
            limit_text = form.get(f"limit_{slug}", "").strip()
            limit: float | None = None
            if limit_text:
                try:
                    limit = float(limit_text)
                    if not 0 <= limit <= MOST_LIMIT:
                        raise ValueError
                except ValueError:
                    named = next(c.label for c in every if c.slug == slug)
                    reading.problems[f"limit_{slug}"] = f"{named}, most to spend: {BAD_LIMIT}"
                    continue
            without = options.get(slug, CompanyOptions()).model_copy(update={"stand_in": None})
            usual = live.model_copy(update={"company_options": {**options, slug: without}})
            standing = f"standin_{slug}" in form
            options[slug] = CompanyOptions(
                allowed=f"allow_{slug}" in form,
                stand_in=None if standing == companies.may_stand_in(slug, usual) else standing,
                monthly_limit=limit,
            )
        tidy = {
            s: o.model_dump(exclude_defaults=True)
            for s, o in options.items()
            if o != CompanyOptions()
        }
        reading.values["company_options"] = tidy or None

    if "model_watch_seen" in form:  # an unticked box is not sent at all
        wanted = "model_watch" in form
        reading.values["model_watch"] = None if wanted == base.model_watch else wanted
    return reading


def unknown_typed(
    choices: dict[str, str] | None, before: dict[str, str] | None, candidate: Settings
) -> dict[str, str]:
    """A model name typed on a row that its company says it does not have. Only a definite no
    counts: a company that cannot be asked, or has no key, is no reason to refuse."""
    found: dict[str, str] = {}
    for key, text in (choices or {}).items():
        if text == (before or {}).get(key):
            continue
        choice = uses.parse(text)
        company = companies.get(choice.company, candidate)
        if choice.form != "model" or company is None:
            continue
        if choice.model in models_for(uses.BY_KEY[key], company, candidate):
            continue
        if providers.build(company.slug, candidate).model_exists(choice.model) is False:
            found[f"choice_{key}"] = f"{uses.BY_KEY[key].label}: " + NO_SUCH_MODEL.format(
                company=company.label, name=choice.model
            )
    return found
