// Full-page shots of this variant: node shoot.js OUTDIR url[:name] ...  (W, VH env for size)
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const BASE = process.env.FAMILYDB_BASE;
const R = "/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness/rounds/r12";
const css = fs.readFileSync(R + "/out/r12-mut-2/style.css", "utf8");
const STATIC = R + "/variants/r12-mut-2/static";
const FONTS = "/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness/fonts/extra";
const out = process.argv[2];
fs.mkdirSync(out, { recursive: true });
const width = +(process.env.W || 1280);
(async () => {
  const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
  const ctx = await browser.newContext({ viewport: { width, height: +(process.env.VH || 900) }, deviceScaleFactor: +(process.env.DPR || 1), colorScheme: "dark" });
  await ctx.route("**/static/**", (r) => {
    const rel = new URL(r.request().url()).pathname.replace(/^\/static\//, "");
    const f = path.join(STATIC, rel);
    const types = { ".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp" };
    if (fs.existsSync(f) && fs.statSync(f).isFile() && types[path.extname(f)]) return r.fulfill({ status: 200, contentType: types[path.extname(f)], body: fs.readFileSync(f) });
    return r.fallback();
  });
  await ctx.route("**/static/style.css*", (r) => r.fulfill({ status: 200, contentType: "text/css", body: css }));
  await ctx.route("**/static/fonts/extra/**", (r) => { const f = path.join(FONTS, path.basename(new URL(r.request().url()).pathname)); return fs.existsSync(f) ? r.fulfill({ status: 200, contentType: "font/woff2", body: fs.readFileSync(f) }) : r.fulfill({ status: 404, body: "" }); });
  const page = await ctx.newPage();
  if (process.env.RM) await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(BASE + "/login");
  await page.fill("#password", "palette-demo-pass");
  await Promise.all([page.waitForNavigation(), page.click("form button[type=submit]")]);
  for (const arg of process.argv.slice(3)) {
    const [url, name] = arg.split("@");
    await page.goto(BASE + url);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(+(process.env.WAIT || 1800));
    await page.screenshot({ path: path.join(out, (name || url.replace(/\W+/g, "_") || "home") + ".png"), fullPage: !process.env.VIEW });
    if (process.env.EVAL) console.log(arg, JSON.stringify(await page.evaluate(process.env.EVAL)));
  }
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
