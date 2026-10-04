# Review: FamilyDB, designs P and Q

The two designs share almost everything. They have the same layout, cream background, deep-green accent, serif headings over a sans body, sidebar, phone tab bar, cards, chips and copy. Most of what follows applies to both. The differences are a small set of identity decisions in Q (logo, Vera's avatar, monospace touches, the Ideas distance map) and how each one handles dark mode.

## P

**What it is**
A calm, warm design system: a cream page and ivory cards, a deep-green "Ask Vera" panel at the top of Home with a yellow Send button, serif page titles ("Good morning, Sam.", "To do", "Plans"), and colour-coded person avatars (S blue, A purple, M pink, T orange, plus a house icon for Everyone). The logo is a small house with a lit yellow window on a green tile. Vera is a white circle with a serif "V". On desktop there's a left sidebar with counts ("2 to rate", "3 late", "1 to decide"), split into a family section and "Behind the scenes". On phone there's a top bar with a "Ready" pill and a five-tab bottom bar (Home, Chat, Ideas, Plans, To do).

**What works**
- Home is a real dashboard. It shows the next plan with a calendar tile ("SUN 4 OCT"), "Tomorrow" and "Leave by 12:30 pm" chips, and See the plan and Move it buttons. Below that come the three following plans, to-dos, recent ideas, and in the right column setup, "How did Silver Falls hike go?", wish lists and Vera today. The opening line "Roller rink tomorrow, and three to-dos are late" links straight to both.
- The colour rules are disciplined and written down on the page. Settings has a "Colours in FamilyDB" legend: each person keeps their colour, green is Vera, "Red only means late, or broken." The rest of the app sticks to it. Red appears only on the To do overdue rail, "6 days late" and the "3 late" badges.
- To do is clear. The overdue rows have a red left rule and show the person avatar, due date, lateness and "No reminder". "Surprise · hidden from Maya" is a visible chip. The add form uses big tappable person chips (Sam, Alex, Maya, Theo, Everyone).
- Plans has a readable month grid with coloured event chips (time and title) and today (3rd) shaded. Under it are "Coming up" and "How did it go?" with large Loved it / OK / Not great face buttons that a 9-year-old can use.
- Dark mode is the most faithful of the two. The Ask Vera panel stays green and remains the focal point. Primary buttons stay green. The overdue rail and chips keep their meaning.

**What doesn't**
- It's generic. A cream, green and serif look with a house logo could belong to any wellness or productivity app. Nothing about it is Vera's or this family's.
- Vera's "V" circle is the same shape as the family's letter avatars, so in Chat she reads as a fifth family member rather than the assistant.
- On phone, the Plans month view shows only dots under the dates (filled pink on 4 and 17, hollow on 29 Sep and 1 Oct). A child can't tell what's on a day without switching to List. "28 Sep" and "1 Nov" wrap inside their cells.
- On phone, Wishes (the kids' own page) isn't in the bottom bar. Also on phone, the "Add a to-do" form sits below the whole list rather than at the top as on desktop.
- The type is small and dense in places for young readers: sidebar counts, the meta lines on to-do rows ("Sun 27 Sep · No reminder"), and the Settings rows.

**Mark: 7/10.** A clean, consistent, well-ordered interface with a colour system that carries real meaning, but it has no identity of its own.

## Q

**What it is**
The same interface as P, with an added layer of identity:
- **Logo:** a smiling computer monitor on a black tile, with a bright green block cursor after "FamilyDB".
- **Vera:** shown as a small dark "pane of glass full of glyphs" (green characters on black) instead of a letter.
- **Status pill:** a black "Vera is ready" pill in green monospace, with a monospace timestamp on Vera's chat messages ("7:48 pm").
- **Section labels:** letter-spaced capitals ("OVERDUE · 3", "NO DATE · 1", "MON TUE…").
- **Ideas:** a new block, "How far each idea is from home", is a green-on-black radar with rings at 30 min, 1 h, 2 h and 3 h, ideas plotted by compass direction, and a numbered list beside it.
- **Settings:** the colour legend explains the system: "Green light belongs to her, and to FamilyDB", "The smiling monitor is the app itself, never Vera."

**What works**
- Everything that works in P works here, because the layouts, Home dashboard, To do rows, Plans grid and rating buttons are the same.
- The app and Vera now have separate, explained signs. The monitor is the app and the glyph pane is Vera. In Chat, Vera no longer looks like a family member.
- The distance radar answers a real family question, "how far is it?", at a glance. Pumpkin patch is 18 min north-west. Cannon Beach is out west at 2 h 45. Silver Falls is due south. On phone it sits after the cards, so it doesn't delay the list.
- The "Vera is ready" pill and the green cursor tie the status language together across the sidebar, the phone top bar and the Status page.

**What doesn't**
- **Dark mode loses the hierarchy.** The Ask Vera panel turns near-black, the same as every other card, so Home loses its anchor (clear on desktop and phone). Primary buttons flip to cream ("Add", "Add a plan", "Add an idea"). Vera's chat bubbles gain a glowing green outline that makes her messages louder than the family's.
- **The glyph pane is noise at small sizes.** At 32–40 px (Home, Chat, the Status row) it reads as a dark speckled square, and a 9-year-old wouldn't read it as a face or a name.
- **The radar crowds its points.** Five of the ten ideas (2–6) cluster under one "2–6" label just south of centre, so the nearest ideas, the ones a family most often picks, are the least readable. It repeats drive times already on each card. On desktop it pushes the idea cards down by about 150 px (the cards start at about 820 px rather than 665).
- **The terminal flavour is technical** for a family app. Monospace and green-on-black read as "developer", against the warm cream elsewhere.
- **The shared faults remain:** the dots-only phone month view, Wishes missing from the phone bar, the add form below the list on phone To do, and small meta type.

**Mark: 7.5/10.** The same solid interface as P with an identity that is memorable and explained, held back by a dark mode that flattens Home and by a Vera mark that stops working at the sizes it's used most.

## Between them

**1. Which would you build for this family, and the three reasons that decided it.**
**Q.**
- **Vera gets a sign of her own.** The family talks to Vera all day, by text and on the web. Q separates "the app" (the smiling monitor) from "the assistant" (the glyph pane) and says so in Settings. In P, Vera's "V" circle sits alongside the family's own letter avatars.
- **The radar suits how they choose ideas.** The Ideas page is where weekend choices get made, and "how far?" is the question. The radar puts all ten looked-up ideas in one picture by direction and time.
- **The usability cost is fixable without touching the system.** Every page, flow and control the kids would use is the same as in P. Q's problems (dark-mode panel and buttons, avatar legibility, radar clustering) are colour and size fixes.

**2. Which has the stronger identity, and does it cost anything in use?**
Q, clearly. A family would recognise the smiling monitor with the green cursor and the "Vera is ready" pill, and could say "the little green screen app". P's house-in-green-tile could belong to many apps.
It does cost something:
- **Dark mode:** the identity's black-and-green palette swallows the Ask Vera panel and turns primary buttons cream.
- **Avatar:** the glyph pane is illegible at avatar size.
- **Ideas:** the radar takes space above the idea cards on desktop.
- **Tone:** monospace makes status feel technical rather than homely.

**3. Where the other one is better, if anywhere (page and element).**
- **Home, dark mode, Ask Vera panel (desktop and phone):** P keeps it deep green so it stays the first thing you see. Q's goes near-black like every other card.
- **Primary buttons in dark mode (To do "Add", Plans "Add a plan", Ideas "Add an idea"):** P keeps them green and consistent with light mode. Q's flip to cream.
- **Vera's avatar in Chat and in Home's "Vera today":** P's "V" is at least readable as a letter at small size. Q's glyph pane is a speckled square.
- **Ideas, desktop:** P's idea cards start right under the filters. In Q they start about 150 px lower.
- **To do, section labels:** P's sentence-case "Overdue · 3" / "No date · 1" is easier for a 9-year-old to read than Q's spaced capitals.

**4. What is still wrong with Q, most important first.**
1. **Dark-mode hierarchy.** Give the Ask Vera panel a distinct dark-green fill and keep primary buttons green. Remove the green glow on Vera's chat bubbles.
2. **Vera's mark at small sizes.** Below about 48 px, simplify the glyph pane to a few large glyphs or a clear "V" inside the pane, so kids can find her in Chat.
3. **Phone access for the kids.** Wishes isn't in the phone bottom bar. The Plans month view shows only dots, so a child can't see what's on a day. On To do, "Add a to-do" sits below the whole list.
4. **Radar clustering.** Spread or zoom the inner rings so the five ideas labelled "2–6" are separately readable. On desktop, consider putting the radar after the cards, as on phone.
5. **Small, dense meta type** for 9- and 11-year-olds: sidebar counts, the to-do meta lines, Settings rows and the radar's ring labels.
