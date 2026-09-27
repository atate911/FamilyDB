"""Speaking instead of typing on the page (static/dictate.js): a mic beside each box that takes
words, from the browser's own speech recognition, which the family may turn off."""

from __future__ import annotations

import re
from pathlib import Path

from familydb.app import App
from familydb.web import create_app

SCRIPT = Path(__file__).resolve().parents[1] / "src/familydb/web/static/dictate.js"


def _page(settings, clock, path: str) -> str:
    return create_app(App(settings, clock)).test_client().get(path).text


def test_the_boxes_that_take_words_offer_a_mic(settings, clock, conn, family) -> None:
    home = _page(settings, clock, "/")
    assert 'src="/static/dictate.js' in home
    # The message box's mic goes beside Send; the others beside their own box.
    assert 'data-dictate="ask-mic"' in home and 'id="ask-mic"' in home
    for path in ("/chat", "/tasks", "/ideas", "/ideas/new"):
        assert re.search(r"<(textarea|input)[^>]*data-dictate", _page(settings, clock, path)), path


def test_turned_off_there_is_no_mic(settings, clock, conn, family) -> None:
    off = settings.model_copy(update={"web_dictation": False})
    assert "dictate.js" not in _page(off, clock, "/")


def test_nothing_but_the_browser_hears_it() -> None:
    """No model, no FamilyDB address: the script sends nothing anywhere, and sends no form."""
    script = SCRIPT.read_text()
    for never in ("fetch(", "XMLHttpRequest", "sendBeacon", ".submit(", "requestSubmit"):
        assert never not in script, never
    assert "SpeechRecognition" in script
