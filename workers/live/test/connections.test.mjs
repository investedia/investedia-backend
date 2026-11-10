import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {ingestConnections,readConnections,MAX_BODY} from '../v1/connections.js';
import {fakeKV} from './helpers.mjs';import worker from '../index.js';
const now=Date.parse('2026-11-10T12:00:00Z');
const sample=JSON.parse(fs.readFileSync(new URL('../../../assets/globe/connections.json',import.meta.url))).connections[0];
function line(id='unit>asset',age=0){return {...structuredClone(sample),id,event:id.split('>')[0],published_at:new Date(now-age).toISOString()};}
const body=(connections=[line()],generated_at=new Date(now).toISOString())=>({schema:'investedia.connections.v1',generated_at,connections});
const req=(b,auth='Bearer unit-test-token')=>new Request('https://unit.test/v1/ingest/connections',{method:'POST',headers:{'Content-Type':'application/json',Authorization:auth},body:JSON.stringify(b)});
const env=()=>({PRICES:fakeKV(),INGEST_TOKEN:'unit-test-token'});
test('connections auth and unconfigured ingest never write',async()=>{const e=env();assert.equal((await ingestConnections(req(body(),''),e,now)).status,401);delete e.INGEST_TOKEN;assert.equal((await ingestConnections(req(body()),e,now)).status,503);assert.equal(e.PRICES.puts,0);});
test('connections validate rules and retain last good on any invalid row',async()=>{const e=env();assert.equal((await ingestConnections(req(body()),e,now)).status,200);const before=e.PRICES.m.get('connections');for(const change of [{type:'sector'},{confidence:.1},{dest:{...sample.dest,lat:100}},{origin:{...sample.origin,lat:sample.dest.lat,lon:sample.dest.lon}},{published_at:'bad'},{evidence:{...sample.evidence,why:''}}]){const r=await ingestConnections(req(body([{...line(),...change}])),e,now);assert.equal(r.status,422);assert.equal(e.PRICES.m.get('connections'),before);}});
test('connections merge by id, prune 30 days by publication time, preserve original dates',async()=>{const e=env();await ingestConnections(req(body([line('old>asset',31*864e5),line('keep>asset',20*864e5)])),e,now);await ingestConnections(req(body([line('new>asset'),line('new>asset')])),e,now);const r=await readConnections(e,now);assert.equal(r.status,200);assert.deepEqual(r.body.connections.map(c=>c.id),['new>asset','keep>asset']);assert.equal(r.body.connections[1].published_at,line('keep>asset',20*864e5).published_at);});
test('connections whitelist nested fields and stale uploads cannot overwrite newer evidence',async()=>{const e=env(),first=line();first.private='drop';first.dest.secret='drop';await ingestConnections(req(body([first])),e,now);const stale=line();stale.explanation='old correction';await ingestConnections(req(body([stale],new Date(now-3600e3).toISOString())),e,now);const s=JSON.parse(e.PRICES.m.get('connections'));assert.equal(s.connections[0].private,undefined);assert.equal(s.connections[0].dest.secret,undefined);assert.equal(s.connections[0].explanation,first.explanation);assert.equal(s.generated_at,new Date(now).toISOString());});
test('connections reject conflicting duplicate ids and bound streamed bodies',async()=>{const e=env();assert.equal((await ingestConnections(req(body([line(),{...line(),explanation:'conflicting'}])),e,now)).status,422);const huge=req({junk:'x'.repeat(MAX_BODY+1)});assert.equal((await ingestConnections(huge,e,now)).status,413);assert.equal(e.PRICES.puts,0);});
test('connections accepts the existing generator output without inventing countries or direction',async()=>{const e=env();const saved=JSON.parse(fs.readFileSync(new URL('../../../assets/globe/connections.json',import.meta.url)));const r=await ingestConnections(req(saved),e,now);assert.equal(r.status,200);assert.equal(r.body.count,saved.connections.length);const out=await readConnections(e,now);assert.equal(out.body.schema,saved.schema);assert.equal(out.body.generated_at,saved.generated_at);});
test('connections GET caches for 300s, ingest purges connection/news/status cache',async()=>{
 const previous=globalThis.caches,map=new Map(),deleted=[],pending=[];globalThis.caches={default:{match:async key=>map.get(key.url)?.clone(),put:async(key,r)=>map.set(key.url,r.clone()),delete:async key=>{deleted.push(key.url);return map.delete(key.url);}}};
 const e=env(),ctx={waitUntil:p=>pending.push(p)};try{
  const requestBody=body([{...line(),published_at:new Date().toISOString()}],new Date().toISOString());let r=await worker.fetch(req(requestBody),e,ctx);assert.equal(r.status,200);await Promise.all(pending);assert.ok(deleted.some(k=>k.includes('/v1/connections')));assert.ok(deleted.some(k=>k.includes('/v1/news')));assert.ok(deleted.some(k=>k.includes('/v1/status')));
  r=await worker.fetch(new Request('https://unit.test/v1/connections',{headers:{Origin:'https://investedia.com'}}),e,ctx);assert.equal(r.status,200);assert.equal(r.headers.get('Cache-Control'),'public, max-age=300');assert.equal(r.headers.get('Access-Control-Allow-Origin'),'https://investedia.com');await Promise.all(pending);
  r=await worker.fetch(new Request('https://unit.test/v1/connections'),e,ctx);assert.equal(r.status,200);assert.equal((await r.json()).connections.length,1);
 }finally{if(previous===undefined)delete globalThis.caches;else globalThis.caches=previous;}
});
test('connections generation appears in news metadata and status without changing article times',async()=>{
 const {handleNews}=await import('../v1/news.js'),{handleStatus}=await import('../v1/prices.js');const e=env();
 const saved=JSON.parse(fs.readFileSync(new URL('../../../assets/globe/news-live.json',import.meta.url)));await e.PRICES.put('news',JSON.stringify({t:now,stories:saved.stories.slice(0,2)}));
 await ingestConnections(req(body()),e,now);const news=await handleNews(e,now),status=await handleStatus(e,now);
 assert.equal(news.body.meta.connections_generated_at,new Date(now).toISOString());assert.equal(status.body.connections_generated_at,new Date(now).toISOString());assert.equal(news.body.data.stories[0].published_at,saved.stories[0].published_at);
});
test('connections retains last good if a merged 30-day population exceeds the row limit',async()=>{
 const e=env();const base=line();base.origin.place='x';base.dest.name='x';base.explanation='x';base.evidence={impact:'x',why:'x',source:'x',headline:'x',direction:'unclear'};
 for(let batch=0;batch<4;batch++){
  const list=Array.from({length:2500},(_,i)=>({...base,id:`unit-${batch}-${i}>asset`,event:`unit-${batch}-${i}`}));
  assert.equal((await ingestConnections(req(body(list)),e,now)).status,200);
 }
 const old=e.PRICES.m.get('connections');assert.equal((await ingestConnections(req(body([line('over-limit>asset')])),e,now)).status,413);assert.equal(e.PRICES.m.get('connections'),old);
});
