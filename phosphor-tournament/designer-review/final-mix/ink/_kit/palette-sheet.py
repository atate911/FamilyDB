# python3 _kit/palette-sheet.py
# Writes palette.html from the tokens in style.css, in the app's shell (taken from type.html).
# Every printed value and every figure is read or measured here, so the sheet can't drift from the CSS.
import os, re, sys, json, subprocess, tempfile, itertools, html
sys.path.insert(0, os.path.dirname(__file__))
from colour import contrast, simulate, de2000, KINDS

root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
css = open(os.path.join(root, "style.css")).read()

def tokens(src):
    return dict((k, v.strip()) for k, v in re.findall(r"--([\w-]+):\s*([^;]+);", src))
a = css.index(":root {"); light = tokens(css[a:css.index("\n}", a)])
d = css.index("@media (prefers-color-scheme: dark)"); dark = dict(light); dark.update(tokens(css[d:css.index("/* ---------- 3. Base", d)]))
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")

tmp = tempfile.mktemp(suffix=".json")
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "palette-check.py"), "--json", tmp], check=True, stdout=subprocess.DEVNULL)
check = json.load(open(tmp)); os.remove(tmp)
npairs = len(check["pairs"]); nfail = sum(not p["ok"] for p in check["pairs"])

PEOPLE = [  # slot, ink, who in the mock family
    (1, "Ultramarine", "Sam", "S"), (2, "Cyan", "Alex", "A"), (3, "Violet", "Maya", "M"), (4, "Tangerine", "Theo", "T"),
    (5, "Chrome yellow", "slot 5", "5"), (6, "Cornflower", "slot 6", "6"), (7, "Grape", "slot 7", "7"), (8, "Umber", "slot 8", "8"),
]
e = html.escape

def chip(name, w=56, h=26):
    dv, nv = light.get(name, ""), dark.get(name, "")
    if not HEX.match(dv):
        return ""
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-hidden="true"><rect width="{w//2}" height="{h}" fill="{dv}"/>'
            f'<rect x="{w//2}" width="{w - w//2}" height="{h}" fill="{nv if HEX.match(nv) else dv}"/></svg>')

def val(name):
    dv, nv = light.get(name, ""), dark.get(name, "")
    return e(dv), e(nv) if nv != dv else "same"

# ---------- the idea: three colours that mean something ----------
faces = "".join(f'<span class="av p{i}" aria-hidden="true">{l}</span>' for i, _, _, l in PEOPLE)
greys = [("paper", "page"), ("paper-2", "wells"), ("line", "hairline"), ("line-2", "rules"), ("edge", "control edge"),
         ("ink-3", "quiet text"), ("ink-2", "second text"), ("ink", "ink"), ("band-hi", "panel plate"), ("band", "the panel")]
grey_html = "".join(f'<div class="g-{n}"><b>{u}</b><code>{light[n]}</code><code>{dark[n]}</code></div>' for n, u in greys)

# ---------- the eight ----------
rows = []
for i, ink, who, l in PEOPLE:
    t = lambda k: light[f"p{i}{k}"]
    n = lambda k: dark.get(f"p{i}{k}", light[f"p{i}{k}"])
    letter = "white" if t("-on").upper() == "#FFFFFF" else "black"
    rows.append(f'''<li class="pal-row p{i}">
  <span class="pal-row__av"><span class="av av--xl p{i}" aria-hidden="true">{l}</span><span class="av p{i}" aria-hidden="true">{l}</span><span class="av av--sm p{i}" aria-hidden="true">{l}</span></span>
  <span class="pal-row__name"><b>{ink}</b><span>--p{i} · {who} · {letter} letter, {contrast(t(""), t("-on")):.1f}:1</span></span>
  <span class="pal-row__ex"><span class="pal-stripe"></span><span class="pal-ev"><span class="m">7 pm</span><em>{who if not who.startswith("slot") else ink}</em>'s plan</span></span>
  <span class="pal-row__val"><code>{t("")}</code> ink · <code>{t("-mark")}</code> stripe · <code>{t("-soft")}</code> wash · <code>{t("-ink")}</code> name<br>night: stripe <code>{n("-mark")}</code> · wash <code>{n("-soft")}</code> · name <code>{n("-ink")}</code></span>
</li>''')

