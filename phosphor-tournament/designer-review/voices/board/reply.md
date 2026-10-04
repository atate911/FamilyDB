**The Board.** The voice: the family's day set like a station departure board, showing what leaves next, when to go and whose it is, readable from across the kitchen.

Every page now renders light and dark, desktop and phone, into `shots/`: 96 shots, all with fonts loaded and nothing wider than the screen. I looked at the shots and fixed what I found, then rendered everything again.

**Type:** Barlow Condensed (600 and 700) is the board face: times, dates, drive and due figures, money, ranks, column heads and navigation. Barlow Semi Condensed 700 sets headings and the wordmark. Atkinson Hyperlegible stays for every sentence and every title a kid reads. Barlow comes from California's highway and rail signs, and its narrow figures line up in columns. Everything is mixed case, as on road signs; only the small column heads and weekday labels are capitals. The new fonts add 60 KB.

**Layout changes:**
- **Home** leads with a full-width Next up board. "Leave by 12:30 pm" is the biggest figure on the page.
- **Route stripes:** each plan row has a bar split into the colours of the people going.
- **To do:** due dates and "6 days late" have their own right-hand column, and Overdue gets its own board.
- **Plans:** Coming up now sits at the top; the month comes after, styled as a timetable.
- **Ideas:** a destinations board, with drive time as a figure and an arrow pointing the way.
- **Wishes:** the ranks are numbered plates joined by the kid's own colour.

Everything else (the sidebar as a navy band, an ink rule along the top of every panel, square corners) carries through to the other pages.

`DIRECTION.md` (430 words) and `STANDARD.md` are written. In STANDARD.md I rewrote sections 1 (tokens, type, spacing, moments) and 9 (brand), updated the component table and phone rules, and recomputed the contrast table for the new colours.

**Unfinished or weaker:**
- **Ask Vera moved down** on Home, below the board and the to-dos, because Chat has its own tab. That is a real reordering the family should agree to.
- **Ask Vera stands out less.** It is now navy like the rest of the structure; only its green top edge and green Send button set it apart.
- **Chat changed least.** It gets a navy header strip, coloured message edges and new day dividers, but its structure is the same.
- **The wish-list line** only bridges the gaps between cards, not one continuous line.
- I **deleted the Bricolage font files** from `fonts/` because nothing uses them now.
- `style.css` still has one hard-coded `#FFFFFF` outside the colour tokens, on the glass pane's button hover. It was there before.
- The new Edit buttons on the To do lists show only a pencil icon. Their name stays readable to screen readers ("Edit Call the dentist about Theo"), and they have the bordered edge the standard requires for icon-only buttons.
