"""Deterministic text rendering shared by the prompt builder and the CLI.

Nothing here may depend on the current time or on who is asking: the idea list is part of the
cached prompt prefix, and any variation defeats the cache.
"""

from __future__ import annotations

from familydb.store.ideas import Idea


def _fmt_minutes(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes / 60:g} h"


def _duration(idea: Idea) -> str | None:
    low, high = idea.duration_min, idea.duration_max
    if low and high and low != high:
        return f"{_fmt_minutes(low)} to {_fmt_minutes(high)}"
    if low or high:
        return f"about {_fmt_minutes(low or high or 0)}"
    return None


def render_idea_line(idea: Idea) -> str:
    """One compact line per idea, exactly what the model sees in its context."""
    parts = [f"#{idea.id}", f"[{idea.kind}]", idea.title]
    if idea.location_name:
        parts.append(f"at {idea.location_name}")
    parts.append(f"for: {', '.join(idea.participants) if idea.participants else 'anyone'}")
    if idea.tags:
        parts.append(f"tags: {', '.join(idea.tags)}")
    parts.append(f"{idea.setting}/{idea.weather}")
    if idea.seasons:
        parts.append(f"seasons: {', '.join(idea.seasons)}")
    duration = _duration(idea)
    if duration:
        parts.append(duration)
    if idea.cost_level is not None:
        parts.append("free" if idea.cost_level == 0 else "cost: " + "$" * idea.cost_level)
    if idea.needs_booking:
        parts.append("needs booking")
    parts.append(f"status: {idea.status}")
    parts.append(f"by {idea.suggested_by_name or 'unknown'} {idea.created_at[:10]}")
    if idea.times_done:
        done = f"done {idea.times_done}x, last {idea.last_done_at}"
        if idea.avg_rating is not None:
            done += f", rating {idea.avg_rating:g}/10"
        parts.append(done)
    parts.append(f"details: {idea.enrichment}")
    return " | ".join(parts)


def render_idea_list(ideas: list[Idea]) -> str:
    if not ideas:
        return "(no ideas yet)"
    return "\n".join(render_idea_line(idea) for idea in ideas)
