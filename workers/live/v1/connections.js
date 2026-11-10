// Evidence-backed lines only. Authenticated writes; reads never generate or infer links.
import { timingSafeEqual } from './news.js';
export const SCHEMA='investedia.connections.v1', RETENTION_MS=30*86400e3;
export const MAX_BODY=2*1024*1024, MAX_ROWS=10000, MAX_STORED=8*1024*1024;
const TYPES=new Set(['direct','acquisition','supply-chain','partnership','central-bank','currency','market','commodity','regulatory','named-peer']);
const RELATIONS=new Set(['subject','parent','acquirer','target','supplier','customer','partner','counterparty','policy-rate','yield','currency','market-benchmark','commodity-output','commodity-input','regulator-action','competitor','index-constituent','other','subsidiary','named-in-headline']);
const result=(status,error)=>({status,body:{error}});
const text=(s,max,required=true)=>{if(typeof s!=='string'||s.length>max||(required&&!s.trim())||/[\u0000-\u001f]/.test(s))throw Error('invalid text');return s;};
const time=s=>{if(typeof s!=='string'||!/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(s)||!Number.isFinite(Date.parse(s)))throw Error('invalid timestamp');return s;};
function point(p,dest=false){
 if(!p||!Number.isFinite(p.lat)||!Number.isFinite(p.lon)||Math.abs(p.lat)>90||Math.abs(p.lon)>180||typeof p.country!=='string'||!p.country.trim()||p.country.length>80)throw Error('invalid coordinates');
 return dest?{name:text(p.name,200),country:p.country,lat:p.lat,lon:p.lon,asset:text(p.asset,120)}:{place:text(p.place,200,false),country:p.country,lat:p.lat,lon:p.lon};
}
function distance(a,b){const rad=x=>x*Math.PI/180;const h=Math.sin(rad(b.lat-a.lat)/2)**2+Math.cos(rad(a.lat))*Math.cos(rad(b.lat))*Math.sin(rad(b.lon-a.lon)/2)**2;return 6371*2*Math.asin(Math.min(1,Math.sqrt(h)));}
function row(c,now){
 if(!c||!TYPES.has(c.type)||!RELATIONS.has(c.relation)||![1,2].includes(c.tier)||!Number.isFinite(c.confidence)||c.confidence<.25||c.confidence>1)throw Error('invalid evidence rules');
 const published=time(c.published_at);if(Date.parse(published)>now+300000)throw Error('future article');
 const origin=point(c.origin),dest=point(c.dest,true),km=distance(origin,dest),e=c.evidence;
 if(km<100||!e||!(e.direction==null||['up','down','mixed','unclear'].includes(e.direction)))throw Error('invalid evidence');
 const out={id:text(c.id,240),event:text(c.event,160),published_at:published,origin,dest,type:c.type,relation:c.relation,tier:c.tier,cross_border:typeof c.cross_border==='boolean'?c.cross_border:origin.country!==dest.country,km:Math.round(km),confidence:c.confidence,
 evidence:{impact:text(e.impact,240),why:text(e.why,2000),direction:e.direction??'unclear',source:text(e.source,240),headline:text(e.headline,1000)},explanation:text(c.explanation,2000)};
 if(c.importance!=null){if(!Number.isInteger(c.importance)||c.importance<0||c.importance>3)throw Error('invalid importance');out.importance=c.importance;}
 if(c.score!=null){if(!Number.isFinite(c.score)||c.score<0||c.score>1000)throw Error('invalid score');out.score=c.score;}
 return out;
}
function clean(body,now){
 if(!body||body.schema!==SCHEMA||!Array.isArray(body.connections)||body.connections.length>MAX_ROWS)throw Error('invalid schema');
 const stamp=time(body.generated_at);if(Date.parse(stamp)>now+300000)throw Error('future generation');
 const rows=new Map();for(const value of body.connections){const r=row(value,now);if(rows.has(r.id)&&JSON.stringify(rows.get(r.id))!==JSON.stringify(r))throw Error('conflicting duplicate id');rows.set(r.id,r);}
 return {schema:SCHEMA,generated_at:stamp,rules:{min_km:100,min_confidence:.25,sector_lines:false},connections:[...rows.values()]};
}
async function readBody(req){
 const reader=req.body?.getReader();if(!reader)throw Object.assign(Error(),{status:400});let size=0,raw='';const decoder=new TextDecoder();
 try{while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>MAX_BODY){await reader.cancel();throw Object.assign(Error(),{status:413});}raw+=decoder.decode(value,{stream:true});}return JSON.parse(raw+decoder.decode());}
 catch(e){if(e.status)throw e;throw Object.assign(Error(),{status:400});}finally{reader.releaseLock();}
}
export async function ingestConnections(req,env,now=Date.now()){
 if(!env.INGEST_TOKEN)return result(503,'ingest not configured');
 if(!timingSafeEqual(req.headers.get('Authorization')||'','Bearer '+env.INGEST_TOKEN))return result(401,'unauthorized');
 if((req.headers.get('Content-Type')||'').split(';')[0].trim()!=='application/json')return result(415,'JSON required');
 let incoming;try{incoming=clean(await readBody(req),now);}catch(e){return result(e.status||422,e.status===413?'too large':'invalid connections');}
 try{
  const previous=await env.PRICES.get('connections'),old=previous?clean(JSON.parse(previous),now):null;
  const newer=!old||Date.parse(incoming.generated_at)>=Date.parse(old.generated_at),rows=new Map();
  for(const r of newer?[...(old?.connections||[]),...incoming.connections]:[...incoming.connections,...old.connections])if(Date.parse(r.published_at)>=now-RETENTION_MS)rows.set(r.id,r);
  const connections=[...rows.values()].sort((a,b)=>Date.parse(b.published_at)-Date.parse(a.published_at)||a.id.localeCompare(b.id));
  if(connections.length>MAX_ROWS)return result(413,'retention capacity exceeded; previous copy retained');
  const merged={...incoming,generated_at:newer?incoming.generated_at:old.generated_at,connections},serialized=JSON.stringify(merged);
  if(new TextEncoder().encode(serialized).length>MAX_STORED)return result(413,'retention size exceeded; previous copy retained');
  const written=serialized!==previous;
  const metadata=JSON.stringify({generated_at:merged.generated_at,count:connections.length}),metaChanged=(await env.PRICES.get('connections:meta'))!==metadata;
  if(written)await env.PRICES.put('connections',serialized);if(written||metaChanged)await env.PRICES.put('connections:meta',metadata);
  return {status:200,body:{ok:true,written:written||metaChanged,count:connections.length,generated_at:merged.generated_at}};
 }catch{return result(503,'connections storage unavailable');}
}
export async function readConnections(env,now=Date.now()){
 try{const raw=await env.PRICES.get('connections');if(!raw)return result(503,'connections unavailable');
  const body=clean(JSON.parse(raw),now);body.connections=body.connections.filter(c=>Date.parse(c.published_at)>=now-RETENTION_MS);
  return {status:200,body:{...body,meta:{connections_generated_at:body.generated_at,count:body.connections.length,retention_days:30}}};
 }catch{return result(503,'connections unavailable');}
}
