// node final.js <folder> <outdir>: every page at 1280 (full page) and 390 (2x, full page),
// retrying a page until no web font failed to load (up to 6 tries).
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path");
const dir = path.resolve(process.argv[2]), out = path.resolve(process.argv[3]);
const pages = ["home", "chat", "ideas", "plans", "todo", "status", "settings"];
(async () => {
  const proxy = process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined;
  const browser = await chromium.launch({ proxy });
  fs.mkdirSync(out, { recursive: true });
  for (const [w, scale, suf] of [[1280, 1, ""], [390, 2, "-phone"]]) for (const n of pages) {
    const f = path.join(dir, n + ".html"); if (!fs.existsSync(f)) { console.log("missing", n); continue; }
    let ok = false, tries = 0, bad = [];
    while (!ok && tries < 6) {
      tries++;
      const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: scale, ignoreHTTPSErrors: true });
      const p = await ctx.newPage(); bad = [];
      p.on("requestfailed", r => { if (/fonts\.(googleapis|gstatic)/.test(r.url())) bad.push(r.url()); });
      await p.goto("file://" + f, { waitUntil: "networkidle" });
      await p.evaluate(() => document.fonts.ready);
      const failed = await p.evaluate(() => [...document.fonts].filter(x => x.status === "error").length);
      ok = bad.length === 0 && failed === 0;
      if (ok || tries === 6) await p.screenshot({ path: path.join(out, n + suf + ".png"), fullPage: true });
      await ctx.close();
    }
    console.log(path.basename(dir), n + suf, ok ? "ok" : "FONTS FAILED", "tries", tries);
  }
  await browser.close();
})();
