# Review: FamilyDB designs P and Q

What I looked at: all six overviews (desktop, phone and dark for each). Full length, for both designs: Home, To do and Plans on desktop and phone; Ideas on desktop for P; Home in dark mode for both.

The two designs share almost everything. The layout, the page structure, the copy, the warm cream palette, the serif headings with sans body text, the person colours (Sam blue, Alex purple, Maya pink, Theo orange), the deep green primary with a mustard Send button, and the phone tab bar are all the same. The differences are in identity and in a few information details. This review is about those differences.

## P

**What it is**
A warm, calm family dashboard with a deliberately "machine" accent for Vera. The logo is a smiling monitor, and "FamilyDB" is followed by a green cursor block. The status pill is black with monospace green text: "● Vera is ready". Vera's avatar everywhere is a small dark square of green glyphs, which Settings calls "a little pane of glass full of glyphs". The Ideas page adds a dark radar chart of "How far each idea is from home", with rings at 15 min, 30 min, 1 h, 2 h and 3 h, numbered green dots, and a numbered list beside it. Dark mode is green-black, and the Ask Vera card turns into a green-outlined panel.

**What works**
- **Home.** The order is right for a family: the greeting with linked shortcuts ("Roller rink tomorrow, and three to-dos are late"), then Ask Vera, Next up, To do, Ideas. The right column holds the admin-only Setup box, labelled "Only admins see this", then "How did it go?", Wish lists and Vera today.
- **Plans calendar.** It has a real legend: "One person's plan, in their colour · Several people: grey, with each face · Everyone · Already happened". The chips follow it. Oaks Park is grey with M and T faces, Nutcracker is Maya pink with an M, and the Everyone plans carry the house icon. On the phone, each day shows small faces (M, T, house) or a hollow circle for past plans, with the same legend underneath. A child can tell "that one's mine" without opening anything.
- **To do.** Overdue tasks are grouped under a red "OVERDUE · 3" heading with a red left rule, "6 days late" in red, and assignee faces. The "Surprise · hidden from Maya" chip is explicit. On the phone, the list comes first and the Add form drops below it.
- **Large, plain controls that children can manage.** Person chips with initials, "Loved it / OK / Not great" face buttons, and a 5-tab phone bar with a "3" badge on To do.
- **Vera's glyph avatar is used consistently** in the sidebar, chat, status rows and "Vera today", so a message from Vera can't be mistaken for one from a family member.
- **The Ideas radar is a strong, memorable picture** of something the family actually cares about: how far away each idea is.

**What doesn't**
- **The identity reads as a developer tool:** the "DB" wordmark, a terminal cursor, a monospace status pill and a glyph screen. It is distinctive, but its references come from programming, not from family life. The black "Vera is ready" pill is also the heaviest object in the sidebar and on the phone header, for a message that is almost always "fine".
- **The radar breaks the Ideas grid.** It sits between the first row of three cards and the rest. Its numbered list repeats the cards' drive times, and in a dark monospace style it is the only fully dark block on a light page. The tiny ring labels (e.g. "30 min", "W 10") are small for kids.
- **The Surprise chip is shortened to "Surprise" on Home**, both phone and desktop, so it doesn't say who the surprise is hidden from. To do and Ideas say "hidden from Maya / Theo".
- **In dark mode the Ask Vera card loses its solid green fill** and becomes an outline. The main action on Home gets less emphasis than in light mode.
- **On the phone, Wishes, Status, Settings, Family and What Vera knows are not in the tab bar.** Only the avatar is left as a way in, and I can't see what it opens. (This applies to Q too.)

**Mark: 8/10.** It is a clear, well-structured and child-legible system, with a calendar legend and face dots that do real work, and an identity that is memorable but leans more "tech" than "family".

## Q

**What it is**
The same app with a quieter, friendlier skin. The logo is a green rounded square holding a house with a small yellow dot. There is no cursor after "FamilyDB". "Vera is ready" is a soft mint pill in normal type, and Vera's avatar is a plain "V" in a circle (white on green). The Ideas page is a plain 3-column card grid with no radar. The month header uses "Mon/Tue" instead of "MON/TUE", and the date eyebrow is in small caps ("SATURDAY 3 OCTOBER"). Dark mode is warm brown-black and keeps the Ask Vera card as a solid green fill.

**What works**
- **Home and To do have the same solid structure as P.** The Surprise chip says "Surprise · hidden from Maya" on Home too, so it is consistent everywhere.
- **The "+ Add" button on To do runs the full width of the form**, desktop and phone. It is the clearest single target on the page, which helps the kids.
- **The status pill is light, so it doesn't compete with the content.** The "Setup: 3 steps left" badge sits on the same line as the "Finish setting up" title, which tightens that card.
- **Dark mode is the better of the two.** The warm dark keeps the cream feel, and the filled green Ask Vera card stays the clear focal point.
- **Ideas reads as one uninterrupted, scannable grid.**

