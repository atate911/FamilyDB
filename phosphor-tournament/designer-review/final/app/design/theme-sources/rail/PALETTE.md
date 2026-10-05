# Rail yellow

**The idea:** like good station signage, a deep rail-blue panel and a crisp light page with blue-black ink, with one signal yellow, always a solid plate under dark letters, marking what you act on next.

## The palette

| Token | Light / dark | Job |
|---|---|---|
| `--paper`, `--ink` | #F5F6F8, #0E1726 / #0D1420, #EEF1F6 | page, ink |
| `--band` | #0B2C69 / #13336F | panel, phone top bar |
| `--signal` | #FFC917 / #FFD23A | today, Leave by, you are here |
| `--alert` | #B42318 / #FF8B74 | late, the only red |
| `--warn` | #A1430B / #FFA766 | setup, needs a look: copper |
| `--ok`, `--vera` | #17703F, #0A6A4B / phosphor | done; Vera |
| `--link`, `--primary` | #163F8E, #1747A3 / #A9C3FF | links, primary button |
| p1 Sam, cobalt | #256FC8, white letter | night stripe #7888D1 |
| p2 Alex, violet | #532CA8, white | #C472FF |
| p3 Maya, plum | #935987, white | #B587AC |
| p4 Theo, tangerine | #EF730B, ink; stripe #D56400 | #E88E33 |
| p5 petrol | #2A595B, white | #B2D9D8 |
| p6 sky | #81BAE6, ink; stripe #4F8AB4 | #8FBCE3 |
| p7 sand | #B99F6C, ink; stripe #977E4D | #F0C584 |
| p8 chestnut | #593721, white | #C79373 |

Vera's glass and phosphor are unchanged. **Yellow and amber** have different jobs and forms: yellow is only a filled plate; warnings are copper with ⚠ on a peach panel.

## Checks

`python3 _kit/palette-check.py` measures the tokens: text passes AA and edges 3:1 in both themes; the weakest avatar letter is 5.0:1. Closest pair under simulation (CIEDE2000, protan / deutan / tritan):

- avatars: 12.5 / 12.1 / 15.8
- stripes by day: 9.2 / 10.9 / 7.0
- stripes at night: 6.7 / 6.8 (cobalt, violet) / 7.7

## Where it is weaker

- At night, cobalt and violet stripes are closest for red–green colour-blindness; names are beside them.
- Tangerine and copper are related hues; warnings always carry ⚠ and words.
- Sky, sand and tangerine avatars fade at their edges on white; the letter carries them.
- White and ink letters make avatars less uniform.
