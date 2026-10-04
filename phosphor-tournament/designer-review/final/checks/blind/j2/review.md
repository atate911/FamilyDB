# Review: FamilyDB, designs P and Q

Both designs share the same base: a warm cream page, a deep green brand, a serif for headings (Fraunces-like), and a grotesque for body text. Both have a left sidebar on desktop, an "Ask Vera" green hero with a yellow Send button, date-tile lists and a month calendar. The differences are in the details, and the details decide it.

## P

**What it is**
A calm, mostly neutral take. Colour is used sparingly: beige icon tiles, one green for the brand and "Tomorrow", and red only for lateness. Every page opens with a plain-English summary line. On Home, "Roller rink tomorrow" and "three to-dos" in that line are underlined links. On phone, navigation moves to a bottom tab bar (Home, Chat, Plans, To do, More), and the "Finish setting up" card shrinks to a one-line "3 setup steps left · Continue" banner at the top of Home.

**What works**
- **Privacy for the kids is designed in.** "Lego set for Theo" carries a dashed "Surprise · hidden from Theo" chip on Ideas, and "Buy Maya's birthday present" carries "Surprise · hidden from Maya" on To do and Home. This app is used by a 9- and 11-year-old, so this is the most important detail in either design.
- **The density is right on phone.** On To do, each item is one tight card with the owner, date, red "6 days late" and "No reminder" on two lines. The add form is one field plus a "Who, when, reminder · Sam · No date · No reminder" disclosure, not a stack of form fields. Phone Plans puts "Coming up" and "How did it go?" before the calendar, and the calendar becomes a compact grid with dots.
- **The rating buttons have labels.** "Loved it / OK / Not great" sit under the faces on Home and Plans, which a 9-year-old can read without guessing.
- **The calendar is honest.** Cannon Beach is one bar spanning Sat 24 to Sun 25 ("Sat 8 am to Sun"). Past plans that need a rating show as dashed tiles with "How did it go?". Times are 12-hour ("1 pm", "7 pm"), which suits a family in Vancouver, WA.
- **Status shows up in the nav.** Sidebar badges read "2 to rate", "3 late", "1 to decide" and "1 to check", so the menu doubles as a to-do summary. The "Vera is answering" pill is always visible.
- **The content holds together.** In Chat, Alex says "Put the hike on Thursday at 10", Vera confirms "Thursday 1 October, 10 am to 2 pm", and the calendar shows it on Thu 1.

**What doesn't**
- **It's visually flat.** On Ideas, all 12 cards use the same beige icon tile and grey kind label ("Outing", "Event", "Seasonal"), so the grid scans as a wall of identical cards. Most calendar events are the same grey-beige. Only Nutcracker is pink, and it's not clear why.
- **Some sentences are long and adult.** One example is the Status hero: "Nothing spent yet today. The last 30 days cost $1.26, about 4¢ a day. Sign-in needs a look, and three more things could be better." Settings rows also carry dense two-line descriptions. Kids will skip these pages, which is acceptable for Status and Settings but shows the tone.
- **Phone loses detail.** The surprise chip shrinks to just "Surprise" on phone Home, without "hidden from Maya". On the phone Chat page, the oldest visible Vera bubble is cut off under "Earlier messages".
- **The Ask Vera textarea shows a browser resize grip** in its corner on both desktop and phone, which is unfinished.
- **Phone Ideas leads with three stacked controls** (search, "Show ideas", a "Filter" row) plus a teal "Looking things up is off" panel before the first card.

**Mark: 8/10**: a restrained, well-proportioned system that handles the hard family-specific cases (surprises, lateness, rating) clearly on both screen sizes; it only lacks visual energy.

## Q

**What it is**
The same base with more colour and more structure. Each idea kind gets its own tinted chip: pink "Activity", violet "Event", blue "Trip", peach "Restaurant". The same colours carry onto calendar events and the "Coming up" list. Each to-do is a wide row with separate owner, due date and reminder columns. Times are 24-hour, set in a figure style with slashed zeros. On phone, navigation is a six-tab strip at the top under the logo, and the sidebar user card reads "Parent · runs the app / Not you? Switch".

**What works**
- **Colour helps scanning on desktop.** On Ideas, the kind chip plus a status chip ("Planned · Sat 17 Oct", "Went Thu 1 Oct", "Tomorrow · 13:00", "Not looked up yet") make the 12 cards easy to sort by eye. The calendar's coloured event blocks (blue Mount St. Helens, plum Nutcracker, pink Oaks Park) read faster than P's beige ones.
- **Filters are explicit on desktop.** Ideas has a single labelled row: Search / Kind / Status / For / Show. To do puts Who, Due and Remind as visible fields beside "Add a to-do". Each to-do row offers "No reminder · Add one" in place.
- **The setup warning on Settings is strong.** The red "One thing needs a look" panel with "Choose a password" is unmistakable.
- **Chat lets you pick who's writing.** The "Writing as" row on Chat (Sam, Alex, Maya, Theo chips) suits a shared family laptop.

