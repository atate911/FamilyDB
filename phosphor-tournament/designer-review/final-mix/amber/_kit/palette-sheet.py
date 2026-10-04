#!/usr/bin/env python3
# Usage: python3 _kit/palette-sheet.py
# Writes palette.html from the colour tokens in style.css, and rewrites the sheet's own CSS block in
# style.css (between "palette-sheet:start" and "palette-sheet:end"): its swatch classes and the
# colour-blind specimen tokens. Run it again whenever a token changes, so the sheet never lies.
import os, re, sys, html
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from colourlib import contrast, simulate, min_pair, KINDS

css_path = os.path.join(ROOT, "style.css")
css = open(css_path).read()
light_src = css[css.index(":root {"):css.index("@media (prefers-color-scheme: dark)")]
dark_src = css[css.index("@media (prefers-color-scheme: dark)"):]
dark_src = dark_src[:dark_src.index("\n}\n")]
tok = lambda src: dict(re.findall(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})\b", src))
L = tok(light_src); D = {**L, **tok(dark_src)}
P = [f"p{i}" for i in range(1, 9)]
PEOPLE = [("p1", "Sam", "Cobalt", "S"), ("p2", "Alex", "Violet", "A"), ("p3", "Maya", "Teal", "M"), ("p4", "Theo", "Olive", "T"),
          ("p5", "Slot 5", "Plum", "5"), ("p6", "Slot 6", "Sky", "6"), ("p7", "Slot 7", "Walnut", "7"), ("p8", "Slot 8", "Petrol", "8")]

GROUPS = [
    ("s-page", "Page and ink", "A clean, neutral light page and navy-black ink: the panel’s navy at full strength, so the page and the panel read as one set.", [
        ("paper", "the page"), ("paper-2", "wells, hover rows, the weekend wash"), ("card", "inputs, tick boxes"),
        ("ink", "text, ruled heads, picked controls"), ("ink-2", "secondary text, margin times"), ("ink-3", "quiet text, labels"),
        ("line", "hairlines between rows"), ("line-2", "running head and calendar rules"), ("edge", "control edges (3:1)")]),
    ("s-panel", "The panel", "A near-black navy terminal down the left and on the phone’s top bar, with white sign lettering. At night it is a lighter navy than the page, so it still reads as a panel.", [
        ("band", "the panel, the phone top bar"), ("on-band", "panel text"), ("on-band-2", "quiet panel text"),
        ("band-hi", "hover, the account plate"), ("band-line", "panel hairlines"), ("alert-plate", "the late count, white letters")]),
    ("s-amber", "Amber phosphor", "The signal: what you act on next. It is always lit on navy: amber letters on the navy screen, or navy letters on an amber plate. It is never printed on paper, so it can’t be mistaken for the copper of a warning.", [
        ("signal", "you are here, Leave by, Tomorrow, today"), ("on-signal", "letters on the amber plate"), ("screen", "the navy behind lit amber"),
        ("on-today", "today’s date, lit"), ("today-wash", "today’s calendar cell"), ("today-rule", "the rule over today, Leave by’s rule"),
        ("primary", "the one primary button"), ("on-primary", "its label")]),
    ("s-signals", "Late, setup, done, links and focus", "One red, one copper, one green, and ink for everything you press.", [
        ("alert", "late, broken, errors: the only red"), ("alert-soft", "late badge, error tags"), ("warn", "set this up, needs a look: copper"),
        ("warn-soft", "the setup panel"), ("ok", "working, done"), ("ok-soft", "working tags, ok banners"),
        ("link", "links, underlined"), ("link-line", "link underline"), ("focus", "the focus ring (amber at night)")]),
    ("s-vera", "Vera’s glass and the phosphor", "The shadow of FamilyDB’s first, green-phosphor design, at today’s strength: Vera’s charcoal glass, her phosphor Send and glow, the lit cursor, the ready pill. Green-black glass, so it never reads as the navy panel; green light, so it never reads as amber.", [
        ("vera", "Vera’s name and rule on paper"), ("vera-bg", "the done tick, the Yes! stamp"), ("vera-soft", "the ready pill"),
        ("ask-bg", "Ask Vera’s glass"), ("send", "her Send"), ("phosphor", "lit prompt, cursor at night, glow"),
        ("glass", "brand panes"), ("cursor", "the wordmark cursor on paper")]),
]

