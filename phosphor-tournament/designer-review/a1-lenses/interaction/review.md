# Review: hierarchy and flow

## Verdict
**7/10.** The desktop pages put the right thing first: Ask Vera on Home, overdue items at the top of To do, a plain-language verdict on Status, and the one item that needs a look at the top of Settings. On the phone, though, forms and filters push the content people came for about a screen down. Some controls also do something different from what they suggest: the "Remind me to…" chip sends half a sentence, the "Writing as" picker on Chat starts on Sam, and reminder links appear while reminders can't be delivered.
**Optimise before building?** Yes. The phone flows for ticking off a to-do and finding an idea are buried, and the Home chips send broken messages. Both are cheap to fix now and expensive to change once the templates are built.

## Protect
- Home: **Ask Vera** is the first card, with the input and Send in it, and the greeting line sums up the day ("Roller rink tomorrow, and three to-dos have slipped past their dates").
- To do: the **Overdue · 3** group with red left rules and "6 days late" wording, shown above the "Whenever" group.
- Status: the one-sentence verdict banner ("Vera is working, and well under budget") above the numbers, and each problem placed next to the action that fixes it ("No backup … Add a key", "Set up Telegram", "Connect").
- Settings: each section row has a one-line state plus a tag (Needs a look / Could be better / no tag), and the "Reading this list" key explains the tags.
- Chat: Vera's confirmation comes with a **receipt card** ("Silver Falls hike · Added to Plans") that links to the thing it created.
- Plans: the **How did it go?** card, with three large labelled face buttons ("Loved it", "It was OK", "Not great") that each submit on their own, with no extra step.

## Fix, ranked

**1. The suggestion chips send half-sentences** (Home, Ask Vera, the "Remind me to…" and "Save an idea…" chips)
- Problem: In `home.html` each chip is a submit button with `name="text"`. Without scripting, tapping "Remind me to…" immediately sends "Remind me to " to Vera. If the textarea already has text, two `text` values are sent. This affects everyone, and kids most, because they tap chips instead of typing.
- Fix: Keep "What should we do next weekend?" as the only chip that sends straight away. Turn the other two into links that open the composer with the text already filled in: `chat.html?draft=Remind%20me%20to%20`, rendered server-side into the textarea, with the cursor at the end via `autofocus`. Give the chips a different look from the send action: an outline chip with a "✎" mark for "starts a message", and a solid chip for "asks now".
- Severity: blocker. Effort: S.

**2. On the phone, the to-do list starts about a screen down** (To do, phone: quick-add form, Telegram banner, filter tabs, search)
- Problem: The first to-do ("Call the dentist about Theo") starts at about 1,000 px. Before it come the full quick-add form (title, Who, Due, Remind, Add), the Telegram notice, the Open/Done/Cancelled/All tabs (which wrap onto two lines) and the search box. The page's main job, ticking something off, is out of view.
- Fix: Order on phone: heading → Open/Done/All tabs (put Cancelled under All, and drop the count text so the tabs fit on one line) → list → quick add. Shrink quick add to a single row ("Add a to-do… [+]") and put Who / Due / Remind inside a `<details><summary>More options</summary>`, which works without scripting. Move the Telegram notice below the list as a single line, or show it only when someone ticks Remind. Hide search behind a search icon when there are fewer than about 15 open items.
- Severity: major. Effort: S.

**3. On the phone, the idea filters fill the first screen** (Ideas, phone: Save a thought, tabs, Search, Kind, Status, For, Show)
- Problem: The first idea card starts at about 1,000 px. Before it come Add an idea, the Save a thought box, the tabs, a "Newest first" label that isn't a control, three full-width selects and a Show button. "Find an idea" turns into "fill in a form". The Restaurants tab also repeats Kind = Restaurant.
- Fix: On phone show the search field, then one `<details>` with the summary "Filter · Any kind, any status, anyone", which holds the three selects and Show. When a filter is set, put its values in the summary line ("Filter · Restaurant, for Theo") with a "Clear" link. Turn "Newest first" into a real sort select, or remove it. Leave Save a thought at the top: it's cheap and it's the quick-capture path.
- Severity: major. Effort: S.

**4. "Writing as" starts on Sam and doesn't follow the conversation** (Chat, the Writing as picker)
- Problem: The signed-in person is already Sam, and the picker defaults to Sam. On a shared laptop a kid who doesn't notice the picker posts as Sam in the family chat. It also offers Maya and Theo while you are in the Family thread, so anyone can speak for a kid. In Maya's own conversation, choosing "Theo" makes no sense.
- Fix: Default to whoever is signed in, and collapse the picker to a single line: "Writing as **Sam** · Change". Show the four chips only after Change is clicked, using `<details>`. In a kid's own conversation, don't show the picker at all: it is always that kid. Optionally, after a message is sent "as" someone other than the signed-in person, show a small line under the bubble ("sent by Sam as Theo").
- Severity: major. Effort: S.

