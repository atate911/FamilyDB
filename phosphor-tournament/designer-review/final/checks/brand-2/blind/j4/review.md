# Review: FamilyDB, designs P and Q

I looked at all six overviews (desktop, phone and dark for each design). I opened the full Home, To do and Plans pages on desktop and phone for both, Q's Ideas page on desktop, and the dark-mode phone Home for both.

The two designs share almost everything. The layout is the same: a left sidebar on desktop, and on phone a top bar plus a five-tab bottom bar (Home, Chat, Ideas, Plans, To do). Both use the same type, a serif for headings and a grotesque for body text whose zeros are slashed ("1Ø ideas", "$2.ØØ"). Both use the same palette: cream background, deep green, a mustard Send button, a colour for each person, and red for anything late. The copy and the order of the cards are the same too. So most of this review is about the places where they differ.

## P

**What it is**
A warm, calm, editorial design: cream paper, a serif "Good morning, Sam.", and a dark-green "Ask Vera" panel with a mustard Send button. The logo is a small green house with a yellow dot. Vera is shown as a white circle with a serif "V". Dark mode is a warm brown-black with the same green panel.

**What works**
- Home gets its order right. The greeting has two underlined links ("Roller rink tomorrow", "three to-dos are late"). Then come Ask Vera, Next up (a big calendar tile for SUN 4 OCT with "Tomorrow" and "Leave by 12:30 pm" chips), To do, and Just added to Ideas. The admin-only "Finish setting up" card sits in the right-hand column and says "Only admins see this."
- To do is clear for a child. Each overdue item has a red left bar, a big round tick, the person's coloured initial and a red "6 days late". Surprise items carry a "Surprise · hidden from Maya" chip. On desktop the add form has big person chips (Sam, Alex, Maya, Theo, Everyone) and a full-width green "+ Add" button.
- On phone, the Ask Vera chips are shortened to "Next weekend?" and "Remind me…", so they fit without truncating.
- The person colours are used the same way on every page (Sam blue, Alex purple, Maya pink, Theo orange), and the Settings page explains them in a "Colours in FamilyDB" card.
- Dark mode is even and comfortable. The red late bars and mustard Send button stay legible.

**What doesn't**
- The Plans calendar's colour code is ambiguous. The Oaks Park roller rink (Maya and Theo) is a pink block, the same pink as Maya's own Nutcracker. Shared plans and family plans are beige. Nothing on the page explains this.
- On phone the calendar uses bare coloured dots under the dates: pink, grey, and hollow circles on 29 Sep and 1 Oct. There is no key, so a 9-year-old can't tell which dot is theirs.
- Vera's "V" monogram is the same kind of circle as the family's S/A/M/T initials. In chat she reads as a fifth family member rather than the assistant.
- The slashed-zero body font ("about 2Ø min drive", "$2.ØØ daily limit") looks technical on a family page and slows reading for kids.
- The identity is pleasant but generic. Apart from the house logo, nothing here is particular to this app.

**Mark**
7/10. It is clean, consistent and child-readable, but the calendar's colour language is left unexplained, and the identity never becomes the family's own.

## Q

**What it is**
The same layout, palette and content as P, with a "friendly terminal" layer on top:
- The logo is a smiling computer monitor, and "FamilyDB" is followed by a green cursor block.
- "Vera is ready" is set in green monospace on a black pill.
- Vera's avatar is a black tile with green glyph lines and a ">" prompt. Settings describes it as "a little pane of glass full of glyphs".
- The Ask Vera panel is near-black green. In dark mode it has a glowing green border, and the date tile header turns bright mint.
- The Ideas page adds a green-on-black radar chart, "How far each idea is from home", with rings at 15 min, 30 min, 1 h, 2 h and 3 h and numbered dots keyed to a list.

