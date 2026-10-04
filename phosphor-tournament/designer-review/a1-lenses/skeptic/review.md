# Review: FamilyDB design (a1), through a skeptical lens

## Verdict
**6/10.** On desktop, with this small and tidy sample (12 ideas, 4 to-dos, one plan a week, short names), it is warm, clear and honest. But the phone layouts are already breaking with this sample: the calendar loses all its text, the chat box sits below the whole thread, labels wrap badly. Pages like Status and Settings also say different things about how healthy the app is. All of this will get worse once a real family's data arrives.

**Optimise before building?** Yes. The phone calendar, the phone chat and the "is it OK?" messages are each a bug in how the design works, not a matter of looks, and they are cheap to fix now and expensive to fix once built.

## Protect
- **Home, "Ask Vera" panel**: the dark green box with the input, the Send button and the suggestion chips is the first thing on the page. You can write to Vera without looking for it.
- **To do, overdue rows**: the red left edge, the "OVERDUE · 3" heading and the "6 days late" text say exactly how late something is in words, not just in colour.
- **Settings, one line per section** ("OpenAI, gpt-6-luna · no backup", "Up to $2.00 a day · about $0.00 spent today"), plus the "Reading this list" key that explains the tags. Someone who isn't technical can read it.
- **Status, "Which AI does each job" table and "No backup" warning**: the cost and the risk are explained in plain words, with an "Add a key" button right there.
- **Plans, "How did it go?" card**: three big face buttons with the plan's name and date. A kid can use it.
- **Everywhere, keyboard focus and no-script forms**: there is a 3 px `:focus-visible` outline throughout `style.css`, and ticking a to-do or picking who is writing are real `<form>` posts and radio buttons, so they keep working with scripting off.

## Fix, ranked

**1. The phone month calendar becomes unlabelled coloured bars** (Plans, `.cal` at ≤820 px)
- Problem: at phone width the CSS sets `.ev { font-size:0; height:8px }` and `.ev * { display:none }`. Every plan turns into an 8 px coloured stripe with no name or time. Because the text is hidden with `display:none`, screen readers find an empty link. The tap target is 8 px tall, far below the 44 px a kid's finger needs. The "Today" label is also cut off ("3 TOD"). Two plans on one day would be two stripes that can't be told apart. On a phone, the "Coming up" list below is the only part of the page that does its job.
- Fix: on phones, show the List view by default, and show the month grid only when someone chooses it. In the phone grid, make the whole day cell (at least 44×44) a link to that day's list, mark plan days with up to 3 dots and "+N" for more, and give the link a visible-to-screen-readers label ("Sat 17 Oct: Nutcracker at the Keller, 19:00"). Drop the "Today" word on phones and keep only the ringed date.
- Severity: blocker. Effort: M.

**2. On phones, the chat box sits below the whole conversation** (Chat, `.compose`)
- Problem: on the phone the "Writing as" pills and the "Write to Vera…" box come after every message in the thread. With a real conversation of several hundred messages, the family scrolls through all of it to reply, or lands at the top (with scripting off, nothing scrolls to the newest message). The person picker wraps onto two lines (Theo drops to a second row) and pushes the box down further.
- Fix: show only the latest ~30 messages, with an "Earlier messages" link at the top of the thread. Put an `id="latest"` anchor on the newest message and send people to `chat.html#latest` after they post. Make `.compose` `position: sticky; bottom: 0` on phones. On a phone that one person signs in on, fold "Writing as" into a single line ("Writing as Sam · change"), and show the four pills only on a computer the family shares.
- Severity: blocker. Effort: M.

