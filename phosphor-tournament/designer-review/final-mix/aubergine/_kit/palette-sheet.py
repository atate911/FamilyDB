#!/usr/bin/env python3
"""Usage: python3 _kit/palette-sheet.py

Writes palette.html (in the same shell as every page, from type.html) and the swatch classes in
style.css (between the palette-sheet:begin and :end comments). Every value printed on the sheet is
read from the tokens in style.css, and every number from _kit/palette-check.py, so the sheet can't
drift from the palette. Colours on the sheet are drawn with var(), so the dark render shows the night palette."""
import re, os, sys, json, subprocess, html
KIT = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(KIT)
sys.path.insert(0, KIT)
from colour import tokens, resolve, MACHADO

css = open(os.path.join(ROOT, "style.css")).read()
DAY, NIGHT = tokens(css)
check = json.loads(subprocess.run([sys.executable, os.path.join(KIT, "palette-check.py"), os.path.join(ROOT, "style.css"), "--json"], capture_output=True, text=True).stdout)

GROUPS = [
    ("The page: stone", [
        ("paper", "the page: warm stone, a grey, never cream"), ("paper-2", "wells, hover rows, the weekend wash, disabled"),
        ("card", "banners inside Ask, raised notes"), ("field", "inputs and tick boxes")]),
    ("Ink and rules: aubergine-black", [
        ("ink", "text, and every picked control"), ("ink-2", "secondary text, meta, margin times"), ("ink-3", "quiet text and labels (still AA)"),
        ("rule", "the 3 px rail over every section"), ("line", "hairlines between rows"), ("line-2", "the running head's and calendar's rules"),
        ("edge", "control edges: inputs, ticks, faces, quiet buttons (3:1)")]),
    ("The panel: aubergine", [
        ("band", "the panel and the phone's top bar"), ("band-hi", "a hovered row, the account plate"), ("band-line", "rules on the panel"),
        ("on-band", "sign lettering"), ("on-band-2", "quiet lettering, icons, counts"),
        ("here-bg", "you are here: a brass plate"), ("on-here", "its letters"), ("here-edge", "its 5 px edge (the kid's colour on her pages)"),
        ("band-focus", "the focus ring on the panel")]),
    ("Brass: what you act on next", [
        ("brass", "the Tomorrow stamp, today's stamp, the night primary button"), ("on-brass", "letters on brass"),
        ("brass-lit", "brass lit on aubergine"), ("brass-line", "the rule beside Leave by, link underlines"),
        ("brass-ink", "brass printed on stone: the Leave by label"),
        ("primary", "the one primary button: aubergine by day, brass at night"), ("primary-2", "its hover"), ("on-primary", "its letters: brass by day"),
        ("today-bg", "today: a brass stamp"), ("on-today", "its letters"), ("today-wash", "today's calendar cell"), ("today-ink", "the date in the greeting"),
        ("link", "links are ink"), ("link-line", "over a brass underline"), ("focus", "the focus ring: plum by day, brass at night")]),
    ("Signals", [
        ("alert", "late, broken, errors: the only red"), ("alert-soft", "its wash"), ("alert-line", "its edge"),
        ("alert-plate", "the late count on the panel"), ("on-alert-plate", "its letters"),
        ("warn", "set this up, needs a look: copper, always with ⚠"), ("warn-soft", "the setup panel"), ("warn-line", "its edge"),
        ("ok", "working, done"), ("ok-soft", "its wash"), ("ok-line", "its edge"),
        ("vera-bg", "a done tick, the strike-through, Yes!"), ("on-vera", "on it")]),
    ("Vera's glass and phosphor (the echo of the first design)", [
        ("vera", "Vera's green as text, her rule in the chat"), ("vera-soft", "the calm pill, receipts"), ("vera-line", "their edge"),
        ("glass", "her glass: the mark, panes, the radar"), ("ask-bg", "the Ask block"), ("glass-line", "rules on glass"),
        ("ask-ink", "words on glass"), ("ask-ink-2", "quiet words on glass"), ("phosphor", "her typed line, the wordmark's cursor, the mark"),
        ("send", "the lit Send"), ("on-send", "its letters"), ("cursor", "the lit cursor"), ("ask-ring", "the ring round Ask Vera"),
        ("phosphor-glow", "the glow"), ("glass-alert", "trouble, on glass")]),
]
PEOPLE = [("p1", "Sam", "sapphire"), ("p2", "Alex", "amethyst"), ("p3", "Maya", "peacock"), ("p4", "Theo", "topaz"),
          ("p5", "Slot 5", "peridot"), ("p6", "Slot 6", "cerulean"), ("p7", "Slot 7", "tiger’s eye"), ("p8", "Slot 8", "tanzanite")]
