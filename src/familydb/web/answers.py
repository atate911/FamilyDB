"""Where every family page is drawn: a page's view builds what it shows and hands it to `answer`.
One place, so anything that must hold for every family page holds here."""

from __future__ import annotations

from typing import Any

from flask import render_template


def answer(template: str, **context: Any) -> str:
    """The page, drawn from its view-model."""
    return render_template(template, **context)
