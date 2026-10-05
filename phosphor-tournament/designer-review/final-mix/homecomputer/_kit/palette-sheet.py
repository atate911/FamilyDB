# python3 _kit/palette-sheet.py
# Writes palette.html from the tokens in style.css (light and dark), and the sheet's own classes
# into style.css §10 (between the generated markers). Swatches are live: they paint with var(--token),
# so the page shows whichever theme the device is in; both values are printed beside each one.
# The colour-blind rows are SVG with fill attributes (CSP allows presentation attributes).
import os, re, sys, html, itertools
sys.path.insert(0, os.path.dirname(__file__))
from colour import contrast, simulate, de2000, KINDS
import importlib.util
spec = importlib.util.spec_from_file_location('pc', os.path.join(os.path.dirname(__file__), 'palette-check.py'))
pc = importlib.util.module_from_spec(spec); spec.loader.exec_module(pc)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
css_path = os.path.join(ROOT, 'style.css')
css = open(css_path).read()
T, report = pc.run(css_path)
L, D = T['light'], T['dark']
e = html.escape

PEOPLE = [  # slot, sticker name, who in the mockups
    ('p1', 'Cobalt', 'Sam'), ('p2', 'Violet', 'Alex'), ('p3', 'Mustard', 'Maya'), ('p4', 'Turquoise', 'Theo'),
    ('p5', 'Walnut', 'Slot 5'), ('p6', 'Sky', 'Slot 6'), ('p7', 'Petrol', 'Slot 7'), ('p8', 'Aubergine', 'Slot 8'),
]
GROUPS = [
    ('The case: page and surfaces', 'Putty grey, never cream: a warm grey with almost no yellow in it. Keycap white for fields.',
     ['paper', 'paper-2', 'card', 'field']),
    ('Ink and seams', 'Brown-black ink, the keyboard’s own colour, and moulded seams for rules.',
     ['ink', 'ink-2', 'ink-3', 'line', 'line-2', 'edge']),
    ('The keyboard surround: the panel', 'The strong, deep panel the page sits beside, and the phone’s top bar.',
     ['band', 'band-hi', 'band-line', 'on-band', 'on-band-2']),
    ('The orange key: the one signal', 'Today, the one primary button, the next thing to set up, you are here.',
     ['signal', 'signal-2', 'on-signal', 'signal-ink', 'today-rule', 'link-line']),
    ('Late: the only red', 'Late, broken and errors. Never a person, never decoration.',
     ['alert', 'alert-soft', 'alert-line', 'alert-plate']),
    ('Set up, working, done', 'Set up is the orange key as a wash, with ⚠. Working is the machine being well. Done is a key pressed in ink.',
     ['warn', 'warn-soft', 'warn-line', 'ok', 'ok-soft', 'done', 'on-done']),
    ('The green screen: Vera’s alone', 'Charcoal glass and phosphor, kept at full strength. No person and no signal is green.',
     ['glass', 'glass-2', 'glass-line', 'phosphor', 'glass-ink', 'vera', 'vera-bg', 'vera-soft', 'cursor', 'send']),
    ('Everyone', 'Plans for the whole family are neutral putty, with the house.',
     ['everyone', 'everyone-soft', 'everyone-ink', 'everyone-mark']),
]
SW = sorted({t for g in GROUPS for t in g[2]})

def val(t):
    a, b = L.get(t, '—'), D.get(t, '—')
    return f'<span class="pal-v"><span>{a}</span><span>{b}</span></span>' if a != b else f'<span class="pal-v"><span>{a}</span><span>same</span></span>'

def cvd_rows(theme, keys, shape):
    t = T[theme]; out = []
    W = 8 * 44
    for k in KINDS:
        cells = []
        for i, key in enumerate(keys):
            c = simulate(t[key], k)
            if shape == 'circle':
                cells.append(f'<circle cx="{18 + i * 44}" cy="18" r="16" fill="{c}"/>')
            else:
                cells.append(f'<rect x="{6 + i * 44}" y="2" width="24" height="32" rx="2" fill="{c}"/>')
        out.append(f'<div class="pal-cvd__row"><span class="pal-cvd__k">{k.capitalize()}</span>'
                   f'<svg class="pal-cvd__svg" viewBox="0 0 {W} 36" width="{W}" height="36" aria-hidden="true" focusable="false">'
                   f'<rect width="{W}" height="36" fill="{t["paper"]}"/>{"".join(cells)}</svg></div>')
    return ''.join(out)

