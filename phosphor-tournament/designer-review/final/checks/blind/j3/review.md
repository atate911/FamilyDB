# Review: FamilyDB designs P and Q

I looked at both overviews and at the full desktop and phone pages for Home, To do, Plans, Ideas and Chat in both designs. For Status and Settings I used the overviews.

## P

**What it is**
A warm, cream-and-forest-green design with a serif display face (Fraunces-like) for headings and a sans for body. On desktop it has a left sidebar ("Behind the scenes" holds Status and Settings) and the signed-in person's card sits partway down that sidebar. On phone a six-item icon tab bar sits under the header (Home, Chat, Ideas, Plans, To do, More). Home is a dashboard: a dark-green "Ask Vera" box with a yellow Send button, then Next up, To do, Just added to Ideas, and a right column with Finish setting up, Wish lists and Vera today. Colour is used heavily by kind of thing: Day trip is blue, Show is pink and Activity is red, on the calendar, in Ideas and in Coming up.

**What works**
- The visual language is consistent and friendly. The tear-off date tiles (SUN 4 OCT) on Home and in Plans › Coming up give a clear rhythm.
- The desktop Plans calendar reads at a glance. Each event chip carries its time and its kind colour, and today's cell is boxed and labelled "TODAY". Past plans show a "Rate it" prompt right on the chip.
- On desktop, Ideas cards carry two tags each: kind ("Restaurant", "Outing") and status ("Planned · Sat 17 Oct", "Not looked up yet"). This makes a 12-card grid easy to scan.
- The desktop To do page puts the whole add form on one row (text, Who, Due, Remind, Add), and the overdue rows have a red left rule with "6 days late" in red.
- The phone tab bar includes Ideas, so all of the family's main sections are one tap away.

**What doesn't**
- All times use a slashed-zero numeral: "13:ØØ", "Ø9:ØØ", "19:ØØ", and "10:00 to 14:00" in Chat. They look like errors or codes, and a 9-year-old will stumble on them.
- Several things break at phone width:
  - Plans: today's cell is clipped to "3 TOD".
  - To do: the Open / Done / Cancelled / All switch wraps, leaving "All" alone on a second line inside the pill.
  - Home: the suggestion chips run off the edge ("Remi…").
  - Chat: the "Writing as" chips wrap, leaving Theo on his own row.
- Phone Ideas puts a full form (Search, Kind, Status and For dropdowns, then a Show button) above the first idea, so the list starts more than a screen down. The page is the longest in the set (about 6,600 px).
- Chat contradicts Plans. Alex says "Put the hike on Saturday at 10" and Vera answers "Done: Silver Falls hike, Saturday 10:00 to 14:00", but the calendar and Ideas show Silver Falls on Thu 1 Oct.
- Chat's "Writing as Sam / Alex / Maya / Theo" switch lets anyone post as anyone, kids included, without signing in.
- The Status page shows a model table with "gpt-6-luna / OpenAI" and three red "None" pills under "Backup if it fails". That is engineer language on a family app, and the red reads as broken.
- The Settings banner is a pink-red alert block with a padlock about a password. That is too alarming for what is really a setup step.
- The To do date field is a raw "mm/dd/yyyy" picker, while the rest of the app uses 24-hour times. To do also offers a "Remind" checkbox even though the banner beneath says reminders can't reach anyone.
- The "How did it go?" faces in Plans have no labels, so the meaning rests on tiny line faces.

**Mark: 6/10.** The visual system is attractive and the desktop calendar and idea cards are strong, but the time numerals, the phone layout breaks and the chat/plan contradiction make it feel unfinished.

## Q

**What it is**
The same family of palette, typefaces and dashboard structure, but more restrained. Kind colours are mostly dropped for neutral beige icon tiles. The sidebar gains a "Vera is answering" status pill under the logo, text badges beside each section ("2 to rate", "3 late", "1 to decide", "1 to check") and a Family page. On phone there is a five-item bottom tab bar (Home, Chat, Plans, To do, More). Times are written as "1 pm" and "9 am", and the date numerals are old-style serif.

**What works**
- The copy is plain and human throughout:
  - Home: the greeting's "Roller rink tomorrow" and "three to-dos" are links.
  - Next up has a "Leave by 12:30 pm" chip.
  - To do says "No reminders are set. Reminders go by Telegram, which isn't connected yet."
  - Status replaces the model table with "How each part is doing": Vera Working, Spending Working, Sign-in Needs a look, Backup Could be better, Telegram Not connected. Each row has its own action button.
