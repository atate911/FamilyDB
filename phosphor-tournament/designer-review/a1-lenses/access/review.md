# Accessibility review: FamilyDB "Kitchen Table" design

Lens: WCAG 2.2 AA and beyond (low vision, dyslexia, colour blindness, one-handed phone use, kids).
Contrast ratios below are computed from the colours in `style.css`. **[Fail]** marks a WCAG 2.2 AA failure. **[Judgement]** marks a problem that is not a WCAG failure but still hurts this family.

## Verdict
**6.5 / 10.** The basics are better than most designs. Body text is 17px Atkinson Hyperlegible with 1.5 line height, buttons and nav items are 38–46px tall, every field has a label, there is a strong focus ring, nothing moves, and lateness is always written out in words. But one grey colour token, `--ink-3`, fails text contrast on almost every page, form-field borders are nearly invisible, and the phone calendar turns plans into nameless 8px coloured bars. These are cheap to fix now and expensive to fix after the design spreads to the other pages.

**Optimise before building?** Yes. Most of the failures live in a handful of shared tokens and components (`--ink-3`, `--line-2` on fields, `.ev` on phone, `.sr`), and every page that hasn't been drawn yet will copy them.

## Protect
1. Type on all pages: body 17px Atkinson Hyperlegible, line height 1.5, numbers with slashed zeros, ink `#1D2526` on paper (14.6:1). Good for dyslexia and low vision.
2. Focus ring on all pages: a 3px ink `:focus-visible` outline offset 3px, switched to sun `#F2C14E` inside the green Ask Vera card (4.6:1 against the green), plus whole-card focus on Ideas cards via `:has()`.
3. Late to-dos (Home and To do): the red bar always comes with "6 days late" in words and the "Overdue · 3" heading, and each tick button has the name "Mark done: Call the dentist about Theo". Colour is never the only signal there.
4. Target sizes on all pages: nav links 44px, `.btn` 46px, `.btn-sm` 38px, month arrows 44px, phone tab bar about 63×54px, checkboxes 22px inside a 44px label. All comfortable for one-handed use.
5. Labels: the "Writing as" `fieldset`/`legend` radio chips (Chat), visible "Who / Due / Kind / Status / For" labels (To do, Ideas), and `.sr` labels where a field has no visible one.
6. Settings rows say their state in plain words ("Still the password the installer made"), the tag repeats it, and a "Reading this list" key explains the tags. No animation anywhere in the CSS. Reading level is about grade 4–7 on every page (rough Flesch-Kincaid estimate).

## Fix, ranked

**1. The secondary grey text fails contrast across the app** (`--ink-3`: Home ".soon .s", "Only parents see this", "Vera hasn't looked it up yet"; sidebar "BEHIND THE SCENES"; Chat timestamps and conversation previews; Status ".stat .x" and meter scale; To do "Whenever suits"; Plans greyed-out day numbers) **[Fail 1.4.3]**
- Problem: `#6E7778` measures 4.48:1 on card, 4.08 on paper, 3.74 on the sidebar's paper-2, 3.70 inside Vera's green chat bubbles, and 4.01 on the setup card's yellow. This text is mostly 13–15px, so it needs 4.5:1. It hurts low-vision parents and anyone reading a phone outdoors, and it is used for hints kids need ("Not looked up yet").
- Fix: set `--ink-3: #596263`. That gives 6.1 on card, 5.6 on paper, 5.1 on paper-2, 5.0 on vera-soft and 5.5 on sun-soft. The look barely changes. Also use the new token for `--home` (the Household avatar).
- Severity: major. Effort: S.

**2. The phone calendar shows plans as nameless coloured bars** (Plans, phone and any window under 820px, which includes desktop at 200% zoom: `.ev { font-size:0 } .ev * { display:none }`) **[Fail 1.1.1/4.1.2, 1.4.10, 2.5.8, 1.4.1]**
- Problem: each plan becomes an 8px-tall link with no accessible name (its only remaining text is a space). The plan's kind is shown by colour alone, and past plans become pale grey bars (29 Sep, 1 Oct) that you can hardly see. A screen reader announces "link" with no name, the target is far below 24px, and a colour-blind parent can't tell the Day trip bar from the Trip bar. On top of that, `role="grid"` sits on a `div` that has no `row`/`gridcell` children, which is invalid ARIA.
- Fix: below 820px, make each day that has plans a single `<a>` covering the whole cell (at least 44px tall) that goes to the list view anchored on that day, e.g. `href="plans-list.html#d-2026-10-09"`, with a hidden name such as "Fri 9 Oct: Mount St. Helens day trip, 09:00". Mark the bars `aria-hidden="true"` and keep them as decoration, and give past plans a 2px dashed `--ink-3` outline instead of a grey fill. Replace `role="grid"` with a real `<table>` (with `<th scope="col">` for the weekdays), or remove the role. Better still for kids, open List view by default on phones.
- Severity: blocker. Effort: M.

