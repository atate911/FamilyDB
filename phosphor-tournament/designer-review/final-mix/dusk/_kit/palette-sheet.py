# Writes palette.html (and the swatch classes it needs in style.css) from the tokens in style.css.
# python3 _kit/palette-sheet.py   — run it again whenever a colour token changes.
import sys, os, re, itertools, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colourlib import contrast, simulate, de2000, read_tokens

here = os.path.dirname(os.path.abspath(__file__)); root = os.path.join(here, "..")
css_path = os.path.join(root, "style.css")
css = open(css_path).read()
Ld, Dk = read_tokens(css)

PEOPLE = [  # slot, name, where it comes from, the family member (slots 5–8 are free)
    (1, "Evening blue", "the sky overhead, the first blue of night", "Sam"),
    (2, "Sea", "the water under the sunset", "Alex"),
    (3, "Heather", "the hills as the light goes violet", "Maya"),
    (4, "Sun gold", "the sun itself, low on the line", "Theo"),
    (5, "Sky", "the pale sky opposite the sun", None),
    (6, "Olive", "the fields, before they go dark", None),
    (7, "Dusk cloud", "a cloud in the last light, indigo in its shadow", None),
    (8, "Sandstone", "the warm rock that holds the day's heat", None),
]
USE = {
    "paper": "the page: dusk-grey, the faintest warmth in it", "paper-2": "wells, hover rows, the weekend wash",
    "card": "fields and tick boxes", "field": "inputs",
    "ink": "text, ruled heads, picked controls", "ink-2": "secondary text, meta", "ink-3": "quiet text, labels (AA)",
    "line": "hairlines between rows", "line-2": "running head and calendar rules", "rule": "the 3 px ruled head",
    "edge": "control edges (3:1)",
    "band": "the panel: the evening sky", "band-2": "the panel's foot, deeper violet", "band-hi": "the account plate, hover",
    "band-line": "rules on the panel", "on-band": "panel lettering", "on-band-2": "quiet panel lettering",
    "signal": "apricot: today, Tomorrow, the primary button, you are here", "signal-2": "the primary button on hover",
    "on-signal": "letters on apricot", "signal-mark": "Leave by's rule, link underlines (3:1)",
    "signal-ink": "today's date as text (AA)", "signal-soft": "today's calendar wash", "signal-line": "apricot hairline",
    "today-bg": "today's stamp", "on-today": "today's figure", "today-wash": "today's cell", "today-ink": "today's date in the greeting",
    "link": "links: ink", "link-line": "a link's apricot underline", "primary": "the one primary button",
    "primary-2": "its hover", "primary-edge": "its edge (ink by day)", "on-primary": "its label",
    "focus": "the focus ring: violet by day, apricot at night",
    "alert": "late, broken: the only red", "alert-soft": "an error's wash", "alert-line": "an error's edge",
    "alert-plate": "the late count on the panel", "on-alert-plate": "its figure",
    "warn": "set this up, needs a look (always with ⚠)", "warn-soft": "the setup panel", "warn-line": "its edge",
    "ok": "working", "ok-soft": "an ok banner", "ok-line": "its edge",
    "vera": "Vera's green as text", "vera-bg": "done: the tick, the strike, Yes!", "vera-bg-2": "done, pressed",
    "on-vera": "on Vera's green", "vera-soft": "the calm pill", "vera-line": "its edge",
    "glass": "Vera's dark glass", "glass-2": "glass, raised", "glass-line": "glass rules", "glass-ink": "text on glass",
    "glass-ink-2": "quiet text on glass", "glass-alert": "a fault on glass", "phosphor": "the phosphor: Send, the cursor, the ring",
    "send": "Send", "send-2": "Send on hover", "on-send": "Send's label", "cursor": "the lit cursor",
    "ask-bg": "Ask Vera's glass", "ask-ink": "text on Ask", "ask-ink-2": "quiet text on Ask", "on-p": "an avatar's letter (all eight)",
    "everyone": "Everyone's avatar", "everyone-soft": "Everyone's wash", "everyone-ink": "Everyone's name", "everyone-mark": "Everyone's stripe",
}
GROUPS = [
    ("The page", ["paper", "paper-2", "card", "field", "ink", "ink-2", "ink-3", "line", "line-2", "rule", "edge"]),
    ("The panel: the evening sky", ["band", "band-2", "band-hi", "band-line", "on-band", "on-band-2"]),
    ("The last light: apricot", ["signal", "signal-2", "on-signal", "signal-mark", "signal-ink", "signal-soft", "signal-line",
                                 "today-bg", "on-today", "today-wash", "today-ink", "primary", "primary-2", "primary-edge", "on-primary",
                                 "link", "link-line", "focus"]),
    ("Late, setup, working", ["alert", "alert-soft", "alert-line", "alert-plate", "on-alert-plate", "warn", "warn-soft", "warn-line",
                              "ok", "ok-soft", "ok-line"]),
    ("Vera: green and phosphor (hers alone)", ["vera", "vera-bg", "vera-bg-2", "on-vera", "vera-soft", "vera-line", "glass", "glass-2",
                                               "glass-line", "glass-ink", "glass-ink-2", "glass-alert", "phosphor", "send", "send-2",
                                               "on-send", "cursor", "ask-bg", "ask-ink", "ask-ink-2"]),
    ("Everyone, and the letters", ["on-p", "everyone", "everyone-soft", "everyone-ink", "everyone-mark"]),
]
ALL = [t for _, g in GROUPS for t in g] + [f"p{i}{s}" for i in range(1, 9) for s in ("", "-soft", "-ink", "-mark")]