def esc(s): return html.escape(s, quote=False)
def sw(name, job):
    night = f" · night {D[name]}" if D[name] != L[name] else " · same at night"
    return f'<li><i class="sw-{name}"></i><div><code>--{name}</code><span>{L[name]}{night}</span><small>{esc(job)}</small></div></li>'

# colour-blind numbers
def closest(key, T):
    cols = [T[p + key] for p in P]
    return {k: min_pair(cols, P, (k,)) for k in KINDS}
NAME = {p: f"{n} ({t.lower()})" for p, n, t, _ in PEOPLE}
cvd_rows = []
for label, key, T in (("Avatars (both themes)", "", L), ("Route stripes by day", "-mark", L), ("Route stripes at night", "-mark", D)):
    c = closest(key, T)
    cells = "".join(f"<td><span class=\"fig\">{c[k][0]:.1f}</span><small>{NAME[c[k][2]]}, {NAME[c[k][3]]}</small></td>" for k in ("protan", "deutan", "tritan"))
    cvd_rows.append(f"<tr><th scope=\"row\">{label}</th>{cells}</tr>")

people_rows = []
for p, n, tone, letter in PEOPLE:
    night = f"night soft {D[p+'-soft']} · ink {D[p+'-ink']} · mark {D[p+'-mark']}"
    people_rows.append(f'''<li class="pal-person {p}">
            <span class="av av--lg" aria-hidden="true">{letter}</span>
            <div><b>{n}</b><span class="tone">--{p} · {tone}</span></div>
            <span class="pal-stripe" aria-hidden="true"></span>
            <span class="pal-plan">{n}’s plan</span>
            <p class="pal-vals">{L[p]} · letter {L[p+"-on"]} <b class="fig">{contrast(L[p], L[p+"-on"]):.1f}:1</b><br>soft {L[p+"-soft"]} · ink {L[p+"-ink"]} · mark {L[p+"-mark"]}<br>{night}</p>
          </li>''')
people_rows.append(f'''<li class="pal-person p0">
            <span class="av av--lg" aria-hidden="true"><svg class="icon" aria-hidden="true"><use href="#i-home"/></svg></span>
            <div><b>Everyone</b><span class="tone">--everyone · neutral</span></div>
            <span class="pal-stripe" aria-hidden="true"></span>
            <span class="pal-plan">Everyone’s plan</span>
            <p class="pal-vals">{L["everyone"]} · soft {L["everyone-soft"]} · ink {L["everyone-ink"]} · mark {L["everyone-mark"]}<br>night {D["everyone"]} · soft {D["everyone-soft"]} · ink {D["everyone-ink"]} · mark {D["everyone-mark"]}</p>
          </li>''')

route = lambda extra="": f'<div class="pal-route{extra}" aria-hidden="true">' + "".join(f'<i class="{p}"></i>' for p in P) + "</div>"
cvd_strips = "".join(
    f'<div class="pal-cvd"><span class="label">{lab}</span><div class="pal-route pal-route--av" aria-hidden="true">' + "".join(f'<i class="cvd-{k}-{p}"></i>' for p in P) + "</div></div>"
    for k, lab in (("normal", "Normal vision"), ("protan", "Protanopia"), ("deutan", "Deuteranopia"), ("tritan", "Tritanopia")))

groups_html = "".join(f'''
      <section class="sheet-sec" aria-labelledby="{gid}">
        <h2 id="{gid}">{esc(title)}</h2>
        <p>{esc(lede)}</p>
        <ul class="pal-sw">{"".join(sw(n, j) for n, j in items)}</ul>
      </section>''' for gid, title, lede, items in GROUPS)

# the shell: copied from type.html, so the sheet sits in the same book
shell = open(os.path.join(ROOT, "type.html")).read()
head, rest = shell.split('<main class="main" id="main">', 1)
tail = rest[rest.index("</main>"):]
head = head.replace("<title>Type · FamilyDB</title>", "<title>Palette · FamilyDB</title>")