**5. Sending a message ends in "Reload if nothing shows"** (Chat, compose footer)
- Problem: Without scripting, the person sends a message, sees nothing happen, and has to reload by hand. Kids won't, and they'll send the message again.
- Fix: Use post-redirect-get to the thread with the user's bubble shown straight away, followed by a "Vera is thinking…" placeholder bubble. While a reply is pending, render only that page with `<meta http-equiv="refresh" content="3">`, then stop refreshing once the answer arrives. Replace the hint with "Vera is answering…". After 30 seconds show "Vera didn't answer. Try again", with a button.
- Severity: major. Effort: M.

**6. Ticking a to-do has no confirmation and no undo** (Home To do card and To do list, the round tick buttons)
- Problem: The tick is a 34 px circle that posts at once. On a phone, a thumb tap that misses or a curious kid ticks the wrong item, which then drops out of the Open list with no trace. The tick is also smaller than the 44 px used for every other control.
- Fix: Make the tick hit area 44×44 px (the circle can stay 34 px inside it). After the post, redirect back with a status bar at the top of the list: "Ticked off: Call the dentist about Theo · **Undo**". Undo is a one-button form. Keep the item in place for that render, struck through, instead of removing it.
- Severity: major. Effort: S.

**7. The phone navigation hides Wishes, which kids use** (all pages, phone tab bar: Home, Chat, Ideas, Plans, To do, More)
- Problem: Wishes and What Vera knows sit behind More, a page that isn't drawn. For a kid, the wish list is the reason to open the app. Meanwhile the desktop sidebar badges "Ideas 12" (a total, which doesn't need anyone) in the same badge style as "To do 3" (overdue, which does).
- Fix: Build the tab bar per role. Kids get Home, Chat, Wishes, To do and More (Ideas and Plans go under More). Parents keep the current set. Use badges only for things that need action (overdue, settings needing a look, plans to rate). Drop the "12" and show the total on the Ideas page itself.
- Severity: major. Effort: S.

**8. Pages contradict each other about whether it's working** (Status job table and verdict vs Settings › Lookups, Ideas "Look it up")
- Problem: Settings says "Lookups · Off: Vera won't look things up on the web", with no tag. Status still lists "Web lookups · gpt-6-luna" and says "Vera is working". Ideas offers "Look it up" links and says "Vera has looked up 10". A parent checking "is it working" gets three different answers.
- Fix: The Status verdict should list every feature that is off or not set up: "Working. Lookups are off, and Telegram and Calendar aren't set up." In the job table, show the Web lookups row as "Off · Turn on" instead of a model name. Give Settings › Lookups a "Could be better" tag. When lookups are off, change Ideas' "Look it up" to "Lookups are off" and link it to the setting.
- Severity: major. Effort: S.

**9. Things that can't work are offered as if they can** (To do: the Remind checkbox and the "No reminder · Add one" link on every row)
- Problem: The banner says reminders won't reach anyone, but each row still invites "Add one" and the quick add has Remind. This adds clutter to every row (a 5th column on desktop) and sets up a promise that fails without any notice.
- Fix: While Telegram isn't linked, remove the per-row reminder column and show the Remind checkbox as disabled, with the help text "Needs Telegram. Set up". Once Telegram is linked, show a bell only on rows that have a reminder ("🔔 Tue 9:00"). Put "Add reminder" inside Edit, not on every row.
- Severity: minor. Effort: S.

**10. On the phone, the month grid shows unlabelled bars** (Plans, phone: month calendar)
- Problem: At 390 px, events shrink to 4 px coloured bars with no title or time, and they are tiny tap targets. The same plans then appear as a readable list in "Coming up" further down. "How did it go? · 2 to answer" sits at the very bottom, and Home doesn't show it at all.
- Fix: On narrow screens (under 600 px), default Plans to the List view, grouped by week, and keep Month as an option. Move "How did it go?" above the calendar or list while it has anything to answer, and add a one-line card on Home: "How did Silver Falls go? 😊 😐 ☹". On desktop, keep the "Rate it" chips in past cells.
- Severity: minor. Effort: M.

## Missing
- Kid view of Home, Chat and To do: what Maya sees, with no setup card, no spend, no "Writing as", her own to-dos and her wish list near the top.
- Empty and first-run states: Home with no plans, no to-dos and no ideas, where each empty card says what to tell Vera ("Try: 'we should go to…'").
- Error and limit states: Vera at the daily limit, the OpenAI key failing, Vera not answering. These need to be shown on Home (the Vera today card), Chat (above the composer) and Status, with the one next action.
- Confirmation and result screens after posting forms (add to-do, save a thought, rate a plan, change setting), using one shared flash-message pattern with Undo where an action removes something.
- The More page on phone, and how the signed-in person is switched there ("Not you? Switch" only exists in the desktop sidebar).
- Long lists: To do with 30 open items and Ideas with 100. They need paging, "show done this week" and how search results look when nothing matches.
- Plans list view and an empty month, plus what happens when a plan is moved from Home's "Move it" (where it lands, and how you get back).
- Kids' conversation from a parent's side: a read-only notice in Maya's thread, and the "a parent can read this" note at the top of the kid's own view.

## One sentence
On every page, put the item people came to act on (the to-do to tick, the idea to find, the message to send) before the forms and filters on the phone, and make each control do exactly what it looks like it does.
