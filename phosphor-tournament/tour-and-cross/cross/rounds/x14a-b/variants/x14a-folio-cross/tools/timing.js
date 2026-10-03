// When DOMContentLoaded fires on the timeline animations run on: node timing.js BASE CSS path
const { chromium } = require("playwright");
const fs = require("fs"); const path = require("path");
const [BASE, CSS, u] = process.argv.slice(2);
const css = fs.readFileSync(CSS, "utf8");
const STATIC = path.resolve(__dirname, "../static");
const FONTS = "/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness/fonts/extra";
(async () => {
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
  const ctx = await b.newContext({ viewport: { width: 1280, height: 900 }, colorScheme: "dark" });
  await ctx.route("**/static/style.css*", r => r.fulfill({ status: 200, contentType: "text/css", body: css }));
  await ctx.route("**/static/**", r => { const rel = new URL(r.request().url()).pathname.replace(/^\/static\//, ""); const f = path.join(STATIC, rel); if (fs.existsSync(f) && fs.statSync(f).isFile()) return r.fulfill({ status: 200, contentType: rel.endsWith(".svg") ? "image/svg+xml" : "image/png", body: fs.readFileSync(f) }); return r.fallback(); });
  await ctx.route("**/static/fonts/extra/**", r => { const f = path.join(FONTS, path.basename(new URL(r.request().url()).pathname)); return fs.existsSync(f) ? r.fulfill({ status: 200, contentType: "font/woff2", body: fs.readFileSync(f) }) : r.fulfill({ status: 404, body: "" }); });
  await ctx.addInitScript(() => { document.addEventListener("DOMContentLoaded", () => { window.__dcl = document.timeline.currentTime; }); });
  const p = await ctx.newPage();
  await p.goto(BASE + "/login"); await p.fill("#password", "palette-demo-pass");
  await Promise.all([p.waitForNavigation(), p.click("form button[type=submit]")]);
  await p.goto(BASE + u); await p.waitForTimeout(1500);
  await p.reload({ waitUntil: "domcontentloaded" });
  const t0 = await p.evaluate(() => [window.__dcl, document.timeline.currentTime]);
  await p.waitForTimeout(60);
  const t1 = await p.evaluate(() => { const a = document.getAnimations().filter(x => x.animationName === "power-on").map(x => [x.effect.target.className, Math.round(x.currentTime)]); return [document.timeline.currentTime, a.slice(0, 4)]; });
  console.log(JSON.stringify({ t0, t1 }));
  await b.close();
})();
