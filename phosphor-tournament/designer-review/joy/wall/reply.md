I've restyled it as **Kitchen Wall, Felt Tip**.

**The idea:** the family calendar on the kitchen wall, filled in by everyone with their own felt-tip pen. Today is circled in green, each person's plans are in their bright colour, and things get crossed off with a satisfying line.

Every page is rendered light and dark, desktop and phone, into `shots/` (96 images). I looked at all of them and fixed what was wrong:
- the tape on Home's today page covered the weekday;
- the "number 1" rosette landed on a lone wish in the states sheet;
- Maya's heading highlight split "My to-dos" across two lines;
- the primary button on the 404 pane was nearly invisible.

The last full render found no font failures and no sideways scrolling. A script checked every colour pair against the new tokens in both themes, and none fail the AA floors.

**What changed:**
- **Type:** headings, the wordmark, dates and money are now Bricolage Grotesque, replacing Manrope. Dates and amounts use its narrowest width, tall and heavy like wall-calendar numbers. Atkinson still sets every word. It's one 123 KB OFL file, and Manrope is deleted.
- **Colour:** the eight people's colours are now bright pens with dark letters, so avatars and calendar blocks look like stickers. The page is a lilac wall with a faint planner dot grid. Dark mode is a deep violet night with the same pens.
- **Moments:**
  - **Today:** circled in a hand-drawn green loop on the calendar. On Home, today's page is taped up a little crooked.
  - **Ticking a to-do:** the tick pops, a green line is drawn through the title, and the "Ticked off" banner bursts with the family's colours.
  - **Wishes:** "Yes!" is a green sticker.
  - **Maya's pages:** they use her own colour.

  All motion is off under reduced motion.

**Unfinished:**
- "All done for today", "Loved it" and "nothing late" aren't drawn in the states sheets, so they get no celebration yet.
- **New body class:** kids' pages need a `kid me-pN` class on `<body>` from the server. I added it to the six kid mockups. It's the one markup change.

`DIRECTION.md` is 393 words. I updated `type.html` and the colour, type and brand sections of `STANDARD.md`. Its contrast table in §7 is regenerated from the live tokens, and a new "Moments" table lists each celebration.

Files are in the folder:
- `DIRECTION.md`
- `STANDARD.md`
- `style.css`
- `type.html`
- `fonts/bricolage-var.woff2`
- `shots/`