bands = "".join(f'<i class="p{i}"></i>' for i, *_ in PEOPLE)
routes = "".join(f'<span class="route" aria-hidden="true">{"".join(f"<i class=p{j}></i>" for j in combo)}</span>'
                 for combo in [(1, 2), (3, 4), (1, 2, 3, 4), (5, 6, 7, 8), (0,)])

# ---------- colour-blind rows: drawn from simulated values (by day) ----------
def cvd_svg(kind):
    w, out = 560, []
    for k, (i, *_rest) in enumerate(PEOPLE):
        out.append(f'<circle cx="{20 + k * 34}" cy="20" r="15" fill="{simulate(light[f"p{i}"], kind)}"/>')
        out.append(f'<rect x="{292 + k * 33}" y="14" width="31" height="12" fill="{simulate(light[f"p{i}-mark"], kind)}"/>')
    out.append(f'<rect x="292" y="32" width="264" height="4" fill="{simulate(light["alert"], kind)}"/>')
    return f'<svg viewBox="0 0 {w} 40" role="img" aria-label="The eight avatars and stripes as seen with {kind}">{"".join(out)}</svg>'
cvd_rows = "".join(f'<tr><th scope="row"><span class="label">{k}</span></th><td>{cvd_svg(k)}</td></tr>' for k in KINDS)
c = check["cvd"]; s = check["signals"]
def worst(key):
    v = min(((d_, a_, b_, k) for k, (d_, a_, b_) in c[key].items() if k != "normal"))
    return f"{v[0]} ({v[1]} and {v[2]}, {v[3]})"

# ---------- every token ----------
GROUPS = [
    ("Page and ink", [("paper", "the page"), ("paper-2", "wells, hover rows, the weekend"), ("card", "inputs, tick boxes"), ("field", "fields"),
                      ("ink", "text, ruled heads"), ("ink-2", "second text, margin times"), ("ink-3", "quiet text, labels"),
                      ("line", "hairlines"), ("line-2", "running head, rules"), ("rule", "the 3 px section rail"), ("edge", "control edges (3:1)")]),
    ("The panel", [("band", "panel and phone top bar"), ("on-band", "panel letters, you-are-here plate"), ("on-band-2", "quiet panel text"),
                   ("band-hi", "account plate, hover"), ("band-line", "panel hairlines"), ("band-edge", "the panel's edge at night"), ("here", "you-are-here edge (a kid's colour on her pages)")]),
    ("Actions", [("link", "links: ink, underlined"), ("link-line", "a link's underline"), ("primary", "the one primary button"), ("primary-2", "its hover"), ("on-primary", "its words"), ("focus", "the focus ring")]),
    ("Signals", [("alert", "late, broken, errors: the only red"), ("alert-soft", "late badge, Not working"), ("alert-line", "their edge"),
                 ("alert-plate", "late count on the panel"), ("on-alert-plate", "its figure"), ("done", "done tick, strike, Yes!, the meter"), ("on-done", "the tick in it"),
                 ("ok", "Working"), ("ok-soft", "its ground"), ("ok-line", "its edge"), ("warn", "set up, needs a look (with ⚠)"), ("warn-soft", "the setup panel"), ("warn-line", "its edge"),
                 ("today-bg", "today's stamp"), ("on-today", "its figures"), ("today-wash", "today's calendar cell")]),
    ("Vera and the glass", [("vera", "her name and rule"), ("vera-bg", "her tile"), ("on-vera", "on it"), ("vera-soft", "the ready pill"), ("vera-line", "receipts"),
                            ("ask-bg", "Ask Vera's glass"), ("ask-ink", "words on it"), ("ask-ink-2", "her typed line"), ("send", "the phosphor Send"), ("on-send", "Send's word"),
                            ("ask-ring", "the ring round Ask"), ("glass", "panes, the pill, the mark"), ("glass-line", "the glass rim"), ("glass-ink", "pane text"), ("glass-alert", "can't answer"),
                            ("phosphor", "the light"), ("phosphor-glow", "its glow"), ("cursor", "the lit cursor"), ("vs-halo", "her screen's halo")]),
    ("Everyone", [("everyone", "the house avatar"), ("everyone-soft", "Everyone's wash"), ("everyone-ink", "the house"), ("everyone-mark", "Everyone's stripe")]),
]
for i, ink, who, _ in PEOPLE:
    GROUPS.append((f"p{i} · {ink} ({who})", [(f"p{i}", "avatar"), (f"p{i}-on", "its letter"), (f"p{i}-mark", "stripe, rule, dot"), (f"p{i}-soft", "wash"), (f"p{i}-ink", "name")]))
