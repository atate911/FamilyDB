# Brief: Kitchen Table, as the family's wall calendar

You are an expert creative graphic and interface designer, with a strong record in calendar and
productivity software.

Your take: **the family hub on the kitchen wall**. Think of the best family organisers (a
wall-mounted family calendar screen, a shared household planner): bright and clean, today big and
unmistakable, each person's colour doing real work, glanceable from across the room, friendly but
organised. Warmth comes from the people's colours and the content, not from beige paper.

## What the family said

"The interface of Kitchen Table is nearly perfect. The only thing: I don't like the overall look.
It reads like a recipe or gardening site. I'd like it to feel more like a home calendar or
house-management page. Can we adjust the vibe to be more like a calendar app?"

So: **the interface stays; the vibe moves.** Find what makes it read as recipes and gardening
(look hard at the cream paper and beige lines, the soft serif headings and serif figures, the
forest green with sun yellow, the rounded softness, the warm card fills) and replace it with what
makes software read as a family's calendar and household organiser: dates and times treated as
the main material, a crisp structured surface, the people's colours used the way a calendar
uses calendar colours, a clear "today", the precision of a grid. Typography matters most here;
small type changes feel like a different design, so choose deliberately and say why.

## What you start from

This folder holds the finished FamilyDB design, "Kitchen Table": twenty-four standalone pages, one
stylesheet (`style.css`), an icon sprite, self-hosted fonts, the brand files in `brand/`, and
`STANDARD.md`, its written standard (read it first). `reference/` has shots of it as it stands.
It was chosen by the family, checked by blind judges and specialist reviewers, and it works: the
phone layout, the kids' pages, every state, the words, the accessibility numbers. Keep all of that.

## Rules

- **Keep the pages, their content and their structure.** Change the look: colour, type, surfaces,
  lines, radii, the brand's treatment, spacing where the look needs it. You may re-present what a
  page already shows in a more calendar-like form (a date as a calendar tile, times in a gutter,
  a list of the week's days as a strip) as long as it shows nothing new and loses nothing. No new
  pages, no new features, and no change to what any page says or does.
- **Keep the brand's facts:** FamilyDB's smiling-monitor mark (you may recolour or re-tile it),
  Vera is never drawn (her small screen, `.vs`, stays her sign; restyle it to fit), red means only
  late or broken, people keep their own colours (eight slots), Vera's things stay hers in colour.
- **Type:** Atkinson Hyperlegible stays for running text (it was chosen for the kids' reading).
  Headings, figures, dates and the wordmark are yours to change: Fraunces may go. A new face must be
  open-licensed and self-hosted in `fonts/` as woff2 (you can download from Google Fonts or its
  GitHub repos, and fontTools is installed for subsetting); keep the total of new font files under
  150 KB. Update `type.html` so it shows the new scale (its reference images to A1 can go).
- **Floors that don't move:** measured contrast in both themes (WCAG AA for text, 3:1 for
  controls), 44 px targets on kids' pages, the phone's first screens, no inline `style=""` and no
  scripts, everything readable with scripting off, `prefers-reduced-motion` honoured. Dark mode is
  shipped too and gets the same care.
- Work only in this folder.

## Deliver

1. The restyled pages, rendered with `DARK="<every page>" ./_kit/render-all.sh .` (it renders every
   page light and dark, desktop and phone, into `shots/`). Look at every shot, fix, render again.
2. `DIRECTION.md` (under 400 words): its name, its idea in one sentence, what changed from Kitchen
   Table and why (type above all), and where it is weaker.
3. Update `STANDARD.md`'s colour, type and brand sections to match.

Reply with the name, the one-sentence idea, and anything unfinished.
