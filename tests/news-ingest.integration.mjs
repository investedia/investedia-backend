// Local HTTP integration only: real saved articles, ephemeral KV/cache, no hosted writes or providers.
import http from 'node:http';import fs from 'node:fs/promises';import os from 'node:os';import path from 'node:path';import {spawn} from 'node:child_process';import assert from 'node:assert/strict';
import worker from '../workers/live/index.js';
const root=path.resolve(new URL('..',import.meta.url).pathname.replace(/^\/([A-Z]:)/,'$1'));
const savedFile=path.join(root,'assets/globe/news-live.json'),original=await fs.readFile(savedFile),feed=JSON.parse(original);
const kv=new Map(),edge=new Map(),originalCaches=globalThis.caches;
globalThis.caches={default:{match:async r=>edge.get(r.url)?.clone(),put:async(r,v)=>edge.set(r.url,v.clone()),delete:async r=>edge.delete(r.url)}};
const env={INGEST_TOKEN:'local-integration-fixture-only',PRICES:{get:async k=>kv.get(k)||null,put:async(k,v)=>kv.set(k,v)}};
const server=http.createServer(async(req,res)=>{try{const chunks=[];for await(const b of req)chunks.push(b);const pending=[];const input=new Request('http://127.0.0.1:'+server.address().port+req.url,{method:req.method,headers:req.headers,...(!['GET','HEAD'].includes(req.method)?{body:Buffer.concat(chunks)}:{})});const output=await worker.fetch(input,env,{waitUntil:p=>pending.push(p)});await Promise.all(pending);res.writeHead(output.status,Object.fromEntries(output.headers));res.end(Buffer.from(await output.arrayBuffer()));}catch{res.writeHead(500).end();}});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const url='http://127.0.0.1:'+server.address().port;
const read=async route=>{const r=await fetch(url+route);return {status:r.status,body:await r.json()}};
const upload=async file=>new Promise((resolve,reject)=>{const child=spawn(process.env.PYTHON||'python',[path.join(root,'tools/push-news-to-worker.py'),'--file',file],{cwd:root,env:{...process.env,WORKER_URL:url,NEWS_INGEST_TOKEN:env.INGEST_TOKEN}});let stdout='',stderr='';child.stdout.on('data',s=>stdout+=s);child.stderr.on('data',s=>stderr+=s);child.on('error',reject);child.on('close',code=>code===0?resolve(JSON.parse(stdout)):reject(Error('Local uploader failed: '+code)));});
const tmp=await fs.mkdtemp(path.join(os.tmpdir(),'investedia-ingest-test-'));
try{
 assert.equal((await read('/v1/news')).status,503);
 const first=await upload(savedFile);assert.equal(first.written,true);
 const n=await read('/v1/news'),g=await read('/v1/globe');assert.equal(n.status,200);assert.equal(g.status,200);assert.equal(n.body.data.stories.length,40);assert.deepEqual(n.body.data.stories.map(s=>s.id),g.body.data.events.map(s=>s.id));
 assert.equal(n.body.meta.fetched_at,new Date(feed.updated_at).toISOString());
 const again=await upload(savedFile);assert.equal(again.written,false);
 const changed=structuredClone(feed);const id=n.body.data.stories[0].id;changed.stories.find(s=>s.id===id).headline='[LOCAL TEST ONLY] '+n.body.data.stories[0].headline;const changedFile=path.join(tmp,'test-feed.json');await fs.writeFile(changedFile,JSON.stringify(changed));
 assert.equal((await upload(changedFile)).written,true);
 const correctedNews=await read('/v1/news'),correctedGlobe=await read('/v1/globe');assert.ok(correctedNews.body.data.stories.find(s=>s.id===id).headline.startsWith('[LOCAL TEST ONLY]'));assert.ok(correctedGlobe.body.data.events.find(s=>s.id===id).headline.startsWith('[LOCAL TEST ONLY]'));
 assert.ok(original.equals(await fs.readFile(savedFile)));
 console.log(JSON.stringify({mode:'local-http-only',authenticatedUpload:'passed',newsArticles:40,globeEvents:40,idempotency:'passed',sameIdCorrection:'passed',edgeCacheInvalidation:'passed',originalTimestamp:'preserved',savedFile:'unchanged',hostedWrites:0}));
}finally{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));globalThis.caches=originalCaches;await fs.unlink(path.join(tmp,'test-feed.json')).catch(()=>{});await fs.rmdir(tmp);}
