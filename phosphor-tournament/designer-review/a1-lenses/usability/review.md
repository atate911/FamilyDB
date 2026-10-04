# FamilyDB design review: usability test lens

Six test tasks were walked through the pictures (desktop and phone). The fixes below refer to them by number:

- **T1** Sam tells Vera to plan Saturday (Home "Ask Vera", then Chat).
- **T2** Sam ticks off "Call the dentist about Theo" (Home to-do card, To do page).
- **T3** Alex finds "the ramen place" (Home "Just added", Ideas).
- **T4** Sam checks what Vera is costing (Home "Vera today", Status).
- **T5** Sam adds a to-do for Alex with a reminder (To do quick add).
- **T6** Theo (a kid), at the family laptop where Sam is signed in, asks Vera for a Lego set for his wish list (Wish lists hint, then Chat).

## Verdict
**7/10.** For a parent at a desktop, T1–T5 mostly succeed on the first try: the Ask Vera box, the overdue group and the plain-language ledes ("4 open, 3 of them overdue. Tick one off when it's done.") make the next step obvious. The failures come at the edges the brief cares about most: a kid on a shared computer posts as Sam, one-tap controls with no undo send things that can't be taken back, and on a phone the lists sit below a full screen of forms and filters.

**Optimise before building?** Yes. T6 fails silently (Theo's wish goes into the family chat as Sam), and the chip/tick controls act on one tap without confirmation or undo. Both are cheap to fix now and expensive once people stop trusting the app.

## Protect
1. Home, the **Ask Vera** card is first, with a large input and a high-contrast yellow **Send**, on desktop and phone. T1 started there with no hesitation.
2. To do, the **OVERDUE · 3** group: red left rule, "6 days late" written out, the owner's avatar and name, and an explicit **Edit** link on every row.
3. Plain-sentence page ledes and teaching empty states: "Kids can tell Vera 'I wish for…' and rank their own list" (Home, Wish lists) and "You can also tell Vera: 'remind Alex…'" (To do footer).
4. Status, the headline "Vera is working, and well under budget." plus the **Spent today** bar with the "a usual day ≈ $0.04" marker. T4 is answered in one glance.
5. Problem banners that carry their own single action: Plans "Google Calendar isn't connected yet → Connect Google Calendar", Settings "One thing needs a look → Choose a password", Status "No backup → Add a key".
6. Phone tab bar with text labels and the red **3** badge on To do, and the 3px focus outline (`style.css:51`) on every control.

## Fix, ranked

**1. "Writing as" silently defaults to the signed-in parent** (Chat, compose "Writing as" chips; Chat conversation list)
- Problem: T6. Theo sits at the laptop where Sam is signed in, goes to Chat, types "I wish for the Lego Ninjago set" and presses Send. The dark **Sam** chip is pre-selected, so the wish goes into the *Family* conversation as Sam, not to Theo's own chat or wish list. On phone the chips wrap to two rows above the input (phone Chat), and a kid reading top-down skips them. Parents can also mistake each other's messages (Sam vs Alex).
- Fix: Make the chip choice and the conversation choice one control. Above the box, write "**Who's writing?**" with Sam / Alex / Maya / Theo chips and *no* default on a shared session. If nobody is picked, submit returns the page with "Pick who's writing first" on the chips (server-side validation, no JS). Picking Maya or Theo posts to that kid's own conversation and says so under the box: "Theo’s own chat · Sam and Alex can read it". Remember the last pick for 30 minutes in the session, and show it in the box placeholder: "Write to Vera as Theo…".
- Severity: blocker. Effort: M.

**2. Suggestion chips send immediately, half-finished** (Home, Ask Vera chips "Remind me to…", "Save an idea…")
- Problem: T1. In `home.html:69-71` the chips are submit buttons, so tapping "Remind me to…" sends the literal text "Remind me to " to Vera. Testers expect a chip ending in "…" to fill the box so they can finish the sentence. On phone the row is cut off at "Remi" with the scrollbar hidden (`.sugg` overflow-x, `style.css:512`), so "Save an idea…" is never seen.
- Fix: Keep "What should we do next weekend?" as a send button, since it is a complete question. Make the two "…" chips links (`home.html?text=Remind+me+to+#ask`) that reload Home with the textarea pre-filled and focused (`autofocus`), which works without JS. On phone, let the chips wrap (`flex-wrap: wrap`) instead of scrolling sideways. Three short chips fit in two lines at 390px.
- Severity: major. Effort: S.

**3. Ticking a to-do is one unlabeled, irreversible tap** (Home To do card and To do page, the round `.tick` button; Plans "How did it go?" faces)
- Problem: T2. The tick is an empty beige ring on cream with no word next to it. Testers are likely to reach for the pencil first. On phone the ring sits beside a multi-line title, where a scroll-tap can mark the wrong row done. It posts at once (`todo.html:82`), the row disappears, and nothing shows how to get it back. "Done" is a filter tab, not an undo. The same applies to the smiley/neutral/sad rating buttons on Plans.
- Fix: Give the ring a darker 2px border (`--ink-3`) and a hit area of at least 44×44px, and show a ✓ on hover/focus. After the POST, redirect back with a banner at the top of the list: "✓ Ticked off *Call the dentist about Theo*. **Undo**" (Undo is a small form that reopens it), kept for this page view. On Home, put the visible word "Done" under each ring at ≤600px.
- Severity: major. Effort: S.

**4. Vera's confirmation doesn't say which day, and the drawn data contradicts itself** (Chat, Vera's "Done" message and the "Silver Falls hike · Added to Plans · 10:00 to 14:00" card; Plans calendar; Ideas)
- Problem: T1. Alex asked for "Saturday at 10", Vera replied "Saturday 10:00 to 14:00", and the card shows only times. Plans then shows the hike on **Thu 1 Oct** with "Rate it", and Ideas says "Went Thu 1 Oct", while today's Saturday cell is empty. A tester asks "so did it go on the calendar or not?" and checks three pages. A relative "Saturday" sent on a Sunday is ambiguous anyway.
- Fix: The plan card in chat always shows the full date and who it's for: "Sat 3 Oct · 10:00–14:00 · Sam and Alex", and links to the plan. Vera's text uses the date too ("Saturday 3 October"). Before the mock is used for usability sessions, regenerate the sample data from one source so Chat, Plans, Ideas and Home agree.
- Severity: major. Effort: S.

**5. On phone, the list people came for is below a screen of form** (phone To do: "Add a to-do" card, Telegram notice and wrapping filter tabs; phone Ideas: Save a thought, tabs and four stacked filter fields plus Show)
- Problem: T2, T3 and T5 on phone. On To do, the first overdue row starts about 1.1 screens down, after the add form, the Telegram notice, the Open/Done/Cancelled tabs (with "All" wrapped onto its own line) and the search. On Ideas, "Ramen at Afuri" is the third card, more than two screens down, under Search, Kind, Status, For and **Show**. The filters also need the Show button with no JS, which kids miss: they change "Any kind" and nothing happens.
- Fix: At ≤600px, To do shows: lede, then the overdue list, then a one-line quick add ("Add a to-do… [+]") whose Who/Due/Remind sit in a `<details><summary>More: who, when, reminder</summary>`. Put the four filter tabs on one line (shorten to Open 4 · Done · Cancelled · All, 14px, horizontal padding 10px). On Ideas, keep Search and Save-a-thought visible and wrap Kind/Status/For/Show in `<details><summary>Filter · Any kind, any status, anyone</summary>`, with the summary showing the current choices.
- Severity: major. Effort: M.

**6. "Reload if nothing shows" is the reply experience** (Chat, footnote "Vera answers in a few seconds. Reload if nothing shows.")
- Problem: T1 and T6. After Send, a tester stares at their own message and nothing happens. Kids won't read the 13px grey footnote, and they press Send again, which double-posts.
- Fix: After the POST, redirect to the conversation with a Vera bubble that says "Vera is thinking…" and a `<meta http-equiv="refresh" content="3">` that is present only while a reply is pending. After 60s, swap it for "Vera didn't answer. Try again" with a button that resends. Disable duplicate sends server-side for 10s with the same text.
- Severity: major. Effort: M.

**7. "Remind" can be ticked when reminders can't be delivered** (To do quick add, "Remind" checkbox; Telegram notice below it; each row's "No reminder · Add one")
- Problem: T5. Sam types "Book flu shots", picks Alex, ticks Remind, presses Add, and believes Alex will be pinged. The notice explaining that reminders won't reach anyone sits *after* the form (desktop) or after the Add button (phone). The "Add one" link on every row makes the same promise.
- Fix: While Telegram isn't set up, render the checkbox disabled with its label changed to "Remind (needs Telegram — Set up)" linking to setup. Replace "Add one" on rows with "Reminders off". Move the notice above the form. Also default **Who** to the signed-in person, not "Household". For a kid, it should be locked to themselves.
- Severity: major. Effort: S.

**8. Status speaks engineer** (Status: "Calls to the AI", "From the cache 0%", the "gpt-6-luna" column, three red "None" pills)
- Problem: T4. Testers find the money fast, but then the red "None ×3" and "No backup" warning sit under a green "working, and well under budget" headline, and a non-technical parent asks "is something broken?". "Answers reused cost less" and "Each question or lookup is one or more calls" don't answer any question they have.
- Fix: Lead the 30-day card with one sentence, "Last 30 days: $1.26, about 4¢ a day", and drop the cache tile for parents. Rename "Calls to the AI" to "Questions Vera handled". Collapse "Which AI does each job" into `<details><summary>Which AI Vera uses (for the techie)</summary>`. Show "None" as a neutral grey "No backup" tag, because the amber banner already carries the warning once.
- Severity: minor. Effort: S.

**9. Icon-only signals testers can't read** (Ideas and Home "Just added" cards: the ↓ ↗ ↖ arrow chips before drive times; Home to-do pencil with no label)
- Problem: T3. Testers read the arrows as "trending down" or "sort", not as compass direction. The Home pencil is the only edit cue there, and kids don't know it.
- Fix: Write the direction as words, as Home "Next up" already does: "22 min drive south". Remove the arrow chip. On Home, give the pencil a visible "Edit" label, as the To do page does.
- Severity: minor. Effort: S.

**10. Status and Settings are hard to reach on phone** (phone header "Vera is on" pill; tab bar "More")
- Problem: T4 on phone. Status lives under "More", which isn't drawn. The obvious target is the green "Vera is on" pill in the header, but it isn't a link. The red **1** on Settings in the desktop sidebar has no phone equivalent.
- Fix: Make the "Vera is on" pill a link to Status, and turn it amber ("Vera: 1 thing to fix") when Status or Settings needs attention. Put a dot on the "More" tab when Settings has a badge.
- Severity: minor. Effort: S.

## Missing
- A **kid's view** of Home, To do and Chat (Theo signed in): what replaces Setup and Vera today, how he adds a wish, and his chat's "parents can read this" note.
- **After-action states**: the post-tick banner with Undo, a plan just moved, and an idea just saved via "Save a thought" (where did it go?).
- **Vera pending, failed and over-limit states** in Chat and Home, e.g. "Vera has hit today's $2.00 limit and is back at midnight."
- **Form errors**: empty to-do title, a due date in the past, an unknown name in Who, a chat sent with nobody picked in "Writing as".
- The phone **More** page (Wishes, What Vera knows, Status, Settings, Switch person) and how "Not you? Switch" works on a shared laptop.
- **Empty first-day Home** for a new family: 0 ideas, 0 plans, no to-dos, with setup as the main task.
- **Long and messy content**: a 60-character to-do title on phone, 40 ideas, three plans on one calendar day (phone month cells show only coloured bars).
- **Sign-in for kids**: how an 8-year-old signs in without typing a strong password.

## One sentence
Make "who is writing" an explicit, required choice on the shared computer that also picks the right conversation, so a kid's message never goes out under a parent's name.