**What doesn't**
- **The Plans calendar has no legend, and the colour logic is inconsistent.** Oaks Park (Maya and Theo) is a pink Maya-coloured chip with M and T faces, while Silver Falls (Sam and Alex) is grey. The Everyone plans (Pho Oregon, Mount St. Helens, Cannon Beach) have no house icon, so the chip doesn't say who is going.
- **The phone calendar is worse.** Each day shows a tiny coloured dot (pink on the 4th and 17th, grey on the 9th, 24th and 25th) with no faces and no key. The pink on the 4th wrongly suggests a Maya-only plan.
- **The identity is generic.** A house-in-a-square logo, a "V" circle and a mint pill could belong to any family or home app. Vera's "V" avatar looks like a family member's initial avatar (the same shape as S, A, M, T), so Vera is less distinct from the people in chat. On Status and "Vera today", Vera is shown with a chat-bubble icon, which is a third symbol for her.
- **On Home, the "Surprise · hidden from Theo" chip on the Lego idea card wraps onto two lines** inside a pill ("Surprise · hidden / from Theo"), which looks broken. It does this on desktop light, dark and phone.
- **There is the same lack of phone navigation to Wishes, Status, Settings and Family as in P.**

**Mark: 7/10.** It is equally well structured and calmer, but its calendar loses the who-is-going information that P carries, and it has little that a family would remember as theirs.

## Between them

### 1. Which would you build for this family, and the three reasons that decided it

**P.**
1. **The calendar tells the family who each plan is for.** Plans has a legend and consistent chips: one person's colour, grey with faces for several people, a house for Everyone, a hollow circle for past plans. On the phone the faces still show in each day cell. Q's phone calendar is uncoded dots, and its desktop colouring contradicts itself (Oaks Park in Maya's pink). For a family of four with kids, "is this mine?" is the main question on the calendar.
2. **Vera is visibly not a person.** Her glyph-square avatar is unlike any family member's initial circle, in chat, Status and Home. Q's "V" circle has the same form as S, A, M and T. The kids should always know when they're talking to the assistant.
3. **It has things a family would remember and use.** The radar of "how far each idea is from home" is a picture children can point at and talk about. Q has no equivalent anywhere.

### 2. Which has the stronger identity, and does it cost anything in use?

**P, clearly.** The cursor after "FamilyDB", the monospace "Vera is ready", the glyph-pane Vera and the green-on-black radar form one idea: Vera is a small friendly machine living in the family's app. A family would recognise and remember it. Q's house logo and V circle are pleasant but anonymous.

It costs something, in three places:
- **The heavy black status pill** draws the eye on every page, including the phone header, to say nothing new.
- **The radar interrupts the Ideas grid** and repeats the card data in small monospace type.
- **In dark mode the Ask Vera card loses its fill** to stay "glassy", so the main input is weaker.

Also, the tech references (DB, terminal, mono) speak to a parent who codes more than to a 9-year-old. None of these block a task. They are costs in emphasis, not in function.

### 3. Where the other one is better

- **Home, Ideas card and To do:** Q's Surprise chip always names who it's hidden from. P shortens it to "Surprise" on Home.
- **To do:** Q's full-width "+ Add" button is the easier target for kids. P's is a small pill.
- **Dark mode, Home:** Q keeps Ask Vera as a solid green card on a warm dark background. P's outlined version on green-black is less inviting and less emphatic.
- **Sidebar and phone header:** Q's light "Vera is ready" pill sits quietly, where P's black monospace pill competes with the page.
- **Ideas:** Q's uninterrupted grid is easier to scan than P's grid split by the radar block.
- **Home, Finish setting up:** Q puts the "3 steps left" badge on the title line, saving a row.

### 4. What is still wrong with P, most important first

1. **Phone navigation.** Wishes (the kids' own lists), Family, Status, Settings and What Vera knows are missing from the 5-tab bar. On a phone, the kids' wish lists are only reachable through a Home card. At minimum, Wishes deserves a tab or a clear "More".
2. **Calm the black "Vera is ready" pill.** Use the light treatment when all is well, and keep the dark or monospace style for moments when Vera needs attention.
3. **Move the Ideas radar** to below the grid, or to its own "Map" view next to "All ideas / Restaurants". Drop the duplicate numbered list, or make it the radar's tooltip or labels, and enlarge the ring labels.
4. **Spell out the Surprise chip everywhere** ("Surprise · hidden from Maya" on Home too). Hiding a gift from a child only works if the parent can see it's working.
5. **Dark mode Ask Vera.** Give the card back a filled green surface, or a stronger background, so it stays the first thing on Home.
