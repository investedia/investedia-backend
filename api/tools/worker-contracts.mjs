// Compare the Java adapter to existing Worker functions using the SAME real saved data.
// Imports have no scheduled execution. No network request, financial calculation or file write.
import fs from 'node:fs';
import path from 'node:path';
import {handlePrices, SYMBOLS_BY_GROUP} from '../../workers/live/v1/prices.js';
import {handleNews, handleGlobe, ingestNews} from '../../workers/live/v1/news.js';
const root = process.argv[2];
const now = Date.parse('2026-11-07T15:00:00Z');
const source = fs.readFileSync(path.join(root, 'assets/quotes.js'), 'utf8');
const quotes = JSON.parse(source.slice(source.indexOf('{'), source.lastIndexOf('}') + 1));
const t = Date.parse(quotes.updated);
const p = Object.fromEntries(Object.entries(quotes.q).filter(([,q])=>Number.isFinite(q.p)&&Number.isFinite(q.d))
  .map(([s,q])=>[s,[q.p,q.d,(q.t||0)*1000,t]]));
const feed = JSON.parse(fs.readFileSync(path.join(root, 'assets/globe/news-live.json'), 'utf8'));
const stories = [...feed.stories].sort((a,b)=>a.published_at<b.published_at?1:a.published_at>b.published_at?-1:0).slice(0,40);
const snapshots = {px: {t,p,provider:'yahoo-spark'}};
const env = {INGEST_TOKEN:'contract-test-only',PRICES:{
  get:async key=>snapshots[key]?JSON.stringify(snapshots[key]):null,
  put:async (key,value)=>{snapshots[key]=JSON.parse(value);}
}};
const ingested = await ingestNews(new Request('https://example.test/v1/ingest/news',{
  method:'POST',headers:{Authorization:'Bearer contract-test-only'},body:JSON.stringify({stories,generated_at:feed.updated_at})
}),env,Date.parse(feed.updated_at));
if(ingested.status!==200)throw new Error('Saved feed failed existing Worker ingestion validation');
const expected = {};
for(const group of ['all',...Object.keys(SYMBOLS_BY_GROUP),'invalid']) {
  expected['/v1/prices?group='+group] = await handlePrices(new URL('https://example.test/v1/prices?group='+group),env,{},now);
}
expected['/v1/news'] = await handleNews(env,now);
expected['/v1/globe'] = await handleGlobe(env,now);
process.stdout.write(JSON.stringify(expected));
