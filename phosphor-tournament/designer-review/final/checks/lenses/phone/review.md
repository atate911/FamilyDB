## Verdict
**7 / 10.** The phone layout is a real phone layout, not the desktop stacked: it has a fixed five-tab bar with badges, an app-height Chat with the box pinned, 44 px ticks and faces, and Settings and More rows that never break. But Home's first screen on a phone is almost all Ask Vera. Ideas is two taps away and its list starts below six tools. The header pill overflows in the exact states when the family most needs it.
**Optimise before building?** Yes. At 390 px, the first screens of Home and Ideas don't show what the family came for, and fixing that later means reworking the templates.

## Protect
- **Every phone page, bottom tab bar**: fixed, five tabs, each about 78 × 56 px and in thumb reach. It has the late count on To do and a dot on More. Kids get Wishes instead of Plans.
- **Chat (phone), the room**: app-height, opens at the newest message without script, the box pinned above the tabs, conversation pills in one row, and the privacy line kept at every width.
- **To do (phone), the rows**: a 44 px tick ring on the left, the pencil on the right, "6 days late" in words plus the red edge, and long titles wrapping in full.
- **Home (phone), the setup banner**: the desktop "Finish setting up" card becomes a one-line "3 setup steps left · Continue". Keep this pattern for anything that's nagging but not urgent.
- **Settings and More (phone), the rows**: icon, then text with the tag under it, then a chevron that never wraps. Status lines in words. The whole row is the target.
- **Home and Plans (phone), "How did it go?"**: three big labelled face buttons (about 58 × 54 px) that are easy for a kid's thumb.

## Fix, ranked

**1. Home's first screen is only the Ask card** (Home, phone, `.ask` card)
- Problem: The top bar, greeting, setup banner and Ask card (about 450 px: a 84 px textarea, a full-width Send, three stacked starter chips and a footnote) fill the first 844 px. "Next up" only peeks under the tab bar. The overdue to-dos start about 1,400 px down, on the third screen, and Wish lists are on the fifth. On desktop, Next up and setup sit beside Ask in the first view. A parent opening the app at 8 am sees a text box, not their day.
- Fix: At ≤ 820 px, make Ask a one-row composer: a one-line textarea that grows, with the 50 px icon Send inside the row (as in Chat). Show the starters as one wrapping row of short chips ("Next weekend?", "Remind me…", "Save an idea…"). Drop "Goes to the family chat as Sam" into the placeholder. Aim for ≤ 220 px, so the next plan's title and time are fully on the first screen. On the phone, put To do above Next up when anything is late.
- Severity: major. Effort: M.

**2. The header pill doesn't fit in the "resting" and "can't answer" states** (all pages, phone `.topbar` › `.pill-health--rest`, `--down`)
- Problem: The states sheet draws "Vera is resting until midnight" at about 229 px. Add the brand (about 129 px), the avatar (36), the 16 px gutters and the gaps, and the top bar needs about 446 px. On a 390 px phone it wraps or pushes sideways, which breaks the "nothing scrolls sideways" rule, and it happens just when something is wrong. At 320 px it's worse. No phone top bar is ever drawn in these states.
- Fix: On the phone, the pill shows a short form ("Resting", "Not answering"), with the full sentence as its accessible name and on Status. Or drop the "FamilyDB" wordmark and keep only the logo below 400 px. Draw both states at 390 and 320.
- Severity: major. Effort: S.

**3. Ideas is hidden behind More** (phone tab bar, parents)
- Problem: Ideas is half of what Vera is for ("what should we do this weekend?"), yet on the phone it's More → Ideas: two taps, and nothing on the tab bar says it's there. Plans already has Home's "Next up" and "All plans" link.
- Fix: Give parents Home, Chat, Ideas, Plans, To do, More (six tabs, about 65 px each, still well over 44). Or swap Plans for Ideas and reach Plans from Home and More. Either way, a parent gets to the idea list in one tap.
- Severity: major. Effort: S.

**4. On the Ideas page, the list starts below six tools** (Ideas, phone)
- Problem: STANDARD §5.2 says "heading, lede, the list, then the tools". The phone page instead stacks Add an idea, "Save a thought for later", the "Looking things up is off" banner (about 130 px), the All/Restaurants segment, Search + Show ideas, and Filter. The first idea starts about 700 px down, behind the tab bar. Browsing on a phone means scrolling past the same tools every time.
- Fix: Order it as heading, then a one-line lede, then search + Filter in one row (the segment folds into Filter as "Kind: Restaurants"), then the list. Make "Add an idea" a small header button. Move "Save a thought" and the lookups banner (as a slim one-liner) below the list or into the Filter disclosure. Goal: three ideas visible in the first screen.
- Severity: major. Effort: M.

