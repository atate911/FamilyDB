Stage 6 is finished. Every brand element is still there: the mark, the wordmark, the pill, the radar, Settings' key and the four brand moments. The costs the judges and lenses named are fixed. All 24 pages are rendered light and dark, desktop and phone (96 shots, no warnings). Three reviewers and I looked at every shot; I fixed what they found and rendered again. No page has `style=""` or `<script>`.

**What changed**
1. **Vera's sign** is redrawn as a crisp rounded-square pane with a lit rim, a few lines of light and a lit `>▮` prompt in the corner.
   - The prompt is the same at every size: 24, 32, 40, and a new 56 px for the kid's empty chat. Smaller sizes have fewer lines rather than shrunken ones.
   - Checked at real size in the phone shots: it reads as a deliberate little screen in light and dark, and it doesn't look like the round person avatars.
   - When she can't answer, the light goes out: an unlit grey screen.
2. **Mono only on glass.** Vera's times and receipts are back in Atkinson. The mono stays only on the pill, the panes and the radar labels. Dropping the receipt's decorative tile on the phone stopped the name wrapping into ragged lines.
3. **Dark mode keeps its hierarchy.** The Ask card is deep-green glass with the brightest edge on the page, and its text box has a real edge (it was 1.2:1). The family's buttons are green again, links are a lighter green, and Vera's bubbles don't glow.
4. **The radar earns its place.**
   - A new scale gives the first half hour more than half the radius.
   - Nearby ideas that share a direction are fanned slightly apart, and each dot has its own number.
   - The ring labels are readable.
   - On desktop the cards start right under the filters and the radar comes after the first row. On the phone it comes after the list.
5. **The calendar shows who without relying on colour.** A plan for several people is grey with each person's face, and a one-person plan carries their initial. The phone month shows initials, the house for Everyone, or a hollow ring for past plans, and Plans has a one-line key.
6. **One figure style for money and clock times.** Every amount and time uses Fraunces digits, so "$0.00 of your $2.00" has one kind of zero. I built a proportional cut for use inside sentences, because the first version left "1 pm" with a visible gap. `type.html` shows the choice and the alternative I tried (an Atkinson zero with its slash removed).
7. **Accessibility.**
   - The phone starters and Edit links have their names back.
   - The focus ring is phosphor on glass.
   - The cursor and the pill stop blinking within five seconds.
   - Type sizes are in rem.
   - The Status figures stack at 320 px.
   - Icon buttons have firmer edges, and the disabled arrow is dashed.
   - Page language is `en-GB`, matching the standard's British spelling.
8. **Small things.**
   - Idea titles are bold Atkinson on every page.
   - Maya is now raspberry, well away from the "late" red. Slot 8 changed from a magenta that couldn't be told apart from Alex's purple to cocoa.
   - The surprise tag reads just "Surprise" in narrow tiles.
   - The kid's empty chat has one filled action.
   - The phone "Ready" pill is centred with the logo.

**Declined**
- **Removing the page refresh while a reply is pending (with scripting off).** The access lens asked for this, but it isn't in BRAND-2's list and it's the recorded behaviour, so the back-off and the "Check for her answer" link stay.
- **A green Send on the Ask card.** It stays sun yellow because the style lens asked to protect it.
- **A focus specimen sheet, spot illustrations and a print style.** These were review suggestions, not BRAND-2 items.
- **Some layout issues from earlier stages that the reviewers saw again** (Status tiles, history rows, the Quick idea placeholder, the kid's to-do row, tight spacing in small headings). They're listed in CHANGES.md for a later pass.
- **The 1000–1180 px width on Ideas.** Cards are two across there, so the radar follows a row and a half; I accepted that rather than add another breakpoint.

STANDARD.md now covers the redrawn sign, the glass-only mono, the dark-mode rules, the radar and calendar rules, the new accessibility rules, and every contrast pair recomputed. CHANGES.md and `type.html` are updated too.

Files are in the project folder:
- `STANDARD.md`
- `CHANGES.md`
- `type.html`
- `reply-stage6.md`
- `fonts/fraunces-text-figures-regular.woff2`
- `fonts/fraunces-text-figures-bold.woff2`