PERSON_TOKENS = ["", "-on", "-soft", "-ink", "-mark"]

def v(theme, name):
    x = resolve(theme, "--" + name)
    return x.upper() if x.startswith("#") else x.replace(" ", "")

def both(name):
    d, n = v(DAY, name), v(NIGHT, name)
    return f"{d}" if d == n else f"{d}<br><span>{n}</span>"

def sw_classes():
    names = [n for _, g in GROUPS for n, _ in g] + [f"{p}{s}" for p, _, _ in PEOPLE for s in PERSON_TOKENS] + ["everyone", "everyone-soft", "everyone-ink", "everyone-mark"]
    return "\n".join(f".sw--{n} {{ background: var(--{n}); }}" for n in names)

def token_groups():
    out = []
    for title, toks in GROUPS:
        lis = "".join(f'<li class="pal-tok"><span class="pal-tok__sw sw--{n}"></span><span><span class="pal-tok__n">--{n}</span><span class="pal-tok__u">{html.escape(u)}</span></span><span class="pal-tok__v">{both(n)}</span></li>' for n, u in toks)
        out.append(f'<div class="pal-group"><h3>{html.escape(title)}</h3><ul class="pal-tokens">{lis}</ul></div>')
    return "\n".join(out)

def people_rows():
    rows = []
    for p, who, jewel in PEOPLE:
        letter = who[0] if not who.startswith("Slot") else p[1]
        vals = (f'--{p} {v(DAY, p)} · letter {v(DAY, p + "-on")}<br>'
                f'stripe {v(DAY, p + "-mark")} <span>/ {v(NIGHT, p + "-mark")}</span><br>'
                f'wash {v(DAY, p + "-soft")} <span>/ {v(NIGHT, p + "-soft")}</span><br>'
                f'ink {v(DAY, p + "-ink")} <span>/ {v(NIGHT, p + "-ink")}</span>')
        rows.append(f'''<li class="pal-person {p}">
  <span class="pal-person__avs" aria-hidden="true"><span class="av av--lg {p}">{letter}</span><span class="av {p}">{letter}</span><span class="av av--sm {p}">{letter}</span></span>
  <span class="pal-person__who"><b>{who}</b><span>{jewel.capitalize()} · <code class="pal-tok__n">--{p}</code></span></span>
  <span class="pal-person__use"><span class="pal-bar"></span><span class="pal-wash"><b>{who}</b> {"Swimming at the Y" if p in ("p1", "p2") else "Her own plan" if p == "p3" else "His own plan" if p == "p4" else "A plan of their own"}</span></span>
  <span class="pal-vals">{vals}</span>
</li>''')
    rows.append(f'''<li class="pal-person p0">
  <span class="pal-person__avs" aria-hidden="true"><span class="av av--lg p0"><svg class="icon"><use href="#i-home"/></svg></span><span class="av p0"><svg class="icon"><use href="#i-home"/></svg></span></span>
  <span class="pal-person__who"><b>Everyone</b><span>Stone, with the house · <code class="pal-tok__n">--everyone</code></span></span>
  <span class="pal-person__use"><span class="pal-bar"></span><span class="pal-wash"><b>Everyone</b> Cannon Beach weekend</span></span>
  <span class="pal-vals">--everyone {v(DAY, "everyone")} <span>/ {v(NIGHT, "everyone")}</span><br>stripe {v(DAY, "everyone-mark")} <span>/ {v(NIGHT, "everyone-mark")}</span><br>wash {v(DAY, "everyone-soft")} <span>/ {v(NIGHT, "everyone-soft")}</span></span>
</li>''')
    return "\n".join(rows)

