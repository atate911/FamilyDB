// node _kit/palette.js sheet
// Writes palette.html in the app's shell (taken from type.html) from the tokens in _kit/palette.js.
// Every swatch is drawn by the live tokens: a block with data-theme="dark" or "light" shows that theme,
// so night and day sit side by side whatever the device is set to. The colour-blind rows use SVG
// filters with the same Machado 2009 matrices as the check.
const fs = require("fs"), path = require("path");
const K = require("./colour.js");
const { PEOPLE, tokens, peopleFor } = require("./palette.js");
const ROOT = path.resolve(__dirname, "..");

const N = tokens(true), D = tokens(false), PN = peopleFor(true), PD = peopleFor(false);
const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const r1 = x => x.toFixed(1);
const initial = p => p.who ? p.who[0] : p.slot.slice(1);
const label = p => p.who ? `${p.who}` : `Slot ${p.slot.slice(1)}`;

// ---------- pieces ----------
const avatars = (size = "") => PEOPLE.map(p => `<span class="av ${p.slot}${size}" aria-hidden="true">${initial(p)}</span>`).join("");
const stripes = () => PEOPLE.map(p => `<span class="pal-stripe ${p.slot}"></span>`).join("");
function scene(theme, cap) {
  return `<figure class="pal-scene pal-th" data-theme="${theme}">
          <figcaption class="pal-cap"><span>${cap}</span><span class="m">${theme === "dark" ? "the default" : "lights on"}</span></figcaption>
          <div class="pal-scene__in">
            <div class="pal-band" aria-hidden="true">
              <b class="wm">FamilyDB<span class="wm__cur"></span></b>
              <span class="pal-band__here">Home</span>
              <span class="pal-band__row">To do <span class="badge badge--late">3 late</span></span>
              <span class="pal-band__row">Plans</span>
            </div>
            <div class="pal-page">
              <div class="pal-ask" aria-hidden="true"><span class="pal-ask__line"><span class="pal-ask__gt">&gt;</span> say it the way you’d say it</span><span class="pal-send">Send</span></div>
              <div class="pal-people" aria-hidden="true">${avatars()}</div>
              <div class="pal-routes" aria-hidden="true">${stripes()}</div>
              <p class="pal-sigs"><span class="pal-today">Sat 3 Oct</span> <span class="pal-late">6 days late</span> <span class="pal-warn">⚠ 3 steps left</span> <span class="pal-ok">✓ Done</span></p>
              <p class="pal-acts"><a href="#s-signals">A link</a> <span class="pal-primary">Add a plan</span></p>
            </div>
          </div>
        </figure>`;
}

function personRow(i) {
  const n = PN[i], d = PD[i], p = PEOPLE[i];
  const cell = (theme, q) => `<td class="pal-th" data-theme="${theme}"><div class="pal-pcell">
                <span class="av av--lg ${p.slot}" aria-hidden="true">${initial(p)}</span>
                <span class="pal-route ${p.slot}" aria-hidden="true"></span>
                <span class="pal-wash ${p.slot}"><b class="pal-pname">${esc(label(p))}</b> <span class="m">7 pm</span></span>
                <code class="pal-hex">avatar ${q.base} · soft ${q.soft}<br>ink ${q.ink} · mark ${q.mark}</code>
              </div></td>`;
  return `<tr>
              <th scope="row"><span class="pal-slot">--${p.slot}</span><b>${esc(p.name)}</b><small>${p.who ? esc(p.who) : "free slot"} · letter ${r1(K.contrast(N["--on-p"], n.base))}:1</small></th>
              ${cell("dark", n)}
              ${cell("light", d)}
            </tr>`;
}

