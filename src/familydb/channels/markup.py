"""Telegram's HTML from what is sent there: the light Markdown models write, drawn as formatting.

Models write **bold**, *italics*, `code` and [links](https://…) whatever they are asked, and
Telegram shows plain text as it is, asterisks and all. Sent as HTML, Telegram draws them. Only
that small set becomes tags, with headings drawn bold and a bullet as a bullet; everything else is
escaped, so nothing a message says can become markup of its own, and a link has to be http or
https. The words stored and shown on the page stay as they were written.

Telegram refuses HTML whose tags do not nest. Crossed marks (**bold *and** italic*) would make
such tags, so a message whose marks cross is sent with its marks as they are written, keeping
its code and links; and should Telegram refuse one all the same, the channel sends the words as
they are (`channels/telegram.py`), so a message is never lost to its formatting.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable

# Stand-ins for what is already markup, so the marks after cannot reach inside it: code, a link's
# tags and a bare address, whose underscores are not italics.
KEPT = re.compile("\ue000(\\d+)\ue001")
FENCE = re.compile(r"```[\w+-]*\n?(.*?)```", re.DOTALL)
CODE = re.compile(r"`([^`\n]+)`")
LINK = re.compile(r"\[([^\]\n]+)\]\((https?://[^\s()]+)\)")
URL = re.compile(r"https?://[^\s<>]+")
TAG = re.compile(r"<(/?)(\w+)[^>]*>")
HEADING = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t#]*$", re.MULTILINE)
BULLET = re.compile(r"^([ \t]*)[*-][ \t]+(?=\S)", re.MULTILINE)
MARKS = (
    (re.compile(r"\*\*(?!\s)(.+?)(?<!\s)\*\*"), "b"),
    (re.compile(r"(?<!\w)__(?!\s)(.+?)(?<!\s)__(?!\w)"), "b"),
    (re.compile(r"~~(?!\s)(.+?)(?<!\s)~~"), "s"),
    (re.compile(r"(?<![\w*])\*(?![\s*])(.+?)(?<![\s*])\*(?![\w*])"), "i"),
    (re.compile(r"(?<![\w_])_(?![\s_])(.+?)(?<![\s_])_(?![\w_])"), "i"),
)


def to_html(text: str, *, heading: bool = False) -> str:
    """The words as Telegram HTML, `heading` drawing the first line bold (a command's answer)."""
    kept: list[str] = []

    def keep(markup: str) -> str:
        kept.append(markup)
        return f"\ue000{len(kept) - 1}\ue001"

    def escaped(words: str) -> str:
        return html.escape(words, quote=False)

    text = FENCE.sub(lambda m: keep(f"<pre>{escaped(m.group(1).strip(chr(10)))}</pre>"), text)
    text = CODE.sub(lambda m: keep(f"<code>{escaped(m.group(1))}</code>"), text)
    text = LINK.sub(
        lambda m: keep(f'<a href="{html.escape(m.group(2))}">') + m.group(1) + keep("</a>"), text
    )
    text = URL.sub(lambda m: keep(escaped(m.group(0))), text)
    text = BULLET.sub("\\1• ", HEADING.sub(r"<b>\1</b>", escaped(text)))
    marked = text
    for mark, tag in MARKS:
        marked = mark.sub(_tagged(tag), marked)
    if _nests(marked):
        text = marked
    if heading:
        first, newline, rest = text.partition("\n")
        if first.strip() and not first.startswith("<b>"):
            text = f"<b>{first}</b>{newline}{rest}"
    return KEPT.sub(lambda m: kept[int(m.group(1))], text)


def _tagged(tag: str) -> Callable[[re.Match[str]], str]:
    return lambda found: f"<{tag}>{found.group(1)}</{tag}>"


def _nests(markup: str) -> bool:
    """Whether every tag in it closes in the order it opened, as Telegram insists."""
    opened: list[str] = []
    for closing, name in TAG.findall(markup):
        if not closing:
            opened.append(name)
        elif not opened or opened.pop() != name:
            return False
    return not opened
