# Kitchen Table, the whole app

The family's decision: "Ok, you sold me on the Kitchen Table (final) idea. Let's flesh this out and prepare to make it into a real interface for the app." Then: "I'm going to set up an option for themes with different colour schemes... let's consider how to handle that and what needs to get built into it."

The designer of `../design` continued in three stages (`design/STAGE8.md`, `STAGE9.md`, `STAGE10.md`, with replies `design/reply-stage*.md`), working from copies of the app's real templates and web modules:

- **Stage 8:** the family's notes from the exploring rounds (no starter buttons on Ask Vera, a small greeting, the phosphor echo kept) and every missing everyday page.
- **Stage 9:** the settings home and its nine sections, the setup flow, and where a theme is chosen (Settings › General for the family, "You" for each person).
- **Stage 10:** `HANDOFF.md` (page map, components to macros, stylesheet, rules kept, words, thirteen pull requests in order, tests that will change, themes, open questions) and `STYLE-draft.md`, the new `docs/STYLE.md`. The stylesheet is split so every colour lives in `design/themes/<name>.css`; Rail yellow and Midnight are ported only to prove the theme contract, and `design/_kit/theme-check.py` checks every theme.

`showcase/index.html` shows all 57 pages (desktop, phone, day, night), the themes proof, the open questions and the handoff.

## Stages 11–13

- **Stage 11:** fitted to the looks the engineers built (`themes.css`, `looks.py`, the Look page): Kitchen Table is one `[data-theme="kitchen"]` block in the built token names, and the built looks recolour it unchanged.
- **Stage 12:** **Afterglow**, a look over Kitchen Table (green glass, scanlines, glow, VT323 titles) through five effect tokens every look defines; every page rendered in it, day and night. **Motion** in Kitchen Table itself: Vera's sign types itself in on Home and while she writes back, the afterglow flash, the landing glow, resting cursors (`design/motion.html`).
- **Stage 13:** the family's decisions folded in: plain Vera box in paper looks; no colour-blind floor; Kitchen Table the default when it ships; each person's look stored with them (migration `0037`) and following them everywhere; Status for every grown-up; presents name whom they're hidden from; to-dos get their own Edit page; "Set by" recorded on kids' to-dos; "installer" gone.

`showcase/index.html` shows all 62 pages with a Look switch (Kitchen Table or Afterglow), plus motion and the built looks.
