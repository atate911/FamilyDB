## Verdict
**6/10.** The system is calm, well worded and unusually honest about states. The three states sheets cover limits, outages, pending and failed messages, empty days, no results and long titles better than most "final" designs do. But the drawings are fitted to a tidy family: 4 to-dos, 12 ideas, one-word names, a two-day trip that falls neatly on Sat–Sun, and short chat messages. Where real data goes past that (multi-day plans, a long Home, the phone's first screen, the shared laptop, Vera's longest message), the design either has no answer or breaks its own written rules.
**Optimise before building?** Yes. The gaps below are cheap to settle in the mockups now and expensive once they are baked into Jinja macros and the one stylesheet.

## Protect
- States sheets (`states`, `states-actions`, `states-content`): every failure has words, a reason and one way out. Kids get "until tomorrow" and never see money or company names.
- To do, overdue rows: "6 days late" in words, plus a 4 px red rule and a named tick. Lateness never depends on colour alone.
- Chat, the privacy line ("Sam and Alex can read your chat with Vera.") shown at every width, plus the kid's "20 messages left today" under the box.
- Home (kid), the "Moving it? Ask a parent" locked line and the wishes shown with words ("Yes!", "Not this time"). A kid can read these.
- No results, Ideas: "Nothing matches "pizza" for Theo", the active filters in words, and the two ways out (Clear, Save as a thought).
- Status, "How each part is doing": one row per area, each with a state tag and one action button.

## Fix, ranked

**1. Plans that span days break the calendar** (Plans, desktop month grid; `style.css` lines 633–635, 665)
- Problem: Only `.c6.span2` (Sat→Sun) exists. A Thu–Sun trip, a week of camp, or a weekend running Sat→Mon across the week row has no class to place it. Worse, the generic `.span2 { grid-column: 1 / -1 }` from Status would make any other `span2` event stretch across the whole week. Cannon Beach only works because it was put on Sat 24–Sun 25. Trips are a headline use of the app, and parents will see broken calendars in the first month.
- Fix: Add `.span2`–`.span7` scoped under `.week` (for example `.week .s3 { grid-column-end: span 3 }`). Have the server split a multi-day plan into one segment per week row, with "continues ›" and "‹ from Sat" ends. Rename Status's `.span2` to `.status-grid__wide`. Draw a Fri→Mon trip and a 9-day trip on the busy-day sheet, and their dots on the phone grid.
- Severity: blocker. Effort: M.

**2. On the phone, the list you came for is not on the first screen** (phone Home, Ideas, To do, Plans)
- Problem: STANDARD §5.2 says "Order: heading, lede, the list, then the tools", and the phone pages don't follow it.
  - Ideas: Add, Save a thought, the lookup banner, tabs, search and filter all come first, so one idea row peeks above the tab bar.
  - To do: the adder, the "Who, when, reminder" box, the segments and search fill the screen, leaving 1½ to-dos.
  - Home: the setup strip plus an Ask card about 420 px tall push Next up, to-dos and everything else under the fold. The first screen carries only the lede sentence.
  - Plans: Add, the Google banner and month navigation come before "Coming up".

  A kid or a parent glancing at a phone sees forms, not their stuff.
- Fix: Apply your own rule.
  - Ideas and To do: put the list straight after the lede. Fold the quick-add and search into one `<details>` "Add or search" row (or a single-line adder with no "Who, when" box until it has focus, which works without script because the server opens it on error).
  - Ideas: move the lookup banner below the list as a slim banner.
  - Home on phone: shrink Ask to a one-line composer with starters folded away, and put the next plan and the late count above it.
  - Plans: move the Google banner below the list.
- Severity: major. Effort: M.

**3. Surprises are on show on the shared laptop** (Home desktop To do card and "Just added to Ideas"; To do list; Ideas cards)
- Problem: The brief says presents never show where a kid reads. A parent's Home opens with "Buy Maya's birthday present" and "Lego set for Theo" in full, and the only guard is the "Surprise · hidden from …" tag. On the family's one laptop, with a parent signed in and a kid walking past or borrowing it ("Not you? Sign out" relies on people remembering), the gift is spoiled. On phone Home the tag also hides "hidden from Maya" (`.tag__more` is visually clipped), so the parent can't tell whom it's hidden from.
- Fix: Wherever surprise items appear on Home and in lists, render their titles behind a `<details>` "Surprise for Maya, tap to show" (no script needed). Add a session idle sign-out for shared computers in Sign-in and security. Keep "hidden from X" visible on phone.
- Severity: major. Effort: S.

**4. Home has no limits for a busy household** (Home, To do card, Next up, Wish lists)
- Problem: The Home To do card shows all 4 to-dos ("All 4 to-dos"), and nothing says what happens with 18 open, 9 of them late. Next up shows 4 plans; Wish lists has one row per kid. Desktop Home is already about 1,900 px and phone Home about 8 screens. With real data, Home turns into a second To do page and "what matters today" gets lost.
- Fix: Write caps into the standard and draw them on `states-content`:
  - To do card: late first, at most 5 rows, then "and 13 more ›".
  - Next up: the next plan plus 3 more.
  - Just added: 4.
  - On phone Home, collapse Wish lists and Vera today into one-line rows.
- Severity: major. Effort: S.

