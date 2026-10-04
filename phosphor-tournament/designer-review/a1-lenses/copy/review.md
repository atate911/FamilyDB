# FamilyDB design review: words and content

## Verdict
**7/10.** Most of the writing is warm, plain and to the point. Home's opening summary, the Status headline and the one-line state for each Settings section read like a person talking to a family, not like software. What lets it down is consistency. The same thing gets three or four names across the seven pages: the whole family, "no date", "not connected", the weekend suggestion. Setup and admin wording also slips into the pages ("the installer", "Telegram bot", "Calls to the AI", "From the cache"). A kid or a non-technical parent can't follow that.

**Optimise before building?** Yes. The mixed terms are cheap to fix now, but once the unbuilt pages, Vera's replies and the Telegram messages copy them they'll be hard to change.

## Protect
- Home, the line under the greeting: "Roller rink tomorrow, and three to-dos have slipped past their dates." It sums up the day in plain words.
- Home, the Ask Vera card: "say it the way you'd say it at the table" plus the example chips. This shows a kid what to type.
- To do, the overdue rows: "6 days late" in red, "Tick one off when it's done", and the screen-reader labels "Mark done: Call the dentist about Theo".
- Status, the top banner and the No-backup box: "Vera is working, and well under budget.", "Checked when you opened this page.", and "if OpenAI is down Vera can't answer", which is followed straight away by the fix.
- Settings, the one-line state under each section ("Off: Vera won't look things up on the web"), the "Reading this list" legend and "Only Sam can change these."
- Chat, the honesty about privacy: "Parents can read the kids' chats. Maya and Theo see a note saying so at the top of theirs." Also the "Writing as" picker.

## Fix, ranked

**1. One name for "the whole family"** (To do: the "Who" select and the rows; Home: the To do card; Ideas: the cards and the "For" filter; Plans: the Coming up list)
- Problem: the same group is called "Household" (To do and Home, with a ★), "Anyone" (Ideas cards and the For filter), "Everyone" (Plans → Coming up) and "Family" (Chat, also with a ★). A kid can't tell whether "Household" includes them. A parent can't tell whether a to-do for "Household" belongs to anybody.
- Fix: use **"Everyone"** on display and in selects ("Who: Everyone", "For: Everyone"), always with the ★ avatar. Make the filter default **"Anyone"**, because the filter means "don't filter by person", which is a different meaning. Keep "Family" only as the name of the shared chat. On a to-do, "Everyone" should read as "nobody in particular", so add the hint "Anyone can tick it off" under the select.
- Severity: major. Effort: S.

**2. Say whether Vera looks things up, and say it the same way everywhere** (Settings → Lookups; Ideas: subtitle, Save a thought, the "Look it up" links; Status → Which AI does each job)
- Problem: Settings says "Lookups · Off: Vera won't look things up on the web". In the same state, Ideas says "Vera has looked up 10", "Vera will look it up and sort it", and offers "Look it up" links, and Status lists "Web lookups · gpt-6-luna". A parent reading both can't tell what Vera actually does, or why drive times are missing.
- Fix: make each of these lines depend on the setting. When it's off, Ideas subtitle: "12 ideas. Looking things up is off, so there are no hours, prices or drive times for new ones. Turn it on in Settings." Save a thought hint: "Just the gist. Vera will sort it for you." Swap "Look it up" for "Turn on lookups" (parents) and remove it for kids. On Status, the row reads "Off". Use one verb, "look up", everywhere, never "lookup" as a noun on family-facing pages.
- Severity: major. Effort: S.

**3. Take out setup and machine wording** (Settings banner and Sign-in row; Home → Finish setting up; Status → Last 30 days and the Spent today note; Settings → Personality; Chat footer)
- Problem: these lines assume someone knows how the app was installed or how AI billing works:
  - "the password the installer made"
  - "Add a Telegram bot"
  - "Calls to the AI · Each question or lookup is one or more calls"
  - "From the cache 0% · Answers reused cost less. Normal while it's new"
  - "she stops using the AI until midnight": to the family, Vera *is* the AI
  - "Vera, as first written"
  - "Reload if nothing shows"
