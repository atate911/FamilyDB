"""Deterministic text rendering shared by the prompt builder and the CLI.

Nothing here may depend on the current time or on who is asking: the idea list is part of the
cached prompt prefix, and any variation defeats the cache.
"""

from __future__ import annotations

from typing import Any

from familydb.availability import calendar_available, weather_available, web_tools_available
from familydb.clock import Clock
from familydb.config import Settings
from familydb.store.ideas import Idea
from familydb.store.members import Member


def _fmt_minutes(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes / 60:g} h"


def _duration(idea: Idea) -> str | None:
    low, high = idea.duration_min, idea.duration_max
    if low is not None and high is not None and low != high:
        return f"{_fmt_minutes(low)} to {_fmt_minutes(high)}"
    if low is not None or high is not None:
        return f"about {_fmt_minutes(low if low is not None else high or 0)}"
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


def render_family_context(family: list[Member], settings: Settings) -> str:
    """The stable family block: who, where, which integrations exist. No dates, no sender."""
    lines = ["Family:"]
    for member in family:
        if not member.active:
            continue
        if member.role == "kid":
            lines.append(f"- {member.display_name} (kid, does not message the bot)")
        else:
            lines.append(f"- {member.display_name} ({member.role})")
    if len(lines) == 1:
        lines.append("- (no members configured yet)")
    lines.append(f"Home area: {settings.home_area or 'not set'}")
    lines.append(f"Timezone: {settings.tz}")
    calendar = "connected" if calendar_available(settings) else "not connected"
    weather = "configured" if weather_available(settings) else "not configured"
    web = "available" if web_tools_available(settings) else "not available"
    lines.append(f"Calendar: {calendar}. Weather: {weather}. Web tools: {web}.")
    return "\n".join(lines)


def render_user_turn(sender: str, text: str, clock: Clock) -> list[dict[str, Any]]:
    """The current message as content blocks: the date line, then the sender-prefixed text."""
    return [
        {"type": "text", "text": f"Today is {clock.describe()}."},
        {"type": "text", "text": f"[{sender}] {text}"},
    ]


def render_history_line(sender: str, text: str) -> str:
    return f"[{sender}] {text}"
