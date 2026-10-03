// Usage: node probe.js BASE CSS WIDTH PATH "js expression returning JSON-able"
const { chromium } = require("playwright");
const fs = require("fs");
const [base, cssPath, width, route, expr] = process.argv.slice(2);
const css = fs.readFileSync(cssPath, "utf8");
const STATIC = __dirname + "/../static";
const path = require("path");
(async () => {
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
  const w = parseInt(width, 10);
  const ctx = await b.newContext({ viewport: { width: w, height: w < 500 ? 844 : 900 }, deviceScaleFactor: 1, colorScheme: "dark" });
  await ctx.route("**/static/style.css*", (r) => r.fulfill({ status: 200, contentType: "text/css", body: css }));
  await ctx.route("**/static/*.svg*", (r) => { const f = STATIC + "/" + path.basename(new URL(r.request().url()).pathname); return fs.existsSync(f) ? r.fulfill({ status: 200, contentType: "image/svg+xml", body: fs.readFileSync(f) }) : r.fallback(); });
  const H = "/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness/fonts/extra";
  await ctx.route("**/static/fonts/extra/**", (r) => { const f = H + "/" + require("path").basename(new URL(r.request().url()).pathname); return fs.existsSync(f) ? r.fulfill({ status: 200, contentType: "font/woff2", body: fs.readFileSync(f) }) : r.fulfill({ status: 404, body: "" }); });
  const p = await ctx.newPage();
  await p.goto(base + "/login");
  await p.fill("#password", "palette-demo-pass");
  await Promise.all([p.waitForNavigation(), p.click("form button[type=submit]")]);
  await p.goto(base + route);
  await p.waitForLoadState("networkidle");
  await p.waitForTimeout(800);
  if (expr.startsWith("shot:")) { await p.screenshot({ path: expr.slice(5), fullPage: true }); console.log("shot", expr.slice(5)); }
  else { const out = await p.evaluate(expr); console.log(JSON.stringify(out, null, 1)); }
  await b.close();
})();
