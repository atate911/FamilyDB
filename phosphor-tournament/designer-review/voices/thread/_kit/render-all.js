// node render-all.js <folder> [page ...]
// Renders every page file in <folder> (every *.html not starting with "_"), or only the named
// pages, full length at 1280 px wide into shots/<page>.png and at 390 px (2x) into
// shots/<page>-phone.png. Pages named in DARK="home chat ..." are also rendered with the
// browser set to dark mode into shots/dark/. A page is retried until its web fonts load.
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path");
const dir = path.resolve(process.argv[2] || ".");
let pages = process.argv.slice(3);
if (!pages.length) pages = fs.readdirSync(dir).filter(f => f.endsWith(".html") && !f.startsWith("_")).map(f => f.replace(/\.html$/, "")).sort();
const dark = (process.env.DARK || "").split(/\s+/).filter(Boolean);
(async () => {
  const proxy = process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined;
  const browser = await chromium.launch({ proxy });
  const out = path.join(dir, "shots"); fs.mkdirSync(path.join(out, "dark"), { recursive: true });
  const shoot = async (name, width, scale, scheme, file) => {
    const f = path.join(dir, name + ".html");
    let ok = false, tries = 0, wide = false, errs = [];
    while (!ok && tries < 5) {
      tries++;
      const ctx = await browser.newContext({ viewport: { width, height: width > 500 ? 900 : 844 }, deviceScaleFactor: scale, colorScheme: scheme, ignoreHTTPSErrors: true });
      const p = await ctx.newPage(); errs = []; let bad = 0;
      p.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
      p.on("requestfailed", r => { if (/\.(woff2?|ttf|otf)|fonts\./.test(r.url())) bad++; });
      await p.goto("file://" + f, { waitUntil: "networkidle" });
      await p.evaluate(() => document.fonts.ready);
      const failed = await p.evaluate(() => [...document.fonts].filter(x => x.status === "error").length);
      wide = await p.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
      ok = !bad && !failed;
      if (ok || tries === 5) await p.screenshot({ path: file, fullPage: true });
      await ctx.close();
    }
    console.log(path.basename(file), ok ? "ok" : "FONTS FAILED", wide ? "WARNING: wider than the screen" : "", errs.length ? "errors: " + errs.join(" | ") : "");
  };
  for (const n of pages) {
    if (!fs.existsSync(path.join(dir, n + ".html"))) { console.log("missing", n); continue; }
    await shoot(n, 1280, 1, "light", path.join(out, n + ".png"));
    await shoot(n, 390, 2, "light", path.join(out, n + "-phone.png"));
    if (dark.includes(n)) {
      await shoot(n, 1280, 1, "dark", path.join(out, "dark", n + ".png"));
      await shoot(n, 390, 2, "dark", path.join(out, "dark", n + "-phone.png"));
    }
  }
  await browser.close();
})();