main = f'''<main class="main" id="main">
    <div class="wrap pal">
      <div class="runhead" aria-hidden="true"><span><b>FamilyDB</b> · Palette</span><span>Saturday 3 October 2026</span></div>

      <div class="page-head">
        <div><p class="overline">Colour</p><h1>Palette</h1><p class="lede">Amber Terminal: a clean light page, navy-black ink and a near-black navy panel, with amber phosphor lighting what you act on next, the way an old amber terminal lit its cursor, while Vera keeps the green one. Every value here is read from the tokens in style.css; switch your device to dark mode to see the night palette.</p></div>
      </div>

      <section class="sheet-sec" aria-labelledby="s-idea">
        <h2 id="s-idea">The idea: two terminals and a page</h2>
        <p>Three things, each with one job. Amber on navy is the family’s own terminal: it lights the next thing to act on. Green on charcoal glass is Vera’s. The page is paper and ink, where the people write in their colours.</p>
        <div class="pal-idea">
          <div class="pal-idea__amber">
            <span class="label">Amber · what you act on next</span>
            <span class="pal-plate"><svg class="icon" aria-hidden="true"><use href="#i-home"/></svg>Home</span>
            <span class="pal-lit">Leave by</span>
            <span class="pal-lit pal-lit--big"><span class="fig">12:30</span> pm</span>
          </div>
          <div class="pal-idea__vera">
            <span class="label">Green · Vera’s</span>
            <span class="pal-phos">&gt; Plans, reminders, ideas: say it the way you’d say it at the table.</span>
            <span class="pal-send"><svg class="icon" aria-hidden="true"><use href="#i-send"/></svg>Send</span>
          </div>
          <div class="pal-idea__paper">
            <span class="label">Paper · the family writes</span>
            <span class="person p3"><span class="av p3" aria-hidden="true">M</span>Maya</span>
            <span class="person p1"><span class="av p1" aria-hidden="true">S</span>Sam</span>
            <span class="late">6 days late</span>
          </div>
        </div>
      </section>

      <section class="sheet-sec" aria-labelledby="s-people">
        <h2 id="s-people">The eight people</h2>
        <p>Mid-deep enamel tones, from warm walnut and olive to cool teal, cobalt and petrol: confident, grown-up and clearly apart. No pink, no pastel, no red (red is late), no bright green (green is Vera’s), no amber (amber is the signal). Each has a letter that passes AA, white or ink. Avatar, route stripe and a one-person plan’s wash, side by side.</p>
        <ul class="pal-people">
          {"".join(people_rows)}
        </ul>
        <p class="label mt-6">All eight as one route stripe</p>
        {route()}
        <p class="label mt-4">On the panel (a kid’s rule, the account plate)</p>
        {route(" pal-route--panel")}
      </section>

      <section class="sheet-sec" aria-labelledby="s-cvd">
        <h2 id="s-cvd">For colour-blind eyes</h2>
        <p>The eight avatars, simulated (Machado 2009). Neighbours differ in lightness as well as hue, so they stay apart. The figures are the closest pair under each simulation (CIEDE2000; under 5 is hard to tell apart, over 10 is clearly different). Names and initials always say who, too.</p>
        {cvd_strips}
        <table class="jobs mt-4">
          <thead><tr><th scope="col">Closest pair</th><th scope="col">Protanopia</th><th scope="col">Deuteranopia</th><th scope="col">Tritanopia</th></tr></thead>
          <tbody>{"".join(cvd_rows)}</tbody>
        </table>
      </section>

      <section class="sheet-sec" aria-labelledby="s-sig">
        <h2 id="s-sig">Signals</h2>
        <p>Each signal has one colour, one form and one job, and always words beside it.</p>
        <ul class="pal-sigs">
          <li><span><span class="greet__date">Saturday 3 October</span></span><p><b>Today</b>: amber lit on the navy screen. Home’s date, the calendar’s day number under an amber rule.</p></li>
          <li><span><span class="leave__l"><svg class="icon" aria-hidden="true"><use href="#i-car"/></svg>Leave by</span></span><p><b>Leave by and Tomorrow</b>: the same lit label over the biggest figure on Home, with an amber rule beside it.</p></li>
          <li><span class="pal-on-band"><span class="pal-plate">Plans</span></span><p><b>You are here</b>: an amber plate on the navy panel, and the navy screen with an amber label on the phone’s tab bar.</p></li>
          <li><span><a class="btn btn--primary" href="#s-sig">Add a plan</a></span><p><b>The one primary button</b>: the navy screen with an amber label by day, an amber plate at night.</p></li>
          <li><span><span class="badge badge--late">3 late</span></span><p><b>Late</b>: the only red. “6 days late” in words, the red rule in the margin, the red plate on the panel.</p></li>
          <li><span><span class="tag tag--look"><svg class="icon" aria-hidden="true"><use href="#i-alert"/></svg>3 steps left</span></span><p><b>Set this up, needs a look</b>: copper, printed on paper with the warning sign. Never lit, never on navy, so it is never the amber signal.</p></li>
          <li><span><span class="tag tag--ok"><svg class="icon" aria-hidden="true"><use href="#i-check"/></svg>Working</span></span><p><b>Done and working</b>: green, the done tick and the “Yes!” stamp.</p></li>
          <li><span><a href="#s-sig">A link</a></span><p><b>Links</b>: navy-black ink with a grey underline that thickens on hover.</p></li>
          <li><span><span class="pal-focus">Focus</span></span><p><b>Focus</b>: a 3 px ring in ink on paper, amber on the panel and at night, phosphor on Vera’s glass.</p></li>
        </ul>
      </section>
{groups_html}
    </div>
  '''