- Fix, line by line:
  - Settings banner: "Everyone still signs in with the same starter password. Give each person their own so Vera knows who's talking."
  - Sign-in row: "Everyone shares one starter password."
  - Home setup step: "Connect Telegram · So the family can text Vera from their phones."
  - Status tiles: "Questions answered 6" / "Cost $1.26 · about $0.04 a day". Move the cache figure behind a "Details" disclosure, or drop it.
  - Spent today note: "If Vera hits the limit, she takes a break until midnight and tells you in the chat."
  - Personality: "Vera's usual personality · she doesn't know about your family yet".
  - Chat footer: "Vera usually answers in a few seconds. If her reply doesn't appear, refresh the page."
- Severity: major. Effort: S.

**4. One set of words for connection states** (Chat header "Telegram not linked yet"; To do banner; Home → Vera today; Status → Connections; Settings → Connections; Plans banner)
- Problem: Telegram is "not linked yet", "isn't set up yet", "Not set up" and "Add a Telegram bot". Google Calendar is "isn't connected yet", "Not connected", "Calendar not connected". The buttons say "Set up Telegram", "Connect calendar", "Connect Google Calendar" and "Connect". The AI keys are "Set" / "Not set". A parent can't tell whether these are different states.
- Fix: two states only, **"Connected" / "Not connected"**. Buttons say **"Connect Telegram"** and **"Connect Google Calendar"** in full, every time, even when the column is short. For the AI keys use "Added" / "Not added" and the button "Add key". The Chat header changes from "Telegram not linked yet" to "Telegram: not connected".
- Severity: major. Effort: S.

**5. Settings: every tag comes from the legend, and every line can be understood without opening the section** (Settings: the Messages, Personality, Connections and Spending rows)
- Problem: "Tell her about you" (an action dressed as a status tag) and "2 not set up" aren't in the "Reading this list" legend, which defines only "Needs a look" and "Could be better". "No weekend ideas: no chat is chosen for them · asks how a plan went at 10:00" is hard to follow: which chat, and 10:00 on which day? "about $0.00 spent today" puts "about" in front of zero.
- Fix: Personality and Connections get the tag "Could be better", and the action moves into the state line. Messages: "Weekend suggestions are off: pick which chat gets them · Vera asks how a plan went the morning after, at 10:00". Spending: "Up to $2.00 a day · nothing spent yet today". Connections: "Telegram and Google Calendar not connected".
- Severity: minor. Effort: S.

