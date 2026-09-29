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
    "a condensed system: titles and labels in IBM Plex Sans Condensed or Barlow Condensed, a text face below",
    "a serif for the family's words (Source Serif 4 or Literata), a sans for labels and controls, a mono for the machine",
    "one superfamily for every role (IBM Plex Sans, Serif and Mono, or Red Hat Text and Mono)",
    "a CRT face on the tubes only (Workbench, Sixtyfour or Doto, their bleed and scanline axes kept light), a quiet sans for the family",
    "one variable sans for everything (Inter, Geist or Bricolage Grotesque), hierarchy by weight, size and width alone",
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
    "a new icon family drawn for this design (your own icons.svg, every icon kept): pixel, engraved line, filled pictogram or lamp-panel symbols",
    "a drawn picture for each kind and section, in one style, used as its mark everywhere",
]
GRAPHICS = [
    "no pictures: type, rules and colour carry everything",
    "small line drawings for each section's head (Coming up, To do, the kids' wishes, Next up, the setup steps, Status's panels), in one style",
    "an instrument panel: dials, gauges and meters wherever the page shows state or cost",
    "a plotted chart or map wherever the page shows places or time",
    "a drawn period terminal or scope around every monitor",
    "a faint pattern on one surface only (scanlines, a grid, halftone)",
    "big numerals and glyphs as the page's pictures",
    "pixel-art sprites for the kinds and sections",
    "technical drawings: thin schematic line art with dimension lines and callouts",
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
             "graphics": GRAPHICS, "motion": MOTION, "pacing": PACING}

# Typesetting dice. Minor: a careful typesetter's adjustment. Major: a new type system or face.
TYPE_MINOR = [
    "tracking tuned per size: display titles tighter (about -0.02em), small labels and caps looser (+0.04 to +0.08em)",
    "leading tuned per size: about 1.1 for titles, 1.5-1.6 for body, 1.3 for labels",
    "tabular lining figures wherever numbers line up (lists, times, dates, counts), proportional in running text",
    "a slashed or dotted zero in the monospaced face, where it has one (font-feature-settings \"zero\")",
    "a stylistic set or character variant of the face (ss01-ss08, cv..), where it has one, for a more distinctive texture",
    "true small caps (font-variant-caps: all-small-caps) for labels and eyebrows instead of uppercase",
    "text-wrap: balance on every heading and pretty on paragraphs, so no line ends on a lonely word",
    "a narrower reading measure: 55-65 characters for paragraphs, chat lines and help text",
    "optical sizing on or tuned per size, where the face has an opsz axis",
    "heading weights one step lighter, with size and colour carrying the hierarchy",
    "heading weights one step heavier with tighter tracking, for a denser, punchier head",
    "body text one step larger (for example 16px to 17px) with the measure kept",
    "labels and small text one step larger and one step less tracked, for legibility",
    "quotes and bullets hung by hand outside the text edge (a negative indent, or the list pulled into the margin)",
    "underlines refined: 1px, offset about .22em, skip-ink on, in a quieter colour than the text",
    "font-synthesis off everywhere, so no faux bold or italic ever appears",
    "one more step between section heads and card titles, so the two never look alike",
    "a monospace for every machine-written string (times, counts, ids, the tubes), a proportional face for everything the family wrote",
    "headings trimmed to their caps (text-box: trim-both cap alphabetic), so titles sit exactly on the rule or edge above",
    "italic for one job only (hints, or Vera's asides), never elsewhere",
    "light text on the dark ground eased half a weight or grade, so it does not bloom",
    "all capitals limited to one role (tiny labels), each with about +0.06em tracking",
    "oldstyle figures in running text and headings, lining figures in data",
    "the tubes' text re-set: size, leading and letter-spacing tuned so VT323 (or its replacement) reads as a real terminal line",
]
TYPE_MAJOR = [
    "replace the page's sans with a different one from the library (a grotesque, a humanist or a geometric), every face keeping one job",
    "replace the display face: page titles and section heads in a library face with character (condensed, wide or serif), body unchanged",
    "set the family's text in a serif from the library (Source Serif 4, Literata, Newsreader or IBM Plex Serif), with a sans or mono for labels and controls",
    "a condensed system: titles and labels in a condensed face (IBM Plex Sans Condensed, Barlow Condensed, or Archivo narrow), body in a text face",
    "width as hierarchy: one variable face (Archivo or Bricolage Grotesque) with wide or narrow titles and normal text",
    "one superfamily for everything (IBM Plex Sans, Serif and Mono, or Red Hat Text and Mono), every role a member",
    "a new type scale: a different ratio (1.2, 1.25 or 1.333) and fewer steps, every size on it",
    "a CRT face for the machine's words on the tubes (Workbench, Sixtyfour or Doto, bleed and scanlines light), the family's words in a quiet sans",
    "a monospaced setting for the family's data (lists, tables, forms) and a proportional face only for titles and chat",
    "a new mono for the machine and the figures (Geist Mono, Red Hat Mono, Azeret Mono, Fira Code, Spline Sans Mono or Victor Mono)",
    "a larger, more generous setting (17-18px body, 1.6 leading) with fewer, clearer heading steps",
    "headings in sentence case at a light weight and a large size, labels in small caps: a magazine's hierarchy",
    "a denser, smaller setting (15px body, 1.4 leading, compact heads), like an information display",
    "one variable sans for the whole page (Inter, Geist, Hanken Grotesk or Recursive), hierarchy by weight and size alone",
]


