# Stage 13: the family's decisions

The family answered the open questions in HANDOFF §9. Fold every answer into the design, HANDOFF.md
and STYLE-draft.md, re-render what changes, and remove each answered question from §9.

1. **Vera's box in the paper looks** (Rail, Ink, Enamel, Fjord, Home Computer): keep it as a plain
   card. No change.
2. **Colour blindness:** "Not concerned about colour blindness." Drop the colour-blind separation
   of the eight people (and of late red against them) as a floor: remove it from the looks check
   and from the contract, and drop the recorded exceptions for Kitchen Table and Home Computer.
   Keep every contrast floor (text, controls, focus, avatar letters), and keep colour never the
   only cue (names and initials stay beside the colours), since that costs nothing.
3. **Home Computer's night red:** no change, same reason.
4. **Kitchen Table becomes the default** when the new layout ships, for every browser that hasn't
   chosen another look. Add the line for the release note.
5. **Looks follow the person:** "Each person should choose their own theme and it follows them on
   all devices." So the choice (look and day/night mode) is stored with the member, not only in
   the browser:
   - a member column (or two) in the next migration, `0037`; the Look page writes it for whoever is
     signed in, kids included, through `familydb/family.py` (the door member changes already go
     through; the web tests that walk the AST name what each module may call, so say the new line);
   - the cookie stays only for pages before anyone signs in (the sign-in page) and is set from the
     member's choice when they sign in; signing in on a new device brings their look with it;
   - no household default is needed now (each person picks; Kitchen Table until they do).
   Update the Look page mockups (`look.html`, `look-kid.html`) to say it follows them everywhere,
   and the account corner and STYLE-draft accordingly.
6. **Status is for every grown-up** (parents too, not only admins), as the app has it. Kids still
   never see it: they never see costs, models or how it works, which is a standing family decision.
   Update the navigation in the mockups for a parent who isn't an admin.
7. **Name whom a present is hidden from:** "Hidden from Maya", not "hidden from the kids". A
   present records the people it's hidden from (by default the person it's for, which the app's
   `gifts_for` already knows); the label names them; it's hidden from exactly those people. Say
   the smallest data change, and which family-decision text in `docs/DESIGN.md` §16 this updates.
8. **To-do edits:** your call. Decide between the to-do's own Edit page and the fold on the row,
   say why in one line, and make the mockups and handoff match.
9. **"Set by Alex" on a kid's to-do:** yes. Record who set each to-do from now on (a column in the
   same `0037` migration), shown on the kid's to-dos.
10. **"Installer" in setup:** your call; earlier the family wanted the word gone. Decide, and list
    the wording change.

Re-render, look, fix. Reply with what changed, briefly.
