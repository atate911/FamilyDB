"""Draw random starting points for the "random" palettes of a round.

Each seed is a handful of dice rolls a designer turns into a tasteful page within the
constraints (the bright green signature on green-black, the floors): a mood, a material and a
companion colour, and the page's structure (layout, type system, controls, icons, motion,
pacing). Truly random: no seed.

Usage: python3 seeds.py N [--steer] [--wildcards W]  -> JSON list of N seeds
"""

import json
import random
import sys
from pathlib import Path

MOODS = [
    "a library at dusk", "a greenhouse at night", "a night train", "an arcade after hours",
    "an observatory", "a lighthouse", "an orchard in autumn", "a jazz club", "a tidepool",
    "a ski lodge", "a desert night", "a print shop", "a tea house", "a planetarium",
    "harbour fog", "a forest after rain", "a record shop", "a winter cabin", "a boathouse",
    "a museum after closing", "a campfire", "a greenhouse in the morning", "a bakery before dawn",
    "a rooftop garden", "a submarine's sonar room", "a 1980s kitchen", "a pine forest",
    "a moonlit pond", "a stationery shop", "a botanical sketchbook", "a lantern festival",
    "a coastal town at night", "a mountain hut", "an old radio", "a candlelit dinner",
]
ROLES = ["accent (links, title tiles, Home's pill)", "wash (the greeting's second light)",
         "top-glow (the afterglow at the top of every page)",
         "lit (the everyday lit things: a calmer tone)", "outing (the outing kind's own colour)",
         "the section colours (a refreshed set)", "a breath in the neutrals (ink, lines)"]
# The roles that reach the whole page: the owner asked that a change show across the page.
PAGE_ROLES = ["heading (page titles and section headings)", "label (small labels and dates)",
              "card-edge (every card's and panel's border)",
              "secondary (the ways to start and secondary buttons; quietFilter)",
              "bubble and bubble-them (the chat bubbles)", "bezel (the monitors' plastic case)",
              "bar (the top bar)", "ambient (a soft second light across the page)",
              "surface (cards tinted by the companion)"]

