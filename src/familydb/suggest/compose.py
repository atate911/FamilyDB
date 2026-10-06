"""Stage: order the verdicts and summarise the days for the model."""

from __future__ import annotations

from familydb.integrations.open_meteo import DayForecast
from familydb.store.ideas import Idea
from familydb.suggest.types import (
    Candidate,
    Context,
    DaySummary,
    SuggestResult,
    WebFind,
    Window,
    clock,
)

MAX_REASONS = 3
VERDICT_ORDER = {"good": 0, "possible": 1, "ruled_out": 2}
# The reply names 3-5 options and a few misses; the rest is paid for twice and unused, so it is
# counted, not listed.
MAX_OFFERED = 12
MAX_RULED_OUT = 6


def _forecast_text(forecast: DayForecast | None) -> str | None:
    if forecast is None:
        return None
    parts = [forecast.summary]
    if forecast.high is not None:
        parts.append(f"high {forecast.high:g}")
    if forecast.rain_chance is not None:
        parts.append(f"rain {forecast.rain_chance}%")
    if forecast.span is not None:  # hour by hour, for the part of the day asked about
        parts.append(f"{clock(forecast.span[0])}-{clock(forecast.span[1])}")
    return ", ".join(parts)


def day_summaries(context: Context) -> list[DaySummary]:
    return [
        DaySummary(
            date=d.date.isoformat(),
            weekday=d.date.strftime("%A"),
            free=[f"{clock(a)}-{clock(b)}" for a, b in d.spans],
            free_known=d.free_known,
            commitments=d.commitments,
            forecast=_forecast_text(d.forecast),
            rain_chance_pct=d.forecast.rain_chance if d.forecast else None,
            high=d.forecast.high if d.forecast else None,
            low=d.forecast.low if d.forecast else None,
        )
        for d in context.days
    ]


# Said of a loved idea when they asked for favourites, so the reply can say why it comes first.
LOVED = "loved last time"


def order_candidates(
    candidates: list[Candidate],
    by_id: dict[int, Idea],
    recently: set[int],
    *,
    prefer: str = "new",
    loved: frozenset[int] | set[int] = frozenset(),
) -> list[Candidate]:
    """Good first, then possible, then ruled out. Within each, recently suggested ideas sink for
    variety; then, for something new, never done first and the best rated; asked for favourites,
    the loved ones first (`loved`), then what they have done before, best rated first."""

    def key(c: Candidate) -> tuple:
        idea = by_id.get(c.idea_id)
        done_before = bool(idea and idea.times_done > 0)
        rating = idea.avg_rating if idea and idea.avg_rating is not None else 0.0
        if prefer == "favourites":
            liked: tuple = (c.idea_id not in loved, not done_before)
        else:
            liked = (done_before,)
        return (VERDICT_ORDER[c.verdict], c.idea_id in recently, *liked, -rating, c.idea_id)

    return sorted(candidates, key=key)


def choose(
    candidates: list[Candidate],
    by_id: dict[int, Idea],
    recently: set[int],
    *,
    prefer: str = "new",
    loved: frozenset[int] | set[int] = frozenset(),
) -> tuple[list[Candidate], int]:
    """What the model is shown, in order, and how many are held back. The recently suggested
    sink before the cut, so asking again brings others up."""

    def said(c: Candidate) -> list[str]:
        mark = prefer == "favourites" and c.idea_id in loved and c.verdict != "ruled_out"
        return ([LOVED] if mark else []) + c.reasons

    ordered = [
        c.model_copy(update={"reasons": said(c)[:MAX_REASONS]})
        for c in order_candidates(candidates, by_id, recently, prefer=prefer, loved=loved)
    ]
    offered = [c for c in ordered if c.verdict != "ruled_out"]
    rejected = [c for c in ordered if c.verdict == "ruled_out"]
    shown = offered[:MAX_OFFERED] + rejected[:MAX_RULED_OUT]
    return shown, len(ordered) - len(shown)


def compose(
    context: Context,
    label: str,
    shown: list[Candidate],
    held_back: int,
    finds: list[WebFind],
    skipped: list[str],
    suggestion_id: int | None,
) -> SuggestResult:
    start, end = context.window if context.window else (None, None)
    return SuggestResult(
        window=Window(
            start=start.isoformat() if start else None,
            end=end.isoformat() if end else None,
            label=label,
        ),
        days=day_summaries(context),
        candidates=shown,
        not_shown=held_back,
        web_finds=finds,
        skipped_checks=skipped,
        travel_from=context.origin.detail if context.origin else "home",
        suggestion={"id": suggestion_id} if suggestion_id is not None else None,
    )
