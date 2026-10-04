**Name:** Kitchen Table

**Idea:** FamilyDB is the family's kitchen table: Vera sits at it, and everything the family keeps track of is laid out on warm paper cards, in plain words, with one bright colour for "this needs you".

**Known unfinished:**
- Google Fonts loads unreliably through this machine's proxy, often failing on one font file. So some renders fall back to system fonts. The shots in `shots/` come from runs where every font loaded.
- Only Home and Chat were rendered at phone width. The other five pages have phone layouts in the CSS (stacked calendar agenda, wrapped to-do rows, stacked settings), but I haven't looked at them.
- The kids' view is described, not drawn. Every page is shown signed in as Sam.
- Linked pages (idea pages, setup steps, list views, edit pages) don't exist, so those links go nowhere.
- The brief disagrees with itself on the hike's date: the chat says Saturday, the plan says Thu 1 Oct. Both are shown as given.
- The 30-day spending chart spreads the brief's 6 calls / $1.26 across days I made up.
- `_build.py` is the generator for the static pages. Running it again overwrites the seven HTML files.
