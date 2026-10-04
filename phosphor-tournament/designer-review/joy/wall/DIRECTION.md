# Kitchen Wall, Felt Tip

**The idea:** the family calendar on the kitchen wall, filled in by everyone with their own felt-tip pen: today circled in green, each person's plans in their bright colour, things crossed off with a satisfying line.

## What makes it joyful

**Type first.** Headings, the wordmark, dates and money are now **Bricolage Grotesque**, a grotesque with a hand in it: a big round "a", ink traps that show at display sizes, and an optical-size axis that keeps it sturdy at 13 px. Modern software, not a book, and nobody's default. Its width axis does a second job: every date and amount is set at 75 % width, 800 weight, tall and heavy like the numbers printed on a wall calendar. Atkinson still sets every word.

**Colour with conviction.** The eight people's colours are now bright pens (cornflower, violet, raspberry, tangerine, teal, periwinkle, lime, caramel) with dark ink letters, so avatars and one-person calendar blocks look like stickers. The page is a lilac wall with a faint planner dot grid, the ink is violet-black, and dark mode is a deep violet night where the same pens keep their colour.

**Shape.** Softer sheets, round controls, date tiles with binding holes.

## Three moments to show the family first

1. **Today, circled.** On Plans, today's date has a hand-drawn green felt-tip loop round it. On Home, today's page is taped to the wall, a little crooked.
2. **Crossing it off.** The tick pops green, then a green line is drawn through the to-do, and the "Ticked off" banner opens with a small burst of the family's colours.
3. **Maya's pages are Maya's.** Her heading is underlined in her raspberry highlighter, and her current tab and her top wish's rosette are in her colour. A "Yes!" on a wish is a green sticker.

All motion is CSS, plays once, and is off under `prefers-reduced-motion`.

## Where it is weaker

- Bricolage's quirks can feel busy in long headings.
- The lilac wall is a strong choice; some may read it as "purple app". The dot grid is faint and disappears on low-quality screens.
- Kids' pages need a body class (`.kid .me-p3`) from the server: a small new hook.
- "All done for today", "Loved it" and "nothing late" have no drawn state yet, so no celebration.
- Celebrations are visual only.