**3. Form fields and to-do tick circles have almost invisible edges** (all inputs, selects and searches on To do, Ideas, Chat and Home; `.tick` on Home and To do) **[Fail 1.4.11]**
- Problem: `--line-2 #D3C6AC` is 1.69:1 against white and 1.65:1 against the card. A field's white fill on a `#FFFCF6` card is the same colour, so the border is the only thing that shows where to tap. The empty tick circle is how you mark a to-do done, and it is just as faint. Low-vision users and anyone in sunlight lose both.
- Fix: add a token `--field-edge: #8A806C` (3.9:1 on white, 3.8 on card) and use it for `input`, `select`, `textarea` and `.tick` borders. Keep `--line-2` for decorative dividers. For the tick, use a 2px edge, or show a faint check mark (`color: var(--ink-3)`) inside the empty circle so it reads as "tap to tick".
- Severity: major. Effort: S.

**4. Reminder status disappears below 1180px** (To do, `.trow .rem { display:none }` at `max-width:1180px`) **[Fail 1.4.10]**
- Problem: on phones, on small laptops and at 200% zoom, "No reminder / Add one" is removed with no replacement. Content lost on reflow is a failure, and the brief requires every to-do to show whether it has a reminder.
- Fix: below 1180px, don't hide the reminder. Put it into the row's meta line as a third item: a bell icon plus "No reminder" (or "Reminder Tue 09:00"), with the "Add one" link at least 24px tall (`padding: 4px 0` or `display:inline-block; min-height:24px`).
- Severity: major. Effort: S.

**5. Past plans on the desktop calendar fail contrast** (Plans, `.ev.past` "Pho Oregon 17:00 Rate it", "Silver Falls hike 10:00 Rate it") **[Fail 1.4.3]**
- Problem: `opacity:.78` on a grey fill brings the time to 2.7:1, the title to 3.8:1 and the 12px "Rate it" to 3.2:1. "Rate it" is a call to action, and it is the faintest text on the page.
- Fix: remove the `opacity`. Keep the `#F1ECE2` fill with the title in `--ink-2` (6.4:1), the time in the new `--ink-3` (5.1:1) and "Rate it" in `--warn` at 14px bold (4.8:1). Show that a plan is past with a dashed left border, not by fading it. Make "Rate it" its own link, or name the event link "Pho Oregon, Tue 29 Sep, past. Rate it".
- Severity: major. Effort: S.

**6. The skip link never appears on screen** (all pages, `<a class="sr" href="#main">Skip to content</a>`) **[Fail 2.4.7]**
- Problem: `.sr` has no `:focus` override, so a keyboard user's first Tab lands on something they cannot see.
- Fix: add `.sr:focus { position:fixed; left:16px; top:12px; width:auto; height:auto; clip:auto; padding:10px 16px; background:var(--card); border:2px solid var(--ink); border-radius:12px; z-index:10; }`.
- Severity: major. Effort: S.

**7. Ask Vera's suggestion chips send half a sentence, and on the phone they are hidden off-screen** (Home, `.sugg` buttons "Remind me to…" and "Save an idea…") **[Judgement, plus 3.2.2-style surprise]**
- Problem: each chip is a submit button (`name="text" value="Remind me to "`), so one tap sends "Remind me to " to Vera at once. Kids and one-handed users tap by accident, and nothing can be undone. On a 390px phone the row scrolls sideways with its scrollbar hidden: "Remin" is cut off and "Save an idea…" can't be seen at all.
- Fix: only full questions submit ("What should we do next weekend?"). Make the starter phrases links that refill the box without JS, e.g. `<a href="home.html?draft=Remind+me+to+#ask">`, with the server putting the text in the textarea and `autofocus` on it. At ≤820px let the chips wrap onto two lines (`flex-wrap: wrap`, remove `overflow-x`).
- Severity: major. Effort: M.

