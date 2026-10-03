// Usage: node shots.js BASE CSS OUTDIR "w|route|name[|full][|hover-selector][|js]" ...
const { chromium } = require("playwright");
const fs = require("fs");
const [base, cssPath, outdir, ...jobs] = process.argv.slice(2);
const css = fs.readFileSync(cssPath, "utf8");
const STATIC = __dirname + "/../static";
fs.mkdirSync(outdir, { recursive: true });
(async () => {
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
  const ctxs = {};
  async function ctxFor(w) {
    if (ctxs[w]) return ctxs[w];
    const ctx = await b.newContext({ viewport: { width: w, height: w < 500 ? 844 : 900 }, deviceScaleFactor: parseFloat(process.env.DSF || "1"), colorScheme: "dark" });
    await ctx.route("**/static/style.css*", (r) => r.fulfill({ status: 200, contentType: "text/css", body: css }));
    await ctx.route("**/static/icons.svg*", (r) => r.fulfill({ status: 200, contentType: "image/svg+xml", body: fs.readFileSync(STATIC + "/icons.svg") }));
    const H = "/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness/fonts/extra";
    await ctx.route("**/static/fonts/extra/**", (r) => { const f = H + "/" + require("path").basename(new URL(r.request().url()).pathname); return fs.existsSync(f) ? r.fulfill({ status: 200, contentType: "font/woff2", body: fs.readFileSync(f) }) : r.fulfill({ status: 404, body: "" }); });
    const p = await ctx.newPage();
    await p.goto(base + "/login");
    await p.fill("#password", "palette-demo-pass");
    await Promise.all([p.waitForNavigation(), p.click("form button[type=submit]")]);
    ctxs[w] = p; return p;
  }
  for (const job of jobs) {
    const [w, route, name, full, hover, js] = job.split("|");
    const p = await ctxFor(parseInt(w, 10));
    await p.goto(base + route);
    await p.waitForLoadState("networkidle");
    await p.waitForTimeout(1800);
    if (hover) { await p.hover(hover); await p.waitForTimeout(300); }
    if (js) { console.log(name, JSON.stringify(await p.evaluate(js))); }
    if (full && full.startsWith("el:")) { await p.locator(full.slice(3)).first().screenshot({ path: outdir + "/" + name + ".png" }); } else await p.screenshot({ path: outdir + "/" + name + ".png", fullPage: full === "full" });
    console.log("shot", name);
  }
  await b.close();
})();
