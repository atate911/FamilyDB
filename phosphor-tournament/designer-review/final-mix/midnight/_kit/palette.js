// Midnight: the one source of FamilyDB's colour.
//   node _kit/palette.js build   writes the colour tokens into style.css (between the palette markers)
//   node _kit/palette.js check   measures every contrast floor and the colour-blind distances
//   node _kit/palette.js sheet   writes palette.html from these values
// Night is designed first and is the default on :root. Day is the same kitchen with the lights on.
const fs = require("fs"), path = require("path");
const K = require("./colour.js");
const ROOT = path.resolve(__dirname, "..");

// ---------- the eight people: one luminous night colour each (the avatar, in both themes) ----------
// Picked by _kit/people-search.js inside eight hue windows, then tuned by eye. Night: the avatar is
// also the stripe, and glows a little. Day: the avatar stays; stripe (-mark) and name (-ink) are the
// a deeper colour of the same hue, from the same search; names (-ink) are that, taken down to AA.
const PEOPLE = [
  { slot: "p1", who: "Sam", name: "moon blue", night: "#96B5FB", day: "#607FCA" },
  { slot: "p2", who: "Alex", name: "iris", night: "#958DF5", day: "#5144A0" },
  { slot: "p3", who: "Maya", name: "lagoon", night: "#69BAB8", day: "#016868" },
  { slot: "p4", who: "Theo", name: "apricot", night: "#ECB489", day: "#B17443" },
  { slot: "p5", who: "", name: "heather", night: "#A78BC2", day: "#614978" },
  { slot: "p6", who: "", name: "sky", night: "#95DAF8", day: "#277895" },
  { slot: "p7", who: "", name: "ochre", night: "#C6950A", day: "#936E09" },
  { slot: "p8", who: "", name: "sage", night: "#93A066", day: "#586328" },
];

// ---------- night (the default) ----------
const NIGHT = {
  // the page: a blue-black kitchen at night; wells a step up, fields a step down
  "--paper": "#0B1020", "--paper-2": "#161D30", "--card": "#121A2B", "--field": "#0E1526",
  "--ink": "#E3E8F3", "--ink-2": "#B7C0D5", "--ink-3": "#939DB6",
  "--line": "#262F47", "--line-2": "#36405C", "--rule": "#E3E8F3", "--edge": "#7884A3",
  // the panel: darker than the page, with a hairline where they meet
  "--band": "#04060D", "--on-band": "#EEF1F8", "--on-band-2": "#A6B0C8", "--band-line": "#1C2338", "--band-hi": "#121829", "--band-edge": "#1F2840",
  "--vera": "#6DFF9C", "--vera-bg": "#4FE08A", "--vera-bg-2": "#6DFF9C", "--on-vera": "#0B1020",
  "--vera-soft": "#0C2219", "--vera-line": "#1F4D38",
  // Vera's glass stays green-black, so it never reads as midnight blue
  "--ask-bg": "#07130F", "--ask-ink": "#EAF2EE", "--ask-ink-2": "#BCD0C5",
  "--ask-rim": "inset 0 0 0 1.5px #3E8A66, inset 0 0 28px rgba(109, 255, 156, .08)", "--ask-edge": "#6F8C7E",
  "--send": "#6DFF9C", "--send-2": "#95FFB8", "--on-send": "#07130F",
  "--ask-ring": "rgba(109, 255, 156, .16)",
  "--ok": "#7FE3A5", "--ok-soft": "#0D2218", "--ok-line": "#24503A",
  "--warn": "#F6B04A", "--warn-soft": "#231A0B", "--warn-line": "#5C4420",
  "--alert": "#FF7369", "--alert-soft": "#2B1117", "--alert-line": "#5E2830",
  "--alert-plate": "#C9302C", "--on-alert-plate": "#FFFFFF",
  "--focus": "#9DB9FF",
  "--on-p": "#0B1020",
  "--everyone": "#454E69", "--everyone-soft": "#1A2133", "--everyone-ink": "#CFD5E3", "--everyone-mark": "#8590AD",
  "--today-bg": "#6DFF9C", "--on-today": "#0B1020", "--today-wash": "#0E2219",
  "--link": "#E3E8F3", "--link-line": "#7C95D6", "--primary": "#E3E8F3", "--primary-2": "#FFFFFF", "--on-primary": "#0B1020",
  "--glass": "#050B09", "--glass-2": "#0C1512", "--glass-line": "#24382F", "--glass-ink": "#E9F1EC", "--glass-ink-2": "#B9C6BF",
  "--glass-alert": "#FF8B74", "--phosphor": "#6DFF9C", "--phosphor-dim": "rgba(109, 255, 156, .34)", "--phosphor-glow": "rgba(109, 255, 156, .5)",
  "--cursor": "#6DFF9C", "--cursor-glow": "rgba(109, 255, 156, .55)", "--vs-halo": "rgba(109, 255, 156, .45)",
  // people glow gently at night: the spread of the halo round an avatar
  "--glow": "9px",
};