# Small visual mutations beyond colour, written as the palette's `css`. Optional: a roll may bring
# none. Each is a starting point, to be done with taste or bent.
MUTATIONS = [
    "section headings in DM Mono, uppercase and letter-spaced",
    "page titles larger and lighter (DM Sans at a light weight, a bigger size)",
    "page titles in VT323, as if typed on a terminal",
    "rounder corners on cards and panels (22-28px)",
    "squarer corners on cards and panels (6-8px), a more technical feel",
    "more generous spacing between sections and inside cards",
    "tighter, denser spacing in cards and lists",
    "thicker card borders (1.5-2px)",
    "a thin coloured rule along the top edge of each panel",
    "larger icons in the bar and the phone's tab bar",
    "chat bubbles squarer, with slightly larger text",
    "eyebrow labels and dates in VT323 at a larger size",
    "the ways to start as rectangular keys, like a keyboard's",
    "section headings with a short underline or overline",
    "body text a touch larger with more line height",
    "buttons with uppercase, letter-spaced labels",
    "cards with a soft inner glow instead of a drop shadow",
    "the calendar date tiles larger and bolder",
    "headings a heavier weight with tighter letter-spacing",
    "a different rhythm for card titles: smaller, bolder, with the kind label larger",
    # Wider presentation moves (all CSS; structure, wording and concepts stay as they are)
    "the bar marks the current page with an underline in its colour instead of a pill",
    "the phone's tab bar marks the current tab with a short bar above its icon",
    "icons drawn with a finer stroke (1.5) throughout",
    "the icon tile beside each page title as a circle instead of a rounded square",
    "section headings led by a short vertical rule in the section's colour",
    "cards drawn as rules (a top and bottom hairline, no box), for a lighter, editorial page",
    "a faint texture on the ground: fine scanlines or a dot grid, drawn with CSS gradients, very subtle",
    "the greeting mirrored on desktop: Next up's monitor on the left, the box on the right",
    "the monitors' cases rounder and deeper, with a larger chin and a power light in the companion colour",
    "primary buttons as pills; secondary buttons as outlined pills",
    "a denser page overall: smaller gaps between sections, tighter panels",
    "an airier page overall: larger gaps between sections, roomier panels",
    "page titles with DM Sans's optical size turned up (opsz 40) and a lighter weight, magazine-like",
    "labels and dates in DM Mono at a slightly larger size, less letter-spaced",
    "chat: Vera's lines without a bubble (text on the page beside her screen), the family's in bubbles",
    "date tiles as small monitors: dark glass, VT323 numbers in the phosphor",
    "the kind labels on idea cards as small filled chips in the kind's colour",
    "a thin glowing line under the top bar in the companion colour",
    "numbers and times in DM Mono everywhere they appear in lists",
    "the ways to start as a vertical list of options on the phone instead of chips",
    # Faces from the library (README): any open-licence face that would ship in static/fonts
    "page titles and section headings in a face from the library that suits the mood",
    "labels, dates and figures in a monospace from the library (IBM Plex Mono, JetBrains Mono, Martian Mono, Recursive...)",
    "the body text in a friendlier, more readable face from the library (Atkinson Hyperlegible, Figtree, Nunito, Lexend...)",
    "page titles in a warm serif from the library (Fraunces with its SOFT axis, or Newsreader), magazine-like",
    "Recursive for the whole page, its CASL axis a little casual and MONO for figures",
    # Typesetting (the owner enjoys it): small, careful improvements
    "a modular type scale (ratio about 1.2 or 1.25) for titles, headings, body and labels",
    "leading and tracking tuned per size: tighter large titles, looser small labels",
    "text-wrap: pretty on paragraphs and balance on headings, no lonely last words",
    "tabular figures in lists, tables, dates and times, so numbers line up",
    "labels and eyebrows in true small caps (font-variant-caps) with a little tracking",
    "DM Sans's optical sizing tuned (font-optical-sizing, opsz per size) for crisper small text and finer titles",
    "a comfortable reading measure (about 60-70 characters) for chat lines and paragraphs",
    "a vertical rhythm: spacing between blocks on one baseline unit",
    "old-style figures in running text, lining figures in tables",
    "heading weights refined: fewer weights, clearer steps between levels",
    # Controls, interaction and motion
    "selects drawn in the page's own style (appearance: base-select, a styled picker)",
    "checkboxes and radios drawn in the palette's own style",
    "scroll bars styled to the palette (thin, in the neutrals)",
    "focus rings redesigned: clear, calm, consistent across every control",
    "hover and press states refined: every control answers the pointer the same way",
    "the afterglow and glow-in timings retuned (a longer, softer echo, or a snappier one)",
    "line weights refined: one hairline weight for dividers, one for boxes, one for focus",
    "shadows reconsidered: fewer, softer, one elevation scale",
    "a clearer sight line on each page: the page title, its one action and the first thing to read in one line of sight",
]

