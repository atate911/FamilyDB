const { chromium } = require("playwright");
const fs = require("fs"); const path = require("path");
const [BASE, CSS, W, ...paths] = process.argv.slice(2);
const css = fs.readFileSync(CSS, "utf8");
const STATIC = path.resolve(__dirname, "../static");
const FONTS = "/tmp/claude-0/-home-user-FamilyDB/62374e35-c7e3-5c25-a94d-0502bde8e9d6/scratchpad/harness/fonts/extra";
(async () => {
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
  const ctx = await b.newContext({ viewport: { width: +W, height: 844 }, colorScheme: "dark" });
  await ctx.route("**/static/style.css*", r => r.fulfill({ status: 200, contentType: "text/css", body: css }));
  await ctx.route("**/static/**", r => { const rel = new URL(r.request().url()).pathname.replace(/^\/static\//, ""); const f = path.join(STATIC, rel); if (fs.existsSync(f) && fs.statSync(f).isFile()) return r.fulfill({ status: 200, contentType: rel.endsWith(".svg") ? "image/svg+xml" : "image/png", body: fs.readFileSync(f) }); return r.fallback(); });
  await ctx.route("**/static/fonts/extra/**", r => { const f = path.join(FONTS, path.basename(new URL(r.request().url()).pathname)); return fs.existsSync(f) ? r.fulfill({ status: 200, contentType: "font/woff2", body: fs.readFileSync(f) }) : r.fulfill({ status: 404, body: "" }); });
  const p = await ctx.newPage();
  await p.goto(BASE + "/login"); await p.fill("#password", "palette-demo-pass");
  await Promise.all([p.waitForNavigation(), p.click("form button[type=submit]")]);
  for (const u of paths) {
    await p.goto(BASE + u); await p.waitForLoadState("networkidle"); await p.waitForTimeout(800);
    const r = await p.evaluate(() => { const vw = document.documentElement.clientWidth; const out = [];
      for (const el of document.querySelectorAll("a[href], button, input:not([type=hidden]), select, textarea, summary")) { const b = el.getBoundingClientRect(); const cs = getComputedStyle(el); if (b.width===0||b.height===0||cs.visibility==="hidden"||el.closest("[aria-hidden=true]")) continue; if (Math.min(b.width,b.height) < 44) out.push(el.tagName+"."+String(el.className).slice(0,30)+" "+Math.round(b.width)+"x"+Math.round(b.height)+" "+(el.innerText||"").trim().slice(0,30).replace(/\n/g," ")); }
      return { out };
      for (const el of document.querySelectorAll("body *")) { const b = el.getBoundingClientRect(); if (b.right > vw + 1 && b.width > 0) out.push(el.tagName + "." + el.className + " w=" + Math.round(b.width) + " r=" + Math.round(b.right)); }
      return { sw: document.documentElement.scrollWidth, vw, out: out.slice(0, 15) }; });
    console.log(u, JSON.stringify(r, null, 1));
  }
  await b.close();
})();
