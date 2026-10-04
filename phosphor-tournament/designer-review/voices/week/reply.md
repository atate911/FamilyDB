The fourth round is called **Week at a Glance**. Every page is rendered light and dark, desktop and phone, into `shots/` (96 shots). All fonts loaded, no page scrolls sideways at 390 or 1280 px, and there are no inline styles or scripts.

**Voice:** the family's week, printed big: seven days across, today in solid ink, everyone in their own pen.

- **Type:** Archivo at three widths, with Atkinson kept for everything people read. Squeezed narrow for the big day numbers, money, ranks and drive times; slightly narrow and heavy for headings; opened wide for small capital labels like weekdays. It's one 86 KB file. Bricolage is gone, and `type.html` is rewritten for the new type.
- **Home:** leads with the next seven days, today first as a solid ink column and the weekend wider. The next plan is written out in full on its own day, and the greeting sits beside Ask Vera. The sidebar is now a masthead across the top, so the week gets the full width.
- **Kid's Home:** it's her week, with her to-do on the day it's due.
- **Phone:** the week turns on its side, one row per day. Tomorrow's plan title shows above the tab bar.
- **To do:** each row leads with its date (red when late), and the list comes first with the add form beside it.
- **Ideas:** drive time is a big figure on each card.
- **Plans:** today is an ink cell and the weekend columns are wider.
- **Chat:** each day starts with its big day number.
- **Wishes:** ranks are big numbers, and rank 1 is solid in the kid's colour.
- **Colour:** today is now ink, so green means only Vera.
- **Docs:** `DIRECTION.md` is 445 words. `STANDARD.md` §1 is rewritten, and the components, phone, accessibility and brand sections are updated with recomputed contrast. Everything passes AA, and controls pass 3:1.

**Unfinished or untested:**
- The render kit only shoots at 390 and 1280 px, so I didn't check 320 px, 200 % zoom, or 820–1180 px, where the masthead should wrap to three rows.
- The kid's My to-dos page didn't get the date column.
- The states sheets pick up the voice through the stylesheet only; their markup is unchanged.
- I added one new line on the kid's Home: "Your to-dos sit on the day they're due."
- An empty Saturday is a big black column. It's honest, but loud, and it softens to grey at night.
- Home's next seven days roll from today, while Plans keeps the Mon–Sun week. That's deliberate, but the family might want one or the other.
