The kid pages now follow the app's rules, and stage 3 is done. All 20 pages render at desktop and phone width, in light and dark: 80 shots, all with fonts loaded, and nothing scrolls sideways at 390 px. No page has an inline style or a script.

**Kid corrections**
- **`todo-kid.html`:** Maya sees only her own to-dos, and can't change them. There's one to-do a parent set for her, "Pack your swim bag", due Thu 8 Oct, set by Alex. Its row has a plain icon instead of a tick button, so nothing looks tappable.
- **How it gets ticked off:** a banner says kindly, "Sam or Alex tick these off. When you've done one, tell Vera… and she'll let them know."
- **Removed for kids:** the quick add, Edit, the "For everyone" group, and the rating faces on her Home. "Moving it? Ask a parent" stays. Her Chat starter "Remind me to pack my skates", which implied she could add to-dos, is now "Can you help me with…".
- **Noted in `CHANGES.md`:** whether kids may tick their own to-dos or rate plans is a family decision, not a design one. If the family allows it later, the existing to-do row and faces drop back in with no new component.

**States, on three sheets**
- **`states.html`:**
  - The daily limit reached, on the header pill, Home's Ask card, the chat box and Status.
  - Maya's own version, with no money talk: "You've sent all 20 of today's messages" and "Vera is resting until tomorrow".
  - Vera can't answer: parents see which company is down; kids are told to try a bit later.
  - A reply on its way, and a message that failed.
- **`states-actions.html`:**
  - The green banner with Undo, after ticking a to-do and after answering a wish.
  - Form errors on Add an idea and on the quick add: a summary at the top that links to each field, plus a message tied to each field.
- **`states-content.html`:** the first empty day for a new family, a search with no results, a busy day with "+2 more", and long titles.

**Dark mode** is checked on every page at both widths. Contrast is recomputed from the colour values in both themes: every text pair is 4.8:1 or better, and control edges 3.8:1 or better.

**`STANDARD.md`** has:
- the colour, type and spacing values, light and dark;
- every component with its variants and when to use it;
- the word table, and a table of what each role can see and do;
- the phone rules and the states;
- the accessibility checks with the real contrast numbers;
- the engineer notes: Jinja macros, the content security policy, what must work with scripting off, and what the four optional small scripts do.

**Invented sample data:** the states sheets use made-up times, four plans on Sat 10 Oct, the long titles and the "pizza" search, just to show each state.

**Not done yet**
- **Kid pages:** her More page and the Family page are linked but not drawn.
- **Wish forms:** the error states for answering and ranking wishes aren't drawn; they would use the same pattern as the other forms.

**One slip to report:** at one point I sent a render log to the folder above mine. I stopped that run, deleted the file (it held only render lines) and re-ran with the log in my scratchpad.

The same summary is in `reply-stage3.md`.