**8. Text smaller than 14px in key places** (phone tab labels 12px, tab badge 11px, phone weekday headers 11px, date-tile weekday 11–12px, calendar "TODAY" and "Rate it" 12px, sidebar "BEHIND THE SCENES" 13px uppercase, `.stat .x`, `.trow small`, `.seg .n` 13px) **[Judgement; low vision, dyslexia, kids]**
- Problem: everything else is 15–17px, so these are the words that get skipped. Uppercase plus letter-spacing at 11–13px is the hardest combination for dyslexic readers. On the phone, "TODAY" is clipped to "TOD" in the 3 Oct cell.
- Fix: set a 14px floor for all text (13px only for tab labels), and use sentence case instead of uppercase for "Behind the scenes", "Overdue" and the weekday headers. On the phone, drop the "Today" word in favour of the filled day circle, with a `.sr` "today" so screen readers still hear it.
- Severity: minor. Effort: S.

**9. Badges whose meaning is lost** (phone tab bar "3" dot on To do; "More" tab; sidebar counts) **[Judgement / 1.3.1]**
- Problem: the phone tab badge `<span class="dot">3</span>` has no hidden text, so a screen reader hears "To do 3" instead of "3 overdue". The sidebar's "Settings 1 needs a look" warning has no phone equivalent because Settings sits behind "More", which has no badge. On desktop, a red "3" and a yellow "12" differ only by colour: one means overdue and the other is a total.
- Fix: add `<span class="sr"> overdue</span>` inside the tab badge. Put a badge on "More" whenever anything inside it needs attention. Give the sidebar badges a word: "3 late" and "12", with the 12 drawn as plain text or an outline rather than a filled pill.
- Severity: minor. Effort: S.

**10. Names and labels that don't match what people see** (Chat, Plans, Ideas) **[Fail 4.1.2/2.5.8 small; rest judgement]**
- Problem:
  - The Chat Send button has both a visible `.l` "Send" and a `.sr` "Send", so its name is read as "Send Send".
  - On the phone the Chat page's `page-head` is `display:none`, so the page has no h1, and the only visible label for the message box is placeholder text.
  - The three "How did it go?" faces (Plans) are icons with no words, and the smile and "meh" faces look almost the same at 22px.
  - The "Look it up" link on Ideas cards is about 22px tall and sits inside the whole-card link, so a near miss opens the idea instead. That is under 24px with no spacing, a 2.5.8 failure.
  - Theo's avatar is white on `#C66A12`, which is 3.84:1.
- Fix:
  - Chat: delete the `.sr` span. Hide the phone h1 with `.sr` instead of `display:none`.
  - Faces: add a visible caption under each face ("Loved it / OK / Not great").
  - "Look it up": give it `min-height:44px; display:inline-flex; align-items:center`, or move it outside the card link.
  - Theo's avatar: set `--theo: #A85A0F` (5.1:1).
- Severity: minor. Effort: S.

## Missing
- Form errors: what an empty to-do title, an invalid date or a failed save looks like. The error should be text tied to the field with `aria-describedby` and named in an error summary at the top, not just a red border.
- What happens after a post: once a to-do is ticked, a thought saved or a face chosen, the reloaded page needs a visible "Done: Call the dentist about Theo. Undo" message, with focus moved to it.
- Chat waiting for Vera with scripting off: "Reload if nothing shows" puts the work on the user. Show a "Vera is writing…" state and a "Check for her reply" button. Don't use a timed meta-refresh, which would fail 2.2.1.
- Forced colours / Windows High Contrast and dark mode: the selected segment (`.seg`), the selected "Writing as" chip and tags rely on background colour only, and need `@media (forced-colors: active)` borders.
- Sign in, "Not you? Switch" and choosing a password: allow paste and password managers, add a show-password toggle, and add no puzzle or memory test (3.3.8). A kid must be able to switch user on a shared laptop without help.
- The kid's view of Home and To do, plus the note that "parents can read this chat". These should be checked for reading level and for 44px targets on a small phone.
- States where things have gone wrong: spending limit reached, Vera offline, Telegram broken. Each needs words and an icon, not just red, on Home, Status and the top bar ("Vera is on").
- Stress cases: long idea titles and ten or more plans in a day at 200% text (`.ev b` is truncated with an ellipsis), the 1.4.12 text-spacing override on `white-space:nowrap` tags, and 320px width.

## One sentence
Change the two colour tokens first, `--ink-3` to `#596263` and the field and tick borders to `#8A806C`: those two lines fix most of the contrast failures on every page, drawn or not.
