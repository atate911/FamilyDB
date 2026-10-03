const { chromium } = require("playwright");
const fs=require("fs"), path=require("path");
const BASE=process.env.BASE, css=fs.readFileSync(process.env.CSS,"utf8"), OUT=process.env.OUT, STATIC=process.env.STATIC, FONTS=process.env.FONTS;
const pages = JSON.parse(process.env.PAGES);
(async()=>{
 const browser = await chromium.launch({executablePath:"/opt/pw-browsers/chromium", ignoreDefaultArgs:["--hide-scrollbars"]});
 for (const width of [1280,390]) {
  const ctx = await browser.newContext({viewport:{width,height: width==390?844:900}, deviceScaleFactor: width==390?2:1, colorScheme:"dark"});
  await ctx.route("**/static/style.css*", r=>r.fulfill({status:200, contentType:"text/css; charset=utf-8", body:css}));
  await ctx.route("**/static/fonts/extra/**", r=>{ const f=path.join(FONTS, path.basename(new URL(r.request().url()).pathname)); if(!fs.existsSync(f)) return r.fulfill({status:404,body:""}); return r.fulfill({status:200, contentType:"font/woff2", body: fs.readFileSync(f)});});
  const page=await ctx.newPage();
  await page.goto(BASE+"/login"); await page.fill("#password","palette-demo-pass"); await Promise.all([page.waitForNavigation(), page.click("form button[type=submit]")]);
  for (const [name,url,full,widths,act] of pages) { if(!widths.includes(width)) continue; await page.goto(BASE+url); await page.waitForLoadState("networkidle");
    if (act) { try { await page.evaluate(act); } catch(e) { console.error(e.message); } }
    await page.waitForTimeout(1500); await page.screenshot({path: path.join(OUT, name+(width==390?'-phone':'')+'.png'), fullPage: full}); }
  await ctx.close();
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
