const { chromium } = require("playwright");
const fs = require("fs");
const H = "/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness";
const ff = fs.readFileSync(H + "/fonts/extra.css", "utf8").replace(/url\(fonts\//g, "url(file://" + H + "/fonts/");
const faces = [
  ["Fraunces 144 w300", "font-family:Fraunces;font-variation-settings:'opsz' 144,'SOFT' 50,'WONK' 0;font-weight:300"],
  ["Fraunces 144 w600 soft100", "font-family:Fraunces;font-variation-settings:'opsz' 144,'SOFT' 100,'WONK' 1;font-weight:600"],
  ["Newsreader 72 w400", "font-family:Newsreader;font-variation-settings:'opsz' 72;font-weight:400"],
  ["Source Serif 4 60 w600", "font-family:'Source Serif 4';font-variation-settings:'opsz' 60;font-weight:600"],
  ["Archivo wide 125 w700", "font-family:Archivo;font-stretch:125%;font-weight:700"],
  ["Archivo 62 w800", "font-family:Archivo;font-stretch:62%;font-weight:800"],
  ["Bricolage 96 w700 wdth75", "font-family:'Bricolage Grotesque';font-variation-settings:'opsz' 96,'wdth' 75;font-weight:700"],
  ["Barlow Condensed 600", "font-family:'Barlow Condensed';font-weight:600"],
];
const row = ([n, s]) => `<div class=r><div class=n>${n}</div><div style="${s}" class=t>Things to do <span class=big>29</span> <span class=big g>12</span> <span class=big i>SAMT</span> <span class=big>991</span></div><div style="${s}" class=h>Where home is · Coming up · $1.26</div></div>`;
const html = `<html><head><style>${ff} body{background:#0a0d0c;color:#eceee8;margin:16px;font:14px sans-serif}.r{border-bottom:1px solid #232a26;padding:6px 0}.n{color:#9ca69f;font:11px monospace}.t{font-size:46px;line-height:1.1}.big{font-size:96px;line-height:0.9;color:#bc97e8;margin-left:12px}.big[g]{color:#9ccdf8}.big[i]{color:#eaa76b}.h{font-size:23px;color:#eceee8}</style></head><body>${faces.map(row).join("")}</body></html>`;
(async () => {
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
  const p = await b.newPage({ viewport: { width: 1300, height: 900 } });
  fs.writeFileSync(__dirname + "/faces.html", html); await p.goto("file://" + __dirname + "/faces.html"); await p.waitForTimeout(1200);
  await p.screenshot({ path: "crops/faces.png", fullPage: true });
  await b.close();
})();