open(os.path.join(ROOT, "palette.html"), "w").write(head + main + tail)

# the sheet's CSS: hand-set rules plus generated swatch and specimen classes
names = sorted({n for _, _, _, items in GROUPS for n, _ in items})
cvd_tokens_l = " ".join(f"--cvd-{k}-{p}: {simulate(L[p], k)};" for k in KINDS for p in P)
block = f"""/* palette-sheet:start (written by _kit/palette-sheet.py; edit the script, not this block) */
/* 5.29 The palette sheet (palette.html) */
:root {{ {cvd_tokens_l} }}
.pal-idea {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--s4); margin-top: var(--s4); }}
.pal-idea > div {{ display: grid; align-content: start; justify-items: start; gap: var(--s3); min-height: 210px; padding: var(--s5); border-radius: var(--r-lg); }}
.pal-idea__amber {{ background: var(--band); color: var(--on-band); }}
.pal-idea__amber .label {{ color: var(--on-band-2); }}
.pal-idea__vera {{ background: var(--glass); color: var(--glass-ink); border-radius: 14px !important; box-shadow: 0 0 0 4px var(--ask-ring), 0 0 24px var(--ask-ring); }}
.pal-idea__vera .label {{ color: var(--glass-ink-2); }}
.pal-idea__paper {{ background: var(--card); color: var(--ink); border: 1px solid var(--line-2); }}
.pal-lit {{ display: inline-flex; align-items: center; gap: 6px; font-family: var(--font-num); font-size: var(--t-sm); font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: var(--signal); text-shadow: 0 0 10px var(--signal-glow); }}
.pal-lit--big {{ font-family: var(--font-head); font-size: 3.5rem; line-height: .9; letter-spacing: 0; text-transform: none; }}
.pal-lit--big .fig {{ font-family: inherit; }}
.pal-plate {{ display: inline-flex; align-items: center; gap: var(--s2); padding: 6px 14px 6px 10px; border-radius: var(--r-sm); background: var(--signal); color: var(--on-signal); font-family: var(--font-num); font-size: 1.25rem; font-weight: 700; }}
.pal-phos {{ font-family: var(--font-mono); font-stretch: 75%; font-size: var(--t-sm); color: var(--glass-ink); }}
.pal-phos::first-letter {{ color: var(--phosphor); text-shadow: 0 0 8px var(--phosphor-glow); }}
.pal-send {{ display: inline-flex; align-items: center; gap: var(--s2); padding: 10px 18px; border-radius: var(--r-md); background: var(--send); color: var(--on-send); font-weight: 700; box-shadow: 0 0 16px var(--phosphor-dim); }}
.pal-idea__paper .person {{ font-weight: 700; color: var(--p-ink); }}
.pal-people {{ list-style: none; margin: var(--s4) 0 0; padding: 0; }}
.pal-person {{ display: grid; grid-template-columns: 44px 10rem 7rem 11rem minmax(0, 1fr); gap: var(--s4); align-items: center; padding: var(--s3) 0; border-top: 1px solid var(--line); }}
.pal-person div > b {{ display: block; font-family: var(--font-num); font-size: 1.25rem; line-height: 1.2; }}
.pal-person .tone {{ font-family: var(--font-mono); font-stretch: 75%; font-size: var(--t-sm); color: var(--p-ink); }}
.pal-stripe {{ height: 8px; border-radius: 4px; background: var(--p-mark); }}
.pal-plan {{ padding: 6px 10px; border-left: 4px solid var(--p-mark); background: var(--p-soft); color: var(--p-ink); font-size: var(--t-meta); font-weight: 700; border-radius: 0 var(--r-sm) var(--r-sm) 0; }}
.pal-vals {{ font-family: var(--font-mono); font-stretch: 75%; font-size: var(--t-sm); line-height: 1.6; color: var(--ink-2); }}
.pal-route {{ display: flex; height: 16px; margin-top: var(--s2); border-radius: 3px; overflow: hidden; }}
.pal-route i {{ flex: 1; background: var(--p-mark); }}
.pal-route--panel {{ height: 32px; padding: 8px; gap: 2px; background: var(--band); border-radius: var(--r-sm); }}
.pal-route--panel i {{ background: var(--p); }}
.pal-route--av {{ height: 40px; gap: 4px; margin-top: 0; border-radius: 0; }}
.pal-route--av i {{ border-radius: var(--r-sm); }}
.pal-cvd {{ display: grid; grid-template-columns: 9rem minmax(0, 1fr); gap: var(--s4); align-items: center; margin-top: var(--s3); }}
.pal-sigs {{ list-style: none; margin: var(--s4) 0 0; padding: 0; display: grid; gap: var(--s3); }}
.pal-sigs li {{ display: grid; grid-template-columns: 13rem minmax(0, 1fr); gap: var(--s5); align-items: center; padding-top: var(--s3); border-top: 1px solid var(--line); }}
.pal-sigs li > span {{ display: flex; }}
.pal-on-band {{ padding: var(--s2); background: var(--band); border-radius: var(--r-sm); width: max-content; }}
.pal-focus {{ display: inline-block; padding: 6px 12px; border: 1.5px solid var(--edge); border-radius: var(--r-md); font-weight: 700; outline: 3px solid var(--focus); outline-offset: 3px; }}
.pal-sw {{ list-style: none; margin: var(--s4) 0 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr)); gap: var(--s4) var(--s5); }}
.pal-sw li {{ display: grid; grid-template-columns: 52px minmax(0, 1fr); gap: var(--s3); align-items: start; }}
.pal-sw i {{ width: 52px; height: 52px; border-radius: var(--r-sm); box-shadow: inset 0 0 0 1px var(--line-2); }}
.pal-sw code {{ display: block; font-family: var(--font-mono); font-stretch: 75%; font-size: var(--t-sm); font-weight: 650; }}
.pal-sw span {{ display: block; font-family: var(--font-mono); font-stretch: 75%; font-size: var(--t-sm); color: var(--ink-2); }}
.pal-sw small {{ display: block; font-size: var(--t-sm); color: var(--ink-3); }}
{chr(10).join(f".sw-{n} {{ background: var(--{n}); }}" for n in names)}
{chr(10).join(f".pal-route .cvd-{k}-{p} {{ background: var(--cvd-{k}-{p}); }}" for k in KINDS for p in P)}
@media (max-width: 820px) {{
  .pal-idea {{ grid-template-columns: minmax(0, 1fr); }}
  .pal-idea > div {{ min-height: 0; }}
  .pal-person {{ grid-template-columns: 44px minmax(0, 1fr); row-gap: var(--s2); }}
  .pal-person > .pal-stripe, .pal-person > .pal-plan, .pal-person > .pal-vals {{ grid-column: 2; }}
  .pal-cvd {{ grid-template-columns: minmax(0, 1fr); gap: var(--s1); }}
  .pal-sigs li {{ grid-template-columns: minmax(0, 1fr); gap: var(--s2); }}
}}
/* palette-sheet:end */"""
if "palette-sheet:start" in css:
    css = re.sub(r"/\* palette-sheet:start.*?palette-sheet:end \*/", lambda m: block, css, flags=re.S)
else:
    css = css.rstrip("\n") + "\n\n" + block + "\n"
open(css_path, "w").write(css)
print("wrote palette.html and the sheet's CSS block")
