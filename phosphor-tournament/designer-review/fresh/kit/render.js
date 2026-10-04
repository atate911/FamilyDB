// Usage: node render.js <folder>
// Renders every page file in <folder> (home, chat, ideas, plans, todo, status, settings .html)
// at 1280 wide (full page) into <folder>/shots/<page>.png, and home and chat at 390 wide
// (phone, 2x) into <folder>/shots/<page>-phone.png.
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path");
const dir = path.resolve(process.argv[2] || ".");
const pages = ["home", "chat", "ideas", "plans", "todo", "status", "settings"];
(async () => {
  const proxy = process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined;
  const browser = await chromium.launch({ proxy });
  const out = path.join(dir, "shots"); fs.mkdirSync(out, { recursive: true });
  const shoot = async (name, width, scale, suffix) => {
    const f = path.join(dir, name + ".html");
    if (!fs.existsSync(f)) { console.log("missing", name + ".html"); return; }
    const ctx = await browser.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: scale, ignoreHTTPSErrors: true });
    const p = await ctx.newPage();
    const errs = []; p.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
    await p.goto("file://" + f, { waitUntil: "networkidle" });
    await p.evaluate(() => document.fonts.ready);
    const wide = await p.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    await p.screenshot({ path: path.join(out, name + suffix + ".png"), fullPage: true });
    console.log("ok", name + suffix, wide ? "(WARNING: wider than the screen)" : "", errs.length ? "errors: " + errs.join(" | ") : "");
    await ctx.close();
  };
  for (const n of pages) await shoot(n, 1280, 1, "");
  for (const n of ["home", "chat"]) await shoot(n, 390, 2, "-phone");
  await browser.close();
})();
