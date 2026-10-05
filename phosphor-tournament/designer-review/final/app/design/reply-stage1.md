**Stage 1 done: Kitchen Table, rebuilt as a system.**

What changed most:
- **The phone has its own layout.** A fixed bottom tab bar; lists start in the first screen; filters and form options are folded into `<details>`; Plans opens on the list, with month days as labelled links. Chat is a full-screen room that opens at the newest message with no script, with the box pinned.
- **`style.css` is rebuilt on tokens and named components.** Radius, spacing and type scales; one item row, one to-do row (with a compact variant), one four-tone banner, one composer, and one state-tag vocabulary. The contrast fixes are in, dark mode is warm, `forced-colors` borders are added, and there are no inline styles or scripts.
- **Numbers are in Fraunces tabular figures everywhere.** Google's Fraunces has no `tnum`, so I generated a digits-only Fraunces with equal-width figures and listed it first in the font stacks. All fonts are self-hosted (about 75 KB).
- **One health state per area**, worded the same on Status, Settings, Ideas and Home. Status leads with money in words, and the model table is folded away. Reminders are truthful: disabled with the reason while Telegram isn't connected.
- **Surprises are tagged in parents' views**, the kids' chat privacy line shows at every width, and the composer says "Writing as Sam · Not you? Sign out".

Declined:
- Drawing Vera as a character (already decided).
- Removing the red late rule on To do: it's kept as a thin rule plus text, because most lenses protect it.
- A per-item "Hide from…" control: a tag is enough while the app hides gifts automatically.
- A no-default writer picker: it only applies before the first password, so it goes with stage-2 sign-in.

I changed three bits of sample data so the pages agree with each other; they are listed in `CHANGES.md`.

Unfinished:
- The More page, Family and the kid pages (stage 2).
- All error, pending and empty states (stage 3).
- Dark mode checked only on Home, Chat and To do.
- In full-page phone shots the fixed tab bar sits at the 844 px fold, where it is on a real phone.
- The sprite is inlined per page because `file://` blocks external `<use>`; `icons.svg` is the file the app should reference.