def strip(kind=None):
    avs = "".join(f'<span class="av av--lg {p}">{(w[0] if not w.startswith("Slot") else p[1])}</span>' for p, w, _ in PEOPLE) + '<span class="av av--lg p0"><svg class="icon"><use href="#i-home"/></svg></span>'
    bars = "".join(f'<i class="{p}"></i>' for p, _, _ in PEOPLE) + '<i class="p0"></i>'
    routes = '<span class="route"><i class="p3"></i><i class="p4"></i></span><span class="route"><i class="p1"></i><i class="p2"></i><i class="p3"></i><i class="p4"></i></span><span class="route"><i class="p5"></i><i class="p6"></i></span><span class="route"><i class="p7"></i><i class="p8"></i></span>'
    cls = f" pal-sim--{kind}" if kind else ""
    return f'<div class="pal-side__row{cls}" aria-hidden="true"><span class="pal-avs">{avs}</span><span class="pal-bars">{bars}</span><span class="pal-bars">{routes}</span></div>'

def cvd_num(kind):
    a = [check["cvd"][f"{t} avatars {kind}"]["closest"][0] for t in ("light", "dark")]
    s = [check["cvd"][f"{t} stripes {kind}"]["closest"][0] for t in ("light", "dark")]
    return f"avatars {min(a)} · stripes {s[0]} day, {s[1]} night"

def side_by_side():
    rows = [("As drawn", "Normal vision", None)] + [(n, "Simulated", k) for n, k in (("Protanopia", "protan"), ("Deuteranopia", "deutan"), ("Tritanopia", "tritan"))]
    out = []
    for name, sub, k in rows:
        out.append(f'<div class="pal-side"><p class="pal-side__l"><b>{name}</b>{sub} · closest {cvd_num(k or "normal")}</p>{strip(k)}</div>')
    return "\n".join(out)

def filters():
    fs = []
    for k, m in MACHADO.items():
        vals = " ".join(" ".join(str(x) for x in row) + " 0 0" for row in m) + " 0 0 0 1 0"
        fs.append(f'<filter id="cvd-{k}" color-interpolation-filters="linearRGB"><feColorMatrix type="matrix" values="{vals}"/></filter>')
    return f'<svg class="pal-filters" aria-hidden="true" focusable="false">{"".join(fs)}</svg>'

def checks():
    c = check["contrast"]; n = sum(len(c[t]) for t in c)
    letters = min((r for t in c for r in c[t] if r[0].endswith("avatar letter")), key=lambda r: r[3])
    worst = {}
    for setn in ("avatars", "stripes"):
        for t in ("light", "dark"):
            worst[(setn, t)] = min((check["cvd"][f"{t} {setn} {k}"]["closest"] + [k] for k in ("protan", "deutan", "tritan")), key=lambda x: x[0])
    fam = min(check["cvd"][f"{t} {s} {k}"]["family4"][0] for t in ("light", "dark") for s in ("avatars", "stripes") for k in ("normal", "protan", "deutan", "tritan"))
    names = {"p1": "Sam", "p2": "Alex", "p3": "Maya", "p4": "Theo", "p5": "slot 5", "p6": "slot 6", "p7": "slot 7", "p8": "slot 8"}
    kinds = {"protan": "protanopia", "deutan": "deuteranopia", "tritan": "tritanopia"}
    def w(key): x = worst[key]; return f"{names[x[1]]} and {names[x[2]]}, {kinds[x[3]]}"
    items = [
        (f"{n - len(check['fail'])}/{n}", "contrast pairs pass, day and night: text at AA (4.5:1), stripes, edges and plates at 3:1."),
        (f"{letters[3]}", f"the weakest avatar letter ({letters[0].split()[0]}); every letter passes AA."),
        (f"{min(worst[('avatars', 'light')][0], worst[('avatars', 'dark')][0])}", f"the closest pair of avatars under any simulation ({w(('avatars', 'light'))}), CIEDE2000."),
        (f"{worst[('stripes', 'light')][0]}", f"the closest day stripes ({w(('stripes', 'light'))})."),
        (f"{worst[('stripes', 'dark')][0]}", f"the closest night stripes ({w(('stripes', 'dark'))})."),
        (f"{fam}", "the closest pair among the family's four (Sam, Alex, Maya, Theo), in any vision, day or night."),
    ]
    return "".join(f"<li><b>{a}</b><span>{b}</span></li>" for a, b in items)

