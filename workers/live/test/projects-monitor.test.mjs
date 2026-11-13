import test from 'node:test'; import assert from 'node:assert/strict';
import { runProjectsMonitor, visibleText, PROJECTS_CRON } from '../v1/projects-monitor.js';
function kv(){const m=new Map();return {get:async k=>m.get(k)??null,put:async(k,v)=>{m.set(k,v)},m};}
const page=(t)=>new Response(`<html><script>var csrf_token_123=1</script><body>${t} updated 10:42</body></html>`,{headers:{'content-type':'text/html',etag:'"a"'}});
test('first run stores state, second run with same text is unchanged, real text change is queued, 304 costs nothing',async()=>{
  const env={PRICES:kv(),PROJECTS_SOURCES_URL:'https://x.test/s.json'};let body='Sunni Dam HEP 382 MW under construction',calls=[];
  const f=async(u,o={})=>{calls.push([u,o.headers?.['If-None-Match']]);if(u.endsWith('s.json'))return Response.json({sources:[{url:'https://sjvn.test/p',projects:['gem:1']},{url:'https://eia.test/f.xlsx',projects:['eia:2']}],due:[{project:'eia:9',note:'Expected 2026-10'}]});
    if(u.includes('eia'))return new Response(null,{status:304});return page(body);};
  let r=await runProjectsMonitor(env,{fetchImpl:f});assert.equal(r.changed,0);assert.equal(r.unchanged,2);
  r=await runProjectsMonitor(env,{fetchImpl:f});assert.equal(r.changed,0,'volatile time/token text must not count as a change');
  body='Sunni Dam HEP 382 MW commissioned';r=await runProjectsMonitor(env,{fetchImpl:f});assert.equal(r.changed,1);
  const q=JSON.parse(await env.PRICES.get('projmon:queue'));assert.deepEqual(q.filter(x=>x.type==='source_changed').map(x=>x.affected_projects),[['gem:1']]);
  assert.equal(q.filter(x=>x.type==='expected_date_passed').length,1,'due items are not duplicated across runs');
  assert(calls.some(c=>c[1]==='"a"'),'conditional request uses stored ETag');
  assert([...env.PRICES.m.keys()].every(k=>k.startsWith('projmon:')),'only projmon:* keys are written');});
test('refusals are recorded, never retried, and the weekly cron is distinct from price crons',async()=>{
  const env={PRICES:kv()};const f=async u=>u.endsWith('.json')?Response.json({sources:[{url:'https://blocked.test'}]}):new Response('',{status:403});
  const r=await runProjectsMonitor(env,{fetchImpl:f});assert.equal(r.errors,1);assert.notEqual(PROJECTS_CRON,'*/2 * * * *');assert.equal(visibleText('<p>a</p> <script>x</script>b'),'a b');});
