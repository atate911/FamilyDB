# Fridge Door

**The idea:** Today Line's calendar made the family's own: a grotesk with a hand in it for everything worth writing big, eight people's colours used like felt-tips, and sticker-sized celebrations when something gets done.

## What makes it joyful

**Type, above all.** Inter is gone. Headings, dates, times, money and the wordmark are now **Bricolage Grotesque** (69 KB, OFL, optical sizes). Big, it has ink traps and round, slightly-too-friendly letters, so "Good morning, Maya." sounds spoken. Small, it opens up so a 13 px weekday stays clear. Its open shapes match Atkinson's. The rule: **Atkinson for reading, Bricolage for what you'd write big on the fridge.**

**Colour.** The page is a planner's lilac with a faint printed dot grid, and the ink is deep indigo. People's colours are clearer and more saturated. **Whoever is signed in wears their colour**: the current tab, their account card, and a highlighter under each page title. Green still means only "now".

**Shape.** Cards and buttons sit on a 3 px lip like stickers, and buttons press down when used. Date tiles are tear-off leaves with binder holes. Each idea kind has its own die-cut tile: a plate, an arch, a ticket, a wrapped box, a tilted sticker.

## Three moments to show the family first

1. **Ticking a to-do off.** The ring pops green, a burst of everyone's colours stays around it, and the title is struck through in green. The flash wears the same tilted sticker.
2. **Today and the countdown.** Today's date is a green sticker over the greeting. The next plan's leaf is torn off and tilted, with "Tomorrow" stuck beside it. Today's number in the month view sits on a tilted disc.
3. **A kid's own pages.** Maya's wish ranks are raspberry stickers, and "Yes!" is stamped on in green.

Motion is CSS, plays once, and is off under `prefers-reduced-motion`.

## Where it is weaker

- Bricolage's display cut is loud, and long settings pages tire the eye.
- The viewer's colour is found with `:has()` on the account avatar. The engineer should emit a body class instead.
- Tilts and lips add noise on dense pages (Status, states sheets).
- The dark primary button is only 3.05:1 against the page.
- Kind shapes are subtle at 40 px, so the word still does most of the work.
