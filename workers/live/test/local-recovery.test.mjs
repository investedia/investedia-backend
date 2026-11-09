import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import worker from '../index.js';
test('recovered Worker never dispatches to former GitHub account by default',async()=>{
 const requests=[];const pending=[];const original=globalThis.fetch;
 globalThis.fetch=async url=>{requests.push(String(url));throw new Error('External request forbidden by test')};
 try {await worker.scheduled({cron:'*/5 * * * *',scheduledTime:Date.now()},{DISPATCH_TOKEN:'test-only-not-a-real-token'}, {waitUntil:p=>pending.push(p)});await Promise.all(pending);assert.deepEqual(requests,[]);}finally{globalThis.fetch=original;}
});
test('production CORS permits only exact Investedia HTTPS origins',async()=>{
 for(const origin of ['https://investedia.com','https://www.investedia.com','http://127.0.0.1:8765','http://localhost:8765','https://investedia.com.attacker.test','https://other.test']){
  const response=await worker.fetch(new Request('https://example.test/v1/prices',{method:'OPTIONS',headers:{Origin:origin}}),{},{});
  assert.equal(response.status,204);
  assert.equal(response.headers.get('Access-Control-Allow-Origin'),['https://investedia.com','https://www.investedia.com'].includes(origin)?origin:null);
 }
});
test('dispatch cannot be re-enabled by legacy settings',async()=>{
 const original=globalThis.fetch; const pending=[];
 globalThis.fetch=async()=>{throw new Error('No dispatch is permitted')};
 try{await worker.scheduled({cron:'*/5 * * * *'},{DISPATCH_ENABLED:'true',DISPATCH_TOKEN:'test-only',DISPATCH_REPOSITORY:'investedia/investedia-backend'},{waitUntil:p=>pending.push(p)});await Promise.all(pending);assert.equal(pending.length,0);}finally{globalThis.fetch=original;}
});
test('recovered Worker schedules remain disabled',()=>{
 assert.match(fs.readFileSync(new URL('../wrangler.toml',import.meta.url),'utf8'),/^crons = \[\]/m);
});
