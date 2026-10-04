The new direction is called **House Log**. Voice: FamilyDB is the family's logbook, where Vera keeps the ruling (dates, times and numbers in a mono margin) and everybody writes the lines, in plain words and their own colour.

Every page is redone in this folder and rendered into `shots/`: light and dark, desktop and phone. I looked at all of them and fixed what was wrong. The final render had no font failures and no page wider than the phone screen.

- **Type:** Archivo for titles and labels. Condensed and heavy, it makes tall headings that fit on a short line; wide and in capitals, it does the running heads and labels. Martian Mono, narrow, is the margin for every date, time and number. Atkinson stays for every word people read. The two new fonts add 128 KB (limit 220). The old Bricolage and JetBrains Mono files are removed, and `type.html` is rewritten.
- **Layout:**
  - Every list has a margin with the date and time, then the tick, then the words. To-do and plan titles line up.
  - Sections are separated by a heavy ink line and a heading, not cards, so more fits on a screen.
  - **Home:** Ask Vera, then Next up and To do as one list, with side notes on the right.
  - **Plans:** Saturday and Sunday are wider, because that's where the family's plans are.
  - **Chat:** reads as a transcript, with who and when in the margin.
  - **Ideas:** a numbered table, so you can compare drive times down one column.
  - **Kids:** Maya's pages are drawn in her colour.
- **Floors:** no inline styles or scripts, one main heading per page, and every text colour pair meets AA in both themes (control edges 3:1 or more). The numbers are in STANDARD.md.
- **Docs:** `DIRECTION.md` is 446 words. `STANDARD.md` has a new layout section and updated colour, type, component, phone, contrast and brand sections.

**Unfinished and weaker:**
- On Home on the phone, the first screen shows the next plan, but the late to-dos start just below it. The lede line still links to them.
- On a 390 px phone the margin takes 68 px, so to-do titles wrap onto more lines than before.
- The Ideas table needs about 1100 px wide. Narrower, it drops columns, and below 1000 px it becomes rows.
- Without boxes the layout leans on thin lines, which can disappear on dim screens.
- I didn't test at 320 px or with forced colours on. The forced-colours rules were updated but not rendered.
- The markup adds a few new class names the engineers will need (listed at the top of STANDARD.md).
