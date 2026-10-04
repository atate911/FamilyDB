# Kitchen Table: stage 1 changes

Stage 1 redraws the seven pages as Sam (admin) signed in as themselves, at desktop and phone width, on a rebuilt system. Files: `style.css` (the system), `icons.svg` (the sprite), `fonts/` (self-hosted WOFF2), and seven pages. Shots: `shots/` (light) and `shots/dark/` (Home, Chat, To do).

## Kept, as the reviews asked

These are unchanged in spirit:

- The dark-green Ask Vera card first, with the yellow Send and the starters.
- The greeting and its one-sentence summary of the day.
- The date tiles.
- "6 days late" written out next to the owner's face.
- The one-line state per Settings section, with tags and a key.
- The plain verdict on Status and the Spent today bar.
- The three faces for rating a plan.
- The receipt card in chat and the colours per person.
- Fraunces with Atkinson at 17 px, 44 px targets, visible focus, and forms that work with no script.

## The synthesis, fix by fix

1. **The phone is its own layout.**
   - A fixed bottom tab bar (Home, Chat, Plans, To do, More), with a late badge on To do and a dot on More when something needs checking.
   - Tools and filters fold into `<details>`.
   - Home on the phone: a slim "3 setup steps left" strip under the greeting. The full checklist stays on desktop.
   - Ideas become compact rows.
   - Settings rows use grid areas (icon | text, tag | chevron), so chevrons no longer drop onto their own line.
   - The Status table stacks into blocks, and its actions sit under each line.
   - Starters wrap instead of scrolling.
   - In full-page shots the fixed bar appears where the first screen ends (844 px). That is where it sits on a real phone.
2. **Phone calendar.**
   - On the phone, Plans opens on the "Coming up" list.
   - The month grid becomes a month at a glance: each day with plans is one whole-cell link with a spoken label ("Fri 9 Oct: Mount St. Helens day trip, 9 am") and dots. Past plans are outlined dots.
   - The "TODAY" word is gone; the filled circle stays, plus `aria-current="date"`.
   - Desktop: the invalid `role="grid"` is removed. Events clamp to two lines, and Cannon Beach is one bar across Sat and Sun.
3. **No kid view.** Stage 2, as FINAL.md sets out. The system is ready for it: role-aware nav, surprise tags, and the privacy line.
4. **Missing states.** Stage 3. The components they need (banner tones, state tags, the composer) exist now.
5. **Reminders.**
   - Rows say "No reminder"; there is no "Add one" on every row.
   - The quick add's "Remind them on the due date" is disabled, and its hint says why: Telegram isn't connected. It links to Connect Telegram.
   - Home says once: "No reminders are set. Reminders go by Telegram, which isn't connected yet."
   - The To do footer says Vera will send it once Telegram is connected.
6. **Numbers.** Every number is in Fraunces with lining, tabular figures, and with no `.num` class needed. Google's Fraunces has no `tnum`, so I built `fonts/fraunces-figures-*.woff2`: digits only, made equal-width, opsz 18, at two weights. It is listed first in both font stacks, so digits render in Fraunces and words fall through to Atkinson. Model names and codes use `.code` (Atkinson, slashed zero kept). Times are 12-hour with no leading zeros.
7. **The system.**
   - Scales are tokens: radius 8/12/18/pill; spacing 4–48 in steps of 4; type 13 (tab labels and the one `.overline`), 14 floor, 15, 17, 19, 20, 24, 40/30, 44.
   - Named components: one `.item` row (lead | body | trail; `--boxed`, `--divided`), one `.todo` row (`--compact` for Home, `--late`), one `.banner` (info / ok / warn / alert, plus `--hero` and `--slim`), one `.composer` (light, and `.ask` on dark green), and one tag vocabulary (`--ok --better --look --broken --off --when --been --surprise`).
   - Two tile sizes (40/56) and three avatar sizes (24/32/40).
   - Kinds of idea are neutral, told apart by icon and word.
   - Calendar events take the colour of who they are for. Several people or Everyone means neutral, with their avatars.
   - Red is used only for late text, the late rule, and (later) broken things. The nav count for late to-dos is a soft red pill.
8. **Contrast.**
   - `--ink-3` #596263: 6.1:1 on card, 5.1:1 on paper-2.
   - Field and tick edges `--edge` #8A806C: 3.9:1 on white, 3.8:1 on card.
   - Ticks have a 44 px hit area around a 32 px ring.
   - Past plans keep full opacity and use a dashed outline.
   - The skip link is visible on focus.
   - Theo is #A2560E (white on it is 5.4:1) and Maya is #B03F66 (5.6:1).
   - Every token pair checks AA in light and dark: text pairs are 4.8:1 or better, control edges 3.8:1 or better.
