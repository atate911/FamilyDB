# Review: FamilyDB designs P and Q

The two designs share most of their structure: the same left sidebar with "Behind the scenes" group, the same cream paper background, deep-green primary, mustard Send button, serif display headings over a sans body, the same per-person colours (Sam blue, Alex purple, Maya magenta, Theo orange, Everyone = grey house), and the same bottom tab bar on phone. The differences are in identity and a handful of components, so most of this review is about those.

## P

**What it is**
A warm, calm, "kitchen-table" interface. The logo is a green rounded square with a little house and a yellow dot. Vera is a white circle with a serif "V". "Vera is ready" is a soft mint pill. In dark mode it becomes a warm brown-charcoal with the same green and mustard accents.

**What works**
- Home is well judged on desktop. The greeting sentence carries two underlined links ("Roller rink tomorrow", "three to-dos"). Ask Vera is the one solid green block, with three suggestion chips. Next up has a calendar-tile date ("SUN 4 OCT") plus "Tomorrow" and "Leave by 12:30 pm" chips. The right column, with Finish setting up, the hike rating, Wish lists and Vera today, is clearly secondary.
- To do: overdue rows have a red left rule and red "6 days late" text. Each row shows the person's avatar and name, the date, and "No reminder". The "Surprise · hidden from Maya" chip says exactly who can't see the item, on Home, To do and Ideas alike. Desktop's full-width green **Add** bar is hard to miss for a kid.
- Ideas desktop: a clean 3-column card grid with serif titles. "Not looked up yet" cards (Lego set, Board game night) get a dashed border, a nice quiet signal.
- Rating ("Loved it / OK / Not great" with faces) is big, friendly and readable by a 9-year-old.
- Phone: everything stacks sensibly, tap targets are large, and the person chips wrap onto two rows. Status keeps the three cost tiles (Cost $1.26 / Questions 6 / A usual day 4¢) side by side.

