"""Telegram's HTML from the light Markdown models write (**bold**, *italics*, `code`,
[links](https://…)).

Only that small set becomes tags (headings bold, a bullet a bullet); everything else is escaped
so a message can never become markup of its own, and a link must be http or https. Telegram
refuses tags that do not nest, so a message whose marks cross is sent with its marks as written,
keeping code and links; if Telegram still refuses, the channel sends the plain words
(`channels/telegram.py`). Stored and page text stay as written.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable

# Stand-ins for what is already markup (code, a link's tags, a bare address whose underscores are
# not italics), so later marks cannot reach inside. Two private-use characters, taken out of what is
# sent first.
OPEN, SHUT = "\ue000", "\ue001"
KEPT = re.compile(f"{OPEN}(\\d+){SHUT}")
FENCE = re.compile(r"```[\w+-]*\n?(.*?)```", re.DOTALL)
CODE = re.compile(r"`([^`\n]+)`")
LINK = re.compile(f"\\[([^\\]\\n]+)\\]\\((https?://[^\\s(){OPEN}{SHUT}]+)\\)")
URL = re.compile(f"https?://[^\\s<>{OPEN}{SHUT}]+")
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
    kept: list[str] = []

    def keep(markup: str) -> str:
        kept.append(markup)
        return f"\ue000{len(kept) - 1}\ue001"

    def escaped(words: str) -> str:
        return html.escape(words, quote=False)

    def restored(markup: str) -> str:
        return KEPT.sub(lambda m: kept[int(m.group(1))], markup)

    text = text.replace(OPEN, "").replace(SHUT, "")
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
    if heading:
        marked, text = _bold_first_line(marked), _bold_first_line(text)
    drawn = restored(marked)
    return drawn if _nests(drawn) else restored(text)


def _bold_first_line(markup: str) -> str:
    first, newline, rest = markup.partition("\n")
    if first.strip() and not first.startswith("<b>"):
        return f"<b>{first}</b>{newline}{rest}"
    return markup


def _tagged(tag: str) -> Callable[[re.Match[str]], str]:
    return lambda found: f"<{tag}>{found.group(1)}</{tag}>"


def _nests(markup: str) -> bool:
    opened: list[str] = []
    for closing, name in TAG.findall(markup):
        if not closing:
            opened.append(name)
        elif not opened or opened.pop() != name:
            return False
    return not opened