def closest(key):
    best = min((v['closest'][0], k, v['closest'][1], v['closest'][2]) for k, v in report['cvd'][key].items() if k != 'normal')
    name = dict((p, n) for p, n, _ in PEOPLE)
    a, b = (name[x.replace('-mark', '')] for x in best[2:])
    return f'{best[0]} ({a} and {b}, {best[1]})'

npass = sum(1 for p in report['pairs'] if p[3] and p[3] >= p[4]); ntot = len(report['pairs'])
low_letter = min((p[3], p[2]) for p in report['pairs'] if p[1].startswith('on-p') and p[0] == 'light')

# ---------- the page ----------
type_html = open(os.path.join(ROOT, 'type.html')).read()
head, rest = type_html.split('<main class="main" id="main">', 1)
tail = '</main>' + rest.split('</main>', 1)[1]
head = head.replace('<title>Type · FamilyDB</title>', '<title>Palette · FamilyDB</title>')

people_rows = []
for p, name, who in PEOPLE:
    people_rows.append(f'''
          <li class="pal-person {p}">
            <span class="av av--lg {p}" aria-hidden="true">{who[0] if not who.startswith('Slot') else who[-1]}</span>
            <span class="pal-person__name"><b>{e(who)}</b><span>{name} · <code class="pal-code">--{p}</code></span></span>
            <span class="pal-person__stripe" aria-hidden="true"></span>
            <span class="pal-person__plan"><b>{e(who)}’s plan</b><span>7 pm</span></span>
            <span class="pal-person__vals">
              <span>avatar <b>{L[p]}</b> · letter {'ink' if L['on-'+p] == L['ink-k'] else 'white'} {contrast(L[p], L['on-'+p]):.1f}:1</span>
              <span>day: soft {L[p+'-soft']} · ink {L[p+'-ink']} · stripe {L[p+'-mark']}</span>
              <span>night: soft {D[p+'-soft']} · ink {D[p+'-ink']} · stripe {D[p+'-mark']}</span>
            </span>
          </li>''')

groups_html = []
for title, note, toks in GROUPS:
    cells = ''.join(f'<li class="pal-sw"><span class="pal-sw__chip sw--{t}" aria-hidden="true"></span><code class="pal-code">--{t}</code>{val(t)}</li>' for t in toks)
    groups_html.append(f'<div class="pal-group"><h3>{e(title)}</h3><p class="small muted">{e(note)}</p><ul class="plain pal-grid">{cells}</ul></div>')

av_keys = [p for p, _, _ in PEOPLE]; mk_keys = [p + '-mark' for p, _, _ in PEOPLE]

