# Dusk: the palette's values, written as OKLCH (lightness, chroma, hue) and printed as hex.
# Run it to see every token's hex; style.css holds the hex values (python3 _kit/dusk-values.py).
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from colourlib import oklch
I = 295  # the dusk hue: indigo-violet; every neutral leans a little toward it
LIGHT = {
  "paper": (.958, .0055, 45), "paper-2": (.922, .008, 40), "card": (1, 0, 0), "field": (1, 0, 0),
  "ink": (.20, .035, I), "ink-2": (.37, .035, I), "ink-3": (.47, .03, I),
  "line": (.85, .012, 320), "line-2": (.77, .016, 310), "edge": (.56, .025, I),
  "band": (.265, .105, 288), "band-2": (.305, .115, 302), "on-band": (.985, .006, 60), "on-band-2": (.84, .045, I),
  "band-line": (.37, .10, 292), "band-hi": (.335, .105, 292),
  "signal": (.80, .135, 58), "signal-2": (.84, .12, 62), "signal-mark": (.64, .155, 50), "signal-ink": (.50, .13, 48),
  "signal-soft": (.95, .028, 62), "signal-line": (.86, .07, 62),
  "focus": (.47, .19, 292),
  "warn": (.47, .095, 75), "warn-soft": (.94, .022, 72), "warn-line": (.82, .06, 72),
  "alert": (.50, .185, 22), "alert-soft": (.945, .022, 20), "alert-line": (.84, .07, 20),
  "alert-plate": (.53, .20, 24),
}
DARK = {
  "paper": (.175, .022, I), "paper-2": (.235, .028, I), "card": (.205, .026, I), "field": (.215, .026, I),
  "ink": (.955, .008, 60), "ink-2": (.85, .02, I), "ink-3": (.73, .025, I),
  "line": (.31, .03, I), "line-2": (.39, .035, I), "edge": (.60, .035, I),
  "band": (.285, .11, 288), "band-2": (.325, .12, 302), "on-band": (.975, .008, 60), "on-band-2": (.84, .045, I),
  "band-line": (.39, .10, 292), "band-hi": (.355, .105, 292),
  "signal": (.82, .125, 60), "signal-2": (.86, .11, 64), "signal-mark": (.78, .135, 58), "signal-ink": (.84, .11, 62),
  "signal-soft": (.25, .045, 50), "signal-line": (.42, .08, 55),
  "focus": (.84, .12, 62),
  "warn": (.84, .11, 82), "warn-soft": (.24, .035, 80), "warn-line": (.42, .06, 80),
  "alert": (.72, .165, 22), "alert-soft": (.25, .05, 20), "alert-line": (.40, .09, 20),
  "alert-plate": (.56, .20, 24),
}
# the eight people, from a sunset sky and its land. base (avatar, under ink letters), mark (stripes, rules, 3:1),
# ink (names, 4.5:1), soft (washes). Night: its own mark, ink and soft; the same base.
PEOPLE = [
  # name            base (avatar)     day mark          day ink           day soft          night mark        night ink         night soft
  ("evening blue", (.63, .15, 266), (.52, .098, 268), (.45, .12, 266), (.94, .025, 266), (.80, .098, 266), (.86, .07, 266), (.27, .06, 266)),
  ("sea",          (.65, .12, 194), (.38, .158, 190), (.40, .08, 192), (.945, .022, 194), (.86, .07, 187), (.87, .07, 190), (.27, .045, 194)),
  ("heather",      (.76, .13, 303), (.38, .092, 309), (.42, .12, 306), (.945, .025, 303), (.68, .099, 303), (.86, .07, 303), (.28, .06, 303)),
  ("sun gold",     (.87, .16, 91),  (.50, .147, 83), (.45, .10, 80),  (.95, .045, 92),  (.89, .159, 97), (.90, .11, 94),  (.27, .045, 88)),
  ("sky",          (.89, .10, 238), (.60, .132, 230), (.45, .10, 234), (.95, .022, 236), (.91, .062, 241), (.90, .05, 238), (.27, .045, 236)),
  ("olive",        (.64, .13, 115), (.38, .153, 111), (.42, .09, 114), (.945, .032, 115), (.64, .160, 120), (.87, .08, 116), (.27, .045, 116)),
  ("dusk cloud",   (.76, .035, 275), (.43, .155, 287), (.44, .07, 282), (.945, .014, 278), (.60, .155, 278), (.86, .045, 278), (.28, .03, 278)),
  ("sandstone",    (.72, .05, 62),  (.38, .045, 51), (.44, .06, 54),  (.945, .018, 60), (.68, .045, 52), (.87, .04, 56), (.27, .025, 56)),
]
EVERYONE = {"day": [(.84, .008, I), (.93, .006, I), (.37, .035, I), (.56, .025, I)],
            "night": [(.42, .02, I), (.24, .025, I), (.85, .02, I), (.73, .025, I)]}

def hexes():
    L = {k: oklch(*v) for k, v in LIGHT.items()}; D = {k: oklch(*v) for k, v in DARK.items()}
    for i, p in enumerate(PEOPLE, 1):
        base, dm, di, ds, nm, ni, ns = (oklch(*x) for x in p[1:])
        L.update({f"p{i}": base, f"p{i}-mark": dm, f"p{i}-ink": di, f"p{i}-soft": ds})
        D.update({f"p{i}": base, f"p{i}-mark": nm, f"p{i}-ink": ni, f"p{i}-soft": ns})
    for th, d in (("day", L), ("night", D)):
        e = [oklch(*x) for x in EVERYONE[th]]
        d.update({"everyone": e[0], "everyone-soft": e[1], "everyone-ink": e[2], "everyone-mark": e[3]})
    return L, D

if __name__ == "__main__":
    L, D = hexes()
    for k in L: print(f"{k:16} {L[k]}  {D[k]}")
