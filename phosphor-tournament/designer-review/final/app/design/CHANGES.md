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

---

# Stage 4: the polish pass (POLISH.md)

Four blind judges chose this design over the original, and the thirteen lenses' mean rose from 6.7 to 7.4. This pass works through POLISH.md in order. All 22 pages are rendered at 1280 and 390 px, light and dark (`shots/`, `shots/dark/`). Nothing scrolls sideways, every shot loaded its fonts, and no page has `style=""` or `<script>`.

## Must fix

1. **Person colours by slot, not by name.** `--sam…--theo`, `.av--sam`, `.msg--maya`, `.ev--theo` and `.d-maya` are gone.
   - There are now eight slots, `--p1…--p8`, each with `-soft`, `-ink` and `-mark`, set by `.p1…p8`, plus `.p0` for Everyone.
   - Avatars, bubbles (`.msg--person`), calendar events and dots all read `--p`, `--p-soft`, `--p-ink` and `--p-mark`.
   - Slots 1–4 are today's colours. Slots 5–8 are new: teal #0B6A84, indigo #5448B0, olive #59661A and magenta #8C3E86.
   - Every slot was checked: white letters are 5.4:1 or better; marks on the card are 5.3:1 or better in light and 7.8:1 or better in dark (in dark, `-mark` uses the lighter ink, which also fixes Maya's 2.8:1 dot). The server stores `person.slot`.
2. **The phone opens on what people came for.**
   - Phone Home: Ask Vera is one row (box and icon Send) with short starters ("Next weekend?", "Remind me…", "Save an idea…"), so the next plan's title and time sit above the tab bar.
   - Card order on the phone is Ask, Next up, To do, How did it go, Wishes, Ideas (`display: contents` plus order classes, no duplicated markup). Next up is capped to one plan plus "3 more plans this month". To do shows the late ones plus "All 4". Vera today is hidden on the phone (the pill and Status cover it). The page is about a quarter shorter.
   - To do on the phone: the list first, the quick add after it.
   - Ideas everywhere: search and "Filter and order" first, then the list; Quick idea and the looking-things-up note come after it.
3. **Ideas in the parent's tab bar.** Parents: Home, Chat, Ideas, Plans, To do. Kids: Home, Chat, Wishes, Plans, To do, so Plans is reachable.
   - Everything else moved into the **account menu behind the avatar**: `more.html` (Wishes, What Vera knows, Status, Settings, Family, Sign out) and a new `more-kid.html` (Ideas, What Vera knows, Sign out).
   - A dot on the avatar says something inside needs checking.
4. **Phone Plans.** The month header, then the Month/List switch, then the month at a glance, then Coming up, then How did it go.
5. **The calendar uses colour, and handles real months.**
   - Events take their slot colour: a 5 px bar and a 20 % tint. A plan for several people takes the first person's colour plus their avatars; Everyone stays neutral, as decided.
   - `.span2` is split in two: `.span-all` for page layouts, and `.len2…7` for an event's length.
   - A plan that crosses a week is split into `.ev--to` (›) and `.ev--from` (‹), with "continues" in its spoken label.
   - Today is a filled disc and a faint wash, never a ring.
   - Past plans are plain and solid, with a small face icon whose label is "Not rated yet". Rating stays in "How did it go?".
   - `states-content.html` now draws a real November: a busy Saturday (two plans, then "+2 more"), a five-day trip to Grandma's from Thu 19 to Mon 23 crossing the weekend and the week edge, and a two-day work trip.
6. **One meaning per signal.**
   - Yellow is only for the Ask card's Send, the logo dot, and "set this up / needs a look". The weekend tint, the warn-coloured "How did it go?" and the resting tone are gone.
   - Mint is only "all good / done". Info banners are a neutral card with a grey icon tile; "Off" is a grey fill with its own icon.
   - Dashed means only "not yet": Not looked up yet, No answer yet, Not done yet, Vera thinking. Card dividers, setup numbers, past events, the surprise tag and failed messages are solid.
   - "Needs a look" is a yellow fill with a "!". "Could be better" and "Not connected" are an outline with a hollow amber dot.
   - "Set this up" appears once per page. On Home it's the setup card (the phone strip goes to Settings' setup banner). Plans and Ideas have one quiet `.note` line. Settings has one setup banner, so the side "Setup" card is gone. Telegram left Home's "Vera today".
   - Sidebar badges are loud only for **3 late** (red) and **1 to decide** (ink outline). "2 to rate" and "1 to check" are quiet grey numbers.
7. **Numbers.**
   - "Fraunces Figures" is out of the body stack, and `unicode-range` limits it to digits and money punctuation. Running text, digits and punctuation included, is Atkinson.
   - Serif tabular figures stay only where numbers stand alone or line up: date tiles, money, the 30-day figures, calendar days, wish ranks, setup numbers, the meter scale and segment counts.
   - I checked Atkinson Hyperlegible Next for an unslashed zero. It has none (its only zero variant, `zero.tf`, is the tabular one), so I kept Atkinson Hyperlegible and its slashed zero in running times as a legibility feature.
8. **Accessibility.**
   - `--tabbar-total` adds the safe-area inset to the tab bar's height, the body's padding and the chat height.
   - `scroll-padding-bottom` keeps the focused control clear of the tab bar, and the chat scroller has `scroll-padding-top`.
   - On screens under 560 px tall, the chat falls back to normal page scroll.
   - Selected segments are filled ink with paper text (13.9:1). The current tab has a 3 px green top bar. The current conversation has the nav's inset bar.
   - Dark today is `--today-bg` #7CC7AE (8.0:1 on the card). Slot marks are fixed as in item 1.
   - Kid targets are 44 px: "Take it off my list", the starters, the small buttons on the phone, setup links, Change links and the tab badge text at 13 px.
   - Hints moved out of `<label>` into `aria-describedby`. The kid's wish box and the to-do quick add have visible labels.
9. **A kid's read-only to-do.**
   - Its lead is the setter's avatar (Alex), never a box or ring, with a dashed "Not done yet" and "Tell Vera I did it", a link that fills her chat box.
   - Her own things lead her phone Home: Ask, My wishes, My to-dos, then Next up and Ideas.
   - The gentle message warning is drawn on `states.html`: "5 messages left today" as an outline tag. Her Ask card says how many she has left.
10. **Words.**
    - The pill is **"Vera is ready"** ("Ready" on the phone). "Vera is writing back" is used while she answers.
    - Wish answers are one set for kids and parents: Yes! · Thinking about it · Not this time · **No answer yet**.
    - "Mark as been" became **"We went"**, with "Not for us: remove it".
    - "Save a thought" became **Quick idea / Save idea**, and "Save "pizza" as an idea".
    - **"Add a backup key"** is used everywhere except the key table.
    - Sign-in: "Parent · admin"; the heading is "For now, everyone shares one family password"; the kids' tiles have no role line.
    - Settings rows: "OpenAI · no backup if it's down", "Vera's standard voice", "Changes to these settings: none yet". The Plans note says "These plans are only in FamilyDB for now". Home's lede says "are late".
    - The Status disclosure is "Technical details: which AI answers each job", and the cache line is dropped.
    - Spelling stays British English, the app's own (colour, kilometres, cancelled, tick off).
11. **Forms and controls.**
    - The quick add shows **Who's it for?** as visible person pills with nothing picked (required). Its error, "Pick who it's for. Pick Everyone if anyone can do it.", is drawn on `states-actions.html`.
    - Ideas submits one sort control, inside "Filter and order". "Show ideas" comes after the filters in the source.
    - A starter that sends is filled, with the send icon. One that fills the box is an outline with a pen and ends in "…".
    - "Share where I am" is gone from the kid's pages.
    - `white-space: nowrap` is removed from buttons, tags and the locked label. The surprise tag shows "hidden from Maya" at every width.
    - Composer boxes have no resize grip.
    - "Not you? Sign out" became "Not Sam? Switch", which goes to the person picker and back to Chat.
12. **Drawn what was missing.**
    - `todo-edit.html`: the form pattern for an existing thing, with title, notes, Who pills (Alex picked), Due with the late hint and quick dates, Reminder ("needs Telegram"), Save/Cancel, Tick it off, Cancel this to-do and History. Every "Edit" link goes to it.
    - Vera's longest message is in the family chat: Thursday's **weekend suggestions**, with three ideas, each with when, drive, a price and who, and a "Plan it" form. Alex's reply puts the roller rink on Sunday, and Vera's receipt follows.

## Left alone, as POLISH.md asks

- **Vera stays undrawn.** The style lens asked again for a character and for spot drawings; declined, as decided.
- **The chat's refresh while a reply is pending is kept.** The pending bubble now has a visible "Check for her answer" link. The accessibility review's concern (2.2.1 / 3.2.5) and a back-off schedule are recorded in STANDARD.md §8.

## Declined or decided differently

