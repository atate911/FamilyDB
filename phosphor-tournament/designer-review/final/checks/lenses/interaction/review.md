# Review: hierarchy and flow

## Verdict
**7 / 10.** On desktop the order is right: every page opens with one plain sentence that links to what matters, and Home makes "write to Vera", "tick off a late to-do" and "rate a plan" one step each. But on the phone, To do and Ideas put their tools ahead of their lists, which breaks the standard's own rule that the list comes first. The Ideas filter is applied by a button that sits above it. And setup and health are counted differently on Home, Settings and Status, so the admin can't tell how much is left.

**Optimise before building?** Yes. The mockups are the source of truth, so the phone order on To do and Ideas and the Ideas filter's submit button would be built wrong as drawn. All three are small layout changes.

## Protect
1. Home, the lede sentence ("**Roller rink tomorrow**, and **three to-dos** have slipped past their dates"). It is the page's summary and its two most useful links in one line.
2. Home, the Ask Vera card first, with starters that either send (paper-plane icon) or fill the box (pencil icon), and "Goes to the family chat as Sam" saying where the message lands.
3. Home and To do, the tick on the left and Edit on the right of each to-do row, each in its own form. After a tick the row stays struck through with a flash and Undo (states-actions). Marking a to-do done never needs a second page.
4. Status, "How each part is doing": one row per part with a state tag and its one fixing action beside it (Set up sign-ins, Add a key, Connect Telegram). It answers "is it working, and what do I do about it" in one place.
5. Kid pages: "Moving it? Ask a parent" on kid Home's Next up, the read-only to-do with "Done? Tell Vera…", and grownups.html instead of an error. A kid never meets a dead control.
6. Phone, the role-aware five-tab bar with the late count on To do and a dot on More, and the More page, which repeats each destination's state in a line ("Settings · Sign-in needs a look · 1 to check").

## Fix, ranked

**1. Phone To do and Ideas: the list starts below the first screen** (phone/todo, phone/ideas)
- Problem: Standard §5.2 says "The list you came for is in the first screen… heading, lede, the list, then the tools". On phone To do, the quick-add card, its two-line "Who, when, reminder" summary, the Open/Done/Cancelled/All control and search push "Overdue · 3" to about 1000 px, under the tab bar at 844 px. On phone Ideas, Add an idea, Save a thought, the Looking-things-up banner, the All/Restaurants control, search and Filter push the first idea to about 1400 px. A parent who opens To do to tick something off, or a kid who opens Ideas to browse, sees only controls.
- Fix: On the phone, order the page as heading, lede, a one-line quick-add (input plus Add, with "Who, when, reminder" as a single-line `<details>` summary or moved below the list), then the list, then the filter control and search. On Ideas, keep Add an idea in the head. Move "Save a thought for later" and the Looking-things-up banner below the list, or make the banner `--slim`. Put the All/Restaurants switch and search on one row above the list, and fold Filter in after them. Check that the first to-do and the first idea land above 700 px at 390 × 844.
- Severity: major. Effort: S.

**2. Ideas: "Show ideas" comes before the filters it applies** (ideas, `.finder` form)
- Problem: In ideas.html the submit button comes before `<details class="disclose">` holding Kind, For and Status. With scripting off, a parent who opens Filter and picks "Theo" has nothing to press below the selects and must go back up to "Show ideas". On the phone that button is off screen once the disclosure is open. A kid looking for "ideas for Theo" will think the filter did nothing.
- Fix: Move the submit button to the end of the form, after the disclosure. Better still, put a second "Show ideas" at the foot of the disclosure body. Open the disclosure server-side when any filter is active (as the standard already says), and show the active filters in its summary.
- Severity: major. Effort: S.