# --- the swatch classes, written into style.css between markers ---
cls = " ".join(f".tk-{t} {{ --sw: var(--{t}); }}" for t in ALL)
cls = re.sub(r"((?:\S+ \{ [^}]*\} ){6})", r"\1\n", cls)
css = re.sub(r"(/\* palette:swatches \*/\n).*?(/\* /palette:swatches \*/)", lambda m: m.group(1) + cls.strip() + "\n" + m.group(2), css, flags=re.S)
open(css_path, "w").write(css)

e = html.escape
def nv(t):
    a, b = Ld[t], Dk[t]
    return a if a == b else f'{a}<span class="pal-night"> / {b}</span>'
def hexes(t):
    a, b = Ld.get(t), Dk.get(t)
    if a == b: return f'<code>{a}</code>'
    return f'<code>{a}</code> <span class="pal-night">night <code>{b}</code></span>'

# --- the colour-blind check, for the page ---
KINDS = [("normal", "Normal vision"), ("protan", "Protanopia"), ("deutan", "Deuteranopia"), ("tritan", "Tritanopia")]
def closest(cols):
    best = None
    for k, _ in KINDS[1:]:
        S = [simulate(h, k) for h in cols]
        d = min((de2000(S[a], S[b]), a, b, k) for a, b in itertools.combinations(range(8), 2))
        best = d if best is None or d < best else best
    return best
AV = [Ld[f"p{i}"] for i in range(1, 9)]; SD = [Ld[f"p{i}-mark"] for i in range(1, 9)]; SN = [Dk[f"p{i}-mark"] for i in range(1, 9)]
cav, csd, csn = closest(AV), closest(SD), closest(SN)
kname = dict(KINDS)
def pairtxt(c): return f"{c[0]:.1f}, {PEOPLE[c[1]][1].lower()} and {PEOPLE[c[2]][1].lower()} ({kname[c[3]].lower()})"

def sim_row(kind, label):
    av = "".join(f'<circle cx="{20 + i * 44}" cy="20" r="16" fill="{simulate(h, kind)}"/>' for i, h in enumerate(AV))
    sd = "".join(f'<rect x="{4 + i * 44}" y="4" width="36" height="8" rx="3" fill="{simulate(h, kind)}"/>' for i, h in enumerate(SD))
    sn = "".join(f'<rect x="{4 + i * 44}" y="4" width="36" height="8" rx="3" fill="{simulate(h, kind)}"/>' for i, h in enumerate(SN))
    return (f'<tr><th scope="row">{label}</th>'
            f'<td><svg class="pal-sim" viewBox="0 0 352 40" aria-hidden="true">{av}</svg></td>'
            f'<td><svg class="pal-sim pal-sim--day" viewBox="0 0 352 16" aria-hidden="true"><rect width="352" height="16" fill="{Ld["paper"]}"/>{sd}</svg></td>'
            f'<td><svg class="pal-sim pal-sim--night" viewBox="0 0 352 16" aria-hidden="true"><rect width="352" height="16" fill="{Dk["paper"]}"/>{sn}</svg></td></tr>')

# --- the page ---
shell = open(os.path.join(root, "type.html")).read()
head = shell[: shell.index('<div class="runhead"')]
head = head.replace("<title>Type · FamilyDB</title>", "<title>Palette · FamilyDB</title>")
tail = shell[shell.index("    </div>\n  </main>"):]

