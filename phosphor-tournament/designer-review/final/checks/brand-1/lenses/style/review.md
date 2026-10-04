# Review: visual style and identity

## Verdict
**8 / 10.** This is one thing made with care. Warm paper, soft Fraunces headings, Atkinson for reading, a colour for each person used the same way everywhere, and a small set of phosphor-on-glass touches add up to a look a family would find calm, friendly and theirs. It is not a "dashboard". The few places where it slips are where the identity is thinnest: Vera's small glyph screen reads as a dark smudge rather than a someone, the calendar breaks its own person-colour rule, and in dark mode the Ask card, the most important thing on Home, sinks into the page.

**Optimise before building?** No. The system is sound and the fixes below are token-, class- and asset-level changes, which are easy to make during the build without redesigning anything.

## Protect
1. The Kitchen Table palette (cream `--paper`, `--card`, `--paper-2` sidebar) with ink text and a single Vera green. On every page it reads warm, quiet and grown-up without feeling corporate.
2. Person colours as slots. Avatars, chat bubbles (Alex's lilac in Chat), dots and event fills mean "this is a person" all through the app, and red is kept for "late". Home To do's 4 px red rule plus "6 days late" is the clearest status cue in the set.
3. The Fraunces / Atkinson pairing: the soft `h1` ("Good morning, Sam.", "Chat with Vera") and Fraunces Figures in date tiles and money (Status "$0.00", "$1.26") give the app its homely, printed feel.
4. The Ask Vera card on Home (deep green, sun-yellow Send, white starter pills). It is the one loud surface, and it rightly makes "talk to Vera" the first thing you see.
5. The brand moments: the sign-in glass pane with the glowing monitor mark and "awake, Saturday 3 October", the 404 pane, and the wordmark's lit cursor. They are small, have character, and are used sparingly.
6. The rhythm: one plain sentence under each `h1`, then cards with 18 px radius on even 16/24 px gaps. Status ("Vera is ready, and well under budget." then the cards) is the model to follow.

## Fix, ranked

**1. Vera's glyph screen reads as a broken thumbnail** (Chat: the 32 px `.vs` beside every Vera bubble; Home: Ask card and "Vera today" row; Status: Vera row; kid Chat: empty-state screen)
- Problem: at 32–40 px, columns of dim green glyphs under scanlines and a 0.55 px blur come out as a near-black square with noise. In the Chat screenshot it looks like an image that failed to load, not like the assistant the family talks to every day. Vera is the closest thing the app has to a mascot, and for Maya (11) she has no presence at all: the warmest moment in the product, "This is your own chat with Vera", is anchored by a dark speck.
- Fix: keep "never a face", but make the screen read at its size. Drop the blur at 24/32 px. Use 3 columns × 4 rows of larger glyphs at 32 px (5 × 12 is for 40 px and up). Raise the bright share to about one in three, and give the square the same 1 px `--glass-line` rim and soft phosphor glow that the mark gets on the sign-in pane, by day too. At 40 px and above, add one fixed bright "signature" glyph (e.g. a `>_` row) so the screen is recognisably *her* every time. Check it at 1× on a phone screenshot, not only zoomed in.
- Severity: major. Effort: S.

**2. Calendar events for several people take the first person's colour** (Plans month grid: "Oaks Park roller rink" Sun 4 is Maya's pink `.p3`; "Silver Falls hike" Thu 1 is Sam's `.p1`)
- Problem: STANDARD §8 says one person gives that person's colour and several or Everyone give neutral with avatars. Instead, Oaks Park for Maya *and* Theo is the same pink as Maya's own "Nutcracker" on the 17th. Theo, scanning for his colour, won't see his roller-rink day, and the "colour = a person" promise breaks on the page that relies on it most. The phone month dots inherit the same error.
- Fix: the `calendar_week` macro emits `.p0` whenever a plan has more than one person, and keeps the avatars inside the event (it already draws M/T). On the phone, show one dot per person (up to three) rather than one dot in the first person's colour.
- Severity: major. Effort: S.

**3. Dark mode: the Ask card disappears** (dark Home, desktop and phone: Ask Vera card)
- Problem: `--ask-bg` at night is #0A0E0D on `--paper` #0C100F, so a 1 px rim is all that separates them. By day the card is the page's anchor. At night it is a faint outline, and the cream "Next weekend?" starter and yellow Send float with nothing holding them. The one thing a parent comes to Home for loses its weight, and the dark theme looks less finished than the light one.
- Fix: give the dark Ask card a real green glass: `--ask-bg` about #0F2A22 (still more than 12:1 with the cream ink), the `--vera-line` rim, and the same faint inner phosphor glow as `--vera-glow`. It should be the brightest-edged card on the page at night, as it is the darkest by day.
- Severity: major. Effort: S.

**4. Slashed zeros sit next to unslashed ones in the same figure** (Status: "$0.00 of your $2.ØØ daily limit"; Home: "Your limit is $2.ØØ a day"; Chat: "6:ØØ pm"; Ideas lede "1Ø have hours")
- Problem: the big figure is Fraunces Figures (round zero), and the line beside it is Atkinson (slashed zero). On Status the two styles of zero meet in one sentence. In money and times the slashed Ø reads as a code or a typo to non-technical parents and to kids. It is the one detail that makes the app feel like software rather than the kitchen table.
- Fix: set `--font-num` (Fraunces Figures) on every money amount and clock time in running text through a `.num` span from the macros (amounts and times are generated, so this is one place). Or subset an unslashed zero into the body face. Keep the slashed zero only in `.code`.
- Severity: minor. Effort: S.

**5. In dark mode the family's primary buttons become bright cream slabs** (dark To do: full-width "Add"; dark Ideas "Add an idea"; dark Plans "Add a plan")
- Problem: `--primary` turns cream at night, so the To do quick-add's full-width button is the brightest thing on a charcoal screen, brighter than any content and harsh at bedtime. It pulls the eye away from the overdue list.
- Fix: at night, primary is `--card`-raised with a cream 1.5 px edge and cream text, or a muted cream (#CFC8B8) fill. Do not make the To do "Add" button full width on desktop. Size it to its label like "Add an idea".
- Severity: minor. Effort: S.

**6. The drive-time instrument collapses into one blob** (Ideas: "How far each idea is from home", dots 2–6)
- Problem: five ideas between 19 and 27 min south pile into a single cluster labelled "2–6". With dots 1, 7–10 scattered, most of the square is empty rings. As the hero visual of Ideas it looks unfinished, and the list next to it does all the work.
- Fix: use a square-root scale with its first ring at 15 min rather than 30 min so the near cluster spreads out, and fan same-bearing dots out along the ring by a few degrees. Or label clustered dots individually with short leader lines. If a family's ideas all fall within one ring, hide the instrument and show the list full width.
- Severity: minor. Effort: M.

**7. Idea titles change face between pages** (Ideas cards: Fraunces "Lego set for Theo"; Home "Just added to Ideas" and phone Ideas rows: Atkinson bold)
- Problem: the same object wears two typefaces, so the cards on Ideas read like headings and the same thing on Home reads like a list item. It is small, but it is the kind of seam that makes a design feel assembled rather than made.
- Fix: pick one. Atkinson 700 at 17 px matches every other item title (plans, to-dos, wishes). Keep Fraunces for card and page headings only.
- Severity: minor. Effort: S.

**8. The kid's to-do row looks unbalanced** (kid Home phone: "My to-dos", "Pack your swim bag")
- Problem: Alex's avatar floats mid-height on the far left with a wide empty gutter. The dashed "Not done yet" pill and the "Tell Vera I did it" link stack beneath, so the row is tall, loose and lopsided next to the tight wish rows above it. This is Maya's page and her own to-do looks like the least finished thing on it.
- Fix: align the lead avatar to the title's first line (top-align as in `.item`), cut the gap to `--s3`, and put "Not done yet" and "Tell Vera I did it" on one line where they fit.
- Severity: minor. Effort: S.

**9. Surprise tags wrap into two-line lozenges in narrow tiles** (Home: "Just added to Ideas", Lego set tile; dark phone Home To do, "Surprise · hidden from Maya")
- Problem: the pill wraps to "Surprise · hidden / from Theo" inside a big rounded outline, which looks like a misplaced button and crowds the tile.
- Fix: in compact tiles, show the eye-off icon plus "Surprise". Keep "hidden from Theo" in the spoken label and on the full card. Or let `.tag` wrap as plain text with no outline.
- Severity: minor. Effort: S.

**10. The kid's empty chat has two equal greens** (kid Chat: "What can we do this weekend?" starter and "Send")
- Problem: the filled dark-green starter and the filled Send button compete. A kid reads two primary actions where the design means one.
- Fix: draw starters with the outline style used everywhere else (white fill, edge), and leave Send as the page's one primary.
- Severity: minor. Effort: S.

## Missing
- A real favicon and home-screen icon rendered and checked at 16 and 180 px. The standard lists them, but none is shown, and the mark's smile at 16 px is the riskiest crop.
- Vera's screen in `--busy` and `--off`, drawn at 32 px on both themes, so the "answering" motion and the dark screen can be judged as images rather than described.
- Any illustration or warmth for empty and celebratory moments: all to-dos done, a wish answered "Yes!", a plan rated "Loved it". Today these are text only. A small set of line spot drawings in the icon stroke would make kids smile without breaking the brand rule.
- What happens to the palette past five people: slots p5–p8 next to the current four on one calendar and in a chat, to show they stay distinct (teal p5 vs Vera's green is the obvious clash).
- Dark mode for the brand moments (sign-in pane, 404, first empty day): glass on charcoal is called out as low contrast, so it needs a drawn check.
- Print or "send to fridge" styling for the plans list or a to-do list, if the family ever prints. It fits the Kitchen Table idea.
- A forced-colors (Windows high-contrast) render of person colours and tags, since so much meaning is carried by tints.
- Photo or map imagery for an idea's own page: the design shows none, and the real app will want to know whether ideas ever carry a picture.

## One sentence
Make Vera's little screen read clearly as *her* at 32 px (crisper, fewer and brighter glyphs, a lit rim, one signature mark), because she is the face of the whole product and right now she looks like a broken image.
