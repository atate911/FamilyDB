// node _kit/palette.js check
// Measures, from the tokens in _kit/palette.js, every contrast floor in both themes (WCAG AA 4.5:1
// for text, 3:1 for controls, stripes and plates) and how far apart the eight people stay under
// simulated colour-blindness (Machado 2009, CIEDE2000). Exits non-zero if a floor fails.
const K = require("./colour.js");
const { tokens, peopleFor } = require("./palette.js");

function pairs(T, night) {
  const P = peopleFor(night), out = [];
  const add = (floor, fg, bg, what) => out.push({ floor, fg, bg, what, a: T[fg] || fg, b: T[bg] || bg });
  for (const bg of ["--paper", "--paper-2", "--card", "--field"]) for (const fg of ["--ink", "--ink-2", "--ink-3"]) add(4.5, fg, bg, "text");
  for (const bg of ["--band", "--band-hi"]) for (const fg of ["--on-band", "--on-band-2"]) add(4.5, fg, bg, "panel text");
  add(4.5, "--band", "--on-band", "you-are-here plate");
  for (const s of ["ok", "warn", "alert"]) { add(4.5, `--${s}`, "--paper", s); add(4.5, `--${s}`, `--${s}-soft`, s + " on its panel"); add(4.5, "--ink", `--${s}-soft`, "ink on " + s + " panel"); }
  add(4.5, "--vera", "--paper", "Vera's green text"); add(4.5, "--vera", "--vera-soft", "ready pill");
  add(4.5, "--on-vera", "--vera-bg", "done stamp"); add(4.5, "--on-today", "--today-bg", "today stamp");
  add(4.5, "--on-alert-plate", "--alert-plate", "late plate text");
  add(4.5, "--on-primary", "--primary", "primary button"); add(4.5, "--link", "--paper", "link");
  add(4.5, "--ask-ink", "--ask-bg", "Ask head"); add(4.5, "--ask-ink-2", "--ask-bg", "Ask note"); add(4.5, "--on-send", "--send", "Send");
  add(4.5, "--glass-ink", "--glass", "glass"); add(4.5, "--glass-ink-2", "--glass", "glass"); add(4.5, "--phosphor", "--glass", "phosphor line"); add(4.5, "--glass-alert", "--glass", "glass alert");
  add(4.5, "--everyone-ink", "--everyone", "Everyone icon"); add(4.5, "--everyone-ink", "--everyone-soft", "Everyone name");
  for (const bg of ["--paper", "--card", "--field"]) add(3, "--edge", bg, "control edge");
  for (const bg of ["--paper", "--paper-2"]) add(3, "--focus", bg, "focus ring");
  add(3, "--today-bg", "--paper", "today stamp edge"); add(3, "--vera-bg", "--paper", "done tick");
  add(3, "--everyone-mark", "--paper", "Everyone stripe"); add(3, "--send", "--ask-bg", "Send on glass");
  add(3, "--phosphor", "--band", "focus on panel");
  for (const p of P) {
    add(4.5, "--on-p", p.base, `${p.slot} avatar letter`);
    add(4.5, p.ink, "--paper", `${p.slot} name`); add(4.5, p.ink, p.soft, `${p.slot} name on wash`); add(4.5, "--ink", p.soft, `${p.slot} wash text`);
    add(3, p.mark, "--paper", `${p.slot} stripe`); add(3, p.mark, "--card", `${p.slot} stripe on card`); add(3, p.mark, p.soft, `${p.slot} rule on wash`);
    if (night) add(3, p.base, "--band", `${p.slot} kid's edge on panel`);
  }
  return out;
}

function cvd(list) {
  const res = {};
  for (const k of K.KINDS) { let best = { d: 1e9 };
    for (let i = 0; i < list.length; i++) for (let j = i + 1; j < list.length; j++) { const d = K.de(list[i].hex, list[j].hex, k); if (d < best.d) best = { d, a: list[i].label, b: list[j].label }; }
    res[k] = best; }
  return res;
}
const fmt = r => K.KINDS.map(k => `${k.slice(0, 5)} ${r[k].d.toFixed(1)} (${r[k].a}/${r[k].b})`).join(" · ");

function run() {
  let fails = 0, n = 0, weakest = {};
  for (const night of [true, false]) {
    const T = tokens(night), name = night ? "night" : "day";
    for (const p of pairs(T, night)) { n++; const c = K.contrast(p.a, p.b); if (c < p.floor) { fails++; console.log(`FAIL ${name} ${p.what}: ${p.fg} on ${p.bg} ${c.toFixed(2)} < ${p.floor}`); }
      if (/avatar letter/.test(p.what) && (!weakest[name] || c < weakest[name].c)) weakest[name] = { c, what: p.what }; }
  }
  console.log(`${n} contrast pairs, ${fails} below the floor. Weakest avatar letter: night ${weakest.night.c.toFixed(2)} (${weakest.night.what}), day ${weakest.day.c.toFixed(2)} (${weakest.day.what}).`);
  const N = peopleFor(true), D = peopleFor(false);
  const av = N.map(p => ({ hex: p.base, label: p.name }));
  console.log("\nClosest pair under each vision (CIEDE2000; under about 8 two colours can be confused alone):");
  console.log("avatars (both themes):  " + fmt(cvd(av)));
  console.log("stripes at night:       " + fmt(cvd(N.map(p => ({ hex: p.mark, label: p.name })))));
  console.log("stripes by day:         " + fmt(cvd(D.map(p => ({ hex: p.mark, label: p.name })))));
  console.log("the family's four:      " + fmt(cvd(av.slice(0, 4))));
  const T = tokens(true), Td = tokens(false);
  console.log("\nNearest person to each signal (normal / worst simulated):");
  for (const [label, hexN, hexD] of [["late red", T["--alert"], Td["--alert"]], ["Vera green", T["--vera"], Td["--vera-bg"]], ["set-up amber", T["--warn"], Td["--warn"]]]) {
    for (const [th, hex, P, key] of [["night", hexN, N, "mark"], ["day", hexD, D, "mark"]]) {
      let nm = { d: 1e9 }, ws = { d: 1e9 };
      for (const p of P) { const d0 = K.de(p[key], hex); if (d0 < nm.d) nm = { d: d0, p: p.name }; for (const k of K.KINDS.slice(1)) { const d = K.de(p[key], hex, k); if (d < ws.d) ws = { d, p: p.name, k }; } }
      console.log(`  ${label.padEnd(13)} ${th.padEnd(5)} ${nm.d.toFixed(1)} (${nm.p}) / ${ws.d.toFixed(1)} (${ws.p}, ${ws.k})`);
    }
  }
  console.log("\nTwo dark blocks side by side (panel and Vera's glass): night contrast " + K.contrast(T["--band"], T["--ask-bg"]).toFixed(2) + ", ΔE " + K.de(T["--band"], T["--ask-bg"]).toFixed(1) +
    "; day " + K.contrast(Td["--band"], Td["--ask-bg"]).toFixed(2) + ", ΔE " + K.de(Td["--band"], Td["--ask-bg"]).toFixed(1));
  console.log("Panel against page: night " + K.contrast(T["--band"], T["--paper"]).toFixed(2) + ":1, day " + K.contrast(Td["--band"], Td["--paper"]).toFixed(2) + ":1. Late plate against panel: night " + K.contrast(T["--alert-plate"], T["--band"]).toFixed(2) + ", day " + K.contrast(Td["--alert-plate"], Td["--band"]).toFixed(2));
  if (fails) process.exitCode = 1;
}
module.exports = { run, pairs, cvd };