# The structure of a random entrant: how the page is built, not only how it is coloured. One roll
# on each axis, a starting point the designer keeps, bends or drops (and says which). Any of them
# may need the page's markup (README: "A palette's own markup").
LAYOUTS = [
    "a single centred reading column, like a book page, with generous margins",
    "a main column with a side rail for the secondary things (Next up, the ways to start, filters)",
    "a dashboard grid of equal instruments, each list or monitor its own module",
    "a newspaper: a masthead with the page title and date, then columns of unequal width",
    "a left navigation rail on desktop instead of the top bar (the phone keeps its tab bar)",
    "a split screen: the machine's glass on one side, the family's things on the other",
    "stacked full-width bands, each section its own band edge to edge, ruled apart",
    "a list-first page: rows like a ledger or a timetable, few boxes",
    "tiles in a grid, each item a square-ish tile with its lead mark on top",
    "a console: a fixed status strip at the top (the date, what is on now), the work below",
    "an index-card box: each item a card with a tab carrying its kind",
    "an asymmetric editorial page: a wide left margin with hanging section heads, text to the right",
]
TYPE_SYSTEMS = [
    "one sans at few sizes and weights, every figure in a mono (DM Sans with DM Mono)",
    "a serif for titles and reading, a sans for labels and controls (Newsreader or Fraunces with a sans)",
    "a monospace page: one mono for everything, the hierarchy by size, weight and case alone",
    "a humanist sans for reading (Atkinson Hyperlegible, Figtree or Lexend) with a technical mono for data",
    "a grotesque with tight large titles and small-caps labels (Instrument Sans or Manrope)",
    "the terminal face (VT323) for the machine's words only, a quiet sans for the family's",
    "Recursive for everything, its axes doing the jobs (casual for Vera, MONO for figures)",
    "a wide or condensed face for titles (Martian Mono or Instrument Sans on its width axis), a neutral text face",
]
CONTROLS = [
    "keycaps: buttons as keys with a little depth, fields as recessed wells",
    "switches and lamps: checkboxes and toggles as small switches with an indicator lamp",
    "a printed form: fields as ruled lines, selects as ruled lines with a caret, buttons as boxed labels",
    "terminal commands: buttons set like [ Send ] on the glass, fields as a prompt line",
    "soft pills: rounded fields and buttons, gentle fills, no hard outlines",
    "flat technical: square corners, one hairline outline, a fill only on press",
    "segmented: related choices as segments in one bar, fields and buttons joined into one control",
]
ICONS = [
    "no icons beside words: the words and a small coloured mark do the work",
    "fine line icons (a 1.25-1.5 stroke) at the cap height of the words they sit with",
    "solid, filled icons in the section colours",
    "icons set in small lit squares, like indicator lamps on a panel",
    "icons drawn as the monitor would draw them: pixel-like, in the phosphor",
    "larger icons leading each card or row, like a catalogue",
]
MOTION = [
    "still: nothing moves but focus and the afterglow",
    "a phosphor warm-up: things arrive from a dim green, as a tube warms (reduced motion kept)",
    "a slow, quiet cursor blink wherever the machine is waiting",
    "crisp: hover and press answer at once, no easing",
    "a long, soft afterglow, like real P1 phosphor decay",
    "a scan: one faint line passes over a monitor when it switches on",
]
PACING = [
    "dense, like a timetable: small gaps, many rows in view",
    "comfortable: today's pacing, made consistent",
    "airy: generous darkspace between sections, few things per screen",
    "rhythmic: every gap on one 8px unit, sections apart by one large step",
    "grouped: tight inside a group, wide between groups, so the groups read at a glance",
]
STRUCTURE = {"layout": LAYOUTS, "type_system": TYPE_SYSTEMS, "controls": CONTROLS, "icons": ICONS,
             "motion": MOTION, "pacing": PACING}

# Structural changes for a mutant: bigger than a refinement, each may need the markup.
STRUCTURE_MUTATIONS = [
    "rearrange Home: a different column structure or order (for example the monitor full width above the lists, or the lists side by side)",
    "move the navigation: a left rail on desktop instead of the top bar, or the top bar redrawn as a console strip",
    "redraw every page head: the title, a rule and the page's one action on one line of sight",
    "turn cards into rows: each item a row with a lead mark, a body and a facts column",
    "turn rows or cards into tiles in a grid",
    "set the chat as a transcript: the speaker in a narrow left column, the lines to the right, no bubbles",
    "hang the section heads in the left margin on desktop, the content to their right",
    "put the Ideas filters in a side panel beside the list instead of above it",
    "redraw the phone's tab bar: a different way of marking the current tab and a different icon treatment",
    "give the page a new type system: a new pairing from the library, each face with one job",
    "give every control one new grammar (fields, selects, checkboxes and buttons redrawn as one family)",
    "change the density across the system: one step denser or airier, every gap on a new unit",
    "change the rounding across the system: everything square, or everything round",
    "redraw the monitors: a different case (inset flush in the page, a flat panel, a deep rounded tube)",
    "change how things arrive and answer: a new, calm motion for arrival, hover and press (reduced motion kept)",
    "change the page's grid: a wider or narrower measure, or the content aligned to a left edge instead of centred",
    "change the icon family: no icons, lamp squares, pixel icons, or solid icons in the section colours",
    "give Status its own instrument panel: each part a lamp or gauge tile",
]

