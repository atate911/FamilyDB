"""Deterministic text rendering. The idea list and family context are in the cached prefix, so
nothing in them may vary with time or sender; what does vary is rendered for the current user
turn only."""

from __future__ import annotations

import json
from typing import Any

from familydb.availability import calendar_available, weather_available, web_tools_available
from familydb.clock import Clock
from familydb.config import Settings
from familydb.memory import Chosen, line_of
from familydb.routing import CONFIRMED
from familydb.store.ideas import Idea, ages_text
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
    """When a dated idea is on, as stored ("on 2026-11-18T20:00"); never relative to today."""
    first, last = idea.happens_from, idea.happens_until
    if not first:
        return None
    if last is None:
        return f"from {first}"
    if last == first[:10]:
        return f"on {first}"
    return f"on {first} to {last}"


def render_idea_line(idea: Idea) -> str:
    """One compact line per idea, as the model sees it."""
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
    if ages := ages_text(idea):
        parts.append(ages)
    parts.append(f"status: {idea.status}")
    parts.append(f"by {idea.suggested_by_name or 'unknown'} {idea.created_at[:10]}")
    if idea.times_done:
        done = f"done {idea.times_done}x, last {idea.last_done_at}"
        if idea.avg_rating is not None:
            done += f", rating {idea.avg_rating:g}/10"
        parts.append(done)
    # Lookup state is left out: it flips after every new idea and would rewrite the cached prefix.
    return " | ".join(parts)


def render_idea_list(ideas: list[Idea]) -> str:
    if not ideas:
        return "(no ideas yet)"
    return "\n".join(render_idea_line(idea) for idea in ideas)


def render_family_context(family: list[Member], settings: Settings) -> str:
    """The stable family block (cached): no dates, no sender."""
    lines = ["Family:"]
    for member in family:
        if member.active:
            lines.append(f"- {member.display_name} ({member.role})")
    if len(lines) == 1:
        lines.append("- (no members configured yet)")
    about = settings.about_family.strip()
    if about:
        lines.append(f"About the family, in their words:\n{about}")
    lines.append(f"Home area: {settings.home_area or 'not set'}")
    lines.append(f"Timezone: {settings.tz}")
    calendar = "connected" if calendar_available(settings) else "not connected (plans kept here)"
    weather = "configured" if weather_available(settings) else "not configured"
    web = "available" if web_tools_available(settings) else "not available"
    lines.append(f"Calendar: {calendar}. Weather: {weather}. Web tools: {web}.")
    return "\n".join(lines)


def render_audience_line(channel: str, chat_id: str, family: list[Member]) -> str | None:
    """Who else reads the reply, for the current turn only; None for a private chat. A Telegram
    group's chat id is negative; kids are read from the family list. In a group, a bare
    `CONFIRMED` is shown as a reaction."""
    if channel == "web" and chat_id == "web":
        line = "This is the family's conversation on the page: everyone who signs in reads it"
    elif channel == "telegram" and chat_id.startswith("-"):
        line = "This is the family's group chat: everyone in it reads your reply"
    else:
        return None
    if any(member.active and member.role == "kid" for member in family):
        line += ", kids among them"
    if channel == "telegram":
        line += (
            f". When you have only saved what was asked and have nothing to add, reply with "
            f"just {CONFIRMED}"
        )
    return line + "."


def render_user_turn(
    sender: str, text: str, clock: Clock, audience: str | None = None
) -> list[str]:
    """The current message in parts (date, audience, text), kept separate so the volatile date
    never merges into the message."""
    parts = [f"Today is {clock.describe()}."]
    if audience:
        parts.append(audience)
    return [*parts, f"[{sender}] {text}"]


# At most this many of a kid's wish topics go with her message: the locked ones first.
KID_TOPICS = 12
PRONOUN = {"female": "Her", "male": "His"}


def render_kid_line(
    name: str,
    age: int | None,
    gender: str | None,
    topics: list[tuple[str, str | None]] | None,
    wording: str | None,
) -> str:
    """Who a kid is and where her wishes stand (docs/WISHES.md), for the current turn only;
    topics are None where anybody else reads the reply."""
    who = {"female": "a girl", "male": "a boy"}.get(gender or "", "a kid")
    line = f"{name} is {who}" + (f", {age}" if age is not None else "") + "."
    if topics:
        shown = [
            f"{topic} (locked to {until[:10]})" if until else topic
            for topic, until in topics[:KID_TOPICS]
        ]
        line += f" {PRONOUN.get(gender or '', 'Their')} wish topics: {', '.join(shown)}."
    if wording:
        line += f" Wording: {wording}."
    return line


def render_location_line(
    sender: str, label: str | None, lat: float, lon: float, minutes_ago: int
) -> str:
    """Where the sender's phone last said they were, for the current turn only."""
    where = f"{label} " if label else ""
    return (
        f"{sender}'s location, from their phone {minutes_ago} min ago: {where}"
        f'({lat:.4f}, {lon:.4f}). For "near here" or "open now", suggest uses it.'
    )


def render_memories(chosen: Chosen) -> str | None:
    """What the family told the bot that goes with this message (familydb/memory.py); per turn."""
    if not chosen.memories:
        return None
    lines = ["What the family has told you about itself (m numbers are for remember):"]
    lines += [line_of(memory) for memory in chosen.memories]
    if chosen.left_out:
        lines.append(f"({chosen.left_out} more, on other things.)")
    return "\n".join(lines)


def render_folded_line(lines: list[str]) -> str:
    """Messages that came due while they were talking, for the reply to carry."""
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
