"""Plain colours for a browser without `light-dark()` (iOS and Safari before 17.5).

The looks write every colour that differs by day and night as `light-dark(day, night)`. A browser
that cannot read it throws the whole value away, and a button comes out white on white. This
writes `static/themes-fallback.css` from `themes.css` and the tokens at the top of `style.css`:
inside `@supports not (color: light-dark(...))`, each token that has a pair is given its day value
(or its night one, by the device's setting or the page's own `data-mode`), so a browser that
cannot do the pair gets what the one that can would have drawn. A browser that can ignores the
file. Run `uv run python -m familydb.web.fallback` after changing either source; a test holds the
file to what this makes.
"""

from __future__ import annotations

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent / "static"
SUPPORTS = "@supports not (color: light-dark(#000, #fff))"
HEADER = (
    "/* Written by familydb/web/fallback.py from themes.css and style.css: do not edit by hand.\n"
    "   Plain day and night colours for a browser without light-dark(). */\n"
)


def pick(value: str, night: bool) -> str:
    """The value with each `light-dark(day, night)` in it replaced by one side."""
    while (start := value.find("light-dark(")) != -1:
        inside = start + len("light-dark(")
        depth, split, end = 0, None, None
        for at in range(inside, len(value)):
            char = value[at]
            depth += (char == "(") - (char == ")")
            if char == "," and depth == 0 and split is None:
                split = at
            if depth < 0:
                end = at
                break
        assert split is not None and end is not None, value
        side = value[split + 1 : end] if night else value[inside:split]
        value = value[:start] + side.strip() + value[end + 1 :]
    return value


def _block(css: str, selector: str) -> str:
    """The body of the first `selector { ... }` rule (balanced braces)."""
    start = css.index(selector + " {") + len(selector) + 2
    depth = 1
    for at in range(start, len(css)):
        depth += (css[at] == "{") - (css[at] == "}")
        if depth == 0:
            return css[start:at]
    raise ValueError(selector)


def _tokens(body: str) -> dict[str, str]:
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    return {
        name: value.strip() for name, value in re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", body)
    }


def _rules(selector: str, tokens: dict[str, str]) -> str:
    """A selector's tokens by day, then by night when the device is set so, then by night when
    the page was told so. `:where()` keeps the specificity of the rules this stands in for."""

    def block(head: str, night: bool, indent: str) -> str:
        lines = "".join(f"\n{indent}  {n}: {pick(v, night)};" for n, v in tokens.items())
        return f"{indent}{head} {{{lines}\n{indent}}}\n"

    auto = f'{selector}:where(:not([data-mode="light"]))'
    return (
        block(selector, False, "  ")
        + "  @media (prefers-color-scheme: dark) {\n"
        + block(auto, True, "    ")
        + "  }\n"
        + block(f'{selector}:where([data-mode="dark"])', True, "  ")
    )


def _night(selector: str, tokens: dict[str, str]) -> str:
    night = "".join(f"\n    {n}: {pick(v, True)};" for n, v in tokens.items())
    return f"  {selector} {{{night}\n  }}\n" if tokens else ""


def build(themes: str, style: str) -> str:
    """The fallback file's text."""
    out = [HEADER, SUPPORTS, " {\n"]
    root = _tokens(_block(style, ":root"))
    paired = {n: v for n, v in root.items() if "light-dark(" in v}
    if paired:
        out.append(_rules(":root", paired))
    shared = _tokens(_block(themes, "[data-theme]"))
    shared_paired = {n: v for n, v in shared.items() if "light-dark(" in v}
    out.append(_rules("[data-theme]", shared_paired))
    for key in re.findall(r'^\[data-theme="([a-z]+)"\] \{', themes, re.M):
        look = _tokens(_block(themes, f'[data-theme="{key}"]'))
        wanted = {n: v for n, v in look.items() if "light-dark(" in v or n in shared_paired}
        if any("light-dark(" in v for v in wanted.values()):
            out.append(_rules(f'[data-theme="{key}"]', wanted))
        elif "color-scheme: dark" in _block(themes, f'[data-theme="{key}"]'):
            # A look with no day (a green screen): the shared and brand pairs are always night.
            out.append(_night(f':root[data-theme="{key}"]', paired))
            out.append(_night(f'[data-theme="{key}"]', shared_paired))
    out.append("}\n")
    return "".join(out)


def written() -> str:
    return build(
        (STATIC / "themes.css").read_text("utf-8"), (STATIC / "style.css").read_text("utf-8")
    )


if __name__ == "__main__":
    (STATIC / "themes-fallback.css").write_text(written(), "utf-8")