**3. Status, Settings and the header disagree about whether things are OK** (Status hero, Settings banner, phone header "Vera is on")
- Problem: Status says, in green, "Vera is working, and well under budget" and names two things not set up. Directly below, all three jobs show a red "None" for the backup, and there is a yellow "No backup" warning. Settings opens with "One thing needs a look" (the password). It tags Connections "2 not set up", but the "AI model … no backup" row has no tag at all. Settings also says "Lookups: Off: Vera won't look things up on the web", while Ideas says "Vera has looked up 10" and Status lists "Web lookups" as a job with a model. The parent who runs the app can't tell which page to believe.
- Fix: work out one state per area (OK / Could be better / Needs a look) in one place and show it the same way on all three pages. Status hero: "Working. 3 things could be better: no backup AI, Telegram, Google Calendar." Make the Settings banner list every "Needs a look", not just "One thing". Tag the AI model row "Could be better". If Lookups are off, show "Lookups off" on the Ideas page and in the Status lookups row instead of a model name.
- Severity: major. Effort: S.

**4. Long pages with no limit on the number of items** (Ideas, To do, Home "Just added")
- Problem: on the phone, 12 ideas already make a page about 3,300 px tall, and the filters (Search, Kind, Status, For, Show) take a whole screen before the first idea. A real list of 80 ideas would run over 20,000 px, and nothing in the design shows paging. To do has the same problem with "Done" and "All", which will grow every week.
- Fix: on phones, collapse the filters into one row, a search box plus a "Filters (2)" `<details>` element (works without scripting). Show 20 ideas or to-dos per page with "Show 20 more" as a plain link (`?page=2`). On To do, cap the "Done" view to the last 30 days, with a link for older ones. Show a one-line summary of the active filters above the results ("Restaurants · for Theo · 3 found · Clear").
- Severity: major. Effort: M.

**5. On phones, the forms come before the content** (To do quick-add, Ideas "Add an idea" + "Save a thought" box)
- Problem: on the phone, the "Add a to-do" form (text, Who, Due, Remind, Add) and the Telegram notice fill the whole first screen. The overdue to-dos, the reason for the page, start below the fold. The filter pills also break: "All" wraps onto a second line inside the pill box, and the search box doesn't fill the width.
- Fix: on phones, put the list first. Shrink quick-add to one text field and a "+" button, and show "Who / Due / Remind" only after a `<details>` labelled "More options". Let the filter pills scroll sideways (`flex-wrap:nowrap; overflow-x:auto`), the same way the Home chips already do, and make the search box full width.
- Severity: major. Effort: S.

**6. Long names and long values break the layout** (Status job table, Settings rows, calendar cells, Home chips)
- Problem: on the phone, "gpt-6-luna" breaks at the hyphen into "gpt-6- / luna", and the Telegram row's description wraps onto 6 lines squeezed beside its button. In Settings on the phone, the chevron drops onto a line of its own under General, AI model and Lookups. On desktop, calendar event names wrap to 3 lines ("Mount St. Helens day trip"), so one busy day makes its whole week row taller. On Home on the phone, the suggestion chips are cut off mid-word ("Remin") with no sign there's more to scroll. Real names ("Grandma's 80th birthday dinner at Il Fornaio") will be worse.
- Fix: use `white-space:nowrap` on model names. On the phone, turn the Status table into stacked rows ("Chat → gpt-6-luna (OpenAI) · Backup: none"), and put the action button under the description, not beside it. Put the Settings chevron in the title row (`grid-row:1; align-self:center`). Limit calendar event names to 2 lines with `-webkit-line-clamp:2` and the full title in `title`. Fade the right edge of the chip row so it is clearly scrollable. Test every page with 40-character titles, names like "Maximilian" and 6-figure costs.
- Severity: major. Effort: S.

**7. A kid's view is promised but never shown** (Home, Chat, To do)
- Problem: the brief says the kids must be able to use the app and see different things, but all seven pages are drawn for the parent Sam. Home shows a "Finish setting up" checklist labelled "Only parents see this", money on "Vera today", and the Settings badge. Nothing shows what Maya sees, how big her targets are, or how much reading she has to do. The single round tick on a to-do posts straight away, with no undo, so one wrong tap by a kid marks something done.
- Fix: draw Home and To do as Maya, aged about 8. Show her own to-dos first, then her wish list with ranks and big up/down buttons, then "Ask Vera" and the next family plan. Hide cost, setup and the Settings badge. After a tick, show "Done: Renew library cards · Undo" at the top of the page for this page load, using a POST form so it works with scripting off.
- Severity: major. Effort: M.