people_rows = []
for i, name, src, who in PEOPLE:
    letter = (who or name)[0]
    lc = contrast(Ld["on-p"], Ld[f"p{i}"])
    people_rows.append(f'''          <li class="pal-person p{i}">
            <span class="pal-person__avs"><span class="av p{i} av--lg" aria-hidden="true">{letter}</span><span class="av p{i}" aria-hidden="true">{letter}</span><span class="av p{i} av--sm" aria-hidden="true">{letter}</span></span>
            <span class="pal-person__name"><b>{e(name)}</b><span class="pal-person__who">{'<b>' + who + '</b> · ' if who else ''}<code>--p{i}</code></span><span class="pal-person__src">{e(src)}</span></span>
            <span class="pal-person__stripe" aria-hidden="true"></span>
            <span class="pal-person__plan"><span class="pal-person__t">{"7 pm" if i % 2 else "Sat 10 am"}</span><b>{e(who + "’s plan" if who else name + "’s plan")}</b></span>
            <span class="pal-person__vals">avatar <code>{Ld[f"p{i}"]}</code> letter {lc:.1f}:1<br>soft <code>{Ld[f"p{i}-soft"]}</code> · ink <code>{Ld[f"p{i}-ink"]}</code> · mark <code>{Ld[f"p{i}-mark"]}</code><br><span class="pal-night">night: soft <code>{Dk[f"p{i}-soft"]}</code> · ink <code>{Dk[f"p{i}-ink"]}</code> · mark <code>{Dk[f"p{i}-mark"]}</code></span></span>
          </li>''')
people_rows.append(f'''          <li class="pal-person p0">
            <span class="pal-person__avs"><span class="av p0 av--lg" aria-hidden="true"><svg class="icon" aria-hidden="true"><use href="#i-home"/></svg></span><span class="av p0" aria-hidden="true"><svg class="icon" aria-hidden="true"><use href="#i-home"/></svg></span><span class="av p0 av--sm" aria-hidden="true"><svg class="icon" aria-hidden="true"><use href="#i-home"/></svg></span></span>
            <span class="pal-person__name"><b>Everyone</b><span class="pal-person__who"><code>--everyone</code></span><span class="pal-person__src">the dusk itself: the page's own grey, a shade deeper</span></span>
            <span class="pal-person__stripe" aria-hidden="true"></span>
            <span class="pal-person__plan"><span class="pal-person__t">Sat 8 am</span><b>Everyone’s plan</b></span>
            <span class="pal-person__vals">avatar <code>{Ld["everyone"]}</code> · soft <code>{Ld["everyone-soft"]}</code> · ink <code>{Ld["everyone-ink"]}</code> · mark <code>{Ld["everyone-mark"]}</code><br><span class="pal-night">night: <code>{Dk["everyone"]}</code> · <code>{Dk["everyone-soft"]}</code> · <code>{Dk["everyone-ink"]}</code> · <code>{Dk["everyone-mark"]}</code></span></span>
          </li>''')

avs_line = "".join(f'<span class="av p{i} av--lg" aria-hidden="true">{(who or name)[0]}</span>' for i, name, src, who in PEOPLE)
stripes_line = "".join(f'<span class="pal-bar p{i}" aria-hidden="true"></span>' for i, *_ in PEOPLE)

token_rows = []
def vals(t):
    a, b = Ld.get(t), Dk.get(t)
    return f'<code>{a}</code>' + ('' if a == b else f' <span class="pal-night">· <code>{b}</code></span>')
for gname, toks in GROUPS:
    token_rows.append(f'<h3 class="pal-tokh">{e(gname)}</h3><ul class="pal-tokgrid">')
    for t in toks:
        token_rows.append(f'<li><span class="pal-sw tk-{t}" aria-hidden="true"></span><code class="pal-tok__n">--{t}</code><span class="pal-tok__v">{vals(t)}</span><small>{e(USE.get(t, ""))}</small></li>')
    token_rows.append('</ul>')
token_rows.append('<h3 class="pal-tokh">The eight people: base, soft, ink, mark</h3><ul class="pal-tokgrid">')
for i, name, src, who in PEOPLE:
    sw = "".join(f'<span class="pal-sw tk-p{i}{s}" aria-hidden="true"></span>' for s in ("", "-soft", "-ink", "-mark"))
    token_rows.append(f'<li><span class="pal-sw4">{sw}</span><code class="pal-tok__n">--p{i}</code><span class="pal-tok__v">{e(name)} · {e(who or "free slot")}</span>'
                      f'<small><code>{Ld[f"p{i}"]}</code> <code>{Ld[f"p{i}-soft"]}</code> <code>{Ld[f"p{i}-ink"]}</code> <code>{Ld[f"p{i}-mark"]}</code><br><span class="pal-night">night <code>{Dk[f"p{i}-soft"]}</code> <code>{Dk[f"p{i}-ink"]}</code> <code>{Dk[f"p{i}-mark"]}</code></span></small></li>')
