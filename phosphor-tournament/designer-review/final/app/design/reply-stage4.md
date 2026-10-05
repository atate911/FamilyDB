I've done the polish pass in the order POLISH.md gives. All 22 pages render at desktop and phone width, light and dark: 88 shots, every one with its fonts loaded and none wider than the screen. No page has inline styles or scripts.

**What changed**
1. **Person colours by slot:** colours are now eight numbered slots that the server assigns to each person, plus a neutral one for Everyone. Today's four colours are slots 1–4, and the four new ones (teal, indigo, olive, magenta) pass contrast in both themes. This also fixes Maya's dot in dark mode, which was below 3:1.
2. **Phone opens on what you came for:** on Home, Ask Vera is now one row, so the next plan's title and time show above the tab bar. Cards are capped ("3 more plans this month", "All 4 to-dos") and the phone Home is about a quarter shorter. To do and Ideas now put the list before the tools.
3. **Tab bars:** parents get Home, Chat, Ideas, Plans, To do; kids get Home, Chat, Wishes, Plans, To do. Everything else moved into a menu behind the avatar, with a new kid version. A dot on the avatar says something needs checking.
4. **Phone Plans:** the Month/List switch sits right under the month header, with the grid after it.
5. **Calendar:**
   - Events carry the person's colour clearly; Everyone stays neutral.
   - A plan over several days is one bar, split at the week edge with ‹ ›.
   - Today is a filled disc, not a ring, and past plans are plain.
   - The states sheet now draws a real November: a busy Saturday ("+2 more") and a five-day trip that crosses a weekend.
6. **One meaning per signal:**
   - Yellow is only Send and "set this up"; mint is only "all good".
   - Info and "Off" are neutral; dashed lines only mean "not yet".
   - "Needs a look" (yellow with "!") and "Could be better" (outline, hollow dot) are easy to tell apart.
   - There's one "set this up" message per page, and only "3 late" and "1 to decide" badges stay loud.
7. **Numbers:** running text is all Atkinson now. The serif figures stay only where numbers stand alone or line up (date tiles, money, calendar days). Atkinson Hyperlegible Next turned out to have no unslashed zero either, so running times keep the slashed zero.
8. **Accessibility:**
   - The tab bar accounts for the iPhone home indicator and never covers the focused control.
   - Chat falls back to normal scrolling on short screens.
   - Selected tabs and segments are no longer shown by a faint fill alone.
   - Today's marker in dark mode passes contrast.
   - Kid targets are 44 px, and field hints are no longer inside the labels.
9. **Kid to-dos:** the row now starts with the face of the parent who set it, plus "Not done yet" and "Tell Vera I did it", so it doesn't look tickable. Maya's own things come first on her phone Home, and she gets a gentle "5 messages left today" warning.
10. **Words:** "Vera is ready", "Vera is writing back", one set of wish answers for kids and parents ("No answer yet"), "We went", "Quick idea", "Add a backup key", "Not Sam? Switch". Spelling stays British English, as POLISH.md says the app is written.
11. **Forms:**
    - The quick add shows "Who's it for?" as visible person pills with nobody picked.
    - Ideas sends one sort control, and the button comes after the filters.
    - Starters that send look different from ones that fill the box.
    - "Share where I am" is gone from kid pages, and buttons and tags can wrap.
12. **New:** a to-do edit page (`todo-edit.html`), and Vera's weekend suggestions message in the family chat, each idea with a "Plan it" button.

**What I declined, and why**
- **US English** (copy review): POLISH.md says the app is British English, so the interface matches it.
- **A fixed-height desktop chat** (engineer): you asked earlier for the whole short conversation to show on desktop, so it still grows.
- **Green for Everyone's calendar events** (style review): green is Vera's colour, and POLISH.md keeps Everyone neutral. Plans for several people now take the first person's colour, so most events have colour.
- **An "I did it" button that marks a kid's to-do** (kid, parent and usability reviews): kids can't change anything, so it fills her chat box instead.
- **Dropping the "Reading this list" key on Settings** (generalist, interaction): kept, because the earlier reviews asked to protect it.
- **A 30-day spending chart** (generalist, skeptic, usability): drawing it would mean inventing daily numbers the brief doesn't give.
- **Left alone, as POLISH.md says:**
  - **Vera:** she stays undrawn.
  - **Pending reply:** the refresh is kept, with a visible "Check for her answer" link. The accessibility concern and a suggested back-off are written into `STANDARD.md` for the engineer.
  - **Family decisions:** ticking, private surprise chats and kids sharing location are listed in `CHANGES.md` under "For the family to decide".

**Invented sample content in this pass:** prices and weather in the weekend suggestions ("about $15 each", "free to get in"), the November events, and a short kid chat on the states sheet. All of it is listed in `CHANGES.md`.

**Unfinished:** the Family and What Vera knows pages are linked but not drawn; Theo's own pages aren't drawn; and I didn't render at 320 px. The segmented controls now wrap instead of scrolling, which was the known risk there.

The same summary is in `reply-stage4.md`, and `STANDARD.md` and `CHANGES.md` are updated.
