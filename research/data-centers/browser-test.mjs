import {createRequire} from 'node:module';import fs from 'node:fs';import assert from 'node:assert/strict';
const require=createRequire(import.meta.url),{chromium}=require('playwright');
const out=new URL('screenshots/',import.meta.url);fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});const results=[];
try{for(const theme of ['dark','light'])for(const width of [1440,390]){const page=await browser.newPage({viewport:{width,height:900},deviceScaleFactor:1}),errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://127.0.0.1:8791');await page.waitForFunction(()=>document.querySelectorAll('.record').length===26);
if(theme==='light')await page.click('#theme');await page.evaluate(label=>document.querySelector('#review-label').textContent=label,`New · Data Centers research · ${width===390?'phone 390':'PC 1440'} · ${theme}`);
assert.match(await page.locator('#detail').innerText(),/indirect corporate exposure/i);assert.match(await page.locator('#detail').innerText(),/not proof of property ownership/i);assert.equal(await page.locator('#assets').innerText(),'26');
assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);await page.screenshot({path:new URL(`new-${width}-${theme}-globe.png`,out).pathname,fullPage:true});
await page.fill('#search','Dubai');assert.equal(await page.locator('.record').count(),1);assert.match(await page.locator('#detail h2').innerText(),/DX1/);await page.fill('#search','');await page.selectOption('#company','EQ:XNYS:DLR');assert.equal(await page.locator('.record').count(),23);await page.selectOption('#company','');
await page.click('[data-view=directory]');assert.equal(await page.locator('.record').count(),26);await page.fill('#search','DUB10');assert.equal(await page.locator('.record').count(),0);await page.fill('#search','');await page.screenshot({path:new URL(`new-${width}-${theme}-directory.png`,out).pathname,fullPage:true});
assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);assert.deepEqual(errors,[]);results.push({width,theme,records:26,search:true,company_filter:true,contradictions_excluded:true,overflow:false,runtime_errors:errors});await page.close();console.log('PASS',width,theme);}
fs.writeFileSync(new URL('browser-results.json',import.meta.url),JSON.stringify(results,null,2)+'\n');}finally{await browser.close()}
