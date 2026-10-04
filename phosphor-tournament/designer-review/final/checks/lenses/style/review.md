## Verdict
**8 / 10.** The look holds together across all twenty pages, in both themes and on the phone. The warm paper, the deep green of Vera, the Fraunces headings and one colour per person make it feel like a calm kitchen table, not an admin panel, and a family would trust it on first sight. What keeps it from a 9 is that the yellow and green signals each have more than one meaning, and there is no drawing anywhere. Parents will find it calm. Kids will find it a bit grown-up and plain.

**Optimise before building? No.** Every fix below is a token or component change in `style.css` and the sprite. None of them means redrawing a page, so they can go in while the templates are built.

## Protect
- The Ask Vera card on Home (both roles): a deep green slab with the one sun-yellow Send. It is the warmest and clearest thing in the app, and it makes the page's first job obvious.
- Person colours carried everywhere: avatars, chat bubbles (Sam blue, Alex lilac, Maya pink), Maya's Nutcracker event on Plans, the picker tiles on Sign in. This is the family's identity in the app.
- Headings and big numbers in Fraunces (Good morning, Sam., October 2026, $0.00 on Status, the date tiles), set against Atkinson for the words. Friendly and well crafted.
- The date tile (`.dt`): green header for tomorrow, neutral for the rest, on Home, Plans and the kid's Home. It is the app's signature object, so keep it exactly as drawn.
- The surfaces: paper, then card, then field, on soft 18 px cards with hairline borders. It stays quiet even on dense pages like Settings and Status, and the dark theme keeps the same layering.
- Kid pages use the same look with fewer things on them (Maya's Home, My wishes, the grown-ups page). They feel like the same app and are not talked down to.

## Fix, ranked

**1. Yellow means too many things** (Plans calendar weekend columns; Home setup card; Plans Google banner; Status rows; "How did it go?" on calendar events; Vera resting)
- Problem: sun and warn yellow are used for the Send button, "set this up", "Could be better", "Not connected", "resting", the "How did it go?" prompts and the weekend columns of the month grid. On Plans the whole Sat and Sun columns are cream-yellow beside a yellow banner, and four of seven rows on Status are yellow. Parents can't tell at a glance what actually needs them, and in dark mode the weekend tint turns into a muddy brown band.
- Fix: remove the weekend tint from `.day--we`, or use a 2–3 % `--paper-2` wash with no hue. Keep `--sun` for the Ask card's Send and the brand dot only. Write "How did it go?" on calendar events in `--ink-2` with the face icon, not in warn colour. Keep warn for "set this up, needs a look, resting".
- Severity: major. Effort: S.

**2. "Off" and "for your information" look like "all good"** (Ideas: "Looking things up is off" banner; Idea page; Add an idea side note)
- Problem: info banners use `--vera-soft` mint, which is almost the same hue as the `--ok-soft` hero on Status ("Vera is answering, and well under budget"). A feature that is switched off reads as healthy, so parents learn to skim the green.
- Fix: draw info banners on `--card` with a 4 px `--vera-line` left rule and the icon tile in `--vera-soft`, with no mint fill. Keep the full mint fill for ok/done only (Status hero, flash with Undo). Alternatively shift `--ok-soft` toward a yellower green so the two never sit side by side looking the same.
- Severity: major. Effort: S.

**3. No drawings at all, and Vera is just a letter** (empty states on states-content; grown-ups page; sign-in; kid Home; Vera's `.mark`)
- Problem: the brief asks for a mascot and drawings, and the design has neither. Vera is a serif "V" in a circle (the standard says never a face). Empty states, "This part is for grown-ups", the brand-new Home and sign-in are text and one line icon. Adults read this as tidy. An 11-year-old reads it as a form, and the moments that should feel welcoming (first day, no wishes yet, a kid sent somewhere they can't go) feel bureaucratic.
- Fix: add a small set of 6–8 single-colour spot drawings in the icon set's line weight, inline SVG in the sprite using `currentColor` (CSP-safe), about 96–120 px. Use them for: first-day Home, empty Ideas, empty To do, empty wish list, grown-ups page, sign-in, Vera can't answer, and resting (a moon). Give Vera's mark a little character without a face, for example the leaf or sprig from the Seasonal icon set into the green disc beside the V, and use the same mark as the Telegram bot's avatar.
- Severity: major. Effort: M.

**4. The month grid is mostly grey, and "today" looks like a focus ring** (Plans, desktop and phone; dark Plans)
- Problem: only single-person events get a colour (Maya's Nutcracker). Everyone events and multi-person events (Mount St. Helens, Cannon Beach, Oaks Park) are beige-grey, so the family calendar has almost no colour. The phone dots are mostly grey. Today (Sat 3) is an empty cell with a heavy 2 px green box, which reads as selected or focused. Past events are dashed boxes with yellow text and look like errors.
- Fix: draw Everyone events in `--vera-soft` with a `--vera` left bar, and multi-person events with the first person's bar plus the avatar stack (already there). Mark today with only the filled green number disc plus a faint `--vera-soft` cell wash, and drop the box. Draw past events solid in `--paper-2` with `--ink-2` text and a "Rate" link. Then dashed edges and the 3 px ring stay for pending items and focus.
- Severity: major. Effort: M.

**5. Dashed lines mean six different things** (Ideas "not looked up" cards; Surprise tag; past calendar events; "Vera is thinking" bubble; setup step numbers; separators in every card)
- Problem: dashes appear on unknown ideas, surprises, past plans, pending replies, setup numbers and as the default card divider. A dashed edge stops meaning anything, and the surprise tag (which matters most to parents) blends in.
- Fix: reserve dashed for "not yet" only (not looked up, thinking). Make card dividers solid `--line` hairlines. Give Surprise a solid tag with its eye-off icon on its own token (for example `--surprise-soft` in a muted plum distinct from Alex's lilac). Draw setup step numbers solid.
- Severity: minor. Effort: S.

**6. "Needs a look" and "Could be better" are almost the same tag** (Status rows; Settings list; Settings "Reading this list" card)
- Problem: both are warn-brown text, one filled and one outlined. Settings needs a legend card to explain them, which shows the tags don't explain themselves. The one parent who looks at Status can't rank Sign-in above Backup at a glance.
- Fix: put a small `!` icon on "Needs a look" with a warn fill and a 1 px `--warn-line`. Show "Could be better" and "Not connected" in `--ink-2` on `--paper-2` with a hollow dot. Give their row tiles neutral `--paper-2` instead of yellow. The legend card can then go.
- Severity: minor. Effort: S.

**7. Serif digits inside small sans text** (to-do meta "Sun 27 Sep · 6 days late"; plan meta "2 h 5 min drive"; ideas drive line)
- Problem: because Fraunces Figures comes first in both stacks, every digit in a 14–15 px Atkinson meta line is a serif with a different weight and x-height. Up close the line jitters ("Mon 28 Sep", "5 days late"). The feature that makes $1.26 and the date tiles beautiful makes the small text look patched.
- Fix: put Fraunces Figures in the heading, display and `.dt` stacks only. Body and meta should use Atkinson with `font-variant-numeric: tabular-nums` where columns need it.
- Severity: minor. Effort: S.

**8. Dark mode: the warn surfaces turn muddy, and Send glares** (dark Home setup card; dark Plans banner and weekend columns; dark Settings top banner)
- Problem: `--warn-soft` #362B17 on #181713 reads as olive-brown dirt rather than a gentle "set this up", and the bright `--sun` Send is the loudest thing on the dark page by far.
- Fix: set the dark `--warn-soft` to a clearer amber-tinted surface (around #33291A with `--warn-line` #6A5428), and drop the weekend tint (see fix 1). Lower the dark `--sun` a step (around #E0B04A). Re-run the contrast table.
- Severity: minor. Effort: S.

**9. Nothing marks the happy moments** (Wishes and the kid's My wishes: "Yes!" tag; To do: ticked row; flash with Undo)
- Problem: a parent saying yes to Maya's sketchbook gets the same small green tag as "Working" on Status. Ticking off a to-do is a grey strike-through. The app has no moment of delight for a kid.
- Fix: give the "Yes!" wish answer its own treatment: `--sun` fill, `--on-sun` text and the gift icon, and a sun-tinted rank circle on that row. When a tick is done, fill the ring in `--ok` with a white check (with a one-off 150 ms scale that is skipped under reduced motion).
- Severity: minor. Effort: S.

## Missing
- The other three person colours (eight in the set, five drawn): avatars, bubbles, calendar bars and dark versions, checked side by side with Maya's pink and Alex's lilac, which are already close.
- Spot drawings for empty, first-day, grown-ups, resting and outage states (see fix 3), and an error page (404/500) in the same look.
- The app and home-screen icon (favicon, apple-touch, maskable), plus Vera's Telegram avatar, built from the house mark so the website and Telegram look like one product.
- A rule for idea photos. If Vera's lookups ever bring images, decide now whether cards show them (aspect ratio, radius, fallback to the kind tile) or never do.
- A forced-colours and high-contrast pass shown as a picture, because the tags and person colours carry so much of the look.
- How Vera's Telegram messages look (bold, emoji or none, how a plan card reads in text) so the tone and look match the website.
- A celebration or "all done" state for To do with nothing late, and for Status with nothing to check, so good days look good and not just empty.
- The Theo kid view, to confirm his orange works as the main colour on his pages as Maya's pink does on hers.

## One sentence
Give each signal colour one meaning: yellow only for Send and "set this up", mint only for "all good", no weekend tint. Then the calm palette tells the family at a glance what needs them.