- To do is compact and well built. There is one input plus a "Who, when, reminder · Sam · No date · No reminder" disclosure. Each row shows person, date, "6 days late" and reminder state on one line. "Surprise · hidden from Maya" is shown as a dashed tag on the birthday present.
- Rating is kid-friendly. "How did it go?" uses large faces labelled "Loved it / OK / Not great", both on Home (Silver Falls hike) and in Plans.
- On phone, Home folds "Finish setting up" into a single "3 setup steps left · Continue" bar, and the three Ask Vera chips stack instead of running off-screen.
- Phone Ideas is a compact list. Filters collapse into one "Filter · Any kind · Anyone · Any status ›" row. Each item shows who, drive time with compass direction, and a date chip ("Sat 17 Oct", "Went Thu 1 Oct").
- Data is consistent. Chat says "Put the hike on Thursday at 10", which matches the calendar. Cannon Beach spans Sat–Sun as one bar on the desktop calendar.
- Chat shows "Writing as Sam · Not you? Sign out" instead of an impersonation switch. It also tells the family "Parents can read Maya's and Theo's chats. The kids see a note saying so."
- Settings has a "Colours in FamilyDB" legend: a person's colour, green for Vera, and "Red only means late, or broken".

**What doesn't**
- Ideas is not in the phone tab bar; it is behind More. On the Ideas page no tab is highlighted.
- Phone Plans is out of order. The month grid sits at the bottom, below "How did it go?", cut off from its own "‹ October 2026 › Today" header at the top. There is no Month/List switch, and days carry only grey or pink dots.
- On the desktop calendar most chips are the same grey-beige (Oaks Park, Mount St. Helens, Cannon Beach), and only Nutcracker is pink. Oaks Park is "Maya and Theo" yet grey, so the colour rule promised in Settings isn't visible. "Mount St. Helens day…" is truncated.
- The text areas show browser resize handles: the Ask Vera box on Home and "Write to Vera…" in Chat. Placeholders are cut off: "e.g. that ramen place Alex men".
- The sidebar carries four differently coloured text badges plus a green status pill, so the badges compete with the section names.

**Mark: 8/10.** It keeps the same appealing look while making each page clearer, calmer and correct on phone, and the remaining faults are mostly placement and polish.

## Between them

### 1. Which would I build for this family?

**Q.** Three things decided it:
1. **It works on phones, where the family will mostly use it.** Q's phone pages have no clipped "3 TOD", no wrapped tab switch and no chips running off-screen. Ideas and To do are compact lists rather than long forms, and setup is folded into one bar.
2. **The kids can read and use it.** Times read "1 pm" instead of "13:ØØ", the rating faces are labelled "Loved it / OK / Not great", and the copy and status rows are plain words instead of "gpt-6-luna" and red "None" pills.
3. **It is honest and consistent.** Chat agrees with the calendar, nobody can post as someone else, and reminders are shown as not set rather than offering a "Remind" box that does nothing.

### 2. Where P is better

- **Plans, desktop calendar:** P's kind-coloured chips (blue Day trip, pink Show, red Activity) with times and a labelled "TODAY" cell scan faster than Q's mostly grey chips.
- **Ideas, desktop cards:** P's two coloured tags per card (kind plus "Planned · Sat 17 Oct" / "Not looked up yet") make the grid easier to sort by eye.
- **Phone navigation:** P's tab bar includes Ideas, and Q's does not.
- **Plans, phone:** P keeps the Month/List switch, with the calendar directly under its month header.

### 3. What is still wrong with Q, most important first

1. Ideas is missing from the phone tab bar. It is a core section and the kids' main way in, and it should replace or join one of the five tabs.
2. Phone Plans needs reordering: put the month grid right under "October 2026", and bring back the Month/List switch.
3. Calendar colour has no visible rule. Either colour chips by person, as the Settings legend promises, or by kind as P does. Also stop truncating titles like "Mount St. Helens day…".
4. The input polish is unfinished: browser resize handles on the Ask Vera and chat text areas, and cut-off placeholders ("…Alex men").
5. The sidebar is noisy. Four multi-coloured text badges plus the "Vera is answering" pill compete with the section names, so they should be reduced to one style, or only the urgent ones kept.
