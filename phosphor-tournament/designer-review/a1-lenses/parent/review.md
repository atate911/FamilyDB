# Review: FamilyDB web design, seen as a parent (Sam)

## Verdict
**7/10.** It's warm and calm, and it mostly speaks my language. Home tells me in one sentence what's wrong today ("Roller rink tomorrow, and three to-dos have slipped past their dates"), and I could write to Vera without learning anything first. What holds it back: on my phone the things that make me trust it (who can read the kids' chats, whether a reminder will actually reach anyone) are quietly hidden. Chat also lets anyone type as anyone, and Status throws AI jargon at me with numbers that don't seem to add up.

**Optimise before building?** Yes. The phone layout, which is where I'll actually use it, drops the privacy and reminder information I need to trust it with the kids and the household.

## Protect
1. Home, the line under "Good morning, Sam.": a one-sentence plain summary of today. That's the first thing I read, and it's enough.
2. Home, the "Ask Vera" card with a big input, a bright yellow Send and the starter chips ("Remind me to…", "Save an idea…"). I can do something in two seconds.
3. Home and To do, overdue rows: red "6 days late" with the owner's face and name. I can see at a glance who dropped what, without anyone being blamed in a big way.
4. Settings, the list where each row says how it stands now ("Up to $2.00 a day · about $0.00 spent today"), plus the "Reading this list" key that explains "Needs a look" and "Could be better".
5. Status, the green banner "Vera is working, and well under budget." and the "Spent today $0.00 of your $2.00 daily limit" bar, with the sentence saying what happens at the limit ("stops… until midnight and says so in the chat").
6. Plans (phone), the "Coming up" list under the calendar and the "How did it go?" smiley buttons. They're quick and kid-friendly, and they make the tiny calendar usable.

## Fix, ranked

**1. Kids' privacy note disappears on the phone** (Chat, the "Parents can read the kids' chats…" note under the conversation list)
- Problem: on desktop the note is there. On phone the stylesheet hides it (`.convo-note { display: none }`) and also hides the page line "the whole family can see it". The phone Chat shows only "Family / Maya / Theo" pills. The kids will mostly be on phones, so they never learn that I can read their chats, and I lose the honesty that makes reading them OK.
- Fix: keep it on every width. On phone, put one line under the pills: "👁 Parents can read Maya's and Theo's chats." In a kid's own thread, put a pinned line at the top of the thread: "Mum/Dad can read this chat." Don't hide `.convo-note` under 820px. Restyle it as a 14px line instead.
- Severity: blocker. Effort: S.

**2. "Writing as" lets anyone post as anyone** (Chat, the Sam / Alex / Maya / Theo chips above the input)
- Problem: on a shared laptop Theo can tap "Sam" and tell Vera "cancel the dentist" or "Theo can have the Lego set", and it shows up in the family chat as me. Nothing shows who is actually signed in. It also defaults to me on a computer the kids use.
- Fix: default "Writing as" to whoever is signed in, and show it as text ("Writing as Sam · Not you? Switch"), not four equal buttons. If you keep the chips, switching to a parent should ask for that parent's password. A kid signed in should only see their own chip. Messages sent "as" someone else should be marked ("typed on Sam's login").
- Severity: blocker. Effort: M.

**3. Reminders: phone To do hides whether a to-do has a reminder** (To do, the "No reminder · Add one" column)
- Problem: desktop shows a reminder status per row. Phone hides it (`.trow .rem { display: none }`). Reminders don't work at all until Telegram is set up, so I'd tick "Remind" on my phone and assume it's handled. That's exactly how the dentist call slips again.
- Fix: on phone, add a third line to each card: "🔔 Reminder Tue 9:00" or "🔕 No reminder". While Telegram isn't connected, show the reminder in amber with the words "won't send – Telegram not set up". Make the "Remind" checkbox in the add form show the same warning inline when ticked.
- Severity: major. Effort: S.

**4. Phone To do: the add form pushes the overdue list off the screen** (To do, the "Add a to-do" card on phone)
- Problem: on phone the first full screen is the form (text, Who, Due, Remind, Add) plus the Telegram notice. The three overdue items only start below the fold. I open this page to tick things off, not to fill in forms.
- Fix: on phone, order it as overdue list first, then a one-line quick add ("Add a to-do…" input + Add button) that expands to Who/Due/Remind only after it's tapped. Move the Telegram notice below the list. Also let the "Open / Done / Cancelled / All" tabs fit on one row: right now "All" wraps onto a second line.
- Severity: major. Effort: S.

**5. Status is written for an engineer** (Status, "Which AI does each job" table and "Last 30 days")
- Problem: "gpt-6-luna / OpenAI", "Backup if it fails: None" in red three times, "From the cache 0%", "Calls to the AI". Three red "None"s make me think something is broken when the banner says it's fine. The numbers also confuse me: 6 calls in 30 days cost $1.26 ("about $0.04 a day"), yet today is $0.00 and the bar says "a usual day ≈ $0.04". I can't tell whether $1.26 is a lot or a little.
- Fix: lead with money in plain words: "This month: $1.26 so far. At this rate about $1.30 a month." Collapse the model table under "Details for whoever set it up". Show "No backup" once, in amber, not three red pills. Rename "From the cache" to "Saved by reusing answers", or drop it. Add a "this month vs last month" line.
- Severity: major. Effort: M.

**6. "Only Sam can change these" excludes the other parent** (Settings, page subtitle)
- Problem: the brief says both parents decide, and Alex is a parent too. If Sam is away and the spending limit or Telegram needs fixing, Alex is stuck. It also reads as if one parent owns the family.
- Fix: write "Parents can change these. Kids don't see this page." If one admin is really needed, say who and how to add another: "Sam and Alex can change these · Add a parent".
- Severity: major. Effort: S.

**7. Setup checklist is buried at the bottom of the phone Home** (Home, the "Finish setting up · 3 left" card)
- Problem: on desktop it sits top-right. On phone it comes after Next up, To do and Just added to Ideas, about four screens down. Changing the installer's shared password is a security item, and on phone I'd never scroll that far.
- Fix: while "Choose your own password" is undone, show one slim red strip on phone right under the greeting: "Everyone still uses the installer's password · Fix it (2 min)". Keep the full checklist where it is.
- Severity: major. Effort: S.

**8. Slashed zeros look like errors** (all pages: times and money, e.g. "Ø9:ØØ", "$2.ØØ", "1Ø:ØØ to 14:ØØ")
- Problem: the font draws 0 with a slash. At a glance on a phone, "09:00" reads like a crossed-out or broken time, and "$0.00" looks odd in the one place I check carefully. The kids won't know what it means.
- Fix: turn off the slashed zero for times, dates and money (for example `font-feature-settings: "zero" 0`, or use a font whose 0 isn't slashed for numbers). Keep the hyperlegible text face.
- Severity: minor. Effort: S.

**9. "Reload if nothing shows" doesn't build trust** (Chat, the hint next to "Send where I am")
- Problem: it tells me in advance that it might not work. On phone the hint is hidden, so a kid who sends and sees nothing just sends again.
- Fix: after sending, show the message right away with "Vera is thinking…" and, after 20 seconds, "Still waiting – Refresh" as a link. Remove the standing hint.
- Severity: minor. Effort: M.

**10. Calendar "today" cell is cramped on phone** (Plans, the 3 October cell)
- Problem: "TODA" is cut off, and the green "3" bubble overlaps the label. The plan bars carry no words, so you only learn what they are from the list below.
- Fix: on phone, drop the "TODAY" word and fill the 3 as a solid green circle. Tapping a day should scroll to that day in "Coming up".
- Severity: minor. Effort: S.

## Missing
- The kid's view of every page: what Maya sees on Home and To do, and that she can't see Settings, Status or cost. I need to see this before I hand her the login.
- The spending limit being hit: what Home, Chat and Status look like when Vera stops, and whether I get a message about it.
- Vera is broken or offline (OpenAI key fails): the red version of the Status banner, and what the Home "Ask Vera" box says then.
- Wishes: how I approve or say no to a wish, and whether the kid sees "No" or just "not yet". This is the most sensitive page for the kids and it isn't drawn.
- Memory ("What Vera knows"): how a kid can make Vera forget something, and whether one kid can see what Vera learned about the other.
- Sign-out and sessions on a shared laptop: how a kid signs out after use, and auto-sign-out.
- Plan detail and "Move it": what happens to the Google Calendar entry and who gets told.
- Who changed what: a visible "Theo cancelled this" or "Vera added this" on to-dos and plans, not only in Settings → "What has changed".

## One sentence
Make the phone layout keep every line that tells us who can see what and whether reminders will really reach someone, because that's what I'd be trusting it with.
