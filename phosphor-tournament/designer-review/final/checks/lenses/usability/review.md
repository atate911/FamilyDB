# Usability review: FamilyDB final design

Lens: a moderated test with the family (Sam and Alex, the parents; Maya, 11; Theo, the younger kid), on a laptop and on phones. I walked six tasks through the pictures and the source pages.

**The six tasks walked**

1. **Sam: "Tell Vera to plan Saturday."** On the desktop and phone Home the Ask Vera box is the first thing under the greeting, with a big yellow Send button. This passes with no hesitation. Two snags. The only weekend starter, "What should we do next weekend?", sends straight away because it is an `--ask` starter. Its pen-icon neighbours "Remind me to…" and "Save an idea…" only fill the box. The pills look nearly the same, so a tester who taps one just to see what it does sends a paid message. On the phone, the "3 setup steps left · Continue" bar sits above Ask Vera and pushes it down. It is still above the fold, so this is minor.
2. **Alex: "Tick off the dentist to-do."** To do → the first overdue row, "Call the dentist about Theo", then the 44 px ring. This passes. The flash with Undo and the struck-through row (states-actions, "Ticked off: … Undo") is exactly what a tester needs to trust the tap. It also works from Home's To do card without leaving the page.
3. **Alex, on the phone: "Find the ramen place."** Ideas is not in the phone tab bar (Home, Chat, Plans, To do, More), so Alex has to guess More → Ideas. Phone Home's "Just added to Ideas" shows only two cards (Lego set, Board game night), and the ramen card isn't one of them. On the Ideas page the first text box is "Save a thought for later", and its placeholder says *"e.g. that ramen place Alex mentioned"*. Expect testers to type "ramen" there and press **Save**, which creates a junk idea instead of finding Ramen at Afuri. The real search box sits below the Looking-things-up banner, and its button says "Show ideas" rather than "Search". The Restaurants tab (2) would have found it in one tap, but it reads as a filter chip, not a way in. **Likely failure.**
4. **Sam: "See what it is costing."** There are three routes: the "Vera today $0.00" card on Home, the "Vera is answering" pill, or Status. On Status, "Spent today $0.00 of your $2.00 daily limit" and "$1.26 in 30 days" are clear. Testers will hesitate at the near-empty bar, whose only mark is a 1 px "upright line" explained in a sentence. On the phone, "Change the limit" is a small link and the "Last 30 days" card falls below the tab bar. There is no picture of cost over time, only three totals. This passes.
5. **Sam: "Add a to-do for Alex."** Sam types into "Add a to-do…". The **Add** button sits right next to the box, before the collapsed "Who, when, reminder · Sam · No date · No reminder" line. Most testers will press Add, and the to-do goes to **Sam**, not Alex. Even those who notice the line have to open a disclosure for the Who select. The reminder checkbox is greyed out because Telegram isn't connected, and the reason sits in small hint text. The phone summary starts with a stray "· Sam". **Likely failure on the first try.**
6. **Maya (11), on the phone: "You packed your swim bag. Mark it done."** My to-dos shows "Pack your swim bag" next to a square tile holding a **check-box icon** (`.tick-ro`, the same i-todo glyph as the tab). It looks exactly like a tickable box. Maya will tap it, and nothing happens. The explanation, "Sam or Alex tick these off… tell Vera", comes in a separate banner below. "Tell Vera" opens an empty chat (`chat-kid.html`, no draft), so she must also think up the sentence. **Hesitation, then a likely give-up.**

