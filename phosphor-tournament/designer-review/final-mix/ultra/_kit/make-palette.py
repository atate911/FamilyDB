#!/usr/bin/env python3
# Usage: python3 _kit/make-palette.py
# Builds palette.html (the palette sheet, in the app's shell) and palette.css (its swatch classes)
# from the tokens in style.css, so every value on the sheet is the value the app uses.
# The colour-blind rows are drawn as SVG fills, worked out here with the same simulation as palette-check.py.
import os, re, sys, itertools, html
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
from colour import CVD, lin, delin, hex2rgb, rgb2hex, de, contrast
pc = __import__("palette-check")
css = open(os.path.join(ROOT, "style.css")).read()
L, D = pc.tokens(css)
KINDS = pc.KINDS
PEOPLE = pc.PEOPLE

def sim(h, kind):
    m = CVD[kind]
    if not m: return h
    c = [lin(v) for v in hex2rgb(h)]
    return rgb2hex(tuple(delin(max(0, min(1, sum(m[i][j] * c[j] for j in range(3))))) for i in range(3)))

def val(t):
    a, b = L[t], D[t]
    return f'{a}<br>{b if b != a else "same"}'

def tok(name, job):
    return (f'<li class="pal-tok"><span class="sw sw--{name}" aria-hidden="true"></span>'
            f'<span class="pal-tok__n"><code class="pal-code">--{name}</code><small>{job}</small></span>'
            f'<span class="pal-tok__v mono">{val(name)}</span></li>')

GROUPS = [
    ("g-page", "Page and ink", "A bright white sheet, crisp blue-black ink, cool hairlines. Night is a blue-black sheet with near-white ink.", [
        ("paper", "the page"), ("paper-2", "wells, hover, disabled"), ("card", "inputs and boxes"), ("field", "text fields"),
        ("ink", "text, ruled heads, quiet buttons"), ("ink-2", "secondary text, margin times"), ("ink-3", "quiet text, labels"),
        ("line", "hairlines between rows"), ("line-2", "running head, calendar rules"), ("rule", "the 3 px section rail"),
        ("edge", "control edges (3:1)")]),
    ("g-panel", "The panel", "Midnight ultramarine: the same blue, deep enough to sit under white sign lettering. The phone's top bar is the same.", [
        ("band", "the panel and the phone's top bar"), ("band-hi", "hover and the account plate"), ("band-line", "rules on the panel"),
        ("on-band", "sign lettering; the you-are-here plate"), ("on-band-2", "quiet lettering and icons"),
        ("alert-plate", "the late count, a solid plate"), ("on-alert-plate", "its figure")]),
    ("g-act", "Ultramarine", "One saturated blue for everything the family does. Text and edges use <code class=\"pal-code\">--act</code>; fills use <code class=\"pal-code\">--act-bg</code> under a white letter. At night the text is lifted to a bright periwinkle so it reads on the dark sheet.", [
        ("act", "links, ticks on hover, the date line"), ("act-bg", "the primary button, today, you are here, a ticked box"),
        ("act-bg-2", "its hover"), ("on-act", "letters on it"), ("act-soft", "today's wash on the calendar"), ("act-line", "a link's underline"),
        ("link", "links"), ("link-2", "a link on hover"), ("primary", "the one primary button"), ("today-bg", "today's stamp and ring"),
        ("focus", "the focus ring")]),
    ("g-sig", "Signals", "Red is only late or broken. Amber is something to set up or look at, always with ⚠ and words. Green is done and Vera.", [
        ("alert", "late, broken: text"), ("alert-soft", "its wash"), ("alert-line", "its edge"),
        ("warn", "set this up: text"), ("warn-soft", "the setup panel"), ("warn-line", "its edge"),
        ("ok", "done, working: text"), ("ok-soft", "its wash"), ("ok-line", "its edge")]),
    ("g-vera", "Vera's glass and phosphor", "Unchanged from the brand: charcoal glass, a phosphor Send and glow, the lit cursor. Green-black next to the midnight panel, so the two dark blocks never read as one.", [
        ("ask-bg", "the Ask pane"), ("glass", "her screen, the mark"), ("glass-line", "rules on glass"), ("glass-ink", "words on glass"),
        ("phosphor", "her typed line, the ready dot"), ("send", "Send"), ("on-send", "its label"), ("cursor", "the lit cursor"),
        ("vera", "Vera's name and rule in the chat"), ("vera-bg", "her tile, the spending meter"), ("vera-soft", "her receipts")]),
]

