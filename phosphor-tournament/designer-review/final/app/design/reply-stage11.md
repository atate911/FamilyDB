I've fitted the design and the handoff to the looks the engineers built, rather than the other way round. Kitchen Table now uses the built token names, sits in `themes.css` as one look, and the chooser is the built Look page. Every page was rendered again, light and dark, desktop and phone (228 screenshots, no warnings). Home and a kid's Home were also rendered in three of the built looks.

**What changed**
- **Token names:**
  - Where the built set has the same role, I adopted its name, for example `--side` → `--band`, `--alert` → `--red`, `--warn` → `--amber`, `--today-bg` → `--today`.
  - Kitchen Table needs 66 roles the built set lacks: links in the side panel, each meaning's wash, Vera's box and Send button, and a colour for each of the eight people. HANDOFF §8.1 lists them.
  - One `[data-theme]` block works out a value for each of those 66 from every look's own colours, so the six built looks don't have to name them.
  - I compared every page pixel by pixel before and after the rename. Nothing moved except the pages whose content I changed on purpose.
- **Kitchen Table as a look:** it's one `[data-theme="kitchen"]` block with `light-dark()` values, as it would sit in the built `themes.css`.
  - The key is `kitchen` rather than `kitchen-table`, because the built test only finds one-word keys.
  - I recommend making it the default when the new layout ships, and not before. Until then it can go in now as one more look. HANDOFF §8.2 lists what the code must stop assuming once the default is no longer dark only.
- **The built looks on Kitchen Table's layout:**
  - Rail yellow, Midnight and Phosphor read well on Home (`shots/looks/`). Maya's Look page is worn in Fjord, which shows a whole page too.
  - A new checker, `_kit/looks-check.py`, replaces the stage 10 one.
  - Kitchen Table, Phosphor, Rail, Fjord, Ink and Midnight all pass.
  - Enamel and Home Computer each need one more colour (`--on-vera`), because the words on Vera's green fill fall just short of the contrast floor. I've added both.
- **The Look page:**
  - `look.html` is the built per-browser page, drawn with Kitchen Table's components; `look-kid.html` is Maya's copy.
  - The small samples of each look keep the built markup, because `test_look.py` counts them.
  - The stage 9 choosers are gone from Settings › General and from the You page, which is "Your password" again, as in the app.
  - The account corner now reads "Look · Your password · Sign out".
  - A household default and a person's own look across devices are written up as a later step, with what each would need.
- **HANDOFF.md:**
  - §8 is rewritten around the built mechanism.
  - The page map adds `/look`, and the first step in the order of work is "Kitchen Table as a look", which can land now.
  - The tests section says exactly what Kitchen Table changes in `test_look.py`.
- **STYLE-draft.md:** its Themes section becomes "Looks", using the built STYLE.md's facts.

**For the family to decide** (HANDOFF §9):
1. **Vera's box in the paper looks.** Rail, Ink, Enamel, Fjord and Home Computer draw her Ask box as a plain card, not dark green. Keep it that way, or give each of those looks a dark box?
2. **Kitchen Table's people colours fail the colour-blind check in three places** (slots 4, 5 and 7). Every look shows these people until it has its own, so this now affects all of them. Retune those three slots, or accept the known exception?
3. **Home Computer:** at night its late red and its orange button colour sit too close together for one kind of colour blindness. Change its night red, or accept it?
4. **Kitchen Table as the default** when the new layout ships: every browser that hasn't chosen Phosphor switches at once. Is that what the family wants, with a line in the release note?
5. **A household default look, and a person's own look across devices:** wanted, and when?

The rest of §9 carries over from stage 10: whether Status is for parents too, "Hidden from Maya", and others.

STAGE12.md is in the folder, but I haven't touched it. This reply is also saved as `reply-stage11.md`.