**What works**
- The Plans calendar explains itself. Each block shows faces: an "M" for Maya's Nutcracker, an "M T" pair for the roller rink, and a house icon for Everyone. Shared plans are grey. A legend under the grid reads "One person's plan, in their colour · Several people: grey, with each face · Everyone · Already happened". On phone the bare dots become small face badges with the same legend, so a kid can find their own plans.
- Vera has a face of her own that can't be mixed up with a family member. It appears in chat, in Ask Vera and in the Status rows.
- The radar on Ideas is a real piece of information: it shows direction and drive time at a glance. It is also the kind of thing a 9- or 11-year-old will enjoy poking at.
- On phone, To do has a full-width title line ("4 open, 3 of them late. Tick one off when it's done."). The "OVERDUE · 3" and "NO DATE · 1" section labels are in small capitals, which separates them a bit more clearly than P's sentence-case labels.
- Dark mode is cooler and more distinct, and the green accents stay readable.

**What doesn't**
- The terminal look (monitor logo, blinking-cursor block, monospace status pill, green-on-black radar) leans toward "developer tool" and away from "family". A parent may read it as techy.
- The radar takes a large block of the Ideas page. The page grows from 1558 to 1882 px on desktop and from about 4100 to 5800 px on phone, which pushes the idea cards down. The radar's labels are tiny green monospace on black.
- On Home, the surprise chip is shortened to just "Surprise", which drops "hidden from Maya / Theo". The To do page keeps the full text, so the two pages disagree about what the chip says.
- The desktop To do "+ Add" button shrinks to a small pill, a weaker target for kids than P's full-width bar.
- On the phone calendar, "28 Sep" and "1 Nov" lose their month names and show only "28" and "1".

**Mark**
7.5/10. It is the same solid base as P, with a calendar that explains who is going, an assistant with a real face and one memorable data view. The terminal styling is a slightly odd match for a family.

## Between them

### 1. Which would you build for this family, and the three reasons that decided it.
**Q.**
1. **Plans tells you who is going.** Q puts faces in each calendar block, shows shared plans in grey and adds a legend, on desktop and on phone. P's pink roller-rink block reads as Maya's alone, and P's phone dots have no key. For kids checking "is this mine?", this matters more than anything else that differs between the two.
2. **Vera is distinguishable.** Q's glyph-pane avatar can't be mistaken for a family member in Chat, Home or Status. P's "V" circle can.
3. **The extras add information, not just decoration.** The Ideas radar answers "what's close?" visually, and the dark-mode glow marks where to talk to Vera. Everything else is the same page as P, so Q's additions cost little.

### 2. Which has the stronger identity, and does it cost anything in use?
**Q**, clearly. The smiling monitor, the cursor block after "FamilyDB", the green-glyph Vera and the radar give the app a recognisable character that P's house logo doesn't. Kids especially will remember "the one with the radar and the little screen".

The costs are real but small:
- The Ideas page is much longer, and its radar labels are tiny.
- The surprise chip on Home is cut to "Surprise".
- The overall tone drifts toward a tech product.

None of these breaks a task.

### 3. Where the other one is better
- **To do (desktop), add form:** P's full-width "+ Add" button is a bigger, clearer target than Q's small pill.
- **Home, Just added to Ideas and To do:** P's chip "Surprise · hidden from Theo / Maya" says who it is hidden from. Q's "Surprise" doesn't.
- **Ideas (phone and desktop):** P reaches the idea cards sooner because it has no radar block in the way.
- **Plans (phone):** P keeps "28 Sep" and "1 Nov" in the grid. Q drops the month names.
- **Logo:** P's house reads as "family" more naturally than a computer monitor.

### 4. What is still wrong with Q, most important first
1. **Wishes isn't in the phone tab bar.** The bottom bar is Home, Chat, Ideas, Plans, To do, so the kids' own wish lists aren't one tap away on the device they'll use most. P has the same gap.
2. **The surprise chip is inconsistent.** Restore "Surprise · hidden from Maya" on Home so it matches To do and says who can't see the item.
3. **The radar is hard to read.** Make its labels larger and higher-contrast, or collapse it on phone so the idea cards come first.
4. **The slashed-zero body font.** "1Ø", "2Ø min" and "$2.ØØ" look technical and slow reading. Use a font with plain figures for body text and keep monospace for Vera's status only.
5. **Small to-do button and calendar month labels.** Restore the full-width "+ Add" button on To do, and put "Sep" and "Nov" back on the phone calendar's spill-over days.
