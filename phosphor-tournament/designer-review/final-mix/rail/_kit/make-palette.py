#!/usr/bin/env python3
"""Build palette.html from the tokens in style.css, so the page can never disagree with them.
It reuses 404.html's shell (sprite, panel, top and tab bars), and writes the swatch classes
(.sw--<token>) into style.css between the PALETTE-SWATCHES markers.
Usage: python3 _kit/make-palette.py"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from colourlib import contrast
root = os.path.join(os.path.dirname(__file__), "..")
css_path = os.path.join(root, "style.css")
css = open(css_path).read()
def block(start):
    i = css.index(start); i = css.index("{", i) + 1; depth = 1; j = i
    while depth:
        depth += {"{": 1, "}": -1}.get(css[j], 0); j += 1
    return css[i:j - 1]
tok = lambda text: {k: v.strip() for k, v in re.findall(r"--([\w-]+):\s*([^;]+);", text)}
light = tok(block(":root {")); dark = dict(light); dark.update(tok(block("@media (prefers-color-scheme: dark)")))
def val(t, n):
    v = t[n]
    while v.startswith("var("): v = t[v[6:-1]]
    return v
used = []
def sw(name, use):
    used.append(name)
    l, d = val(light, name), val(dark, name)
    night = "same at night" if l == d else f"night {d}"
    return (f'<li class="sw"><span class="sw__chip sw--{name}" aria-hidden="true"></span>'
            f'<span class="sw__t"><b>--{name}</b><span class="mono">{l} · {night}</span><span class="sw__use">{use}</span></span></li>')
def group(title, hid, intro, items):
    return (f'<section class="card" aria-labelledby="{hid}"><div class="card__head"><h2 id="{hid}">{title}</h2></div>'
            f'<p class="pal-intro">{intro}</p><ul class="swatches">' + "".join(sw(n, u) for n, u in items) + "</ul></section>")

PEOPLE = [("p1", "Cobalt", "Sam", "S"), ("p2", "Violet", "Alex", "A"), ("p3", "Plum", "Maya", "M"), ("p4", "Tangerine", "Theo", "T"),
          ("p5", "Petrol", "Slot 5", "5"), ("p6", "Sky", "Slot 6", "6"), ("p7", "Sand", "Slot 7", "7"), ("p8", "Chestnut", "Slot 8", "8")]

page = []
page.append('<div class="page-head"><div><h1>Palette</h1><p class="lede">Rail yellow: a deep rail-blue panel, a crisp light page, blue-black ink, and one signal yellow for what you act on next. Every value here is read from the tokens in <span class="code">style.css</span>; switch your device to dark mode to see the night palette.</p></div></div>')

# people first: what the family will look for
rows = []
for p, hue, who, letter in PEOPLE:
    on = contrast(val(light, p + "-on"), val(light, p))
    rows.append(f'<li class="pal-person {p}"><span class="av av--lg {p}" aria-hidden="true">{letter}</span>'
                f'<span class="pal-person__t"><b>{who}</b><span class="mono">--{p} · {hue}</span></span>'
                f'<span class="pal-stripe" aria-hidden="true"></span>'
                f'<span class="pal-soft">{who}’s plan</span>'
                f'<span class="pal-vals mono">{val(light, p)} · on {val(light, p + "-on")} {on:.1f}:1<br>soft {val(light, p + "-soft")} · ink {val(light, p + "-ink")} · mark {val(light, p + "-mark")}<br>night: soft {val(dark, p + "-soft")} · ink {val(dark, p + "-ink")} · mark {val(dark, p + "-mark")}</span></li>')
rows.append(f'<li class="pal-person p0"><span class="av av--lg p0" aria-hidden="true"><svg class="icon" aria-hidden="true"><use href="#i-home"/></svg></span>'
            f'<span class="pal-person__t"><b>Everyone</b><span class="mono">--everyone · neutral</span></span><span class="pal-stripe" aria-hidden="true"></span>'
            f'<span class="pal-soft">Everyone’s plan</span><span class="pal-vals mono">{val(light, "everyone")} · soft {val(light, "everyone-soft")} · ink {val(light, "everyone-ink")} · mark {val(light, "everyone-mark")}<br>night: {val(dark, "everyone")} · soft {val(dark, "everyone-soft")} · mark {val(dark, "everyone-mark")}</span></li>')
route = "".join(f'<i class="{p}"></i>' for p, *_ in PEOPLE)
page.append('<section class="card" aria-labelledby="h-people"><div class="card__head"><h2 id="h-people">The eight people</h2></div>'
            '<p class="pal-intro">Enamel colours, mid to deep, each with the letter colour that reads best on it (white or ink). Avatar, route stripe and a one-person plan’s wash, side by side. No pink, no red, no green: red is late and green is Vera’s.</p>'
            '<ul class="plain pal-people">' + "".join(rows) + '</ul>'
            '<p class="label mt-5">All eight as one route stripe</p><span class="pal-route" aria-hidden="true">' + route + '</span>'
            '<p class="label mt-5">On the panel (a kid’s rule)</p><span class="pal-route pal-route--band" aria-hidden="true">' + route + '</span></section>')

# signals, drawn with the real components
page.append('<section class="card" aria-labelledby="h-signals"><div class="card__head"><h2 id="h-signals">Signals</h2></div>'
            '<p class="pal-intro">Each signal has one colour and one job, and always words beside it.</p><ul class="plain pal-signals">'
            '<li><span class="greet__date">Saturday 3 October</span><span><b>Today and what’s next</b>: signal yellow, only as a solid plate under dark letters (today’s date, the calendar’s day, Leave by, you are here on the panel).</span></li>'
            '<li><span class="leave__l"><svg class="icon" aria-hidden="true"><use href="#i-car"/></svg>Leave by</span><span><b>Leave by</b>: the same plate over the biggest figure on Home.</span></li>'
            '<li><span class="badge badge--late">3 late</span><span><b>Late</b>: the only red. “6 days late” in words, the red rule in the margin, the red plate on the panel.</span></li>'
            '<li><span class="tag tag--look"><svg class="icon" aria-hidden="true"><use href="#i-alert"/></svg>Needs a look</span><span><b>Set this up, needs a look</b>: copper, with the warning sign. Never yellow, so it can’t be mistaken for today.</span></li>'
            '<li><span class="tag tag--ok"><svg class="icon" aria-hidden="true"><use href="#i-okc"/></svg>Working</span><span><b>Done and working</b>: green, the done tick and the “Yes!” stamp.</span></li>'
            '<li><a href="home.html">A link</a><span><b>Links</b>: rail blue with an underline.</span></li>'
            '<li><a class="btn btn--primary" href="home.html">Primary</a><span><b>The one primary button</b>: rail blue, white letters (pale blue with dark letters at night).</span></li>'
            '<li><span class="pal-focus">Focus</span><span><b>Focus</b>: a 3 px blue ring (phosphor on glass and on the panel).</span></li>'
            '<li><span class="pill-health pal-pill">Vera is ready</span><span><b>Vera</b>: green on paper, phosphor on her glass.</span></li>'
            '</ul></section>')

page.append(group("Page and ink", "h-page", "A crisp, faintly cool white page and blue-black ink, like the lettering on a station sign.", [
    ("paper", "the page"), ("paper-2", "wells, hover rows, the weekend wash"), ("card", "inputs, tick boxes"), ("field", "fields"),
    ("ink", "text, ruled heads, picked controls"), ("ink-2", "secondary text, margin times"), ("ink-3", "quiet text, labels"),
    ("line", "hairlines between rows"), ("line-2", "running head and calendar rules"), ("edge", "control edges (3:1)")]))
page.append(group("The panel", "h-panel", "Deep rail blue, with white sign lettering. The phone’s top bar is the same blue.", [
    ("band", "the panel and the phone top bar"), ("on-band", "panel text, you are here plate"), ("on-band-2", "quiet panel text"),
    ("band-hi", "hover, the account plate"), ("band-line", "panel hairlines"), ("alert-plate", "the late count, with a white rim")]))
page.append(group("Signals and actions", "h-sig", "One yellow, one red, one green, one copper, one blue.", [
    ("signal", "today, Leave by, you are here"), ("on-signal", "letters on the signal"), ("signal-rule", "today’s rule over its calendar cell"),
    ("today-wash", "today’s calendar cell"), ("alert", "late, broken, errors"), ("alert-soft", "late badge, error tags"),
    ("warn", "set this up, needs a look"), ("warn-soft", "the setup panel"), ("ok", "working, done"), ("ok-soft", "working tags, ok banners"),
    ("link", "links"), ("link-line", "link underline"), ("primary", "the primary button"), ("focus", "the focus ring")]))
page.append(group("Vera’s glass and the phosphor", "h-glass", "The shadow of FamilyDB’s green-screen first design, unchanged: Vera’s charcoal glass, her phosphor Send and glow, the lit cursor. It is green-black, so it never reads as the blue panel.", [
    ("vera", "Vera’s name and rule on paper"), ("vera-bg", "the done tick, Yes! stamp, meter"), ("vera-soft", "the calm Ready pill"),
    ("ask-bg", "Ask Vera’s glass"), ("ask-field", "the box on her glass"), ("send", "her Send"), ("glass", "brand panes, the radar"),
    ("phosphor", "lit prompt, cursor at night, glow"), ("cursor", "the wordmark cursor on paper")]))

shell = open(os.path.join(root, "404.html")).read()
head, rest = shell.split('<main class="main" id="main">', 1)
tail = rest[rest.index("</main>"):]
head = head.replace("<title>Page not found · FamilyDB</title>", "<title>Palette · FamilyDB</title>")
main = ('<main class="main" id="main">\n    <div class="wrap pal">\n      <div class="runhead" aria-hidden="true"><span><b>FamilyDB</b> · Palette</span><span>Saturday 3 October 2026</span></div>\n'
        + "\n".join("      " + s for s in page) + "\n    </div>\n  ")
open(os.path.join(root, "palette.html"), "w").write(head + main + tail)

rules = "\n".join(f".sw--{n} {{ background: var(--{n}); }}" for n in used)
start, end = "/* PALETTE-SWATCHES (generated by _kit/make-palette.py) */", "/* /PALETTE-SWATCHES */"
blockcss = f"{start}\n{rules}\n{end}"
if start in css:
    css = css[:css.index(start)] + blockcss + css[css.index(end) + len(end):]
else:
    css = css.replace("/* ---------- 7. Phone", blockcss + "\n\n/* ---------- 7. Phone", 1)
open(css_path, "w").write(css)
print("palette.html:", len(used), "tokens,", len(PEOPLE), "people")