main = f'''<main class="main" id="main">
    <div class="wrap">
      <div class="runhead" aria-hidden="true"><span><b>FamilyDB</b> · Palette</span><span>Saturday 3 October 2026</span></div>

      <div class="page-head">
        <div><p class="overline">Colour</p><h1>Palette: Home Computer</h1><p class="lede">The family machine of the early 80s, set beside FamilyDB’s green screen: a putty case, a brown-black keyboard, the striped sticker colours of the badge for the family’s eight pens, one orange key for “this one”, and the green screen kept for Vera.</p></div>
      </div>

      <section class="sheet-sec" aria-labelledby="s-idea">
        <h2 id="s-idea">The machine</h2>
        <p>Every colour on a page is a part of the machine, and each part has one job. Look at a screen and you can tell what’s what before you read it. Colour is never the only cue: late always says “days late”, setup carries ⚠, and every person has a name and a letter.</p>
        <div class="hc" aria-hidden="true">
          <div class="hc__case">
            <div class="hc__badge"><span class="hc__stripe"><i class="p3"></i><i class="p4"></i><i class="p1"></i><i class="p2"></i></span><span class="hc__name">FamilyDB</span></div>
            <div class="hc__deck">
              <span class="hc__row"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></span>
              <span class="hc__row"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i class="hc__go">RETURN</i></span>
              <span class="hc__row"><i></i><i></i><i></i><i></i><i class="hc__space"></i><i></i><i></i></span>
            </div>
          </div>
          <div class="hc__screen"><span class="hc__line"></span><span class="hc__line hc__line--s"></span><span class="hc__prompt">&gt;<b></b></span></div>
        </div>
        <ol class="plain hc-key">
          <li><span class="hc-key__n">1</span><span class="hc-key__chip sw--paper"></span><span><b>The putty case is the page.</b> A light warm grey, not cream, with keycap white for fields.</span></li>
          <li><span class="hc-key__n">2</span><span class="hc-key__chip sw--band"></span><span><b>The keyboard surround is the panel</b> down the left, and the phone’s top bar. It’s strong and deep, and it’s brown-black, so it never reads as Vera’s glass.</span></li>
          <li><span class="hc-key__n">3</span><span class="hc-key__chip hc-key__chip--stripe"></span><span><b>The badge stripe is the family.</b> The sticker colours are the eight pens. The panel’s edge carries the family’s first four, like the stripe on the case.</span></li>
          <li><span class="hc-key__n">4</span><span class="hc-key__chip sw--signal"></span><span><b>The orange key means “this one”:</b> today, the one primary button, the Tomorrow stamp, a Yes!, the step to set up next, and the edge of “you are here”.</span></li>
          <li><span class="hc-key__n">5</span><span class="hc-key__chip sw--glass hc-key__chip--glass"></span><span><b>The green screen is Vera’s alone.</b> Charcoal glass, phosphor Send, the lit cursor, at the same strength as before. Nothing else on the page is green apart from “Working”.</span></li>
          <li><span class="hc-key__n">6</span><span class="hc-key__chip sw--alert"></span><span><b>Red is only late.</b> No person is red, and red is never decoration.</span></li>
        </ol>
      </section>

      <section class="sheet-sec" aria-labelledby="s-people">
        <h2 id="s-people">The eight pens</h2>
        <p>Eight colours from the stickers and stripes of those machines. Going round the wheel, deep and light take turns, so neighbours differ in lightness as well as hue. Deep pens take a white letter and light pens an ink one, whichever passes AA (lowest {low_letter[0]}:1). No pink, no pastel, no red and no green.</p>
        <div class="pal-side">
          <div><p class="label">Side by side</p>
            <p class="pal-avs">{''.join(f'<span class="av av--lg {p}" aria-hidden="true">{(w[0] if not w.startswith("Slot") else w[-1])}</span>' for p, _, w in PEOPLE)}<span class="av av--lg p0" aria-hidden="true"><svg class="icon" aria-hidden="true"><use href="#i-home"/></svg></span></p></div>
          <div><p class="label">Route stripes</p>
            <p class="pal-stripes" aria-hidden="true">{''.join(f'<i class="{p}"></i>' for p, _, _ in PEOPLE)}<i class="p0"></i></p></div>
          <div><p class="label">A plan for several</p>
            <p class="pal-route" aria-hidden="true"><i class="p3"></i><i class="p4"></i></p></div>
        </div>
        <ul class="plain pal-people">{''.join(people_rows)}
        </ul>
      </section>

      <section class="sheet-sec" aria-labelledby="s-signals">
        <h2 id="s-signals">The signals</h2>
        <p>One orange key, one red, and Vera’s green. Each always comes with words.</p>
        <ul class="plain pal-sig">
          <li><p class="label">The orange key</p><p class="pal-sig__demo"><span class="pal-stamp">Tomorrow</span><span class="pal-today">3</span><a class="btn btn--primary btn--sm" href="plans.html">Add a plan</a></p><p class="small muted">Today, the next plan, the one primary button, Yes!, “you are here”. A filled key under ink letters; as words it’s deep orange.</p></li>
          <li><p class="label">Late</p><p class="pal-sig__demo"><span class="pal-late">6 days late</span><span class="pal-latetag">3 late</span><span class="pal-plate">3 late</span></p><p class="small muted">The only red. On the panel it’s a solid plate.</p></li>
          <li><p class="label">Set up</p><p class="pal-sig__demo"><span class="pal-warn">⚠ 3 steps left</span></p><p class="small muted">The orange key as a wash, always with ⚠ and the steps in words.</p></li>
          <li><p class="label">Done and working</p><p class="pal-sig__demo"><span class="pal-done" aria-hidden="true"><svg class="icon" aria-hidden="true"><use href="#i-check"/></svg></span><span class="pal-ok">Working</span></p><p class="small muted">A ticked box is pressed in ink. Working is the machine being well.</p></li>
          <li><p class="label">Links and focus</p><p class="pal-sig__demo"><a href="todo.html">three to-dos</a><span class="pal-focus">Focus</span></p><p class="small muted">Links are ink with an orange underline. Focus is a 3 px ink ring, putty-white at night and phosphor on glass.</p></li>
          <li class="pal-sig__vera"><p class="label">Vera</p><p class="pal-sig__demo"><span class="pal-glass"><span>&gt; say it the way you’d say it at the table.</span><b>Send</b></span></p><p class="small muted">Her glass and phosphor, unchanged, set off by a warm panel instead of a navy one.</p></li>
        </ul>
      </section>

      <section class="sheet-sec" aria-labelledby="s-tokens">
        <h2 id="s-tokens">Every colour token</h2>
        <p>Day value, then night. The swatches paint from the tokens in <code class="pal-code">style.css</code>, so they show the theme your device is in.</p>
        {''.join(groups_html)}
      </section>

      <section class="sheet-sec" aria-labelledby="s-cvd">
        <h2 id="s-cvd">Seen with colour-blindness</h2>
        <p>The eight avatars and day stripes, simulated (Machado 2009) and measured (CIEDE2000; under 5 is hard to tell apart). Closest avatars: {closest('light avatars')}. Closest day stripes: {closest('light stripes')}; night stripes: {closest('dark stripes')}. {npass} of {ntot} contrast pairs pass in both themes (<code class="pal-code">python3 _kit/palette-check.py</code>).</p>
        <div class="pal-cvd">
          <div><p class="label">Avatars</p>{cvd_rows('light', av_keys, 'circle')}</div>
          <div><p class="label">Route stripes, day</p>{cvd_rows('light', mk_keys, 'bar')}</div>
          <div><p class="label">Route stripes, night</p>{cvd_rows('dark', mk_keys, 'bar')}</div>
        </div>
      </section>
    </div>
  '''
