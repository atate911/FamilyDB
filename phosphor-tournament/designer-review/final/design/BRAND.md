# Stage 5: give it a brand

The family likes the final design but says it looks **generic**, and wants **some branding**: a
look that is unmistakably FamilyDB, fresher and more its own. Cream paper with a soft serif and
rounded cards is a very common look right now; the question for this stage is what makes this one
FamilyDB's and nobody else's. The answer should be **a little sprinkle**, not a new theme: the
layout, the system and everything the checks protected stay.

## What FamilyDB already owns

The app had a strong identity before this redesign, and Kitchen Table dropped it. Two assets are in
`brand-ref/`:

1. **The mark** (`favicon.svg`, `icon-512.png`, `apple-touch-icon.png`): a little monitor with a
   smile, drawn in one stroke, **phosphor green on charcoal**. It is FamilyDB's: the favicon, the
   home-screen icon on a phone, and the mark in the bar. It is never Vera's face.
2. **Vera's screen**: Vera is never drawn, so where she speaks the page showed a small screen full
   of words nobody can read, as if busy: columns of terminal glyphs, the newest of each run bright
   and the rest dim, faint scanlines, blurred past reading. While she was thinking the glyphs
   fell, a row at a time. It is how she is *there* without a face, and it works whatever the family
   calls her.

Bring both into Kitchen Table, redrawn to sit naturally on warm paper:

- **The mark replaces the generic house** everywhere: the bar, the sidebar, sign-in, the favicon and
  the home-screen icon (draw it at 16, 32, 180 and 512 px). Refine it if you like, but keep the
  smiling monitor, one stroke, phosphor on charcoal. Give it a wordmark beside it that belongs with
  it (for example a lit cursor after the name, the way a terminal waits).
- **Vera's screen replaces the "V" circle** wherever she appears: the Ask card, chat, receipts, the
  header status. Small, at the avatar sizes; glyphs `aria-hidden`; the falling glyphs only while she
  is answering, and no motion at all under `prefers-reduced-motion`.

## Typography is the brand's voice

The family noticed that the final already reads like a different design from the one they chose,
and typography is much of why. They put it this way: type lands hard; small changes feel like a
different design. Since the version they chose, the type has drifted: numbers moved into a serif
cut and back, the size scale tightened, much of the bold went, line heights changed. Each change
had a reason, and together they changed the voice. So in this stage:

1. **The anchor is the type of the version they chose**, in `reference-a1/` (its `style.css`, its
   pages and shots): Fraunces headings at its weights and sizes, Atkinson Hyperlegible body at 17
   px, its bold card and row titles, its line heights and spacing. Compare the current type with it,
   page by page. Where the current type differs and the difference did not fix a named problem
   (slashed zeros where numbers stand alone, the 14 px floor, phone wrapping, contrast), bring it
   back to how it was.
2. **Type is part of the brand, so change it on purpose and little.** The wordmark is the strongest
   type moment. Fraunces has optical-size and softness axes and some characterful alternates: one
   small, consistent choice in large headings brands more than a new face would. The mono for Vera's
   voice is the only new face, small and sparing. No other new faces.
3. **Show it.** Make `type.html`, a specimen page: the scale (each step's face, size, weight, line
   height and where it is used) and a side-by-side of real lines (Home's greeting and summary, a
   to-do row, a date tile, a price, a chat message from Vera and one from the family) as they were in
   `reference-a1/` and as they are now. Say in `CHANGES.md` every type change from the chosen
   version, and why it is worth the change in voice.
4. **Settle the brand elements first, then type, and change type last and least.**

## The brand rule

**Warm paper is the family's. Phosphor on charcoal is FamilyDB's and Vera's.** The pairing of the
two (a pane of dark glass with green light, set on cream paper) is the signature. It appears where
the brand, Vera or something live is, and nowhere else. The family's own things (names, ideas,
to-dos, wishes) stay on paper in their own colours. Every touch says something true; none is only
ornament.

## Other touches to consider (take what helps the brand, leave the rest)

1. **Her voice in a mono:** Vera's small machine lines (receipts, her message times, the live
   status) in one monospaced face, self-hosted, one weight. The family's words stay Atkinson.
2. **One instrument, where it shows something true:** ideas plotted by drive time and direction
   from home, as a small glass pane on Ideas (every dot also named in text). The judges' favourite
   idea across twenty designs. At most one instrument per page.
3. **Live things glow:** the "Vera is ready" status, a reply on its way, the cursor in her box; a
   soft glow or a slow blink, none under reduced motion.
4. **Brand moments:** sign-in (the mark, awake, and who you are), the first empty day of a new
   family, the page a kid sees on a grown-ups' page, a missing page: these are where a brand is
   felt most. Use the mark and the glass here, never a drawing of Vera.
5. **Dark mode becomes phosphor at night:** charcoal glass instead of warm brown, cream ink, Vera's
   things in phosphor green with a soft glow, amber for what needs a look, people in their colours.
   Day stays Kitchen Table.
6. You may tune Kitchen Table's own green so it belongs with the phosphor (for example a deeper,
   glassier green for Vera's card), if contrast holds.

## What not to do

- No dark page in light mode; no CRT curvature, vignettes or heavy scanlines on the page (faint
  scanlines inside a pane are fine); no pixel font on headings or on anything the family wrote.
- No green on the family's own items; green stays Vera's, the brand's, and "all good".
- No more than one instrument per page; no pane that only decorates; no drawing of Vera, and the
  mark never stands in for her.
- Nothing that breaks what the checks protected: measured contrast in light and dark, 44 px targets
  on kids' pages, the phone's first screens, no inline styles or scripts, everything readable with
  scripting off.

## What to deliver

0. `type.html`, as described under typography.
1. The pages updated, light and dark, desktop and phone, kids' pages too; the favicon and
   home-screen icons as files (`brand/`).
2. A new section in `STANDARD.md`, "The brand": the mark and wordmark (sizes, clear space, on paper
   and on dark), Vera's screen (sizes, states, motion), the brand rule, each phosphor element with
   its tokens and where it may and may not appear, and the dark theme.
3. `CHANGES.md`: what you tried, what you kept, what you dropped and why.
4. Render everything (`DARK="<every page>" ./_kit/render-all.sh .`), look at every shot, fix and
   render again.

Then stop and reply with what you kept and how it changes the feel.