NAMES = [("p1", "Sam", "S", "cerulean"), ("p2", "Alex", "A", "teal"), ("p3", "Maya", "M", "violet"), ("p4", "Theo", "T", "cinnamon"),
         ("p5", "Slot 5", "5", "ochre"), ("p6", "Slot 6", "6", "aubergine"), ("p7", "Slot 7", "7", "sage"), ("p8", "Slot 8", "8", "slate")]

def person_row(p, name, letter, hue):
    on = lambda t: "white" if t[p + "-on"].upper() == "#FFFFFF" else "ink"
    return (f'<li class="pal-person {p}"><span class="av av--lg {p}" aria-hidden="true">{letter}</span>'
            f'<span class="pal-person__n"><b>{name}</b><small>{hue} · <code class="pal-code">--{p}</code></small></span>'
            f'<span class="pal-bar" aria-hidden="true"></span>'
            f'<span class="pal-wash"><span class="av av--sm {p}" aria-hidden="true">{letter}</span>{name}</span>'
            f'<span class="pal-person__v mono">{L[p]} · {on(L)} {contrast(L[p + "-on"], L[p]):.1f}<br>{D[p]} · {on(D)} {contrast(D[p + "-on"], D[p]):.1f}</span></li>')

def cvd_rows(t, theme):
    cols = [t[p] for p in PEOPLE] + [t["everyone"]]
    out = []
    for k in KINDS:
        best = min((de(cols[a], cols[b], k), a, b) for a, b in itertools.combinations(range(9), 2))
        label = {"normal": "Normal", "protan": "Protanopia", "deutan": "Deuteranopia", "tritan": "Tritanopia"}[k]
        names = [n[1] for n in NAMES] + ["Everyone"]
        dots = "".join(f'<circle cx="{18 + i * 40}" cy="18" r="16" fill="{sim(c, k)}"/>' for i, c in enumerate(cols))
        out.append(f'<li class="pal-cvd__row"><span class="pal-cvd__k">{label}</span>'
                   f'<svg class="pal-cvd__dots" viewBox="0 0 356 36" role="img" aria-label="The eight colours and Everyone as seen with {label.lower()}">{dots}</svg>'
                   f'<span class="pal-cvd__d mono">closest {best[0]:.1f}<small>{names[best[1]]} / {names[best[2]]}</small></span></li>')
    return f'<div class="pal-cvd__theme pal-cvd__theme--{theme}"><p class="overline">{"By day" if theme == "day" else "At night"}</p><ul class="plain pal-cvd">' + "".join(out) + "</ul></div>"

# measured figures for the sheet
fails, n = 0, 0
for t in (L, D):
    for label, f, b, floor in pc.pairs(t):
        n += 1; fails += contrast(t[f], t[b]) < floor
def closest(t, suf):
    cols = {p: t[p + suf] for p in PEOPLE}; cols["everyone"] = t["everyone" + ("-mark" if suf else "")]
    return min((de(cols[a], cols[b], k), a, b, k) for k in KINDS for a, b in itertools.combinations(cols, 2))
cl = [closest(L, ""), closest(L, "-mark"), closest(D, ""), closest(D, "-mark")]
low = min(c[0] for c in cl)
letters = min(contrast(t[p + "-on"], t[p]) for t in (L, D) for p in PEOPLE)

