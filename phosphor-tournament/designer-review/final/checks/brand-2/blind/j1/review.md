# Review: FamilyDB designs P and Q

Both designs share the same skeleton. Each has a cream page, a left sidebar on desktop and a five-tab bar on phone (Home, Chat, Ideas, Plans, To do). Each has a dark-green "Ask Vera" block with a yellow Send button, serif headings, sans body text, and per-person colours (Sam blue, Alex purple, Maya pink, Theo orange, Everyone a grey house). Each has a light and a dark theme. The difference lies in a handful of identity choices and in a few places where one explains more than the other.

## P

**What it is**
A warm, card-based family dashboard with a "friendly terminal" layer on top. The logo is a little smiling monitor followed by a green cursor block after "FamilyDB▌". The status pill is black and set in monospace green ("● Vera is ready"). Vera's avatar is a tile of green glyphs, which Settings › "Colours in FamilyDB" calls "a little pane of glass full of glyphs". The Ideas page has a dark radar chart, "How far each idea is from home", with rings at 15 min, 30 min, 1 h, 2 h and 3 h, numbered dots and a numbered list beside it. In dark mode the page turns a cool green-black, and the Ask Vera block gains a glowing green outline.

**What works**
- **Plans calendar explains itself.** A legend under the grid reads "One person's plan, in their colour · Several people: grey, with each face · Everyone · Already happened". The cells follow it: Oaks Park (Maya and Theo) is grey with both faces, Nutcracker is Maya's pink, and Mount St. Helens and Cannon Beach carry the house icon.
- **The phone calendar carries the same rule.** Each day shows a face or a house icon, so you can see *who* at a glance: M/T on the 4th, a house on the 9th, 24th and 25th, M on the 17th, and an empty ring for 29 Sep and 1 Oct. The legend is repeated under the grid.
- **Home has a clear order** on both widths. The greeting has linked facts ("Roller rink tomorrow, and three to-dos are late"), then Ask Vera with three starter chips, then Next up with a big date tile and "Leave by 12:30 pm", then To do with red left rules and "6 days late" in red. The secondary right column holds Finish setting up, the hike rating, Wish lists and Vera today. On phone, setup collapses to a single "Setup: 3 steps left · Continue" strip.
- **To do is simple enough for a child.** Each person is a large named chip with a face (Sam, Alex, Maya, Theo, Everyone), the tick circles are big, and the overdue group is separated from "No date". On phone every row is a full card with the late count on its own line.
- **The radar** is a memorable, honest picture of something real. Drive times are mapped by direction, it is explained in one sentence, and it is backed by a readable list.
- **Dark mode keeps the character.** The green glyph tile and the mono pill fit the dark background naturally, and the red late rules turn salmon and stay legible.

**What doesn't**
- **On desktop the radar breaks the Ideas grid.** It sits after the first row of three cards, so the twelve ideas are split three-then-nine around a large black panel. On phone it sits below all twelve cards, followed by the full ten-line list a second time, which makes the page very long (about 5,800 px at phone width).
- **The radar's labels are tiny monospace green on near-black** ("30 min", "15 min", "3 h"). At 10 (west) the dot and number sit on top of the "W" axis label. A 9-year-old will not read it.
- **The surprise chip is vague on Home.** The birthday present to-do and the Lego idea say only "Surprise". The To do and Ideas pages say "Surprise · hidden from Maya" / "hidden from Theo", so the most-seen page gives the least information on the most sensitive item.
- **The terminal idiom (monospace pill, cursor block, glyph avatar) speaks to a developer parent rather than to the family.** It is also the only place monospace appears, so it reads as a different voice from the rest of the page.
- **On phone the "Add a to-do" form sits below the whole list,** after the overdue and no-date groups. The fastest action is the hardest to reach (Q does the same).

**Mark: 8/10.** A calm, well-ordered system with a real personality, and the clearest Plans page of the two. It loses points because its signature feature, the radar, is placed and lettered with less care than the rest.

## Q

**What it is**
The same app in a plainer, warmer dress. The logo is a green rounded square with a white house and a small yellow dot. The status pill is light mint ("● Vera is ready") in sans text. Vera is a white circle with a serif "V". Dates and section labels are in small caps ("SATURDAY 3 OCTOBER"), and the green is a slightly lighter, bluer teal. Ideas is a clean four-by-three grid with serif card titles and no radar. Dark mode is a warm brown-black rather than green-black.

