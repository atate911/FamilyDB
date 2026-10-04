# Fresh designers: no pictures, only a description

Six designers, each a fresh process run outside the repository, so none of them sees the
project's notes, the earlier designs, today's page or each other's work.

- `a1`–`a3` got `BRIEF-description-only.md`: what the site is and does, who uses it, the seven
  pages to design, and the demo family's data.
- `b1`–`b3` got `BRIEF-with-concept.md`: the same, plus one paragraph on the direction ("a
  modern, easy-to-use family app that carries the character of an old green phosphor computer
  screen").

Each made seven standalone HTML pages and a stylesheet (mockups, not the app's templates),
rendered with `kit/render.sh` at 1280 wide and Home and Chat at 390, and wrote `DESIGN.md`.

## What came back

`gallery.html` (published as an artifact) shows all six, with the findings. In short: the three
given only the description all named theirs Kitchen Table (warm paper, Fraunces, per-person
colours); the three given the Phosphor line made Afterglow (twice) and Kitchen Terminal (green
glass, VT323 for big moments, Atkinson Hyperlegible, amber for "needs you"). All six share one
page structure. They are one model run six times on one brief, so read the agreement as one
opinion repeated.

Each `<id>/` holds the pages, `style.css`, `DESIGN.md`, the designer's `REPLY.md`, and
`shots/` rendered by `kit/final.js` (every page at 1280 and 390, retried until the web fonts
loaded).