**5. Vera's biggest message is never drawn** (Chat, desktop and phone)
- Problem: Every Vera bubble drawn is two to four lines with at most one plan card. The Weekend suggestions message (several ideas with drive times, weather and "add to plans" choices) is the main thing Vera sends, and it's absent. A five-card reply in a phone room where the scroller is already only about half the screen (pills, privacy line, "Writing as", box, location checkbox and tab bar take the rest) will not fit. With the on-screen keyboard open, the thread shrinks to two or three lines.
- Fix: Draw the Weekend suggestions message on desktop and phone: a compact list of idea rows inside one bubble, each a link with a "Plan it" button (a form). On phone, hide the privacy line and the location row while the textarea has focus (`:focus-within` on `.room`, no script), and drop the tab bar from the Chat room.
- Severity: major. Effort: M.

**6. Calendar events turn into stubs at real widths** (Plans desktop, `.ev b` clamped to 2 lines)
- Problem: At 1280 px, each day is about 130 px. Already in the mock, "Mount St. Helens day…" is clamped, and "Maya's end-of-season…" is clamped on the long-titles sheet. Real titles like "Dentist – Theo (bring forms)" or "Grandma's 80th at the Lakeview" will nearly all clamp. Busy days also show only two events plus a small "+2 more" link. As a result, the month view shows times and stubs, not plans.
- Fix: Let the event title use the full cell width by dropping the inner margin (`--s2` → `--s1`). Put the time inline before the title ("9a Mount St. Helens…"), not on its own line. Raise the clamp to 3 lines when a day has only one event. Make "+N more" a full-width 44 px target.
- Severity: minor. Effort: S.

**7. Health words already disagree between pages** (Home "Vera today" and Status "How each part is doing")
- Problem: Home tags Vera **"Answering"**, but Status tags the same area **"Working"**, which is the word STANDARD §3 requires. §8 says `health(area)` feeds every page "so they can't disagree", and the mockups already do. Settings uses "Could be better" for four sections while Status's hero counts "three more things". That's defensible (sections ≠ areas), but a parent comparing the two pages will think one is wrong.
- Fix: Home uses `tag(health('vera'))`, which gives "Working". On Settings, have the banner give the same count in the same words as the Status hero, or link each "Could be better" to the Status row it comes from.
- Severity: minor. Effort: S.

**8. Phone fields and controls are tight at 390 px and untested at 320 px** (Ideas phone "Save a thought" input; To do phone segments)
- Problem: The "Save a thought for later" placeholder is already cut off at 390 px ("e.g. that ramen place Alex men"). The To do segments (Open 4 / Done / Cancelled / All) fill the width at 390 px and must "never wrap" (§2), so at 320 px or 200 % zoom they will clip or scroll sideways. The standard says to test at 320 px, but no 320 px drawing is supplied.
- Fix: Shorten the placeholder ("e.g. that ramen place"). Put the Save button under the field below 400 px. Let the segments become a `<select>` or two rows (Open/Done and Cancelled/All) below 360 px. Add 320 px screenshots of To do, Ideas and Chat to the set.
- Severity: minor. Effort: S.

**9. Status shows totals where the brief asks for "over 30 days"** (Status, "Last 30 days" card; "Which AI does each job" row)
- Problem: Three numbers ($1.26, 6, 4¢) can't show a spike, such as the one day a runaway lookup cost $1.80. The question "is it costing more lately?" goes unanswered. The model-per-job table and the fallback are folded into a footer row labelled "for whoever set it up", although the brief lists them as Status content. "$0.00 … Nothing spent yet today" will also be false when 0.3¢ has been spent.
- Fix: Add a 30-bar SVG sparkline (server-drawn `<rect height>` presentation attributes, which CSP allows) with the limit line and the highest day labelled. Show the model table open on desktop. Show sub-cent spend as "under 1¢".
- Severity: minor. Effort: S.

**10. "A choice of who is writing" became "Sign out"** (Chat composer, "Writing as Sam · Not you? Sign out")
- Problem: On a shared laptop, the brief asks for a choice of who is writing. The design asks the next person to sign out and back in with a password, which means a full sign-in round trip for an 11-year-old. The "Who's writing?" picker appears only in the brand-new-install specimen on the sign-in page. Families will just type as Sam, and Vera will learn things about the wrong person.
- Fix: Next to "Writing as Sam", add a "Switch person" link to the sign-in person picker with a `next=` back to Chat, keeping the draft. Or state plainly in the standard that switching means signing in, and test that a kid can do it alone.
- Severity: minor. Effort: S.

## Missing
- Multi-day and cross-week plans, on the month grid and the phone dots (see Fix 1).
- The Weekend suggestions message and Vera's "how did it go?" prompt as they appear in chat.
- Long and duplicate person names: "Alexandra", two people starting with "S", or a fifth family member. Not drawn on sign-in tiles, "Writing as", avatars, choice pills or event avatars.
- Very long lists: 200 ideas, a Done tab with 500 to-dos, a kid with 30 wishes. No pagination, "show more" or sort is drawn for any list.
- Whole-page failures: session expired, a form posted after sign-out (CSRF), server error, and the phone being offline. The sheets cover Vera failing, not the app failing.
- A plan in the past with no rating, and a plan that was cancelled or moved, in Plans list and Ideas status tags.
- A 320 px and 200 %-zoom set for the four list pages and Chat with the keyboard open.
- Home for Alex, a parent who isn't an admin: what replaces the setup card and Vera today without the Behind the scenes items.

## One sentence
Re-draw the phone pages so each opens on its list, and draw the calendar and chat with a real family's month: a five-day trip, a busy Saturday, and Vera's full Weekend suggestions.