- **US English** (copy lens): declined. POLISH.md says the app is written in British English, so the UI matches it.
- **A fixed-height desktop chat room** (engineer): declined. Earlier feedback asked for the whole short conversation to show on desktop, so the room grows with the latest 30 messages. The phone keeps the app-height scroller.
- **Colouring Everyone events** (style lens: Vera's green): declined. Green is Vera, and POLISH.md keeps Everyone neutral. Multi-person plans now take their first person's colour, so most plans have colour.
- **"I did it" as a form that marks the to-do** (kid, parent, usability lenses): declined, because kids can't change anything. "Tell Vera I did it" fills her chat box instead, which uses her messages as the rules allow.
- **Removing the "Reading this list" key** (generalist, interaction): kept, because the protect list names it. It now explains tags that carry their own icons.
- **A 30-day spending sparkline** (generalist, skeptic, usability): not drawn. It needs daily data the brief doesn't give, and drawing it would mean inventing numbers. The STANDARD notes how to draw it CSP-safely (SVG `<rect height>`).

## For the family to decide (not designed in)

- Whether kids may tick their own to-dos or rate how a plan went.
- Whether each parent gets a private chat with Vera for planning surprises.
- Whether a kid may share where they are with a message. It's hidden on kid pages until the family allows it.

## Sample data added in this pass

- **Vera's weekend suggestions**, with times, a weather line, "free to get in", "about $15 each" and "skates to hire", and Alex's reply that books the roller rink.
- The **November month**: Alex's book club, Theo's soccer, the farmers market, Maya's recital, the Spokane trip and Sam's work trip.
- **Maya's "Can hamsters eat carrots?" chat** on the states sheet.
- The to-do edit page's **"added by Sam on Fri 25 Sep"**.

## Still open

- The Family page and What Vera knows are linked but not drawn.
- A 320 px pass was not rendered; the segments now wrap instead of scrolling, which was the known risk.
- Theo's own pages are not drawn. They follow Maya's with his slot.

---

# Stage 5: the brand (BRAND.md)

The family said the final looks generic. This stage brings back what FamilyDB already owned (the smiling monitor and Vera's screen) and anchors the type back to A1, the version they chose. The brand is a sprinkle: the layout, components, roles, phone order and every check from stages 1–4 are unchanged. Order of work, as asked: brand elements first, then type, last and least.

New pages: `type.html` (the type specimen) and `404.html` (the missing page). New files: `brand/` (icons), `type/` (six crops from `reference-a1/` shots), `fonts/fraunces-soft-600.woff2`, `fonts/jetbrains-mono-400.woff2`. Removed: `fonts/fraunces-600.woff2` (replaced by the soft cut). All 24 pages rendered at 1280 and 390 px, light and dark: 96 shots, fonts loaded on all, nothing wider than the screen, no `style=""` or `<script>`.

## Kept

1. **The mark replaces the house** in the sidebar, the phone bar, sign-in, Settings' colour key, the panes, and as the favicon and home-screen icon (`brand/`: SVG, 16, 32, 180, 512). Redrawn from `brand-ref/` on a 24 grid: one 2 px round stroke, a monitor with a stand, two eyes and a smile, phosphor #6DFF9C on a charcoal #0E1312 square. The house stays only as Everyone's avatar, where it means the family.
2. **The wordmark with a lit cursor.** "FamilyDB" in Fraunces 600, soft, and a green block that blinks slowly like a waiting terminal. Ink on paper with a darker green cursor (#1B9A55, so it holds 3:1 on cream); cream and phosphor at night.
3. **Vera's screen replaces the "V" circle** everywhere she appears: the Ask card, every message of hers, the pending bubble, Home's Vera row, Status' Vera row, Settings' key, the kid's empty chat, the states sheets. Glass with blurred glyphs (one in five bright), faint scanlines, `aria-hidden`. Three states: ready (still), answering (glyphs fall a row at a time; the only motion), can't answer (the glass goes dark). No motion under reduced motion.
4. **Her voice in a mono** (JetBrains Mono 400, 14 px, 21 KB): her message times, the line under a receipt, the status pill, pane lines and the instrument. Her messages themselves stay Atkinson, like the family's.
5. **The status pill is glass.** "Vera is ready" in phosphor mono with a breathing dot. Resting: quiet ink and a hollow dot. Down: alert paper in plain Atkinson bold, because an outage is a sentence for the family, not a machine line.
6. **One instrument, on Ideas:** a glass pane plotting the ten looked-up ideas by drive time (square-root scale, rings at 30 min, 1, 2 and 3 h) and direction from home. The SVG is hidden from assistive tech; the numbered list beside it names every dot with its time and direction. On the phone it comes after the list, so the first screen is still search and ideas.
7. **Brand moments:** sign-in (a pane: the mark, "FamilyDB · awake, Saturday 3 October", then who's using it), a family's first empty day ("FamilyDB is set up and awake"), the grown-ups page a kid lands on (the mark alone, glowing; the words stay on paper), and a new missing page, `404.html`.
8. **Live things glow:** the pill's dot, the wordmark's cursor and the caret in Vera's box (`caret-color`), the bright glyphs, and Vera's bubble at night.
9. **Dark mode is phosphor at night.** Warm brown became charcoal glass (#0C100F page, #161D1B card), cream ink, Vera's green became phosphor with a soft glow, amber for "needs a look", coral for late, and people's colours lightened on tinted charcoal. Every pair in STANDARD §7 was recomputed and all pass (lowest text pair 6.5:1, `--ink-3` on a field).
10. **A deeper, glassier green by day for the Ask card** (#1E5C4F → #12382F). Its text goes from 7.8 to 12.9:1, and it sits with the phosphor screen in its corner.
11. **The family's actions leave Vera's green at night.** New tokens `--link`, `--primary`, `--primary-2`, `--on-primary`: identical to before by day, cream at night. In my first dark pass, "Add an idea", "Save changes" and every link were phosphor, which put Vera's colour on the family's own things.

## Typography: every change from A1, and why

Compared rule by rule with `reference-a1/style.css` and page by page with its shots; `type.html` shows the scale and six real lines, A1 above and now below. Since A1 the type had drifted (h1 40, h2 24, h3 20, lede 19, card titles at h3 size, Next up's title 24, date tiles 36/22, money 32, to-do titles 17, group heads 17 sentence case, page eyebrow in capitals, meta line 1.4). **All of that is reverted to A1:** h1 42 (32 phone), h2 23, h3 19, lede 18 (16 phone), card titles at h2 size, Next up 26, Ask Vera 22, the hero banner 26, date tiles 34/28/21, money 30, figures 32, to-do titles 18 (17 on Home), group heads 15 capitals, the eyebrow 15 bold in sentence case, calendar weekday heads in small capitals, meta line 1.5, date-tile capitals at +0.08em.

What still differs from A1, and why each is worth the change in voice:

1. **Numbers that stand alone use Fraunces Figures** (date tiles, money, figures, counts). *Named problem: slashed zeros.* A1 set them in Fraunces, but stage 1's Atkinson stack slashed them. Figures is Fraunces' own digits made tabular, so they look like A1 and line up. Running text keeps Atkinson's slashed zero.
2. **13 px is the smallest step** (A1 used 11–12 px for date-tile and calendar capitals). *Named problem: the 14 px floor*, with 13 px kept for capitals only.
3. **Tags have a line height of 1.15** (A1: 1). *Named problem: phone wrapping.* Tags may wrap since the polish pass, and at 1 their two lines would touch.
4. **Times read "1 pm", not "13:00".** A copy change from the final, not a type change; listed because it shows in the side-by-side.
5. **The one Fraunces choice: `h1` and the wordmark use the softness axis at 100.** The same letters with rounder terminals, warmer and more its own at 42 px, invisible at body sizes. No other heading uses it, no alternates are on. The font file is the variable Fraunces subset with opsz and SOFT, weight fixed at 600 (58 KB).
6. **One new face, the mono**, for Vera's machine lines only (above).

## Tried and dropped

- **The mark as drawn at 16 px from the 32 px artwork:** the eyes and smile blurred into a "U". Replaced by a hand-pixelled `mark-16.svg` with crisp edges.
- **Vera's screen with no rim on the Ask card:** charcoal on dark green disappeared. It now has a 40 % phosphor rim there. At night all screens looked like holes in the page, so they get a faint lit rim and inner glow (`--vs-lit`).
- **Glyphs at 0.35 px blur:** readable at 2x ("1a=14"). Now 0.55 px, which is past reading but still glyph-like.
- **A pane of glass for the sliders tile on the grown-ups page:** decoration only, so it became the mark. A small pane around the mark was tried next and dropped: glass inside glass read as a double frame. The mark alone is the moment.
- **Mono for the whole receipt:** the title went mono too (a selector caught both spans). Only the line under the title is mono; the plan's name is the family's, so it stays Atkinson.
- **An instrument label "1–6" for the near cluster:** wrong, because idea 1 (the pumpkin patch) is north-west. It is now "1" and "2–6".
- **Considered, not done:** Vera's whole messages in mono (the family reads them; they stay Atkinson, as BRAND.md says), a pixel or display face for headings (ruled out), a second instrument (Plans by distance; one per page and one in the app is enough), scanlines on cards (only inside panes and screens), green "today" washing the family's plans (today's tile header and disc stay green as the live thing; the plans in it keep the person's colour).

## Fixed in passing (found while looking at every shot)

- The November specimen skipped 30 Nov, so 1 Dec sat under Monday. The grid now runs to Mon 30 Nov.
- The phone avatar link underlined its initial; the phone pill sat 6 px above the mark and avatar.
- The resting Ask card's placeholder was 1.5:1 on the deeper green; it now uses `--ask-ink-2`.
- A failed reply from Vera had a red rim plus her green glow at night. The glow is off when she can't answer, and her screen goes dark.
- The 404 pane had a divider pressed against its text; panes have no divider.
- Drive times and receipt times broke between the number and its unit ("18 / min", "2 / pm"); they're held together with no-break spaces.

## Still open

- The full-page phone shots show the fixed tab bar at the 844 px fold, over content, as in stage 4. On a real phone it's at the bottom of the screen.
- The instrument shows the ten ideas Vera has looked up; the two not looked up are named under it only by their absence. The list says "Drive times Vera looked up".

---

# Stage 6: keep the brand, lose its costs (BRAND-2.md)

Four blind judges found the branded version clearly stronger in identity, but three would have built the plain one because the brand cost something in use. This stage keeps every brand element (the mark, the wordmark, the pill, the radar, Settings' key, the four brand moments) and removes those costs, in BRAND-2's order. All 24 pages are rendered at 1280 and 390 px, light and dark (96 shots), looked at, fixed and rendered again.

## 1. Vera's sign reads as her at 24–32 px

- **Was:** a glass square of 5 × 12 tiny glyphs, blurred, under scanlines. Judges called it "a dark smudge" and "a broken thumbnail".
- **Now:** inline SVG, crisp, built from four parts:
  - a rounded square (radius ¼ of the size, so never mistaken for a round person avatar);
  - a lit phosphor rim;
  - one to three short, rounded lines of light, the newest brightest;
  - her signature: a lit prompt `>▮` in the bottom-left corner, the same at every size.
- **Sizes:** 24 px has one line, 32 px two, 40 px three, and a new 56 px for the kid's empty chat. Small sizes have fewer lines, not smaller ones.
- **Halo:** a 3 px halo, Kitchen Table green by day and phosphor at night, keeps it a lit screen on both.
- **Busy:** the lines light one after another and the cursor blinks, only while a reply is on its way.
- **Off:** the light goes out. Rim, lines and prompt turn control-edge grey, the cursor goes hollow, and the halo goes. A first try in the glass-edge colour vanished on the dark card.
- **Checked at real size** in the phone shots, light and dark.

## 2. Mono only on the glass

- Vera's message times and the line under a receipt are back in Atkinson.
- The radar list's numbers are Atkinson bold.
- The mono stays only on dark glass: the status pill, pane lines, and the radar's ring labels and dot numbers.
- On the phone the receipt drops its decorative kind tile, so "Oaks Park roller rink" gets the width. It no longer breaks into three ragged lines.

## 3. Dark mode keeps its hierarchy

- **The Ask card is deep-green glass at night** (#0F2A22, text 12.5:1), with the page's brightest edge (a 1.5 px green rim at 4.6:1 against the page, plus a faint inner glow).
- **Its box now has a real edge** (`--ask-edge`, 4.4:1). Before, it was 1.2:1, a WCAG 1.4.11 failure.
- **The family's primary buttons are Kitchen Table green day and night** (night #2D7462, white text 5.5:1). Links are a lighter green (#8BD3B4), never phosphor. Stage 5's cream buttons are gone.
- **No glow on Vera's bubbles.** Glow stays on the pill, the panes and her screen.

## 4. The radar earns its place

- **A piecewise scale** gives the first half hour more than half the radius, with rings at 15 min, 30 min, 1 h, 2 h and 3 h.
- **The near cluster is spread out.** Ideas sharing a direction are fanned a few degrees apart, and every dot carries its own number; the "2–6" lump is gone. The caption says the near ones are spread.
- **Ring labels are legible:** 10 px drawn at about 1.45×, set along the north axis.
- **Placement:**
  - Desktop: the cards now start right under the filters, and the radar sits after the first row of three, between two lists ("All ideas, continued").
  - Phone: it stays after the list, which reads as one box.

## 5. The calendar says who without colour alone

- **The macro derives the colour from the people.** One person gets their colour; several people or Everyone get neutral grey. No template picks a colour.
- **Every event shows its people:** small avatars, or the house for Everyone. Oaks Park, for Maya and Theo, is now grey with M and T, no longer Maya's pink.
- **The phone month** shows up to three 14 px markers per day: an initial in the person's colour, the house for Everyone, or a hollow ring for a past plan.
- **The November sample** gained its missing markers (book club, recital, the trip, Sam's work trip).
- **Plans has a one-line key** under the calendar.
- **Outside-month labels** ("28 Sep") hide their month on the phone with the clip pattern, so they no longer wrap.

## 6. Money and clock times in one figure style

- Every amount and every clock time, wherever it appears, is in Fraunces Figures, the face of the big money figures.
  - A filter on the rendered page wraps them in `.fig`, so no template has to remember.
  - "$0.00 of your $2.00" now has one kind of zero, and "7:48 pm" matches "$2.00".
- In sentences they use a second, proportional cut of the same digits (`fonts/fraunces-text-figures-*.woff2`, 2.5 KB each). The first render used the tabular cut, which left "1 pm" with a gap like a missing digit.
- Ranges like "6–9 pm" wrap both ends. The first filter only caught the 9.
- Other numbers in sentences keep Atkinson's slashed zero.
- `type.html` has a new section showing the choice.
- **Tried and not chosen:** an Atkinson zero with its slash removed.
  - Atkinson's slash is only the gap between two counters, so the shape is easy to make, and it reads as Atkinson.
  - But it would leave a big Fraunces "$0.00" beside a small Atkinson "$2.00": two figure styles in one line.

## 7. Accessibility

- **Names restored:** on the phone, the starters' long labels and the Edit links' "Edit" were `display:none` beside `aria-hidden` stand-ins, so they had no names. They are now hidden with the `.sr` clip pattern, and STANDARD makes this a rule.
- **Focus on glass:** the ring is phosphor (14.7:1) on panes, the radar and the pill. Before, it was 1.2:1 on the 404 pane.
- **No endless blinking:** the wordmark cursor blinks twice and stays lit, and the pill's dot breathes once (both under 5 s). Reduced motion still stops everything.
- **Sizes in rem:** every type size in px is now rem (30 declarations), and the top and tab bars use `min-height`.
- **Narrow screens:** the Status figures stack at 400 px and below.
- **Firmer edges:** icon buttons use `--edge` (3.8:1). A disabled arrow is `--ink-3` with a dashed edge.
- **Forced colours:** the phone month markers get a `CanvasText` border.
- **Page language** is `en-GB`, matching the standard's British spelling (it said `en-US`).

## 8. Small things

- **Idea titles** are Atkinson 700 at 17 px on every page (they were Fraunces on the Ideas cards).
- **Maya's slot** is raspberry #A83C80. It sits further from "late" red (ΔE 58, was 40) and from Everyone's grey under protanopia (29, was 8).
  - The cost: it sits closer to Alex's purple under protanopia, which the initials now cover.
- **Slot 8** is cocoa #6F4E37 (was a magenta indistinguishable from slot 2).
- **The surprise tag** in narrow tiles (Home's idea tiles and compact to-dos) says "Surprise"; "hidden from Maya" stays in its spoken name.
- **The kid's empty chat** has one filled action (Send). The starters are outlines everywhere outside the Ask card.
- **The phone "Ready" pill** is centred with the mark, and the avatar letter in the phone bar is no longer underlined.
- **The To do "Add" button** is sized to its label.

## Found while looking at every shot, and fixed

- **Settings rows** broke "Up to / $2.00 / a day" onto three lines. A descendant rule (`.srow__text span`) caught the new figure spans; it is now a child rule.
- **Two text buttons were phosphor at night** ("Take it off my list", "Cancel this to-do"). They now use `--link`.
- **The radar's W** sat on dot 10. The plot has more margin now, and the ring labels alternate sides of the axis.
- **The phone calendar key** broke between a marker and its words; each pair now holds together.
- **"10 am"** broke inside a crowded day cell; event times don't wrap.
- **The idea page's history row** had a 24 px Vera sign beside 40 px tiles; it is 40 px now.
- **The resting Ask box** at night had no edge; it uses `--ask-edge`.
- **The November specimen:** Sam's work trip was in the second lane with the first free, Wed 14 Oct had no phone marker, and the caption still said "dots in the plans' colours".
- **The account rows** said "signed in on this phone" on a computer and the reverse; they say "signed in here".

## Declined, and why

- **Dropping the meta refresh** while a reply is pending (access lens, not in BRAND-2's list). It stays as STANDARD §8 records, with the server back-off and the visible "Check for her answer" link. It is the family's chosen behaviour with scripting off, and the opt-in alternative is noted there for the engineer.
- **A focus specimen sheet, spot illustrations for happy moments, a print style:** these are suggestions from the reviews, not BRAND-2 items, and are left for a later pass.
- **The 1000–1180 px band on Ideas:** the cards are two across there, so the radar follows a row and a half. Accepted rather than adding a third breakpoint.
- **The Ask card's Send stays sun yellow** in both themes. The style lens asked to protect it, and it is the Ask card's one action, not a family primary button. Selected segments and chips stay inverted (ink fill, cream at night), as the system defines them.
- **Earlier-stage layout seams the reviewers saw again, left for a later pass:**
  - Status: the "Last 30 days" tiles don't align when a label wraps, and "Technical details" breaks up on the phone.
  - Edit a to-do: the history rows don't line up.
  - The states sheets: the quick-add error sits beside the chips on desktop; the Undo banners are loose on the phone.
  - Ideas: the phone Quick idea placeholder is cut short.
  - The kid's to-do row is loose.
  - Word spacing in small Fraunces headings ("Add a to-do") is tight.

---

# Stage 7: the last touches (LAST.md)

All four new judges chose this version (8, 7.5, 8, 7.5 against 7 each). This stage does only the small things they named, and nothing else. All 24 pages are rendered at 1280 and 390 px, light and dark (96 shots), looked at, fixed and rendered again.

1. **The surprise chip always says who it's hidden from.**
   - Stage 6 shortened it to a bare "Surprise" in narrow tiles, which hid the one fact a parent needs to trust.
   - In a narrow tile (Home's idea tiles and Home's compact to-dos) it now shows the lock and **"Hidden from Maya"**, with "(a surprise)" in its spoken name.
   - Everywhere else it reads **"Surprise · hidden from Maya"**, as before.
2. **The radar has its own place.**
   - It no longer splits the idea cards. The cards are one grid again, and the radar is a band after them.
   - **Desktop:** the band is always shown.
   - **Phone:** it is folded behind "Show the map" before Quick idea, so the phone Ideas page is about a quarter shorter (4,286 px tall in the 2x shot, down from 5,820).
   - **No numbered list:** the cards are the list.
   - **Names on the dots:** each dot carries the idea's short name ("Pumpkin patch", "Oaks Park"), the first words of its card's title, so a kid can match it.
   - **Atkinson labels:** names are 15 px (14 on the phone), and ring, compass and "Home" labels are 13 px Atkinson.
   - **Drawn twice from one data table:** a wide plot and a narrow one, each with label positions set per idea. Nothing sits on a compass letter ("W" no longer covers Cannon Beach, and "N" moved off "3 h").
   - **Scale:** the first half hour now gets 70 % of the radius, so the five near ideas spread out.
   - **The fold:** both this and To do's fold (item 4) use one native `<details>`. On the desktop it is always open: the summary is hidden and its `::details-content` is shown. No script.
3. **The status pill is quiet when all is well.**
   - "Vera is ready" is a soft-green pill in Atkinson 700 with a still dot.
   - The dark glass pill with the mono voice appears only when there is something to notice:
     - "Vera is writing back" (new; its dot breathes until the reply lands);
     - "Vera is resting until midnight";
     - "Vera can't answer right now", now on glass in coral (`--glass-alert`, 8.2:1).
   - The states sheet shows all four.
4. **To do's Add is a full, obvious button again.**
   - **Desktop:** the card is the box, then who and when, then **Add as a full-width bar**.
   - **Phone:** a one-row "Add a to-do" (box and Add) is at the top of the list, with "Who, when, reminder · Nobody picked yet · No date · No reminder" folded beneath it.
   - **Still nobody by default.** The form is `novalidate`; the server checks who and sends the form back with the fold open and the error in it (drawn on the states sheet).
5. **Small craft.**
   - Spill-over days on the phone calendar show their month in small capitals beneath the number ("28" over "SEP", "1" over "NOV"). In stage 6 the month was only spoken.
   - "Add a to-do" and other small Fraunces headings get their spacing back (letter-spacing 0, a little word spacing), so it no longer reads "Adda to-do".
   - The Status cost figures stay on one row on phones from 360 px and stack only below that.

STANDARD.md is updated for the pill, the radar, the Add form, the surprise chip's words, the phone calendar and the Status figures. type.html says where the mono now goes.

## Found while looking at every shot, and fixed

- **Narrow chip:** "Hidden from Theo" wrapped in Home's Lego tile; it is now one line, sized to its words.
- **Spill-over days:**
  - On the phone, the extra height for the month label also moved the other spill-over days; only a day that carries a month changes now.
  - Phone day cells align to the top, so every row's numbers line up.
  - On the desktop, "1 Nov" reads inline like "28 Sep".
- **Map compass:** "N" sat on the outer ring and "S", "W" and "E" sat off their axes. All four now sit just outside the ring, on their axes.
- **Status figures:** they stay on one row, and a wrapped label ("Questions answered") no longer pushes its figure below the others; the values share a line.
- **The rebuilt To do form's error state:**
  - The errored box had lost its red edge.
  - The who-error sat inside the chip row. It now sits on its own line above the chips, as on every other form.
- **The states sheet** labelled four pills "all three states"; it says "calm, then the three that need noticing".

## Left alone (LAST.md: change nothing else)

These were noted again by the reviewers but are not on LAST.md's list:
- the phone Technical details row on Status;
- the cut-off Quick idea placeholder;
- hyphenated directions breaking at the hyphen;
- the edit form's quick-date chips sitting under Reminder on the phone;
- the kid's narrower My wishes card;
- the loose Undo banners on the phone;
- the narrow cards in the first-day specimen.

---

# Stage 8: the whole app, part 1 (STAGE8.md)

The family chose Kitchen Table as the design. Its look stays exactly as stage 7 left it (type, colour, brand, Vera's sign, every phosphor touch at the same strength, none added). This stage makes it cover the real app's everyday pages, from `app-reference/` (templates, `views.py` wording, `routes.py`, `roles.py`, `auth.py`, `family.py`, `status.py`, `chat.py`). Every page is rendered at 1280 and 390 px, light and dark.

## The family's three notes

1. **No starter buttons on Ask Vera.** They're gone from Home, the kid's Home, Chat and the states sheets. The box, Send and "Goes to the family chat as Sam" stay. The kid's empty chat now rests on the app's own line: "Nothing said here yet." under "Just you and Vera. Tell her what you wish for, or ask about the plans."
2. **The greeting earns its space.**
   - "Good morning, Sam · Saturday 3 October" is now one small line, still in the soft Fraunces.
   - The useful line under it ("Roller rink tomorrow, and three to-dos are late", with its links) is the large one.
   - The Ask card's label is the page's h1, as in the real app: "What's on your mind?", with Vera's screen and "Vera" beside it.
   - On the desktop, Ask Vera, Next up and the start of To do are on the first screen. To do moved to the top of the right-hand column (now a little wider), and the wish lists card moved left to keep the columns even.
   - On the phone, the first screen is Ask Vera and the next plan, for the kid too: her Next up now comes right after Ask (it used to come after her wishes and to-dos).
3. **The phosphor echo stays as it was.** Nothing green was added. The only new mono is a tool's JSON on the admin's history page, which sits on glass, where the mono already lives.

## New pages

- **`plans-list.html`, the real `/plans`.**
  - "Coming up" for the next 90 days, grouped by month. Each plan shows its date tile, title (linked to its idea when it has one), when, how far off ("tomorrow", "in 2 weeks"), status ("tentative"), where, who and notes.
  - A "Recently" card.
  - The calendar source note: "Google Calendar isn't connected, so these are the plans Vera made."
  - "Put something on the calendar" folds beside the list. With Google Calendar not connected, as in this sample family, it says so instead of showing a form, as the real page does. The connected form, and "Move it" / "Cancel it" ("This takes it off the family calendar for everyone"), are drawn as components (`mini-fold`) for when it is connected.
- **`restaurants.html`, the real `/restaurants`.** "2 places the family has talked about." Each place card has its cost, today's hours, summary, where, drive, who, rating, and "Details may be out of date" when stale. Links: "Everything we know", "Their site", "Map".
- **`memory.html`, "What Vera knows" (`/memory`).**
  - Grouped by who a fact is about. Each fact shows "Must" (a rule), "A guess" (she inferred it) and "Until …" tags, plus its kind and where it came from in the family's own words ("Alex, Sun 20 Sep: “Maya's gone vegetarian…”").
  - Forget on each line.
  - "Tell Vera something to remember" with About, Kind, Until and the must-or-never box.
  - A "Forgotten" fold.
  - Grown-ups only.
- **`you.html`, Your password**: change it, with the current password, the real tips, and "signs you out on every other phone and computer".
- **`you-first.html`, a first sign-in with a starting password**: "Choose your own password", Maya's kid shell, a small brand pane ("first sign-in · Maya").
- **`password-shown.html`**: Maya's page just after the admin made her a starting password. It's shown once, in a dashed, selectable box, with the real "Shown this once: send it to Maya now…".
- **`family.html`, the real `/family`.** Everyone with role, age, how Vera reaches them, today's messages for a kid, and "Signs in" / "Starting password". Then "Add somebody" (name, role, Telegram id) and what each role does, in `ROLE_WORDS`.
- **`member.html`, the real `member_form.html`**, for Maya:
  - Name, role, birthday ("11 today. Only the age goes to Vera, never the date."), male or female (kids only), Telegram id, on the list.
  - Signing in: make a new starting password, take her password away.
  - Linking her Telegram (not connected yet).
  - "Take Maya off the list for good" folded in red, behind an "I'm sure" box.
- **`idea-edit.html`, the real `idea_form.html` in edit mode.**
  - Title, Kind (free text with suggestions), Status, Description.
  - "Everything else" open: where, link, on from, starting at, until, who it's for, tags, indoor or out, weather, cost, shortest/longest, book ahead, seasons, needs booking.
  - Save changes.
- **`activity.html`, one message's history (`/status/activity/<key>`), admin only.**
  - What was asked and what Vera said.
  - The model calls as a table that scrolls sideways inside its box.
  - The tools she used, each folding open to what it was given and answered, as machine text on glass.
  - What the lookup found, and the pages it read.
- **`403.html`**: the real refusal in a brand pane, "403 · signed in Maya · role kid", "For a parent", "This page is for the grown-ups. Ask a parent if you need it.", Back to the start.
- **`wishes-maya.html`, one kid's wishes for a parent (`/wishes?who=`)**, which the mockups lacked: add a wish for Maya, her lists with move and answer controls, and Flagged with Yes / Not this time.

## Existing pages checked against the real templates

- **Every page:**
  - The real footer: "A little less planning. A little more together." and "FamilyDB © 2026 by Andrew Tate. Version v1.0. All rights reserved." (kids and signed-out pages without the version).
  - "Your password" in the account corner and menu, and Sign out as a POST button.
- **Kids:**
  - No "What Vera knows" (the real app keeps memory for grown-ups).
  - Only their own chat (the "Family" conversation is gone from Maya's chat).
- **Sign in:** rebuilt to the real behaviour.
  - Your name and your password are typed; the family is never listed. A wrong name gets the same answer as a wrong password, and the page shows that error.
  - The real forgot hint: "An admin can make you a new starting password on the Family page" (it used to say "Ask Sam or Alex", and Alex isn't an admin).
  - The shared-password case keeps a "From" picker on each form.
- **Home:**
  - The real placeholder ("Plans for the weekend, an idea to keep, a reminder, the calendar…").
  - Vera's last line from the past day with "Continue with Vera".
  - "Something to eat · 2 restaurants to try" and "Add an idea" under Ideas.
  - The setup card's "Each one is a short page that says what to do" and "All the setup steps".
  - Next up lost "Leave by" and "Move it": neither is on the real Home, and a plan only moves with Google Calendar.
- **Chat:**
  - The real ledes ("Weekends, ideas, to-dos and the calendar: anything you'd ask in Telegram works here too" / "Just you and Vera…").
  - "The kids' conversations" with "Each kid talks to Vera on her own. You can read along."
  - Placeholder "Message Vera".
  - No "Not Sam? Switch" (there's no such thing).
  - The pending bubble says the real "Thinking about the last message. The answer will show here when it arrives."
- **Ideas:**
  - The real lede.
  - The real status filter ("Any but dropped", An idea, Planned, Done, Dropped).
  - No sort; the button is "Filter".
  - "Restaurants" links to the new page.
  - The quick idea became the real "Save a thought for later" fold, near the top, posting to the chat ("Organise in the chat").
- **An idea:**
  - Status tag, "#12", "Suggested by Maya · added Sun 20 Sep", the description, and an "Original thought" fold.
  - The place panel: what it is, address and Map, getting there, phone, website, prices, opening hours, and where they came from.
  - At a glance: for, indoor or out, weather, seasons, how long, cost, booking, so far, link.
  - The lookup row with "Look it up again" and "How it was looked up".
  - "Record how it went" (when, out of ten, again?, who, notes; saving marks it done).
  - Edit and "Drop it".
  - Gone: the invented Notes, History, "Vera asks at 10 am" and "remove it, undo for a minute".
- **New idea:** the real fields, through the same `idea_fields` as editing.
  - Title and Kind are required.
  - Who it's for is the real free-text field.
  - The surprise checkbox is gone (no such field).
  - "Add it", and what happens after (it opens with "Saved #13…"; a duplicate opens the existing one).
- **To do:**
  - The real lede, and the real note: "Times use Pacific time. A deadline or preferred window doesn't set a reminder or book your calendar."
  - The add form's fold has notes, deadline (date and time), preferred window, remind me at, repeats (all eight choices), and "Count from when it's done".
  - **Reminders appear in the chat**: every "reminders need Telegram" line was wrong and is fixed (Home, To do, Edit, Status, setup).
  - The edit page uses the real Status select (Open / Done / Cancelled), "New reminder or snooze until", "Cancel the pending reminder" and the real hint. Gone: the invented undo card and History.
- **Wishes**, rebuilt to the real three lists per kid (Every day, Christmas "In 83 days", Birthday "In 162 days").
  - The parent overview shows each kid's top three per list, "5 open", Flagged and Answers.
  - The new one-kid page and the kid's own page have Top / Up / Down, "Which list" + Move, Take off, "I wish for…" with "On", Answers ("Yes!" / "Not this time." with the note and "Ask again after 10 October"), and Flagged / Said no to ("A house rule", "Asked a parent").
  - **"Thinking about it" is gone**: the real app has only Yes! and Not this time.
- **Status:**
  - Added: Connected to (Google Calendar, weather and travel, reading the web, the weekend digest, this page); Where the money went (by kind of call, cache share, last call); Recent activity, admin only, each line opening `activity.html`; Waiting; Worth a look (a failed lookup; calls that ended oddly; the price check).
  - The Telegram line no longer says reminders can't go out.
- **The month calendar:**
  - The real source note.
  - No "Today" button (the real one shows "This month" only on another month).
  - "Put something on the calendar" links to the list view.
  - Month / List both link.
- **404:** the real words: "Not found", "There's nothing at that address.", "Back to the start". "Ask Vera to find it" is gone (a refused role can't chat).
- **Grown-ups page:** the real "manage" refusal, "changed by an admin… ask Sam" (it used to say "tell Sam or Alex").

## Wording changed, meaning kept

- "What Vera remembers" is titled **What Vera knows**, as the nav has said since stage 1.
- "the bot" became **Vera** wherever the family reads it (the persona's name; the real app does the same when a persona is set).
- "Organize in Chat" became **Organise in the chat** (British spelling, as the standard asks).
- "Edit #12" became **Change this idea**, with "Idea #12" above it; the number stays visible.
- The Family page's long intro became the lede ("Who Vera talks to. Each person signs in as themselves…"), and the Telegram note sits under the list.
- "Things to do" stays **To do** as the title, to match the nav and tabs; the real lede follows it.
- The To do quick-add button stays **Add**, not "Save task": stage 7's family note asked for a full, obvious Add.

## Kept from the design, not in the real app (for the hand-off)

These were designed in earlier stages at the family's request and aren't in the real templates; stage 10 should list each with the server change it needs:
- Person colour slots, and who a plan is for.
- "How did it go?" faces.
- "Vera today" on Home.
- The calm health pill shown all the time (the real bar lights only on trouble).
- The radar's names.
- Overdue grouping and "N days late".
- "Surprise · hidden from".
- The kid's "Tell Vera I did it".
- "20 messages left today".
- "Earlier messages".
- Undo after a tick.
- Nobody picked by default in the quick add (the real form defaults to the current person).

## Not finished

- A parent reading a kid's conversation (read-only, "Maya and Vera") isn't drawn.
- The plain parent (Alex) and the shared-password shell aren't drawn as whole pages; the sign-in page shows the shared case's "From" picker.
- The chat's per-message "used …" lines, the HELD / RETRYING / LOST waiting lines and the dictation mic aren't drawn (the states sheet has pending and failed).
- Status's "Models and prices" tables and "Who answers"' fallback wording are reduced to one line and the existing Technical details.
- The Family page's "Asked to talk to Vera" (Telegram knocks) isn't drawn: Telegram isn't connected in this sample.
- Settings and setup are stage 9.

# Stage 9: the whole app, part 2: settings and setting up (STAGE9.md)

The look stays as stage 8 left it, and no phosphor was added. Every new page uses existing parts where they fit: cards, folds, fields, tags, banners, `.steps`, `.srow` and `.choice`. The content and wording come from `app-reference/`: `fields.py` for every group and box with its help, `settings.py` for the overview lines and messages, `setup.py` and `status.py` for the steps, and the templates. Every page is rendered at 1280 and 390 px, light and dark.

## Settings

- **`settings.html`, the real `/settings`.** It has a row per page in the real order, each with its icon and the real one or two lines on how that page stands. The lines are worked out the way `settings.overview()` does it ("Vancouver, WA", "OpenAI answers, with gpt-6-luna.", "About $0.04 spent today.", "Last: Look ideas up on the web, Fri 2 Oct, 8:40 pm, by Sam."). A page gets "Needs a look" only when the real page would; in this sample nothing does, and Lookups shows "Off". Every row now links to its page. On the side are "Setting up" (the real line, plus a way into setup) and "Reading this list". The old colours card is gone: with themes, the colours are no longer fixed.
- **One page per section**, `settings-<name>.html`, sharing one layout:
  - the page's title and its real blurb, with "‹ Settings" above;
  - every settings page listed down the side on a desktop (left out below 1000 px, where the crumb does the job, as the real page says);
  - each group from `fields.py` as a card with its heading and its note. Fine-tuning groups (`folded=True`) fold, and when folded they say "2 changed".
  - Every box has its real label and help. The allowed range (from `limits()`) ends the help of a box you type in. A box changed here says "changed".
  - A dropdown's first choice is "Default (…)". A box you type in shows its default as the placeholder.
  - Model and chat boxes list their choices, then "Another model…" or "Another Telegram chat…", which opens a box to type into. It shows only while "Another" is chosen, by CSS `:has()` alone; a browser without `:has()` always shows it.
  - Each form has one Save, in a bar that stays in reach while the form is on screen and says "An empty box uses the default it shows." The AI model page's two Saves don't float ("still"), as in the real page, because they would sit beside a form they don't save.
- **General**: Where home is, Exact position (folded, 2 changed), This page, **How it looks** (new: see Themes), The server's log (folded), then the real "Where this page is served" and "A name for the page". The name card has the four steps, the commands, and the Docker fold.
- **AI model**:
  - Who answers: the three company cards (OpenAI "recommended", "✓ answers now"), the key form checked with the company, and "How to get a key from OpenAI" folded.
  - Then How strong a model answers (each level says the model and its price); Models, with the two in use and "Other models" folded; A second company; Keeping up with the companies (changed: off); Asking a stronger model; Better and best models (folded). "Save models" follows.
  - Then Voice notes and Photos, with their own Save, and "Every company's key", folded.
- **Spending**: the "About $0.04 spent today, of the $2.00 limit" line inside the form, then The daily limit, The kids' wish lists, Thinking, and What one message may use (folded).
- **Messages**:
  - "What Vera sends unasked" lists all nine kinds from `views.AUTOMATIC`. Each has a light (filled when on, a ring when off) beside the word On or Off, then when it goes, what it costs, how many went in 30 days, and Change.
  - "Sent lately" folds open to the message itself. (A message not sent yet would say "not sent yet"; none is, in this sample.)
  - Then the four groups, and the line to Personality.
- **Lookups**: Looking ideas up (changed: off), When, How often (folded), and the line to AI model.
- **Personality and family**:
  - The token line.
  - Who she is: personality, name, her description, and anything to add (changed).
  - About the family, empty with the real placeholder.
  - What she says unasked: groups of her lines. Each box has "Can use …" and a "Reads as" preview. "Reminders and follow-ups" says "1 of your own"; the long groups fold.
  - One Save.
- **Connections**:
  - Telegram, not set up: the token form, then Answering on Telegram and In a Telegram group, each with a quiet Save of its own, and the setup link.
  - Google Calendar, not connected: "Connect Google Calendar" open, with the client JSON form, and "Use a calendar by its id" folded.
- **Sign-in and security**: Signing in (everybody has their own password), Staying signed in, See a key (type your password, "Show it") and Sign everyone out (danger).
- **What has changed**: newest first. A key shows only "replaced" and a long text only "rewritten"; each line has when, who and from where.

## Setting up

These pages tell one story: Sam setting up a new install. On these pages the menu has no counts, and until a model is connected the pill reads "Vera can't answer yet".

- **`setup.html`**: "Let's get FamilyDB ready", the real lead, the seven steps (a number or ✓, title, how it stands, and a Done / Needed / Recommended / Optional tag), and "Carry on: Connect an AI model".
- **Every step page** has:
  - the steps along the top (All, then 1 to 7), with the current one in ink and done ones ticked;
  - "Step 3 of 7 · about 5 minutes · needed before it can answer";
  - the title, why it matters, then the form;
  - Back, and Next / Skip for now / Skip this at the foot;
  - for a needed step that isn't done, the real "Skipping is fine…" note.
- **`setup-you.html`**: your first name, "Add me".
- **`setup-password.html`**: the three tips, "For Sam, the admin on the family list", and the own-password form.
- **`setup-model.html`**: the company cards, "Get a key from OpenAI" with its steps, the key box and the model lineup with prices, and the daily limit folded.
- **`setup-told.html`**: the model step after OpenAI refused the key. This is the real `setup_told.html` message, at the top and on the box.
- **`setup-home.html`**: town, time zone (from the server, by region), units, "Save where home is".
- **`setup-telegram.html`**: "1. Make your bot", the six BotFather steps and the token.
- **`setup-telegram-link.html`** (a second state of the same step): "✓ Your bot is @tate_family_bot", "2. Link your phone", a message waiting with "That's me, Sam", and the group chat and different-bot folds.
- **`setup-family.html`**: "Theo is on the family list." at the top, everyone on the list, "Waiting to be let in" (Jo, from Telegram, with name and role), Add somebody, and what each role does. This also draws the Telegram knocks that stage 8 left out of the Family page.
- **`setup-calendar.html`**: "1. Give FamilyDB its own key to Google", the five Google Cloud steps, and the JSON.
- **`setup-done.html`**: "You're set up", "Ask “What should we do this weekend?”", "Or message @tate_family_bot", Left for later (Google Calendar), Personality, and where everything can be changed later.

## Themes: where and how they're chosen

Kitchen Table stays the default. The four themes in `theme-sources/` (Rail yellow, Enamel, Midnight, Ink) stand in as named examples. Each one is shown by its own colours, copied from its stylesheet.

- **For the family: Settings › General › "How it looks"**, inside General's one form and saved with its Save.
  - Each theme is a card with a real preview: a tiny Home in that theme (its panel, a heading, Vera's box, a card with the family's four colours, the button and the theme's accent), drawn twice, by day and by night. Each card also has the theme's name and one line about it.
  - The chosen card is ringed in ink with a tick, and the theme in use says "✓ In use".
  - Under the cards: "Light or dark, for the family": Light / Dark / Match this device, with what Match means.
- **For each person: You** (`you.html`, which was "Your password"; the account corner and menu now say "You").
  - "How it looks for you": "The family's theme: Kitchen Table" (the default, which follows the family's choice), or one of the five theme cards, and Light / Dark / Match this device, each with "Save how it looks".
  - Below that sits the password card, as before.
- **Kids too, on `you-kid.html`**: "How your screen looks. Only your own screen changes. Nobody else sees it." The account menu leads there.
- **With scripting off**: these are plain radio buttons in a form with a Save. The page reloads in the new theme (POST, redirect, GET). The radio cards are labels around real radios, so keyboard, screen reader and forced colours all work.
- **In the stylesheet**: the night tokens now also apply under `:root[data-appearance="dark"]`, and the media query stops applying under `data-appearance="light"`. So the server only has to write `data-appearance` (and `data-theme`) on `<html>`. See STANDARD.md §8.

## Found while looking at every shot, and fixed

- Bold words inside setup steps broke onto their own line (`.steps b` was a block); they're inline in sentences now.
- Settings side by side now line up row by row (label, box, help) using CSS subgrid, so a label that wraps no longer pushes its box down.
- Theme cards each carry their own radio ring, which fills with a tick when chosen; on a person's page the Kitchen Table card says "The family's".
- On the phone, Light / Dark / Match this device stack full width instead of leaving one alone on a line.
- The persona dropdown spans the card so its token count isn't cut off; long dropdown text ends in an ellipsis instead of being clipped.
- Setup pages keep everything within the 760 px column (banners, notes, the Left for later card); the chevrons stay at the right of their rows; spacing added after step lists and before the role descriptions; "✓ Your bot is @tate_family_bot." lost a stray space; the pill reads "Can't answer yet" so it fits.
- "Sent lately" rows keep their chevron at the right on the phone; the "changed" pills and inline commands have a stronger background in the dark.
- Connections' state lines are the real sentences; Sign-in and security's card descriptions share one style.

## Not finished

- The setup steps' other states are words only and not drawn:
  - Telegram "connecting…" (with its short meta refresh) and "refused";
  - Google's consent step (2) and calendar choice (3);
  - setup's "Nearly there" and "Not quite ready yet".
- Each settings page shows one state: Personality's "drift" note and Restore button, the Connections page once Telegram and Google are connected, and a revealed key (`settings_security(revealed=True)` exists in the generator but isn't a page) are not drawn.
- Only some of Vera's lines are drawn on Personality (the real page has about 60 in eight groups). Each group's first lines are shown, and "Answering /today…", "On Telegram" and "Telling an admin" are left out.
- The themes themselves are not designed here, as asked. Only Kitchen Table's tokens are in `style.css`; a theme's stylesheet would override them under `data-theme`.
- The sign-in page always uses the family's theme, since nobody is known yet.
- Kept as found: the sidebar's "Settings · 1 to check" and the home page's setup card (from earlier stages) disagree with the real overview, where nothing needs a look in this sample. The 24-hour times in settings boxes ("10:00") next to 12-hour times in sentences are the real app's.

# Stage 10: ready to build (STAGE10.md)

The look of every page is unchanged. This stage prepares the design to be built, and makes adding a theme a matter of adding a file. Every page was rendered again at 1280 and 390 px, light and dark (228 shots, no warnings), along with the two test themes.

## New files

- **`HANDOFF.md`**, for the engineers. It covers:
  - the page map (every mockup → template, route, view) and what the app can't produce yet, each with the smallest server change;
  - components → Jinja macros;
  - the stylesheet, fonts, brand files and head lines;
  - the rules kept, and what each existing script needs;
  - every wording change;
  - thirteen pull requests in order;
  - the tests that will change;
  - Themes;
  - open questions.
- **`STYLE-draft.md`**: the new `docs/STYLE.md`, in the current one's voice and structure, describing Kitchen Table as built.
- **`themes/kitchen-table.css`**: every colour token, by day and by night, moved out of `style.css`.
- **`themes/rail.css`, `themes/midnight.css`**: Rail yellow (light first) and Midnight (dark first), ported only to test the contract.
- **`_kit/theme-check.py`**: checks every theme file against the contract and its floors, and writes `palette/<theme>.html`.
  - The floors: contrast; the eight people and late red under simulated colour blindness (Machado 2009, CIEDE2000); phosphor kept for Vera.
- **`theme-test/`**: Home, Plans and a kid's Home in Rail and Midnight. Their shots are in `shots/themes/`, with the palette sheets.

## style.css, built for themes

- **Two layers.**
  - `style.css` now holds only what every theme shares: type, space, shape, sizes, and the brand (glass, phosphor, cursor, the mark's glass, the white rules in the always-dark Ask box).
  - Every colour is in the theme file.
  - Pages carry `data-theme` and `data-mode` on `<html>`, link their theme, and write `theme-color` for day and night.
- **No literal colour outside the tokens.**
  - Avatar letters were hard-coded white; now `--pN-on`.
  - The Ask box's rules and dimmed fills are now `--ask-rule` and `--ask-fill`.
  - The pane's scanlines are now `--glass-scan`.
  - The tab bar's shadow is now `--shadow-up`.
  - The dead `.ask .starter` rules are gone.
  - The FamilyDB mark's fill and stroke moved out of the markup into classes.
- **Renamed and removed.** `--sun` became `--send`, its only job. The unused `--info*` and `--vera-bg-2` are gone.
- **The panel has its own tokens.** The sidebar and the phone's top bar (`--side`, `--side-ink`, `--side-ink-2`, `--side-hi`, `--side-line`, `--side-mark`, `--side-link`) re-scope ink, card, line, focus and link inside it, so a theme may make the panel dark. The current page's mark is `--side-mark`, no longer Vera's green.
- **`data-appearance` became `data-mode`** (`auto`, `light`, `dark`), as the handoff names it.
- **The theme pickers list the installed theme files.**
  - That is Kitchen Table, Rail yellow and Midnight; Enamel and Ink were placeholders with no file, and are gone.
  - Each preview half carries `data-theme` and `data-mode` and is drawn by the theme file itself. The ten blocks of copied preview colours are gone.

## Found while porting the two themes, and fixed in the system

1. The sidebar assumed a light panel: on Rail's navy its words and links vanished. Fixed by the panel tokens.
2. Re-scoping Vera's green inside the panel turned the health pill's words yellow on pale green. The pill keeps Vera's tokens; only the nav's mark uses `--side-mark`.
3. The account corner's links were the page's link colour, unreadable on a dark panel. Fixed by `--side-link`.
4. Avatar letters were always white; Midnight's and Rail's light avatars need dark ones. Fixed by `--pN-on`.
5. The tab bar's shadow was a warm-brown literal. Fixed by `--shadow-up`.

## Also fixed

- **The wordmark's cursor never blinked.** Its animation count was a typo (`2te`), so the browser dropped the animation. It now blinks twice and stays lit, as STANDARD.md §7 says.
- **The kid's Home still showed "Thinking about it"** on a wish, which the real app doesn't have. The wish now shows "No answer yet".
- **The script notes** in STANDARD.md and STYLE-draft.md now keep the app's own `ask.js`, `dictate.js` and `wishes.js`, retire `menu.js`, and allow an optional `password.js`. They had named four new scripts.

## What the checks found

- **Kitchen Table** passes every contrast floor in both modes. Its people fall under the colour-blind floor in three places, recorded as known until the family decides (HANDOFF.md §9, question 1):
  - slot 4 and slot 7 are 1.1 apart under protanopia;
  - slots 2 and 5 are 2.5 apart under deuteranopia;
  - late red is 2.1 from slot 4 under deuteranopia.
- **Midnight** passes everything.
- **Rail yellow fails at night.** Its late red sits next to three of its warm people for colour-blind eyes. That is a flaw in Rail's palette, and the test catches it.

## Not done

- Nothing in `src/familydb/` was touched, as asked.
- The real test suite isn't here, so HANDOFF.md §7 lists the markup the tests likely pin, rather than the tests themselves.
- The JS files aren't here either: the hooks in HANDOFF.md §4 come from the templates.

# Stage 11: fitted to the looks the app built (STAGE11.md)

The family's engineers built theme support into the current app (`app-reference/built-looks/`): one `themes.css` of `light-dark()` blocks, seven looks in `web/looks.py`, a per-browser cookie, the Look page at `/look`, and `tests/test_look.py`. That is now the app's mechanism, so the design and the handoff follow it, replacing stage 10's plan (one file per theme, a family default and a per-person choice kept on the server).

## Token names: the built ones, and nothing moved

- **Renamed** to the built names wherever the role was the same:
  - `--side*` → `--band`, `--on-band`, `--on-band-2`, `--band-hi`, `--band-line`; the panel's mark → `--here-icon`, with the current item as `--here` / `--on-here`;
  - `--today-bg` → `--today`; `--alert` → `--red`; `--warn` → `--amber`;
  - `--primary-2` → `--primary-hover`; `--shadow-lift` → `--pop`; `--shadow-up` → `--pop-up`;
  - the wordmark's cursor is a look's `--cursor`.
- **66 roles Kitchen Table needs that the built set lacks** (HANDOFF.md §8.1 lists them all): the panel's links, each meaning's wash and rule, words on a late plate and on Vera's green, her pill and rim, her box's words, rim, edge, rules and Send, and the eight people. A `[data-theme]` block works each one out for every look from its own tokens.
- **Kitchen Table is one block**, `[data-theme="kitchen"]`, every value `light-dark(day, night)`, exactly as it would sit in the built `themes.css`.
  - The key is `kitchen`: the built test only reads one-word keys.
  - The fixed layer's night (the glass) is `light-dark()` too, so no media queries are left.
- **Proved:** every page rendered before and after the rename, and compared pixel by pixel. The only differences were the pages whose content changed in this stage, and animation noise on the states sheet (two renders of it differ from each other in the same place).

## The Look page replaces the stage-9 pickers

- **`look.html`** is the built Look page in Kitchen Table:
  - Day and night, with the built words;
  - every look as a card with its radio, name, blurb and its own Day and Night samples (Phosphor: "Night only");
  - "Use this look".
  - The samples keep the built markup (`look-sample[data-theme]`), which the test counts.
- **`look-kid.html`** is Maya's, just after she chose Fjord: the flash, and the whole page worn in Fjord.
- **The pickers are gone** from Settings › General and from "You". The You page is "Your password" again, as in the app, with a line pointing to Look.
- **The account corner** reads "Look · Your password · Sign out", and the phone menus have a Look row.
- **A household default and a person's own look** are a marked later step (HANDOFF.md §8.5), as the built STYLE.md lists them.
- **Removed:** the dead picker styles (`.themes`, `.theme*`, `.thumb`, `.mini*`, `.appear`), stage 10's `themes/` folder, its ports, `theme-test/` and `_kit/theme-check.py`.

## The built looks on Kitchen Table's shapes

- **Rendered:** Home and a kid's Home in Rail yellow, Midnight and Phosphor, day and night, desktop and phone (`looks-test/`, `shots/looks/`). They read.
- In the paper looks, Vera's box becomes a card, because their `--ask-bg` is `var(--card)`. That's a question for the family.
- **`_kit/looks-check.py`** replaces `theme-check.py`. For every look it runs:
  - the built floors (`test_look.py`'s);
  - the pairs Kitchen Table's layout draws;
  - the colour-blind checks, with Kitchen Table's three known shortfalls recorded.
  - It also writes `palette/<look>.html`.
- **Results:**
  - Kitchen Table, Phosphor, Rail yellow, Fjord, Ink and Midnight pass.
  - Enamel and Home Computer need an `--on-vera` (white words on Vera's green fill), added after the looks in `themes.css`; in the built file it goes inside each look's own block.
  - Home Computer's late red and orange action colour meet for tritanopes at night (4.9 against a floor of 6). That's a built look, so it goes to the family.
- **Phosphor as a look** names `--here-icon` and `--here-pill`, which it skipped as the default.

## Documents

- **HANDOFF.md:**
  - §8 is rewritten around the built mechanism.
  - The page map gains `/look`, and Your password is the app's again.
  - The order of work starts with Kitchen Table as a look on today's layout, a PR that can land now.
  - The tests list says what Kitchen Table changes in `test_look.py`.
  - The open questions are updated.
- **STYLE-draft.md:** "Looks" replaces Themes, with the built STYLE.md's facts.
- **STANDARD.md:** token names, the Look page and its sample, and the notes for the engineer.

# Stage 12: Afterglow as a look, and the small things that move (STAGE12.md)

## Afterglow, a look for Kitchen Table

- **`[data-theme="afterglow"]` in `themes.css`**, chosen on the Look page like any other (third card, after Phosphor). It is the earlier Afterglow round (`afterglow-ref/`) as a palette in the built names, plus effects. No page, markup or wording changed for it.
- **Night first, with a day.**
  - Night: charcoal glass with a breath of green.
  - Day: pale green-grey paper.
  - Both: a dark glass band, the dark glass Ask box, faint scanlines on both, and Vera the one lit thing.
- **Five effect tokens** join the look contract: `--fx-page`, `--fx-scan`, `--fx-glow`, `--fx-title`, `--fx-title-adjust`.
  - Every look names them: plain in the `[data-theme]` block and in Kitchen Table's own block.
  - `style.css` reads them once, in a new §11 "Effects".
  - Scanlines are a background under the words. They are off in forced colours and print.
- **VT323** (`fonts/vt323-400.woff2`, 18 KB, OFL) sets the page titles and the wordmark in Afterglow only, at Fraunces' cap height. Atkinson stays for everything read.
- **Vera stays the one lit thing**: in Afterglow her sign gets a wider halo and a fully lit rim, and her Send and chat lines glow. Nothing of the family's glows.
- **The glass panes' scanlines** (sign-in, 404, first day) moved from a film over the words (`.pane::after`) to the glass under them, in every look. They look the same.
- **Measured:** `_kit/looks-check.py` gained check D. It composites the scanline over the band and the Ask box, and the page light over the paper, and measures the words on top.
  - Afterglow passes every floor by day and night; its lowest is 4.70:1.
  - It wears Kitchen Table's people and is checked on them.
  - Its day green moved from `#0B6638` to `#0C6150` so late red stays clear of it for protanopes (5.4 → 14.1).
- **Rendered:** every page, day and night, desktop and phone, in `shots/afterglow/day/` and `shots/afterglow/night/` (240 shots, from `afterglow-test/`). Palette sheet: `palette/afterglow.html`, `shots/afterglow/palette-afterglow.png`.
- **Proposed:** once Kitchen Table ships, Afterglow becomes the look called "Phosphor" (HANDOFF.md §8.8, §9 question 12).

## The small things that move (every look)

- **Her sign types itself in**: once on Home, as the page opens (`.vs--hello`), and on a loop only while she writes back (`.vs--busy`, rewritten from a flicker into typing). Bars only: never words, never a face.
- **Afterglow** on the flash after an action; **landing** glow on `:target` cards, days and plans; the **wordmark's cursor** blinks for about four seconds, then rests lit.
- All CSS, in a new `style.css` §12. Every new motion lives inside `prefers-reduced-motion: no-preference`; the old ones stop in the `reduce` block. In Afterglow the lights are brighter (`--fx-glow`), never longer.
- **`motion.html`**: a fourth states sheet, showing each motion in place with when it plays. `shots/motion-frames.png` shows the sign's typing frame by frame.
- **`_kit/render-all.js`** takes screenshots with `animations: "disabled"`, so every shot shows the motions at rest.

## Documents

- **HANDOFF.md:**
  - §8.7 effect tokens;
  - §8.8 Afterglow, and its relation to Phosphor;
  - §8.9 what the built `themes.css`, `style.css` and `test_look.py` need;
  - §8.10 the motions;
  - the macro's `hello` state, the page map, and open questions 12–15.
- **STYLE-draft.md:** Looks (effects, Afterglow), Her screen (typing), Small things, Accessibility (motion), What does not move.
- **STANDARD.md:**
  - effects and Afterglow in the engineer's notes;
  - the sign's states and motion;
  - the wordmark's cursor;
  - the live-glow row;
  - a "Small things (motion)" table;
  - the motion sheet as a component.

# Stage 13: the family's decisions (STAGE13.md)

Each answer is folded into the design, HANDOFF.md, STYLE-draft.md and STANDARD.md. The answered questions are gone from HANDOFF §9; five remain (the grown-ups page for a parent, and the four from stage 12).

1. **Vera's box in the paper looks** stays a plain card. No change; the docs now say it was chosen.
2. **No colour-blind floor for the people.**
   - `_kit/looks-check.py` no longer simulates colour blindness: the people against each other, late red against them, and the recorded exceptions for Kitchen Table and Home Computer are all gone. Its palette sheets lose the "closest pairs" tables, and now fit a phone.
   - Every contrast floor stays, each person's letter on their colour included.
   - Colour is still never the only cue.
   - Every look passes, Home Computer included.
3. **Home Computer's night red**: no change.
4. **Kitchen Table becomes the default** when the new layout ships, for everyone who hasn't chosen. A look chosen before `0037` is copied from its cookie to the person once. The release note's line is in HANDOFF §8.2.
5. **A look follows the person.**
   - `members.look` in migration `0037`, written by the Look page through `familydb.family.choose_look`. The web AST test gains that one allowed call.
   - The cookie stays for pages before sign-in, and is set from the person's look when they sign in. While the family shares a password, it stays per browser.
   - No household default.
   - `look.html` and `look-kid.html` say it follows you; the phone menu's Look row says "Yours, on every phone and computer you sign in on".
6. **Status is for every grown-up.**
   - New mockups `home-parent.html` and `more-parent.html` (Alex, a parent): Status alone under "Behind the scenes", no Settings, Family or setup card.
   - Kids still never see it.
7. **A present is hidden from exactly whom it names**, by default its `gifts_for`.
   - The data change: `ideas.hidden_from` in `0037`, backfilled from `gifts_for`.
   - `visible_to` checks the viewer against it, for every role.
   - So Maya's Home now shows Theo's Lego set, tagged "Hidden from Theo".
   - The wishes note says a gift idea "is hidden from whoever it's for".
   - The `docs/DESIGN.md` §16 line to replace is given in HANDOFF §1 item 9.
8. **To-do edits: the to-do's own Edit page** (`todo-edit.html` → `task_form.html`, `GET /task/<id>/edit`), replacing the fold. Seven fields unfolding inside a list lose your place on a phone.
9. **"Set by Alex"**: `tasks.created_by_member_id` in `0037`, set from now on, shown on the kid's to-dos.
10. **"Installer" is gone** from what the family reads: "the password FamilyDB started with" in setup's password step, Status and Settings › Sign-in (four strings, HANDOFF §1 item 19).

Also fixed: the "Hidden from Theo" tag ran past its box in a narrow idea tile; it now wraps inside it.

Re-rendered: the pages that changed (Home, Maya's Home, both Look pages, both menus, Wishes, setup's password step) and the two new ones, by day and night on desktop and phone, in Kitchen Table and in Afterglow; and the palette sheets.

# Stage 14: the last answers (STAGE14.md)

- **Afterglow is one fixed look.**
  - Its `themes.css` block has one value per token (each `light-dark()` pair replaced by its night half) and `color-scheme: dark`, and the two `data-mode` rules skip it, as they skip Phosphor.
  - `looks.py`: `has_day=False`, band `#060A08`.
  - On the Look page: one "Night only" sample. The built line under "Day and night" now reads "Phosphor and Afterglow are green screens, so they have no day: they are always night, whatever is chosen here."
  - `shots/afterglow/`: one set (the night shots moved up; `day/` deleted).
  - `_kit/looks-check.py` reads a look with no `light-dark()` as night only (it was Phosphor by name), and its palette sheet has one column for such a look.
- **Phosphor is the design language; Afterglow is one look drawn from it.** Nothing is renamed, and the Phosphor look stays as it is. HANDOFF §8.8, STYLE-draft "Looks" and STANDARD say so.
- **My three calls (HANDOFF §9, now empty):**
  - A parent opening Settings, setup or the family list gets the friendly page, worded for an admin's part and naming the admin. New mockup: `admin-only.html`.
  - Afterglow's pixel face stays on titles and the wordmark only.
  - The five motions stay, and none of the old ones come back.
- **Re-rendered:** the Look pages, `admin-only.html` (Kitchen Table day and night, and Afterglow), and the palette sheets.
