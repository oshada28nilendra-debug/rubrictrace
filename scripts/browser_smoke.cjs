// Actual headless rendering check, not a usability study or accessibility audit.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');
(async () => {
  const root = path.resolve(process.argv[2]);
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:390,height:844}});
    const errors=[]; const requests=[];
    page.on('pageerror', e=>errors.push(e.message));
    page.on('request', r=>requests.push(r.url()));
    await page.goto(pathToFileURL(path.join(root,'pack/review.html')).href);
    assert.equal(await page.locator('article').count(),2);
    assert.match(await page.locator('body').innerText(),/No final score/);
    assert.equal(await page.locator('script,iframe,img,form').count(),0);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    const headings = await page.locator('article').first().locator('h3').allTextContents();
    assert.equal(headings[0],'Student response');
    await page.goto(pathToFileURL(path.join(root,'export/feedback.html')).href);
    const text = await page.locator('body').innerText();
    assert.match(text,/100\.00/);assert.match(text,/20\.00/);
    assert.deepEqual(errors,[]);
    assert.equal(requests.filter(u=>/^https?:/.test(u)).length,0);
    fs.writeFileSync(path.join(root,'browser-verification.json'),JSON.stringify({status:'passed',browser:browser.version(),checks:['two submissions rendered','source-first headings','no active content','mobile no horizontal overflow','expected final scores','no page errors','no HTTP requests'],limitation:'Synthetic rendering check only'},null,2));
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exit(1);});