body = f'''
      <div class="runhead" aria-hidden="true"><span><b>FamilyDB</b> · Palette</span><span>Saturday 3 October 2026</span></div>

      <div class="page-head">
        <div><p class="overline">Specimen</p><h1>Palette: Ultramarine</h1><p class="lede">One saturated ink-blue for everything the family does: <a href="#s-act">links</a>, the one primary button, you are here, today and a ticked box. A midnight panel sits under it, the page is bright white and the ink is crisp. People get every colour but blue, so the ultramarine is always the family's. Vera keeps her phosphor glass. Red only ever means late.</p></div>
      </div>

      <section class="sheet-sec" aria-labelledby="s-idea">
        <h2 id="s-idea">Six colours, six jobs</h2>
        <p>Each colour on a page has one job, so you can read a screen by its colours before you read its words. Colour is never the only cue: each one also comes with a word, an icon or a shape.</p>
        <ul class="plain pal-five mt-4">
          <li class="pal-five__i pal-five__i--act"><b>Ultramarine</b><span>What the family does: links, Add, you are here, today, done.</span><span class="mono">{L["act-bg"]} · {D["act-bg"]}</span></li>
          <li class="pal-five__i pal-five__i--band"><b>Midnight</b><span>Where you are: the panel and the phone's top bar.</span><span class="mono">{L["band"]} · {D["band"]}</span></li>
          <li class="pal-five__i pal-five__i--sheet"><b>White and ink</b><span>The page and what's written on it.</span><span class="mono">{L["paper"]} / {L["ink"]}</span></li>
          <li class="pal-five__i pal-five__i--pens"><b>Eight pens</b><span>Who: avatars, route stripes, a kid's own pages.</span><span class="pal-five__dots" aria-hidden="true">{"".join(f'<i class="{p}"></i>' for p in PEOPLE)}</span></li>
          <li class="pal-five__i pal-five__i--vera"><b>Phosphor</b><span>Vera, on her glass. Nobody else is green.</span><span class="mono">{L["phosphor"]}</span></li>
          <li class="pal-five__i pal-five__i--late"><b>Red</b><span>Late, and only late.</span><span class="mono">plate {L["alert-plate"]}<br>text {L["alert"]} · {D["alert"]}</span></li>
        </ul>
      </section>

      <section class="sheet-sec" aria-labelledby="s-act">
        <h2 id="s-act">Ultramarine at work</h2>
        <p>The real parts of the app, as they are drawn. Each is the family doing something, so each is the same blue.</p>
        <div class="pal-work mt-4">
          <figure class="pal-work__i"><div class="side pal-mini"><ul class="nav"><li><a href="#s-act"><svg class="icon" aria-hidden="true"><use href="#i-home"/></svg><span>Home</span></a></li><li><a href="#s-act" aria-current="page"><svg class="icon" aria-hidden="true"><use href="#i-cal"/></svg><span>Plans</span></a></li></ul></div><figcaption>You are here: a white plate on the panel with an ultramarine edge</figcaption></figure>
          <figure class="pal-work__i"><a class="btn btn--primary" href="#s-act"><svg class="icon" aria-hidden="true"><use href="#i-plus"/></svg>Add a plan</a><figcaption>The one primary button</figcaption></figure>
          <figure class="pal-work__i"><p><a href="#s-act">See all plans</a> and <a class="pal-hover" href="#s-act">a link on hover</a></p><figcaption>Links, underlined</figcaption></figure>
          <figure class="pal-work__i"><span class="dt dt--today"><span class="dt__wd">Today</span><span class="dt__d">3</span><span class="dt__m">Oct</span></span><figcaption>Today's stamp</figcaption></figure>
          <figure class="pal-work__i"><span class="pal-ticks"><span class="tick"><span><svg class="icon" aria-hidden="true"><use href="#i-check"/></svg></span></span><span class="tick tick--done"><span><svg class="icon" aria-hidden="true"><use href="#i-check"/></svg></span></span></span><figcaption>A box, then ticked</figcaption></figure>
          <figure class="pal-work__i"><nav class="seg" aria-label="View (sample)"><a href="#s-act" aria-current="page"><svg class="icon icon--sm" aria-hidden="true"><use href="#i-grid"/></svg>Month</a><a href="#s-act"><svg class="icon icon--sm" aria-hidden="true"><use href="#i-list"/></svg>List</a></nav><figcaption>A tab switch</figcaption></figure>
          <figure class="pal-work__i"><span class="btn btn--quiet pal-focus">Focused</span><figcaption>The focus ring</figcaption></figure>
        </div>
      </section>

      <section class="sheet-sec" aria-labelledby="s-people">
        <h2 id="s-people">The eight people and Everyone</h2>
        <p>Every colour but blue, which belongs to the family's actions, and none red, pink or green. By day dark and mid colours alternate, so neighbours differ in lightness as well as hue; dark ones take a white letter and mid ones an ink letter. At night every colour is lifted and takes an ink letter. The avatar, the stripe and the rule are the same colour. Each value below is day, then night, with the letter's contrast.</p>
        <ul class="plain pal-people mt-4">
          {"".join(person_row(*n) for n in NAMES)}
          <li class="pal-person p0"><span class="av av--lg p0" aria-hidden="true"><svg class="icon" aria-hidden="true"><use href="#i-home"/></svg></span><span class="pal-person__n"><b>Everyone</b><small>grey, with the house · <code class="pal-code">--everyone</code></small></span><span class="pal-bar" aria-hidden="true"></span><span class="pal-wash"><span class="av av--sm p0" aria-hidden="true"><svg class="icon" aria-hidden="true"><use href="#i-home"/></svg></span>Everyone</span><span class="pal-person__v mono">{L["everyone"]} · stripe {L["everyone-mark"]}<br>{D["everyone"]} · stripe {D["everyone-mark"]}</span></li>
        </ul>
      </section>

      <section class="sheet-sec" aria-labelledby="s-routes">
        <h2 id="s-routes">Route stripes</h2>
        <p>A plan's people as one 6 px bar, split into their colours, the way Home, Coming up and the calendar draw them. The faces and names always sit beside it.</p>
        <ul class="plain pal-routes mt-4">
          <li><span class="route" aria-hidden="true"><i class="p1"></i><i class="p2"></i></span><span>Sam and Alex</span></li>
          <li><span class="route" aria-hidden="true"><i class="p3"></i><i class="p4"></i></span><span>Maya and Theo</span></li>
          <li><span class="route" aria-hidden="true"><i class="p1"></i><i class="p2"></i><i class="p3"></i><i class="p4"></i></span><span>The four of them</span></li>
          <li><span class="route" aria-hidden="true"><i class="p0"></i></span><span>Everyone</span></li>
          <li><span class="route" aria-hidden="true"><i class="p5"></i><i class="p6"></i><i class="p7"></i><i class="p8"></i></span><span>Slots 5 to 8</span></li>
        </ul>
      </section>

      <section class="sheet-sec" aria-labelledby="s-cvd">
        <h2 id="s-cvd">As colour-blind eyes see them</h2>
        <p>The eight avatars and Everyone, simulated (Machado 2009) and measured with CIEDE2000; under about 6 two colours start to look alike. The closest pair anywhere, avatars or stripes, day or night, is <b>{low:.1f}</b>. Names and faces still say who is who.</p>
        <div class="pal-cvd-wrap mt-4">{cvd_rows(L, "day")}{cvd_rows(D, "night")}</div>
      </section>

      <section class="sheet-sec" aria-labelledby="s-sig">
        <h2 id="s-sig">Signals</h2>
        <p>Each one also says it in words or with an icon.</p>
        <ul class="plain pal-sig mt-4">
          <li><span><span class="late">6 days late</span> <span class="badge badge--late">3 late</span></span><span><b>Late</b>: the only red</span></li>
          <li><span><span class="tag tag--look"><svg class="icon" aria-hidden="true"><use href="#i-alert"/></svg>3 steps left</span></span><span><b>Set this up</b>: amber, with ⚠</span></li>
          <li><span><span class="tag tag--ok"><svg class="icon" aria-hidden="true"><use href="#i-check"/></svg>Working</span></span><span><b>Done, working</b>: green on its wash</span></li>
          <li><span><span class="tag tag--broken"><svg class="icon" aria-hidden="true"><use href="#i-alert"/></svg>Not working</span></span><span><b>Broken</b>: red on its wash</span></li>
          <li><span><span class="dt dt--today dt--sm"><span class="dt__wd">Today</span><span class="dt__d">3</span><span class="dt__m">Oct</span></span></span><span><b>Today</b>: the ultramarine stamp</span></li>
          <li><span><a class="btn btn--primary btn--sm" href="#s-sig">Save</a> <a class="btn btn--quiet btn--sm" href="#s-sig">Cancel</a></span><span><b>The one primary</b>: solid ultramarine; quiet buttons are edged</span></li>
        </ul>
      </section>

      <section class="sheet-sec" aria-labelledby="s-glass">
        <h2 id="s-glass">Vera's glass beside the panel</h2>
        <p>The two dark blocks on every desktop page. The panel is midnight blue and square; Vera's glass is green-black, rounded, ringed and lit in phosphor. They are close in value (about {contrast(L["band"], L["glass"]):.1f}:1) but far apart in hue.</p>
        <div class="pal-glass mt-4">
          <div class="side pal-mini pal-mini--tall"><span class="brand"><svg class="mark-fdb" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="8" fill="#0E1312"/><g transform="translate(4 4)" fill="none" stroke="#6DFF9C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="3" width="19" height="13.5" rx="3.5"/><path d="M12 16.5V21M8.5 21h7M9 8.25v1.25M15 8.25v1.25M9 12.25c1.7 1.35 4.3 1.35 6 0"/></g></svg><b class="wm">FamilyDB<span class="wm__cur" aria-hidden="true"></span></b></span><ul class="nav"><li><a href="#s-glass" aria-current="page"><svg class="icon" aria-hidden="true"><use href="#i-home"/></svg><span>Home</span></a></li><li><a href="#s-glass"><svg class="icon" aria-hidden="true"><use href="#i-todo"/></svg><span>To do</span><span class="badge badge--late">3 late</span></a></li></ul></div>
          <section class="ask pal-ask" aria-label="Ask Vera (sample)"><div class="ask__head"><svg class="vs vs--xl" width="56" height="56" viewBox="0 0 56 56" aria-hidden="true" focusable="false"><rect class="vs__bg" width="56" height="56" rx="14"/><rect class="vs__rim" x=".5" y=".5" width="55" height="55" rx="13.5"/><g class="vs__rows"><rect class="vs__r" x="10" y="9" width="20" height="4" rx="2.0"/><rect class="vs__r" x="33" y="9" width="12" height="4" rx="2.0"/><rect class="vs__r" x="10" y="16" width="11" height="4" rx="2.0"/><rect class="vs__r" x="24" y="16" width="18" height="4" rx="2.0"/><rect class="vs__r vs__r--new" x="10" y="23" width="16" height="4" rx="2.0"/><rect class="vs__r vs__r--new" x="29" y="23" width="8" height="4" rx="2.0"/></g><polyline class="vs__p" points="10.5,32.5 16.5,38.25 10.5,44" stroke-width="3"/><rect class="vs__c" x="21" y="31" width="9.5" height="14" rx="1"/></svg><div><h3>Ask Vera</h3><p class="ask__line"><span class="ask__prompt" aria-hidden="true">&gt;</span> The glass, the lit cursor and her Send.</p></div></div><div class="composer__row"><span class="pal-field">Ask or tell Vera…</span><span class="btn composer__send"><svg class="icon" aria-hidden="true"><use href="#i-send"/></svg><span class="lbl">Send</span></span></div></section>
        </div>
      </section>

      {"".join(f"""<section class="sheet-sec" aria-labelledby="{gid}">
        <h2 id="{gid}">{title}</h2>
        <p>{intro} Day value on top, night below.</p>
        <ul class="plain pal-toks mt-3">{"".join(tok(n, j) for n, j in items)}</ul>
      </section>""" for gid, title, intro, items in GROUPS)}

      <section class="sheet-sec" aria-labelledby="s-pv">
        <h2 id="s-pv">People, every variant</h2>
        <p>The avatar colour, its letter, the wash, the ink for names on the wash and the page, and the mark for stripes and rules. Day value on top, night below.</p>
        <ul class="plain pal-toks mt-3">{"".join(tok(f"{p}{s}", f"{n}: {j}") for p, n, _, _ in NAMES for s, j in (("", "avatar, a kid's tab"), ("-on", "the letter"), ("-soft", "the wash"), ("-ink", "names"), ("-mark", "stripes, rules")))}{"".join(tok(f"everyone{s}", f"Everyone: {j}") for s, j in (("", "avatar"), ("-soft", "the wash"), ("-ink", "names, the house"), ("-mark", "the stripe")))}</ul>
      </section>

      <section class="sheet-sec" aria-labelledby="s-checks">
        <h2 id="s-checks">Measured</h2>
        <p><code class="pal-code">python3 _kit/palette-check.py</code> reads these tokens from <code class="pal-code">style.css</code>. {n} contrast pairs in the two themes, {fails} below their floor: text passes AA (4.5:1), and control edges, stripes and plates pass 3:1. The weakest avatar letter is {letters:.1f}:1. Closest colour-blind pair: avatars {cl[0][0]:.1f} by day and {cl[2][0]:.1f} at night, stripes {cl[1][0]:.1f} by day and {cl[3][0]:.1f} at night.</p>
      </section>
'''

