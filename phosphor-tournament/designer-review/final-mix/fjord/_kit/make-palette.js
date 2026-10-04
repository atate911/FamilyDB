// node _kit/make-palette.js
// Writes palette.html (the palette sheet) from the tokens in style.css, in the same shell as type.html,
// and the swatch classes it needs into style.css between the "palette sheet" markers.
// Every value and every contrast figure on the sheet is read or measured here, so the sheet can't drift.
const fs = require("fs"), path = require("path"), { execFileSync } = require("child_process");
const dir = path.join(__dirname, "..");
const cssFile = path.join(dir, "style.css");
let css = fs.readFileSync(cssFile, "utf8");

function block(src, re) {
  const m = src.match(re); let i = m.index + m[0].length, d = 1; const s = i;
  while (d) { if (src[i] === "{") d++; if (src[i] === "}") d--; i++; }
  return src.slice(s, i - 1);
}
const toks = src => Object.fromEntries([...src.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)].map(m => [m[1], m[2].trim()]));
const day = toks(block(css, /^:root\s*\{/m));
const night = { ...day, ...toks(block(css, /@media \(prefers-color-scheme: dark\)\s*\{\s*:root\s*\{/)) };
const res = (T, v) => { let n = 0; while (v && /^var\(/.test(v) && n++ < 5) v = T[v.match(/var\((--[\w-]+)/)[1]]; return v; };
const val = (T, k) => { const v = res(T, T[k]); return /^#/.test(v) ? v.toUpperCase() : v.replace(/\s+/g, " "); };
const report = JSON.parse(execFileSync("node", [path.join(__dirname, "palette-check.js"), cssFile, "--json"]).toString());
const ratioOf = (theme, f, b) => { const r = report.contrast.find(x => x[0] === theme && x[1] === f && x[2] === b); return r ? r[3].toFixed(1) : "–"; };

const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");
const used = new Set();
const sw = k => { used.add(k); return `<span class="pal-sw pal-sw--${k.slice(2)}" aria-hidden="true"></span>`; };
const vals = k => { const d = val(day, k), n = val(night, k); return `<span class="pal-v"><span class="pal-v__t">day</span> <code class="m">${esc(d)}</code></span><span class="pal-v"><span class="pal-v__t">night</span> <code class="m">${esc(n)}</code></span>`; };
const row = (k, job) => `<li class="pal-row">${sw(k)}<span class="pal-row__k"><b class="m">${k}</b>${vals(k)}</span><span class="pal-row__j">${job}</span></li>`;
const list = rows => `<ul class="pal-rows plain">\n${rows.map(([k, j]) => "  " + row(k, j)).join("\n")}\n</ul>`;

const people = [
  ["p1", "Cornflower", "Sam", "the clear blue of a field flower; the family's steadiest colour"],
  ["p2", "Heather", "Alex", "dusk on the fell: a grey violet, never pink"],
  ["p3", "Cloudberry", "Maya", "the one warm, ripe colour; her pages are ruled in it"],
  ["p4", "Sea", "Theo", "shallow fjord water over pale stones"],
  ["p5", "Pine", "free", "a grey spruce-green, kept far from Vera's green"],
  ["p6", "Lichen", "free", "birch-bark yellow-green; light avatar, olive stripe"],
  ["p7", "Rye", "free", "crispbread brown: warm, quiet, not red"],
  ["p8", "Lupin", "free", "the roadside lupin: a light blue-violet"],
];
const letters = { Sam: "S", Alex: "A", Maya: "M", Theo: "T" };

const personRow = ([s, name, who, note], i) => {
  const L = letters[who] || String(i + 1);
  const label = who === "free" ? `${i + 1} · free slot` : `${i + 1} · ${who}`;
  return `<li class="pal-person ${s}">
    <span class="pal-person__avs"><span class="av av--lg ${s}" aria-hidden="true">${L}</span><span class="av ${s}" aria-hidden="true">${L}</span><span class="av av--sm ${s}" aria-hidden="true">${L}</span></span>
    <span class="pal-person__id"><b class="pal-person__name">${name}</b><span class="label">${label}</span><span class="pal-person__ink">${who === "free" ? name : who + "’s"} name in ink</span><span class="small muted">${note}</span></span>
    <span class="pal-ev" aria-hidden="true"><span class="pal-ev__t m">7 pm</span><b>${who === "free" ? name : who + "’s"} plan</b></span>
    <ul class="pal-quad plain">
      <li>${sw("--" + s)}<span><b class="m">base</b>${vals("--" + s)}<span class="small muted">letter ${ratioOf("light", "--on-p", "--" + s)}:1</span></span></li>
      <li>${sw("--" + s + "-soft")}<span><b class="m">-soft</b>${vals("--" + s + "-soft")}</span></li>
      <li>${sw("--" + s + "-ink")}<span><b class="m">-ink</b>${vals("--" + s + "-ink")}<span class="small muted">${ratioOf("light", "--" + s + "-ink", "--" + s + "-soft")} / ${ratioOf("dark", "--" + s + "-ink", "--" + s + "-soft")} on soft</span></span></li>
      <li>${sw("--" + s + "-mark")}<span><b class="m">-mark</b>${vals("--" + s + "-mark")}<span class="small muted">${ratioOf("light", "--" + s + "-mark", "--paper")} / ${ratioOf("dark", "--" + s + "-mark", "--paper")} on paper</span></span></li>
    </ul>
  </li>`;
};

const ladder = [["--card", "card"], ["--paper", "paper: the sky"], ["--paper-2", "paper-2"], ["--line", "line"], ["--line-2", "line-2"], ["--edge", "edge"], ["--ink-3", "ink-3"], ["--ink-2", "ink-2"], ["--band-hi", "band-hi"], ["--band", "band: the deep water"], ["--ink", "ink"]];

const cb = report.sets;
const cbRow = (k, label) => {
  const v = cb[k], kinds = ["normal", "protan", "deutan", "tritan"], nm = x => people.find(p => p[0] === x)[1];
  return `<tr><th scope="row"><b>${label}</b></th>${kinds.map(x => `<td data-label="${x}"><b class="num">${v.perKind[x].d.toFixed(1)}</b><small>${nm(v.perKind[x].a)} / ${nm(v.perKind[x].b)}</small></td>`).join("")}</tr>`;
};
const passes = report.contrast.filter(r => typeof r[3] === "number");
const failing = passes.filter(r => r[3] < r[4]).length;

const type = fs.readFileSync(path.join(dir, "type.html"), "utf8");
const head = type.slice(0, type.indexOf('<main')).replace("<title>Type · FamilyDB</title>", "<title>Palette · FamilyDB</title>");
const tail = type.slice(type.indexOf("</main>"));

const main = `<main class="main" id="main">
    <div class="wrap pal">
      <div class="runhead" aria-hidden="true"><span><b>FamilyDB</b> · Palette</span><span>Saturday 3 October 2026</span></div>

      <div class="page-head">
        <div><p class="overline">Specimen</p><h1>Fjord</h1><p class="lede">A pale northern sky over deep slate water. The page is cool, light and quiet, so the only colours that speak are the family’s eight, and the one thing that glows is Vera’s green glass.</p></div>
      </div>

      <section class="sheet-sec" aria-labelledby="s-axis">
        <h2 id="s-axis">One cool axis, sky to depth</h2>
        <p>Every neutral sits on one blue-grey line, from the white of a field to the slate-indigo of the panel. Nothing on it is warm and nothing is bright, so it never competes. Against it, the people are clean colours and Vera is the only light.</p>
        <figure class="pal-fjord" aria-hidden="true">
          <div class="pal-fjord__sky">
            <span class="pal-fjord__people">${people.map(([s], i) => `<span class="av ${s}">${letters[people[i][2]] || i + 1}</span>`).join("")}</span>
            <span class="pal-fjord__vera"><svg class="vs" width="40" height="40" viewBox="0 0 32 32" focusable="false"><rect class="vs__bg" width="32" height="32" rx="8"/><rect class="vs__rim" x=".5" y=".5" width="31" height="31" rx="7.5"/><g class="vs__rows"><rect class="vs__r" x="6" y="6" width="12" height="3" rx="1.5"/><rect class="vs__r" x="20" y="6" width="6" height="3" rx="1.5"/></g><polyline class="vs__p" points="6.5,17.5 10.5,21.25 6.5,25" stroke-width="2"/><rect class="vs__c" x="13.5" y="16.75" width="6" height="9" rx="1"/></svg></span>
          </div>
          <ol class="pal-ladder plain">${ladder.map(([k, l]) => `<li>${sw(k)}<span class="m"><span class="pal-d">${val(day, k)}</span><span class="pal-n">${val(night, k)}</span></span><span class="label">${l}</span></li>`).join("")}</ol>
        </figure>
      </section>

      <section class="sheet-sec" aria-labelledby="s-people">
        <h2 id="s-people">The eight people</h2>
        <p>Colours from a northern summer: cornflower, heather, cloudberry, sea, pine, lichen, rye and lupin. They’re clean and a little cool, never sugary, and none of them is red or Vera’s green. Every avatar takes a dark letter (lowest ${Math.min(...people.map(([s]) => +ratioOf("light", "--on-p", "--" + s))).toFixed(1)}:1). Lightness alternates around the wheel, so colours that share a hue for colour-blind eyes still differ in value.</p>
        <div class="pal-side">
          <div><p class="label">Side by side</p><p class="pal-avs">${people.map(([s], i) => `<span class="av av--lg ${s}" aria-hidden="true">${letters[people[i][2]] || i + 1}</span>`).join("")}<span class="av av--lg p0" aria-hidden="true"><svg class="icon"><use href="#i-home"/></svg></span></p></div>
          <div><p class="label">Route stripes</p><p class="pal-stripes" aria-hidden="true">${people.map(([s]) => `<span class="route"><i class="${s}"></i></span>`).join("")}<span class="route"><i class="p0"></i></span></p></div>
          <div><p class="label">Several people</p><p class="pal-stripes" aria-hidden="true"><span class="route"><i class="p3"></i><i class="p4"></i></span><span class="route"><i class="p1"></i><i class="p2"></i></span><span class="route"><i class="p1"></i><i class="p3"></i><i class="p4"></i></span><span class="route"><i class="p5"></i><i class="p6"></i><i class="p7"></i><i class="p8"></i></span></p></div>
        </div>
        <ul class="pal-people plain">
${people.map(personRow).join("\n")}
          <li class="pal-person p0">
            <span class="pal-person__avs"><span class="av av--lg p0" aria-hidden="true"><svg class="icon"><use href="#i-home"/></svg></span><span class="av p0" aria-hidden="true"><svg class="icon"><use href="#i-home"/></svg></span><span class="av av--sm p0" aria-hidden="true"><svg class="icon"><use href="#i-home"/></svg></span></span>
            <span class="pal-person__id"><b class="pal-person__name">Everyone</b><span class="label">0 · the house</span><span class="pal-person__ink">Neutral, never a colour</span><span class="small muted">the axis itself: plans for the whole family</span></span>
            <span class="pal-ev" aria-hidden="true"><span class="pal-ev__t m">8 am</span><b>Everyone’s plan</b></span>
            <ul class="pal-quad plain">
              <li>${sw("--everyone")}<span><b class="m">base</b>${vals("--everyone")}</span></li>
              <li>${sw("--everyone-soft")}<span><b class="m">-soft</b>${vals("--everyone-soft")}</span></li>
              <li>${sw("--everyone-ink")}<span><b class="m">-ink</b>${vals("--everyone-ink")}</span></li>
              <li>${sw("--everyone-mark")}<span><b class="m">-mark</b>${vals("--everyone-mark")}</span></li>
            </ul>
          </li>
        </ul>
      </section>

      <section class="sheet-sec" aria-labelledby="s-page">
        <h2 id="s-page">The page</h2>
        <p>Light and airy by day: blue-grey paper, white fields, a soft blue-black ink. At night the same line goes dark: the page is a deep blue-black and the ink a pale frost.</p>
        ${list([["--paper", "the page"], ["--paper-2", "wells, hover rows, the weekend wash, “Off” tags"], ["--card", "inputs, tick boxes, banners inside Ask"], ["--ink", "text, ruled heads, picked controls"], ["--ink-2", "secondary text, margin times"], ["--ink-3", "quiet text and labels (still AA)"], ["--line", "hairlines between rows"], ["--line-2", "the running head’s and the calendar’s rules"], ["--edge", "control edges (3:1)"]])}
      </section>

      <section class="sheet-sec" aria-labelledby="s-panel">
        <h2 id="s-panel">The panel, beside Vera</h2>
        <p>The panel is the deep water: slate-indigo, the darkest thing on the page except Vera’s glass. The two dark blocks stay apart by hue (indigo against green-black), by value (the panel is lighter) and by form (Vera is round and lit).</p>
        <div class="pal-duo" aria-hidden="true">
          <div class="side pal-panel">
            <ul class="nav">
              <li><a href="home.html" aria-current="page" tabindex="-1"><svg class="icon" aria-hidden="true"><use href="#i-home"/></svg><span>Home</span></a></li>
              <li><a href="todo.html" tabindex="-1"><svg class="icon" aria-hidden="true"><use href="#i-todo"/></svg><span>To do</span><span class="badge badge--late">3 late</span></a></li>
              <li><a href="wishes.html" tabindex="-1"><svg class="icon" aria-hidden="true"><use href="#i-gift"/></svg><span>Wishes</span><span class="badge badge--act">1 to decide</span></a></li>
              <li><a href="plans.html" tabindex="-1"><svg class="icon" aria-hidden="true"><use href="#i-cal"/></svg><span>Plans</span><span class="badge badge--quiet">2 to rate</span></a></li>
            </ul>
          </div>
          <div class="ask pal-ask">
            <div class="ask__head"><svg class="vs" width="44" height="44" viewBox="0 0 32 32" aria-hidden="true" focusable="false"><rect class="vs__bg" width="32" height="32" rx="8"/><rect class="vs__rim" x=".5" y=".5" width="31" height="31" rx="7.5"/><g class="vs__rows"><rect class="vs__r" x="6" y="6" width="12" height="3" rx="1.5"/><rect class="vs__r" x="20" y="6" width="6" height="3" rx="1.5"/></g><polyline class="vs__p" points="6.5,17.5 10.5,21.25 6.5,25" stroke-width="2"/><rect class="vs__c" x="13.5" y="16.75" width="6" height="9" rx="1"/></svg><div><h3>Ask Vera</h3><p class="ask__line"><span class="ask__prompt">&gt;</span> say it the way you’d say it at the table.</p></div></div>
            <p class="pal-ask__send"><span class="btn composer__send" aria-hidden="true"><svg class="icon"><use href="#i-send"/></svg> Send</span></p>
          </div>
        </div>
        ${list([["--band", "the panel and the phone’s top bar"], ["--band-hi", "hover, the account plate"], ["--band-line", "rules on the panel"], ["--on-band", "sign lettering; the “you are here” plate"], ["--on-band-2", "quiet lettering and icons"], ["--alert-plate", "the late count on the panel"]])}
      </section>

      <section class="sheet-sec" aria-labelledby="s-signals">
        <h2 id="s-signals">Signals</h2>
        <p>Red is only lateness and breakage. Amber is “set this up”. Green is today, done and Vera. What you act on is deep fjord blue: links and the one primary button, with a bright blue focus ring. Each signal also says what it means in words.</p>
        <div class="pal-signals">
          <span class="pal-today" aria-hidden="true"><span>Sat</span><b class="num">3</b></span>
          <span class="tag tag--broken">6 days late</span>
          <span class="tag tag--look"><svg class="icon" aria-hidden="true"><use href="#i-alert"/></svg>3 steps left</span>
          <span class="tag tag--ok">Working</span>
          <span class="btn btn--primary" aria-hidden="true"><svg class="icon"><use href="#i-plus"/></svg>Add a plan</span>
          <span class="btn btn--quiet" aria-hidden="true">See the plan</span>
          <a href="todo.html">All 4 to-dos</a>
          <span class="btn btn--quiet pal-focus" aria-hidden="true">Focus ring</span>
        </div>
        ${list([["--alert", "late, broken, errors: the only red"], ["--alert-soft", "the late tag’s wash"], ["--warn", "set this up, needs a look"], ["--warn-soft", "the setup side note"], ["--ok", "working, done"], ["--ok-soft", "the done tag’s wash"], ["--today-bg", "today’s stamp"], ["--today-wash", "today’s calendar cell"], ["--vera", "Vera’s green as text"], ["--vera-bg", "a done tick, the meter, the panel’s “you are here” edge"], ["--link", "links"], ["--link-line", "a link’s underline"], ["--primary", "the one primary button"], ["--focus", "the focus ring"]])}
      </section>

      <section class="sheet-sec" aria-labelledby="s-glass">
        <h2 id="s-glass">Vera’s glass and the phosphor</h2>
        <p>Kept at today’s strength, on purpose: the shadow of FamilyDB’s first green CRT. The glass is green-black and the phosphor the only lit green, so on a cool blue page it reads as a small screen left on.</p>
        ${list([["--glass", "Vera’s glass, panes, the mark"], ["--ask-bg", "the Ask block"], ["--glass-ink", "words on glass"], ["--phosphor", "Send, her typed line’s prompt, the lit cursor on glass"], ["--cursor", "the wordmark’s cursor on paper"], ["--glass-alert", "“can’t answer” on glass"]])}
      </section>

      <section class="sheet-sec" aria-labelledby="s-check">
        <h2 id="s-check">The check</h2>
        <p><code class="m">node _kit/palette-check.js</code> reads these tokens from <code class="m">style.css</code>. ${passes.length} contrast pairs in both themes, ${failing ? failing + " below their floor" : "every one at or above its floor"}: AA for text, 3:1 for control edges, stripes and rules. For colour-blindness it simulates each eye (Machado 2009) and measures the closest two people (CIEDE2000; above about 8 they’re easy to tell apart side by side).</p>
        <div class="tscale-wrap mt-3">
          <table class="jobs pal-cb">
            <thead><tr><th scope="col">Closest pair</th><th scope="col">Normal</th><th scope="col">Protanopia</th><th scope="col">Deuteranopia</th><th scope="col">Tritanopia</th></tr></thead>
            <tbody>
              ${cbRow("avatars", "Avatars")}
              ${cbRow("stripes, day", "Route stripes, day")}
              ${cbRow("stripes, night", "Route stripes, night")}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </main>
`;
fs.writeFileSync(path.join(dir, "palette.html"), head + main + tail);

// swatch classes, one per token shown
const START = "/* @palette-sheet: generated by _kit/make-palette.js */", END = "/* @palette-sheet end */";
const sheetCss = `${START}
/* The palette sheet (palette.html). Nothing here is used by the app's pages. */
.pal-sw { display: inline-block; width: 44px; height: 44px; border-radius: var(--r-sm); box-shadow: inset 0 0 0 1px var(--line); flex: none; }
${[...used].map(k => `.pal-sw--${k.slice(2)} { background: var(${k}); }`).join("\n")}
.pal-rows { margin-top: var(--s4); display: grid; }
.pal-row { display: grid; grid-template-columns: 44px minmax(0, 17rem) minmax(0, 1fr); gap: var(--s4); align-items: center; padding: var(--s2) 0; border-top: 1px solid var(--line); }
.pal-row__k b { display: block; font-size: var(--t-sm); }
.pal-v { display: inline-block; margin-right: var(--s3); font-size: var(--t-sm); color: var(--ink-2); }
.pal-v__t { font-family: var(--font-num); font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-3); }
.pal-v code { font-size: var(--t-sm); }
.pal-row__j { color: var(--ink-2); }
.pal-fjord { margin-top: var(--s5); border-top: 1px solid var(--line-2); }
.pal-fjord__sky { display: flex; justify-content: space-between; align-items: center; gap: var(--s4); padding: var(--s7) var(--s5); background: linear-gradient(to bottom, var(--card), var(--paper)); }
.pal-fjord__people { display: flex; flex-wrap: wrap; gap: var(--s2); }
.pal-fjord__people .av { width: 44px; height: 44px; font-size: 1.1875rem; }
.pal-fjord__vera .vs { display: block; filter: drop-shadow(0 0 10px var(--phosphor-glow)); }
.pal-ladder { display: grid; grid-template-columns: repeat(11, minmax(0, 1fr)); }
.pal-ladder li { display: grid; gap: 2px; align-content: start; min-width: 0; }
.pal-ladder .pal-sw { width: 100%; height: 72px; border-radius: 0; box-shadow: none; }
.pal-ladder li:nth-child(10) .pal-sw, .pal-ladder li:nth-child(11) .pal-sw { height: 120px; }
.pal-ladder .m, .pal-ladder .label { font-size: var(--t-xs); padding-right: 4px; overflow-wrap: anywhere; }
.pal-side { display: flex; flex-wrap: wrap; gap: var(--s5) var(--s8); margin-top: var(--s5); }
.pal-avs { display: flex; flex-wrap: wrap; gap: var(--s2); margin-top: var(--s2); }
.pal-stripes { display: flex; gap: 10px; margin-top: var(--s2); }
.pal-stripes .route { width: 10px; min-height: 64px; height: 64px; border-radius: 5px; }
.pal-people { margin-top: var(--s5); display: grid; }
.pal-person { display: grid; grid-template-columns: 8.5rem minmax(0, 15rem) 10rem minmax(0, 1fr); gap: var(--s4); align-items: start; padding: var(--s4) 0; border-top: 1px solid var(--line); }
.pal-person__avs { display: flex; align-items: center; gap: var(--s2); }
.pal-person__id { display: grid; gap: 2px; border-left: 4px solid var(--p-mark); padding-left: var(--s3); }
.pal-person__name { font-family: var(--font-head); font-size: var(--t-h3); }
.pal-person__ink { color: var(--p-ink); font-weight: 700; }
.pal-ev { display: grid; padding: 4px var(--s2) 6px 10px; border-left: 4px solid var(--p-mark); background: var(--p-soft); color: var(--ink); font-size: var(--t-sm); }
.pal-ev__t { color: var(--ink-2); }
.pal-quad { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--s3) var(--s4); }
.pal-quad li { display: grid; grid-template-columns: 36px minmax(0, 1fr); gap: var(--s2); align-items: start; }
.pal-quad .pal-sw { width: 36px; height: 36px; }
.pal-quad b { display: block; font-size: var(--t-sm); }
.pal-quad .pal-v { display: block; margin: 0; }
.pal-quad .small { display: block; font-size: var(--t-sm); }
.pal-duo { display: grid; grid-template-columns: 248px minmax(0, 1fr); gap: var(--s5); margin-top: var(--s5); align-items: stretch; }
.pal-panel { padding: var(--s4) var(--s3); border-radius: var(--r-sm); }
.pal-ask { border-radius: 14px; box-shadow: var(--ask-rim), 0 0 0 4px var(--ask-ring), 0 0 34px -12px var(--phosphor-glow); display: flex; flex-direction: column; justify-content: space-between; gap: var(--s4); }
.pal-ask h3 { font-size: 1.5rem; color: var(--ask-ink); }
.pal-ask__send .btn { min-width: 9rem; }
.pal-signals { display: flex; flex-wrap: wrap; align-items: center; gap: var(--s3) var(--s4); margin-top: var(--s5); }
.pal-today { display: inline-grid; justify-items: center; padding: 4px 10px 6px; border-radius: var(--r-md); background: var(--today-bg); color: var(--on-today); font-family: var(--font-num); font-weight: 700; text-transform: uppercase; font-size: var(--t-sm); line-height: 1; }
.pal-today b { font-size: 1.75rem; }
.pal-focus { outline: 3px solid var(--focus); outline-offset: 3px; }
.pal-n { display: none; }
@media (prefers-color-scheme: dark) { .pal-d { display: none; } .pal-n { display: inline; } }
.pal-cb td b { display: block; font-size: 1.5rem; line-height: 1.1; }
@media (max-width: 1180px) { .pal-person { grid-template-columns: 8.5rem minmax(0, 1fr) 10rem; } .pal-quad { grid-column: 2 / -1; } }
@media (max-width: 820px) {
  .pal-row { grid-template-columns: 44px minmax(0, 1fr); }
  .pal-row__j { grid-column: 2; }
  .pal-person { grid-template-columns: minmax(0, 1fr); gap: var(--s3); }
  .pal-quad { grid-column: auto; }
  .pal-ladder { grid-template-columns: repeat(4, minmax(0, 1fr)); row-gap: var(--s3); }
  .pal-ladder .pal-sw, .pal-ladder li:nth-child(10) .pal-sw, .pal-ladder li:nth-child(11) .pal-sw { height: 48px; }
  .pal-fjord__sky { padding: var(--s5) var(--s3); }
  .pal-fjord__people .av { width: 32px; height: 32px; font-size: var(--t-sm); }
  .pal-duo { grid-template-columns: minmax(0, 1fr); }
  .pal-duo .pal-panel { display: block; }
}
${END}`;
const a = css.indexOf(START), b = css.indexOf(END);
if (a >= 0) css = css.slice(0, a) + sheetCss + css.slice(b + END.length);
else { const at = css.lastIndexOf("@media (prefers-reduced-motion: reduce)"); css = css.slice(0, at) + sheetCss + "\n\n" + css.slice(at); }
fs.writeFileSync(cssFile, css);
console.log("palette.html written;", used.size, "swatches");