def type_change():
    """One typographic change: a major one a third of the time, otherwise a minor one."""
    return random.choice(TYPE_MAJOR) if random.random() < 1 / 3 else random.choice(TYPE_MINOR)


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
    "draw a new icon family for the whole app (your own icons.svg, every icon kept), in the design's own line and colour",
    "give each section's head a small drawn picture (Home's Coming up, To do and the kids' wishes, Next up, the setup steps, Status's panels), all in one style",
    "redraw the monitors as detailed period terminals or scopes, drawn in SVG around the green glass",
]

# Graphics, pictures and iconography dice, for a graphics mutant. Pictures are placed through the
# markup or loaded by css from the design's own static folder, and a picture must earn its place.
GRAPHICS_MINOR = [
    "icons at a new stroke weight and size, matched to the cap height and weight of the words beside them",
    "icons in containers: each section's icon on a small tile, lamp or key in its section colour",
    "icons out of their containers: bare glyphs, one size, one stroke",
    "the kind icons redrawn as small badges in each kind's colour",
    "the page-title icons enlarged into a drawn emblem for each section",
    "a drawn divider or ornament between sections (a rule with a small mark, a bracket, a leader)",
    "the section heads on Home (Coming up, To do, the kids' wishes) and the setup steps given a small line drawing each",
    "the radar and scopes redrawn: finer rings, tick marks, a bearing scale and a legend",
    "the FamilyDB mark in the bar redrawn in the design's line, keeping its idea (a smiling monitor) and its #6dff9c",
    "the phone's tab-bar icons redrawn for the design, with a clear current state",
    "the status lamps redrawn as one family of small signals (ring, dot, bar, lamp), one meaning each",
    "arrows, chevrons and carets redrawn as one family (weight, angle, size) across links, selects and folds",
    "a faint texture on one surface only (scanlines on the glass, a grid on the trays, halftone on the greeting)",
]
GRAPHICS_MAJOR = [
    "a new icon family drawn for the app (your own icons.svg, every icon kept): pixel icons, engraved line icons, filled pictograms or lamp-panel symbols",
    "pictures: a small drawn illustration for each section's head on every page, in one style (line art, pixel art or technical drawing)",
    "an instrument panel: Status and the cost readout drawn as dials, gauges, meters or a bar chart in SVG",
    "the monitors redrawn as illustrations: a detailed period terminal or scope, drawn in SVG, around the green glass",
    "a greeting picture: a drawn scene or emblem beside or behind the question (a skyline, a radar sweep, a switchboard), light enough to read over",
    "no icons at all: words, numerals and coloured marks carry everything, and the space goes to type",
    "big numerals and glyphs as the graphics: dates, counts and initials set large as the page's pictures",
    "a mapped page: the radar, the plans and the ideas drawn as a plotted chart or map with the family's places marked",
    "a pictorial kind system: each kind (restaurant, activity, outing, trip, show, seasonal, event) gets a drawn picture used as its mark everywhere",
    "a schematic language: thin technical line drawings, dimension lines and callouts for the heads, the monitors and the setup steps",
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


COLOUR_ROLES = ["bg", "surface", "accent", "label", "card-edge", "bubble-them", "bezel", "heading", "lit"]


def colour_distance(x, y):
    """Mean OKLab distance (x100) between two palettes' shared colour roles; 0 when unknown."""
    if not x or not y:
        return 0.0
    import math
    sys.path.insert(0, str(Path(__file__).parent))
    from colorlib import hex_to_rgb, rgb_to_oklab
    common = [k for k in COLOUR_ROLES if k in x and k in y]
    if not common:
        return 0.0
    return 100 * sum(math.dist(rgb_to_oklab(hex_to_rgb(x[k])), rgb_to_oklab(hex_to_rgb(y[k]))) for k in common) / len(common)


def mutants(parents, n, protected=None, n_type=0, n_graphics=0, n_cross=None, cross_pool=None):
    """n mutants over the parents ({id, name, family}). Each point mutant has three changes: one of
    colour, one of structure and one of type. From three on, the last
    is a crossover: one parent's structure (markup, layout, type, controls) with another's colours,
    from two different families. A carried random entrant (protected) gets the first point mutant,
    so a random idea's line has room to grow."""
    out = []
    if n_cross is None:
        n_cross = 1 if n >= 3 and len(parents) >= 2 else 0
    n = n if n >= n_cross else n_cross
    first = [p for p in parents if p["id"] == protected]
    rest = [p for p in parents if p["id"] != protected]
    order = first + random.sample(rest, len(rest))
    for i in range(n - n_cross):
        parent = order[i % len(order)]
        changes = [random.choice(COLOUR_MUTATIONS), random.choice(STRUCTURE_MUTATIONS), type_change()]
        out.append({"kind": "point", "parent": parent["id"], "parentName": parent["name"], "changes": changes})
    # A type mutant: a carried winner with typographic changes only (one major, two minor), so
    # the panel sees what the typesetting alone does. It prefers a parent no point mutant used.
    for _ in range(n_type):
        used = {m["parent"] for m in out}
        pool = [p for p in parents if p["id"] not in used] or parents
        parent = random.choice(pool)
        out.append({"kind": "type", "parent": parent["id"], "parentName": parent["name"],
                    "changes": [random.choice(TYPE_MAJOR), *random.sample(TYPE_MINOR, 2)]})
    # A graphics mutant: a carried winner with its pictures and iconography changed only (one
    # major change, one or two minor), so the panel sees what graphics alone can do.
    for _ in range(n_graphics):
        used = {m["parent"] for m in out}
        pool = [p for p in parents if p["id"] not in used] or parents
        parent = random.choice(pool)
        out.append({"kind": "graphics", "parent": parent["id"], "parentName": parent["name"],
                    "changes": [random.choice(GRAPHICS_MAJOR), *random.sample(GRAPHICS_MINOR, random.choice([1, 2]))]})
    if n_cross:
        # Two parents from different families whose colours are far apart (swapping near-identical
        # colours changes nothing), then preferring those no point mutant used, so the round's
        # variation spreads over all four carried. The direction is left to chance.
        used = {m["parent"] for m in out}
        pool = cross_pool or parents
        pairs = [(a, b) for a in pool for b in pool if a["id"] != b["id"]]
        far = {(a["id"], b["id"]): colour_distance(a.get("colours"), b.get("colours")) for a, b in pairs}
        top = max(far.values()) or 1

        def worth(a, b):
            return (2 * (a.get("family") != b.get("family")) + 3 * far[(a["id"], b["id"])] / top
                    + 0.5 * ((a["id"] not in used) + (b["id"] not in used)))
        best = max(worth(a, b) for a, b in pairs)
        a, b = random.choice([(a, b) for a, b in pairs if worth(a, b) >= best - 0.25])
        out.append({"kind": "crossover", "parent": a["id"], "parentName": a["name"],
                    "colourParent": b["id"], "colourParentName": b["name"],
                    "changes": [f"the structure of {a['name']} (its markup, layout, type, controls, spacing and non-colour css) "
                                f"with the colours of {b['name']} (its tokens, glow numbers and colour roles)"]})
    return out


# The wild lane: designs built from a clean sheet on a radically different design language, in a
# lane of their own so a new idea has time to mature. Nothing is off the table for them.
WILD_LANGUAGES = [
    "Teletext and Ceefax: blocky mosaic graphics, a strict 40-column grid, double-height headlines, page numbers",
    "Swiss International Style: a strict grid, flush-left grotesque type, huge numerals, asymmetric dark space",
    "Bauhaus: primary geometry (circles, squares, bars), bold type, the phosphor green as the one primary",
    "brutalist web: raw structure shown proudly, rules and system type, underlined links, no decoration",
    "a vector-arcade display (Vectrex, Asteroids): everything drawn in glowing outlines on black, no fills",
    "an oscilloscope and lab instrument front: graticules, traces, knobs and engraved legends",
    "mission control, 1969: consoles of monospaced status readouts and rows of indicator lamps",
    "Dieter Rams and Braun: quiet grey hardware, one coloured control, perfect grids, small lowercase type",
    "a trading terminal: dense multi-panel data, function-key bars, tiny type, everything visible at once",
    "the first graphical desktops (Mac System 1, GEM): 1-bit windows, striped title bars, pixel icons",
    "ANSI and BBS art: box-drawing characters, block shading, 80-column text-mode screens",
    "Minitel and videotex: chunky mosaic graphics and a service-menu page structure",
    "an e-ink reader: calm, typographic, book-like pages, nothing glows but the signature",
    "railway signage and timetables: numbered lines, line colours, stop lists, big legible type",
    "an architectural blueprint: a cyanotype grid, dimension lines, title blocks, stamped labels",
    "a newspaper broadsheet: masthead, columns, rules, headlines and datelines",
    "a modular synthesiser: panels, patch points, knobs, engraved labels, cables as lines",
    "a 1980s cockpit or dashboard: backlit gauges, segmented displays, warning lamps",
    "line-printer and punched-card era: green-bar paper, perforations, fixed-width columns",
    "a split-flap departures board: flap characters, rows, times, the clatter of change",
    "a handheld console (Game Boy): a four-green palette, pixel sprites, chunky boxes",
    "LCD calculators and digital watches: seven-segment digits, grey-green panels, tiny legends",
    "a museum exhibition: large type, generous space, object labels and captions",
    "a field notebook under a green work lamp: ruled pages, stamps, clips and hand-set labels",
    "a library card catalogue: drawers, index cards with typed headings, call numbers",
    "Tron and the neon grid: glowing outlines, a dark grid floor, light trails as the lines",
    "a zine: collage, torn paper, tape and stickers, kept legible",
    "a star chart and planetarium desk: arcs, rings, coordinates, a dark dome",
    "a hand-drawn sketch: pen lines, loose boxes, annotations, kept legible",
    "a poster: the greeting as one huge typographic statement, everything else small",
]
WILD_TWISTS = [
    "no cards and no boxes at all: space, type and lines only",
    "the whole of Home on one screen, nothing below the fold on desktop",
    "one long scrolling ribbon: every section a full-width chapter",
    "a navigation that is the page: a large index or map of the app is the home",
    "one type size for everything: hierarchy by weight, colour, case and space alone",
    "big type: the greeting and each page title as a poster",
    "a grid of equal cells, like a control panel, on every page",
    "a timeline as the spine of every page",
    "conversation first: Vera's thread at the centre, everything else around it",
    "radical density: every page shows everything at once, like an instrument",
    "radical sparsity: one thing at a time, large, with everything else a step away",
    "the phone first: design the phone, and let the desktop be the phone widened",
    "pictures first: every section led by a drawing or a diagram",
    "sound made visible: level meters, waveforms and signal lines as the page's ornament",
]


def wild_seeds(n, past=None):
    """n wild rolls: a design language and a twist, distinct. Languages never tried come first
    while there are enough of them; after that the dice lean to the least used."""
    past = past or {}
    fresh = [o for o in WILD_LANGUAGES if not past.get(o)]
    langs = (random.sample(fresh, n) if len(fresh) >= n
             else fresh + pick_weighted([o for o in WILD_LANGUAGES if o not in fresh], lambda o: past.get(o, 0), n - len(fresh)))
    twists = random.sample(WILD_TWISTS, min(n, len(WILD_TWISTS)))
    return [{"language": lang, "twist": tw, "companion_hue_deg": random.randrange(0, 360)}
            for lang, tw in zip(langs, twists)]


def wild_mutants(parents, n):
    """Big leaps on the wild lane's carried designs: two large changes each."""
    pool = STRUCTURE_MUTATIONS + TYPE_MAJOR + GRAPHICS_MAJOR + WILD_TWISTS
    out = []
    order = random.sample(parents, len(parents)) if parents else []
    for i in range(n if order else 0):
        parent = order[i % len(order)]
        out.append({"kind": "wild", "parent": parent["id"], "parentName": parent["name"],
                    "changes": random.sample(pool, 2)})
    return out


# The phosphor mutant: a carried winner with the original page's CRT light brought back (the owner,
# after round 9: "we've gained a lot but also lost a little of the unique effect of the original
# phosphor interface. I'd suggest bringing some of that back"). Every one restores the kit's
# effects that fit its design; the dice pick two to push furthest, so rounds learn which matter.
PHOSPHOR_BASE = ("bring back the original Phosphor page's light wherever this design shows phosphor: every "
                 "effect in phosphor_kit.md that fits it, in this design's own terms")
PHOSPHOR_EMPHASES = [
    "the lit words and marks: the tube's layered halo (a tight one and a wide faint one) on the mark, the key "
    "word, the primary button and every lit state, clearly visible at 100%",
    "the green screens as real tubes again: VT323 at three strengths, a third of a pixel of blur, bloom, "
    "scanlines, and the curved glass falling into shadow at its corners",
    "glowing dots on the black: the live lamps and status lights as small green points that glow and breathe, "
    "and a faint field of phosphor dots where the machine speaks",
    "the page's own light: the green afterglow at the top of the page with faint scanlines through it, and "
    "highlights along the top edges of the machine's surfaces",
    "light that behaves as a tube's did: what lights up (hover, focus, the box being typed in, a new message) "
    "does so at once and fades over a second, leaving an afterglow",
    "the radar and her screen at full strength: the sweep's afterglow, glowing blips, and her glyph screen's "
    "bloom and scanlines",
    "the primary actions lit from within: a green ring and light pooled under the primary button and Send",
    "the machine's voice as lit phosphor: Vera's words, times and live readouts with a soft halo, while the "
    "family's words stay grounded and sharp",
]


def phosphor_mutants(parents, n):
    """n phosphor mutants, one per parent in the order given (the caller puts first the ones that
    kept least of the original's light). No two share an emphasis while the list lasts."""
    parents = parents[:n]
    deck = random.sample(PHOSPHOR_EMPHASES, len(PHOSPHOR_EMPHASES))
    out = []
    for i, p in enumerate(parents):
        pair = deck[2 * i:2 * i + 2] if 2 * i + 2 <= len(deck) else random.sample(PHOSPHOR_EMPHASES, 2)
        out.append({"kind": "phosphor", "parent": p["id"], "parentName": p["name"], "changes": [PHOSPHOR_BASE] + pair})
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
        "type_details": random.sample(TYPE_MINOR, random.choice([1, 2, 2, 3])),
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
