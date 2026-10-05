# Writes Dusk's values (from dusk-values.py) into style.css's two :root blocks, between the
# "dusk:start" and "dusk:end" comments. Brand tokens (glass, phosphor, Send) stay outside them.
import sys, os, re, importlib.util
here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("dv", os.path.join(here, "dusk-values.py")); dv = importlib.util.module_from_spec(spec); spec.loader.exec_module(dv)
L, D = dv.hexes()

DAY = """  /* surfaces: the page is dusk-grey, with the faintest warmth left in it (never cream, never pink) */
  --paper: {paper};  --paper-2: {paper-2};  --card: {card};  --field: {field};
  /* text: indigo-black ink, the colour of the sky just after the light goes */
  --ink: {ink};  --ink-2: {ink-2};  --ink-3: {ink-3};
  /* lines: hairlines (decorative), the ruled head (ink), control edges (3:1) */
  --line: {line};  --line-2: {line-2};  --rule: {ink};  --edge: {edge};
  /* the panel: the evening sky, deep indigo-violet, deepening toward violet at its foot (and the phone's top bar) */
  --band: {band};  --band-2: {band-2};  --on-band: {on-band};  --on-band-2: {on-band-2};  --band-line: {band-line};  --band-hi: {band-hi};
  --band-sky: linear-gradient(180deg, {band} 0%, {band} 35%, {band-2} 100%);
  --band-sky-x: linear-gradient(90deg, {band} 0%, {band-2} 100%);
  /* the signal: apricot, the last light. What you act on next: today, the next plan, Leave by, the primary button */
  --signal: {signal};  --signal-2: {signal-2};  --on-signal: {ink};  --signal-mark: {signal-mark};  --signal-ink: {signal-ink};
  --signal-soft: {signal-soft};  --signal-line: {signal-line};
"""
DAY_TONES = """  /* tones */
  --ok: #17703F;  --ok-soft: #DDF1E4;  --ok-line: #A9D9BA;
  --warn: {warn};  --warn-soft: {warn-soft};  --warn-line: {warn-line};
  --alert: {alert};  --alert-soft: {alert-soft};  --alert-line: {alert-line};
  --alert-plate: {alert-plate};  --on-alert-plate: #FFFFFF;
  --focus: {focus};
"""
NIGHT = """    --paper: {paper};  --paper-2: {paper-2};  --card: {card};  --field: {field};
    --ink: {ink};  --ink-2: {ink-2};  --ink-3: {ink-3};
    --line: {line};  --line-2: {line-2};  --rule: {ink};  --edge: {edge};
    --band: {band};  --band-2: {band-2};  --on-band: {on-band};  --on-band-2: {on-band-2};  --band-line: {band-line};  --band-hi: {band-hi};
    --band-sky: linear-gradient(180deg, {band} 0%, {band} 35%, {band-2} 100%);
    --band-sky-x: linear-gradient(90deg, {band} 0%, {band-2} 100%);
    --signal: {signal};  --signal-2: {signal-2};  --on-signal: {paper};  --signal-mark: {signal-mark};  --signal-ink: {signal-ink};
    --signal-soft: {signal-soft};  --signal-line: {signal-line};
"""
NIGHT_TONES = """    --ok: #7FE3A5;  --ok-soft: #10251A;  --ok-line: #24503A;
    --warn: {warn};  --warn-soft: {warn-soft};  --warn-line: {warn-line};
    --alert: {alert};  --alert-soft: {alert-soft};  --alert-line: {alert-line};
    --alert-plate: {alert-plate};  --on-alert-plate: #FFFFFF;
    --focus: {focus};
"""
def people(d, ind, night):
    out = [] if night else [ind + "--on-p: " + d["ink"] + ";"]
    for i in range(1, 9):
        out.append(ind + f"--p{i}: {d[f'p{i}']}; --p{i}-soft: {d[f'p{i}-soft']}; --p{i}-ink: {d[f'p{i}-ink']}; --p{i}-mark: {d[f'p{i}-mark']};")
    out.append(ind + f"--everyone: {d['everyone']}; --everyone-soft: {d['everyone-soft']}; --everyone-ink: {d['everyone-ink']}; --everyone-mark: {d['everyone-mark']};")
    out.append(ind + f"--today-bg: {d['signal']}; --on-today: {d['paper'] if night else d['ink']}; --today-wash: {d['signal-soft']}; --today-ink: {d['signal-ink']};")
    return "\n".join(out) + "\n"
def actions(d, ind, night):
    if night:
        return ind + f"--link: {d['ink']};  --link-line: {d['signal-mark']};  --primary: {d['signal']};  --primary-2: {d['signal-2']};  --primary-edge: {d['signal']};  --on-primary: {d['paper']};\n"
    return ind + f"--link: {d['ink']};  --link-line: {d['signal-mark']};  --primary: {d['signal']};  --primary-2: {d['signal-2']};  --primary-edge: {d['ink']};  --on-primary: {d['ink']};\n"

def fill(t, d): return re.sub(r"\{([\w-]+)\}", lambda m: d[m.group(1)], t)
css_path = os.path.join(here, "..", "style.css")
css = open(css_path).read()
def put(css, tag, text):
    return re.sub(r"(( *)/\* dusk:%s \*/\n).*?[ \t]*(/\* /dusk:%s \*/)" % (tag, tag), lambda m: m.group(1) + text + m.group(2) + m.group(3), css, flags=re.S)
css = put(css, "day", fill(DAY, L))
css = put(css, "day-tones", fill(DAY_TONES, L))
css = put(css, "day-people", people(L, "  ", False) + actions(L, "  ", False))
css = put(css, "night", fill(NIGHT, D))
css = put(css, "night-tones", fill(NIGHT_TONES, D))
css = put(css, "night-people", people(D, "    ", True) + actions(D, "    ", True))
open(css_path, "w").write(css)
print("style.css: Dusk tokens written")
