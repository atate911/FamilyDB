I've folded all ten of the family's answers into the design, HANDOFF.md, STYLE-draft.md and STANDARD.md, and re-rendered the pages that changed.

1. **Vera's box in the paper looks:** no change; the docs now say the family chose a plain card.
2. **Colour blindness:**
   - **Removed:** the people's colour-blind floor, from the looks check, the docs and the planned `test_look.py` additions. The recorded exceptions for Kitchen Table and Home Computer are gone too.
   - **Kept:** every contrast floor, avatar letters included, and names or initials stay beside every colour.
   - All nine looks pass.
3. **Home Computer's night red:** no change.
4. **Kitchen Table as default:** it becomes the default when the new layout ships, for anyone who hasn't chosen a look. Anyone who chose one earlier keeps it. The release-note line is in HANDOFF §8.2.
5. **Looks follow the person:**
   - **Stored:** with the member, in a new `members.look` column in migration `0037`, written by the Look page through `familydb/family.py`, kids included.
   - **New AST-test line:** `web/looks.py` may call `familydb.family.choose_look`.
   - **The cookie** now only covers the pages before sign-in, and is set from the person's look when they sign in. While the family still shares one password, the look stays per browser.
   - **No household default.**
   - **Wording:** the Look pages and the phone menu now say the look follows you.
6. **Status for every grown-up:** two new mockups, `home-parent.html` and `more-parent.html`, show Alex as a parent, with Status alone under "Behind the scenes" and no setup card. Kids still never see it.
7. **"Hidden from Maya":**
   - **Data change:** one column, `ideas.hidden_from`, in `0037`, filled from `gifts_for`.
   - **Who it hides from:** exactly those people, whatever their role. So Maya's Home now shows Theo's Lego set, tagged "Hidden from Theo".
   - **DESIGN.md §16:** I couldn't read `docs/DESIGN.md`, because it isn't in this folder. HANDOFF §1 item 9 gives the replacement for its "hidden from the kids" decision.
8. **To-do edits:** I chose the to-do's own Edit page over the fold. Seven fields unfolding inside a list lose your place on a phone; a page is one short form with a way back.
9. **"Set by Alex":** a new `tasks.created_by_member_id` column in the same `0037` migration, recorded from now on and shown on the kid's to-dos.
10. **"Installer":** I dropped it. It now reads "the password FamilyDB started with" in four strings, listed in HANDOFF §1 item 19.

Fixes from looking at the renders:
- The "Hidden from Theo" tag ran past its box in a narrow idea tile (it did on the admin's Home already); it now wraps inside.
- The palette sheets now fit a phone.

HANDOFF §9 is down to five open questions: whether a parent opening Settings gets the friendly page or the plain refusal, and the four Afterglow and motion questions from stage 12.

The reply is in `reply-stage13.md`.
anged page and the two new ones, by day and night, desktop and phone, in Kitchen Table and in Afterglow, plus the palette sheets. I looked at each and fixed the tag.