**What doesn't**
- Plans colour-coding is inconsistent. On the desktop calendar, Oaks Park roller rink (Maya **and** Theo) is filled pink in Maya's colour, while Silver Falls hike (Sam and Alex) is neutral beige. On phone the month grid reduces plans to unlabelled dots (pink, grey, hollow) with **no legend**, so a kid can't tell what a dot means.
- The identity is generic. The house-icon logo and the "V" monogram could belong to any family-organiser template, and nothing on the page is distinctly "Vera".
- Phone Home: the setup banner and Ask Vera push Next up partly under the tab bar on first view. The To do page puts "Add a to-do" at the very bottom on phone (on desktop it's at the top).
- Small craft slips: "Add a to-do" in the serif sets tight enough to read "Adda to-do". "28 Sep" and "1 Nov" wrap inside phone calendar cells. On phone the Add button stops short of the input's right edge.

**Mark: 7/10.** Clear, warm and competent on every page, but its Plans colour logic contradicts itself and nothing about it would be remembered.

## Q

**What it is**
The same layout and palette given a "friendly terminal" identity. The logo is a black square holding a smiling green-outlined monitor. "FamilyDB" is followed by a green cursor block. "Vera is ready" sits in a black pill in green monospace. Vera's avatar is a little black tile of green glyphs and a prompt (">_"). The Ask Vera panel is darker (near-black green). Ideas gains a green-on-black radar, "How far each idea is from home". In dark mode the whole thing turns cool green-black, and Ask Vera gets a green outline glow.

**What works**
- The identity is coherent and is explained in the product itself. Settings → "Colours in FamilyDB" says "Vera is a little pane of glass full of glyphs. Green light belongs to her… The smiling monitor is the app itself, never Vera." The logo, the status pill, the Vera avatar in chat and on Status, and the radar all speak that one language.
- Plans is better worked out than P's. Each calendar entry carries faces: M/T on Oaks Park, a house icon on Mount St. Helens and Cannon Beach. Multi-person plans are neutral, consistent with a legend under the grid: "One person's plan, in their colour · Several people: grey, with each face · Everyone · Already happened". On phone the month grid shows the actual faces and house icons instead of anonymous dots, plus the same legend. That is much easier for the kids to read.
- The Ideas radar (desktop) puts "how far" into one picture, with rings at 15 min / 30 min / 1 h / 2 h / 3 h, compass points and a numbered key listed nearest first. It is something kids would actually enjoy reading. On phone it's sensibly moved below the idea list instead of blocking it.
- Desktop To do: the uppercase tracked "OVERDUE · 3" / "NO DATE · 1" group labels separate the groups more clearly than P's sentence-case ones.
- Everything P does well (Home hierarchy, rating faces, overdue treatment, setup card) is kept intact.

**What doesn't**
- The terminal register (black pill, monospace "Vera is ready", ">_" glyph avatar, CRT-green radar) leans toward a developer tool. It is a slightly odd fit for a family with a 9-year-old, and the black "Ready" pill is the loudest object in the phone header, louder than the page title's actions.
- The radar is costly. It interrupts the desktop Ideas grid after the first row and adds roughly 1,700 px to the phone Ideas page (5,820 px vs P's 4,112). Its point labels and ring labels are tiny green monospace. The numbers 1–10 follow distance order, not the card order, so you have to cross-reference the key.
- Home shortens the chip to just "Surprise" on the to-do and the Lego idea, losing "hidden from Maya/Theo", which is the part that matters. To do and Ideas still show it in full, so it's also inconsistent.
- Status on phone stacks the three cost tiles one per row, making a long page longer (5,146 px vs 4,818).
- The desktop To do **Add** is a small pill rather than a full-width bar, weaker as the page's main action. The calendar wraps "28 / Sep" and "1 / Nov" onto two lines in the cells. It shares P's tight "Adda to-do" serif heading.

**Mark: 7.5/10.** It is the same solid system with a memorable, self-consistent personality and a clearer Plans calendar. The personality is a little techy for kids, and the radar costs space.

## Between them

### 1. Which would you build for this family?
**Q.** Three reasons decided it:
1. **Plans is legible to the kids.** Faces and house icons on calendar entries, a written legend, and multi-person plans that don't borrow one child's colour. P's phone calendar is unlabelled dots, and its desktop paints a Maya-and-Theo plan in Maya's pink.
2. **Vera is a recognisable character.** The glyph tile is the same in Ask Vera, in every chat message, on Status and on Home's "Vera today". A child can see at a glance which messages are Vera's. In P, Vera is a generic "V" circle.
3. **It costs almost nothing in the core flows.** Home, To do, Chat and Settings are effectively P's pages. The identity sits in the header, the avatars and one panel on Ideas, so the family loses none of P's clarity.

### 2. Which has the stronger identity, and does it cost anything?
**Q, clearly.** The smiling monitor, the blinking-cursor block after "FamilyDB", the green-on-black "Vera is ready" pill and the glyph avatar would be recognised as "our app" from across the room. P looks like a well-made template. The cost is real but modest:
- the monospace/terminal tone reads as techy rather than homely;
- the black header pill grabs attention it hasn't earned;
- the radar adds a lot of length on phone and uses tiny text;
- in dark mode the black pill nearly disappears into the dark header.

### 3. Where is P better?
- **Home → Surprise chip:** P says "Surprise · hidden from Maya"; Q's Home says only "Surprise".
- **To do (desktop) → Add button:** P's full-width green bar is a stronger, more kid-proof primary action than Q's small pill.
- **Ideas (desktop):** P's uninterrupted 3-column grid scans faster than Q's grid broken by the radar block. P's serif card titles are also warmer than Q's sans.
- **Status (phone):** P keeps the three cost tiles in one row; Q stacks them.
- **Vera's avatar for young kids:** P's friendly "V" is less cryptic than a ">_" glyph tile.

### 4. What is still wrong with Q, most important first
1. **Home's "Surprise" chip drops who it's hidden from.** Use "Surprise · hidden from Maya" everywhere. Secrecy is the one thing on that chip a parent needs to trust.
2. **Tone down the terminal cues where kids look.** Swap the black monospace "Ready" pill for a quieter one (P's mint pill works). Keep the glyph and green for Vera herself, not for system status.
3. **Make the radar earn its space.** Use larger labels, label the dots with names or icons rather than distance-rank numbers, and make it collapsible on phone (it adds about 1,700 px).
4. **Make To do's Add the obvious primary action** (full-width, as in P). On phone, put the Add a to-do form at the top as on desktop, not after the list.
5. **Craft fixes:** stop "28 Sep" and "1 Nov" wrapping in calendar cells, fix the tight "Adda to-do" serif spacing, and keep the Status cost tiles in one row on phone.
