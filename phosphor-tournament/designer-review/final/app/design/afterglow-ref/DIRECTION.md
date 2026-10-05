# Afterglow

**The idea:** FamilyDB as a calm green-phosphor screen, day and night, where Vera's things glow and the family's things sit on the glass in their own colours.

## What changed from Kitchen Table, and why

- **The glass is the page.** Charcoal glass with a faint green tint (`#0A100E`) is the page whatever the system scheme, with one soft afterglow at the top and no scanlines. Cards are a lighter glass with a faint sheen.
- **Glow means Vera or live.** Phosphor and glow appear only on the Ask card's rim, the lit **Send** (it replaces the yellow), Vera's screen, the busy pill, today's date and the wordmark cursor. The family's links are soft mint and their primary button is a pale plate, never phosphor.
- **People are lit pastels.** Avatars, dots and calendar bars use each person's light colour with dark letters, so "mine" is the brightest thing on screen after Vera's green.
- **One pixel face, only for big moments.** VT323 sets page titles (56 px, 44 on the phone), the wordmark, and figures that stand alone: date-tile days, money and the Status figures. Nothing in it is under 28 px. Fraunces and the mono are gone, so card titles, sentences, pills and pane lines are all Atkinson Hyperlegible.
- **The signals are unchanged.** Coral means only late or broken, and amber means set this up or needs a look. Every pair is measured (STANDARD §7).
- **A light page for those who need it.** `<html data-theme="light">` gives pale green-grey paper with deep-green ink. Vera's glass stays dark, so the direction still reads. See `shots/light-theme/`.

Layout, components, words, roles, states and phone rules are unchanged; only the type sheet's descriptions and one states-sheet sentence were reworded.

## Where it is weaker

- **The light page has no switch.** It needs a per-person setting that doesn't exist yet. Until one is added, nobody can choose it.
- **The pixel face is a taste call.** Long titles wrap sooner, and some readers will find even a title harder going than Fraunces.
- **Dark by default.** On a bright phone outdoors, or for readers with astigmatism, it is harder to read than cream paper.
- **Less warmth.** Without the paper and the serif, the warmth comes only from the people's colours and the cream-tinted ink.
- **The setup card** reads as a heavy amber-brown block.