# Small random changes to a winner, for its mutants: one colour change, sometimes a refinement too.
COLOUR_MUTATIONS = [
    "turn the companion colour's hue by about +30 degrees, keeping its roles and lightness",
    "turn the companion colour's hue by about -30 degrees, keeping its roles and lightness",
    "make the companion a step richer (more chroma), where it is used",
    "make the companion a step dustier (less chroma), where it is used",
    "carry the companion into one more page-wide role it does not have yet (heading, label, card-edge, secondary, bubble-them, bar or ambient: pick the one that suits it)",
    "take the companion out of one role where it is weakest, and put that role back to its quiet default",
    "warm the ink and the neutrals a small step",
    "cool the ink and the neutrals a small step",
    "soften the text contrast by about one step (for example 13:1 to 12:1)",
    "sharpen the text contrast by about one step (for example 12:1 to 13:1)",
    "give the monitors a different case (bezel): a period beige, putty, grey or charcoal plastic",
    "raise the page's glow a small step (about +0.1), or lower it a small step if it is already high",
    "tint the chat bubbles (bubble and bubble-them) in the palette's own colours",
    "make the Ideas page's Filter button quiet (quietFilter) in the companion colour",
]


def mutants(parents, n, protected=None):
    """n mutants over the parents ({id, name, family}). Each point mutant has two or three changes,
    one of colour and one of structure, and half the time a refinement too. From three on, the last
    is a crossover: one parent's structure (markup, layout, type, controls) with another's colours,
    from two different families. A carried random entrant (protected) gets the first point mutant,
    so a random idea's line has room to grow."""
    out = []
    n_cross = 1 if n >= 3 and len(parents) >= 2 else 0
    first = [p for p in parents if p["id"] == protected]
    rest = [p for p in parents if p["id"] != protected]
    order = first + random.sample(rest, len(rest))
    for i in range(n - n_cross):
        parent = order[i % len(order)]
        changes = [random.choice(COLOUR_MUTATIONS), random.choice(STRUCTURE_MUTATIONS)]
        if random.random() < 0.5:
            changes.append(random.choice(MUTATIONS))
        out.append({"kind": "point", "parent": parent["id"], "parentName": parent["name"], "changes": changes})
    if n_cross:
        # Two parents from different families, preferring those no point mutant used, so the
        # round's variation spreads over all four carried.
        used = {m["parent"] for m in out}
        pairs = [(a, b) for a in parents for b in parents if a["id"] != b["id"]]
        best = max(2 * (a.get("family") != b.get("family")) + (a["id"] not in used) + (b["id"] not in used)
                   for a, b in pairs)
        a, b = random.choice([(a, b) for a, b in pairs
                              if 2 * (a.get("family") != b.get("family")) + (a["id"] not in used) + (b["id"] not in used) == best])
        out.append({"kind": "crossover", "parent": a["id"], "parentName": a["name"],
                    "colourParent": b["id"], "colourParentName": b["name"],
                    "changes": [f"the structure of {a['name']} (its markup, layout, type, controls, spacing and non-colour css) "
                                f"with the colours of {b['name']} (its tokens, glow numbers and colour roles)"]})
    return out


