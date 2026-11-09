import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import worker from '../index.js';
test('recovered Worker never dispatches to former GitHub account by default',async()=>{
 const requests=[];const pending=[];const original=globalThis.fetch;
 globalThis.fetch=async url=>{requests.push(String(url));throw new Error('External request forbidden by test')};
 try {await worker.scheduled({cron:'*/5 * * * *',scheduledTime:Date.now()},{DISPATCH_TOKEN:'test-only-not-a-real-token'}, {waitUntil:p=>pending.push(p)});await Promise.all(pending);assert.deepEqual(requests,[]);}finally{globalThis.fetch=original;}
});
test('local loopback frontend can use Worker CORS',async()=>{
 const response=await worker.fetch(new Request('https://example.test/v1/prices',{method:'OPTIONS',headers:{Origin:'http://127.0.0.1:8765'}}),{},{});
 assert.equal(response.status,204);assert.equal(response.headers.get('Access-Control-Allow-Origin'),'http://127.0.0.1:8765');
});
test('recovered Worker schedules remain disabled',()=>{
 assert.match(fs.readFileSync(new URL('../wrangler.toml',import.meta.url),'utf8'),/^crons = \[\]/m);
});
