# python3 _kit/palette-check.py [style.css] [--json]
# Reads the colour tokens from style.css (light :root and the dark block), resolves var(),
# checks every contrast pair the pages use against its floor (AA text 4.5, controls/marks 3:1),
# and runs the colour-blind check (Machado 2009, CIEDE2000) on the eight people's colours.
import re, sys, os, json, itertools
sys.path.insert(0, os.path.dirname(__file__))
from colour import contrast, simulate, de2000, KINDS

def tokens(css):
    root = re.search(r':root\s*\{(.*?)\n\}', css, re.S).group(1)
    dark = re.search(r'@media \(prefers-color-scheme: dark\)\s*\{\s*:root\s*\{(.*?)\n  \}', css, re.S).group(1)
    decl = lambda b: dict(re.findall(r'--([\w-]+):\s*([^;]+);', b))
    light = decl(root)
    night = dict(light); night.update(decl(dark))
    def res(t, k, depth=0):
        v = t[k].strip()
        m = re.fullmatch(r'var\(--([\w-]+)\)', v)
        return res(t, m.group(1), depth + 1) if m else v
    out = {}
    for name, t in (('light', light), ('dark', night)):
        out[name] = {k: res(t, k) for k in t if re.fullmatch(r'#[0-9A-Fa-f]{6}', res(t, k) or '')}
    return out

# (fg, bg, floor, use)
PAIRS = [
    ('ink', 'paper', 4.5, 'body text'), ('ink', 'paper-2', 4.5, 'text on a well'), ('ink', 'card', 4.5, 'text in fields'),
    ('ink-2', 'paper', 4.5, 'secondary text'), ('ink-2', 'paper-2', 4.5, 'secondary on a well'),
    ('ink-3', 'paper', 4.5, 'quiet text, labels'), ('ink-3', 'paper-2', 4.5, 'quiet on a well'), ('ink-3', 'card', 4.5, 'placeholders'),
    ('ink-3', 'today-wash', 4.5, "today's cell"), ('ink', 'today-wash', 4.5, "today's cell text"),
    ('edge', 'paper', 3, 'control edges'), ('edge', 'card', 3, 'field edges'), ('edge', 'paper-2', 3, 'edges on a well'),
    ('link', 'paper', 4.5, 'links'),
    ('on-primary', 'primary', 4.5, 'primary button label'), ('primary-edge', 'paper', 3, 'primary button edge'),
    ('on-signal', 'signal', 4.5, 'Tomorrow stamp, Yes! stamp'), ('signal-ink', 'paper', 4.5, 'orange as text'),
    ('today-ink', 'paper', 4.5, "greeting's date"), ('on-today', 'today-bg', 4.5, "today's day number"),
    ('today-rule', 'today-wash', 3, "today's rule on its cell"),
    ('on-done', 'done', 4.5, 'done tick'), ('done', 'paper', 3, 'done tick against the page'),
    ('vera', 'paper', 4.5, "Vera's name and rule"), ('vera', 'vera-soft', 4.5, 'Ready pill'),
    ('on-vera', 'vera-bg', 4.5, 'Vera tile'),
    ('ok', 'ok-soft', 4.5, 'tag Working'), ('ok', 'paper', 4.5, 'ok text'),
    ('warn', 'warn-soft', 4.5, 'setup panel, Needs a look'), ('warn', 'paper', 4.5, 'step numbers'),
    ('ink', 'warn-soft', 4.5, 'setup panel text'), ('ink-2', 'warn-soft', 4.5, 'setup panel meta'), ('ink-3', 'warn-soft', 4.5, 'setup panel quiet'),
    ('alert', 'alert-soft', 4.5, 'late badge'), ('alert', 'paper', 4.5, 'late text, OVERDUE'),
    ('on-band', 'band', 4.5, 'panel text'), ('on-band-2', 'band', 4.5, 'panel quiet text'), ('on-band-2', 'band-hi', 4.5, 'account plate'),
    ('band', 'on-band', 4.5, 'you are here plate'), ('signal', 'on-band', 1.0, '(edge on the plate, decorative)'),
    ('on-alert-plate', 'alert-plate', 4.5, 'late count on the panel'), ('alert-plate', 'band', 3, 'late plate against the panel'),
    ('phosphor', 'band', 3, 'wordmark cursor on the panel'),
    ('glass-ink', 'glass', 4.5, 'pane text'), ('phosphor', 'glass', 4.5, 'phosphor on glass'), ('ask-ink-2', 'ask-bg', 4.5, "Vera's line on Ask"),
    ('on-send', 'send', 4.5, 'Send'), ('glass-alert', 'glass', 4.5, "can't answer pill"),
    ('everyone-ink', 'everyone', 4.5, 'house avatar'), ('everyone-mark', 'paper', 3, "Everyone's stripe"),
    ('ink', 'everyone-soft', 4.5, 'Everyone plan words'),
]
for i in range(1, 9):
    p = f'p{i}'
    PAIRS += [(f'on-{p}', p, 4.5, f'{p} avatar letter'), (f'{p}-ink', 'paper', 4.5, f'{p} name on paper'),
              (f'{p}-ink', f'{p}-soft', 4.5, f'{p} name on its wash'), ('ink', f'{p}-soft', 4.5, f'words on {p} wash'),
              ('ink-2', f'{p}-soft', 4.5, f'time on {p} wash'), (f'{p}-mark', 'paper', 3, f'{p} route stripe'),
              (f'{p}-mark', 'card', 3, f'{p} stripe on a field')]

