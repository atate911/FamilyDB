"""The page the examples open on (examples/export.py): the household and the moment, a door for
each person, and what to try. Drawn in FamilyDB's own type and its Kitchen Table colours, light
and dark, from the fonts the example already carries."""

from __future__ import annotations

import html
from pathlib import Path

from examples.household import RECEIPT_ON_DO, REPLY_ON_EAT

TITLE = "FamilyDB Example Household"

DOORS = (
    {
        "key": "sam",
        "kicker": "Admin · on a phone or a desk",
        "title": "Sam, who runs it",
        "text": "Now opens on the box, then what waits on Sam: how the science center went, "
        "Maya's sketchbook, her pitch for the bounce hall. Under them, the plate and Vera's picks "
        "for tonight and the weekend. The row leads to Eat, Do, Week, Kids, Soon, Lists and Did, "
        "and every place, plan, reminder and outing has a page of its own.",
        "open": "Open Sam's FamilyDB",
        "more": (
            ("Her reply over a page", f"/eat?asked={REPLY_ON_EAT}"),
            ("A receipt with Undo", f"/do?asked={RECEIPT_ON_DO}"),
            ("This week", "/week"),
            ("What about…", "/about"),
            ("A place", "/idea/1"),
            ("An outing", "/did/1"),
            ("Status", "/status"),
        ),
    },
    {
        "key": "maya",
        "kicker": "Kid · eleven",
        "title": "Maya, eleven",
        "text": "Her own Now: the box, her list with the days to Christmas and to her birthday, "
        "her library books, and picks made for her. Her row is Now, Do, My week and My list. No "
        "costs, no settings, nothing about how it works, in the Afterglow look she chose.",
        "open": "Open Maya's FamilyDB",
        "more": (("My list", "/kids"), ("My week", "/week"), ("Do", "/do")),
    },
    {
        "key": "board",
        "kicker": "Kitchen tablet",
        "title": "The kitchen board",
        "text": "Today and tomorrow in the middle, the nearer one largest; what waits on "
        "someone; the shopping list, always; the weekend's picks; the saved ideas along the "
        "bottom, the untouched ones fading. Tap your face on the box before you ask.",
        "open": "Open the board",
        "more": (),
    },
    {
        "key": "first-day",
        "kicker": "New install",
        "title": "The first day",
        "text": "The family is on the list and a model is connected, but nothing is saved yet. "
        "Vera says who she is and asks for one place you'd happily go back to; each destination "
        "says what will land there.",
        "open": "Open the first day",
        "more": (("What about…", "/about"), ("Eat", "/eat"), ("Do", "/do")),
    },
)

# The page's own look, kept beside it.
STYLE = (Path(__file__).parent / "start.css").read_text("utf-8")


def page(written: dict[str, dict[str, str]], pictures: set[str], *, whole: bool = True) -> str:
    """The start page. `written` is each person's addresses and the files they went to;
    `pictures` the people with a picture in pictures/. Without `whole`, only what goes inside
    the body, with its title and style first, for a host that supplies the document."""

    def file(key: str, address: str) -> str | None:
        name = written.get(key, {}).get(address)
        return f"{key}/{name}" if name else None

    doors = []
    for door in DOORS:
        key = door["key"]
        home = file(key, "/") or file(key, "/board")
        if home is None:
            continue
        picture = (
            f'<a class="door__pic" href="{home}" tabindex="-1" aria-hidden="true">'
            f'<img src="pictures/{key}.png" alt="" width="390" height="560" loading="lazy" /></a>'
            if key in pictures
            else ""
        )
        more = "".join(
            f'<li><a href="{target}">{html.escape(label)}</a></li>'
            for label, address in door["more"]
            if (target := file(key, address))
        )
        doors.append(
            f'<article class="door">{picture}<div class="door__body">'
            f'<p class="door__kicker">{html.escape(door["kicker"])}</p>'
            f"<h2>{html.escape(door['title'])}</h2><p>{html.escape(door['text'])}</p>"
            f'<a class="door__open" href="{home}">{html.escape(door["open"])}</a>'
            + (f'<ul class="door__more" aria-label="Straight to">{more}</ul>' if more else "")
            + "</div></article>"
        )
    body = f"""<main class="ex">
  <header class="ex__head">
    <b class="wm">FamilyDB<span class="wm__cur" aria-hidden="true"></span></b>
    <h1>The Okafor-Lindqvists, on a Friday at five</h1>
    <p class="ex__lede">A made-up family of four in Portland, a week of their plans, and Vera,
    as each of them would see FamilyDB. Every page is the real site, drawn by the code you are
    about to put live. Links work, and every button says what it would have done; nothing is
    sent or saved.</p>
    <p class="ex__moment">Friday 16 October 2026 · 5:02 pm · Portland, OR ·
    overcast, dry tomorrow</p>
  </header>
  <section class="doors" aria-label="Whose FamilyDB to open">
    {"".join(doors)}
  </section>
  <section class="try" aria-labelledby="try-h">
    <h2 id="try-h">What to try</h2>
    <ul>
      <li><b>Change the width.</b> From a tablet's width the row of places stands at the left; on
      a desk the box keeps a column of its own, with the last of the conversation under it.</li>
      <li><b>Press anything.</b> Each button and form says what it would have done on your own
      FamilyDB. Nothing leaves the page.</li>
      <li><b>Day or night.</b> The pages follow your device's light or dark setting.</li>
    </ul>
  </section>
  <p class="ex__foot">Everything here is invented: the family, the places, the events and the
  conversations. Made by <code>uv run python -m examples</code> from the FamilyDB repository, at a
  fixed moment, so it looks the same each time it is made.</p>
</main>"""
    head = f"<title>{TITLE}</title>\n<style>{STYLE}</style>\n"
    if not whole:
        return head + body + "\n"
    return (
        '<!doctype html>\n<html lang="en-US">\n<head>\n<meta charset="utf-8" />\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, '
        'viewport-fit=cover" />\n' + head + "</head>\n<body>\n" + body + "\n</body>\n</html>\n"
    )