src = open(os.path.join(ROOT, "type.html")).read()
head, rest = src.split('<div class="wrap">', 1)
tail = rest[rest.index("  </main>"):]
head = head.replace("<title>Type · FamilyDB</title>", "<title>Palette · FamilyDB</title>")
head = head.replace('<link rel="stylesheet" href="style.css">', '<link rel="stylesheet" href="style.css">\n<link rel="stylesheet" href="palette.css">')
head = head.replace("<body>", '<body class="page-palette">', 1)
open(os.path.join(ROOT, "palette.html"), "w").write(head + '<div class="wrap">' + body + "    </div>\n" + tail)

# palette.css: the sheet's own classes. Swatches point at the live tokens, so they switch with the theme.
names = sorted({n for _, _, _, items in GROUPS for n, _ in items} | {f"{p}{s}" for p in PEOPLE for s in ("", "-on", "-soft", "-ink", "-mark")} | {f"everyone{s}" for s in ("", "-soft", "-ink", "-mark")})
sw = "\n".join(f".sw--{n} {{ --sw: var(--{n}); }}" for n in names)
open(os.path.join(ROOT, "palette.css"), "w").write(f"""/* palette.css: the palette sheet only (palette.html). Built by _kit/make-palette.py; edit that, not this. */
.pal-code {{ font-family: var(--font-mono); font-stretch: 75%; font-size: .92em; }}
.sw {{ width: 44px; height: 44px; border-radius: var(--r-md); background: var(--sw); box-shadow: inset 0 0 0 1px var(--line-2); flex: none; }}
{sw}

/* five colours, five jobs */
.pal-five {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: var(--s2); }}
.pal-five__i {{ display: flex; flex-direction: column; gap: var(--s2); min-height: 196px; padding: var(--s4); border-radius: var(--r-md); }}
.pal-five__i b {{ font-family: var(--font-head); font-size: var(--t-h3); line-height: 1.1; }}
.pal-five__i span {{ font-size: var(--t-meta); line-height: 1.35; }}
.pal-five__i .mono {{ margin-top: auto; font-size: var(--t-sm); }}
.pal-five__i--act {{ background: var(--act-bg); color: var(--on-act); }}
.pal-five__i--band {{ background: var(--band); color: var(--on-band); }}
.pal-five__i--sheet {{ background: var(--paper); color: var(--ink); box-shadow: inset 0 0 0 1.5px var(--edge); }}
.pal-five__i--pens {{ background: var(--paper); color: var(--ink); box-shadow: inset 0 0 0 1.5px var(--line-2); }}
.pal-five__i--vera {{ background: var(--glass); color: var(--glass-ink); box-shadow: inset 0 0 0 1.5px var(--phosphor-dim), 0 0 0 3px var(--ask-ring); }}
.pal-five__i--vera b, .pal-five__i--vera .mono {{ color: var(--phosphor); }}
.pal-five__i--late {{ background: var(--alert-plate); color: var(--on-alert-plate); }}
.pal-five__dots {{ margin-top: auto; display: grid; grid-template-columns: repeat(4, 22px); gap: 6px; }}
.pal-five__dots i {{ width: 22px; height: 22px; border-radius: 50%; background: var(--p); }}

/* ultramarine at work */
.pal-work {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--s5) var(--s6); align-items: start; }}
.pal-work__i {{ margin: 0; display: grid; gap: var(--s2); justify-items: start; }}
.pal-work__i figcaption {{ font-size: var(--t-sm); color: var(--ink-3); }}
.pal-mini {{ width: 220px; padding: var(--s3) var(--s2); border-radius: var(--r-sm); }}
.pal-mini--tall {{ width: auto; display: flex; flex-direction: column; gap: var(--s3); padding: var(--s4) var(--s3); }}
.pal-hover {{ color: var(--link-2); text-decoration-color: currentColor; text-decoration-thickness: 2px; }}
.pal-ticks {{ display: inline-flex; gap: var(--s3); }}
.pal-focus {{ outline: 3px solid var(--focus); outline-offset: 3px; }}

/* people */
.pal-people {{ display: grid; }}
.pal-person {{ display: grid; grid-template-columns: 40px minmax(0, 12rem) minmax(80px, 1fr) minmax(0, 9rem) auto; gap: var(--s4); align-items: center; padding: var(--s3) 0; border-top: 1px solid var(--line); }}
.pal-person__n b {{ display: block; font-family: var(--font-num); font-size: 1.25rem; line-height: 1.1; }}
.pal-person__n small, .pal-tok__n small {{ display: block; font-size: var(--t-sm); color: var(--ink-3); }}
.pal-bar {{ height: 6px; border-radius: 3px; background: var(--p-mark); }}
.pal-wash {{ display: inline-flex; align-items: center; gap: var(--s2); justify-self: start; padding: 4px 10px 4px 4px; border-radius: var(--r-pill); background: var(--p-soft); color: var(--p-ink); font-weight: 700; font-size: var(--t-meta); }}
.pal-wash .av {{ border-color: var(--p-soft); }}
.pal-person__v {{ font-size: var(--t-sm); color: var(--ink-2); text-align: right; line-height: 1.5; }}

/* routes */
.pal-routes {{ display: flex; flex-wrap: wrap; gap: var(--s4) var(--s7); }}
.pal-routes li {{ display: flex; align-items: center; gap: var(--s3); }}
.pal-routes .route {{ min-height: 56px; }}

/* colour-blind rows */
.pal-cvd-wrap {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--s6); }}
.pal-cvd__theme {{ padding: var(--s4); border-radius: var(--r-md); }}
.pal-cvd__theme--day {{ background: {L["paper"]}; color: {L["ink"]}; box-shadow: inset 0 0 0 1px var(--line-2); }}
.pal-cvd__theme--night {{ background: {D["paper"]}; color: {D["ink"]}; box-shadow: inset 0 0 0 1px var(--line-2); }}
.pal-cvd__theme .overline {{ color: inherit; }}
.pal-cvd {{ display: grid; gap: var(--s3); margin-top: var(--s2); }}
.pal-cvd__row {{ display: grid; grid-template-columns: 7.5rem minmax(0, 1fr) 6.5rem; gap: var(--s3); align-items: center; }}
.pal-cvd__k {{ font-size: var(--t-sm); font-weight: 700; }}
.pal-cvd__dots {{ width: 100%; max-width: 356px; height: auto; }}
.pal-cvd__d {{ font-size: var(--t-sm); }}
.pal-cvd__d small {{ display: block; font-family: var(--font-text); }}

/* signals */
.pal-sig {{ display: grid; }}
.pal-sig li {{ display: grid; grid-template-columns: minmax(0, 18rem) minmax(0, 1fr); gap: var(--s4); align-items: center; padding: var(--s3) 0; border-top: 1px solid var(--line); }}
.pal-sig li > span:first-child {{ display: flex; flex-wrap: wrap; gap: var(--s2); align-items: center; }}

/* the two dark blocks */
.pal-glass {{ display: grid; grid-template-columns: 248px minmax(0, 1fr); gap: var(--s5); align-items: start; }}
.pal-ask h3 {{ font-size: var(--t-h2); }}
.pal-ask .composer__row {{ display: flex; gap: var(--s3); margin-top: var(--s3); }}
.pal-field {{ flex: 1; min-height: 56px; padding: var(--s3) var(--s4); border-radius: var(--r-md); background: var(--field); color: var(--ink-3); border: 1.5px solid var(--ask-edge); }}

/* tokens */
.pal-toks {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: var(--s7); }}
.pal-tok {{ display: grid; grid-template-columns: 44px minmax(0, 1fr) auto; gap: var(--s3); align-items: center; padding: var(--s2) 0; border-top: 1px solid var(--line); }}
.pal-tok__v {{ font-size: var(--t-sm); color: var(--ink-2); text-align: right; line-height: 1.45; }}

@media (max-width: 1180px) {{ .pal-five {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }} .pal-cvd-wrap {{ grid-template-columns: minmax(0, 1fr); }} }}
@media (max-width: 820px) {{
  .pal-five {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .pal-five__i {{ min-height: 0; }}
  .pal-toks {{ grid-template-columns: minmax(0, 1fr); }}
  .pal-person {{ grid-template-columns: 40px minmax(0, 1fr) auto; }}
  .pal-person .pal-bar {{ grid-column: 1 / -1; grid-row: 2; }}
  .pal-person .pal-wash {{ grid-column: 2; grid-row: 3; }}
  .pal-person__v {{ grid-column: 3; grid-row: 1; }}
  .pal-sig li {{ grid-template-columns: minmax(0, 1fr); gap: var(--s2); }}
  .pal-glass {{ grid-template-columns: minmax(0, 1fr); }}
  .pal-cvd__row {{ grid-template-columns: minmax(0, 1fr) 6rem; }}
  .pal-cvd__dots {{ grid-column: 1 / -1; grid-row: 2; }}
}}
""")
print("wrote palette.html and palette.css")