9. **Who is writing.** The composer says "Writing as Sam · Not you? Sign out"; there is no picker. Home's box says "Goes to the family chat as Sam."
10. **Starters.** Only the complete question sends, as its own form with `name="prompt"`, so it never posts two `text` fields. The stems "Remind me to…" and "Save an idea…" are links (`?draft=…#ask-text`) that the server renders into the box. They look different: the send chip has a send icon and a tint; the stems have a pen icon and an outline.
11. **Chat.**
    - The room is a column-reverse scroller, so it opens at the newest message with no script.
    - "Earlier messages" sits at the top (the server renders the latest 30), and the last message carries `id="latest"`.
    - On the phone, the room fills the screen with the box pinned above the tab bar.
    - "Reload if nothing shows" is gone. The pending and failed states come in stage 3.
    - "Share where I am with this message" is drawn as the scripting-on state; the enhancement script inserts it.
12. **One health state per area.** Each area has one state, written the same way on Status ("How each part is doing"), Settings, the Ideas banner and Home:
    - Vera: Working
    - Spending: Working
    - Sign-in: Needs a look
    - Backup: Could be better
    - Telegram: Not connected
    - Google Calendar: Not connected
    - Looking things up: Off

    The header pill "Vera is answering" covers the Vera area only. The Settings attention moves to the nav badge "1 to check" and the dot on More.
13. **Words.**
    - Everyone (★ became a house); "Anyone" only as the "don't filter" choice.
    - "No date" (one phrase).
    - Connected / Not connected; keys are Added / Not added.
    - Weekend suggestions; "looking things up" and "look up".
    - "Questions answered".
    - Status leads with money in words ("Nothing spent yet today. The last 30 days cost $1.26, about 4¢ a day"). The model table is folded under "Which AI does each job · for whoever set it up". The cache figure is inside that fold and explained.
    - Gone: installer, bot, "calls", "From the cache".
14. **Build safety.**
    - No `style=""` and no `<script>` in any page (the generator asserts both).
    - The meter is an SVG whose widths are attributes.
    - Compass arrows are replaced by words ("27 min drive, south"), as the usability review asked.
    - Fonts are self-hosted (about 75 KB).
    - Icons come from one sprite, `<use href="#i-name">`. *Mockup only:* the sprite is inlined at the top of each page, because browsers refuse an external `<use>` from `file://`. In the app it is `/static/icons.svg#i-name`, and `icons.svg` is that file. The preload link is left out for the same reason; add `<link rel="preload">` for `atkinson-400.woff2` in the app.
15. **Privacy and surprises.**
    - The chat privacy line shows at every width: it sits under the conversation list on desktop and under the pills on the phone.
    - "Buy Maya's birthday present" and "Lego set for Theo" carry a dashed "Surprise · hidden from Maya/Theo" tag in parents' views. On narrow rows it shortens to "Surprise", and the rest is kept for screen readers.
16. **Dark mode.**
    - It's the same kitchen with the lamp on: warm near-black paper, cream ink, a lighter green for Vera's text and a deeper green for her surfaces.
    - The person colours keep their hue.
    - `forced-colors` adds borders wherever selection is shown by background alone (nav, tabs, segments, conversation pills, tags, ticks, today).

## Borrowed from the blind judges

- On the next plan: "Leave by 12:30 pm".
- Key phrases in the summary sentence are links.
- A one-line "How did Silver Falls hike go?" with three labelled faces on Home.
- Each person's colour on their chat bubbles.
- Ideas order by Newest or Nearest.
- A single colour key, "Colours in FamilyDB", on Settings.

Not borrowed: the "in 1 day" countdown. "Tomorrow" already says it.

## Declined or decided differently, and why

- **Vera as a character** (style review). Declined, as decided: she is felt, not shown. Her mark is her initial in her green.
- **Red left bars and red headings removed from To do** (style). Kept, as the 4 px late rule and "Overdue" in red text, because the protect list and five other lenses name them. Red stays text- and rule-only; no red fills.
- **"Hide from…" control on every item** (kid review). The app leaves gifts out of a kid's pages entirely, so parents only need to *see* that something is a surprise, not to set it. A tag is enough for stage 1. Where it's set (Edit) is a stage-3 form.
- **Wishes as a parent tab on the phone.** Parents get Home, Chat, Plans, To do, More, as FINAL.md says. Ideas moves under More for parents on the phone. Kids get Wishes in stage 2.
- **A "Who's writing?" picker with no default** (usability). This applies only before the first admin has chosen a password. Sam is signed in as themselves here, so it isn't drawn. It belongs to the stage-2 shared-laptop sign-in.
- **Meta refresh for pending replies**: noted for stage 3. The page refreshes only while a reply is pending.

