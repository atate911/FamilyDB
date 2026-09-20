"""Stage: order the verdicts and summarise the days for the model."""

from __future__ import annotations

from familydb.integrations.open_meteo import DayForecast
from familydb.store.ideas import Idea
from familydb.suggest.types import Candidate, Context, DaySummary, SuggestResult, WebFind, Window

MAX_REASONS = 3
VERDICT_ORDER = {"good": 0, "possible": 1, "ruled_out": 2}
# The reply names three to five options and a few of the ideas that did not fit. Everything past
# that is tokens the model pays for twice and never uses, so it is counted rather than listed.
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
    return ", ".join(parts)


def day_summaries(context: Context) -> list[DaySummary]:
    return [
        DaySummary(
            date=d.date.isoformat(),
            weekday=d.date.strftime("%A"),
            free=list(d.free),
            free_known=d.free_known,
            forecast=_forecast_text(d.forecast),
            rain_chance_pct=d.forecast.rain_chance if d.forecast else None,
            high=d.forecast.high if d.forecast else None,
            low=d.forecast.low if d.forecast else None,
        )
        for d in context.days
    ]


def order_candidates(
    candidates: list[Candidate], by_id: dict[int, Idea], recently: set[int]
) -> list[Candidate]:
    """Good first (never done, then best rated), then possible, then ruled out.

    Ideas suggested recently sink to the end of their group so the family sees variety.
    """

    def key(c: Candidate) -> tuple:
        idea = by_id.get(c.idea_id)
        times_done = idea.times_done if idea else 0
        rating = idea.avg_rating if idea and idea.avg_rating is not None else 0.0
        return (
            VERDICT_ORDER[c.verdict],
            c.idea_id in recently,
            times_done > 0,
            -rating,
            c.idea_id,
        )

    return sorted(candidates, key=key)


def compose(
    context: Context,
    label: str,
    candidates: list[Candidate],
    finds: list[WebFind],
    skipped: list[str],
    by_id: dict[int, Idea],
    recently: set[int],
    suggestion_id: int | None,
) -> SuggestResult:
    ordered = [
        c.model_copy(update={"reasons": c.reasons[:MAX_REASONS]})
        for c in order_candidates(candidates, by_id, recently)
    ]
    offered = [c for c in ordered if c.verdict != "ruled_out"]
    rejected = [c for c in ordered if c.verdict == "ruled_out"]
    shown = offered[:MAX_OFFERED] + rejected[:MAX_RULED_OUT]
    held_back = (len(offered) - len(offered[:MAX_OFFERED])) + (
        len(rejected) - len(rejected[:MAX_RULED_OUT])
    )
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
        suggestion={"id": suggestion_id} if suggestion_id is not None else None,
    )