**3. Setup and health are counted three different ways** (Home "Finish setting up", Settings banner, nav badge and side card, Status hero)
- Problem: The same state reads "3 steps left" (Home, Settings side card), "1 to check" (Settings nav badge and More), "1 thing needs a look" (Settings banner), "Sign-in needs a look, and three more things could be better" (Status), and four "Could be better" tags on the Settings list (AI model, Messages, Personality, Connections). The admin can't tell whether there is one thing to do, three, or five, or which page is the list to work through.
- Fix: Make the setup steps the single checklist (Home's card, phone "Continue"). On Settings, put "Setup: 3 steps left · Continue setup" in place of the separate banner and move it to the top of the main column, not the foot of the side column. Make the Settings nav badge count what Settings tags as Needs a look plus unfinished setup steps, with the same number on More. Have Status's hero name the same items. Derive all of them from `health()`, as §8 intends, and check the copy so the words agree.
- Severity: major. Effort: M.

**4. Chat: changing who is writing means signing out** (chat, "Writing as Sam · Not you? Sign out")
- Problem: The brief asks for "a choice of who is writing (on a shared computer)". Once people have their own passwords, the only way to switch is Sign out, which leaves the conversation and the draft and goes back to the person picker. A kid at the family laptop who finds Sam signed in will either write as Sam or give up. The "Who's writing?" pills appear only in the family-password mode (signin sheet).
- Fix: Replace "Not you? Sign out" with "Not Sam? **Switch**", linking to the sign-in person picker with `?next=/chat` and the draft carried in the query (`draft.js` or a server-side draft). Return to the same conversation after the password, with the kid landing in their own chat. Keep plain Sign out in the sidebar user card.
- Severity: major. Effort: M.

**5. Phone Plans: the month switcher is far from the month** (phone/plans)
- Problem: "‹ October 2026 › Today" sits above "Coming up" and "How did it go?", and the month grid it controls is at the very bottom. It reads as if the arrows change Coming up. Someone checking "what's on in November" taps › and sees nothing near the top change.
- Fix: On the phone, order the page as Coming up (no month heading), then How did it go, then the month switcher directly on top of the grid. Or give the phone the same Month/List segmented control as desktop, with the arrows inside the Month view only.
- Severity: minor. Effort: S.

**6. "2 to rate" leads to a page where rating is below the calendar** (desktop Plans nav badge, Plans "How did it go?" card)
- Problem: On a 900 px-tall laptop, the Plans badge lands on a full-screen calendar, and the rating card starts below it at about 1000 px. The inline "How did it go?" links on 29 Sep and 1 Oct are small and dashed. The badge promises an action the page hides.
- Fix: Point the sidebar badge and tab at `plans.html#rate`. Or, while anything is waiting for a rating, show a slim banner under the lede ("2 plans to rate · Rate them") that jumps to the card.
- Severity: minor. Effort: S.

**7. Ideas is two taps away on the phone, and phone rows lose the kind in words** (phone tab bar, phone/ideas rows)
- Problem: "Find an idea" is one of the five main paths, but parents reach Ideas only through More or Home's "All 12 ideas". The phone rows also drop the "Activity / Restaurant / Outing" label and keep only the tile icon, so the kind is shown by icon alone, which kids and the standard's "no meaning by colour alone" spirit both suffer from.
- Fix: Put the kind back in the row meta ("Activity · Everyone · 27 min, south"). Keep the tab set for now, but promote Ideas to the More page's first row (it already is) and add a "New ideas" link with its count on phone Home's "Just added to Ideas" card.
- Severity: minor. Effort: S.

**8. Settings needs a legend to be read** (settings, "Reading this list" and "Colours in FamilyDB" cards)
- Problem: Two side cards explain tags and colours. That means the tags in the list don't carry their own meaning, and those cards push the one actionable side card ("Setup: 3 steps left · Continue setup") to the bottom of the page.
- Fix: Drop "Reading this list". Make each row's summary line say the consequence ("No backup: if OpenAI is down, Vera can't answer"). Move "Colours" to Family. Put the setup card first (see Fix 3).
- Severity: minor. Effort: S.

**9. Phone To do: Edit is a bare pencil** (phone/todo, phone/home To do card)
- Problem: Desktop says "Edit" in words. The phone shows only a pencil icon next to a tick ring, two round targets in one row, and a kid or a non-technical parent may not know which one changes the to-do and which one finishes it.
- Fix: Keep the word on the phone ("Edit", the 15 px meta size is enough), or move Edit into the row's title link (tap the title to open the to-do) and drop the separate control.
- Severity: minor. Effort: S.

**10. To do: searching drops the Open/Done/All choice, and switching view drops the search** (todo `.todo-bar`, ideas `.seg`)
- Problem: The search form has no hidden `status` field, and the segment links carry no `q`. A parent who searches "dentist" while on Done gets Open results, and switching to All clears the search. Ideas has the same split between the All/Restaurants links and the finder form.
- Fix: Carry the current view as a hidden input in each search form, and add the current `q` to each segment link. Give the to-do search a visible submit button or icon button for people who don't know to press Enter.
- Severity: minor. Effort: S.

## Missing
- An unplanned idea's own page: the drawn idea is already on the calendar. The main idea-to-plan step ("Put it on the calendar" as the page's primary action) and the "Add a plan" form (a `#` link on Plans) are not shown.
- Idea cards have no direct action ("Plan it", "Ask Vera about this"), so moving from finding to planning always means opening the idea first.
- A parent reading Maya's chat: does the composer show, and does it write as Sam into Maya's chat? Neither the closed state nor the wording is drawn.
- The Plans list view (Month/List) and a single plan's page, which "See the plan", "Move it" and the calendar events all link to (`#` or the plans anchor today).
- The to-do Edit page, including Cancel (the "Cancelled" filter implies it) and where Undo of a cancel lands.
- What happens after Send from Home's Ask card: whether the person is taken to Chat at `#latest` with the pending bubble, and how they get back to Home.
- Search results across everything (one box that finds a to-do, an idea or a plan). Today each page has its own search, and Home has none.
- The admin "first time" Home after setup is finished, showing what fills the right column once "Finish setting up" disappears.

## One sentence
On the phone, put the list before the tools on To do and Ideas, as the standard already says, so that marking a to-do done or finding an idea starts with the thing itself and not with forms.
