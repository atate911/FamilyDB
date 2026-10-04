# Brief: Kitchen Table, tomato

You are an expert creative graphic and interface designer.

Among twenty designs judged blind, the warmest one scored highest of all: a Kitchen Table in tomato
red (8.5 from all three judges). Its look is in `reference/` (its stylesheet, notes and shots).
The family chose a green version, which became the finished design in this folder. Make the
**tomato direction** of the finished design: the warmth, appetite and friendliness of the tomato
reference, carried into the finished system. Things to resolve:

- In the reference, tomato was the brand, the Send button and "late" all at once. The finished
  design keeps red for late or broken only. Find a tomato that is the family's warm accent, and a
  way to keep "late" unmistakable (a deeper brick with the clock icon and words, or another clear
  single signal), and say how in DIRECTION.md.
- The reference drew Vera as a little tomato. She must stay undrawn: keep her small screen, perhaps
  warmed to sit with tomato (it may stay phosphor on charcoal, which reads as hers).
- Keep the dark mode warm.
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
