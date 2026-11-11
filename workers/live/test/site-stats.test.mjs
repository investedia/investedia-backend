import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {ingestNews,handleNews,mergeStats} from '../v1/news.js';
const feed=JSON.parse(fs.readFileSync(new URL('../../../assets/globe/news-live.json',import.meta.url),'utf8'));
const body=stats=>({generated_at:feed.updated_at,stories:feed.stories.slice(0,40),...(stats?{stats}:{})});
const NOW=Date.parse(feed.updated_at)+3600e3;
const setup=()=>{const map=new Map();return {map,env:{INGEST_TOKEN:'test-only',PRICES:{get:async k=>map.get(k)||null,put:async(k,v)=>map.set(k,v)}}}};
const post=b=>new Request('https://example.test/v1/ingest/news',{method:'POST',headers:{Authorization:'Bearer test-only'},body:JSON.stringify(b)});
test('homepage totals only grow and ignore bad values',()=>{
  assert.deepEqual(mergeStats({articles:10,sources:5},{articles:12,sources:4,projects:3}),{articles:12,sources:5,projects:3});
  assert.deepEqual(mergeStats(null,{articles:-1,sources:'9',projects:2.5}),null);
  assert.equal(mergeStats(null,null),null);
});
test('stats sent with a news push are returned by /v1/news, and a stats-only change is still written',async()=>{
  const {env}=setup();
  assert.equal((await ingestNews(post(body({articles:7000,sources:400,projects:2797})),env,NOW)).status,200);
  let r=await handleNews(env,NOW);assert.deepEqual(r.body.meta.stats,{articles:7000,sources:400,projects:2797});
  const again=await ingestNews(post(body({articles:7001,sources:400,projects:2797})),env,NOW+1000);assert.equal(again.body.written,true);
  r=await handleNews(env,NOW+1000);assert.equal(r.body.meta.stats.articles,7001);
  await ingestNews(post(body()),env,NOW+2000);r=await handleNews(env,NOW+2000);assert.equal(r.body.meta.stats.articles,7001);
});
