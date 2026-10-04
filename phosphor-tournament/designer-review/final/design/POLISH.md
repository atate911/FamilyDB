# Stage 4: the polish pass

The final design was checked twice.

- **Four blind judges** compared the original Kitchen Table with your final, as two unnamed designs on the same seven pages, in both orders. All four chose the final: 8, 8, 8 and 8 against 6.5, 6, 6 and 6. Their reviews are `reviews-final/blind-j*.md` (a comment at the top of each says which letter is yours).
- **The same thirteen lenses** reviewed all twenty pages. Their mean rose from 6.7 to 7.4, and five now say build it as it is. Their reviews are `reviews-final/*.md`.

What is left is a short pass, not a redesign. Do the items below in order, then render and look at everything again (light and dark, desktop and phone). Update `CHANGES.md` and `STANDARD.md`. Where you disagree with a reviewer, say why in `CHANGES.md`.

## Must fix (raised by several, or a blocker)

1. **Person colours by slot, not by name** (system, engineer: blockers). Replace `--sam…--theo`, `.av--sam`, `.msg--maya`, `.ev--theo`, `.d-maya` and the like with eight numbered slots (`--p1…--p8`, `.p1…p8`) that the server assigns per member. Keep today's four colours as slots 1 to 4, and add four more that pass contrast in light and dark. "Everyone" stays neutral.
2. **The phone opens on what people came for** (phone, generalist, parent, interaction, usability, skeptic, and three blind judges). On phone Home, shrink Ask Vera to one row (box and Send; starters fold away or move under it) so the next plan and anything late show on the first screen. On phone To do and Ideas, the list comes before the tools, as your standard already says. Keep the phone Home shorter: cap each card and link to the rest.
3. **Ideas in the parent's phone tab bar** (three blind judges, usability, phone, interaction). Find a tab bar that holds Home, Chat, Ideas, Plans and To do. One way is to move More's contents into the account menu behind the avatar in the top bar (Wishes, What Vera knows, Status, Settings, Family, Sign out). Decide the kid's tab bar the same way; the kid lens wants Plans reachable.
4. **Phone Plans**: the Month/List switch sits right under the month header, and the grid follows it (blind judges, interaction, phone).
5. **The calendar uses colour, and handles real months** (all four blind judges, style, skeptic, engineer). Events take their person slot's colour clearly, not as a hairline on grey. A plan that spans days draws as one bar across them, including across a week boundary. Fix `.span2`, which means two things. "Today" must not look like a focus ring. Draw one real-feeling month: a five-day trip that crosses a weekend, and a busy Saturday.
6. **One meaning per signal** (style, generalist, parent, and three blind judges). Yellow only for Send and "set this up"; mint only for "all good"; "Off" and "for your information" get their own neutral look; dashed lines mean one thing; "Needs a look" and "Could be better" must be easy to tell apart. Cut the "set this up" warnings to one place per page. Make the sidebar badges quiet, except the ones that need action now (late, to decide).
7. **Numbers** (type, generalist, style, engineer). Take the custom "Fraunces Figures" out of the body font stack: words, digits and punctuation in running text are Atkinson. Use the serif tabular figures only where numbers stand alone or line up (date tiles, money, counts, time columns). If Atkinson's slashed zero still reads badly in running times ("10 am"), check whether Atkinson Hyperlegible Next has an unslashed-zero alternate you can switch on, and say what you chose.
8. **Accessibility failures** (access): the fixed tab bar must not hide the focused control (`scroll-padding-bottom`); respect the safe-area inset at the bottom; let the chat room fall back to normal page scroll on short screens; show the selected tab and segment by more than a faint fill; fix dark mode's today marker and slot colours below 3:1; bring every target on a kid's page to 44 px; move hints out of `<label>` into `aria-describedby`.
9. **A kid's read-only to-do must not look tickable** (usability, kid). Use a marker that is clearly not a checkbox. Put her own things at the top of her phone Home. Warn her gently before her messages run out (for example at 5 left).
10. **Words** (copy). The pill for "Vera is ready" must not say "answering"; keep "answering" for when she is writing back. Replace "Mark as been". Use one set of words for a wish's answer, the same for kids and parents. An idea is never a "thought": rename "Save a thought". Match the app's own spelling (it is written in British English) and keep each button's words the same everywhere.
11. **Forms and controls** (usability, engineer, interaction, parent). The quick add shows "Who" as visible pills, so a to-do is never assigned to the wrong person by default. Only one sort control is submitted on Ideas, and the button that applies filters comes after them. A starter that sends looks different from one that fills the box. Hide "Share where I am" on a kid's pages. Remove `white-space: nowrap` from buttons and tags that can wrap.
12. **Draw what's still missing**: the to-do edit form (todo-edit.html), and Vera's longest message (the weekend suggestions, with a short list, times and links) in the family chat.

## Leave alone

- Vera stays undrawn. The style lens asks again for a character, but that was decided.
- Whether kids may tick their own to-dos, whether parents get a private chat with Vera for surprises, and a kid sharing location are family decisions. Note them in `CHANGES.md` under "For the family to decide"; don't design them in.
- The chat's refresh while a reply is pending is how the app works. Keep it, with a visible "Check for her answer" link beside it, and record the accessibility review's concern in `STANDARD.md` for the engineer.

When it's done, reply with what changed, what you declined and why, and anything unfinished.
