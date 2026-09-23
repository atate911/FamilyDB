"""Stage: which ideas plausibly fit the window. Pure rules; the first failing rule is the reason."""

from __future__ import annotations

from datetime import date

from familydb.config import Settings
from familydb.integrations.open_meteo import DayForecast
from familydb.store.ideas import Idea
from familydb.suggest.types import Candidate, Constraints, Context, Shortlisted

RECENTLY_DONE_DAYS = 60
LOW_RATING = 5.0
RAIN_CHANCE_MAX = 50
RAIN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}
SNOW_CODES = {71, 73, 75, 77, 85, 86}
WARM_C = 18.0
WARM_F = 64.0
BLOCK_ORDER = ("morning", "afternoon", "evening")
BLOCK_MINUTES = {"morning": 240, "afternoon": 300, "evening": 300}
LONG_IDEA_MINUTES = 480
SHORTLIST_MAX = 8
ANYONE = {"whole family", "family", "everyone", "anyone", "all of us"}


def fmt_minutes(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes / 60:g} h"


def longest_free_span(free: list[str]) -> int:
    """Minutes in the longest run of consecutive free blocks."""
    best = current = 0
    for block in BLOCK_ORDER:
        if block in free:
            current += BLOCK_MINUTES[block]
            best = max(best, current)
        else:
            current = 0
    return best


def whole_day_free(free: list[str]) -> bool:
    return all(block in free for block in BLOCK_ORDER)


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


def _status_reason(idea: Idea, today: date) -> str | None:
    if idea.status == "planned":
        return "already planned"
    if idea.status == "done" and idea.last_done_at:
        try:
            days_ago = (today - date.fromisoformat(idea.last_done_at[:10])).days
        except ValueError:
            days_ago = None
        if days_ago is not None and days_ago < RECENTLY_DONE_DAYS:
            weeks = max(1, days_ago // 7)
            return f"done {weeks} week{'s' if weeks != 1 else ''} ago"
    if idea.avg_rating is not None and idea.avg_rating < LOW_RATING:
        return f"rated {idea.avg_rating:g}/10 last time"
    return None


def participants_match(idea: Idea, requested: list[str]) -> bool:
    if not requested or not idea.participants:
        return True
    wanted = [r.casefold().strip() for r in requested]
    for entry in idea.participants:
        text = entry.casefold().strip()
        if text in ANYONE:
            return True
        if any(w in text or text in w for w in wanted):
            return True
    return False


def _constraint_reason(idea: Idea, constraints: Constraints) -> str | None:
    if (
        constraints.max_cost_level is not None
        and idea.cost_level is not None
        and idea.cost_level > constraints.max_cost_level
    ):
        return "over the budget asked for"
    if constraints.setting and idea.setting not in (constraints.setting, "either"):
        return f"{idea.setting} only"
    if (
        constraints.max_duration_minutes is not None
        and idea.duration_min is not None
        and idea.duration_min > constraints.max_duration_minutes
    ):
        return f"needs about {fmt_minutes(idea.duration_min)}"
    return None


def _weather_fit(
    idea: Idea, context: Context, settings: Settings
) -> tuple[list[date], str, str | None]:
    """(fitting days, weather state, reason when nothing fits)."""
    needs_dry = idea.setting == "outdoor" or idea.weather == "dry"
    needs_warm = idea.weather == "warm"
    needs_snow = idea.weather == "snow"
    fits: list[date] = []
    known = False
    bad: list[str] = []
    for day in context.days:
        forecast = day.forecast
        if forecast is not None:
            known = True
        ok = True
        if needs_dry:
            dry = day_is_dry(forecast)
            if dry is False:
                ok = False
                chance = f" ({forecast.rain_chance}%)" if forecast and forecast.rain_chance else ""
                bad.append(f"rain likely {day.date:%A}{chance}")
        if ok and needs_warm and day_is_warm(forecast, settings) is False:
            ok = False
            bad.append(f"not warm enough {day.date:%A}")
        if ok and needs_snow and day_has_snow(forecast) is False:
            ok = False
            bad.append(f"no snow forecast {day.date:%A}")
        if ok:
            fits.append(day.date)
    if not fits:
        return [], "poor", "; ".join(bad) or "weather does not fit"
    if not (needs_dry or needs_warm or needs_snow):
        return fits, ("ok" if known else "unknown"), None
    return fits, ("ok" if known else "unknown"), None


def _duration_fit(idea: Idea, days: list[date], context: Context) -> tuple[list[date], str | None]:
    needs = idea.duration_min or idea.duration_max
    long_idea = idea.kind == "day_trip" or (needs is not None and needs >= LONG_IDEA_MINUTES)
    contexts = [context.day(d) for d in days]
    contexts = [c for c in contexts if c is not None]
    if not contexts or not contexts[0].free_known:
        return days, None
    if idea.kind == "trip":
        if all(whole_day_free(c.free) for c in context.days):
            return days, None
        return [], "needs the whole window free"
    fits: list[date] = []
    best_block = 0
    for day in contexts:
        span = longest_free_span(day.free)
        best_block = max(best_block, span)
        if long_idea:
            if whole_day_free(day.free):
                fits.append(day.date)
        elif needs is None:
            if day.free:
                fits.append(day.date)
        elif needs <= span:
            fits.append(day.date)
    if fits:
        return fits, None
    if best_block == 0:
        return [], "no free time in the window"
    if long_idea:
        return [], "needs a whole free day"
    return [], f"needs about {fmt_minutes(needs or 0)}, only {fmt_minutes(best_block)} free"


def shortlist(
    all_ideas: list[Idea], context: Context, constraints: Constraints, settings: Settings
) -> tuple[list[Shortlisted], list[Candidate], list[Candidate]]:
    """(kept for evaluation, ruled out with reasons, extras beyond the cap as 'possible')."""
    kept: list[Shortlisted] = []
    ruled_out: list[Candidate] = []

    def out(idea: Idea, reason: str) -> None:
        ruled_out.append(
            Candidate(idea_id=idea.id, title=idea.title, verdict="ruled_out", reasons=[reason])
        )

    for idea in all_ideas:
        if constraints.idea_ids and idea.id not in constraints.idea_ids:
            continue
        if idea.status == "dropped":
            continue
        reason = _status_reason(idea, context.today)
        if reason:
            out(idea, reason)
            continue
        if not participants_match(idea, constraints.participants):
            out(idea, f"for {', '.join(idea.participants)}")
            continue
        if idea.seasons and context.season not in idea.seasons:
            out(idea, f"for {', '.join(idea.seasons)}")
            continue
        reason = _constraint_reason(idea, constraints)
        if reason:
            out(idea, reason)
            continue
        if context.window is None:
            kept.append(Shortlisted(idea, [], "unknown"))
            continue
        fits, weather_state, reason = _weather_fit(idea, context, settings)
        if reason:
            out(idea, reason)
            continue
        fits, reason = _duration_fit(idea, fits, context)
        if reason:
            out(idea, reason)
            continue
        kept.append(Shortlisted(idea, fits, weather_state))  # type: ignore[arg-type]

    kept.sort(key=lambda s: (s.idea.times_done > 0, s.idea.last_done_at or "", s.idea.id))
    extras = [
        Candidate(
            idea_id=s.idea.id,
            title=s.idea.title,
            verdict="possible",
            reasons=["not checked in detail"],
            fits_days=[d.isoformat() for d in s.fits_days],
        )
        for s in kept[SHORTLIST_MAX:]
    ]
    return kept[:SHORTLIST_MAX], ruled_out, extras