def usage():
    """What the hall of fame has tried: companion hues (30-degree bins), page roles and mutations."""
    from pathlib import Path
    here = Path(__file__).parent
    hues, roles, muts = [0] * 12, {}, {}
    try:
        arc = json.loads((here / "archive.json").read_text())["palettes"]
    except OSError:
        return hues, roles, muts
    sys.path.insert(0, str(here))
    from colorlib import hex_to_rgb, rgb_to_oklch
    for p in arc.values():
        try:
            t = json.loads((Path(p["dir"]) / "palettes" / f"{p['id']}.json").read_text())["tokens"]
        except OSError:
            continue
        for role in ("accent", "wash", "bubble-them", "card-edge", "heading", "secondary", "bar", "ambient", "bezel"):
            if role in t and t[role].lower() != t["brand"].lower():
                L, C, h = rgb_to_oklch(hex_to_rgb(t[role]))
                if C > 0.03:
                    hues[int(h // 30) % 12] += 1
                roles[role] = roles.get(role, 0) + 1
    for f in here.glob("rounds/*/seeds.json"):
        for sd in json.loads(f.read_text()):
            for m in sd.get("refinements", []):
                muts[m] = muts.get(m, 0) + 1
    return hues, roles, muts


STEER = None  # set by --steer: (hue counts, role counts, mutation counts)


def pick_weighted(options, count_of, k):
    """k distinct options, each weighted towards the ones tried least."""
    pool, out = list(options), []
    for _ in range(min(k, len(pool))):
        weights = [1 / (1 + count_of(o)) for o in pool]
        choice = random.choices(pool, weights)[0]
        out.append(choice)
        pool.remove(choice)
    return out


def role_key(label):
    return label.split(" (")[0].split(" and ")[0]

# The owner wants grounded colour away from the green motif: each random companion comes as a
# real-world material at its hue, not as coloured light.
MATERIALS = ["clay", "walnut", "slate", "linen", "pewter", "denim", "sandstone", "oxblood", "ink",
             "oat", "terracotta", "moss", "graphite", "cork", "indigo cloth", "brass (aged, not shiny)",
             "river stone", "felt", "leather", "porcelain", "rust", "sage leaf", "bark", "wool"]


def seed():
    if STEER:
        hues_used = STEER[0]
        hue_bin = random.choices(range(12), [1 / (1 + c) for c in hues_used])[0]
        hue = hue_bin * 30 + random.randrange(0, 30)
    else:
        hue = random.randrange(0, 360)
    return {
        "mood": random.choice(MOODS),
        "material": random.choice(MATERIALS),
        "companion_hue_deg": hue,
        "companion_note": ("a hue in the green family: make the variation tonal"
                           if 110 <= hue <= 175 else "a companion colour at this OKLCH hue"),
        "companion_roles": random.sample(ROLES, random.randint(1, 3)) + (
            pick_weighted(PAGE_ROLES, lambda r: STEER[1].get(role_key(r), 0), random.randint(3, 5)) if STEER
            else random.sample(PAGE_ROLES, random.randint(3, 5))),
        "second_companion_hue_deg": random.choice([None, random.randrange(0, 360)]),
        "ground_hue_deg": random.randrange(120, 196),
        "ground_step": random.choice(["as dark as today", "a half step lighter", "a step lighter"]),
        "ink": random.choice(["warm", "neutral", "cool", "faintly tinted by the companion"]),
        "text_contrast_target": round(random.uniform(11.0, 15.5), 1),
        "glow": round(random.uniform(0.4, 1.0), 2),
        "screenGlow": round(random.uniform(0.6, 1.0), 2),
        **{axis: random.choice(options) for axis, options in STRUCTURE.items()},
        "refinements": (pick_weighted(MUTATIONS, lambda m: STEER[2].get(m, 0), random.choice([0, 0, 1, 1, 2]))
                        if STEER else random.choice([[], [], random.sample(MUTATIONS, 1), random.sample(MUTATIONS, 2),
                                                     random.sample(MUTATIONS, 1)])),
    }


if __name__ == "__main__":
    if "--steer" in sys.argv:
        STEER = usage()
    n = int(sys.argv[1])
    wild = int(sys.argv[sys.argv.index("--wildcards") + 1]) if "--wildcards" in sys.argv else 0
    out = [seed() for _ in range(n)]
    # Moods, materials and each structural axis are distinct within a round where the list allows
    # (four "rooftop gardens" in round 7's first draw), and with --steer lean towards the ones
    # earlier rounds' seeds used least.
    axes = {"mood": MOODS, "material": MATERIALS, **STRUCTURE}
    past = {k: {} for k in axes}
    if STEER:
        for f in Path(__file__).parent.glob("rounds/*/seeds.json"):
            for sd in json.loads(f.read_text()):
                for k in past:
                    past[k][sd.get(k)] = past[k].get(sd.get(k), 0) + 1
    for key, options in axes.items():
        picks = []
        while len(picks) < n:
            picks += pick_weighted(options, lambda o, k=key: past[k].get(o, 0), n - len(picks))
        for sd, pick in zip(out, picks):
            sd[key] = pick
    for i in random.sample(range(n), min(wild, n)):
        out[i]["ambition"] = "wildcard"
    print(json.dumps(out, indent=1))