**8. Empty and first-week states are drawn only for wishes** (Home "Wish lists", Status, Plans)
- Problem: "No wishes yet" for both kids is the only empty state drawn. Not shown: Home with no plans or to-dos (the large "Next up" card would be empty), Ideas with no ideas, or a filter that finds nothing. Status shows "$0.00" next to a bar whose filled part is a 4 px stub, and "From the cache 0%" in a 30 px number, which looks like a fault.
- Fix: write the empty text for each card ("Nothing planned yet. Ask Vera: 'what should we do this weekend?'", with that question as a button). When there's no data, hide the cache figure or write it as "Not yet". On a $0.00 day, replace the bar with "Nothing spent yet today".
- Severity: minor. Effort: S.

**9. Error and failure states are missing** (Status, Chat, Home "Ask Vera")
- Problem: every page shows success. There is no design for: OpenAI down, the daily limit reached ("she stops using the AI until midnight" is promised but never shown), a message that failed to send, or Vera taking a long time to answer. With scripting off, the "Reload if nothing shows" hint in Chat is all the family gets.
- Fix: draw three states. (a) A Status hero in red, "Vera can't answer: OpenAI isn't responding since 14:02. Add a backup key.", plus a matching red "Vera is off" chip in the phone header. (b) A yellow notice above the chat box: "Today's $2.00 is used up. Vera is back at midnight. Change the limit". (c) An inline note on a failed message: "Didn't reach Vera · Try again". On Chat, use a `<meta http-equiv="refresh">` while an answer is pending.
- Severity: major. Effort: M.

**10. Dates and units are mixed** (To do "Due" field, Settings "General")
- Problem: the Due field shows the browser's `mm/dd/yyyy`, while the rest of the app writes "Sun 27 Sep", 24-hour times and "°C and kilometres" for a family in Vancouver, WA. The text font's crossed zeros ("10:00", "$2.00") look like "Ø" to a young reader.
- Fix: set `lang` to the family's locale and show the chosen format under the field ("Due: Tue 6 Oct"). Add chips for "Today", "Tomorrow" and "Sat", which cover most due dates. Use a figure style for times and money without the crossed zero (`font-feature-settings: "zero" 0`, or a font whose zero isn't crossed).
- Severity: minor. Effort: S.

## Missing
- A kid signed in, and a phone "More" page (`more.html`), which on phones is the only way to reach Wishes, What Vera knows, Status and Settings. Neither is drawn.
- A busy calendar: 4+ plans on one day, plans lasting several days that cross a week boundary (only Cannon Beach's 24–25 is shown), and the "+N more" overflow.
- Home after setup is finished, and Home with a large backlog (20 overdue to-dos, so the "To do" card needs a cap and a "+17 more" link).
- Chat with a long history, a kid's own conversation as a parent sees it (read-only? with a banner?), and messages with links, lists or photos.
- Failure states: AI provider down, daily limit hit, Telegram token rejected, Google Calendar sign-in expired, a failed save, and a 404 for a deleted idea.
- Confirming and undoing: making Vera forget a memory, deleting an idea, cancelling a plan, and undoing a tick.
- Tablet and narrow-laptop widths (820–1000 px), where the layout switches to one column but a phone's spacing is not used yet.
- Large text (200% zoom) and the dark mode a phone may ask for at night. Neither is addressed in `style.css`.

## One sentence
Before building, put every page through a phone with a real family's worth of data (80 ideas, a 300-message chat, a busy October, a kid signed in), because the phone calendar and chat already break with this small sample.