shell = open(os.path.join(ROOT, "type.html")).read()
head, rest = shell.split('    <div class="wrap">', 1)
tail = rest[rest.index("  </main>"):]
head = head.replace("<title>Type · FamilyDB</title>", "<title>Palette · FamilyDB</title>")

body = f'''    <div class="wrap">
      <div class="runhead" aria-hidden="true"><span><b>FamilyDB</b> · Palette</span><span>Saturday 3 October 2026</span></div>
      {filters()}
      <div class="page-head">
        <div><p class="overline">Colour</p><h1>Aubergine &amp; Brass</h1><p class="lede">A well-kept house: warm stone walls and aubergine-black ink, a deep aubergine panel the page sits beside, and brushed brass on whatever you act on next, like the handle on a good door. The family wear jewel tones. Vera keeps her green glass, the one lit thing. Every value here is read from the tokens in <code>style.css</code>; switch your device to dark mode to see the house with the lamps on.</p></div>
      </div>

      <section class="sheet-sec" aria-labelledby="s-idea">
        <h2 id="s-idea">Four materials</h2>
        <p>Each colour on a page is one of four materials, and each material has one job. You can tell what something is by what it is made of before you read it. Colour is never the only cue: late always says “days late”, setup always carries ⚠, you are here is a plate as well as a colour.</p>
        <div class="pal-board">
          <div class="pal-mat pal-mat--band">
            <p class="pal-mat__name">Aubergine</p>
            <p class="pal-mat__job">The panel down the left and the phone's top bar: deep plum-black, lettered in stone. The page sits beside it. Ink is the same aubergine, darkened to near black.</p>
            <div class="pal-mat__foot"><span class="pal-here"><svg class="icon" aria-hidden="true"><use href="#i-home"/></svg>Home</span><span class="pal-plate">3 late</span><span class="pal-mat__val">--band {v(DAY, "band")} / {v(NIGHT, "band")}</span></div>
          </div>
          <div class="pal-mat pal-mat--brass">
            <p class="pal-mat__name">Brass</p>
            <p class="pal-mat__job">What you act on next, and nothing else: you are here, the Tomorrow stamp, today, the rule beside Leave by, the primary button and the underline under a link.</p>
            <div class="pal-mat__foot"><span class="pal-leave"><span>Leave by</span><b>12:30 pm</b></span><span class="btn pal-btn-brass">Add a plan</span></div>
          </div>
          <div class="pal-mat pal-mat--stone">
            <p class="pal-mat__name">Stone</p>
            <p class="pal-mat__job">The page: a warm grey, never cream, with aubergine-black ink, hairline rules and a 3 px rail over every section.</p>
            <div class="pal-mat__foot"><span class="pal-type"><b>Oaks Park roller rink</b><span>Maya and Theo · 27 min drive, south</span><span>Sun 4 Oct, 1 pm</span></span><span class="btn btn--primary">Save the plan</span><a href="#s-signals">A link</a></div>
          </div>
          <div class="pal-mat pal-mat--glass">
            <p class="pal-mat__name">Glass</p>
            <p class="pal-mat__job">Vera's alone, kept at full strength: charcoal glass, a phosphor Send and glow, the lit cursor. Its green-black sits beside aubergine without ever reading as the panel.</p>
            <div class="pal-mat__foot"><span class="pal-glassline"><b>&gt;</b> Plans, reminders, ideas<i></i></span><span class="pal-send"><svg class="icon" aria-hidden="true"><use href="#i-send"/></svg>Send</span></div>
          </div>
        </div>
      </section>

      <section class="sheet-sec" aria-labelledby="s-people">
        <h2 id="s-people">The eight people: jewel tones</h2>
        <p>Sapphire, amethyst, peacock, topaz, peridot, cerulean, tiger’s eye and tanzanite: deep, saturated and grown-up, chosen to sit beside aubergine and brass. No pink, nothing that reads as red (red is late) or as Vera's green, and no gold (gold is brass). Light and deep tones alternate, so neighbours differ in lightness as well as hue. Each has an avatar with its own letter (white or ink, whichever passes AA), a stripe for routes and rules, a wash and an ink for names. Day values first, night after the slash.</p>
        <ul class="pal-people">
{people_rows()}
        </ul>
      </section>

      <section class="sheet-sec" aria-labelledby="s-side">
        <h2 id="s-side">Side by side, and as colour-blind eyes see them</h2>
        <p>Avatars, single stripes and shared routes, then the same row through the Machado simulation of each colour-blindness. Numbers are CIEDE2000 distances for the closest pair (about 5 is a clear difference; under 3 is hard to tell apart). Names and initials always sit beside the colour.</p>
{side_by_side()}
      </section>

      <section class="sheet-sec" aria-labelledby="s-signals">
        <h2 id="s-signals">The signals</h2>
        <p>One colour, one job, and always a word or a shape with it.</p>
        <div class="pal-signals">
          <div class="pal-sig"><div class="pal-sig__show"><span class="late-txt">6 days late</span><span class="badge badge--late">3 late</span></div><div><h3>Late: the only red</h3><p>Late, broken and errors. On the panel, a solid red plate.</p></div></div>
          <div class="pal-sig"><div class="pal-sig__show"><span class="tag tag--look"><svg class="icon" aria-hidden="true"><use href="#i-alert"/></svg>3 steps left</span></div><div><h3>Set up: copper</h3><p>Set this up or needs a look, always with ⚠. Copper is darker and redder than brass and never lit.</p></div></div>
          <div class="pal-sig"><div class="pal-sig__show"><span class="tick tick--done" aria-hidden="true"><span><svg class="icon"><use href="#i-check"/></svg></span></span><span class="tag tag--ok">Working</span></div><div><h3>Done: green</h3><p>A ticked box, Yes!, working. Deeper than Vera's phosphor, and never a person's colour.</p></div></div>
          <div class="pal-sig"><div class="pal-sig__show"><span class="dt dt--today"><span class="dt__wd">Sat</span><span class="dt__d">3</span><span class="dt__m">Oct</span></span><span class="tag tag--when pal-when">Tomorrow</span></div><div><h3>Today and next: brass</h3><p>Today is a brass stamp; the next plan's Tomorrow is a brass plate.</p></div></div>
          <div class="pal-sig"><div class="pal-sig__show"><span class="btn btn--primary">Save the plan</span><a href="#s-tokens">See every token</a></div><div><h3>Act: the primary button and links</h3><p>By day an aubergine plate lettered in brass; at night a brass plate. Links are ink over a brass underline.</p></div></div>
          <div class="pal-sig"><div class="pal-sig__show"><span class="btn btn--quiet pal-focus">Focused</span><span class="pal-glasspill"><b>&gt;</b> Vera is ready</span></div><div><h3>Focus, and Vera</h3><p>The focus ring is plum by day and brass at night (brass on the panel, phosphor on glass). Vera's things are always glass and phosphor.</p></div></div>
        </div>
      </section>

      <section class="sheet-sec" aria-labelledby="s-tokens">
        <h2 id="s-tokens">Every colour token</h2>
        <p>Name, job, and value by day (and at night, under it, where it changes). The people's tokens are in their rows above.</p>
{token_groups()}
      </section>

      <section class="sheet-sec" aria-labelledby="s-checks">
        <h2 id="s-checks">The checks</h2>
        <p>Measured from the tokens by <code>_kit/palette-check.py</code>, both themes.</p>
        <ul class="pal-checks">{checks()}</ul>
      </section>
    </div>
'''
open(os.path.join(ROOT, "palette.html"), "w").write(head + body + tail)
css = re.sub(r"(/\* palette-sheet:begin[^\n]*\*/\n).*?(/\* palette-sheet:end \*/)", lambda m: m.group(1) + sw_classes() + "\n" + m.group(2), css, flags=re.S)
open(os.path.join(ROOT, "style.css"), "w").write(css)
print("wrote palette.html and", len(sw_classes().splitlines()), "swatch classes")