PEOPLE = [f'p{i}' for i in range(1, 9)]

def run(path='style.css'):
    T = tokens(open(path).read())
    report = {'pairs': [], 'fails': 0, 'cvd': {}}
    for theme in ('light', 'dark'):
        t = T[theme]
        for fg, bg, floor, use in PAIRS:
            if fg not in t or bg not in t: report['pairs'].append((theme, fg, bg, None, floor, use)); continue
            c = contrast(t[fg], t[bg])
            report['pairs'].append((theme, fg, bg, round(c, 2), floor, use))
            if c < floor: report['fails'] += 1
        for label, keys in (('avatars', PEOPLE), ('stripes', [p + '-mark' for p in PEOPLE])):
            res = {}
            for k in KINDS:
                d, a, b = min((de2000(simulate(t[a], k), simulate(t[b], k)), a, b) for a, b in itertools.combinations(keys, 2))
                near = {s: min((de2000(simulate(t[s], k), simulate(t[x], k)), x) for x in keys) for s in ('alert', 'vera-bg', 'signal') if s in t}
                if theme == 'dark': near['phosphor'] = min((de2000(simulate(t['phosphor'], k), simulate(t[x], k)), x) for x in keys)
                res[k] = {'closest': (round(d, 1), a, b), 'near': {s: (round(v[0], 1), v[1]) for s, v in near.items()}}
            report['cvd'][f'{theme} {label}'] = res
    return T, report

if __name__ == '__main__':
    path = next((a for a in sys.argv[1:] if not a.startswith('--')), 'style.css')
    T, r = run(path)
    if '--json' in sys.argv: print(json.dumps(r, indent=1)); sys.exit()
    for theme, fg, bg, c, floor, use in r['pairs']:
        flag = 'MISSING' if c is None else ('FAIL' if c < floor else '')
        if flag or '--all' in sys.argv: print(f'{theme:5} {fg:>15} on {bg:<14} {c}  (floor {floor})  {use}  {flag}')
    n = len(r['pairs'])
    print(f'{n - r["fails"]}/{n} contrast pairs pass')
    lows = {}
    for theme, fg, bg, c, floor, use in r['pairs']:
        if c and fg.startswith('on-p') and bg.startswith('p'): lows.setdefault(theme, []).append((c, bg))
    for theme, l in lows.items(): print(f'{theme}: weakest avatar letter {min(l)[0]}:1 ({min(l)[1]})')
    for key, res in r['cvd'].items():
        print(key)
        for k, v in res.items():
            print(f'  {k:13} closest {v["closest"][0]:5} {v["closest"][1]}/{v["closest"][2]}   near: ' + ', '.join(f'{s} {d} ({x})' for s, (d, x) in v['near'].items()))