## Verdict
**7/10.** The core loops (ask Vera, tick a to-do, read the cost, see what's next) are short, plainly worded and visible on the first screen, with good feedback (flash plus Undo, error summaries written as the fix). But three of the six tasks hit predictable stumbles. The ramen search collides with the "Save a thought" box. The quick-add sends to-dos to the wrong person. A kid's read-only to-do wears a checkbox icon.
**Optimise before building?** Yes. The three stumbles are cheap layout and wording changes now, but they become support questions ("why is everything assigned to me?") once built.

## Protect
- Home: the Ask Vera card first, with the "Goes to the family chat as Sam" line under it, so everyone knows where the message lands.
- To do and Home To do card: the 44 px tick ring, the red left edge, and "6 days late" said in words, not only in colour.
- states-actions: "Ticked off: … Undo" flash, with the ticked row kept in place and struck through until the next page view.
- Chat (phone and desktop): "Writing as Sam · Not you? Sign out" right above the box, for shared computers.
- Settings and Status: every problem row pairs a plain-word tag ("Needs a look", "Not connected") with its one fixing button ("Set up sign-ins", "Connect Telegram").
- grownups page: "This part is for grown-ups" with "Go to my Home" and "Ask Vera something", a kind dead end instead of an error.

## Fix, ranked

**1. Quick-add assigns to the wrong person** (To do, quick-add form; also the quick add on states-actions)
- Problem: Add sits between the title and the collapsed "Who, when, reminder" line, so Sam presses Add before seeing the owner and every to-do defaults to Sam. Alex's to-dos get lost under Sam's name. It hurts the parents most, because they assign to each other and to the kids.
- Fix: show **Who** as a visible row of person pills (Sam / Alex / Maya / Theo / Everyone, as on idea-new "Who's it for?") between the title box and Add, with nothing preselected or the viewer preselected and highlighted. Keep only "When" and "Reminder" in the disclosure. Put Add last, after the pills. Have the flash name the owner: "Added for Alex: …". Remove the leading "·" in the phone summary.
- Severity: major. Effort: S.

**2. "Save a thought" sits where people look for search** (Ideas, top of page, desktop and phone)
- Problem: the first box on Ideas is a write box whose placeholder is "that ramen place Alex mentioned", which is exactly what someone looking for the ramen place types. They press Save and create a duplicate idea. The real search is lower, after a banner, with a button called "Show ideas". Everyone who comes to find something is hurt by this.
- Fix: put the search box first, directly under the title, with the button labelled **Search**. Move "Save a thought for later" below the list or into the "Add an idea" area, and change its placeholder so it doesn't use an example that's already saved (e.g. "a hike someone mentioned"). When a jot matches an existing idea, the flash should say "You already have Ramen at Afuri. Open it?"
- Severity: major. Effort: S.

**3. Kid's read-only to-do looks tickable** (todo-kid and home-kid, "Pack your swim bag" tile)
- Problem: the `.tick-ro` tile shows a checkbox-with-tick icon in a square the size of a button. Maya taps it and nothing happens, and the explanation is in a separate banner below. This hurts the kids, who must be able to use the app.
- Fix: replace the tile with a non-control glyph, such as the clock or a small "Set by Alex" avatar, and give it no border or button shape. Put a real button on the row itself: "I did it", which posts a message to Vera or the parents ("Maya says she packed her swim bag"). At minimum, make "Tell Vera" link to `chat-kid.html?draft=I packed my swim bag#ask-text`.
- Severity: major. Effort: S.

**4. Ideas is hidden on the phone** (phone tab bar, Home "Just added to Ideas")
- Problem: Ideas is one of the five things Vera keeps, but on the phone it lives under More. Phone Home shows only two recent ideas, so "find the ramen place" starts with a guess. This hurts parents on phones, which is most use.
- Fix: for parents, swap a tab, e.g. Home, Chat, Plans, Ideas, To do, with Wishes, Status and Settings under More and the To do badge kept. If five tabs must stay as they are, add a search field to phone Home ("Find an idea, plan or to-do") that searches all lists. At the very least, show four recent ideas plus a "Restaurants" link on phone Home.
- Severity: major. Effort: M.

**5. Starter pills that send look the same as ones that only fill the box** (Home Ask Vera, chat-kid starters)
- Problem: "What should we do next weekend?" sends a paid question on tap, while "Remind me to…" and "Save an idea…" only fill the box. The difference is just the icon (paper plane versus pen). Kids exploring will fire questions and use up their daily messages (chat-kid, "20 messages left today").
- Fix: make starters fill the box and never send. If a one-tap send stays, end its label with an arrow and give it the filled style ("Ask: What should we do next weekend? →"). Add a Saturday-specific starter on a weekend morning ("Plan today", "Plan this Saturday").
- Severity: minor. Effort: S.

**6. Edit for a to-do is not designed** (To do, "Edit" links point to `todo.html#t-dentist`)
- Problem: Edit is the only way to change the owner, the due date or the reminder, or to cancel a to-do. Its target is an anchor on the same page, and no edit form is drawn. Testers will expect "move the dentist to Tuesday" and "cancel this" to be there. Cancelled is a filter tab, but nothing shows how a to-do gets cancelled.
- Fix: draw the to-do edit page or inline expand, with title, Who pills, Due, Reminder, **Cancel this to-do** as a text button, and Save. On phone, also offer "Push to tomorrow" as a one-tap row action for late items.
- Severity: major. Effort: M.

**7. The spend meter shows almost nothing** (Status, "Spent today" bar; Home "Vera today")
- Problem: at $0.00 the bar is empty, with a 1 px "upright line" that a sentence has to explain. Parents asking "is it costing a lot?" get no picture of the 30 days. The brief asks for calls and cost over 30 days, and the page shows three totals.
- Fix: add a 30-bar sparkline of daily cost with the daily limit as a line, labelled "last 30 days, most $0.11 on 27 Sep". Make the usual-day marker a labelled tick ("usual 4¢"). On the phone, put "Change the limit" as a full-width quiet button under the meter.
- Severity: minor. Effort: M.

**8. Reminders look available but are greyed out** (To do quick-add "Reminder"; every row "No reminder")
- Problem: every to-do shows "No reminder" with a struck bell, and the reminder checkbox is disabled. The reason is in small hint text. Parents will try to add a reminder for Alex and not understand why they can't.
- Fix: while Telegram is off, replace the disabled checkbox with one line plus a button: "Reminders need Telegram. [Connect Telegram]". Hide the per-row "No reminder" metadata until reminders are possible, because it says the same thing four times.
- Severity: minor. Effort: S.

**9. Too many routes to Status, and the pill isn't clearly a link** (top bar and sidebar "Vera is answering")
- Problem: the green health pill is a link to Status but looks like a label. Nobody in the walk-through would click it to find cost. Meanwhile the Home "Vera today" card duplicates Status. This is harmless, but the pill doesn't add a reliable route.
- Fix: add a chevron or underline on hover and focus, and give it an accessible name: "Vera is answering. See status and spending".
- Severity: minor. Effort: S.

**10. Phone Home is very long** (phone home, roughly 6,500 px)
- Problem: Wish lists, the rating card and Vera today sit below roughly seven screens of scroll. "1 to decide" on Maya's wish is easy to miss on the phone.
- Fix: on the phone, collapse Next up to the first plan plus "3 more", and To do to the overdue items plus "All 4". Move "How did it go?" and the "1 to decide" wish above Ideas, since they ask the parent to act.
- Severity: minor. Effort: S.

## Missing
- The to-do edit page (owner, date, reminder, cancel). Two of my six tasks need it.
- What happens right after "Send" from Home: does the page go to Chat with "Vera is thinking…", and where is the reply? The states sheet shows waiting in chat, not the Home-to-Chat handover.
- Search results and an empty search on Ideas ("No ideas match 'ramen'. Save it as a new idea?").
- A way for a kid to say "done" or "I can't" on their own to-do without typing to Vera.
- The phone Plans month view: phone Plans shows "Coming up", and it isn't clear how a parent moves a plan on the phone.
- First-visit help for the kids: what Vera is, the message limit, and the fact that parents can read their chat, said once in kid words.
- Confirmation copy when a parent ticks someone else's to-do ("Ticked off for Alex. Alex gets a message").
- A results flash after "Save a thought", so the person sees where it went in the list.

## One sentence
Put the visible **Who** pills between the to-do box and the Add button, so a to-do can't silently be assigned to the wrong person.
