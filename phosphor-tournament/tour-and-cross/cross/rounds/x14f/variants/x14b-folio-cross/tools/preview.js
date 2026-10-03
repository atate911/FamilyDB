const { chromium } = require("playwright");
const fs = require("fs");
const sprite = fs.readFileSync("../static/icons.svg", "utf8");
const ids = [...sprite.matchAll(/<symbol id="i-([^"]+)"/g)].map(m => m[1]);
const cell = (id) => `<div class=c><svg width=24 height=24><use href="#i-${id}"/></svg><svg width=18 height=18><use href="#i-${id}"/></svg><svg width=64 height=64><use href="#m-${id}"/></svg><span>${id}</span></div>`;
const html = `<html><body style="background:#0a0d0b;color:#e8e6d8;font:11px monospace;margin:10px">${sprite.replace('<svg ', '<svg style="display:none" ')}<div style="display:grid;grid-template-columns:repeat(9,1fr);gap:8px">${ids.map(cell).join("")}</div><style>.c{display:flex;flex-direction:column;align-items:center;gap:4px}.c svg:nth-child(3){color:#6dff9c}</style></body></html>`;
(async () => {
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
  const p = await b.newPage({ viewport: { width: 1000, height: 900 } });
  await p.setContent(html);
  await p.screenshot({ path: "preview.png", fullPage: true });
  await b.close();
})();