// ---------- day: the same kitchen with the lights on ----------
const DAY = {
  "--paper": "#EEF1F7", "--paper-2": "#E0E4EE", "--card": "#FFFFFF", "--field": "#FFFFFF",
  "--ink": "#0B1020", "--ink-2": "#353D52", "--ink-3": "#4E576D",
  "--line": "#C4CAD8", "--line-2": "#A8B0C3", "--rule": "#0B1020", "--edge": "#6C7489",
  // the panel stays midnight by day: the night the page sits beside
  "--band": "#0A0F1E", "--on-band": "#FFFFFF", "--on-band-2": "#AEB7CC", "--band-line": "#222A42", "--band-hi": "#182036", "--band-edge": "#0A0F1E",
  "--vera": "#0A6A4B", "--vera-bg": "#0B8457", "--vera-bg-2": "#08623F", "--on-vera": "#FFFFFF",
  "--vera-soft": "#DCF0E5", "--vera-line": "#A6D6BD",
  "--ask-bg": "#0E1312", "--ask-ink": "#FFFFFF", "--ask-ink-2": "#C4CEC9",
  "--ask-rim": "inset 0 0 0 1px rgba(255, 255, 255, .08)", "--ask-edge": "transparent",
  "--send": "#6DFF9C", "--send-2": "#95FFB8", "--on-send": "#0E1312",
  "--ask-ring": "rgba(109, 255, 156, .28)",
  "--ok": "#17703F", "--ok-soft": "#DDF1E4", "--ok-line": "#A9D9BA",
  "--warn": "#8A4B00", "--warn-soft": "#FBEBCD", "--warn-line": "#E3BD78",
  "--alert": "#B42318", "--alert-soft": "#FBE6E3", "--alert-line": "#EDB9B3",
  "--alert-plate": "#C9302C", "--on-alert-plate": "#FFFFFF",
  "--focus": "#2D4FC4",
  "--on-p": "#0B1020",
  "--everyone": "#CDD2DE", "--everyone-soft": "#E3E7EF", "--everyone-ink": "#353D52", "--everyone-mark": "#6C7489",
  "--today-bg": "#0B8457", "--on-today": "#FFFFFF", "--today-wash": "#E1F2E8",
  "--link": "#0B1020", "--link-line": "#7F8FB8", "--primary": "#0B1020", "--primary-2": "#252E48", "--on-primary": "#FFFFFF",
  "--glass": "#0E1312", "--glass-2": "#161D1B", "--glass-line": "#2A3632", "--glass-ink": "#E9F1EC", "--glass-ink-2": "#B9C6BF",
  "--glass-alert": "#FF8B74", "--phosphor": "#6DFF9C", "--phosphor-dim": "rgba(109, 255, 156, .34)", "--phosphor-glow": "rgba(109, 255, 156, .5)",
  "--cursor": "#12945A", "--cursor-glow": "rgba(18, 148, 90, .35)", "--vs-halo": "rgba(18, 148, 90, .35)",
  "--glow": "0px",
};

// ---------- deriving each person's four colours per theme ----------
const setL = (hex, L) => { const [, C, H] = K.hex2oklch(hex); for (let c = C; c >= 0; c -= 0.002) { const o = K.oklch2hex(L, c, H); if (o.inGamut) return o.hex; } return K.oklch2hex(L, 0, H).hex; };
// walk lightness in a direction until fn(hex) holds
const walk = (hex, dir, fn) => { let [L] = K.hex2oklch(hex); for (let i = 0; i < 200; i++) { const h = setL(hex, L); if (fn(h)) return h; L += dir * 0.004; } throw new Error("no value for " + hex); };
function person(p, T, night) {
  const base = p.night;
  if (night) {
    const soft = K.oklch2hex(0.255, 0.035, K.hex2oklch(base)[2]).hex;
    const mark = base;
    const ink = walk(setL(base, Math.max(K.hex2oklch(base)[0], 0.84)), 1, h => K.contrast(h, soft) >= 7 && K.contrast(h, T["--paper"]) >= 7);
    return { base, soft, ink, mark };
  }
  const [, , H] = K.hex2oklch(base);
  const soft = K.oklch2hex(0.945, 0.028, H).hex;
  const mark = p.day;
  const ink = walk(mark, -1, h => K.contrast(h, soft) >= 5.2 && K.contrast(h, T["--paper"]) >= 5.2);
  return { base, soft, ink, mark };
}
const peopleFor = night => PEOPLE.map(p => ({ ...p, ...person(p, night ? NIGHT : DAY, night) }));

