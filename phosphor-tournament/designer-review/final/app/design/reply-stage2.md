Both Chat fixes are in, and stage 2 is done. All 17 pages render at desktop and phone width with fonts loaded. Nothing scrolls sideways at 390 px, and no page has an inline style or a script. I checked every shot, and kid Home in dark mode, then fixed what I found and re-rendered.

**Chat fixes**
- **Phone:** the thread now starts under a pinned "Earlier messages" bar with a hairline and a fade. A message that runs past the top fades out under the bar instead of being cut off mid-sentence.
- **Desktop:** the chat area now grows with the conversation, so Sam's question shows above Vera's answer. The server still sends only the latest 30 messages. On the phone, the chat still fills the screen with the box pinned at the bottom.

**Stage 2 pages**
- **Kid view (Maya):** `home-kid`, `chat-kid` and `todo-kid` use her own menu and her own tab bar (Home, Chat, Wishes, To do, More). She never sees cost, models, setup or gifts. Where something isn't hers to change, she sees a lock and "Ask a parent", for example moving a plan or editing a to-do for everyone.
- **`wishes-kid`:** she adds wishes and orders them with up and down buttons, each a small form. The parents' answers show as a word ("Yes!", "Thinking about it", "Not this time") plus their own note.
- **`wishes` (parent):** the undecided wish has Yes / Thinking about it / Not this time with nothing pre-selected, and an optional note for Maya. A side card steers presents to gift ideas, which the kids never see.
- **`more`:** Ideas, Wishes, Status, Settings, Family and Sign out, with the same badges as the desktop menu.
- **`signin`:** pick who you are, then your password, with paste allowed and a Show button. Below it is the brand-new-install case: one family password, "Who are you?" with nobody picked, and a sample message box asking "Who's writing?" with no default.
- **`grownups`, `idea`, `idea-new`:**
  - `grownups`: a friendly page, with a way back to Home or the chat.
  - `idea`: Oaks Park roller rink on its own page.
  - `idea-new`: the full form pattern for the engineer, with grouped sections, "(required)" and "(optional)" written out, hints, and Save / Cancel.

**Added to the system, not drawn as one-offs:** back link, empty state, the "Ask a parent" lock, choice pills, the ranked wish row with the parent's note, the form pattern (with error styles ready for stage 3), password field, key/value pairs, the person picker, and up/down arrow icons. `CHANGES.md` lists them all.

**Things to check**
- **Maya's wishes are invented.** The brief gave Maya no wishes, and ranking and answers can't be shown on an empty list, so she now has four:
  - Ice skates (thinking about it)
  - A sketchbook and brush pens (yes)
  - A sleepover with Ava (not this time)
  - A pet hamster (added today, not decided yet)

  The parent Home and menu now say "1 to decide". Theo still has none, which shows the empty state.
- **"20 messages left today" is an invented number** for the kids' daily message cap.
- **Maya sees her own to-dos plus the ones for Everyone.** The brief has none of hers, so her list shows only "Renew library cards".
- **The Show password button needs scripting.** With scripting off it isn't rendered, and paste still works.

**Not done yet**
- **Missing kid pages:** the kid's More page and the Family page are linked but not drawn.
- **No states yet (stage 3):** limit reached, Vera can't answer, pending and failed messages, Undo after an action, form errors.
- **Dark mode:** checked only on Home, Chat, To do and kid Home.
- **Phone screenshots:** the fixed tab bar still appears at the 844 px fold, where a real phone's first screen ends.

The same summary is in `reply-stage2.md`.