## Data I changed so the pages agree

- **Chat.** Alex now says "Put the hike on Thursday at 10", and Vera confirms "Thursday 1 October, 10 am to 2 pm". This matches Plans (Silver Falls, Thu 1 Oct). The brief's version contradicted its own plan list.
- **Setup step 1.** It was "choose your own password". It is now "Give everyone their own password: only Sam has one so far". FINAL.md says Sam is signed in as themselves, so the first admin password exists already. What's left is sign-ins for Alex, Maya and Theo, so "Needs a look" on Sign-in still holds.
- **"Lego set for Theo".** Its kind is now **Gift idea** (it was "Other"). The brief names gift ideas, and the app must recognise gifts to keep them from the kids.

## Known gaps, stage 1

- The More page, the family page and the kid pages are linked but not drawn (stage 2).
- Pending, failed, limit and error states, the after-action flash with Undo, and form errors (stage 3).
- Dark mode is rendered for Home, Chat and To do only. The tokens cover every page, but the rest are unchecked until stage 3.

---

# Stage 2: the missing pages

New pages: `home-kid.html`, `chat-kid.html`, `todo-kid.html` and `wishes-kid.html` (as Maya); `wishes.html` and `more.html` (as Sam); `signin.html` (signed out); `grownups.html` (Maya opening Settings); `idea.html` and `idea-new.html` (as Sam). Every page is rendered at 1280 and 390 px; kid Home also in dark.

## Two fixes to Chat first

- **Phone: a clear top edge.** The thread now starts under a pinned "Earlier messages" bar, with a hairline and a 24 px fade. A message that runs past the top fades out under the bar instead of being cut off bare under the privacy line. The bar is `position: sticky` inside the column-reverse scroller, so it needs no script.
- **Desktop: the whole short conversation.** On desktop the room grows with the thread instead of scrolling inside a fixed height, so Sam's question is in view above Vera's answer. The server still sends only the latest 30 messages, and `#latest` takes a long thread to the newest one. On the phone the room keeps the app-height scroller with the box pinned.

## Roles in the shell

`page()` now takes a role, and the shell follows it:

- **Admin (Sam):** as in stage 1. The Wishes nav item gets a "1 to decide" badge.
- **Kid (Maya):**
  - Her own nav: Home, Chat with Vera, My wishes, My to-dos, Plans, Ideas, What Vera knows.
  - Her own tab bar on the phone: Home, Chat, Wishes, To do, More.
  - No "Vera is answering" pill, no "Behind the scenes", and no cost, models, setup or gifts anywhere.
  - Her account card says "Not Maya? Sign out".
- **Signed out:** a plain page with the brand mark only (`.solo`).

## New components, added to the system and nowhere drawn one-off

- `.crumb`: the back link on an idea's pages.
- `.empty` (and `--center`): icon tile, a line that says what to do, the action. Used for Maya's empty to-dos, her new chat, Theo's empty wishes and the grown-ups page.
- `.locked`: a lock with "Ask a parent", where something isn't the kid's to do (moving a plan, changing a to-do for everyone).
- `.choices` / `.choice` (`--person`): radio or checkbox pills with avatars. **Where a choice must be made, none starts checked**: the parent's answer to a wish, who you are on the first-install sign-in, and who is writing while the family shares a password. The same component is the multi-select "Who's it for?" on the idea form.
- `.ranks` / `.rank` (`--decide`): a ranked wish with its number, the answer as a tag, the parent's words in a `.quote`, and up/down buttons. Each button is its own small POST form; the top and bottom ones are disabled. "Take it off my list" is a `.textbtn` form.
- `.form`, `.fieldset`, `.req` / `.opt`, `.form__row`, `.actions`, `.field__error`, `.field--error`: the form pattern. Labels sit above fields, hints sit below, and "(required)" / "(optional)" are written out. Errors are styled now and drawn in stage 3.
- `.pw`: a password field with a Show button. Paste and password managers are allowed (`autocomplete="current-password"`, nothing blocked). Show is the script-enhanced state, like "Share where I am": the script toggles the input type and `aria-pressed`. With scripting off, the button isn't rendered.
- `.kv`: key and value pairs (what Vera found about an idea).
- `.people` / `.person-tile`: the "pick who you are" grid on sign-in.
- `.composer--sample`: a composer shown inside a page, to explain the shared-password state.
- New icons in the sprite: `arrowup` and `arrowdown`.