token_rows.append('</ul>')

page = head + f'''<div class="runhead" aria-hidden="true"><span><b>FamilyDB</b> · Palette</span><span>Saturday 3 October 2026</span></div>

      <div class="page-head">
        <div><p class="overline">Colour</p><h1>Dusk</h1><p class="lede">The evening sky when the family gets home. A deep indigo-violet panel, a page with the faintest dusk left in its grey, and apricot, the last light, on whatever you do next. The people take their colours from the sunset sky and the land under it; red is only ever late; Vera’s window is the one thing lit green. Every value here is read from the tokens in <code>style.css</code>; switch your device to dark mode to see the night.</p></div>
      </div>

      <section class="sheet-sec" aria-labelledby="s-idea">
        <h2 id="s-idea">The idea: one evening, top to bottom</h2>
        <p>Read the page the way you’d read the sky from the doorstep. Up top, the deep sky is the panel. On the horizon, a line of apricot is the last light: it falls only on what you act on next. Below it, the land is the page, dusk-grey, where the family writes in their colours. And there’s one lit window: Vera’s glass, in the phosphor green the app was born with.</p>
        <figure class="pal-scene">
          <div class="pal-sky">
            <div class="pal-cap"><span class="label">The sky · the panel</span><b>Deep indigo-violet</b><span>Not navy, not lilac: the hour after sunset. It deepens toward violet at its foot, and the phone’s top bar is the same sky.</span><span class="pal-cap__v"><code>--band</code> {nv("band")} → <code>--band-2</code> {nv("band-2")}</span></div>
            <div class="pal-window">
              <span class="label">The one lit window · Vera</span>
              <p class="pal-window__line"><span class="pal-window__p">&gt;</span> Plans, reminders, ideas<span class="pal-window__cur" aria-hidden="true"></span></p>
              <span class="pal-window__send">Send</span>
              <span class="pal-cap__v"><code>--glass</code> {nv("glass")} · <code>--phosphor</code> {nv("phosphor")}</span>
            </div>
          </div>
          <div class="pal-horizon" aria-hidden="true"></div>
          <div class="pal-land">
            <div class="pal-cap"><span class="label pal-cap__lit">The last light · apricot</span><b>What you act on next</b><span>Today’s date, the Tomorrow stamp, Leave by’s rule, the one primary button, the edge of “you are here”, and the underline of a link. Nothing else is apricot, so the eye goes there first.</span><span class="pal-cap__v"><code>--signal</code> {nv("signal")} · <code>--signal-mark</code> {nv("signal-mark")} · <code>--signal-ink</code> {nv("signal-ink")}</span></div>
            <div class="pal-cap"><span class="label">The land · the page</span><b>Dusk-grey paper, indigo-black ink</b><span>A grey with the day’s warmth just leaving it (never cream, never pink), and ink the colour of the sky overhead.</span><span class="pal-cap__v"><code>--paper</code> {nv("paper")} · <code>--ink</code> {nv("ink")}</span></div>
            <div class="pal-folk"><span class="avs pal-folk__avs">{avs_line.replace(" av--lg", "")}</span><span class="pal-cap__v">The family, in the sunset’s colours</span><span class="tag tag--broken pal-folk__late">3 late</span><span class="pal-cap__v">Red: late, and nothing else</span></div>
          </div>
        </figure>
      </section>

      <section class="sheet-sec" aria-labelledby="s-people">
        <h2 id="s-people">The eight people</h2>
        <p>Each from a sunset sky or the land under it: grown-up, dusky colours, none pink, none red, none green enough to be Vera’s. Every avatar takes the same indigo letter (all pass AA, the weakest {min(contrast(Ld["on-p"], h) for h in AV):.1f}:1). Light and deep colours alternate round the wheel, so neighbours differ in lightness as well as hue. The route stripe and a person’s rule are the deep “mark”; a one-person plan sits on the soft wash with its mark down the edge.</p>
        <div class="pal-side">
          <div><span class="label">Side by side: avatars</span><div class="pal-side__avs">{avs_line}</div></div>
          <div><span class="label">Route stripes</span><div class="pal-side__bars">{stripes_line}</div></div>
          <div><span class="label">A plan with several people</span><div class="pal-side__route"><span class="route" aria-hidden="true"><i class="p1"></i><i class="p3"></i><i class="p4"></i></span><span class="route" aria-hidden="true"><i class="p2"></i><i class="p5"></i></span><span class="route" aria-hidden="true"><i class="p6"></i><i class="p7"></i><i class="p8"></i></span><span class="route" aria-hidden="true"><i class="p0"></i></span></div></div>
        </div>
        <ul class="pal-people">
{chr(10).join(people_rows)}
        </ul>
      </section>

      <section class="sheet-sec" aria-labelledby="s-signals">
        <h2 id="s-signals">The signals</h2>
        <p>Each signal has one colour and one job, and each also says it in words or a shape, so colour is never the only cue.</p>
        <div class="pal-signals">
          <div class="pal-sig"><span class="label">Today</span><div class="pal-sig__demo"><span class="greet__date">Saturday 3 October</span> <span class="pal-today">3</span></div><p>Apricot: the stamp on today’s date, its wash on the calendar, and the date in the greeting (burnt apricot, so it reads as text).</p></div>
          <div class="pal-sig"><span class="label">Next</span><div class="pal-sig__demo"><span class="tag tag--when pal-when">Tomorrow</span> <span class="pal-leave"><span class="leave__l">Leave by</span> <b>12:30 pm</b></span></div><p>Apricot: the next plan is stamped, and Leave by has the apricot rule.</p></div>
          <div class="pal-sig"><span class="label">The one primary button</span><div class="pal-sig__demo"><a class="btn btn--primary" href="#s-signals"><svg class="icon" aria-hidden="true"><use href="#i-plus"/></svg>Add a plan</a></div><p>An apricot plate with an ink edge by day (the edge carries the 3:1); a plain apricot plate at night.</p></div>
          <div class="pal-sig"><span class="label">Links and focus</span><div class="pal-sig__demo"><a href="#s-signals">See all plans</a> <span class="btn btn--quiet pal-focus">Focused</span></div><p>Links are ink with an apricot underline. The focus ring is violet by day, apricot at night, phosphor on the panel and on glass.</p></div>
          <div class="pal-sig"><span class="label">Late, the only red</span><div class="pal-sig__demo"><span class="late">6 days late</span> <span class="tag tag--broken">3 late</span></div><p>A cool red, kept far from apricot: crimson, not orange. Always with “late” or “couldn’t”.</p></div>
          <div class="pal-sig"><span class="label">Set this up, needs a look</span><div class="pal-sig__demo"><span class="tag tag--look"><svg class="icon" aria-hidden="true"><use href="#i-alert"/></svg>3 steps left</span></div><p>Honey-brown, always with ⚠, on a sand panel. Never apricot: setup isn’t urgent.</p></div>
          <div class="pal-sig"><span class="label">Done, working</span><div class="pal-sig__demo"><span class="tick tick--done pal-tick"><span><svg class="icon" aria-hidden="true"><use href="#i-check"/></svg></span></span> <span class="tag tag--ok"><svg class="icon" aria-hidden="true"><use href="#i-check"/></svg>Working</span></div><p>Green, Vera’s colour: done is her tick. No person is green.</p></div>
          <div class="pal-sig"><span class="label">Vera, ready</span><div class="pal-sig__demo pal-sig__demo--band"><span class="pill-health">Vera is ready</span></div><p>The phosphor echo is untouched: her glass, Send and glow, the lit cursor, the ready pill and the mark.</p></div>
        </div>
      </section>

      <section class="sheet-sec" aria-labelledby="s-cvd">
        <h2 id="s-cvd">For colour-blind eyes</h2>
        <p>The eight avatars and route stripes as people with each kind of colour blindness see them (Machado 2009 simulation, full strength; distances in CIEDE2000, where about 5 is clearly different side by side). Closest pairs: avatars {pairtxt(cav)}; day stripes {pairtxt(csd)}; night stripes {pairtxt(csn)}. Names and initials always sit beside the colour.</p>
        <table class="jobs pal-cvd">
          <thead><tr><th scope="col">Seen with</th><th scope="col">Avatars</th><th scope="col">Stripes, day</th><th scope="col">Stripes, night</th></tr></thead>
          <tbody>{"".join(sim_row(k, l) for k, l in KINDS)}</tbody>
        </table>
      </section>

      <section class="sheet-sec" aria-labelledby="s-tokens">
        <h2 id="s-tokens">Every colour token</h2>
        <p>The swatch shows the theme you’re in; the values are day, then night where it differs. Hex values live only on <code>:root</code>.</p>
        <div class="pal-tokens">
{chr(10).join("          " + r for r in token_rows)}
        </div>
      </section>
''' + tail
page = page.replace('<li><a href="home.html">', '<li><a href="home.html">', 1)
open(os.path.join(root, "palette.html"), "w").write(page)
print("palette.html written;", len(ALL), "swatch classes in style.css")