function tokens(night) {
  const T = { ...(night ? NIGHT : DAY) };
  for (const p of peopleFor(night)) { T["--" + p.slot] = p.base; T[`--${p.slot}-soft`] = p.soft; T[`--${p.slot}-ink`] = p.ink; T[`--${p.slot}-mark`] = p.mark; }
  return T;
}

// ---------- CSS ----------
const GROUPS = [
  ["the page: paper, ink, rules and control edges", /^--(paper|paper-2|card|field|ink|ink-2|ink-3|line|line-2|rule|edge)$/],
  ["the panel down the left (and the phone's top bar)", /^--(band|on-band|on-band-2|band-line|band-hi|band-edge)$/],
  ["Vera and today: her green", /^--(vera|vera-bg|vera-bg-2|on-vera|vera-soft|vera-line|today-bg|on-today|today-wash)$/],
  ["the Ask block: Vera's glass with its phosphor Send", /^--(ask-|send|on-send)/],
  ["signals: done, set this up, late (the only red), focus", /^--(ok|warn|alert|on-alert|focus)/],
  ["the eight people: avatar (under --on-p letters), -soft wash, -ink names, -mark stripes and rules; slot 0 is Everyone", /^--(on-p|p\d|everyone|glow$)/],
  ["the family's actions: links and the one primary button", /^--(link|primary|on-primary)/],
  ["the brand: phosphor on dark glass", /^--(glass|phosphor|cursor|vs-halo)/],
];
function block(T, indent) {
  const out = [], used = new Set();
  for (const [title, re] of GROUPS) {
    const keys = Object.keys(T).filter(k => re.test(k) && !used.has(k)); if (!keys.length) continue;
    keys.forEach(k => used.add(k)); out.push(`${indent}/* ${title} */`);
    let line = indent;
    for (const k of keys) { const piece = `${k}: ${T[k]};`; if (line.length + piece.length > 112 && line.trim()) { out.push(line.replace(/\s+$/, "")); line = indent; } line += piece + "  "; }
    out.push(line.replace(/\s+$/, ""));
  }
  const rest = Object.keys(T).filter(k => !used.has(k)); if (rest.length) throw new Error("ungrouped " + rest);
  return out.join("\n");
}
function css() {
  const N = tokens(true), D = tokens(false);
  return `/* palette:begin (written by _kit/palette.js build: edit the values there, not here) */
/* Midnight. Night comes first: a blue-black kitchen at night, a darker panel, soft-white ink,
   the family's colours lit like windows and Vera's green glass at home among them.
   It is the default; day applies when the device asks for light, or with data-theme="light". */
:root, [data-theme="dark"] {
  color-scheme: dark;
${block(N, "  ")}
}
/* Day: the same kitchen with the lights on. A cool moonstone page and midnight ink; the panel stays midnight. */
@media (prefers-color-scheme: light) {
  :root:not([data-theme="dark"]) {
    color-scheme: light;
${block(D, "    ")}
  }
}
/* data-theme on <html> overrides the device; on any element it themes that block (the palette sheet shows both) */
[data-theme="light"] {
  color-scheme: light;
${block(D, "  ")}
}
/* swatches for palette.html, one per colour token */
${Object.keys(N).filter(k => /^#|^rgba/.test(N[k])).map(k => `.t${k.slice(1)} { --sw: var(${k}); }`).join("\n")}
/* palette:end */`;
}
function build() {
  const f = path.join(ROOT, "style.css"); let s = fs.readFileSync(f, "utf8");
  const a = s.indexOf("/* palette:begin"), b = s.indexOf("/* palette:end */");
  if (a < 0 || b < 0) throw new Error("palette markers missing in style.css");
  s = s.slice(0, a) + css() + s.slice(b + "/* palette:end */".length);
  fs.writeFileSync(f, s); console.log("style.css: palette written");
}

module.exports = { PEOPLE, NIGHT, DAY, tokens, peopleFor };
if (require.main === module) {
  const cmd = process.argv[2];
  if (cmd === "build") build();
  else if (cmd === "check") require("./palette-check.js").run();
  else if (cmd === "sheet") require("./palette-sheet.js").run();
  else if (cmd === "print") { for (const n of [true, false]) { console.log(n ? "NIGHT" : "DAY"); for (const p of peopleFor(n)) console.log(p.slot, p.name.padEnd(10), p.base, p.soft, p.ink, p.mark); } }
  else console.log("usage: node _kit/palette.js build | check | sheet | print");
}