**What works**
- **Consistent, calm cards everywhere.** Ideas in particular reads as one even grid (Gift idea, Activity, Restaurant / Outing, Event, Seasonal / Show, Day trip, Trip / …). Serif titles ("Lava tubes at Ape Cave", "Pumpkin patch at Bi-Mart farm") make each card feel like a place rather than a record.
- **The surprise label is explicit everywhere.** It reads "Surprise · hidden from Maya" on the Home to-do and "Surprise · hidden from Theo" on the Home idea card, as on the full pages.
- **The To do "Add" button is full width** on desktop and phone, which makes an easy, unmistakable target for a child.
- **Settings › "Colours in FamilyDB" states the red rule.** It reads "6 days late · Red only means late, or broken", alongside "Green is Vera".
- **Home, To do, Status and Settings are as well ordered as P's,** since the layout is the same, and dark mode is even and readable.

**What doesn't**
- **The Plans calendar has no legend, and its colour logic is inconsistent.** Oaks Park roller rink (Maya *and* Theo) is filled pink with a pink rule, just like Maya's own Nutcracker. Mount St. Helens and Cannon Beach have no Everyone icon in the cells, so colour alone is left to say who, and here it says the wrong thing.
- **On phone, the calendar days show only dots:** pink on the 4th and 17th, grey on the 9th, 24th and 25th, hollow on the 29th and 1st. A child cannot tell from a dot whose plan it is or that the 4th includes Theo.
- **"28 Sep" and "1 Nov" wrap to two lines** in the phone calendar's corner cells, which is slightly untidy against the single-number days.
- **The identity is generic.** A house-in-a-square logo and a "V" avatar could belong to any household app. Nothing on any page would make a child say "that's ours".
- **On phone the "Add a to-do" form is below the list,** as in P.

**Mark: 7/10.** Tidy, legible and safe, but its Plans page, the one that most needs to show "who", reads less clearly, and it has nothing a family would remember.

## Between them

### 1. Which would you build for this family, and the three reasons that decided it

**P.**
1. **Plans shows who it's for, on both desktop and phone.** P's legend and its face-or-house markers make the calendar readable by every family member. Q's pink-for-two-people block and bare phone dots do not.
2. **It has an identity a family can own.** The smiling monitor, the glyph-tile Vera and the radar of "how far from home" give the app a face and one genuinely delightful family-specific view, while every working page (Home, To do, Status, Settings) is as clear as Q's.
3. **Its fixes are cheap.** P's weaknesses are about placement and labels: move the radar, enlarge its labels, lengthen the surprise chip. Q's are structural (calendar encoding) or about character, which is harder to add later.

### 2. Which has the stronger identity, and does it cost anything in use?

**P, clearly.** The cursor-blink "FamilyDB▌", the black mono "Vera is ready" pill, the glyph-pane Vera avatar and the green-on-black radar recur on every page and in both themes. A child would recognise it. It does cost something:
- On Ideas, the radar interrupts the card grid on desktop and doubles the list on phone.
- Its monospace micro-labels are the least legible text in either design.
- The terminal tone leans "dad's side project" more than "our family's app". The cost is concentrated on one page and one pill. Home, To do and Plans pay nothing for it.

### 3. Where the other one is better

- **Home › To do card and Just added to Ideas:** Q's "Surprise · hidden from Maya" and "hidden from Theo" chips are clearer than P's bare "Surprise".
- **To do › Add a to-do:** Q's full-width Add button is a better target than P's small pill, especially on phone.
- **Ideas (desktop):** Q's unbroken twelve-card grid with serif titles scans better than P's grid split by the radar.
- **Settings › Colours in FamilyDB:** Q's "Red only means late, or broken" explains a rule that P's key leaves unstated.

### 4. What is still wrong with P, most important first

1. **The surprise chip on Home says only "Surprise".** It should name who it is hidden from ("hidden from Maya"), as the To do and Ideas pages already do. This is the item a kid must not misread.
2. **The radar's placement on Ideas.** On desktop, move it out of the grid, either above the cards or as its own band after them. On phone, drop the duplicate ten-line list or collapse it behind a toggle.
3. **Radar legibility.** The ring labels are tiny monospace green on black, and dot 10 collides with the "W" label. Enlarge them, use the body sans, and give the compass letters clear space.
4. **On phone, "Add a to-do" sits below the whole list.** Put it, or a sticky "+ Add" button, at the top. Taking Q's full-width button would help too.
5. **The terminal voice is inconsistent.** Monospace appears only in the status pill and the radar. Either soften the pill to match the rest of the type, or use the mono voice deliberately for Vera everywhere, so it reads as Vera's voice rather than a stray style.
