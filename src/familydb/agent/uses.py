"""What the family has Vera do, and which company and model does each: eight **uses**, each with one
choice (`Settings.model_choices`), laid over the settings that used to say it in five places (the
company, a strength per situation, each company's everyday model).

A choice is one of:

- `<company>:<model>`: that model, asked of that company (a model name may itself hold a colon);
- `same:<use>`: whatever another use is answered with;
- `off`: the use is not done, for those that can be off (what it means is `Use.off`);
- nothing: the environment's choice for it (`Settings.env_choices`: the older keys, PROVIDER and
  the levels among them, read into choices at load), else the use's own *default*: off for one
  that starts off, its anchor's company at its own level, or the company FamilyDB starts on.

`resolve` says what a use is answered with. `answering` (and `hearing`, `looking`) turns that into
who is asked and for which model, once at the gateway's door, so the gateway, the request builder
and the daily check need only ask here, not learn a new way to choose a model. A stand-in answers
at the chosen model's *level* in its company's lineup (`catalog`), or everyday for a model nobody
listed.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any

from familydb import happening
from familydb.agent import providers
from familydb.agent.providers import Provider, catalog, companies, prices
from familydb.base.config import USE_KEYS, Settings

SAME = "same"
OFF = "off"
KINDS_OF_NEED = ("answer", "search", "hear", "look")


@dataclass(frozen=True)
class Use:
    key: str
    label: str
    line: str  # one line under the name on the page
    kinds: tuple[str, ...]  # the calls it covers: gateway.KINDS, and "transcribe" and "look"
    surface: str  # "chat" or "worker": the kind of call it is
    default_level: str  # the lineup level it answers at when nothing is chosen (catalog.LEVELS)
    needs: str  # what a company must be able to do for it: answer, search, hear, look
    anchor: str = ""  # the use whose company it defaults to
    exact: bool = False  # follows its anchor exactly (same model) by default
    default_off: bool = False  # off until the family chooses a model for it
    off: str = ""  # what being off means; empty: it cannot be off
    group: str = ""  # which of the page's groups it is drawn in


USES: tuple[Use, ...] = (
    Use(
        "chat",
        "Answering the family",
        "Reads each message and writes the answer.",
        ("chat", "retry"),
        "chat",
        "everyday",
        "answer",
        group="Talking",
    ),
    Use(
        "digest",
        "The weekend digest",
        "The week's ideas, sent on its day.",
        ("digest",),
        "chat",
        "everyday",
        "answer",
        anchor="chat",
        exact=True,
        group="Talking",
    ),
    Use(
        "choose",
        "Choosing suggestions",
        "Picks what to suggest from everything the household knows.",
        ("choose",),
        "chat",
        "best",
        "answer",
        anchor="chat",
        off="Suggestions come in FamilyDB's own order.",
        group="Thinking",
    ),
    Use(
        "lookup",
        "Looking things up",
        "Fills ideas in on the web: hours, addresses, prices.",
        ("enrich", "discover", "places", "price_check"),
        "worker",
        "everyday",
        "search",
        anchor="chat",
        group="Looking",
    ),
    Use(
        "onnear",
        happening.NAME,
        "Looks for what is on near home.",
        ("scout", "find_feeds"),
        "worker",
        "everyday",
        "search",
        anchor="lookup",
        exact=True,
        group="Looking",
    ),
    Use(
        "hear",
        "Voice notes",
        "Writes down what a voice note says.",
        ("transcribe",),
        "worker",
        "everyday",
        "hear",
        off="The family is asked to type.",
        group="Hearing and seeing",
    ),
    Use(
        "look",
        "Photos",
        "Reads a poster, a menu or a ticket.",
        ("look",),
        "worker",
        "everyday",
        "look",
        anchor="lookup",
        exact=True,
        off="The family is asked in words.",
        group="Hearing and seeing",
    ),
    Use(
        "judge",
        "Weighing changes",
        "Decides what to do when a model goes or a price moves.",
        ("judge",),
        "worker",
        "best",
        "answer",
        anchor="lookup",
        default_off=True,
        off="Changes to the models wait for an admin.",
        group="Thinking",
    ),
)
BY_KEY: dict[str, Use] = {use.key: use for use in USES}
BY_KIND: dict[str, Use] = {kind: use for use in USES for kind in use.kinds}
assert tuple(BY_KEY) == USE_KEYS  # config.py names them too, so a stored choice can be read there


@dataclass(frozen=True)
class Choice:
    """A stored choice, read."""

    form: str  # "default", "same", "off" or "model"
    follows: str = ""
    company: str = ""
    model: str = ""

    def __str__(self) -> str:
        if self.form == "same":
            return f"{SAME}:{self.follows}"
        if self.form == "off":
            return OFF
        if self.form == "model":
            return f"{self.company}:{self.model}"
        return ""


def parse(text: str | None) -> Choice:
    """A stored choice. Anything that is not one reads as the default, so a hand-edited or
    out-of-date value never stops the app."""
    value = (text or "").strip()
    if not value:
        return Choice("default")
    if value == OFF:
        return Choice("off")
    head, _, rest = value.partition(":")
    if head == SAME:
        return Choice("same", follows=rest) if rest in BY_KEY else Choice("default")
    if head and rest and head != SAME:
        return Choice("model", company=head, model=rest)
    return Choice("default")


def use_of(kind: str) -> Use:
    try:
        return BY_KIND[kind]
    except KeyError:
        raise ValueError(f"no use covers a call of kind {kind!r}") from None


@dataclass(frozen=True)
class Resolution:
    """What a use is answered with."""

    use: str
    company: str | None  # None: off, or nothing that can do it
    model: str | None
    level: str  # the lineup level a stand-in answers at
    explicit: bool = False  # chosen for this use (or followed from one that was)
    followed: str = ""  # the use it takes its answer from
    off: bool = False
    source: str = "default"  # "chosen", "same", "default" or "off": for the page to say
    notes: list[str] = field(default_factory=list)


def _level_of(company: str, model: str) -> str:
    known = catalog.known(company, model)
    return known.level if known is not None else catalog.EVERYDAY


def _loops(settings: Settings, use_key: str) -> bool:
    """Whether following `same:` choices from this use comes back round to a use already seen."""
    seen = {use_key}
    current = use_key
    while True:
        choice = parse(chosen_text(settings, current))
        if choice.form != "same":
            return False
        if choice.follows in seen:
            return True
        seen.add(choice.follows)
        current = choice.follows


def chosen_text(settings: Settings, use_key: str) -> str | None:
    """The choice in force for a use: the page's, else the environment's (`Settings.env_choices`,
    the older keys read into choices at load), else None."""
    return settings.model_choices.get(use_key) or settings.env_choices.get(use_key) or None


def resolve(settings: Settings, use_key: str, _seen: tuple[str, ...] = ()) -> Resolution:
    """What this use is answered with, now. The environment's choice for a use (the older keys)
    answers as the page's would, but counts as a default rather than a choice: it is what the use
    falls back to, drawn as such, and a stand-in answers at its level as before."""
    found = _resolve(settings, use_key, _seen)
    if found.explicit and not settings.model_choices.get(use_key) and not found.followed:
        return dataclasses.replace(found, explicit=False, source="default")
    return found


def _resolve(settings: Settings, use_key: str, _seen: tuple[str, ...]) -> Resolution:
    use = BY_KEY[use_key]
    choice = parse(chosen_text(settings, use_key))
    if choice.form == "off" and use.off:
        return Resolution(use_key, None, None, catalog.EVERYDAY, off=True, source="off")
    if choice.form == "same" and not _loops(settings, use_key):
        found = resolve(settings, choice.follows, (*_seen, use_key))
        return Resolution(
            use_key,
            found.company,
            found.model,
            found.level,
            explicit=True,
            followed=choice.follows,
            off=found.off,
            source="same",
        )
    if choice.form == "model" and companies.get(choice.company, settings) is not None:
        if choice.model in catalog.LEVELS:
            # The company at a level of its lineup ("anthropic:better"), as the environment's
            # older keys say it, or anyone may: the model the lineup gives it today.
            surface = _surface(use)
            model = providers.model_at(
                providers.build(choice.company, settings), surface, choice.model
            )
            return Resolution(
                use_key, choice.company, model, choice.model, explicit=True, source="chosen"
            )
        return Resolution(
            use_key,
            choice.company,
            choice.model,
            _level_of(choice.company, choice.model),
            explicit=True,
            source="chosen",
        )
    return _default(settings, use, _seen)


def _default(settings: Settings, use: Use, seen: tuple[str, ...]) -> Resolution:
    """What a use does when nothing was chosen for it, by the page or the environment: off, for
    one that starts off; what it hears with, for voice notes; its anchor exactly, for one that
    follows another; else its anchor's company (or the company FamilyDB starts on) at its own
    default level."""
    if use.default_off:
        return Resolution(use.key, None, None, catalog.EVERYDAY, off=True, source="off")
    if use.key == "hear":
        return _hearing(settings)
    surface = _surface(use)
    anchor = (
        resolve(settings, use.anchor, (*seen, use.key))
        if use.anchor and use.anchor not in seen
        else None
    )
    if anchor is not None and not anchor.off and anchor.company is not None:
        if use.exact and anchor.model:
            return Resolution(
                use.key,
                anchor.company,
                anchor.model,
                anchor.level,
                explicit=anchor.explicit,
                followed=use.anchor,
                source="same" if anchor.explicit else "default",
            )
        provider = providers.build(anchor.company, settings)
        if use.needs == "search":
            provider = providers.with_search(settings, provider, surface)
    elif use.needs == "search":
        provider = providers.for_surface(settings, surface, web=True)
    else:
        provider = providers.for_surface(settings, surface)
    model = providers.model_at(provider, surface, use.default_level)
    # It answers on the company another use was chosen to, so nothing else says who: `answering`
    # builds that company's provider.
    anchored = anchor is not None and anchor.explicit and provider.name == anchor.company
    return Resolution(
        use.key,
        provider.name,
        model,
        use.default_level,
        explicit=anchored,
        followed=use.anchor if anchored else "",
        source="same" if anchored else "default",
    )


def without(settings: Settings, use_key: str) -> Settings:
    """The settings with no page choice for this use (the environment's stays)."""
    return settings.model_copy(
        update={"model_choices": {k: v for k, v in settings.model_choices.items() if k != use_key}}
    )


def default_choice(settings: Settings, use_key: str) -> str:
    """The choice a use has when none is stored for it, in the form the page stores one: the
    environment's for it, else `same:<use>` where it follows another exactly, `off`, or
    `<company>:<model>`; empty when nothing can do it. Stored choices of the other uses stay, so a
    default that follows a use the family moved follows it there."""
    use = BY_KEY[use_key]
    res = resolve(without(settings, use_key), use_key)
    if res.off:
        return OFF
    if use.exact and res.followed == use.anchor and use.anchor:
        return f"{SAME}:{use.anchor}"
    return f"{res.company}:{res.model}" if res.company and res.model else ""


def default_level(settings: Settings, use_key: str) -> str:
    """The lineup level a use answers at when none is stored for it."""
    return resolve(without(settings, use_key), use_key).level


def _hearing(settings: Settings) -> Resolution:
    """Who hears when nobody was chosen to: the chat's company first, if it can."""
    first = resolve(settings, "chat").company
    for provider in providers.hearers(settings, first=first):
        model = provider.listener()
        if model:
            return Resolution("hear", provider.name, model, catalog.EVERYDAY)
    return Resolution("hear", None, None, catalog.EVERYDAY)


def on(settings: Settings, use_key: str) -> bool:
    """Whether the use is done at all: it has not been turned off."""
    return not resolve(settings, use_key).off


@dataclass(frozen=True)
class Answering:
    """Who answers a kind of call, worked out once at the gateway's door: the company's provider,
    the model it answers with, the lineup level a stand-in answers at, and the use's own thinking
    (None: the setting's)."""

    provider: Provider
    model: str
    level: str
    effort: str | None
    resolution: Resolution


def _surface(use: Use) -> str:
    return "chat" if use.surface == "chat" else "worker"


def answering(settings: Settings, kind: str, *, api: Any = None) -> Answering:
    """Who answers a call of this kind, and with which model: the family's choice for its use,
    else what the older settings say (`resolve`). A chosen company that cannot search is passed
    over for a lookup as `providers.with_search` says; a chosen model gone is swapped for the
    daily check's replacement as any model is (`prices.swapped`). An injected `api` (a test's
    fake) means the company as chosen, whatever it can do."""
    use = use_of(kind)
    res = resolve(settings, use.key)
    surface = _surface(use)
    effort = settings.use_effort.get(use.key) or None
    if res.off or res.company is None or res.model is None:
        # Off, or nothing can do it: the older machinery's answer stands, as it always did (an
        # unconfigured provider is refused at the door, `can_ask`).
        provider = providers.for_surface(settings, surface, api=api, web=use.needs == "search")
        level = use.default_level
        return Answering(provider, providers.model_at(provider, surface, level), level, effort, res)
    provider = providers.build(res.company, settings, api=api)
    level = res.level
    if use.needs == "search" and api is None:
        provider = providers.with_search(settings, provider, surface)
    if provider.name != res.company:
        return Answering(provider, providers.model_at(provider, surface, level), level, effort, res)
    return Answering(provider, prices.swapped(provider.name, res.model), level, effort, res)


def hearing(settings: Settings, *, audio: Any = None) -> list[tuple[Provider, str | None]]:
    """Who may hear a voice note, in the order to ask, each with the model: the company and model
    chosen for it (by the page or the environment) first, then (unless an `audio` stand-in is
    injected) any other that can hear and the family let stand in; with nothing chosen,
    `providers.hearers` behind the chat's company, each with its own."""
    res = resolve(settings, "hear")
    if res.off:
        return []
    named = res.explicit or parse(chosen_text(settings, "hear")).form == "model"
    if not (named and res.company):
        first = resolve(settings, "chat").company
        return [
            (one, one.listener()) for one in providers.hearers(settings, audio=audio, first=first)
        ]
    first = providers.build(res.company, settings, audio=audio)
    if audio is not None:
        return [(first, res.model)] if first.listener() or res.model else []
    spares = [
        (one, one.listener())
        for one in providers.hearers(settings)
        if one.name != res.company and companies.may_stand_in(one.name, settings)
    ]
    return [(first, res.model), *spares] if first.configured() else spares


def looking(settings: Settings, *, api: Any = None) -> list[tuple[Provider, str | None]]:
    """Who may look at a photo, in the order to ask, each with the model: as `hearing`, for the
    photos use (which follows the lookups unless chosen apart)."""
    res = resolve(settings, "look")
    if res.off:
        return []
    named = res.explicit or parse(chosen_text(settings, "look")).form == "model"
    if not (named and res.company):
        first = resolve(settings, "lookup").company
        return [(one, one.viewer()) for one in providers.lookers(settings, api=api, first=first)]
    first = providers.build(res.company, settings, api=api)
    if api is not None:
        return [(first, res.model)]
    spares = [
        (one, one.viewer())
        for one in providers.lookers(settings)
        if one.name != res.company and companies.may_stand_in(one.name, settings)
    ]
    return [(first, res.model), *spares] if first.configured() and first.viewer() else spares
