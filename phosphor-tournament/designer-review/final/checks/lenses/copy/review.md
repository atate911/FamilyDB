# Review: words and content (UX writing lens)

## Verdict
**8/10.** The words are well above the usual standard. The copy is plain and warm, and it tells people what to do next. Errors are written as the fix, kids get their own version with no money or company names, and STANDARD.md §3 gives "one word per thing" as a rule the engineer can follow. It loses marks in a few places. The most-seen status phrase, "Vera is answering", also means "wait, she's replying". A few objects have two names (idea/thought, late/overdue, "Not looked up yet"/"Vera hasn't checked this yet", "Not decided yet"/"To decide"). And a handful of admin lines let machine detail or vague labels through ("gpt-6-luna", "Answers reused", "Vera's first personality", "Mark as been").

**Optimise before building?** No. Every fix below is a word change in the §3 table or in one template string. None of them changes a layout, so they can land during the build, as long as the §3 table is updated first.

## Protect
- Form errors (states-actions, "Add an idea · two errors"): errors written as the fix, e.g. "Give the idea a name, like 'Ramen at Afuri'", "That date has passed. Pick today or later."
- Kid-safe versions of every Vera state (states): "Vera is resting until tomorrow. You can write to her again in the morning.", "You've sent all 20 of today's messages", and no money or company names.
- grownups page: "This part is for grown-ups … There's nothing here you need to do." with "Go to my Home" / "Ask Vera something". A dead end that is kind and gives a way out.
- Honest privacy lines for kids: chat-kid "Sam and Alex can read this chat", wishes-kid "Wishes aren't secret: Sam and Alex see your list.", kid Home "Moving it? Ask a parent".
- Status hero and Spending card (status): "Is Vera working, and what is she costing? Checked when you opened this page." and "$0.00 of your $2.00 daily limit … a usual day is about 4¢". Cost is told in family terms, and the model table is folded under its own heading.
- Flash messages and empty states (states-actions, states-content): "Ticked off: … Undo", "Answer saved: Yes to 'A pet hamster'. Maya can see it now.", "No ideas yet. When someone says 'we should try…', Vera saves it here."

## Fix, ranked

**1. "Vera is answering" means two things** (header pill on every parent page; states, "Pending" chat box)
- Problem: The health pill says "Vera is answering" to mean *she's working*. The pending chat box says "Vera is answering. The box opens again when she's done." to mean *wait, she's replying now*. While a reply is pending, both show at once. A parent can't tell whether the green pill means "ready" or "busy", and the waiting message sounds like a status. This is the most-repeated phrase in the app.
- Fix: Keep the health words for health and rename the pill state to **"Vera is ready"**. Change Status hero and Home to "Vera is ready, and well under budget." and the Status Vera row to "Ready to answer here on the website." In the pending box, keep the dashed bubble "Vera is thinking…" and change the box line to **"Vera is writing back. You can type again when she's done."** Change the placeholder from "Wait for Vera's answer" to "Vera is writing back…". Update STANDARD §3 so health = ready / resting / can't answer.
- Severity: major. Effort: S.

**2. "Mark as been" is not English** (idea page, "Finished with it?" card)
- Problem: Nobody will know what this does, least of all a 9-year-old reading over a shoulder. It also doesn't match the status the app shows afterwards ("Went Thu 1 Oct", filter "Went").
- Fix: Change the card heading to "Been there?" and the button to **"We went"**, with a hint under it: "It moves to 'Went' and Vera asks how it was." If the job is to drop an idea, offer a second, quieter link: "Not for us, remove it".
- Severity: major. Effort: S.

**3. Wish answers: kids get two near-synonyms, parents a third** (wishes-kid and home-kid tag "Not decided yet"; wishes parent tag "To decide"; legend in "How wishes work")
- Problem: Maya sees "Thinking about it" on one wish and "Not decided yet" on another. Both mean "no answer yet", and her "How wishes work" legend explains only the first. The parent page tags the same wish "To decide", which goes against §3.
- Fix: Rename the empty state to **"No answer yet"**, which matches the line under it ("Sam and Alex haven't answered yet"). Add it to the kid legend: "No answer yet: Sam and Alex haven't looked yet." Use the same tag on the parent page, and keep the nav badge "1 to decide".
- Severity: major (kids). Effort: S.

**4. An idea is also a "thought"** (ideas, "Save a thought for later"; states-content, "Save 'pizza' as a thought"; home chip "Save an idea…")
- Problem: The same object has two names on one page. A family will wonder whether thoughts live somewhere other than Ideas. The brief's term list is plan / idea / to-do / reminder, with no "thought".
- Fix: Change the heading to **"Quick idea"**, with the hint "Just the gist. Vera will fill in the rest." and the button "Save idea". In no-results, change to "Save 'pizza' as an idea". Strike "thought" in §3.
- Severity: minor. Effort: S.