tok_rows = []
for g, items in GROUPS:
    tok_rows.append(f'<tr><th colspan="4" scope="rowgroup">{e(g)}</th><th class="u"></th></tr>' if False else f'<tr><th colspan="5" scope="rowgroup">{e(g)}</th></tr>')
    for name, use in items:
        dv, nv = val(name)
        tok_rows.append(f'<tr><td><code>--{name}</code></td><td>{chip(name)}</td><td><code>{dv}</code></td><td><code>{nv}</code></td><td class="u">{e(use)}</td></tr>')

low_av = min((p for p in check["pairs"] if "avatar letter" in p["use"]), key=lambda p: p["ratio"])

main = f'''
    <div class="wrap">
      <div class="runhead" aria-hidden="true"><span><b>FamilyDB</b> · Palette</span><span>Saturday 3 October 2026</span></div>
      <p class="overline">Palette, round 7</p>
      <h1 class="pal-big">Ink</h1>
      <p class="pal-idea">Almost no colour: a white page, black ink, a black panel and greys only for structure, so the only colours on any screen are the family's eight inks, late red and Vera's green glass. When you see colour, it is a person, it is late, or it is Vera.</p>

      <div class="pal-three">
        <div><h3>The family</h3><div class="pal-faces">{faces}</div><p>Eight inks, the most saturated the app has worn. They carry everything: faces, route stripes, a one-person plan's wash, a kid's own pages.</p></div>
        <div><h3>Late</h3><div class="pal-late-sw">6 days late</div><p>The only red. Always with words: "6 days late", "OVERDUE · 3".</p></div>
        <div><h3>Vera</h3><div class="pal-vera-sw"><span class="ask__prompt">&gt; say it the way you'd say it</span><span class="pal-send">Send</span></div><p>Her green-black glass and phosphor Send: the old CRT, kept at full strength.</p></div>
      </div>

      <section class="sheet-sec" aria-labelledby="h-grey">
        <h2 id="h-grey">Everything else is grey</h2>
        <p>Ten neutrals with no tint at all, from the page to the panel. They draw structure only: rules, edges, wells and quiet words. By day the page is pure white and the ink true black; at night the page is near-black, the ink white, and the panel a deeper black with a hairline edge. Each chip shows its day value, then night.</p>
        <div class="pal-greys">{grey_html}</div>
      </section>

      <section class="sheet-sec" aria-labelledby="h-eight">
        <h2 id="h-eight">The eight inks</h2>
        <p>Avatar, stripe, and a one-person plan, side by side. Each ink keeps its own letter, white or black, whichever reads better (lowest {low_av["ratio"]:.1f}:1). Light and dark inks alternate, so neighbours differ in lightness as well as hue. No pink, no pastel, no red (red is late), no green (green is Vera's). The avatars are the same at night; stripes, washes and names lift so they read on the dark page.</p>
        <ul class="pal-rows">{"".join(rows)}</ul>
      </section>

      <section class="sheet-sec" aria-labelledby="h-together">
        <h2 id="h-together">All eight together</h2>
        <div class="pal-together">
          <div><span class="label">The faces</span><div class="pal-faces pal-faces--sm mt-3">{faces}</div><span class="label mt-4">Every stripe in a row</span><div class="pal-band" aria-hidden="true">{bands}</div></div>
          <div><span class="label">Route stripes as plans use them: two, two, four, four, Everyone</span><div class="pal-routes">{routes}</div></div>
        </div>
      </section>

      <section class="sheet-sec" aria-labelledby="h-cvd">
        <h2 id="h-cvd">For colour-blind eyes</h2>
        <p>The eight faces and their day stripes, simulated (Machado 2009, full strength), with late red underneath. Closest pair, CIEDE2000: faces {worst("avatars")}; day stripes {worst("stripes, day")}; night stripes {worst("stripes, night")}. The family's four faces never come closer than {min(v[0] for v in c["family of four, avatars"].values())}. Names and initials are always beside the colour.</p>
        <table class="pal-cvd"><tbody>{cvd_rows}</tbody></table>
      </section>

      <section class="sheet-sec" aria-labelledby="h-sig">
        <h2 id="h-sig">The signals</h2>
        <p>Only late is a colour. Today and Vera share her green. Everything you press, pick or finish is ink.</p>
        <div class="pal-sigs">
          <div class="pal-sig"><span class="label">Late</span><div class="pal-sig__demo"><span class="pal-late">6 days late</span><span class="pal-plate-panel">To do <span class="pal-plate">3 late</span></span></div><p><code>--alert</code> {light["alert"]} / {dark["alert"]}, plate {light["alert-plate"]} on the black panel ({contrast(light["alert-plate"], light["band"]):.1f}:1).</p></div>
          <div class="pal-sig"><span class="label">Today</span><div class="pal-sig__demo"><span class="pal-today">Saturday 3 October</span></div><p>Vera keeps the date, so today is her green: <code>--today-bg</code> {light["today-bg"]} / {dark["today-bg"]}.</p></div>
          <div class="pal-sig"><span class="label">Vera</span><div class="pal-sig__demo"><span class="pill-health">Vera is ready</span><span class="pal-vera-name">Vera</span></div><p>The ready pill and her name: <code>--vera</code> {light["vera"]} / phosphor {dark["vera"]}.</p></div>
          <div class="pal-sig"><span class="label">Done</span><div class="pal-sig__demo"><span class="pal-donebox" aria-hidden="true"><svg class="icon icon--sm"><use href="#i-check"/></svg></span><span class="pal-done">Call the dentist</span></div><p>Ticked off in ink, struck through in ink. <code>--done</code> is the ink.</p></div>
          <div class="pal-sig"><span class="label">Set up, needs a look</span><div class="pal-sig__demo"><span class="pal-setup">⚠ 3 steps left</span></div><p>Ink on a grey well under an ink rule, always with ⚠ and words. No amber.</p></div>
          <div class="pal-sig"><span class="label">Links, the button, focus</span><div class="pal-sig__demo"><a href="plans.html">All plans</a><a class="btn btn--primary" href="plans.html">Add a plan</a><span class="pal-focus">Focus</span></div><p>Ink, underlined; one black button; a 3 px ink ring (phosphor on glass and on the panel).</p></div>
        </div>
      </section>

      <section class="sheet-sec" aria-labelledby="h-tok">
        <h2 id="h-tok">Every colour token</h2>
        <p>Read from <code>style.css</code> by <code>_kit/palette-sheet.py</code>. The chip is day on the left, night on the right. {npairs} contrast pairs are measured by <code>_kit/palette-check.py</code>: {npairs - nfail} pass (text 4.5:1, edges, stripes and plates 3:1) in both themes.</p>
        <table class="pal-tok">
          <thead><tr><th scope="col">Token</th><th scope="col"><span class="sr">Swatch</span></th><th scope="col">Day</th><th scope="col">Night</th><th scope="col" class="u">Use</th></tr></thead>
          <tbody>{"".join(tok_rows)}</tbody>
        </table>
      </section>
    </div>
'''

shell = open(os.path.join(root, "type.html")).read()
head, rest = shell.split('<main class="main" id="main">', 1)
tail = rest.split("</main>", 1)[1]
head = head.replace("<title>Type · FamilyDB</title>", "<title>Palette · FamilyDB</title>")
if 'id="i-check"' not in head:
    head = head.replace("</svg>\n<header", '<symbol id="i-check" viewBox="0 0 24 24"><path d="M4 12.5l5 5L20 6.5"/></symbol></svg>\n<header', 1)
open(os.path.join(root, "palette.html"), "w").write(head + '<main class="main" id="main">' + main + "  </main>" + tail)
print("palette.html written:", npairs, "pairs,", nfail, "failing")
