// Read-only, version-pinned pilot API. No source fetching, writes or automatic publication.
const VERSION=/^\d{8}T\d{6}Z-[0-9a-f]{12}$/;
const COMPANY=/^I:[0-9a-f]{20}$/;
const CREDITS=['Wikidata (CC0)','GLEIF (CC0)','SEC EDGAR','World Bank (CC BY 4.0)','ECB'];
const response=(status,body,headers={})=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json','Cache-Control':status===200?'public, max-age=300':'no-store',...headers}});
const error=(status,code,reason)=>response(status,{error:{code,message:code.replaceAll('_',' '),reason,retryable:status>=500},meta:{stale:false,source_credits:CREDITS}});
class ApiError extends Error {constructor(status,code,reason){super(code);Object.assign(this,{status,code,reason});}}
const fail=(s,c,r)=>{throw new ApiError(s,c,r);};
const parse=value=>typeof value==='string'?JSON.parse(value):value;
async function object(env,key){const item=await env.MARKETS_BUCKET.get(key);if(!item)throw new Error('snapshot_object_missing');return item.json?await item.json():parse(item);}
function parameters(url,allowed){
 for(const [key] of url.searchParams){if(!allowed.includes(key)||url.searchParams.getAll(key).length!==1)fail(400,'invalid_query','unknown_or_duplicate_parameter');}
}
function integer(url,name,fallback,max){const value=url.searchParams.get(name);if(value==null)return fallback;if(!/^[1-9]\d*$/.test(value)||Number(value)>max)fail(400,'invalid_query','invalid_'+name);return Number(value);}
async function snapshot(env){
 const store=env.MARKETS_KV||env.PRICES;if(!store?.get||!env.MARKETS_BUCKET?.get)throw new Error('markets_storage_not_configured');
 const pointer=parse(await store.get('markets:current'));
 if(!pointer||!VERSION.test(pointer.version))throw new Error('no_valid_active_version');
 async function load(version){
  const prefix='markets/'+version;const manifest=await object(env,prefix+'/api-manifest.json');
  if(manifest.version!==version||manifest.schema!=='markets.registry/v1'||manifest.publication_eligible!==true||manifest.fixture===true)throw new Error('snapshot_not_publishable');
  if(!Number.isFinite(Date.parse(manifest.updated_at)))throw new Error('invalid_snapshot_timestamp');
  return {manifest,prefix,stale:Date.now()-Date.parse(manifest.updated_at)>48*3600e3};
 }
 try{return await load(pointer.version);}
 catch(e){if(pointer.previous_version&&VERSION.test(pointer.previous_version)&&Number.isFinite(Date.parse(pointer.updated_at))&&Date.now()-Date.parse(pointer.updated_at)<=24*3600e3){const old=await load(pointer.previous_version);old.stale=true;old.reason='active_snapshot_unavailable_previous_version';return old;}throw e;}
}
function metadata(s){return {notice:'Not investment advice',schema:'markets/v1',version:s.manifest.version,updated_at:s.manifest.updated_at,stale:s.stale,reason:s.reason||null,freshness:s.manifest.freshness||{},coverage_status:s.manifest.coverage||{},source_credits:s.manifest.source_credits||CREDITS};}
async function search(url,env,s){
 parameters(url,['country','sector','type','exchange','currency','verified','page','limit','version']);
 if(url.searchParams.has('type')&&url.searchParams.get('type')!=='stock')fail(422,'type_not_available','pilot_stocks_only');
 const verified=url.searchParams.get('verified')??'true';if(!['true','false'].includes(verified))fail(400,'invalid_query','verified_must_be_boolean');
 const page=integer(url,'page',1,10000),limit=integer(url,'limit',20,100);
 const criteria=[];
 for(const name of ['country','sector','exchange','currency']){
  const value=url.searchParams.get(name);if(value==null)continue;
  if(name==='country'&&!['US','GB'].includes(value))fail(422,'unsupported_country','US_GB_pilot_only');
  if(name==='exchange'&&!s.manifest.mic_allowlist.includes(value))fail(422,'unsupported_exchange','pilot_MICs_only');
  if(name==='currency'&&!/^[A-Z]{3}$/.test(value))fail(400,'invalid_query','currency_code_format');
  if(name==='currency'&&!s.manifest.currencies.includes(value))fail(422,'unsupported_currency','currency_not_in_snapshot');
  if(name==='sector'&&(!value||value.length>80))fail(400,'invalid_query','sector_code_format');
  criteria.push(name+':'+value);
 }
 if(!criteria.length)criteria.push('all:all');
 const keys=criteria.map(key=>s.manifest.filters[key]);
 if(keys.some(key=>!key))return {rows:[],total:0,total_verified:0,total_including_unverified:0,total_unverified:0,hidden_unverified:0,page,limit,next_page:null,version:s.manifest.version};
 const lists=await Promise.all(keys.map(k=>object(env,s.prefix+'/'+k)));
 const smallest=lists.reduce((a,b)=>a.length<=b.length?a:b);const sets=lists.map(l=>new Set(l));
 const filtered=smallest.filter(id=>sets.every(set=>set.has(id)));
 const verifiedPath=s.manifest.filters['verified:true'];const verifiedIds=new Set(verifiedPath?await object(env,s.prefix+'/'+verifiedPath):[]);
 const verifiedTotal=filtered.filter(id=>verifiedIds.has(id)).length,unverified=filtered.length-verifiedTotal;
 const visible=verified==='true'?filtered.filter(id=>verifiedIds.has(id)):filtered;
 if(page>1&&(page-1)*limit>=visible.length)fail(400,'page_out_of_range','no_rows_at_requested_page');
 const wanted=visible.slice((page-1)*limit,page*limit),paths=[...new Set(wanted.map(id=>'rows/'+id.split(':')[1][0]+'.json'))];
 if(paths.length>16)throw new Error('invalid_row_sharding');
 const shards=await Promise.all(paths.map(key=>object(env,s.prefix+'/'+key)));const rows=Object.assign({},...shards);
 const selected=wanted.map(id=>rows[id]);if(selected.some(r=>!r||!r.active||r.verification_status==='rejected'||(verified==='true'&&r.verification_status!=='verified')))throw new Error('invalid_search_index');
 return {rows:selected,total:visible.length,total_verified:verifiedTotal,total_including_unverified:filtered.length,total_unverified:unverified,
   hidden_unverified:verified==='true'?unverified:0,page,limit,next_page:page*limit<visible.length?page+1:null,version:s.manifest.version};
}
async function route(url,env,s){
 const path=url.pathname;
 if(url.searchParams.has('version')&&url.searchParams.get('version')!==s.manifest.version)fail(409,'version_changed','restart_pagination_at_active_version');
 if(path==='/v1/markets/search')return await search(url,env,s);
 let m=path.match(/^\/v1\/markets\/country\/([A-Z]{2})$/);
 if(m){parameters(url,['version']);if(!s.manifest.countries.includes(m[1]))fail(404,'coverage_not_available','US_GB_pilot_only');return await object(env,s.prefix+'/country/'+m[1]+'.json');}
 m=path.match(/^\/v1\/markets\/company\/([^/]+)$/);
 if(m){parameters(url,['version','page','limit']);let id;try{id=decodeURIComponent(m[1]);}catch{fail(400,'invalid_query','invalid_company_id');}
  if(!COMPANY.test(id))fail(400,'invalid_query','invalid_company_id');
  const key='company/'+id+'.json';const item=await env.MARKETS_BUCKET.get(s.prefix+'/'+key);if(!item)fail(404,'unknown_entity','company_not_in_pilot');const data=item.json?await item.json():parse(item);
  const page=integer(url,'page',1,10000),limit=integer(url,'limit',20,50),total=data.reported_relationships.length;
  if(page>1&&(page-1)*limit>=total)fail(400,'page_out_of_range','no_relationships_at_requested_page');
  const relations=data.reported_relationships.slice((page-1)*limit,page*limit);
  return {...data,legal_entity:{...data.legal_entity,reported_relationships:relations},reported_relationships:relations,relationship_total:total,page,limit,next_page:page*limit<total?page+1:null};
 }
 m=path.match(/^\/v1\/markets\/connections\/([A-Z]{2})$/);
 if(m){parameters(url,['page','limit','version']);if(!s.manifest.countries.includes(m[1]))fail(404,'coverage_not_available','US_GB_pilot_only');
  const page=integer(url,'page',1,10000),limit=integer(url,'limit',20,50);const data=await object(env,s.prefix+'/connections/'+m[1]+'.json');
  const total=data.corporate.length;if(page>1&&(page-1)*limit>=total)fail(400,'page_out_of_range','no_connections_at_requested_page');return {...data,corporate:data.corporate.slice((page-1)*limit,page*limit),currency:data.currency.slice(0,5),
   corporate_total:total,currency_total:data.currency.length,page,limit,next_page:page*limit<total?page+1:null};
 }
 if(/^\/v1\/markets\/(country|connections)\//.test(path))fail(400,'invalid_query','country_requires_uppercase_ISO2');
 fail(404,'not_found','unknown_markets_route');
}
export async function handleMarkets(req,env,ctx={waitUntil:()=>{}}){
 if(env.MARKETS_API_ENABLED!=='true')return error(404,'not_found','markets_API_disabled');
 if(req.method==='OPTIONS')return new Response(null,{status:204,headers:{'Access-Control-Allow-Methods':'GET, OPTIONS'}});
 if(req.method!=='GET')return error(405,'method_not_allowed','read_only_API');
 const url=new URL(req.url);const cache=globalThis.caches?.default;const key=new Request(url.toString());
 try{
  const s=await snapshot(env);const versioned=new Request(url.toString()+(url.search?'&':'?')+'__markets_version='+s.manifest.version);
  const hit=cache?await cache.match(versioned):null;
  if(hit){const body=await hit.json();body.meta=metadata(s);if(req.headers.get('If-None-Match')===hit.headers.get('ETag')&&!s.stale)return new Response(null,{status:304,headers:hit.headers});return new Response(JSON.stringify(body),{status:200,headers:hit.headers});}
  const data=await route(url,env,s);const body={data,meta:metadata(s)};
  const etag='"'+s.manifest.version+'-'+url.pathname.replace(/\W/g,'')+'-'+url.search+'"';
  const result=response(200,body,{'ETag':etag,'X-Markets-Cached-At':String(Date.now())});
  if(cache)ctx.waitUntil(Promise.all([cache.put(versioned,result.clone()),cache.put(key,result.clone())]));
  if(req.headers.get('If-None-Match')===etag)return new Response(null,{status:304,headers:result.headers});
  return result;
 }catch(e){
  if(e instanceof ApiError)return error(e.status,e.code,e.reason);
  const old=cache?await cache.match(key):null;
  if(old&&Date.now()-Number(old.headers.get('X-Markets-Cached-At'))<=24*3600e3){
   const body=await old.json();body.meta={...body.meta,stale:true,reason:'upstream_unavailable_last_good'};return response(200,body,{'Cache-Control':'public, max-age=60'});
  }
  return error(503,'no_valid_snapshot','markets_snapshot_or_storage_unavailable');
 }
}
