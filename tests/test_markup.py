"""Telegram's HTML from what is sent there (channels/markup.py), and falling back to the words."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from telegram.error import BadRequest

from familydb.channels.markup import to_html
from familydb.channels.telegram import formatted


@pytest.mark.parametrize(
    ("written", "drawn"),
    [
        ("**Hopscotch** is open until 18:00", "<b>Hopscotch</b> is open until 18:00"),
        ("Try *Ramen Ichiban*, or _the falls_.", "Try <i>Ramen Ichiban</i>, or <i>the falls</i>."),
        ("__bold__ and ~~gone~~", "<b>bold</b> and <s>gone</s>"),
        ("Say `#42` to me", "Say <code>#42</code> to me"),
        ("```\nlist <all>\n```", "<pre>list &lt;all&gt;</pre>"),
        ("## Saturday\nthe hike", "<b>Saturday</b>\nthe hike"),
        ("- one\n* two\n  - three", "• one\n• two\n  • three"),
        (
            "Book at [their site](https://example.com/a_b?x=1&y=2).",
            'Book at <a href="https://example.com/a_b?x=1&amp;y=2">their site</a>.',
        ),
        (
            "[**Hopscotch**](https://example.com/pdx)",
            '<a href="https://example.com/pdx"><b>Hopscotch</b></a>',
        ),
        # What only looks like marks is left as it is: words, sums, and addresses.
        ("snake_case_name and file_name.txt", "snake_case_name and file_name.txt"),
        ("5 * 3 * 2 = 30", "5 * 3 * 2 = 30"),
        ("see https://x.com/_a_/b_c_ now", "see https://x.com/_a_/b_c_ now"),
        ("**not closed", "**not closed"),
        ("Reminder: bins out (Sam). Task #12.", "Reminder: bins out (Sam). Task #12."),
    ],
)
def test_the_marks_models_write_are_drawn(written: str, drawn: str) -> None:
    assert to_html(written) == drawn


def test_nothing_said_can_become_markup_of_its_own() -> None:
    assert to_html("a < b & <b>c</b>") == "a &lt; b &amp; &lt;b&gt;c&lt;/b&gt;"
    assert to_html("[x](javascript:alert(1))") == "[x](javascript:alert(1))"
    assert to_html('[x](https://e.com/"onmouseover=")') == (
        '<a href="https://e.com/&quot;onmouseover=&quot;">x</a>'
    )


def test_crossed_marks_are_left_as_written_rather_than_refused() -> None:
    """Telegram refuses tags that do not nest, so crossed marks are not drawn at all; code and
    links still are."""
    assert to_html("**bold *crossed** italic*") == "**bold *crossed** italic*"
    assert to_html("**a *b** c* `d`") == "**a *b** c* <code>d</code>"


def test_a_heading_is_drawn_bold() -> None:
    assert to_html("Here's today:\n10:00 Soccer", heading=True) == (
        "<b>Here's today:</b>\n10:00 Soccer"
    )
    assert to_html("## Already\nx", heading=True) == "<b>Already</b>\nx"


class Sends:
    """Stands in for a send: refuses HTML with `refusal`, once, then takes anything."""

    def __init__(self, refusal: str | None = None) -> None:
        self.sent: list[tuple[str, dict[str, Any]]] = []
        self.refusal = refusal

    async def __call__(self, text: str, **extra: Any) -> None:
        if self.refusal and extra.get("parse_mode"):
            refusal, self.refusal = self.refusal, None
            raise BadRequest(refusal)
        self.sent.append((text, extra))


def test_it_goes_as_html_and_as_the_words_when_telegram_refuses_the_formatting() -> None:
    fine = Sends()
    asyncio.run(formatted(fine, "**Done** ✓", reply_markup="buttons"))
    assert fine.sent == [("<b>Done</b> ✓", {"parse_mode": "HTML", "reply_markup": "buttons"})]
    refused = Sends("Can't parse entities: unexpected end tag at byte offset 12")
    asyncio.run(formatted(refused, "**Done** ✓", reply_markup="buttons"))
    assert refused.sent == [("**Done** ✓", {"reply_markup": "buttons"})]


def test_any_other_refusal_is_not_hidden_by_sending_again() -> None:
    """A chat that is gone is gone however it is written; delivery keeps it for another try."""
    gone = Sends("Chat not found")
    with pytest.raises(BadRequest):
        asyncio.run(formatted(gone, "hello"))
    assert gone.sent == []
