// node _kit/palette-check.js [style.css] [--json]
// Reads the colour tokens from style.css (:root, and the dark block), then
//  1. measures every contrast pair the standard promises (WCAG 2.2: 4.5:1 text, 3:1 controls, stripes, rules),
//  2. simulates protanopia, deuteranopia and tritanopia (Machado, Oliveira & Fernandes 2009, severity 1)
//     and reports the closest pair of people (CIEDE2000) for avatars, day stripes and night stripes,
//  3. checks no person sits near late red or Vera's green, in normal vision or any simulation.
// Exit code 1 if any floor fails.
const fs = require("fs"), path = require("path");
const file = process.argv[2] && !process.argv[2].startsWith("--") ? process.argv[2] : path.join(__dirname, "..", "style.css");
const css = fs.readFileSync(file, "utf8");

function block(re) {
  const m = css.match(re); if (!m) throw new Error("no block " + re);
  let i = m.index + m[0].length, depth = 1, s = i;
  while (depth) { if (css[i] === "{") depth++; if (css[i] === "}") depth--; i++; }
  return css.slice(s, i - 1);
}
function tokens(src) {
  const t = {};
  for (const m of src.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) t[m[1]] = m[2].trim();
  return t;
}
const light = tokens(block(/^:root\s*\{/m));
const darkSrc = block(/@media \(prefers-color-scheme: dark\)\s*\{\s*:root\s*\{/);
const dark = { ...light, ...tokens(darkSrc) };
const resolve = (T, v) => { let n = 0; while (/^var\(/.test(v) && n++ < 5) v = T[v.match(/var\((--[\w-]+)/)[1]]; return v; };

const hex = h => { h = h.replace("#", ""); if (h.length === 3) h = [...h].map(c => c + c).join(""); return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16) / 255); };
const lin = c => c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
const gam = c => c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055;
const lum = rgb => { const [r, g, b] = rgb.map(lin); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
const ratio = (a, b) => { const [x, y] = [lum(hex(a)), lum(hex(b))].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };

// Machado 2009, severity 1.0, applied in linear RGB
const M = {
  protan: [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
  deutan: [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
  tritan: [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
};
const sim = (rgb, k) => { if (k === "normal") return rgb; const l = rgb.map(lin); return M[k].map(r => gam(Math.min(1, Math.max(0, r[0] * l[0] + r[1] * l[1] + r[2] * l[2])))); };
const lab = rgb => {
  const [r, g, b] = rgb.map(lin);
  const X = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047, Y = 0.2126 * r + 0.7152 * g + 0.0722 * b, Z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883;
  const f = t => t > 216 / 24389 ? Math.cbrt(t) : (24389 / 27 * t + 16) / 116;
  return [116 * f(Y) - 16, 500 * (f(X) - f(Y)), 200 * (f(Y) - f(Z))];
};
function de2000([L1, a1, b1], [L2, a2, b2]) {
  const rad = Math.PI / 180, C1 = Math.hypot(a1, b1), C2 = Math.hypot(a2, b2), Cb = (C1 + C2) / 2;
  const G = 0.5 * (1 - Math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)));
  const ap1 = a1 * (1 + G), ap2 = a2 * (1 + G), Cp1 = Math.hypot(ap1, b1), Cp2 = Math.hypot(ap2, b2);
  const h = (b, a) => { if (!a && !b) return 0; const x = Math.atan2(b, a) / rad; return x < 0 ? x + 360 : x; };
  const hp1 = h(b1, ap1), hp2 = h(b2, ap2), dL = L2 - L1, dC = Cp2 - Cp1;
  let dh = 0; if (Cp1 * Cp2) { dh = hp2 - hp1; if (dh > 180) dh -= 360; else if (dh < -180) dh += 360; }
  const dH = 2 * Math.sqrt(Cp1 * Cp2) * Math.sin(dh * rad / 2), Lb = (L1 + L2) / 2, Cpb = (Cp1 + Cp2) / 2;
  let hb = hp1 + hp2; if (Cp1 * Cp2) { if (Math.abs(hp1 - hp2) > 180) hb += hb < 360 ? 360 : -360; hb /= 2; }
  const T = 1 - 0.17 * Math.cos((hb - 30) * rad) + 0.24 * Math.cos(2 * hb * rad) + 0.32 * Math.cos((3 * hb + 6) * rad) - 0.2 * Math.cos((4 * hb - 63) * rad);
  const dT = 30 * Math.exp(-(((hb - 275) / 25) ** 2)), Rc = 2 * Math.sqrt(Cpb ** 7 / (Cpb ** 7 + 25 ** 7));
  const Sl = 1 + 0.015 * (Lb - 50) ** 2 / Math.sqrt(20 + (Lb - 50) ** 2), Sc = 1 + 0.045 * Cpb, Sh = 1 + 0.015 * Cpb * T, Rt = -Math.sin(2 * dT * rad) * Rc;
  return Math.sqrt((dL / Sl) ** 2 + (dC / Sc) ** 2 + (dH / Sh) ** 2 + Rt * (dC / Sc) * (dH / Sh));
};
const dE = (a, b, k) => de2000(lab(sim(hex(a), k)), lab(sim(hex(b), k)));

// ---- 1. contrast pairs: [fg, bg, floor, use]
const P = n => [1, 2, 3, 4, 5, 6, 7, 8].map(i => n.replaceAll("N", i));
const pairs = [
  ["--ink", "--paper", 4.5, "body text"], ["--ink-2", "--paper", 4.5, "secondary text"], ["--ink-3", "--paper", 4.5, "quiet text, labels"],
  ["--ink-3", "--paper-2", 4.5, "quiet text on a well"], ["--ink-3", "--card", 4.5, "placeholders"], ["--ink-3", "--today-wash", 4.5, "today's cell"],
  ["--edge", "--paper", 3, "control edges"], ["--edge", "--card", 3, "field edges"], ["--edge", "--paper-2", 3, "edges on a well"],
  ["--focus", "--paper", 3, "focus ring"], ["--focus", "--card", 3, "focus ring on a field"],
  ["--link", "--paper", 4.5, "links"], ["--link", "--paper-2", 4.5, "links on a well"], ["--link-line", "--paper", 3, "link underline"],
  ["--on-primary", "--primary", 4.5, "primary button"], ["--primary", "--paper", 3, "primary button edge"], ["--on-primary", "--primary-2", 4.5, "primary hover"],
  ["--paper", "--ink", 4.5, "picked choice, Tomorrow stamp"],
  ["--vera", "--paper", 4.5, "Vera's name"], ["--vera", "--vera-soft", 4.5, "ready pill"], ["--on-vera", "--vera-bg", 4.5, "done tick"],
  ["--on-today", "--today-bg", 4.5, "today's stamp"], ["--today-bg", "--today-wash", 3, "today's rule"],
  ["--ok", "--ok-soft", 4.5, "tag Working"], ["--ok", "--paper", 4.5, "ok text"],
  ["--warn", "--warn-soft", 4.5, "setup panel"], ["--warn", "--paper", 4.5, "step numbers"], ["--ink", "--warn-soft", 4.5, "setup text"], ["--ink-2", "--warn-soft", 4.5, "setup quiet text"],
  ["--alert", "--alert-soft", 4.5, "late tag"], ["--alert", "--paper", 4.5, "late text"], ["--alert", "--card", 4.5, "error on a field"],
  ["--on-band", "--band", 4.5, "panel text"], ["--on-band-2", "--band", 4.5, "panel quiet text"], ["--on-band-2", "--band-hi", 4.5, "account plate"],
  ["--band", "--on-band", 4.5, "you are here plate"], ["--on-alert-plate", "--alert-plate", 4.5, "late count on the panel"],
  ["--phosphor", "--band", 3, "focus ring on the panel"], ["--vera-bg", "--on-band||--band", 3, "you-are-here green edge (against the plate or the panel, whichever it is drawn on more strongly)"],
  ["--everyone-mark", "--paper", 3, "Everyone's stripe"], ["--everyone-ink", "--everyone", 4.5, "house avatar"], ["--everyone-ink", "--paper", 4.5, "Everyone name"],
  ["--phosphor", "--glass", 4.5, "phosphor on glass"], ["--glass-ink", "--glass", 4.5, "pane text"], ["--glass-ink-2", "--glass", 4.5, "pane quiet text"],
  ["--ask-ink", "--ask-bg", 4.5, "Ask text"], ["--ask-ink-2", "--ask-bg", 4.5, "Vera's typed line"], ["--on-send", "--send", 4.5, "Send"],
  ["--glass-alert", "--glass", 4.5, "can't answer"], ["--cursor", "--paper", 3, "wordmark cursor on paper"],
  ...P("--on-p|--pN").map(s => [...s.split("|"), 4.5, "avatar letter"]),
  ...P("--ink|--pN-soft").map(s => [...s.split("|"), 4.5, "words on a one-person plan"]),
  ...P("--ink-2|--pN-soft").map(s => [...s.split("|"), 4.5, "time on a plan"]),
  ...P("--pN-ink|--pN-soft").map(s => [...s.split("|"), 4.5, "name on wash, kid's tab"]),
  ...P("--pN-ink|--paper").map(s => [...s.split("|"), 4.5, "name on paper"]),
  ...P("--pN-mark|--paper").map(s => [...s.split("|"), 3, "stripe, rule"]),
  ...P("--pN-mark|--pN-soft").map(s => [...s.split("|"), 3, "event rule on its wash"]),
  ...P("--pN|--band").map(s => [...s.split("|"), 3, "kid's edge on the panel"]),
];
const json = process.argv.includes("--json");
let fails = 0; const rows = [];
for (const [name, T] of [["light", light], ["dark", dark]]) {
  for (const [f, b, floor, use] of pairs) {
    const fv = resolve(T, T[f]), bvs = b.split("||").map(x => resolve(T, T[x]));
    if (!/^#/.test(fv || "") || bvs.some(bv => !/^#/.test(bv || ""))) { rows.push([name, f, b, "n/a", floor, use]); continue; }
    const r = Math.max(...bvs.map(bv => ratio(fv, bv))); if (r < floor) fails++;
    rows.push([name, f, b, r, floor, use]);
  }
}
const kinds = ["normal", "protan", "deutan", "tritan"];
function closest(list) {
  let best = { d: 1e9 };
  for (const k of kinds) for (let i = 0; i < list.length; i++) for (let j = i + 1; j < list.length; j++) {
    const d = dE(list[i][1], list[j][1], k); if (d < best.d) best = { d, k, a: list[i][0], b: list[j][0] };
  }
  return best;
}
function perKind(list) {
  const o = {};
  for (const k of kinds) { let m = { d: 1e9 }; for (let i = 0; i < list.length; i++) for (let j = i + 1; j < list.length; j++) { const d = dE(list[i][1], list[j][1], k); if (d < m.d) m = { d, a: list[i][0], b: list[j][0] }; } o[k] = m; }
  return o;
}
const names = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8"];
const sets = {
  "avatars": names.map(n => [n, resolve(light, light["--" + n])]),
  "stripes, day": names.map(n => [n, resolve(light, light["--" + n + "-mark"])]),
  "stripes, night": names.map(n => [n, resolve(dark, dark["--" + n + "-mark"])]),
};
const out = { contrast: rows, sets: {}, signals: [] };
for (const [k, list] of Object.entries(sets)) out.sets[k] = { closest: closest(list), perKind: perKind(list) };
// distance from late red and Vera's green (and from Everyone's grey), every vision
for (const [nm, T, key] of [["day", light, ""], ["night", dark, "-mark"], ["avatars", light, "@"]]) {
  for (const n of names) {
    const c = resolve(T, T["--" + n + (key === "@" ? "" : key || "-mark")]);
    const refs = { late: resolve(T, T["--alert"]), vera: resolve(T, T["--vera-bg"]), phosphor: resolve(T, T["--phosphor"]), everyone: resolve(T, T[key === "@" ? "--everyone" : "--everyone-mark"]) };
    for (const [rn, rv] of Object.entries(refs)) {
      let m = 1e9, mk = ""; for (const k of kinds.slice(1)) { const d = dE(c, rv, k); if (d < m) { m = d; mk = k; } }
      out.signals.push([nm, n, rn, dE(c, rv, "normal"), m, mk]);
    }
  }
}
if (json) { console.log(JSON.stringify(out, null, 1)); process.exit(fails ? 1 : 0); }
const f2 = x => typeof x === "number" ? x.toFixed(2) : x;
const failing = rows.filter(r => typeof r[3] === "number" && r[3] < r[4]);
console.log(`Contrast: ${rows.length} pairs, ${failing.length} below their floor.`);
for (const r of failing) console.log("  FAIL", r[0], r[1], "on", r[2], f2(r[3]), "<", r[4], "(" + r[5] + ")");
const lowest = (theme, pre, suf) => { const rs = rows.filter(r => r[0] === theme && new RegExp(pre).test(r[1]) && new RegExp(suf).test(r[2])); return rs.reduce((a, b) => (b[3] < a[3] ? b : a), rs[0]); };
for (const t of ["light", "dark"]) {
  console.log(`\n${t}: lowest avatar letter ${f2(lowest(t, "^--on-p$", "^--p\\d$")[3])} (${lowest(t, "^--on-p$", "^--p\\d$")[2]}),` +
    ` name on wash ${f2(lowest(t, "^--p\\d-ink$", "soft")[3])}, name on paper ${f2(lowest(t, "^--p\\d-ink$", "^--paper$")[3])},` +
    ` stripe on paper ${f2(lowest(t, "^--p\\d-mark$", "^--paper$")[3])} (${lowest(t, "^--p\\d-mark$", "^--paper$")[1]})`);
}
console.log("\nColour-blind (CIEDE2000 between the closest two people):");
for (const [k, v] of Object.entries(out.sets)) {
  console.log(`  ${k.padEnd(15)} closest ${v.closest.d.toFixed(1)} (${v.closest.a}/${v.closest.b}, ${v.closest.k})   ` +
    kinds.map(x => `${x} ${v.perKind[x].d.toFixed(1)} ${v.perKind[x].a}/${v.perKind[x].b}`).join(" · "));
}
const sig = out.signals.sort((a, b) => a[3] - b[3]);
console.log("\nNearest person to each signal (CIEDE2000; normal vision, then the worst simulation):");
for (const rn of ["late", "vera", "phosphor", "everyone"]) {
  const s = sig.find(x => x[2] === rn), c = out.signals.filter(x => x[2] === rn).sort((a, b) => a[4] - b[4])[0];
  console.log(`  ${rn.padEnd(9)} normal ${s[3].toFixed(1)} (${s[1]}, ${s[0]})   simulated ${c[4].toFixed(1)} (${c[1]}, ${c[0]}, ${c[5]})`);
}
console.log("\nAll pairs:");
for (const r of rows) console.log(`  ${r[0].padEnd(5)} ${(r[1] + " on " + r[2]).padEnd(34)} ${f2(r[3]).padStart(6)}  (${r[4]}:1) ${r[5]}`);
process.exit(fails ? 1 : 0);
