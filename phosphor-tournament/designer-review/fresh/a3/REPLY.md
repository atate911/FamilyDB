The design is called **Kitchen Table**.

**Idea:** the website is the family's kitchen table on a Saturday morning: Vera is there to talk to, today's stuff is on top, and everything else is one tap away.

The seven pages, `style.css` and `DESIGN.md` (393 words) are in the folder, and all nine screenshots are rendered. No page scrolls sideways at 1280 or 390 px. I did four rounds of looking and fixing:
- **Phone tab bar:** it showed up in the middle of the full-page phone shots. It's now a sticky row of five tabs at the top.
- **Plans:** the calendar was too cramped, so tomorrow's plan and "How did it go?" moved below it. The rating faces are now drawn icons instead of emoji.
- **Status:** the chart labels were enlarged.
- **To do:** the quick-add box now has its own line.
- **Home:** an overflowing drive-time label was fixed, and the skate drawing no longer overlaps the buttons on a phone.

What's unfinished or worth knowing:
- **Fonts in the shots:** the sandbox's network keeps failing some Google Fonts downloads. In each render, a few pages fall back to the backup fonts (Georgia and the system sans) instead of Fraunces and Atkinson Hyperlegible. I tried more than ten renders and none loaded every font on every page. In the final set, `home`, `plans`, `home-phone` and `chat-phone` loaded everything. The others may show the fallbacks in places. The layouts hold either way.
- **Invented details:** the per-day split in the 30-day cost chart is made up (12, 19 and 27 Sep and 1 Oct). It adds up to the given 6 calls and $1.26. Dates in the to-do quick add and the 10:00 time in "How did it go?" are placeholders too.
- **Slashed zeros:** Atkinson Hyperlegible draws zeros with a slash (10:00). That's how the font is designed, not a bug.
- **Not drawn:** the parent-versus-kid differences appear only in wording: the Settings page says only parents see it, and the kids are listed as "no settings". The phone "more" menu is a `<details>` menu, so it doesn't appear open in any shot.
- **Extra folder:** `_src/build.py`, the script that generates the pages, is in the folder. It's not part of the deliverable and can be deleted.
