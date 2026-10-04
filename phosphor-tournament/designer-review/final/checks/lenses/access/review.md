# FamilyDB final design: accessibility review

Lens: WCAG 2.2 AA and beyond, plus real-world low vision, dyslexia, colour blindness and one-handed phone use. I read all four overviews, the full-length desktop, phone and dark pages, `style.css`, `STANDARD.md` and the HTML for Home, Chat, To do, Plans, Wishes (kid), Add an idea, Sign in and the states sheets. I computed contrast from the CSS tokens with the WCAG 2.x formula, in light and in dark mode. Each item below is marked **[Failure]** (fails a WCAG 2.2 AA criterion, or a working path is broken) or **[Judgement]** (passes AA, but real users will be hurt).

## Verdict
**7.5 / 10.** The foundation is unusually good. Every text token pair I computed passes AA in both themes. Fields have real labels, errors are written as the fix and wired up with `aria-describedby` and `aria-invalid`, and focus, forced colours and reduced motion are all handled. What remains are a handful of real failures where the page meets the edges of the phone: the fixed tab bar, the app-height chat, the 3-second meta refresh and a broken phone link. There are also a few non-text contrast gaps (selected segments, dark-mode "today" and Maya's colour).

**Optimise before building? No.** Every failure below can be fixed in CSS or one template, without changing the design, so fix them in the first build pass rather than redrawing.

## Protect
- **Text contrast tokens** (`style.css` §2): every text pair I computed is ≥ 4.5:1 in light and dark. Examples: `--ink-3` on `--paper-2` 5.1, `--ok` on `--ok-soft` 4.9, `--alert` on `--alert-soft` 4.8, dark `--on-vera` on `--vera-bg` 5.55. `--edge` (3.8 on card) is used for every input, tick ring and choice pill.
- **Forms** (Add an idea, the To do quick add, `states-actions.html`): visible labels, "(required)/(optional)" in words, error summary with `role="alert"` linking to fields, per-field errors above the box, typed values kept, and errors such as "A link starts with https://".
- **Words, not colour** (To do rows, Status, Settings, nav badges): "6 days late", "Needs a look", "3 late", "1 to decide". The red rule and the tints only repeat what the words say. Calendar events and phone day links carry full spoken labels.
- **Atkinson Hyperlegible at 17 px body, 14 px floor, `.measure`/`.lede`/`.banner__text` capped at 62ch.** This is good for low vision and dyslexia. Keep the plain grade 4–7 wording, e.g. "This part is for grown-ups … There's nothing here you need to do".
- **Named controls**: ticks "Mark done: Call the dentist about Theo", faces "Loved it (Silver Falls hike)", wish arrows "Move Ice skates up", Edit links with the hidden title, and "Number 1:" on wishes.
- **Focus, motion, forced colours**: a 3 px `:focus-visible` ring (sun-yellow inside the Ask card, 4.6:1 on its green), the skip link on every page, `prefers-reduced-motion` stopping the typing dots, and `forced-colors` borders for every selected state.

## Fix, ranked

**1. The fixed tab bar can hide the focused control** (all phone pages, `.tabbar`) **[Failure, 2.4.11 Focus Not Obscured]**
- Problem: the 68 px `position: fixed` tab bar covers the bottom of the viewport, and there is no `scroll-padding`. When a keyboard or switch user tabs down a long page (To do, Ideas, Settings), the browser scrolls the next link only just into view, behind the bar. The same happens in Chat, where the sticky "Earlier messages" bar can cover a focused receipt link at the top of the scroller. Users at 200% zoom land on this layout too, because 1280 px ÷ 2 is below 820 px.
- Fix: in the phone media query add `html { scroll-padding-bottom: calc(var(--tabbar-h) + env(safe-area-inset-bottom) + 16px); scroll-padding-top: 16px; }` and `.scroller { scroll-padding-top: 56px; }`. Then tab through To do at 390 px to confirm.
- Severity: major. Effort: S.

**2. The 3-second meta refresh while a reply is pending** (Chat, `STANDARD.md` §8 "While a reply is pending") **[Failure, F41 / 2.2.1; also 3.2.5]**
- Problem: with scripting off, the page reloads every 3 s for up to 60 s. Each reload puts a screen-reader user back at the top of the page, drops their reading position and replays the page title. It interrupts a slow reader or a kid sounding out Vera's last message, and a magnifier user loses their scroll position. Under `prefers-reduced-motion` the dots stop, but the page still reloads every 3 s.
- Fix: drop the meta refresh. In the pending bubble (`.msg--pending`), show "Vera is thinking. **Check for her answer**". That is a plain link to `chat.html#latest`, so the person decides when to reload. Keep `chat.js` polling for everyone with scripting on. If an automatic fallback is kept at all, use a single refresh after 20 s or more, never a loop.
- Severity: major. Effort: S.

**3. The phone setup banner points at a hidden card** (Home phone, `.banner--slim.phone-only` → `href="#setup"`) **[Failure: broken link; 2.4.4 / 3.2.4 in spirit]**
- Problem: the "3 setup steps left · Continue" button links to `#setup`, but `section#setup` has `.desk-only` (`display: none` at ≤ 820 px). On a phone, and at 200% zoom on a laptop, Continue goes nowhere. The full-length `phone/home.jpg` confirms the card isn't on the page. The admin can't reach "Set up sign-ins" from Home.
- Fix: point Continue at the real setup page (the first unfinished step of the first-time setup flow), or render the setup card on the phone at the bottom of Home and keep the anchor.
- Severity: major. Effort: S.

**4. The chat room collapses at short heights** (Chat phone, `.chat { height: calc(100dvh - 56px - 68px) }`) **[Failure, 1.4.10 Reflow]**
- Problem: the room is a fixed app-height column. Its fixed-height children are the conversation pills (~52 px), the privacy line (~50 px), and the composer: "Writing as", the 50 px box, and the 44 px location check (~150 px). At 200% zoom on a 1280×720 laptop (640×360 CSS px), or on a 740×360 landscape Android, 360 − 124 leaves ~236 px for ~250 px of fixed parts. The message scroller gets almost no height, so you can't read Vera's answer. This also hurts low-vision users who keep zoom high.
- Fix: `@media (max-width: 820px) and (max-height: 560px) { .chat { height: auto; } .scroller { flex: none; overflow: visible; } .room .composer { position: static; } }`, so the page scrolls normally. Also fold the location checkbox into the `composer__foot` line, or into `<details>`, on short screens.
- Severity: major. Effort: S.

**5. The tab bar ignores the iPhone safe area** (`.tabbar`, `body { padding-bottom }`, `.chat` height) **[Failure: content clipped and covered]**
- Problem: `* { box-sizing: border-box }` plus `height: 68px` with `padding-bottom: calc(6px + env(safe-area-inset-bottom))`. On an iPhone with a home indicator (34 px inset, and the pages set `viewport-fit=cover`), that leaves about 22 px for a 24 px icon plus a 13 px label, so the labels clip. The page's `padding-bottom: 68px` and the chat height don't include the inset, so the last row of every page and the chat box sit partly under the bar. STANDARD §1 says "68 px plus env(safe-area-inset-bottom)", but the CSS doesn't do that.
- Fix: `.tabbar { height: calc(var(--tabbar-h) + env(safe-area-inset-bottom)); }`, `body { padding-bottom: calc(var(--tabbar-h) + env(safe-area-inset-bottom)); }`, and subtract the same inset in `.chat`'s height.
- Severity: major. Effort: S.

**6. Selected tabs and segments are shown only by a faint fill and a hue shift** (To do / Ideas / Plans `.seg`, desktop `.convo`, phone `.tabbar`) **[Failure, 1.4.11 for `.seg` and `.convo`; Judgement for the tab bar]**
- Problem: the selected segment is `--card` on `--paper-2`, which I computed at **1.20:1** (1.04 in dark), plus a 0.18-alpha shadow. The selected desktop conversation is `--card` with a `--line-2` border on `--paper`, about 1.5:1. The current phone tab is `--vera-soft` (about 1.2:1 against `--card`) and the label changes from grey `--ink-2` to green `--vera`. Both labels are dark, so for someone with colour blindness or low vision it is a hue change only. A kid looking at "Open / Done / Cancelled / All" can't tell which list they're on. (The desktop sidebar is fine: its 3 px `--vera` bar is 6.3:1.)
- Fix: give the selected segment a 1.5 px `--ink` border, or fill it with `--ink` and put `--paper` text on it, as the phone conversation pills and `.choice:checked` already do. Give the current tab a 3 px `--vera` bar on its top edge. Give `.convo[aria-current]` the same inset 3 px `--vera` bar as the nav.
- Severity: major. Effort: S.

**7. Dark mode: today's marker and Maya's colour are under 3:1** (Plans calendar, dark) **[Failure, 1.4.11]**
- Problem: dark `--vera-bg` (#2D7462) against dark `--card` is **2.86:1**. That is both the today ring (`.day--today`) and the filled today number, and the visible `dark/plans-phone.jpg` ring is dim. `--maya` (#B03F66) isn't redefined for dark, so Maya's phone calendar dot is **2.84:1** on the card and her event bar is **2.67:1** on `--maya-soft`. On the phone, that dot is the only visual sign that a day is Maya's.
- Fix: in dark mode, outline today with `--vera` (#7CC7AE, 8:1) instead of `--vera-bg`. Add dark values for the person colours used as marks (e.g. dot and bar use `--{person}-ink`: Maya's #F2A3BE is about 7:1). The STANDARD's eight-colour set should be checked at 3:1 against the dark card too, not only "4.5:1 with white letters".
- Severity: major. Effort: S.

**8. The To do segmented control scrolls sideways with no visible scrollbar at 320 px** (To do and kid To do phone, `.todo-bar .seg`) **[Likely failure, 1.4.10; verify]**
- Problem: `.seg` is `flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none`. "Open 4 · Done · Cancelled · All" at 17 px bold needs about 335 px. It fits at 390 (358 px available), but at 320 px CSS (288 px available, which is also 400% zoom on a 1280 screen) "All" is pushed off the edge, with no scrollbar and no fade to show it's there.
- Fix: let this segment wrap into a 2×2 grid below 360 px (`@media (max-width: 360px) { .todo-bar .seg { display: grid; grid-template-columns: 1fr 1fr; border-radius: var(--r-md); } }`), or shorten "Cancelled" to "Dropped". Check every `.seg` at 320 px.
- Severity: minor. Effort: S.

**9. Small targets and text below the stated floor, on the pages kids use** (`.textbtn` 32 px "Take it off my list" on kid Wishes; setup links 32 px; `.starter`, `.btn--sm` and `.seg a` at 40 px; tab badge 12 px; `.av--sm` 12 px) **[Judgement: AA 2.5.8 (24 px) passes; the STANDARD's own 44 px / 14 px rule doesn't]**
- Problem: "Take it off my list" is a destructive 32 px text button directly under the parent's quote, on the page Maya (11) uses most. It's an easy mis-tap one-handed. The starter pills and `--sm` buttons ("See the plan", "Move it", "Connect Google Calendar") are 40 px. The tab bar's late count is 12 px red on pink.
- Fix: set `.textbtn`, `.card--setup .steps a` and `.rank > .linkbtn` to `min-height: var(--target)`. Raise `.starter`, `.btn--sm` and `.seg a` to 44 px on the phone only. Make the tab badge 13 px bold (it's only a digit), and make sure the Undo flash follows "Take it off my list" as drawn for to-dos.
- Severity: minor. Effort: S.

**10. Field hints sit inside `<label>` and become part of the field's name; some boxes have only a placeholder visibly** (Add an idea "Kind", To do quick-add "Who"/"Due", Wishes "A word for Maya"; To do "Add a to-do…", kid "What do you wish for?", Chat "Write to Vera…") **[Judgement]**
- Problem: because `.field__hint` is inside the `<label>`, a screen reader announces "Kind, optional, Gift ideas never show on Maya's or Theo's pages, combo box", as one long name. That also breaks voice control ("click Kind" still works, but the name is noisy). The quick-add boxes rely on a placeholder as their only visible label. Once a dyslexic user or a kid starts typing, the prompt vanishes. That's acceptable for a one-line add next to an "Add" button, but not for the composer once a draft is long.
- Fix: in the `field()` macro, render the hint outside the label with an `id` and add `aria-describedby` on the control (as the error already does). Keep the placeholder boxes, but add a short visible label above the kid's wish box ("Add a wish") and the chat composer on desktop ("Message to Vera").
- Severity: minor. Effort: S.

## Missing
- A tested 320 px and 400%-zoom pass of every page, with screenshots. The pack shows 390 px only, though STANDARD §5.9 asks for 320.
- Light-mode high-contrast and `prefers-contrast: more` values: thicker `--line-2` borders, `--ink-3` going to `--ink-2`. Cards and quiet buttons are bounded by 1.4–1.7:1 lines, which low-vision users won't see.
- Text-spacing check (1.4.12): `.dt` (fixed 64 px, `overflow: hidden`), `.badge` (fixed 24 px height) and `.tag` (`white-space: nowrap`) are the likely clippers under 0.12 em letter spacing or larger iOS Dynamic Type.
- How a screen reader hears a *new* message arriving when `chat.js` swaps the pending bubble. The `role="log"` is there, but the swap must insert a new node, not change text in place, or it won't be announced.
- The "Show" password button's states. It is drawn statically, so the `aria-pressed` text change and its focus-ring position next to the field need a spec.
- What a kid sees when "Take it off my list" is pressed (confirmation or Undo flash on the wish list), and the reason in words on the disabled first "Move up" arrow.
- The dark-mode values for all eight person colours as marks (dots, bars, avatar edges), checked at 3:1 against the dark card.
- An audio or "read aloud" check of Vera's replies to kids. Reading level is controlled on the pages, but the model's output isn't, and that's most of what Maya reads.

## One sentence
Make the phone shell honest about the screen it sits on: give the fixed tab bar its safe area and `scroll-padding`, let the chat room fall back to normal page scroll on short screens, and replace the 3-second refresh with a "Check for her answer" link. Then keyboard, zoom and screen-reader users get the same app as everyone else.