**5. Machine detail on admin pages** (settings, "AI model" row "OpenAI, gpt-6-luna · no backup"; status, "Which AI does each job · for whoever set it up" and "Answers reused this month: 0%. A reused answer costs less; 0% is normal for a new install.")
- Problem: A non-technical parent sees a model codename in the Settings summary. "Answers reused" is cache jargon that doesn't help any decision. "for whoever set it up" reads as a shrug.
- Fix: Change the Settings row to **"OpenAI · no backup if it's down"** and keep the model name inside the section. Rename the Status disclosure to **"Technical details: which AI answers each job"**. Drop the reused-answers line, or move it inside the disclosure as "Saved by reusing answers this month: $0.00".
- Severity: minor. Effort: S.

**6. Vague Settings summaries** (settings rows "Personality and family", "Messages", "What has changed")
- Problem: "Vera's first personality" sounds like a version number. "Weekend suggestions are off until you pick a chat for them" doesn't say which chat, and Telegram isn't connected anyway. "What has changed · Nothing yet" could mean app updates or setting changes.
- Fix: Change Personality to **"Vera's standard voice · doesn't know your family yet"**. Change Messages to **"Weekend suggestions: off, choose where Vera sends them · asks how a plan went at 10 am"**. Change What has changed to **"Changes to these settings: none yet"**.
- Severity: minor. Effort: S.

**7. Kids get different words for the same idea states** (home-kid, "New ideas" card: "Vera hasn't checked this yet"; parent Home "Just added to Ideas", "Not looked up yet")
- Problem: This breaks §3's "one word per thing" and the filter word "Not looked up yet". A kid and a parent describing the same card use different words.
- Fix: On both pages, use **"Just added to Ideas"** as the card heading and **"Not looked up yet"** as the tag. "Look up" is grade-4 language already.
- Severity: minor. Effort: S.

**8. Wrong or slippery claims in banners** (plans, Google banner "These are the plans Vera made."; home lede "three to-dos have slipped past their dates")
- Problem: Plans are also added by hand ("Add a plan"), so "plans Vera made" is false. "Slipped past their dates" is a little cute, and it adds a third word for late ("late", "Overdue" heading, "slipped past").
- Fix: Change the Plans banner to **"Google Calendar: not connected. These plans are only in FamilyDB for now. Connect it to see them on your phones' calendars too."** Change the Home lede to **"Roller rink tomorrow, and three to-dos are late."**
- Severity: minor. Effort: S.

**9. Button and label drift** (status "Add a key" vs table "Add key" vs states "Add a backup key"; signin "Sam · Admin" vs "Alex · Parent"; signin "Brand-new install: one family password")
- Problem: Three labels for one action break §3 ("Add key"). "Admin" next to "Parent" suggests Sam isn't a parent. "Install" is a machine word on a page the kids see.
- Fix: Use **"Add a backup key"** everywhere the key would be the backup, and "Add key" only in the table. Label Sam **"Parent · admin"**. Change the sign-in heading to **"For now, everyone shares one family password"** (the wording §3 already asks for).
- Severity: minor. Effort: S.

**10. Spelling and locale don't match the family** (settings "Colours in FamilyDB", "°C and kilometres"; todo filter "Cancelled"; verb "Tick one off")
- Problem: The family is in Vancouver, WA and pays in dollars, but the UI copy is in British spelling and idiom. A US kid says "check off", not "tick off". The settings value can stay the family's choice, but the interface words should be in one locale.
- Fix: Choose US English for the copy: "Colors", "Canceled", "Check one off when it's done", "Checked off: … Undo", and aria "Mark done" stays. Record the choice in STANDARD §3.
- Severity: minor. Effort: S.

## Missing
- Vera's own outgoing messages: the Telegram reminder, the Thursday weekend suggestions, the "How did it go?" morning question, and the reply when a kid says "I packed my swim bag". This is where most of the family reads the copy, and §3 says the words must match.
- "Connect Telegram" and "Add key" walk-throughs. Bot tokens and API keys are the biggest jargon risk for a non-technical parent. Each step needs plain words and an error written as the fix.
- What Vera knows: how a memory is phrased, and the confirm and undo copy for "forget this", which should be kind when a kid uses it.
- Sign-in failures: wrong password, a kid locked out, session expired, signed out on a shared computer.
- The delete-idea confirmation itself ("Deleting asks once more"), and Undo text for delete and move.
- A kid's late to-do ("Was due Sun 27 Sep", per §3) and a kid's empty states (no wishes yet, no to-dos), read aloud for Theo at 9.
- Alex's (parent, non-admin) view of the pill, cost and a settings link, which §4 describes but no page shows.
- A server-down or offline page in the family's voice, not a stack trace.

## One sentence
Give the green pill its own word, "Vera is ready", so that "Vera is answering" only ever means "she's writing back to you right now".
