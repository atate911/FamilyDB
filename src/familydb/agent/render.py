"""Deterministic text rendering shared by the prompt builder and the CLI.

Nothing here may depend on the current time or on who is asking: the idea list is part of the
cached prompt prefix, and any variation defeats the cache.
"""

from __future__ import annotations

import json
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


def render_dates(idea: Idea) -> str | None:
    """When a dated idea is on, as stored: "on 2026-11-18T20:00", "on 2026-10-01 to 2026-10-31",
    "from 2026-10-01". None for an idea tied to no date. Never relative to today: the idea list
    is cached."""
    first, last = idea.happens_from, idea.happens_until
    if not first:
        return None
    if last is None:
        return f"from {first}"
    if last == first[:10]:
        return f"on {first}"
    return f"on {first} to {last}"


def render_idea_line(idea: Idea) -> str:
    """One compact line per idea, exactly what the model sees in its context."""
    parts = [f"#{idea.id}", f"[{idea.kind}]", idea.title]
    if idea.location_name:
        parts.append(f"at {idea.location_name}")
    dates = render_dates(idea)
    if dates:
        parts.append(dates)
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
    # Not whether its details have been looked up: that flips a minute after every new idea and
    # would make the next message write the cached prefix again. describe_idea says it.
    return " | ".join(parts)


def render_idea_list(ideas: list[Idea]) -> str:
    if not ideas:
        return "(no ideas yet)"
    return "\n".join(render_idea_line(idea) for idea in ideas)


def render_family_context(family: list[Member], settings: Settings) -> str:
    """The stable family block: who, where, which integrations exist. No dates, no sender."""
    lines = ["Family:"]
    for member in family:
        if member.active:
            lines.append(f"- {member.display_name} ({member.role})")
    if len(lines) == 1:
        lines.append("- (no members configured yet)")
    about = settings.about_family.strip()
    if about:
        # In their own words, from the Personality page. Stable, so it belongs in the prefix.
        lines.append(f"About the family, in their words:\n{about}")
    lines.append(f"Home area: {settings.home_area or 'not set'}")
    lines.append(f"Timezone: {settings.tz}")
    calendar = "connected" if calendar_available(settings) else "not connected"
    weather = "configured" if weather_available(settings) else "not configured"
    web = "available" if web_tools_available(settings) else "not available"
    lines.append(f"Calendar: {calendar}. Weather: {weather}. Web tools: {web}.")
    return "\n".join(lines)


def render_user_turn(sender: str, text: str, clock: Clock) -> list[str]:
    """The current message in parts: the date line, then the sender-prefixed text.

    They stay separate so the volatile date never merges into the message itself.
    """
    return [f"Today is {clock.describe()}.", f"[{sender}] {text}"]


def render_location_line(
    sender: str, label: str | None, lat: float, lon: float, minutes_ago: int
) -> str:
    """Where the sender's phone last said they were, for the current turn only: it changes."""
    where = f"{label} " if label else ""
    return (
        f"{sender}'s location, from their phone {minutes_ago} min ago: {where}"
        f'({lat:.4f}, {lon:.4f}). For "near here" or "open now", suggest uses it.'
    )


def render_folded_line(lines: list[str]) -> str:
    """Messages that came due in this chat while they were talking, for the reply to carry."""
    return (
        "Also due in this chat just now; mention each in your reply, briefly and in your own "
        "words, keeping its number:\n" + "\n".join(f"- {line}" for line in lines)
    )


def render_history_line(sender: str, text: str) -> str:
    return f"[{sender}] {text}"


def _record_ref(output: Any) -> str:
    if not isinstance(output, dict):
        return ""
    if "duplicate_of" in output:
        return f" (already existed as #{output['duplicate_of']})"
    if isinstance(output.get("id"), int):
        return f" (#{output['id']})"
    plan = output.get("plan")
    if isinstance(plan, dict) and "id" in plan:
        return f" (plan #{plan['id']})"
    return ""


def render_retry_note(prior_calls: list[dict[str, Any]], write_tools: set[str]) -> str | None:
    """For a retried message: which write tools already ran, so the model does not repeat them."""
    done: list[str] = []
    for call in prior_calls:
        if call.get("is_error") or call.get("tool_name") not in write_tools:
            continue
        try:
            output = json.loads(call["output"]) if call.get("output") else {}
        except ValueError:
            output = {}
        if isinstance(output, dict) and output.get("available") is False:
            continue
        done.append(f"{call['tool_name']}{_record_ref(output)}")
    if not done:
        return None
    return (
        "This message was processed before but the reply failed. These tool calls already "
        "succeeded and must not be repeated: " + "; ".join(done) + ". Continue from there and "
        "answer as if this were the first reply."
    )
