// Rasterise every Lucide symbol of the page's sprite onto a coarse grid, for the mosaic icons.
// Usage: NODE_PATH=$(npm root -g) node raster.js GRID STROKE THRESH > grids.json
const { chromium } = require("playwright");
const fs = require("fs");
const sprite = fs.readFileSync("/home/user/FamilyDB/src/familydb/web/static/icons.svg", "utf8");
const GRID = +process.argv[2] || 12, STROKE = +process.argv[3] || 2.2, THRESH = +process.argv[4] || 0.3;
(async () => {
  const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
  const page = await browser.newPage();
  await page.setContent("<html><body></body></html>");
  const out = await page.evaluate(async ({ sprite, GRID, STROKE, THRESH }) => {
    const doc = new DOMParser().parseFromString(sprite, "image/svg+xml");
    const res = {};
    const S = 480; // raster size
    for (const sym of doc.querySelectorAll("symbol")) {
      const id = sym.getAttribute("id");
      const inner = sym.innerHTML;
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="${STROKE}" stroke-linecap="round" stroke-linejoin="round">${inner.replace(/currentColor/g, "#000")}</svg>`;
      const img = new Image();
      img.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(svg)));
      await img.decode();
      const c = document.createElement("canvas"); c.width = S; c.height = S;
      const ctx = c.getContext("2d"); ctx.drawImage(img, 0, 0);
      const data = ctx.getImageData(0, 0, S, S).data;
      const cell = S / GRID; const rows = [];
      for (let gy = 0; gy < GRID; gy++) {
        let row = "";
        for (let gx = 0; gx < GRID; gx++) {
          let on = 0, n = 0;
          for (let y = Math.floor(gy * cell); y < Math.floor((gy + 1) * cell); y++)
            for (let x = Math.floor(gx * cell); x < Math.floor((gx + 1) * cell); x++) { on += data[(y * S + x) * 4 + 3] / 255; n++; }
          row += on / n >= THRESH ? "#" : ".";
        }
        rows.push(row);
      }
      res[id] = rows;
    }
    return res;
  }, { sprite, GRID, STROKE, THRESH });
  console.log(JSON.stringify(out, null, 1));
  await browser.close();
})();
