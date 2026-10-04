# Brief: a voice for FamilyDB, round 4 — "the week on one page"

You are an expert creative graphic and interface designer with a strong point of view on layout and typography: your work is recognisable at a glance, and people find it easy to use.

**Your starting idea** (develop it, push it, or bend it if a better one appears as you work):
families think in weeks. The paper week-planner on a fridge, a desk planner open at this week:
seven days side by side, each person in their colour, today unmistakable, the weekend given its
due. Let the week be the organising idea of the layout (Home included), with a typographic system
built around big day numerals and a clear structural grid, more Swiss poster than spreadsheet.

## Where this has been (read `history/`)

FamilyDB is a family's planning app: plans on a calendar, to-dos with reminders, ideas for what to
do, the kids' wish lists, and Vera, the assistant the family writes to (she is never drawn; her
small screen, `.vs`, is her sign). The family has steered the look through several rounds:

1. **Kitchen Table** (cream paper, soft serif, forest green): "the interface is nearly perfect, but
   it reads like a recipe or gardening site. Make it feel like a home calendar app."
2. **Calendar** (cool grey, Inter or Manrope, hairline grid): "great, but still sterile, like an
   AI-designed app. Functional but plain, no real soul. The typography is fine but uninspired."
3. **Felt Tip / Fridge Door** (lilac planner page, Bricolage Grotesque, felt-tip people colours,
   small celebrations): this folder is Felt Tip. The family now asks for **another round of
   creative ideas for making it more distinctive and usable, focusing on layout and typography,
   and a distinctive visual "voice" for the app**.

So this round is not a recolour. **Layout and typography are the work**, and the result should
have a voice: a page anyone in the family would recognise as FamilyDB with the logo covered.
Distinctive *and* more usable: every layout change should make something faster to find, read or
do, and you should be able to say what.

## What you may change

- **Layout, freely:** page structure, hierarchy, what leads, the shell and navigation, how lists,
  cards and the calendar are composed, the phone layout. Re-present what pages show in better
  forms (a timeline instead of a list, a week instead of cards), merge or reorder sections.
- **Typography, freely:** pick a pairing with a point of view. Atkinson Hyperlegible stays for
  running text the kids read unless you have a legibility reason to change it, stated. Display,
  headline, figure and label faces are yours. **Not** Fraunces, Inter, Manrope or Bricolage
  Grotesque (all used in earlier rounds), and not Space Grotesk or another default "AI" face.
  Open-licensed, self-hosted woff2 in `fonts/` (Google Fonts or the families' repos; fontTools is
  installed), new font files under 220 KB in total. Update `type.html`.
- **Colour**, as far as your voice needs. Felt Tip's palette is a fine start, not a rule.

## What stays

- **Every page keeps its job and its information:** nothing a page shows or lets you do is lost,
  and nothing needs data the app doesn't have. No new features, no new pages. Words may be
  re-ordered or re-headed where a layout needs it, but keep their meaning, and keep Vera's lines.
- **The brand's facts:** FamilyDB's smiling-monitor mark (recolour or re-tile it), Vera never
  drawn, red means only late or broken, each person keeps a colour, kids never see costs, models
  or how it works, presents hidden from whoever they're for.
- **Floors that don't move:** WCAG AA contrast for text and 3:1 for controls in both themes, 44 px
  targets on kids' pages, the phone's first screen showing what matters, no inline `style=""` and
  no scripts, everything works with scripting off, `prefers-reduced-motion` honoured, emoji never
  as decoration. Dark mode gets the same care.
- **Scope:** put your real layout effort into Home, Plans, To do, Chat, Ideas, and the kid's Home
  and Wishes, desktop and phone. Carry the voice through every other page so none looks like it
  came from another app.
- Work only in this folder.

## Deliver

1. The pages, rendered with `DARK="<every page>" ./_kit/render-all.sh .` (every page light and
   dark, desktop and phone, into `shots/`). Look at every shot, fix, render again.
2. `DIRECTION.md` (under 450 words): the name; the voice in one sentence; the type pairing and why;
   each layout change and what it makes easier; where it is weaker.
3. Update `STANDARD.md` (layout, colour, type, brand sections) to match.

Reply with the name, the voice in one sentence, and anything unfinished.
