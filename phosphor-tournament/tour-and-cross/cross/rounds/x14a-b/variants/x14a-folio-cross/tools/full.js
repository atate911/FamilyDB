// Full-page shots of chosen pages for inspection: node full.js BASE CSS OUTDIR width path...
const { chromium } = require("playwright");
const fs = require("fs"); const path = require("path");
const [BASE, CSS, OUT, W, ...paths] = process.argv.slice(2);
const css = fs.readFileSync(CSS, "utf8");
const STATIC = path.resolve(__dirname, "../static");
const FONTS = "/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness/fonts/extra";
(async () => {
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium", ignoreDefaultArgs: ["--hide-scrollbars"] });
  const phone = +W < 500;
  const ctx = await b.newContext({ viewport: { width: +W, height: phone ? 844 : 900 }, deviceScaleFactor: phone ? 2 : 1, colorScheme: "dark" });
  await ctx.route("**/static/style.css*", r => r.fulfill({ status: 200, contentType: "text/css", body: css }));
  await ctx.route("**/static/**", r => {
    const rel = new URL(r.request().url()).pathname.replace(/^\/static\//, "");
    const f = path.join(STATIC, rel);
    if (fs.existsSync(f) && fs.statSync(f).isFile()) return r.fulfill({ status: 200, contentType: rel.endsWith(".svg") ? "image/svg+xml" : "image/png", body: fs.readFileSync(f) });
    return r.fallback();
  });
  await ctx.route("**/static/fonts/extra/**", r => { const f = path.join(FONTS, path.basename(new URL(r.request().url()).pathname)); return fs.existsSync(f) ? r.fulfill({ status: 200, contentType: "font/woff2", body: fs.readFileSync(f) }) : r.fulfill({ status: 404, body: "" }); });
  const p = await ctx.newPage();
  await p.goto(BASE + "/login"); await p.fill("#password", "palette-demo-pass");
  await Promise.all([p.waitForNavigation(), p.click("form button[type=submit]")]);
  for (const u of paths) {
    await p.goto(BASE + u); await p.waitForLoadState("networkidle"); await p.waitForTimeout(1500);
    const name = u.replace(/[^a-z0-9]+/gi, "_").replace(/^_|_$/g, "") || "home";
    await p.screenshot({ path: path.join(OUT, `${name}-${W}.png`), fullPage: true });
  }
  await b.close();
})();
