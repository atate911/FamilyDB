# Brief: colour for FamilyDB — "Midnight"

You are an expert colour and interface designer with a bold eye: your palettes have a real point of view, stay legible, and you can defend every value.

**Your direction:** dark first. FamilyDB opens in its dark theme by default, the way a screen in a
dark kitchen at night should look: a deep blue-black page, a darker panel, ink in soft white, and
Vera's green glass at home among it. This is where the phosphor history can speak loudest without
changing the layout. People's colours glow gently (luminous, never neon). A light theme is still
required and must be just as considered, but design the dark one first and say so in PALETTE.md.

## The situation

FamilyDB is a family's planning app: plans on a calendar, to-dos with reminders, ideas, the kids'
wish lists, and Vera, the assistant the family writes to (never drawn; her small screen, `.vs`, is
her sign, and her dark glass with a phosphor-green Send is hers alone). After six rounds the family
has chosen the **layout and type** in this folder: House Log with The Board's navy left panel (read
`DIRECTION.md` and `STANDARD.md` first). What's left is **colour**. Their words: "I'm not sure about
the colours, especially the pink", and "Colors still need to be fixed."

## Your job: colour only

Layout, type, sizes, spacing and markup stay exactly as they are (a class hook only if a colour
truly needs one). Design the whole palette, light and dark:

- page, surfaces, ink, rules and control edges;
- **the left panel**: the family liked The Board's strong left panel. It must stay a strong,
  deep panel the page sits beside, but its colour is yours (your brief may name one); the phone's
  top bar follows it;
- **the eight people's colours** (`--p1`…`--p8`, each with its soft, ink and mark variants, plus
  Everyone): they're used for avatars with a letter, route stripes, calendar events and a kid's own
  pages. Eight that are clearly distinct, confident and grown-up: **no hot or bubblegum pink, no
  sugary pastels**, none that reads as red (red means late), none that could be mistaken for Vera's
  green. Check they stay distinguishable for the colour-blind (simulate protanopia, deuteranopia and
  tritanopia in a script and report the closest pair), and that letters on avatars pass AA;
- the signals: late (red, the only red), setup and warnings, done/ok, today, links and the one
  primary button, focus;
- **The phosphor echo stays.** FamilyDB's first design language was a green-phosphor CRT, and the
  family said: "I like how there's a shadow of the Phosphor interface in these renderings. Not
  enough to change the layout, but enough green CRT to echo the history of the design." That shadow
  is Vera's dark glass with its phosphor Send and glow, the lit cursor, her typed line after `>`,
  the wordmark's lit cursor, the ready pill and the smiling-monitor mark. Keep it at today's
  strength in both themes and make your palette welcome it: tune the glass and phosphor only so
  they sit well with your colours, never so they fade into them.

Floors: WCAG AA for text and 3:1 for controls in both themes, measured by script from the tokens and
checked on the shots; colour is never the only cue (it isn't today: keep it so).

Add `palette.html`: one page in the same shell showing every colour token with its name and value,
the eight people as avatars and route stripes side by side, and the signals, so the family can see
the palette at a glance (it renders with the rest).

## Deliver

1. Re-render every page light and dark (`DARK="<every page>" ./_kit/render-all.sh .`), look at the
   shots, fix, render again.
2. `PALETTE.md` (under 350 words): its name, the idea in one sentence, the palette (a table of the
   main tokens and the eight people), the colour-blind check result, and where it is weaker.
3. Update `STANDARD.md`'s colour section.

Reply with the name, the one-sentence idea, and anything unfinished.

## Why another round

Six palettes were already made for this layout: Rail yellow, Metro lines, Enamel, Amber Terminal,
Ultramarine and Fjord (`earlier-palettes/`: their notes, and `six-earlier.png`, each one's palette
sheet above its Home). The family's verdict: **"None of those are really speaking to me."** They
did like the palette sheets. Notice what the six share (a light grey page, a navy-ish panel,
eight mid-deep people's colours, one signal colour) and don't make a seventh of the same: commit
to your direction harder than they did. Yours must be clearly different from all six.

Make `palette.html` as clear and as good to look at as the best of theirs, and have it tell the
palette's idea, not only its values. `_kit/` is yours to add check and sheet scripts to.
