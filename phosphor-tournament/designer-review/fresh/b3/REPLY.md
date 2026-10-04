**Afterglow**: a warm family app that glows like an old green phosphor screen. The terminal is in the light, the type and the `>` prompt, while the reading and the words stay modern and friendly.

Unfinished or known issues:
- Fonts: the render proxy sometimes fails to load a Google Fonts file. When that happens a page falls back to plain monospace or sans. The shots in `shots/` are taken from runs where every page loaded its fonts, but a fresh `./_kit/render.sh .` may show a fallback font on one or two pages.
- "Send where I am" is drawn as a checkbox. Sending a real location needs a few lines of JavaScript, which the brief allows.
- Only the Family chat has messages. Maya's and Theo's chats are shown as links but not drawn. The kids' view (no Settings or Status, their own to-dos and wishes) is only described, not drawn.
- The 30-day cost bars on Status are invented, but they add up to the real totals: 6 calls, $1.26.
- The data has one mismatch I kept as written: the chat says the hike is "Saturday 10:00", while the plan is on Thu 1 Oct.
- Phone shots exist only for Home and Chat. The other pages have phone CSS but I didn't look at them at 390 px.
