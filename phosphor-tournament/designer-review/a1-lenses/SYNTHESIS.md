# Kitchen Table (green): thirteen lenses, merged

Thirteen fresh reviewers, each with one lens, looked at the seven A1 pages on desktop and phone and
read the source: generalist, visual style, design system, interaction, typography, usability,
skeptic, a parent, a kid (8 to 13), accessibility, copy, a front-end engineer and a phone-first
designer. All thirteen answered **Optimise before building? Yes.**

| Lens | Mark | Their one change |
|---|---:|---|
| Generalist | 7 | Design the phone as its own layout, role-aware, drawn first for Maya |
| Visual style | 7 | Give Vera a face (declined, see decisions) |
| Design system | 6.5 | One component each: item row, banner, to-do row, composer, state tags, on real scales |
| Interaction | 7 | On the phone, the thing people came to act on comes before forms and filters |
| Typography | 7 | One lining, tabular, unslashed figure style for every number |
| Usability | 7 | "Who is writing" must be explicit and pick the right conversation |
| Skeptic | 6 | Test every page on a phone with a real family's worth of data |
| Parent | 7 | Keep every privacy and "will this reminder reach anyone" line on the phone |
| Kid | 6 | Design the screens Maya and Theo see; hide surprises; "Ask a parent" |
| Accessibility | 6.5 | `--ink-3` to #596263 and field edges to #8A806C |
| Copy | 7 | One word for each thing, everywhere |
| Engineer | 7 | No inline styles; self-host the fonts |
| Phone | 6 | Bottom tab bar; lists start in the first screen; calendar becomes a list |

Mean 6.7. The blind judges, comparing it with nineteen other designs, gave it 8, 8 and 9: it is
the strongest of the set, and these lenses say how much further it can go.

## Protect (named by most lenses)

- Home: the dark green **Ask Vera** card, first on the page, with the yellow Send and the starters.
- Home: the greeting and its **one-sentence summary of the day**.
- The **date tiles** (SUN / 4 / OCT) on Home and Plans.
- To do: the **Overdue** group with "6 days late" written out and the owner's face and name.
- Settings: **one line per section saying how it stands**, the tags, and the "Reading this list" key.
- Status: the **plain verdict** first and the **Spent today** bar with "a usual day" marker.
- Plans: **How did it go?** with three big labelled faces.
- Chat: the **receipt card** that links to what Vera made, and the per-person colours everywhere.
- Fraunces headings with Atkinson Hyperlegible at 17 px, 44 px targets, focus always visible,
  every form working with no script, and the plain, honest voice.

## Fix (grouped; who raised it)

1. **The phone is its own layout** (generalist, phone, interaction, usability, skeptic, parent,
   style, type, system). Bottom tab bar, role-aware; the list people came for inside the first
   screen; tools and filters folded into `<details>`; Settings rows and the Status table re-laid
   for 390 px; Home in a phone order; ideas as compact rows; chips that wrap.
2. **The phone calendar shows nameless bars** (generalist, style, interaction, skeptic, access,
   engineer, phone, parent, kid). Phones open on the list; the grid's day cells become links with
   dots and a spoken label; multi-day plans as one bar.
3. **No kid view** (every lens, as a fix or as missing). Kid Home, kid Chat, Wishes with ranking
   and the parents' answers, the More page, kid sign-in, a friendly "for grown-ups" page.
4. **Missing states** (eleven lenses). Daily limit reached, Vera can't answer, a message pending
   and failed, after-action flash with Undo, form errors, empty first day, no results, long and
   busy content.
5. **Reminders and what can't work** (interaction, usability, parent, access, engineer, phone,
   copy). Reminder state visible at every width; "Remind" disabled with the reason while Telegram
   isn't connected; bells only where a reminder is set.
6. **Numbers** (generalist, style, type, parent, kid, skeptic). Times, money, counts and day
   numbers in one lining, tabular figure style without a slashed zero.
7. **The system** (system, type, style, access). Radius, spacing and type scales; a 14 px floor;
   one item row, one to-do row, one banner with four tones, one composer, one state-tag vocabulary;
   saturated colour kept for people (and Vera's green), kinds neutral with icons; red only for
   late text and broken things.
8. **Contrast and controls** (access, style, usability). `--ink-3` #596263; field and tick edges
   #8A806C; visible skip link; past plans without opacity.
9. **Who is writing** (usability, parent, kid, interaction, skeptic). Never post a kid as a parent.
10. **Chips that send half a sentence** (interaction, usability, access, engineer). Only a
    complete question sends; the stems fill the box.
11. **Chat waiting and long threads** (interaction, usability, parent, kid, engineer, phone,
    skeptic). "Vera is thinking..." instead of "Reload if nothing shows"; the latest 30 messages;
    the box pinned on the phone.
12. **Pages that disagree about health** (generalist, interaction, skeptic, copy). One state per
    area, shown the same way on Status, Settings, Ideas and the header pill.
13. **Words** (copy, kid, parent, usability, system). One term per thing; no installer, bot,
    cache or model talk where a family reads; Status leads with money in words.
14. **Build-safety** (engineer, style, type). No inline styles; self-hosted fonts; one icon sprite.
15. **Privacy and surprises** (parent, kid). The "parents can read the kids' chats" line on every
    width and inside the kid's own chat; gifts marked as surprises and left out where a kid reads.
16. **Dark mode** (generalist, style, system, skeptic, access): phones at bedtime.

## Decisions taken in the synthesis

- **Vera is not drawn.** The style lens asked for a character. The project's style guide records
  the opposite on purpose (Vera is felt, not shown), and a drawn figure would fight the family's
  freedom to rename her or switch the persona off. She keeps a small mark: her initial in her green,
  taken from her name, and her words.
- **Numbers in Fraunces lining tabular figures**, Atkinson for words. Accessibility liked the
  slashed zero; three lenses read it as an error in times and prices. Codes and keys keep it.
- **Kinds go neutral; people keep colour**, and calendar events take the colour of who they are for.
- **Twelve-hour clock** in the mockup (a family in Washington State); the standard says times follow
  the family's clock setting.
- **Settings stays admin-only** (that is how the app works); the line says who can change it and
  how to add another admin, rather than "only Sam".
