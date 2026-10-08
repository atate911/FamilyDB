# If you add a page (not served)

Files and folders beginning with an underscore are never served or searched.

1. Write the page as `slug.md`, or `slug/index.md` for a section, under `src/familydb/wiki/`.
2. Add it to `_nav.json` with its title, audience (`grownups` or `admin`), depth (`overview`, `howto` or `deep`) and at most three `see_also` pages, never a hub.
3. Make the page's H1 equal its nav title, character for character.
4. Link other pages as `/wiki/slug#anchor`. Headings give the anchors; python-markdown anchors H2 and H3 only.
5. End a concept, deep or reference page with one `Developer docs:` line; how-to pages and hubs have none.
6. Run `uv run pytest tests/test_wiki.py -q`: it fails if the nav and the files disagree, a link or anchor does not resolve, or a page carries inline script or style.