**5. No way into the Plans list on a phone** (Plans, phone, `.cal-bar .seg` and the "List view" link)
- Problem: `style.css` hides the Month/List switch on the phone, and the "List view" link in Coming up is `desk-only`. The phone only shows "Coming up" (four plans) and a dot grid. Older plans, and anything beyond the four, can only be reached by tapping a day dot. §5.4 says "Plans open on the list", but there is no list to open.
- Fix: Keep a plain "All plans" link (or the two-way switch) in the Coming up header on the phone. Make "Coming up" the top of the real list (grouped by week, "Earlier" folded). Leave the month grid as the jump-to-day tool below it.
- Severity: major. Effort: S.

**6. The Chat box is crowded and sits next to Sign out** (Chat, phone, `.room .composer`)
- Problem: Above the box sit "Writing as Sam · Not you? Sign out" and below it the location checkbox row, all above the 68 px tab bar. With a phone keyboard up (about 300 px), the conversation pills, privacy line, composer block and tab bar leave the thread roughly 150–200 px. That's two bubbles. "Sign out" is a small link right above the text box, so a mis-tap logs a parent out mid-message. On a personal phone, "who is writing" isn't in doubt.
- Fix: Hide the tab bar while the box has focus (`body:has(.composer textarea:focus) .tabbar { display: none }`, no script needed). Collapse "Writing as / Sign out" into the avatar in the top bar on the phone. Make "Share where I am" a 44 px pin toggle next to Send instead of a row of its own. Draw this keyboard-up state.
- Severity: major. Effort: M.

**7. On the phone, an idea's kind is only an icon** (Ideas, phone, `.idea__kind { display: none }`)
- Problem: Desktop cards say "Gift idea", "Activity", "Seasonal". The phone rows keep only a grey icon tile (a gift, a star, a leaf). The brief asks that each idea show its kind. Kids and non-technical parents won't decode a leaf as "Seasonal".
- Fix: Put the kind word first in the meta line: "Activity · Everyone · 19 min, south".
- Severity: minor. Effort: S.

**8. "Take it off my list" is a 32 px target on a kid's page** (Wishes for a kid, phone, `.rank > .linkbtn`)
- Problem: `style.css` overrides it to `min-height: 32px`, breaking the standard's own 44 px rule. It sits right above the up and down arrows, so an 11-year-old aiming for an arrow can remove a wish.
- Fix: Restore `--target` (44 px), and put at least 8 px between it and the arrows (or put it after the arrows). The removal already asks for confirmation or offers Undo, which should stay.
- Severity: minor. Effort: S.

**9. Folded summaries start with a stray "·"** (To do, phone, "Who, when, reminder"; Status, phone, "Which AI does each job")
- Problem: When the summary wraps on the phone, the second line starts "· Sam · No date · No reminder" and "· for whoever set it up". The second one also tells a parent nothing.
- Fix: Put the separator inside the first-line span, or drop it when wrapping. Give the Status summary a real line: "Chat, digest and lookups all use gpt-6-luna · no backup".
- Severity: minor. Effort: S.

**10. Awkward wraps at 390 px** (an idea's own page, phone, `.idea-head`; Sign in, phone, person tiles)
- Problem: On the idea page, the kind tile sits beside the title, so "Oaks Park roller rink" breaks over two lines with a gap on the left. In the sign-in tiles, "Kid · picked" breaks into "Kid ·" / "picked".
- Fix: On the phone, stack the tile above the overline, or drop it, and let the title use the full width. Show "picked" as the tile's selected border plus visually hidden text rather than a wrapped word.
- Severity: minor. Effort: S.

## Missing
- Chat and the Home Ask card with the phone keyboard open, including where the thread, box and tab bar end up.
- The phone top bar in the "resting" and "can't answer" states, and every page at 320 px, which the standard requires but never draws.
- The Plans list view at 390 px, and what a tapped day dot lands on.
- The Ideas Filter disclosure opened on the phone (kind, status and who choices), and Ideas or To do "no results" at phone width.
- The edit-a-to-do form, "Move it" for a plan and "Who, when, reminder" opened on the phone: the date, time and person pickers are where thumbs struggle.
- What tapping the top-right avatar does on the phone (account, sign out, switch person).
- The iPhone home-indicator inset and landscape: `env(safe-area-inset-bottom)` is in the CSS but no frame shows it.
- A flash with Undo on the phone, whether it stays visible above the fixed tab bar, and where focus lands.

## One sentence
On the phone, shrink Home's Ask Vera card to one row so that today's next plan and anything overdue are on the first screen.