**6. One name for the weekly suggestion** (Status → Which AI does each job; Settings → Messages; Vera's own replies)
- Problem: it's "Weekend digest", "The weekly 'what should we do'" and "weekend ideas". "Digest" is jargon, and "ideas" is already a section with its own meaning. "Backup" is used both for the AI fallback (Status) and by Vera for a rainy-day plan (Chat). That's a small clash, but it shows up on the parent's screens.
- Fix: call it **"Weekend suggestions"** everywhere, with the hint "Vera's Thursday message: what fits your free weekend". If that day isn't fixed, write "Vera's weekly message". On Status, rename "Backup if it fails" to **"If it's down, Vera switches to"**, and the "None" value to "Nothing yet".
- Severity: minor. Effort: S.

**7. Dates and times a kid can read, and that match each other** (Chat: Vera's confirmation and the plan card; Plans and Home: times; To do: the date field)
- Problem: Vera confirms "Done: Silver Falls hike, Saturday 10:00 to 14:00" without a date. The card says "Added to Plans · 10:00 to 14:00", still with no day. Yet Plans and Ideas show the hike on Thu 1 Oct, so a reader can't check what she booked. Times use a 24-hour clock ("13:00", "19:00") while the to-do date field shows "mm/dd/yyyy" and General says "Vancouver, WA". The kids will trip over "13:00".
- Fix: every confirmation states the weekday, date and time: "Done. Silver Falls hike is on Sat 3 Oct, 10 am to 2 pm." The plan card reads "Added to Plans · Sat 3 Oct, 10 am–2 pm". Take the clock format from Settings → General and add it to that line ("Vancouver, WA · °C, km, 12-hour clock") so the choice can be seen and changed.
- Severity: major. Effort: S.

**8. "No date" and reminders on To do** (To do: the "Whenever" group, the reminder column and the Remind checkbox; Home: the To do card)
- Problem: a to-do with no date is "Any time" on Home, and "Whenever · 1" plus "No date · Whenever suits" on To do. That's three phrasings for one state, two of them on the same row. "No reminder · Add one" repeats on all four rows and drowns out the reminders that are set. The "Remind" checkbox doesn't say when the reminder goes out or to whom.
- Fix: the group heading is **"No date"**, the row shows only "No date", and Home uses "No date" too. Show the reminder bell only when a reminder is set ("Reminder Tue 9:00"). Put "Add a reminder" inside Edit. Relabel the checkbox **"Remind them on the due date"** and add a hint giving the time Vera sends it. While Telegram isn't connected, the hint reads "Won't send until Telegram is connected."
- Severity: minor. Effort: S.

**9. Clear up the Ideas words** (Ideas: the filter button, the card tags, the Kind list)
- Problem: the filter button is labelled "Show", but "Show" is also one of the kinds (Nutcracker). "Not looked up yet" appears twice on the Lego and Board game cards (a tag at the top and text at the bottom). The kinds overlap: a parent can't tell Activity from Outing from Event, and there's no gift kind, so "Lego set for Theo" is filed under "Other" although the brief names gift ideas. The status filter says "Been there" while the cards say "Went Thu 1 Oct".
- Fix: rename the button **"Filter"**. Keep "Not looked up yet" in the footer only. Kinds: Outing, Restaurant, Day trip, Trip, Show, Seasonal, Gift, Other (merge Activity and Event into Outing, or explain each in the select). Use one word for status: the filter is "Been" and the card tag "Been · Thu 1 Oct", or both say "Went".
- Severity: minor. Effort: S.

**10. Fix the ambiguous small labels** (phone header "Vera is on"; Chat "Send where I am"; Plans "Rate it" and the face buttons; Home phone chip "Remin…")
- Problem: "Vera is on" doesn't say on what, or what "off" would mean. "Send where I am" reads like an instruction, and a kid could tick it without knowing it shares their location. The calendar says "Rate it" while the card below asks "How did it go?" with three wordless faces. On the phone the "Remind me to…" chip is cut off at "Remin".
- Fix: header "Vera is answering" (or "Vera's taking a break" once the limit is reached). The checkbox reads **"Share my location with this message"**. On kids' accounts it's off by default with the hint "Only tick this if a grown-up says it's OK." The calendar link reads "How did it go?", and the faces carry visible words: "Loved it", "OK", "Not great". On the phone, let the chips wrap instead of cutting them off.
- Severity: minor. Effort: S.

## Missing
- What a kid sees: Home greeting, To do and Wishes in Maya's voice, and the note at the top of her own chat ("Mum and Dad can read this chat too"). None of this is drawn, and the wording has to work for a young reader.
- Empty states: a first day with no ideas, plans or to-dos, and searches or filters with no results ("Nothing matches 'ramen'. Clear filters").
- What Vera says when she can't answer: the spending limit reached (Home, Chat, Status), OpenAI down, a message that failed to send, a lookup that found nothing.
- Connections that worked and then broke (Telegram unlinked, Google Calendar access expired) and what the Settings tag and line say then.
- Confirmations and undo: to-do ticked off or cancelled, idea deleted, "forget this" on What Vera knows, plan moved. Each needs a short message and an Undo.
- Form errors on the quick adds: an empty to-do, a due date in the past, an empty "Save a thought".
- The text of the Telegram messages Vera sends (a reminder, weekend suggestions, "how did it go?"), so they use the same terms as the website.
- Wording for sign-in, choosing a password and the first-time setup steps, including the steps a non-technical parent will hit (Telegram, keys).

## One sentence
Before anything is built, agree one word for each thing (Everyone, No date, Connected / Not connected, Weekend suggestions, look up) and use it on every page, in Vera's replies and in her Telegram messages.
