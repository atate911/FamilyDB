# Brief: Afterglow

You are an expert creative graphic and interface designer.

FamilyDB's design direction began as the **Phosphor Interface**: a modern, easy-to-use family app
that carries the character of an old green phosphor computer screen. The best phosphor designs in
the blind judging scored 7.3 to 7.7 (two of them are in `reference/`: shots, a stylesheet and
notes); the family chose a warm paper design, finished in this folder, whose dark mode is already
"phosphor at night". Make the **phosphor-first direction** of the finished design, called
Afterglow: the charcoal glass and green light are the page by day and night, and the family's own
things sit on it in their own colours. Things to resolve:

- The judges marked phosphor up where it carried information and down where it decorated or hurt
  reading. A pixel or mono face may be used for big moments only (page titles or big figures),
  never for anything the family reads; Atkinson stays for reading.
- Keep it calm and warm enough for a family with kids, not a hacker's terminal: generous spacing,
  soft glow only on what is Vera's or live, no heavy scanlines on the page.
- Ship a light theme too (it may be the less important one), because some people need it.
## What you start from

This folder holds the finished FamilyDB design, "Kitchen Table": twenty-four standalone pages, one
stylesheet (`style.css`), an icon sprite, self-hosted fonts, the brand files in `brand/`, and
`STANDARD.md`, its written standard (read it first). It was chosen by the family, checked by blind
judges and specialist reviewers, and it works: the phone layout, the kids' pages, every state, the
words, the accessibility numbers. Your job is **one alternative direction for its look**, so the
family can compare. Keep all of that working.

## Rules

- **Keep the pages, their content and their structure.** Change the look: colour, type, surfaces,
  the brand's treatment, spacing where the look needs it. Small markup changes are fine where a
  look needs a hook; no new pages, no new features, and no change to what any page says or does.
- **Keep the brand's facts:** FamilyDB's smiling-monitor mark (you may recolour or re-tile it),
  Vera is never drawn (her small screen, `.vs`, stays her sign; restyle it to fit), red-only-means
  late-or-broken (or an equally clear single signal for late), people keep their own colours, and
  the type rules in STANDARD (Atkinson Hyperlegible for everything read).
- **Floors that don't move:** measured contrast in every theme you ship (WCAG AA for text, 3:1 for
  controls), 44 px targets on kids' pages, the phone's first screens, no inline `style=""` and no
  scripts, everything readable with scripting off, `prefers-reduced-motion` honoured.
- Work only in this folder.

## Deliver

1. The restyled pages, rendered with `DARK="<every page>" ./_kit/render-all.sh .` (it renders every
   page light and dark, desktop and phone, into `shots/`). Look at every shot, fix, render again.
2. `DIRECTION.md` (under 400 words): its name, its idea in one sentence, what changed from Kitchen
   Table and why, and where it is weaker.
3. Update `STANDARD.md`'s colour, type and brand sections to match.

Reply with the name, the one-sentence idea, and anything unfinished.