function filters() {
  const M = {
    protanopia: [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    deuteranopia: [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    tritanopia: [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
  };
  return `<svg class="sprite" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg">${Object.entries(M).map(([k, m]) =>
    `<filter id="cvd-${k}" color-interpolation-filters="linearRGB"><feColorMatrix type="matrix" values="${m.map(r => r.join(" ") + " 0 0").join(" ")} 0 0 0 1 0"/></filter>`).join("")}</svg>`;
}
function closest(list, kind) {
  let b = { d: 1e9 }; for (let i = 0; i < list.length; i++) for (let j = i + 1; j < list.length; j++) { const d = K.de(list[i].hex, list[j].hex, kind); if (d < b.d) b = { d, a: list[i].n, b: list[j].n }; } return b;
}
function cvdRows() {
  const av = PN.map(p => ({ hex: p.base, n: p.name })), sd = PD.map(p => ({ hex: p.mark, n: p.name }));
  return K.KINDS.map(k => {
    const a = closest(av, k), s = closest(sd, k), name = k === "normal" ? "Normal vision" : k[0].toUpperCase() + k.slice(1);
    const cell = theme => `<td class="pal-th pal-sim pal-sim--${k}" data-theme="${theme}"><span class="pal-people">${avatars()}</span><span class="pal-routes pal-routes--sm">${stripes()}</span></td>`;
    return `<tr><th scope="row"><b>${name}</b><small>closest: ${r1(a.d)} at night (${a.a} / ${a.b}), ${r1(s.d)} by day (${s.a} / ${s.b})</small></th>${cell("dark")}${cell("light")}</tr>`;
  }).join("\n            ");
}

const SIGNALS = [
  ["Late", "the only red", "--alert", `<span class="pal-late">6 days late</span> <span class="badge badge--late">3 late</span>`, "Always with the words “days late”; the plate is the panel’s late count."],
  ["Set this up", "sodium amber", "--warn", `<span class="pal-warn">⚠ 3 steps left</span>`, "Always with ⚠ and words, on its own wash."],
  ["Done, working", "green", "--ok", `<span class="pal-ok">✓ Done</span>`, "Ticks and receipts; the tick itself is Vera’s green."],
  ["Today", "Vera’s green stamp", "--today-bg", `<span class="pal-today">Sat 3 Oct</span>`, "The date stamp on Home and the calendar."],
  ["Vera", "phosphor on green-black glass", "--phosphor", `<span class="pal-ask pal-ask--mini"><span class="pal-ask__line"><span class="pal-ask__gt">&gt;</span> ready</span><span class="pal-send">Send</span></span>`, "Hers alone: the glass, the lit cursor, the ready pill, the mark."],
  ["Links", "ink, moonlit underline", "--link-line", `<a href="#s-signals">See the plan</a>`, "Ink words with a blue underline that turns ink on hover."],
  ["The one primary button", "ink", "--primary", `<span class="pal-primary">Add a plan</span>`, "Soft white at night, midnight by day."],
  ["Focus", "moonlight ring", "--focus", `<span class="pal-focus">Focused</span>`, "Phosphor on the panel and on glass."],
];
function signalRows() {
  return SIGNALS.map(([name, sub, tok, html, note]) => `<tr><th scope="row"><b>${name}</b><small>${sub}</small></th>
              <td class="pal-th" data-theme="dark">${html}<code class="pal-hex">${tok} ${N[tok]}</code></td>
              <td class="pal-th" data-theme="light">${html}<code class="pal-hex">${tok} ${D[tok]}</code></td>
              <td class="pal-note">${note}</td></tr>`).join("\n            ");
}

const GROUPS = [
  ["The page", /^--(paper|paper-2|card|field|ink|ink-2|ink-3|line|line-2|rule|edge)$/],
  ["The panel", /^--(band|on-band|on-band-2|band-line|band-hi|band-edge)$/],
  ["Vera, today, the glass", /^--(vera|today|on-today|on-vera|ask-|send|on-send|glass|phosphor|cursor|vs-halo)/],
  ["Signals and actions", /^--(ok|warn|alert|on-alert|focus|link|primary|on-primary)/],
  ["People", /^--(on-p|p\d|everyone)/],
];
function tokenTables() {
  const seen = new Set();
  return GROUPS.map(([title, re]) => {
    const keys = Object.keys(N).filter(k => re.test(k) && !seen.has(k) && /^#|^rgba|^transparent/.test(N[k])); keys.forEach(k => seen.add(k));
    const sw = (theme, k) => /^#|^rgba/.test(theme === "dark" ? N[k] : D[k]) ? `<span class="pal-sw t${k.slice(1)}"></span>` : "";
    return `<div><h3 class="pal-h3">${title}</h3>
          <table class="pal-tokens">
            <thead><tr><th scope="col">Token</th><th scope="col">Night</th><th scope="col">Day</th></tr></thead>
            <tbody>
            ${keys.map(k => `<tr><th scope="row"><code>${k}</code></th><td class="pal-th" data-theme="dark">${sw("dark", k)}<code>${esc(N[k])}</code></td><td class="pal-th" data-theme="light">${sw("light", k)}<code>${esc(D[k])}</code></td></tr>`).join("\n            ")}
            </tbody>
          </table></div>`;
  }).join("\n          ");
}

function run() {
  const src = fs.readFileSync(path.join(ROOT, "type.html"), "utf8");
  const top = src.slice(0, src.indexOf('<div class="wrap">') + '<div class="wrap">'.length).replace("<title>Type · FamilyDB</title>", "<title>Palette · FamilyDB</title>");
  const tail = src.slice(src.indexOf("  </main>"));
  const { pairs } = require("./palette-check.js");
  let n = 0, fails = 0; for (const night of [true, false]) for (const p of pairs(tokens(night), night)) { n++; if (K.contrast(p.a, p.b) < p.floor) fails++; }
  const letters = PN.map(p => K.contrast(N["--on-p"], p.base)); const minLetter = Math.min(...letters);
  const worst = (list) => { let w = { d: 1e9 }; for (const k of K.KINDS.slice(1)) { const c = closest(list, k); if (c.d < w.d) w = { ...c, k }; } return w; };
  const wa = worst(PN.map(p => ({ hex: p.base, n: p.name }))), wd = worst(PD.map(p => ({ hex: p.mark, n: p.name })));

  const body = `
      <div class="runhead" aria-hidden="true"><span><b>FamilyDB</b> · Palette</span><span>Saturday 3 October 2026</span></div>

      <div class="page-head">
        <div><p class="overline">Colour</p><h1>Midnight</h1>
        <p class="lede">Night comes first. A blue-black kitchen at night: the panel darker than the page, ink in soft white, each person’s colour lit like a window, and Vera’s green glass at home among them. By day the lights come on and the panel stays midnight.</p></div>
      </div>
${filters()}
      <section class="sheet-sec" aria-labelledby="s-idea">
        <h2 id="s-idea">The idea: a kitchen at night</h2>
        <p>Every earlier palette was a light grey page with a navy panel. Midnight starts from the other end: FamilyDB opens dark, the way a screen in a dark kitchen should look. In the dark the phosphor history speaks loudest, so Vera’s glass is no longer the one dark thing on a light page. It is the one <em>green</em> light among blue-black.</p>
        <div class="pal-duo">
        ${scene("dark", "Night")}
        ${scene("light", "Day")}
        </div>
        <dl class="pal-legend">
          <div><dt>The panel</dt><dd>Darker than the page at night, with a hairline where they meet. By day it is the night that stays: midnight #0A0F1E beside a moonstone page.</dd></div>
          <div><dt>The page</dt><dd>Blue-black #0B1020, not graphite and not navy; ink is soft white #E3E8F3, never pure white, so a page at night doesn’t glare.</dd></div>
          <div><dt>Lit windows</dt><dd>The eight people are luminous mid-light colours with a faint glow at night. The same avatar by day; stripes and names go deeper to stay legible on paper.</dd></div>
          <div><dt>Green glass</dt><dd>Vera’s glass is green-black, not blue-black, with its phosphor ring and Send. Next to the panel the hue, the rim and her round corners keep the two apart.</dd></div>
        </dl>
      </section>

      <section class="sheet-sec" aria-labelledby="s-people">
        <h2 id="s-people">The eight people</h2>
        <p>Avatar, route stripe and a one-person plan’s wash, night beside day. Each is its own hue family (blue, iris, lagoon, apricot, heather, sky, ochre, sage), and neighbours differ in lightness as well as hue, so they part for colour-blind eyes too. No pink, no red, nothing that could be Vera’s green. Every avatar takes the same midnight letter; the weakest is ${r1(minLetter)}:1.</p>
        <div class="pal-scroll">
          <table class="pal-ptable">
            <thead><tr><th scope="col">Person</th><th scope="col">Night</th><th scope="col">Day</th></tr></thead>
            <tbody>
            ${PEOPLE.map((_, i) => personRow(i)).join("\n            ")}
            <tr><th scope="row"><span class="pal-slot">--everyone</span><b>Everyone</b><small>neutral, with the house</small></th>
              <td class="pal-th" data-theme="dark"><div class="pal-pcell"><span class="av av--lg p0" aria-hidden="true"><svg class="icon" aria-hidden="true"><use href="#i-home"/></svg></span><span class="pal-route p0" aria-hidden="true"></span><span class="pal-wash p0"><b class="pal-pname">Everyone</b> <span class="m">8 am</span></span><code class="pal-hex">${N["--everyone"]} · mark ${N["--everyone-mark"]}</code></div></td>
              <td class="pal-th" data-theme="light"><div class="pal-pcell"><span class="av av--lg p0" aria-hidden="true"><svg class="icon" aria-hidden="true"><use href="#i-home"/></svg></span><span class="pal-route p0" aria-hidden="true"></span><span class="pal-wash p0"><b class="pal-pname">Everyone</b> <span class="m">8 am</span></span><code class="pal-hex">${D["--everyone"]} · mark ${D["--everyone-mark"]}</code></div></td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="sheet-sec" aria-labelledby="s-cvd">
        <h2 id="s-cvd">As colour-blind eyes see them</h2>
        <p>The same avatars and stripes through a simulation of each kind of colour-blindness (Machado 2009), measured in CIEDE2000. Under about 8, two colours can be confused alone. The closest pair anywhere is ${r1(wa.d)} for avatars (${wa.a} / ${wa.b}, ${wa.k}) and ${r1(wd.d)} for day stripes (${wd.a} / ${wd.b}, ${wd.k}). Names and initials are always beside the colour.</p>
        <div class="pal-scroll">
          <table class="pal-ptable pal-cvd">
            <thead><tr><th scope="col">Vision</th><th scope="col">Night</th><th scope="col">Day</th></tr></thead>
            <tbody>
            ${cvdRows()}
            </tbody>
          </table>
        </div>
      </section>

      <section class="sheet-sec" aria-labelledby="s-signals">
        <h2 id="s-signals">Signals</h2>
        <p>Red means late and nothing else. Green means today and Vera. Amber means set this up. Each one always comes with a word or a sign, so colour is never the only cue.</p>
        <div class="pal-scroll">
          <table class="pal-ptable pal-sigt">
            <thead><tr><th scope="col">Signal</th><th scope="col">Night</th><th scope="col">Day</th><th scope="col">Rule</th></tr></thead>
            <tbody>
            ${signalRows()}
            </tbody>
          </table>
        </div>
      </section>

      <section class="sheet-sec" aria-labelledby="s-tokens">
        <h2 id="s-tokens">Every colour token</h2>
        <p>Written into <code>style.css</code> by <code>_kit/palette.js</code>; this page is written by the same script. Checked by <code>node _kit/palette.js check</code>: ${n} contrast pairs, ${fails ? fails + " below the floor" : "all at or above the floor"} (text 4.5:1, controls, stripes and plates 3:1).</p>
        <div class="pal-tok-grid">
          ${tokenTables()}
        </div>
      </section>
    </div>
`;
  fs.writeFileSync(path.join(ROOT, "palette.html"), top + body + tail);
  console.log("palette.html written");
}
module.exports = { run };
