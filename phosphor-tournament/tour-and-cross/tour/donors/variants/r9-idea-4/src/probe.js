// Probe: node probe.js BASE CSSFILE OUTDIR spec.json
// spec: [{url, name, width, measure:[selectors], shot:true, full:false, clip:{x,y,width,height}}]
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const [BASE, CSS, OUT, SPEC] = process.argv.slice(2);
const css = fs.readFileSync(CSS, "utf8");
const spec = JSON.parse(fs.readFileSync(SPEC, "utf8"));
const FONTS = "/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness/fonts/extra";
fs.mkdirSync(OUT, { recursive: true });
(async () => {
  const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium", ignoreDefaultArgs: ["--hide-scrollbars"] });
  const out = {};
  for (const width of [...new Set(spec.map((s) => s.width || 1280))]) {
    const phone = width < 600;
    const context = await browser.newContext({ viewport: { width, height: phone ? 844 : 900 }, deviceScaleFactor: phone ? 2 : 1, colorScheme: "dark" });
    await context.route("**/static/style.css*", (r) => r.fulfill({ status: 200, contentType: "text/css; charset=utf-8", body: css }));
    await context.route("**/static/fonts/extra/**", (r) => {
      const f = path.join(FONTS, path.basename(new URL(r.request().url()).pathname));
      if (!fs.existsSync(f)) return r.fulfill({ status: 404, body: "" });
      return r.fulfill({ status: 200, contentType: "font/woff2", body: fs.readFileSync(f) });
    });
    const page = await context.newPage();
    await page.goto(BASE + "/login");
    await page.fill("#password", "palette-demo-pass");
    await Promise.all([page.waitForNavigation(), page.click("form button[type=submit]")]);
    for (const s of spec.filter((x) => (x.width || 1280) === width)) {
      await page.goto(BASE + s.url);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(1200);
      const m = {};
      for (const sel of s.measure || []) {
        m[sel] = await page.$$eval(sel, (els) => els.slice(0, 6).map((e) => { const b = e.getBoundingClientRect(); return [Math.round(b.x), Math.round(b.y + scrollY), Math.round(b.width), Math.round(b.height)]; }));
      }
      out[s.name] = m;
      if (s.shot) await page.screenshot({ path: path.join(OUT, s.name + ".png"), fullPage: !!s.full, clip: s.clip });
    }
    await context.close();
  }
  await browser.close();
  console.log(JSON.stringify(out, null, 0));
})();
