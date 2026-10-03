// Lists small click targets and evaluates expressions on a page of this palette's render.
const { chromium } = require("playwright");
const fs = require("fs");
const BASE = process.env.FAMILYDB_BASE;
const css = fs.readFileSync("out/r10-mut-4/style.css", "utf8");
const [url, width, expr] = [process.argv[2], +(process.argv[3] || 1280), process.argv[4]];
(async () => {
  const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
  const ctx = await browser.newContext({ viewport: { width, height: 900 } });
  await ctx.route("**/static/style.css*", (r) => r.fulfill({ status: 200, contentType: "text/css", body: css }));
  const FONTS = "/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness/fonts/extra";
  await ctx.route("**/static/fonts/extra/**", (r) => r.fulfill({ status: 200, contentType: "font/woff2", body: fs.readFileSync(FONTS + "/" + require("path").basename(new URL(r.request().url()).pathname)) }));
  const page = await ctx.newPage();
  await page.goto(BASE + "/login");
  await page.fill("#password", "palette-demo-pass");
  await Promise.all([page.waitForNavigation(), page.click("form button[type=submit]")]);
  await page.goto(BASE + url);
  await page.waitForLoadState("networkidle"); await page.waitForTimeout(800);
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
  await browser.close();
})();
