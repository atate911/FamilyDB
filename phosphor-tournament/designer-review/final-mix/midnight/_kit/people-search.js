// node _kit/people-search.js [rounds]
// The search that proposed Midnight's eight people. Each person has a hue window, a luminous night
// colour (the avatar in both themes, and the night stripe) and a deeper day stripe of the same hue.
// It maximises the smallest CIEDE2000 distance between any two people under normal vision and
// simulated protanopia, deuteranopia and tritanopia (Machado 2009), for avatars and for the stripes
// of both themes, while keeping every person clear of late red, set-up amber and Vera's green,
// avatar letters AA and day stripes 3:1 on paper. The values in _kit/palette.js were tuned from its output.
const K = require("./colour.js");
const LETTER = "#0B1020", DAYPAPER = "#EEF1F7";
const SIG = [["#FF7369", 20, 6], ["#B42318", 20, 6], ["#6DFF9C", 22, 5], ["#0B8457", 18, 5], ["#F6B04A", 11, 0], ["#8A4B00", 11, 0]]; // colour, normal floor, simulated floor
// blue, iris, lagoon, wheat/marigold, heather, harbour, apricot, lichen
const WIN = [[250, 266], [282, 298], [182, 198], [72, 92], [304, 320], [218, 236], [50, 64], [104, 120]];
const NL = [0.68, 0.86], NC = [0.08, 0.15], DL = [0.45, 0.62], DC = [0.08, 0.15];
const clamp = (v, [a, b]) => Math.min(b, Math.max(a, v));
function make(i, nL, nC, nH, dL, dC) {
  if (nH < WIN[i][0] || nH > WIN[i][1]) return null;
  if (i === 4 && dC > 0.1) return null; // heather never turns magenta by day
  const n = K.oklch2hex(nL, nC, nH), d = K.oklch2hex(dL, dC, nH);
  if (!n.inGamut || !d.inGamut) return null;
  if (K.contrast(n.hex, LETTER) < 5.5 || K.contrast(d.hex, DAYPAPER) < 3.4 || K.contrast(d.hex, "#FFFFFF") < 3.4) return null;
  return { i, nL, nC, nH, dL, dC, night: n.hex, day: d.hex };
}
function rnd(i) { for (;;) { const r = (x) => x[0] + Math.random() * (x[1] - x[0]); const p = make(i, r(NL), r(NC), r(WIN[i]), r(DL), r(DC)); if (p) return p; } }
function minPair(set, key) { let m = 99; for (const k of K.KINDS) for (let i = 0; i < set.length; i++) for (let j = i + 1; j < set.length; j++) m = Math.min(m, K.de(set[i][key], set[j][key], k)); return m; }
function score(set) {
  let pen = 0;
  for (const s of set) for (const key of ["night", "day"]) for (const [hex, fn, fs] of SIG) {
    const d = K.de(s[key], hex); if (d < fn) pen += fn - d;
    if (fs) for (const k of K.KINDS.slice(1)) { const e = K.de(s[key], hex, k); if (e < fs) pen += (fs - e) * 0.5; }
  }
  return Math.min(minPair(set, "night"), minPair(set, "day") + 1) - pen;
}
const rounds = +process.argv[2] || 16;
let best = null, bs = -1e9;
for (let r = 0; r < rounds; r++) {
  const set = WIN.map((_, i) => rnd(i)); let sc = score(set);
  for (let it = 0; it < 5000; it++) {
    const i = Math.floor(Math.random() * 8), o = set[i], j = () => (Math.random() - .5);
    const p = make(i, clamp(o.nL + j() * .04, NL), clamp(o.nC + j() * .02, NC), o.nH + j() * 5, clamp(o.dL + j() * .04, DL), clamp(o.dC + j() * .02, DC));
    if (!p) continue; set[i] = p; const s2 = score(set); if (s2 >= sc) sc = s2; else set[i] = o;
  }
  if (sc > bs) { bs = sc; best = set.map(x => ({ ...x })); }
}
console.log("score", bs.toFixed(2), "night min", minPair(best, "night").toFixed(2), "day min", minPair(best, "day").toFixed(2));
for (const s of best) console.log(s.night, s.day, `H ${s.nH.toFixed(0)}  night L ${s.nL.toFixed(2)} C ${s.nC.toFixed(3)}  day L ${s.dL.toFixed(2)} C ${s.dC.toFixed(3)}`);
module.exports = { score, minPair };
