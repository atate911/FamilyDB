**Afterglow**

**Idea:** a calm, dark family screen with the glow of an old green terminal: what Vera keeps shines soft green, and only what needs a person lights up amber.

All seven pages, `style.css` and `DESIGN.md` (exactly 400 words) are in the folder, and `shots/` holds the final renders. I did three rounds of rendering and fixing. Every page renders at 1280 px and 390 px with no sideways scrolling.

**What's unfinished:**
- **Fonts sometimes fail to load during rendering.** Every render printed `net::ERR_TOO_MANY_RETRIES` for some Google Fonts files, on different pages each time. The proxy status and a direct fetch both looked fine. When it happens, that page falls back to system fonts, so your own render may differ from mine. The final set of shots was taken after the last small change to the Ideas radar, and I didn't open those last images.
- **Only Home and Chat were checked at phone width.** The render script only shoots those two. The other five have phone styles (stacked cards, compact calendar, single-column to-dos) that I never looked at.
- **Two radar labels are tight.** On the Ideas page, the "30 min" ring label sits close to the short-drive dots. The four ideas that are about 20 minutes south have been spread apart a little so their dots don't overlap, so their exact directions are approximate.
- **The brief's dates disagree.** In the chat, Vera puts the Silver Falls hike on "Saturday 10:00", but the plan data says Thursday 1 Oct. I kept both as given.
- **Some things I added aren't in the brief:**
  - The "Leave by 12:30" line.
  - The "Loved it / OK / Not again" buttons for asking how a plan went.
  - Treating the Lego set and board game night as the most recently added ideas.
  - The "Family planning" line under the logo.
- **There is no light theme**, because the phosphor look depends on a dark screen.
- **The pages are generated.** I built them with a small script, `_src/build.py`, so the navigation stays the same everywhere; the HTML files themselves stand alone. The kid view is only described (kids don't see Status or Settings), not drawn.