## Page by page

- **Kid Home (Maya).**
  - The greeting's summary links her plan and her wishes.
  - Ask Vera with kid starters: "What can we do this weekend?" sends; "I wish for…" and "Can you help me with…" fill the box. The footer says the message goes to her own chat and that Sam and Alex can read it.
  - "Next up for you" (only plans for Maya or Everyone), with "Moving it? Ask a parent".
  - My wishes (ranked, answers as tags), My to-dos (only hers, plus Everyone's), "How was Pho Oregon?" and New ideas, with gifts left out.
  - No setup, spending or gift items. "Not looked up yet" reads "Vera hasn't checked this yet".
- **Kid Chat.** It opens on her own chat, "You and Vera". The note that Sam and Alex can read it shows on the conversation list, under the pills on the phone, and in the room header. The empty chat starts with three kid prompts. The composer says "Writing as Maya · Not Maya? Sign out" and "20 messages left today" (the family's daily cap for kids). The location box says "ask a grown‑up first".
- **Kid To do.**
  - She adds to-dos for herself only: no "Who" choice, and no reminder option, because kids never see why reminders can't go out yet.
  - "Yours" shows the "All done!" empty state.
  - "For everyone" lists Renew library cards. She can tick it off; changing it says "Ask a parent".
  - No red: a kid has no late items here, and kids' late items will use the amber "Was due" wording in stage 3.
- **Wishes, kid.** Add a wish; the list is "most wanted first", with up/down buttons and "Take it off my list". The parents' answers are in words: the tag plus their quote. The key explains the three answers, and a note says wishes aren't secret.
- **Wishes, parent.**
  - Maya's list, with each answer and a Change link.
  - The new wish ("A pet hamster", added today) opens a decision form: Yes / Thinking about it / Not this time, with no default, plus "A word for Maya (optional)" and Save answer.
  - Theo's empty state.
  - "Planning a surprise?" steers presents to gift ideas, which kids never see.
- **More (Sam, phone).** Three groups:
  - For the family: Ideas, Wishes with "1 to decide", What Vera knows.
  - Behind the scenes: Status (Working), Settings ("1 to check"), Family.
  - You: Sam, sign out.

  The rows are the Settings row component, and the badges match the nav.
- **Sign in (shared laptop).**
  - 1: pick who you are. These are links, so it works with no script; Maya is shown picked.
  - 2: "Hi Maya", her password with Show, Sign in, "Not Maya? Pick again", and who to ask if it's forgotten.
  - Below: the brand-new-install case. One family password, "Who are you?" with nobody picked, and a sample message box showing "Who's writing?" with no default, as every composer does in that state.
- **For grown-ups.** A kid who opens `/settings` gets a friendly page: "This part is for grown‑ups", why, "Go to my Home", "Ask Vera something", and "If something seems wrong, tell Sam or Alex". Nothing technical.
- **An idea's own page (Oaks Park roller rink).**
  - A back link, then the kind, the name, and tags for when and how far.
  - "On the calendar" (date tile, leave by, who it's for, and when Vera will ask how it went).
  - "What Vera found", which says honestly that it won't be refreshed while looking things up is off.
  - Notes, using the form pattern.
  - Who it's for, History, and "Finished with it?": Mark as been, and Delete with an undo.
- **Add an idea.** The form pattern in full:
  - Three fieldsets: What is it? / Who's it for? / Details (optional).
  - "Name (required)", and the Kind hint that gift ideas never show on the kids' pages.
  - Person pills, defaulting to Everyone, and "It's a surprise: hide it from Maya and Theo".
  - Save idea and Cancel.
  - The aside repeats the same "Looking things up is off" banner as Ideas, and offers "Quicker: tell Vera".

## Data added for stage 2 (the brief had none)

- **Maya's wishes.** To draw ranking and the answers, Maya now has four wishes:
  - Ice skates: Thinking about it (Alex)
  - A sketchbook and brush pens: Yes (Sam)
  - A sleepover with Ava: Not this time (Alex, with a reason)
  - A pet hamster: added today, not decided yet

  The parent Home's Wish lists card and the nav now say "4 wishes · 1 to decide". Theo still has none, which shows the empty state.
- **"20 messages left today"** is a sample of the family's daily message cap for kids.
- **Maya's to-dos.** *Superseded in stage 3:* a kid sees only to-dos she owns. See below.

## Still open

- The kid's More page (`more-kid.html`, linked from her tab bar) and Family are not drawn.
- All the states (stage 3): limit reached, Vera can't answer, pending and failed messages, flash with Undo, and form errors drawn on the form.
- Dark mode is checked on Home, Chat, To do and kid Home only.
- In full-page phone shots, the fixed tab bar still sits at the 844 px fold.

---

# Stage 3: kid corrections, states, dark mode, the standard

## Kid permissions, corrected to match the app

The app's rules: a kid sees **only to-dos she owns**, and **cannot change anything** (add, tick, edit, or rate a plan). She can read ideas and plans, chat within her daily message count, and keep and rank her own wish list.

- **`todo-kid.html`** is read-only.
  - No quick add, no ticks, no Edit, and no "For everyone" group.
  - Sample data: one to-do a parent set for her, "Pack your swim bag", due Thu 8 Oct, set by Alex.
  - The row is `.todo--ro`: an icon tile in place of the tick button, so nothing looks tappable.
  - A banner says kindly how it gets done: "Sam or Alex tick these off. When you've done one, tell Vera … and she'll let them know."
- **`home-kid.html`**:
  - The to-do card shows the same read-only row with the same line.
  - The "How was Pho Oregon?" faces are gone.
  - "Moving it? Ask a parent" stays.
- **`chat-kid.html`**: the starter "Remind me to pack my skates", which implied she could add a to-do, became "Can you help me with…".
- Wishes are unchanged: she may add, rank and take off her own.
- **A family decision, not a design one.** Whether a kid may tick her own to-dos or rate plans is up to the family. The app currently says no. If that changes, the kid row swaps `.todo--ro` for the normal `.todo`, and `.faces` returns to her Home. No new component is needed.

## States, on three sheets

- **`states.html` (Vera's states):**
  - The header pill in three tones (answering / resting until midnight / can't answer right now).
  - Limit reached: on Home's Ask card, in the chat box, and at the top of Status with a full meter.
  - Maya's own version, with no money talk: "You've sent all 20 of today's messages" and "Vera is resting until tomorrow".
  - Vera can't answer: the Status hero and health row, and the chat for Alex and for Maya, where kids get no company names.
  - A reply pending ("Vera is thinking", with the box closed and a 3-second meta refresh only in that state).
  - A message that failed ("Didn't reach Vera · Try again").
- **`states-actions.html`:**
  - The flash with Undo, for a to-do ticked off (the row stays, struck through) and for a wish answered.
  - Form errors on Add an idea and on the To do quick add: a summary first that links to each field, plus a message tied to each field with `aria-describedby` and `aria-invalid`. Values are kept, and the options fold is opened when it holds an error.
- **`states-content.html`:**
  - The first empty day for a new family.
  - A search with no results ("pizza" for Theo), with Clear and "Save as a thought".
  - A busy day: two events, then "+2 more"; on the phone, dots and a spoken label listing all four.
  - Long titles on an idea card, a to-do row, a calendar event (clamped to two lines) and a Settings row.

**Sample data on the sheets is invented to show each state:** times, the four plans on Sat 10 Oct, the long titles, and "pizza".

## System additions (all in `style.css` §5.26)

- Pill tones `--rest` and `--down`.
- `.todo--ro`, `.todo--done` and `.tick--done`.
- `.flash` and `.errors`.
- `.msg--pending` with typing dots (still under reduced motion), plus `.msg--failed`, `.msg--system` and `.msg__fail`.
- The closed composer: disabled textarea and Send, with a slim banner giving the reason.
- `.ev-more`, and a third calendar lane.
- Specimen layout for the sheets.

## Dark mode

All 20 pages are rendered dark at 1280 and 390 px (`shots/dark/`) and checked. Contrast is recomputed from the tokens for both themes: every text pair is 4.8:1 or better, and control edges 3.8:1 or better. The table is in STANDARD.md §7.

## STANDARD.md

It covers:

- the tokens, light and dark;
- every component with its variants and when to use it;
- the word table and the role table (admin, parent, kid);
- the phone rules and the states;
- the accessibility checks with the real numbers;
- engineer notes: Jinja macros, CSP, what works with scripting off, the four optional scripts, and the data the design depends on.

## Still open

- The kid's More page and the Family page are linked but not drawn.
- The ranking and decision forms show their resting state only; their own error states follow the same pattern as `states-actions.html`.
- In full-page phone shots, the fixed tab bar sits at the 844 px fold. That is where it is on a real phone.
