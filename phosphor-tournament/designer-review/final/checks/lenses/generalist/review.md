# FamilyDB final design: generalist review

## Verdict
**8 / 10.** This is a warm and coherent system. It has one clear idea behind it (a plain sentence first, cards below, a person's colour wherever that person appears), and it carries that idea through all twenty pages, both widths, dark mode and the kid views, with states drawn for nearly every case. What keeps it from a 9 is mostly emphasis, not structure. The "not set up yet" yellow appears on almost every page and drowns out the one thing that needs attention. Several phone pages put their tools before their list. And numbers are set in a custom serif inside the sans text, which costs readability and adds engineering work.

**Optimise before building?** Yes, but only a short pass. The top fixes are cheap tweaks to tokens and layout order. Each one gets copied into every template once building starts, so they should be settled first.

## Protect
- **Home, Ask Vera card** (desktop and phone): dark green with the sun-yellow Send and three starters. You can write to Vera straight away, and it is unmistakably the main action of the app.
- **Person colours and avatars everywhere**: To do owner chips, plan avatars, chat bubbles (Alex lilac), the calendar event bars (Nutcracker in Maya's pink). Who a thing belongs to is visible before you read it.
- **To do, late rows**: the 4 px red rule plus "6 days late" in words, with Overdue and No date grouped. Red keeps one meaning ("Red only means late, or broken").
- **Kid views** (home-kid, todo-kid, wishes-kid, grownups): the same design with the money, gifts and ticks removed, "Moving it? Ask a parent", wish answers in words ("Yes!", "Not this time"), and a friendly "This part is for grown-ups" page instead of an error.
- **Status, "How each part is doing"**: each part gets a sentence, a word tag and exactly one action button ("Set up sign-ins", "Connect Telegram"). A non-technical parent can fix things from this page alone.
- **"Surprise · hidden from Maya" tag** (To do: "Buy Maya's birthday present"; Ideas: "Lego set for Theo"), together with the rule that kids never see gifts at all.

## Fix, ranked

**1. Too many "set this up" warnings everywhere** (Home setup card, Plans Google Calendar banner, To do footer line, Home "Vera today" Telegram tag, Settings banner, Settings "Setup: 3 steps left" card, Settings tags, Status rows)
- Problem: The same three unfinished setup steps show up in warm yellow on almost every admin page. Settings alone has a warn banner, a warn card and five warn-coloured tags. Because yellow is everywhere, the one real "Needs a look" (Sign-in) stands out no more than "Could be better" on Messages or Personality. A parent quickly learns to ignore yellow, which defeats the colour system. It also makes a working app look unfinished.
- Fix: Show setup in one place per context: the setup card on Home (compact on phone) and the Settings banner. Drop the Plans warn banner and turn it into one quiet line under the calendar header ("Not on your phones' calendars yet · Connect Google Calendar"). On Settings, remove the "Setup: 3 steps left" side card. Show a tag only on rows in `--look` or `--broken`, and show "Could be better" as plain `--ink-3` text inside the summary line rather than a tinted tag. Settings should then show one yellow item, which is what the sidebar's "1 to check" already promises.
- Severity: major. Effort: S.

**2. Phone list pages put the tools before the list** (phone Ideas; phone To do to a lesser extent)
- Problem: Phone Ideas stacks six rows before the first idea: Add an idea, Save a thought for later, the "Looking things up is off" banner with its button, the All ideas / Restaurants switch, Search + "Show ideas", and Filter. Only the top of "Lego set for Theo" shows above the tab bar. Phone To do puts a quick-add card, the segment control and search above the overdue list. This breaks STANDARD §5.2 ("Order: heading, lede, the list, then the tools").
- Fix: On phone Ideas, keep heading, lede, the All ideas / Restaurants switch and one row of Search plus a Filter disclosure, then the list. Move "Save a thought for later" and the "Looking things up is off" banner below the list, or fold them into one `<details>` labelled "Add or save". Turn "Add an idea" into a small `+` button beside the h1. On phone To do, make the quick-add one line (field and Add) and move "Who, when, reminder" so it only opens after you type.
- Severity: major. Effort: S.

**3. Fraunces digits inside Atkinson sentences** (every page: "Sun 27 Sep", "6 days late", chat "Thursday 1 October, 10 am to 2 pm", "$1.26 in all")
- Problem: The "Fraunces Figures" subset swaps every digit to a serif, so most meta lines and Vera's replies mix two typefaces in the middle of a word group. Atkinson Hyperlegible was chosen so that letters and digits are hard to confuse, which matters for kids and low vision, and this swap undoes that for exactly the numbers that matter (dates, times, money). It also adds a custom font build step that someone has to maintain.
- Fix: Keep Fraunces numbers only where numbers are display type: the date tiles, the Status money ($0.00, $1.26, 4¢), the calendar day numbers and the wish ranks. Let running text use Atkinson's own digits. Remove the subset from the body stack and set Fraunces explicitly on those classes (`.dt`, `.money`, `.cal .day b`, `.rank__n`).
- Severity: major. Effort: S.

**4. The phone Home's first screen is all Ask card** (phone home, home-kid)
- Problem: On a 390 × 844 phone, the setup banner and the Ask card (two-line box, full-width Send, three stacked starters, footnote) fill the first screen. The "Next up" heading lands at the tab bar, and the late to-dos are a full scroll away. The brief says Home must show "what matters today". The greeting sentence links help, but the card most people come for is below the fold.
- Fix: On phone, give the Ask card a one-line textarea that grows when focused, an icon-only Send inside the row (as in Chat), and the starters as one wrapping row of short chips ("This weekend?", "Remind me…", "Save an idea…"). Drop the "Goes to the family chat as Sam" footnote on phone. The aim is that the top plan row of Next up appears above the tab bar.
- Severity: major. Effort: S.

**5. Settings explains itself with legend cards** (Settings, "Reading this list" and "Colours in FamilyDB")
- Problem: Two side cards explain what tags and colours mean. If a parent needs a key to read a settings list, the tags are not doing their job. The colours card on a settings page also reads like design documentation that leaked into the product.
- Fix: Remove both cards. Fix 1 already makes the tags self-explanatory (only "Needs a look" and "Off" remain). Move "Each person keeps their colour" to the Family page, where colours are actually assigned.
- Severity: minor. Effort: S.

**6. Status hides the model table and gives only 30-day totals** (Status, "Which AI does each job" disclosure; "Last 30 days" tiles)
- Problem: The brief asks for "calls and cost over 30 days" and which model answers each job, plus any fallback. The 30-day card shows three totals and leaves half its height empty, so a spending spike on one day can't be seen. The model and fallback table is folded away at the bottom under "for whoever set it up".
- Fix: Fill the 30-day card with a 30-bar SVG chart of daily cost (bars as `<rect height>`, which the CSP allows, as the meter already does), with the limit as a line and the tallest day labelled. Keep the table folded on phone, but open it by default on desktop for admins.
- Severity: minor. Effort: M.

**7. Ideas uses one action label in three wordings** (Ideas: "Show ideas" button next to sort; Home "Not looked up yet" vs home-kid "Vera hasn't checked this yet")
- Problem: "Show ideas" next to a search box reads like a view switch, not "apply search". The not-looked-up state also uses two different phrasings, which goes against §3's "one word per thing".
- Fix: Rename the button "Search" (or "Apply" when only the filter changed). Use "Not looked up yet" for everyone, or add "Vera hasn't checked this yet" to §3 as the kids' version, as was done for "Was due…".
- Severity: minor. Effort: S.

**8. The kid's tab label doesn't match the page** (home-kid, todo-kid phone tab bar)
- Problem: Maya's tab bar says "To do" and "Wishes", but the pages and sidebar say "My to-dos" and "My wishes". It is small, but kids rely on the same word in both places.
- Fix: Use "My to-dos" and "My wishes" in the kid tab bar; at 13 px they fit within a fifth of 390 px. Otherwise use the short form in the sidebar as well.
- Severity: minor. Effort: S.

**9. Past plans ask "How did it go?" in two places on Plans** (desktop Plans: dashed events on Tue 29 and Thu 1, plus the "How did it go?" card)
- Problem: The dashed calendar events carry "How did it go?" with a face icon inside a 130 px cell, next to a full card that asks the same question. The cramped copy in the cell adds noise and looks clickable for rating, but it is not a form.
- Fix: Keep the dashed edge for past plans, but replace the in-cell text with a small face icon whose spoken label is "Not rated yet". Leave rating to the card.
- Severity: minor. Effort: S.

## Missing
- A real "today has passed" state for Home: what the next plan card looks like on the day itself (today, under way, after) and how "How did it go?" moves up on Home that evening.
- A one-tap way to dismiss or snooze the setup reminders ("Not now, remind me next week") for a family that deliberately never connects Telegram or Google Calendar.
- Notification or flash design for when Vera does something on her own (a reminder sent, the weekend suggestions arriving) and how the web shows that it happened.
- The Plans list view and an idea's "Plan it" path from the idea page: the brief names them, but neither the list view nor the plan form is drawn.
- Memory ("What Vera knows"): the forget flow, including confirmation and Undo, which kids also use.
- A second kid's view (Theo, younger) to check reading level and the "No wishes yet" empty state as Theo sees it.
- Print and share: a plain printable week, which families pin on the fridge.
- Dark mode warn surfaces: the brown warn cards look muddy next to the green Ask card. They need a quick check once fix 1 has thinned them out.

## One sentence
Cut the yellow "set this up" warnings down to one place per page, so that the one thing that really needs a look is the only thing that stands out.