**What doesn't**
- **Surprises aren't protected.** "Lego set for Theo" appears on Ideas and Home with "Theo" as the owner and no surprise or hidden marking. "Buy Maya's birthday present" has no marking either. If the kids use the site, they see their own presents.
- **The digits look broken.** Every zero is slashed: "13:Ø0", "$2.ØØ", "Vera has looked up 1Ø", "Ø9:ØØ". In a warm family app it reads like a glitch, and "Ø" is hard for a 9-year-old to read as a time. The 24-hour clock is also an odd choice for a US family.
- **The phone layouts break.**
  - On To do, each item balloons to about a third of the screen (title, then avatar, then date, then "days late" on separate lines). The "Open / Done / Cancelled / All" control wraps, so "All" sits on its own second line, and the search field stops short of full width.
  - On Settings, the chevron drops to its own line under General, Spending, Lookups and What has changed.
  - The calendar's today cell is clipped to "3 TOD". The calendar shows only coloured bars with no titles.
  - The Ask Vera prompt chips are cut off ("Remi…").
  - Ideas makes you scroll past four full-width form fields (Search, Kind, Status, For) and a Show button before the first idea.
- **The rating faces have no words.** On Plans, "How did it go?" is three bare face icons with no labels.
- **The content contradicts itself.**
  - Chat says "Put the hike on Saturday at 10" and "Done: Silver Falls hike, Saturday 10:00 to 14:00", but Plans and Ideas put Silver Falls on Thu 1 Oct.
  - Cannon Beach shows as two separate blocks (Sat "08:00" and Sun "all day") rather than one weekend.
  - Status says "Two things aren't set up yet" while Home says "3 left".
- **The To do add form uses a raw browser date input** ("mm/dd/yyyy" with a native calendar icon), which clashes with the "Sun 27 Sep" date style used everywhere else.

**Mark: 6/10**: the stronger colour system and explicit filters help on desktop, but the slashed-zero numerals, the broken phone layouts and the missing surprise protection let down the family and phone use the brief centres on.

## Between them

### 1. I would build P.
Three reasons decided it:
1. **It keeps the kids' presents secret.** P marks "Surprise · hidden from Theo/Maya" on the gift idea and the birthday-present to-do. Q shows "Lego set for Theo" with Theo as owner and no protection. For a family where the 9- and 11-year-old use the site, this is a content-safety issue, not just a styling difference.
2. **It holds up on the phone.** P's to-dos stay compact, its segmented controls fit, and its Plans page puts the list before the calendar. Q's phone To do, Settings, Plans (the "3 TOD" cell) and Home chips all wrap or clip.
3. **It's readable for kids.** P has labelled "Loved it / OK / Not great" buttons, 12-hour times and plain digits. Q has bare face icons, a 24-hour clock and slashed zeros ("13:ØØ").

### 2. Where Q is better
- **Ideas (desktop):** the coloured kind chips plus the "Planned · Sat 17 Oct" / "Went Thu 1 Oct" / "Not looked up yet" status chips and the per-card "Look it up" link. This is clearly better than P's uniform beige cards.
- **Plans calendar (desktop):** the colour-coded event blocks, with a matching colour on the "Coming up" tag pills.
- **Ideas filters (desktop):** the visible labelled Kind / Status / For row, against P's collapsed "Filter · Any kind · Anyone · Any status" row.
- **To do (desktop):** "No reminder · Add one" inline on each row.
- **Chat:** the "Writing as" person chips (Sam / Alex / Maya / Theo) are a clearer way to switch speaker than P's "Writing as Sam · Not you? Sign out".

### 3. What is still wrong with P (most important first)
1. **The Ideas grid and the calendar are visually monotonous.** Adopt a restrained per-kind tint, as Q does, so cards and events can be told apart at a glance.
2. **The surprise chip loses its "hidden from …" text on phone Home.** That text is exactly what a parent needs to see to trust it.
3. **On phone Chat, the top Vera message is clipped** under "Earlier messages".
4. **The Ask Vera textarea shows a browser resize grip** on desktop and phone.
5. **Status and Settings copy is long and adult.** The Status hero runs to four sentences on phone, and many Settings rows have two-line descriptions. Shorten them to a headline plus one line.
