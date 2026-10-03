// Usage: node probe.js BASE CSS WIDTH PATH "js expression returning JSON-able"
const { chromium } = require("playwright");
const fs = require("fs"); const path = require("path");
const [BASE, CSS, W, U, EXPR] = process.argv.slice(2);
const css = fs.readFileSync(CSS, "utf8");
const STATIC = path.resolve(__dirname, "../static");
const FONTS = "/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness/fonts/extra";
(async () => {
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
  const ctx = await b.newContext({ viewport: { width: +W, height: 900 }, colorScheme: "dark" });
  await ctx.route("**/static/style.css*", r => r.fulfill({ status: 200, contentType: "text/css", body: css }));
  await ctx.route("**/static/fonts/extra/**", r => { const f = path.join(FONTS, path.basename(new URL(r.request().url()).pathname)); return fs.existsSync(f) ? r.fulfill({ status: 200, contentType: "font/woff2", body: fs.readFileSync(f) }) : r.fulfill({ status: 404, body: "" }); });
  await ctx.route("**/static/icons.svg*", r => r.fulfill({ status: 200, contentType: "image/svg+xml", body: fs.readFileSync(path.join(STATIC, "icons.svg")) }));
  const p = await ctx.newPage();
  await p.goto(BASE + "/login"); await p.fill("#password", "palette-demo-pass");
  await Promise.all([p.waitForNavigation(), p.click("form button[type=submit]")]);
  await p.goto(BASE + U); await p.waitForLoadState("networkidle"); await p.waitForTimeout(600);
  const r = await p.evaluate(EXPR);
  console.log(JSON.stringify(r, null, 1));
  await b.close();
})();
