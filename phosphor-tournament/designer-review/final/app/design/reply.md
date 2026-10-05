**Kitchen Table**: FamilyDB should feel like the family's kitchen table. Vera is the first thing you can talk to, and everything else is a short pile of plain-language cards you can take in at a glance.

Unfinished / known issues:
- Google Fonts load unreliably through this sandbox's network proxy (ERR_TOO_MANY_RETRIES). On some render runs, a few shots fall back to system fonts. The markup and CSS are the same either way; a re-render usually picks the fonts up.
- Only Home and Chat were checked at 390 px. The other pages have phone styles, and the renderer reports no sideways scrolling on any page, but I didn't see them as phone screenshots. On the phone, Plans shrinks events to coloured bars; it relies on the "Coming up" list below the calendar for the details.
- The demo data says the hike is on "Saturday" in the chat but on Thu 1 Oct in Plans. I kept both as given.
- The kid's view and the Restaurants tab are described in DESIGN.md but not drawn.
