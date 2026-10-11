"""Stage: which ideas plausibly fit the window; pure rules, the first failing one is the reason.

Two kinds of rule. A fact rules an idea out: already planned, for somebody else, over its dates,
past the limits asked or a firm rule, no snow for a snow idea, not enough free time. A matter of
taste only lowers it to possible, with the reason said first, and leaves the choice to the family
and to the stronger call that reads the dossier (suggest/choosing.py): it was done lately, the last
two visits disappointed, rain or cold is forecast, a long day out has something else on the day.
What the family plans anyway is counted on Status (suggest/taken.py), so a taste rule that does not
suit them shows.

Every idea that passes goes on to be evaluated: that is local work (its place, and arithmetic), so
none is left "not checked in detail" for coming late on the list, and which are shown is decided
after, by the same order the reply is given in (compose.py).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date

from familydb.base.config import Settings
from familydb.base.dates import age_on, fmt_minutes
from familydb.integrations.open_meteo import DayForecast
from familydb.store.ideas import GIFT, Idea, ages_text
from familydb.store.members import Member
from familydb.suggest import people as who
from familydb.suggest.types import Candidate, Constraints, Context, Shortlisted

# How long an idea that was done rests before it is offered again, by kind: a restaurant is good
# again sooner than a day trip. Any other kind rests REST_DAYS; asked for their favorites ("our
# usual"), a week is enough.
REST_DAYS = 60
REST_BY_KIND = {"restaurant": 21, "activity": 30, "outing": 60, "day_trip": 180}
FAVORITE_REST_DAYS = 7
# A rating below this is a disappointment. Only the last two in a year count: one is feedback, not
# a dislike (docs/MEMORY.md), so it is offered as possible with the rating said; two in a row rule
# it out. Older ones have lapsed: the place, or the family, has moved on.
LOW_RATING = 5
RATING_DAYS = 365
# Loved: a rating this high last time, or "again" the latest word on it.
FAVORITE_RATING = 8
RAIN_CHANCE_MAX = 50
RAIN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}
SNOW_CODES = {71, 73, 75, 77, 85, 86}
WARM_C = 18.0
WARM_F = 64.0
LONG_IDEA_MINUTES = 480
# The least free time worth offering an idea of unknown length for.
SHORT_VISIT_MINUTES = 60


def day_is_dry(forecast: DayForecast | None) -> bool | None:
    if forecast is None:
        return None
    if forecast.rain_chance is not None:
        return forecast.rain_chance < RAIN_CHANCE_MAX
    if forecast.code is None:
        return None
    return forecast.code not in RAIN_CODES and forecast.code not in SNOW_CODES


def day_is_warm(forecast: DayForecast | None, settings: Settings) -> bool | None:
    if forecast is None or forecast.high is None:
        return None
    threshold = WARM_F if settings.weather_units == "imperial" else WARM_C
    return forecast.high >= threshold


def day_has_snow(forecast: DayForecast | None) -> bool | None:
    if forecast is None or forecast.code is None:
        return None
    return forecast.code in SNOW_CODES


def rest_days(idea: Idea, prefer: str = "new") -> int:
    """How long this idea rests once done before it is offered again."""
    if prefer == "favorites":
        return FAVORITE_REST_DAYS
    return REST_BY_KIND.get(idea.kind.casefold(), REST_DAYS)


def _status_reason(
    idea: Idea, today: date, plan: tuple[date, date] | None, rest: int = REST_DAYS
) -> tuple[str | None, str | None]:
    """(why it is out, why it rests) from what became of it. `plan` is its latest live plan's
    first and last day: a planned idea is out while that is to come, and once it is over counts as
    done on its day, so an idea nobody said how it went is not left out for good. `rest` is how
    many days a done one rests (`rest_days`); resting is said, not ruled out."""
    if idea.status == "planned":
        if plan is None:
            return "already planned", None
        first, last = plan
        if last >= today:
            return f"already planned for {day_text(first)}", None
        if (today - last).days < rest:
            return None, f"was planned for {day_text(first)}"
    elif idea.status == "done" and idea.last_done_at:
        try:
            days_ago = (today - date.fromisoformat(idea.last_done_at[:10])).days
        except ValueError:
            days_ago = None
        if days_ago is not None and days_ago < rest:
            if days_ago < 7:
                said = {0: "done today", 1: "done yesterday"}.get(
                    days_ago, f"done {days_ago} days ago"
                )
                return None, said
            weeks = days_ago // 7
            return None, f"done {weeks} week{'s' if weeks != 1 else ''} ago"
    return None, None


def rating_reason(ratings: Sequence[int]) -> str | None:
    """What to say of its ratings in the last year, newest first, when they disappointed: the
    last one, or the last two when both did. Said first, and possible at best; never ruled out."""
    last = list(ratings[:2])
    if len(last) == 2 and all(rating < LOW_RATING for rating in last):
        said = f"{last[0]}" if last[0] == last[1] else f"{last[1]} and {last[0]}"
        return f"rated {said}/10 the last two times"
    if last and last[0] < LOW_RATING:
        return f"rated {last[0]}/10 last time"
    return None


def day_text(day: date) -> str:
    return f"{day:%a} {day.day} {day:%b}"


def dates_text(idea: Idea) -> str:
    """When a dated idea is on, in a few words ("only on Sun 18 Oct")."""
    first, last = idea.first_day, idea.last_day
    if first is None:
        return "on no day given"
    if last is None:
        return f"on from {day_text(first)}"
    if last == first:
        return f"only on {day_text(first)}"
    return f"on {day_text(first)} to {day_text(last)}"


def dates_reason(idea: Idea, context: Context) -> str | None:
    """Why a dated idea cannot be done in this window (over, or other days)."""
    if idea.first_day is None and idea.last_day is None:
        return None
    last = idea.last_day
    if last is not None and last < context.today:
        return f"was over on {day_text(last)}"
    if context.window is None:
        return None
    if any(idea.on(day.date) for day in context.days):
        return None
    return dates_text(idea)


def participants_match(
    idea: Idea, requested: list[str], people: Sequence[Member] | None = None
) -> bool:
    """Whether an idea is for who is coming. With the family list (`people`) both are read as
    the people they mean (suggest/people.py), and fit when they share somebody; words that name
    nobody on it, or no list, are compared as text."""
    if not requested or not idea.participants:
        return True
    if people:
        wanted, saved = who.resolve(requested, people), who.resolve(idea.participants, people)
        if wanted.anyone or saved.anyone or wanted.ids & saved.ids:
            return True
        if not wanted.unplaced and not saved.unplaced:
            return False
    folded = [r.casefold().strip() for r in requested]
    for entry in idea.participants:
        text = entry.casefold().strip()
        if text in who.ANYONE:
            return True
        if any(w in text or text in w for w in folded):
            return True
    return False


def kids_coming(
    constraints: Constraints, people: Sequence[Member], today: date
) -> list[tuple[str, int]]:
    """(name, age) of each kid the question is about whose age is known: those it names, or
    every kid when it names nobody on the family list (the family is going)."""
    named = who.resolve(constraints.participants, people) if constraints.participants else None
    everyone = named is None or named.anyone or not named.ids
    coming = []
    for member in people:
        if member.role != "kid" or not member.active:
            continue
        if not everyone and named is not None and member.id not in named.ids:
            continue
        age = age_on(member.birth_date, today)
        if age is not None:
            coming.append((member.display_name, age))
    return coming


def _age_reason(idea: Idea, kids: Sequence[tuple[str, int]]) -> str | None:
    """Why an idea is not for a kid coming: "Mia is 4; ages 6+"."""
    for name, age in kids:
        if (idea.min_age is not None and age < idea.min_age) or (
            idea.max_age is not None and age > idea.max_age
        ):
            return f"{name} is {age}; {ages_text(idea)}"
    return None


def _constraint_reason(idea: Idea, constraints: Constraints) -> str | None:
    """Why the question's limits, or a firm rule's (named by its memory), leave it out."""
    if (
        constraints.max_cost_level is not None
        and idea.cost_level is not None
        and idea.cost_level > constraints.max_cost_level
    ):
        held = constraints.because("max_cost_level")
        return f"dearer than {held} allows" if held else "over the budget asked for"
    if constraints.setting and idea.setting not in (constraints.setting, "either"):
        held = constraints.because("setting")
        if held:
            return f"{idea.setting} only, and {held} says {constraints.setting}"
        return f"{idea.setting} only"
    tags = {" ".join(tag.casefold().split()) for tag in idea.tags}
    for tag in constraints.avoid:
        if tag in tags:
            return f"{tag}, which {constraints.because(f'avoid:{tag}')} rules out"
    if (
        constraints.max_duration_minutes is not None
        and idea.duration_min is not None
        and idea.duration_min > constraints.max_duration_minutes
    ):
        return f"needs about {fmt_minutes(idea.duration_min)}"
    return None


def _weather_fit(
    idea: Idea, context: Context, settings: Settings
) -> tuple[list[date], str, str | None, str | None]:
    """(fitting days, weather state, why it is out, what to say of it). A day that fails only for
    rain or cold still fits, the weather poor and said, when no day fits outright: some families
    go out in the rain. No snow for a snow idea is a fact: a day without it never fits."""
    needs_dry = idea.setting == "outdoor" or idea.weather == "dry"
    needs_warm = idea.weather == "warm"
    needs_snow = idea.weather == "snow"
    fits: list[date] = []
    wet: list[date] = []  # days that fail only for rain or cold
    known = False
    bad: list[str] = []
    snowless: list[str] = []
    for day in context.days:
        if not idea.on(day.date):
            continue
        forecast = day.forecast
        if forecast is not None:
            known = True
        taste: str | None = None
        if needs_dry and day_is_dry(forecast) is False:
            chance = f" ({forecast.rain_chance}%)" if forecast and forecast.rain_chance else ""
            taste = f"rain likely {day.date:%A}{chance}"
        elif needs_warm and day_is_warm(forecast, settings) is False:
            taste = f"not warm enough {day.date:%A}"
        if needs_snow and day_has_snow(forecast) is False:
            snowless.append(f"no snow forecast {day.date:%A}")
            bad.append(taste or snowless[-1])
            continue
        if taste:
            bad.append(taste)
            wet.append(day.date)
            continue
        fits.append(day.date)
    if fits:
        return fits, ("ok" if known else "unknown"), None, None
    if wet:
        return wet, "poor", None, "; ".join(bad)
    return [], "poor", "; ".join(snowless or bad) or "weather does not fit", None


# Said of a long day out on a day with something else on it, but time enough around it.
NOT_WHOLE = "something else on that day"


def _duration_fit(
    idea: Idea, days: list[date], context: Context
) -> tuple[list[date], str | None, str | None]:
    """(fitting days, why it is out, what to say of it). A long day out wants a day with nothing
    else on it; with eight hours free around something else it still fits, and that is said."""
    needs = idea.duration_min or idea.duration_max
    long_idea = idea.kind == "day_trip" or (needs is not None and needs >= LONG_IDEA_MINUTES)
    contexts = [context.day(d) for d in days]
    contexts = [c for c in contexts if c is not None]
    if not contexts or not contexts[0].free_known:
        return days, None, None
    if idea.kind == "trip":
        if all(c.whole for c in context.days):
            return days, None, None
        return [], "needs the whole window free", None
    fits: list[date] = []
    around: list[date] = []  # a long day out, with time enough around something else
    best_block = 0
    for day in contexts:
        span = day.longest
        best_block = max(best_block, span)
        if long_idea:
            if span >= LONG_IDEA_MINUTES:
                (fits if day.whole else around).append(day.date)
        elif needs is None:
            if span >= SHORT_VISIT_MINUTES:
                fits.append(day.date)
        elif needs <= span:
            fits.append(day.date)
    if fits:
        return fits, None, None
    if around:
        return around, None, NOT_WHOLE
    if best_block == 0:
        return [], "no free time in the window", None
    if long_idea:
        return [], "needs a whole free day", None
    return [], f"needs about {fmt_minutes(needs or 0)}, only {fmt_minutes(best_block)} free", None


def shortlist(
    all_ideas: list[Idea],
    context: Context,
    constraints: Constraints,
    settings: Settings,
    *,
    people: Sequence[Member] | None = None,
    plans: Mapping[int, tuple[date, date]] | None = None,
    ratings: Mapping[int, Sequence[int]] | None = None,
    prefer: str = "new",
) -> tuple[list[Shortlisted], list[Candidate]]:
    """(kept for evaluation, ruled out with reasons). `people` is the family list, to read who
    is coming by; `plans` each idea's latest live plan (`store.plans.latest_by_idea`); `ratings`
    each idea's in the last year, newest first (`store.outcomes.recent_ratings`); `prefer` what
    they asked for, new things or favorites, which rest less."""
    kept: list[Shortlisted] = []
    ruled_out: list[Candidate] = []
    kids = kids_coming(constraints, people or (), context.today)

    def out(idea: Idea, reason: str) -> None:
        ruled_out.append(
            Candidate(idea_id=idea.id, title=idea.title, verdict="ruled_out", reasons=[reason])
        )

    for idea in all_ideas:
        if constraints.idea_ids and idea.id not in constraints.idea_ids:
            continue
        if idea.status == "dropped" or idea.kind.casefold() == GIFT:
            continue
        # What is said first and makes it possible at best; a later fact still rules it out.
        caveats: list[str] = []
        reason, resting = _status_reason(
            idea, context.today, (plans or {}).get(idea.id), rest_days(idea, prefer)
        )
        if reason:
            out(idea, reason)
            continue
        if resting:
            caveats.append(resting)
        said = rating_reason((ratings or {}).get(idea.id, ()))
        if said:
            caveats.append(said)
        if not participants_match(idea, constraints.participants, people):
            out(idea, f"for {', '.join(idea.participants)}")
            continue
        reason = _age_reason(idea, kids)
        if reason:
            out(idea, reason)
            continue
        if idea.seasons and context.season not in idea.seasons:
            out(idea, f"for {', '.join(idea.seasons)}")
            continue
        reason = dates_reason(idea, context)
        if reason:
            out(idea, reason)
            continue
        reason = _constraint_reason(idea, constraints)
        if reason:
            out(idea, reason)
            continue
        if context.window is None:
            kept.append(Shortlisted(idea, [], "unknown", caveats, resting=bool(resting)))
            continue
        fits, weather_state, reason, said = _weather_fit(idea, context, settings)
        if reason:
            out(idea, reason)
            continue
        if said:
            caveats.append(said)
        fits, reason, said = _duration_fit(idea, fits, context)
        if reason:
            out(idea, reason)
            continue
        if said:
            caveats.append(said)
        kept.append(
            Shortlisted(idea, fits, weather_state, caveats, resting=bool(resting))  # type: ignore[arg-type]
        )
    return kept, ruled_out
