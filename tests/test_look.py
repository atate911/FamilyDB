"""The Look page: which of the page's looks a browser wears, kept in a cookie."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import familydb.web as package
from familydb.app import App
from familydb.web import create_app, looks

PASSWORD = "open sesame please"
STATIC = Path(package.__file__).parent / "static"


@pytest.fixture
def page(settings, clock, conn, family):
    app = App(settings.model_copy(update={"web_password": PASSWORD}), clock)
    client = create_app(app).test_client()
    assert client.post("/login", data={"password": PASSWORD}).status_code == 302
    return client


def _token(client, path: str = "/look") -> str:
    found = re.search(r'name="csrf" value="([^"]+)"', client.get(path).text)
    assert found is not None
    return found.group(1)


def _cookies(response) -> str:
    return " ".join(response.headers.getlist("Set-Cookie"))


def _wearing(client) -> tuple[str, str | None]:
    html = re.search(r"<html[^>]*>", client.get("/").text)
    assert html is not None
    theme = re.search(r'data-theme="([^"]+)"', html.group(0))
    mode = re.search(r'data-mode="([^"]+)"', html.group(0))
    return (theme.group(1) if theme else ""), (mode.group(1) if mode else None)


def test_the_page_is_kitchen_table_and_follows_the_device_until_somebody_chooses(page) -> None:
    assert _wearing(page) == ("kitchen", None)
    head = page.get("/").text
    assert '<meta name="color-scheme" content="light dark" />' in head
    assert 'media="(prefers-color-scheme: light)"' in head and 'content="#EFE7D7"' in head
    assert 'media="(prefers-color-scheme: dark)"' in head and 'content="#121816"' in head
    assert "The default" in page.get("/look").text


def test_the_look_page_offers_every_look_in_its_own_colours(page) -> None:
    text = page.get("/look").text
    for one in looks.LOOKS:
        assert one.name in text and f'value="{one.key}"' in text
        assert f'class="look-sample" data-theme="{one.key}"' in text  # a sample drawn in it
    assert 'name="mode"' in text and "Match my device" in text
    assert 'href="/look"' in page.get("/plans").text  # and the bar's menu reaches it
    # Phosphor has no day, so it is drawn once; the others twice.
    assert text.count('class="look-sample" data-theme="phosphor"') == 1
    assert text.count('class="look-sample" data-theme="rail"') == 2


def test_choosing_a_look_keeps_it_in_this_browser(page) -> None:
    sent = page.post("/look", data={"csrf": _token(page), "theme": "rail", "mode": "dark"})
    assert sent.status_code == 302 and sent.headers["Location"] == "/look"
    cookie = sent.headers["Set-Cookie"]
    assert "fdb_look=rail.dark" in cookie and "HttpOnly" in cookie and "SameSite=Lax" in cookie
    assert "Saved. This browser wears Rail yellow from now on." in page.get("/look").text
    assert _wearing(page) == ("rail", "dark")
    head = page.get("/").text
    assert '<meta name="color-scheme" content="dark" />' in head
    assert 'content="#13336F"' in head  # the browser's own bar is the night panel

    page.post("/look", data={"csrf": _token(page), "theme": "fjord", "mode": "auto"})
    assert _wearing(page) == ("fjord", None)
    head = page.get("/").text
    assert '<meta name="color-scheme" content="light dark" />' in head
    assert 'media="(prefers-color-scheme: light)"' in head and 'content="#252B4A"' in head


def test_kitchen_table_can_be_chosen_and_worn(page) -> None:
    sent = page.post("/look", data={"csrf": _token(page), "theme": "kitchen", "mode": "light"})
    assert "fdb_look=kitchen.light" in sent.headers["Set-Cookie"]
    assert _wearing(page) == ("kitchen", "light")
    head = page.get("/").text
    assert '<meta name="color-scheme" content="light" />' in head
    assert 'content="#EFE7D7"' in head  # the browser's own bar is the cream panel
    assert page.get("/look").text.count('class="look-sample" data-theme="kitchen"') == 2


def test_phosphor_has_no_day_to_choose(page) -> None:
    page.post("/look", data={"csrf": _token(page), "theme": "phosphor", "mode": "light"})
    assert _wearing(page) == ("phosphor", None)


@pytest.mark.parametrize(
    "form",
    [
        {"theme": "plaid", "mode": "auto"},
        {"theme": "rail", "mode": "sepia"},
        {"theme": "<script>", "mode": "auto"},
        {"mode": "auto"},
    ],
)
def test_nothing_but_a_look_this_page_has_is_kept(page, form) -> None:
    sent = page.post("/look", data={"csrf": _token(page), **form})
    assert looks.COOKIE not in _cookies(sent)
    assert "not one of the looks" in page.get("/look").text  # said once, where it was asked
    assert _wearing(page) == ("kitchen", None)


def test_a_cookie_that_names_no_look_is_the_default(page) -> None:
    for value in ("", "plaid.auto", "rail", "rail.sepia", '"><script>.auto', "rail.dark.extra"):
        page.set_cookie(looks.COOKIE, value)
        theme, mode = _wearing(page)
        assert "<script>" not in page.get("/").text.split("<body")[0]
        assert (theme, mode) == ("kitchen", None) or value == "rail.dark.extra"


def test_a_form_from_another_site_does_not_change_the_look(page) -> None:
    elsewhere = {"Origin": "https://evil.example"}
    token = _token(page)
    sent = page.post(
        "/look", data={"csrf": token, "theme": "ink", "mode": "dark"}, headers=elsewhere
    )
    assert looks.COOKIE not in _cookies(sent)
    sent = page.post("/look", data={"csrf": "not-this-session", "theme": "ink", "mode": "dark"})
    assert looks.COOKIE not in _cookies(sent)
    assert _wearing(page) == ("kitchen", None)


def test_the_look_is_for_anybody_signed_in_and_nobody_else(settings, clock, conn, family) -> None:
    app = App(settings.model_copy(update={"web_password": PASSWORD}), clock)
    client = create_app(app).test_client()
    assert client.get("/look").status_code == 302  # to sign in
    assert client.post("/look", data={"theme": "ink", "mode": "dark"}).status_code == 401


def test_every_look_is_written_down_once_in_the_stylesheets() -> None:
    """The catalogue and themes.css list the same looks: each has a block with the same tokens as
    every other, and the colour the browser is told its bar is (`looks.Look.band`) is the panel
    the stylesheet draws.
    """
    themes = (STATIC / "themes.css").read_text("utf-8")
    blocks = dict(re.findall(r'\[data-theme="([a-z]+)"\] \{(.*?)\n\}', themes, re.S))
    assert set(blocks) == {one.key for one in looks.LOOKS}

    def tokens(body: str) -> set[str]:
        return set(re.findall(r"^\s+(--[a-z0-9-]+):", body, re.M))

    # The roles Kitchen Table's layout reads that the built set lacks sit in one block every look
    # shares (`[data-theme]`), worked out from its own tokens; a look may name one to set itself
    # apart, so they are left out of the comparison. The block comes first, so a look's own wins.
    shared = set(_shared(themes))
    assert themes.index("\n[data-theme] {") < themes.index('\n[data-theme="')
    # The page reads these two with a fallback: a value for every look would change a page that
    # does without.
    assert "--here-icon" not in shared
    ignored = shared
    first = tokens(next(iter(blocks.values()))) - ignored
    for key, body in blocks.items():
        assert tokens(body) - ignored == first, f"{key}: {(tokens(body) - ignored) ^ first}"
    for one in looks.LOOKS:
        if not one.has_day:  # a green screen: one value for each token, always night
            assert "color-scheme: dark" in blocks[one.key], one.key
            assert "light-dark(" not in blocks[one.key], one.key
            continue
        found = re.search(
            r"--band: (?:light-dark\((#[0-9A-Fa-f]{6}), (#[0-9A-Fa-f]{6})\)|(#[0-9A-Fa-f]{6}));",
            blocks[one.key],
        )
        assert found, one.key
        day, night = (found[1], found[2]) if found[1] else (found[3], found[3])
        assert (day.upper(), night.upper()) == (one.band[0].upper(), one.band[1].upper()), one.key
        assert "color-scheme: light dark" in blocks[one.key]


def test_a_look_is_a_set_of_tokens_and_nothing_else() -> None:
    """themes.css only names custom properties and the two rules that pick day or night: no
    selector for a part of the page, so a theme can never be the reason one page is different."""
    themes = (STATIC / "themes.css").read_text("utf-8")
    code = re.sub(r"/\*.*?\*/", "", themes, flags=re.S)
    selectors = [s.strip() for s in re.findall(r"([^{}]+)\{", code)]
    assert all(s.startswith("[data-theme") for s in selectors), selectors
    assert "!important" not in code and "@import" not in code and "url(" not in code


def _luminance(colour: str) -> float:
    channels = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(a: str, b: str) -> float:
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _declared(block: str) -> dict[str, str]:
    return {k: v.strip() for k, v in re.findall(r"^\s+(--[a-z0-9-]+): ([^;]+);", block, re.M)}


def _shared(themes: str) -> dict[str, str]:
    """The tokens of the bare `[data-theme]` block every look takes unless it names its own."""
    found = re.search(r"\n\[data-theme\] \{(.*?)\n\}", themes, re.S)
    assert found
    return _declared(found.group(1))


def _pair(value: str) -> tuple[str, str]:
    """`light-dark(a, b)` as (a, b); anything else is the same in both modes."""
    inside = re.fullmatch(r"light-dark\((.*)\)", value)
    if not inside:
        return value, value
    depth = 0
    for at, char in enumerate(inside.group(1)):
        depth += (char == "(") - (char == ")")
        if char == "," and depth == 0:
            return inside.group(1)[:at].strip(), inside.group(1)[at + 1 :].strip()
    raise AssertionError(value)


def _colour(tokens: dict[str, str], value: str, which: int, depth: int = 0) -> str | None:
    """A token's value as #RRGGBB in one mode, following var(), light-dark() and color-mix() in
    sRGB; None for what is not a plain colour (a shadow, a transparent fill)."""
    value = value.strip()
    if value.startswith("light-dark("):
        value = _pair(value)[which]
    if depth > 12:
        return None
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
        return value
    named = re.fullmatch(r"var\((--[a-z0-9-]+)\)", value)
    if named:
        return _colour(tokens, tokens[named[1]], which, depth + 1) if named[1] in tokens else None
    clear = re.fullmatch(r"rgb\((\d+) (\d+) (\d+)(?: / ([\d.]+))?\)", value)
    if clear:  # laid over the page, as the eye sees it
        hexed = "#" + "".join(f"{int(clear[i]):02X}" for i in (1, 2, 3))
        under = (
            _colour(tokens, tokens["--paper"], which, depth + 1) if "--paper" in tokens else None
        )
        if clear[4] is None or float(clear[4]) >= 1 or under is None:
            return hexed
        return _mixed(hexed, under, float(clear[4]))
    mixed = re.fullmatch(r"color-mix\(in srgb, (.+?) (\d+(?:\.\d+)?)%, (.+)\)", value)
    if mixed:
        a, b = (_colour(tokens, mixed[i], which, depth + 1) for i in (1, 3))
        return _mixed(a, b, float(mixed[2]) / 100) if a and b else None
    return None


def _mixed(colour: str, into: str, share: float) -> str:
    return "#" + "".join(
        f"{round(int(colour[i : i + 2], 16) * share + int(into[i : i + 2], 16) * (1 - share)):02X}"
        for i in (1, 3, 5)
    )


def test_every_look_keeps_the_contrast_floors_by_day_and_by_night() -> None:
    """The floors of "Accessibility" in docs/STYLE.md, held for each look in both modes: 4.5:1 for
    words (4:1 on hover wells), 3:1 for box edges, the focus ring and words on each fill colour.
    """
    themes = (STATIC / "themes.css").read_text("utf-8")
    shared = _shared(themes)
    blocks = dict(re.findall(r'\[data-theme="([a-z]+)"\] \{(.*?)\n\}', themes, re.S))
    assert blocks
    short: list[str] = []
    for key, body in blocks.items():
        tokens = {**shared, **_declared(body)}
        # A look with no day (Phosphor, a green screen) is measured at night only.
        for mode, which in (("day", 0), ("night", 1))[0 if looks.BY_KEY[key].has_day else 1 :]:

            def at(name: str, which: int = which, tokens: dict = tokens, key: str = key) -> str:
                found = _colour(tokens, tokens[f"--{name}"], which)
                assert found, f"{key}: --{name} is not a colour"
                return found

            paper, card, well = at("paper"), at("card"), at("paper-2")
            pairs: list[tuple[str, str, str, float]] = []
            for name in ("ink", "ink-2", "ink-3", "link", "red", "amber", "ok", "vera"):
                pairs += [(name, at(name), surface, 4.5) for surface in (paper, card)]
            for name in ("lilac", "cyan", "lemon", "pink", "orange"):
                pairs += [(name, at(name), surface, 4.5) for surface in (paper, card)]
            for name in ("red", "ok", "vera", "cyan", "lilac"):
                pairs.append((f"{name} on a well", at(name), well, 4.0))
            pairs += [
                ("on-band", at("on-band"), at("band"), 4.5),
                ("on-band-2", at("on-band-2"), at("band"), 4.5),
                ("on-band on a hover", at("on-band"), at("band-hi"), 4.5),
                ("on-here", at("on-here"), at("here"), 4.5),
                ("on-primary", at("on-primary"), at("primary"), 4.5),
                ("on-today", at("on-today"), at("today"), 4.5),
                ("today-rule", at("today-rule"), paper, 4.5),
                ("today-rule on its wash", at("today-rule"), at("today-wash"), 4.5),
                ("ink on today's wash", at("ink"), at("today-wash"), 4.5),
                ("on-person", at("on-person"), at("person"), 4.5),
                ("edge on a card", at("edge"), card, 3.0),
                ("edge on a field", at("edge"), at("field"), 3.0),
                ("focus", at("focus"), paper, 3.0),
            ]
            # Words on each colour when it is a fill: tags, stamps, the family's initials.
            for name in ("lilac", "cyan", "lemon", "pink", "orange", "amber", "red", "ok", "vera"):
                pairs.append((f"on-bright on {name}", at("on-bright"), at(name), 4.5))
            # Words in a colour on its own faint tint, as a tag or a badge is drawn.
            for name in ("red", "amber", "ok", "cyan", "lemon"):
                pairs.append((f"{name} on its tint", at(name), _mixed(at(name), card, 0.10), 4.5))
            for name, foreground, background, floor in pairs:
                got = _contrast(foreground, background)
                if got < floor - 0.005:
                    short.append(f"{key} {mode} {name}: {got:.2f} < {floor}")
    assert not short, "\n".join(short)


# What Kitchen Table's layout draws that the built pages do not: (what, words, ground, floor).
KITCHEN_LAYOUT = (
    [
        ("the panel's links on its current item", "band-link", "band-hi", 4.5),
        ("the panel's mark on its current item", "here-icon", "here", 3.0),
        ("Vera's words in her box", "ask-ink", "ask-bg", 4.5),
        ("Vera's quiet words in her box", "ask-ink-2", "ask-bg", 4.5),
        ("Send", "on-send", "send", 4.5),
        ("words on Vera's fill", "on-vera", "vera-bg", 4.5),
        ("Vera on her wash (the pill)", "vera", "vera-soft", 4.5),
        ("the late plate", "on-red", "red", 4.5),
    ]
    + [(f"{m} on its wash", m, f"{m}-soft", 4.5) for m in ("ok", "amber", "red")]
    + [(f"p{i}'s name on its wash", f"p{i}-ink", f"p{i}-soft", 4.5) for i in range(1, 9)]
    + [(f"p{i}'s name on a card", f"p{i}-ink", "card", 4.5) for i in range(1, 9)]
    + [(f"p{i}'s letter", f"p{i}-on", f"p{i}", 4.5) for i in range(1, 9)]
    + [(f"p{i}'s mark on a card", f"p{i}-mark", "card", 3.0) for i in range(1, 9)]
)


def test_every_look_keeps_the_floors_kitchen_tables_layout_needs() -> None:
    """The roles Kitchen Table's layout reads are worked out for each look from its own tokens (or
    named by the look), and they hold the same floors by day and by night. The people are Kitchen
    Table's own eight, so they are measured on Kitchen Table's card only. Colour never has to carry
    a person alone (a name or an initial is beside it), so people are not held apart from each
    other: the family decided against that floor."""
    themes = (STATIC / "themes.css").read_text("utf-8")
    shared = _shared(themes)
    blocks = dict(re.findall(r'\[data-theme="([a-z]+)"\] \{(.*?)\n\}', themes, re.S))
    short: list[str] = []
    for key, body in blocks.items():
        tokens = {**shared, **_declared(body)}
        pairs = [p for p in KITCHEN_LAYOUT if key == "kitchen" or not re.match(r"p\d", p[1])]
        for mode, which in (("day", 0), ("night", 1))[0 if looks.BY_KEY[key].has_day else 1 :]:
            for what, words, ground, floor in pairs:
                a = _colour(tokens, tokens[f"--{words}"], which)
                b = _colour(tokens, tokens[f"--{ground}"], which)
                assert a and b, f"{key} {mode} {what}: --{words} or --{ground} is not a colour"
                if _contrast(a, b) < floor - 0.005:
                    short.append(f"{key} {mode} {what}: {_contrast(a, b):.2f} < {floor}")
    assert not short, "\n".join(short)


def test_a_look_may_only_add_effects_of_the_allowed_kinds() -> None:
    """Beside colour a look may name five effect tokens (a light on the page, scanlines, a glow,
    the face of titles). Each is one of a few plain forms, so a look cannot smuggle in an image, a
    link or a font the page does not carry: nothing here is `url()`, and a face is self-hosted."""
    themes = (STATIC / "themes.css").read_text("utf-8")
    shared = _shared(themes)
    blocks = dict(re.findall(r'\[data-theme="([a-z]+)"\] \{(.*?)\n\}', themes, re.S))
    names = ("--fx-page", "--fx-scan", "--fx-glow", "--fx-title", "--fx-title-grid")
    assert set(names) <= set(shared)  # every look has all five, plain unless it says otherwise
    faces = {"VT323", "Fraunces", "Georgia", "serif"}
    for key, body in blocks.items():
        got = {
            **{n: shared[n] for n in names},
            **{n: v for n, v in _declared(body).items() if n in names},
        }
        page, scan, glow, title, grid = (got[n] for n in names)
        assert page == "none" or all(
            float(a) <= 0.1 for a in re.findall(r"rgb\([^)/]*/ ?([\d.]+)\)", page)
        ), key
        assert "url(" not in page and "image" not in page, key
        assert (
            scan == "transparent"
            or float(re.fullmatch(r"rgb\([^)/]*/ ?([\d.]+)\)", scan)[1]) <= 0.06
        ), key
        assert 0 <= float(glow) <= 1, key
        assert title.endswith("var(--font-head)"), key
        assert set(re.findall(r'"([^"]+)"', title)) <= faces, key
        assert re.fullmatch(r"\d+(?:\.\d+)?", grid) and 0 <= float(grid) <= 50, (
            key
        )  # px; 0 an outline face


def _look_tokens(key: str) -> dict[str, str]:
    themes = (STATIC / "themes.css").read_text("utf-8")
    blocks = dict(re.findall(r'\[data-theme="([a-z]+)"\] \{(.*?)\n\}', themes, re.S))
    return {**_shared(themes), **_declared(blocks[key])}


def test_afterglow_is_one_fixed_look_whose_band_is_the_one_the_browser_is_told() -> None:
    tokens = _look_tokens("afterglow")
    look = looks.BY_KEY["afterglow"]
    assert not look.has_day and look.band == ("#060A08", "#060A08")
    assert tokens["--band"].upper() == "#060A08"
    themes = (STATIC / "themes.css").read_text("utf-8")
    block = re.search(r'\[data-theme="afterglow"\] \{(.*?)\n\}', themes, re.S).group(1)
    assert "light-dark(" not in block and "color-scheme: dark" in block


def test_in_afterglow_green_is_veras_alone() -> None:
    """Stage 17's choice: the family's links, current place, main button and its edge, and today's
    tile are warm off-white or warm grey, so the one green thing on a page is Vera's."""
    tokens = _look_tokens("afterglow")

    def greenish(name: str) -> bool:
        colour = _colour(tokens, tokens[name], 1)
        assert colour, name
        r, g, b = (int(colour[i : i + 2], 16) for i in (1, 3, 5))
        return g - max(r, b) > 12

    family = ("--link", "--here-icon", "--lit", "--primary", "--primary-edge", "--today")
    family += ("--chosen",)
    assert [name for name in family if greenish(name)] == []
    assert greenish("--vera")