page = head + main + tail
# the panel: no page is current on the sheet (as in type.html)
open(os.path.join(ROOT, 'palette.html'), 'w').write(page)

# ---------- the sheet's classes in style.css ----------
START = '/* ---------- 10. The palette sheet (written by _kit/palette-sheet.py) ---------- */'
END = '/* ---------- end of 10 ---------- */'
sw = '\n'.join(f'.sw--{t} {{ background: var(--{t}); }}' for t in SW)
block = f'''{START}
{sw}
.pal-code {{ font-family: var(--font-mono); font-stretch: 75%; font-size: var(--t-sm); }}
.hc {{ display: grid; grid-template-columns: minmax(0, 1fr) 200px; gap: var(--s5); align-items: end; margin-top: var(--s5); max-width: 760px; }}
.hc__case {{ background: var(--paper-2); border: 1px solid var(--line-2); border-radius: 10px 10px 4px 4px; padding: var(--s4) var(--s5) var(--s5); }}
.hc__badge {{ display: flex; align-items: center; gap: var(--s3); margin-bottom: var(--s4); }}
.hc__stripe {{ display: grid; grid-template-columns: repeat(4, 14px); height: 22px; transform: skewX(-18deg); }}
.hc__stripe i, .pal-stripes i, .pal-route i {{ display: block; background: var(--p-mark); }}
.hc__stripe i {{ background: var(--p); }}
.hc__name {{ font: 700 1.125rem/1 var(--font-head); letter-spacing: -0.02em; color: var(--ink-2); }}
.hc__deck {{ display: grid; gap: 6px; background: var(--band); border-radius: 6px; padding: 12px; }}
.hc__row {{ display: flex; gap: 6px; }}
.hc__row i {{ flex: 1; height: 26px; border-radius: 3px; background: var(--card); box-shadow: inset 0 -3px 0 var(--line-2); }}
.hc__row i.hc__space {{ flex: 5; }}
.hc__row i.hc__go {{ flex: 2.2; background: var(--signal); box-shadow: inset 0 -3px 0 var(--today-rule); color: var(--on-signal); font: 700 .75rem/26px var(--font-num); letter-spacing: .06em; font-style: normal; text-align: center; }}
.hc__screen {{ height: 150px; background: var(--glass); border-radius: 14px; box-shadow: 0 0 0 4px var(--ask-ring), inset 0 0 0 1px var(--glass-line); padding: 20px; display: flex; flex-direction: column; gap: 8px; }}
.hc__line {{ height: 5px; width: 70%; border-radius: 3px; background: var(--phosphor-dim); }}
.hc__line--s {{ width: 45%; }}
.hc__prompt {{ margin-top: auto; color: var(--phosphor); font: 700 1.5rem/1 var(--font-mono); text-shadow: 0 0 8px var(--phosphor-glow); display: flex; align-items: center; gap: 6px; }}
.hc__prompt b {{ width: 12px; height: 22px; background: var(--phosphor); box-shadow: 0 0 8px var(--phosphor-glow); border-radius: 1px; }}
.hc-key {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: var(--s4) var(--s6); margin-top: var(--s6); }}
.hc-key li {{ display: grid; grid-template-columns: 20px 36px minmax(0, 1fr); gap: var(--s3); align-items: start; }}
.hc-key__n {{ font: 700 1rem/36px var(--font-num); color: var(--ink-3); }}
.hc-key__chip {{ width: 36px; height: 36px; border-radius: var(--r-md); box-shadow: inset 0 0 0 1px var(--line-2); }}
.hc-key__chip--stripe {{ background: linear-gradient(to right, var(--p3) 0 25%, var(--p4) 25% 50%, var(--p1) 50% 75%, var(--p2) 75%); }}
.hc-key__chip--glass {{ box-shadow: inset 0 0 0 2px var(--phosphor); }}
.pal-side {{ display: flex; flex-wrap: wrap; gap: var(--s5) var(--s7); margin-top: var(--s5); }}
.pal-avs {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: var(--s2); }}
.pal-stripes {{ display: flex; gap: 10px; height: 56px; margin-top: var(--s2); }}
.pal-stripes i {{ width: 6px; border-radius: 1px; }}
.pal-route {{ display: grid; grid-template-rows: 1fr 1fr; width: 6px; height: 56px; margin-top: var(--s2); }}
.pal-people {{ margin-top: var(--s5); border-top: 1px solid var(--line); }}
.pal-person {{ display: grid; grid-template-columns: 40px 150px 120px 150px minmax(0, 1fr); gap: var(--s4); align-items: center; padding: var(--s3) 0; border-bottom: 1px solid var(--line); }}
.pal-person__name {{ display: grid; line-height: 1.3; }}
.pal-person__name span {{ color: var(--ink-3); font-size: var(--t-sm); }}
.pal-person__stripe {{ height: 6px; background: var(--p-mark); border-radius: 1px; }}
.pal-person__plan {{ display: grid; background: var(--p-soft); border-left: 4px solid var(--p-mark); padding: 4px 10px; font-size: var(--t-sm); line-height: 1.3; }}
.pal-person__plan b {{ color: var(--p-ink); }}
.pal-person__plan span {{ color: var(--ink-2); font-family: var(--font-mono); font-stretch: 75%; }}
.pal-person__vals {{ display: grid; font-family: var(--font-mono); font-stretch: 75%; font-size: var(--t-sm); color: var(--ink-2); line-height: 1.45; }}
.pal-person__vals b {{ color: var(--ink); font-weight: 650; }}
.pal-sig {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: var(--s5) var(--s6); margin-top: var(--s5); }}
.pal-sig li {{ border-top: 1px solid var(--line); padding-top: var(--s3); }}
.pal-sig__demo {{ display: flex; flex-wrap: wrap; align-items: center; gap: var(--s3); min-height: 56px; margin: var(--s2) 0; }}
.pal-stamp {{ background: var(--signal); color: var(--on-signal); border: 1px solid var(--primary-edge); border-radius: var(--r-sm); padding: 2px 8px; font: 700 var(--t-sm)/1.3 var(--font-num); letter-spacing: .06em; text-transform: uppercase; }}
.pal-today {{ display: inline-grid; place-items: center; width: 36px; height: 36px; background: var(--today-bg); color: var(--on-today); border-radius: var(--r-md); font: 700 1.375rem/1 var(--font-num); }}
.pal-late {{ color: var(--alert); font-weight: 700; }}
.pal-latetag {{ color: var(--alert); background: var(--alert-soft); border: 1px solid var(--alert-line); border-radius: var(--r-sm); padding: 2px 8px; font-weight: 700; font-size: var(--t-sm); }}
.pal-plate {{ background: var(--alert-plate); color: var(--on-alert-plate); border-radius: var(--r-sm); padding: 2px 8px; font: 700 1rem/1.3 var(--font-num); box-shadow: 0 0 0 8px var(--band); margin-left: 8px; }}
.pal-warn {{ color: var(--warn); background: var(--warn-soft); border: 1px solid var(--warn-line); border-radius: var(--r-sm); padding: 2px 8px; font-weight: 700; font-size: var(--t-sm); }}
.pal-done {{ display: inline-grid; place-items: center; width: 30px; height: 30px; background: var(--done); color: var(--on-done); border-radius: var(--r-md); }}
.pal-done .icon {{ stroke-width: 2.8; }}
.pal-ok {{ color: var(--ok); background: var(--ok-soft); border: 1px solid var(--ok-line); border-radius: var(--r-sm); padding: 2px 8px; font-weight: 700; font-size: var(--t-sm); }}
.pal-focus {{ outline: 3px solid var(--focus); outline-offset: 3px; border-radius: var(--r-sm); padding: 2px 8px; font-weight: 700; }}
.pal-glass {{ display: flex; align-items: center; gap: var(--s3); background: var(--ask-bg); border-radius: 14px; box-shadow: 0 0 0 4px var(--ask-ring); padding: 10px 10px 10px 14px; color: var(--ask-ink-2); font: 450 var(--t-sm)/1.3 var(--font-mono); font-stretch: 75%; }}
.pal-glass b {{ background: var(--send); color: var(--on-send); border-radius: var(--r-md); padding: 8px 14px; font: 700 var(--t-meta)/1 var(--font-text); }}
.pal-group {{ margin-top: var(--s6); }}
.pal-group h3 {{ font-size: var(--t-h3); }}
.pal-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: var(--s4); margin-top: var(--s3); }}
.pal-sw {{ display: grid; gap: 4px; }}
.pal-sw__chip {{ height: 56px; border-radius: var(--r-md); box-shadow: inset 0 0 0 1px var(--line-2); }}
.pal-v {{ display: flex; justify-content: space-between; font-family: var(--font-mono); font-stretch: 75%; font-size: var(--t-sm); color: var(--ink-2); }}
.pal-v span + span {{ color: var(--ink-3); }}
.pal-cvd {{ display: flex; flex-wrap: wrap; gap: var(--s5) var(--s7); margin-top: var(--s5); }}
.pal-cvd__row {{ display: grid; grid-template-columns: 96px auto; align-items: center; gap: var(--s3); margin-top: 6px; }}
.pal-cvd__k {{ font-size: var(--t-sm); color: var(--ink-2); }}
.pal-cvd__svg {{ max-width: 100%; height: auto; border-radius: var(--r-sm); }}
@media (max-width: 820px) {{
  .hc {{ grid-template-columns: 1fr; }}
  .hc__screen {{ height: 110px; }}
  .hc__row i {{ height: 18px; }}
  .hc__row i.hc__go {{ line-height: 18px; font-size: .625rem; }}
  .pal-person {{ grid-template-columns: 40px minmax(0, 1fr); }}
  .pal-person__stripe, .pal-person__plan, .pal-person__vals {{ grid-column: 1 / -1; }}
  .pal-cvd__row {{ grid-template-columns: 1fr; gap: 2px; }}
  .hc-key, .pal-sig {{ grid-template-columns: 1fr; }}
}}
{END}'''
if START in css:
    css = css[:css.index(START)] + block + css[css.index(END) + len(END):]
else:
    css = css.rstrip('\n') + '\n\n' + block + '\n'
open(css_path, 'w').write(css)
print('wrote palette.html and style.css §10;', f'{npass}/{ntot} pairs pass')
