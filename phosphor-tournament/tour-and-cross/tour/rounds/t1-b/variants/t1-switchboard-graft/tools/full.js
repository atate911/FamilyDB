// Usage: node full.js BASE CSS OUTDIR WIDTH path...  full-page shots at a width
const { chromium } = require("playwright");
const fs = require("fs"); const path = require("path");
const [BASE, CSS, OUT, W, ...paths] = process.argv.slice(2);
const css = fs.readFileSync(CSS, "utf8");
const STATIC = path.resolve(__dirname, "../static");
const FONTS = "/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness/fonts/extra";
fs.mkdirSync(OUT, { recursive: true });
(async () => {
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
  const ctx = await b.newContext({ viewport: { width: +W, height: 900 }, colorScheme: "dark", deviceScaleFactor: +W < 500 ? 2 : 1 });
  await ctx.route("**/static/style.css*", r => r.fulfill({ status: 200, contentType: "text/css", body: css }));
  await ctx.route("**/static/fonts/extra/**", r => { const f = path.join(FONTS, path.basename(new URL(r.request().url()).pathname)); return fs.existsSync(f) ? r.fulfill({ status: 200, contentType: "font/woff2", body: fs.readFileSync(f) }) : r.fulfill({ status: 404, body: "" }); });
  await ctx.route("**/static/icons.svg*", r => r.fulfill({ status: 200, contentType: "image/svg+xml", body: fs.readFileSync(path.join(STATIC, "icons.svg")) }));
  const p = await ctx.newPage();
  await p.goto(BASE + "/login"); await p.fill("#password", "palette-demo-pass");
  await Promise.all([p.waitForNavigation(), p.click("form button[type=submit]")]);
  for (const u of paths) {
    await p.goto(BASE + u); await p.waitForLoadState("networkidle"); await p.waitForTimeout(1500);
    const name = (u.replace(/[^a-z0-9]+/gi, "_") || "root") + "-" + W + ".png";
    await p.screenshot({ path: path.join(OUT, name), fullPage: true });
    console.log(name);
  }
  await b.close();
})();