def test_the_floors_hold_with_the_scanlines_laid_over_their_ground() -> None:
    """A look's scanlines are drawn under the words; laid over the band and Vera's glass at their
    strength, the words there still hold 4.5:1 (HANDOFF section 8.9, looks-check D)."""
    short = []
    for key in (one.key for one in looks.LOOKS):
        tokens = _look_tokens(key)
        scan = re.fullmatch(r"rgb\((\d+) (\d+) (\d+) / ?([\d.]+)\)", tokens["--fx-scan"])
        if not scan:
            continue
        line = "#" + "".join(f"{int(scan[i]):02X}" for i in (1, 2, 3))
        for which in (0, 1)[0 if looks.BY_KEY[key].has_day else 1 :]:
            for words, ground in (
                ("on-band", "band"),
                ("on-band-2", "band"),
                ("ask-ink", "ask-bg"),
            ):
                a, b = (_colour(tokens, tokens[f"--{n}"], which) for n in (words, ground))
                if not (a and b):
                    continue
                laid = _mixed(line, b, float(scan[4]))
                if _contrast(a, laid) < 4.5 - 0.005:
                    short.append(f"{key} {words} on scanlined {ground}: {_contrast(a, laid):.2f}")
    assert not short, "\n".join(short)


def test_the_people_and_the_main_buttons_edge_hold_their_floors_in_every_look() -> None:
    """Each person's letter on their fill, in Kitchen Table and in any look that draws its own
    people (Afterglow's tinted glass); and, where a look draws the main button's edge apart from its
    fill (Afterglow's dark glass button), that edge on a card, as anything you press is held."""
    themes = (STATIC / "themes.css").read_text("utf-8")
    blocks = dict(re.findall(r'\[data-theme="([a-z]+)"\] \{(.*?)\n\}', themes, re.S))
    short = []
    for one in looks.LOOKS:
        tokens, own = _look_tokens(one.key), _declared(blocks[one.key])
        pairs = [("words on a chosen chip", "on-chosen", "chosen", 4.5)]
        if "--chosen-edge" in own:
            pairs.append(("a chosen chip's edge on a card", "chosen-edge", "card", 3.0))
        if "--primary-edge" in own:
            pairs.append(("the main button's edge on a card", "primary-edge", "card", 3.0))
        if one.key == "kitchen" or "--p1-fill" in own:
            pairs += [(f"p{i}'s letter", f"p{i}-on", f"p{i}-fill", 4.5) for i in range(1, 9)]
            pairs.append(("Everyone's mark", "everyone-on", "everyone-fill", 4.5))
        for which in (0, 1)[0 if one.has_day else 1 :]:
            for what, words, ground, floor in pairs:
                a, b = (_colour(tokens, tokens[f"--{n}"], which) for n in (words, ground))
                assert a and b, f"{one.key}: {what}"
                if _contrast(a, b) < floor - 0.005:
                    short.append(f"{one.key} {which} {what}: {_contrast(a, b):.2f} < {floor}")
    assert any("--primary-edge" in _declared(body) for body in blocks.values())
    assert not short, "\n".join(short)
