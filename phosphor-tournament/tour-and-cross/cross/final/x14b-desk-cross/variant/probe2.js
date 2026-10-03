// Lists small click targets and evaluates expressions on a page of this palette's render.
const { chromium } = require("playwright");
const fs = require("fs");
const BASE = process.env.FAMILYDB_BASE;
const css = fs.readFileSync("out/x14b-desk-cross/style.css", "utf8");
const [url, width, expr] = [process.argv[2], +(process.argv[3] || 1280), process.argv[4]];
(async () => {
  const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
  const ctx = await browser.newContext({ viewport: { width, height: Number(process.env.VH || 900) } });
  await ctx.route("**/static/style.css*", (r) => r.fulfill({ status: 200, contentType: "text/css", body: css }));
  const FONTS = require("path").resolve(__dirname, "../../../../fonts/extra");
  await ctx.route("**/static/fonts/extra/**", (r) => { const f = require("path").join(FONTS, require("path").basename(new URL(r.request().url()).pathname)); return fs.existsSync(f) ? r.fulfill({ status: 200, contentType: "font/woff2", body: fs.readFileSync(f) }) : r.fulfill({ status: 404, body: "" }); });
  const page = await ctx.newPage();
  await page.goto(BASE + "/login");
  await page.fill("#password", "palette-demo-pass");
  await Promise.all([page.waitForNavigation(), page.click("form button[type=submit]")]);
  await page.goto(BASE + url);
  await page.waitForTimeout(800);
  const out = await page.evaluate((expr) => {
    if (expr) return eval(expr);
    const r = [];
    for (const el of document.querySelectorAll("a[href], button, input:not([type=hidden]), select, textarea, summary")) {
      const b = el.getBoundingClientRect(); const cs = getComputedStyle(el);
      if (b.width === 0 || b.height === 0 || cs.visibility === "hidden" || el.closest('[aria-hidden="true"]')) continue;
      if (Math.min(b.width, b.height) < 44) r.push(`${el.tagName} ${el.className} "${(el.innerText||'').trim().slice(0,30)}" ${Math.round(b.width)}x${Math.round(b.height)}`);
    }
    return r;
  }, expr);
  console.log(JSON.stringify(out, null, 1));
  if (process.env.SHOT) await page.screenshot({ path: process.env.SHOT, fullPage: !!process.env.FULL });
  console.log(await page.evaluate(()=>{const c=getComputedStyle(document.querySelector(".coming"),"::before");return [c.width,c.opacity,c.display,c.content, c.left, c.top, c.zIndex, c.filter].join(" ")}));
  await browser.close();
})();
