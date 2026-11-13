"""Research-local cross-sector contract. No production imports, mutations or uploads.
The legacy Energy result is preserved separately and never rewritten by this module.
"""
import copy,hashlib,json,math,re

SCHEMA='investedia.projects.sector-envelope.proposal.v2'
SECTORS={'energy':'Energy','data_centers':'Data Centers','real_estate':'Real Estate'}
ROLES={'direct_property_owner','indirect_property_owner','reported_group_owner','developer','operator','lessee','investor','contractor','affiliation'}
ROUTES={'public_equity','listed_REIT','listed_stapled_security','verified_fund','research_only'}
ASSETS={'project','campus','building','existing_asset','programme'}
STAGES={'announced','planning','under_construction','expanding','operating','completed','unknown'}

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def https(value):return isinstance(value,str) and value.startswith('https://') and not re.search(r'https://[^/]*@',value)
def evidence_valid(e):return isinstance(e,dict) and https(e.get('url')) and bool(e.get('locator')) and bool(re.fullmatch('[a-f0-9]{64}',e.get('sha256',''))) and bool(e.get('checked_at'))

def validate(record,sectors=None):
 sectors=sectors or SECTORS
 if record.get('schema')!=SCHEMA:raise ValueError('Unrecognized proposed schema')
 if record.get('sector') not in sectors:raise ValueError('Sector needs an explicit registered label')
 if not record.get('id') or not record.get('name'):raise ValueError('Project identity missing')
 asset=record['asset']
 if asset['category'] not in ASSETS or asset.get('parent_id')==record['id']:raise ValueError('Asset category or parent invalid')
 if asset.get('category')=='programme' and asset.get('count_as_project'):raise ValueError('Programme is not an individual project')
 if asset.get('category')=='building' and not asset.get('building_identity_evidence'):raise ValueError('Building requires scoped identity evidence')
 if not evidence_valid(record.get('identity_evidence')):raise ValueError('Identity must retain documentary provenance')
 status=record['status']
 if status['stage'] not in STAGES or not status.get('as_of') or not status.get('label'):raise ValueError('Invalid status')
 loc=record['location'];precision=loc['precision']
 if precision not in {'exact','approximate','unknown'}:raise ValueError('Explicit geographic precision required')
 if precision=='unknown':
  if loc.get('lat') is not None or loc.get('lon') is not None:raise ValueError('Unknown point cannot carry coordinates')
 else:
  if not all(type(loc.get(k)) in (int,float) and math.isfinite(loc[k]) for k in ('lat','lon')) or abs(loc['lat'])>90 or abs(loc['lon'])>180:raise ValueError('Invalid coordinates')
  if not loc.get('basis') or not evidence_valid(loc.get('evidence')):raise ValueError('Geographic evidence missing')
  if precision=='exact' and (loc.get('evidence',{}).get('record_id')!=record['id'] or loc.get('evidence',{}).get('scope')!='specific_site'):raise ValueError('Exact point requires record-bound site evidence')
  if precision=='approximate' and not loc.get('label'):raise ValueError('Approximate point requires visible label')
 if loc.get('satellite_allowed') and precision!='exact':raise ValueError('Approximate/unknown points cannot request site imagery')
 for image in record.get('imagery',[]):
  if not https(image.get('source_url')) or image.get('rights_status')!='cleared' or not image.get('licence') or not image.get('credit') or image.get('project_id')!=record['id']:raise ValueError('Image must have identified project and cleared rights')
  if image.get('type')=='satellite' and (precision!='exact' or not loc.get('satellite_allowed')):raise ValueError('Site imagery requires a verified exact point')
 for e in record['exposures']:
  if e['role'] not in ROLES or not e.get('relationship_scope'):raise ValueError('Economic role scope required')
  if not evidence_valid(e.get('evidence')):raise ValueError('Economic relationship evidence required')
  if e.get('property_stake') is not None:
   if e.get('stake_scope')!='specific_property' or not 0<=e['property_stake']<=100 or not evidence_valid(e.get('property_evidence')) or e['property_evidence'].get('record_id')!=record['id']:raise ValueError('Company/JV percentage is not property stake')
  if e['role'] in {'direct_property_owner','indirect_property_owner'}:
   proof=e.get('property_evidence',{})
   if proof.get('record_id')!=record['id'] or proof.get('scope')!='specific_property' or not evidence_valid(proof):raise ValueError('Property ownership requires per-property proof')
   if e['role']=='indirect_property_owner':
    chain=e.get('property_chain')
    if not isinstance(chain,list) or not chain or not all(isinstance(edge,dict) and edge.get('record_id')==record['id'] and edge.get('scope')=='specific_property' and edge.get('from') and edge.get('to') and evidence_valid(edge.get('evidence')) for edge in chain):raise ValueError('Indirect property ownership requires sourced per-property chain')
  if e['role']=='affiliation' and e.get('investment_access',{}).get('verified'):raise ValueError('Affiliation is not verified investment exposure')
  listing=e.get('listing');access=e['investment_access']
  if access['type'] not in ROUTES:raise ValueError('Unknown investment route')
  if access.get('verified'):
   if not listing or not listing.get('ticker') or not listing.get('exchange') or not listing.get('security_type') or not evidence_valid(listing.get('evidence')):raise ValueError('Verified access needs current documented listing')
   if access['type']=='listed_stapled_security' and listing['security_type']!='stapled_security':raise ValueError('Stapled security must not be called common stock')
  hq=e.get('headquarters')
  if hq:
   if hq.get('precision') not in {'exact','approximate'} or not evidence_valid(hq.get('evidence')):raise ValueError('HQ precision/evidence required')
   if hq['precision']=='exact' and not hq['evidence'].get('specific_office'):raise ValueError('City cannot become exact office')
   if not all(type(hq.get(k)) in (int,float) and math.isfinite(hq[k]) for k in ('lat','lon')) or abs(hq['lat'])>90 or abs(hq['lon'])>180:raise ValueError('Invalid HQ point')
 # Each publishable field needs its own disposition. No self-declared eligible boolean.
 for field,decision in record['reuse']['fields'].items():
  if decision.get('status') not in {'cleared','pending','omit'} or not decision.get('basis'):raise ValueError('Field reuse basis missing')
 return True

def public_projection(record):
 validate(record)
 if record['verification']['classification'] not in {'company_confirmed','regulator_confirmed'}:raise ValueError('Research affiliation not publishable')
 if not record['exposures'] or not any(e['investment_access'].get('verified') for e in record['exposures']):raise ValueError('No verified investment route')
 fields=record['reuse']['fields']
 required={'identity','status','economic_relationship','listing','location'}
 if not required.issubset(fields) or any(fields[k]['status']!='cleared' for k in required):raise ValueError('Required factual reuse unresolved')
 if any(d['status']=='pending' for d in fields.values()):raise ValueError('Pending fields cannot enter release')
 review=record['reuse'].get('review',{})
 fact=copy.deepcopy(record);fact.pop('reuse',None);fact.pop('legacy_energy',None)
 if review.get('fact_sha256')!=digest(fact) or not review.get('reviewer') or not review.get('date') or not review.get('basis'):raise ValueError('Record-bound reuse review required')
 out=copy.deepcopy(record)
 for key,d in fields.items():
  if d['status']=='omit':out.pop(key,None)
 out.pop('legacy_energy',None)
 return out

def wrap_energy(raw,normalized,source_receipt):
 """Preserve the existing normalizer byte-for-byte in legacy_energy; sidecar only."""
 r=raw;src=r['source'];identity={'url':src['url'],'sha256':source_receipt['sha256'],'checked_at':source_receipt['as_of'],'locator':'Existing verified Energy record '+r['id'],'sha256_scope':'verified_input_snapshot','snapshot_commit':source_receipt['commit'],'snapshot_path':'assets/globe/projects-invest.json'}
 precision='exact' if r.get('precision')=='exact' else 'approximate' if r.get('lat') is not None else 'unknown'
 loc={'precision':precision,'lat':r.get('lat'),'lon':r.get('lon'),'label':r.get('name'),'basis':'Existing approved Energy verification; inherited without new site audit','satellite_allowed':False,'evidence':{**identity,'record_id':r['id'],'scope':'specific_site' if precision=='exact' else 'source_reference'}}
 exposures=[]
 for e in r.get('exposures',[]):
  v=e.get('verification',{});listing=v.get('listing',{});links=v.get('link',[]);link=next((x for x in links if x.get('url')),None)
  if not link:continue
  ev={'url':link['url'],'sha256':source_receipt['sha256'],'checked_at':v.get('verified_at') or source_receipt['as_of'],'locator':'Inherited verified Energy evidence chain; source record '+r['id'],'sha256_scope':'verified_input_snapshot','snapshot_commit':source_receipt['commit']}
  parent={'name':e.get('listed_name') or v.get('identity',{}).get('legal_name'),'ticker':listing.get('ticker'),'exchange':{'NYSE':'XNYS','Nasdaq':'XNAS'}.get(listing.get('exchange'),listing.get('exchange')),'exchange_mic':{'NYSE':'XNYS','Nasdaq':'XNAS'}.get(listing.get('exchange')),'exchange_name':listing.get('exchange'),'security_type':'common_equity','evidence':{'url':listing.get('source_url') or link['url'],'sha256':source_receipt['sha256'],'checked_at':listing.get('checked_at') or source_receipt['as_of'],'locator':'Existing Energy listing verification','sha256_scope':'verified_input_snapshot','snapshot_commit':source_receipt['commit']}}
  # Preserve legacy ownership proof, but do not independently re-certify real-estate title here.
  h=e.get('hq');hq=None
  if h:hq={'city':h.get('city'),'lat':h['lat'],'lon':h['lon'],'precision':'approximate','evidence':{'url':h['source_url'],'sha256':source_receipt['sha256'],'checked_at':h.get('checked_at') or source_receipt['as_of'],'locator':'Inherited CC0 HQ city from Energy evidence','sha256_scope':'verified_input_snapshot','snapshot_commit':source_receipt['commit']}}
  exposures.append({'role':'reported_group_owner','label':'Existing verified Energy ownership chain; legacy classification preserved','relationship_scope':'generator/plant ownership under existing Energy rules, not new real-estate title certification','property_stake':None,'verification':copy.deepcopy(v),'listing':parent,'evidence':ev,'headquarters':hq,'investment_access':{'type':'public_equity','verified':True,'scope':'Indirect company equity; no direct project purchase'}})
 stage_label=r.get('stage','').lower()
 stage='planning' if 'pre-construction' in stage_label else 'under_construction' if 'construction' in stage_label or 'commissioning' in stage_label else 'announced' if 'announced' in stage_label else 'operating' if 'operating' in stage_label else 'unknown'
 categories={e.get('verification',{}).get('category') for e in r.get('exposures',[])}
 classification='company_confirmed' if categories=={'A'} else 'regulator_confirmed' if categories=={'B'} else 'mixed_company_and_regulator'
 out={'schema':SCHEMA,'id':r['id'],'name':r['name'],'sector':'energy','country_code':r['cc'],'city':None,'asset':{'category':'project','subtype':r.get('kind'),'parent_id':None,'count_as_project':True},'status':{'stage':stage,'label':r.get('stage') or 'Unknown','as_of':source_receipt['as_of']},'location':loc,'identity_evidence':identity,'exposures':exposures,'imagery':[],'verification':{'classification':classification,'inherited_categories':sorted(categories),'basis':'Existing Energy verification retained; not re-reviewed in Phase4'},'reuse':{'status':'inherited_existing_energy','fields':{'identity':{'status':'cleared','basis':src.get('licence','Existing published Energy source')}},'review':None},'legacy_energy':copy.deepcopy(normalized),'preview_only':True}
 validate(out);return out

def wrap_dc(p,record,company,city_receipt):
 identity=p['sources'][0];claims=record['economic_relationships'];sources=record.get('source_evidence') or claims[0]['evidence']
 def ev(e):return {'url':e['url'],'sha256':e.get('response_sha256') or e.get('sha256'),'checked_at':e.get('retrieved_at',e.get('checked_at')),'locator':e['locator']}
 exposures=[]
 rolemap={'property_owner':'reported_group_owner','developer':'developer','operator':'operator','lessee':'lessee','investor':'investor','contractor':'contractor'}
 for c in claims:
  e0=copy.deepcopy(p['invest']['exposures'][0]);l=company['security_class_evidence'];hq=e0.get('hq')
  h={'city':hq['city'],'lat':hq['lat'],'lon':hq['lon'],'precision':'approximate','evidence':{'url':hq['source_url'],'sha256':city_receipt['hq_sha256'],'checked_at':hq['checked_at'],'locator':'Existing CC0 HQ city reference','sha256_scope':'local_reference_file','snapshot_path':'../phase3/headquarters-references.json'}} if hq else None
  ex={'role':rolemap[c['role']],'label':c.get('qualified_label') or c['role'],'relationship_scope':record.get('relationship_scope') or 'specific named facility operating exposure','maturity':'planned' if record['id'].endswith('DE3') else 'reported','property_stake':None,'listing':{'name':company['name'],'ticker':company['ticker'],'exchange':company['mic'],'exchange_mic':company['mic'],'security_type':'common_equity','evidence':{'url':l['url'],'sha256':l['sha256'],'checked_at':company['listing_checked_at'],'locator':'Cover securities table: common equity ticker and exchange'}},'evidence':ev(c['evidence']),'headquarters':h,'investment_access':{'type':'listed_REIT','verified':True,'scope':'Indirect listed-company equity exposure; no direct property purchase'}}
  if c.get('chain_evidence'):ex['parent_chain_evidence']=ev(c['chain_evidence'])
  exposures.append(ex)
 loc=p['location_accuracy'];location={'precision':'approximate','lat':loc['lat'],'lon':loc['lon'],'label':loc['label']+' city reference','basis':'Verified city, not facility footprint','satellite_allowed':False,'evidence':{'url':loc['source_url'],'sha256':city_receipt['city_sha256'],'checked_at':loc['checked_at'],'locator':'Wikidata QID/country/P625 checked city reference','sha256_scope':'local_reference_file','snapshot_path':'../phase3/city-references.json'}}
 isbuilding='building' in record.get('scope','')
 asset={'category':'building' if isbuilding else 'project','subtype':'Data center development','parent_id':None,'count_as_project':True}
 if isbuilding:asset['building_identity_evidence']=ev(sources)
 out={'schema':SCHEMA,'id':p['id'],'name':p['name'],'sector':'data_centers','country_code':p['cc'],'city':p['location'],'asset':asset,'status':{'stage':'under_construction' if record['id'].endswith('DE3') else 'operating','label':p['stage'],'as_of':record.get('status_as_of') or '2026-11-13','certainty':'target_only_current_completion_unknown' if record['id'].endswith('DE3') else 'company_reported'},'location':location,'identity_evidence':ev(sources),'exposures':exposures,'imagery':[],'verification':{'classification':'company_confirmed','date':'2026-11-13','property_title_verified':False},'reuse':{'fields':{},'review':None},'preview_only':True,'reported_metrics':{'capacity':p.get('capacity'),'cost':p.get('cost'),'historic_expected_completion':p.get('expected_completion')},'notes':record.get('source_conflicts',[])}
 # A target is not a verified construction stage. Preserve uncertainty explicitly.
 if record['id'].endswith('DE3'):out['status']['stage']='unknown'
 if record['id'].endswith('NY3'):
  out['status'].update(stage='operating',label='Operating facility, company-reported; launched 25 September 2025',evidence={'url':'https://www.coresite.com/data-center/ny3-secaucus-nj','sha256':'0844383897fd1375018dd54d970f787f9e76f2d5f29c41398392892833dae52a','checked_at':'2026-11-13','locator':'Current NY3 service page, named facility and operating services; checked separately from launch announcement'})
 for k in ('identity','status','economic_relationship'):out['reuse']['fields'][k]={'status':'pending','basis':'Source-specific corporate factual reuse/access conditions unresolved; no whole tables/prose copied'}
 for k in ('listing','location'):out['reuse']['fields'][k]={'status':'cleared','basis':'Owner-approved narrow SEC identifiers / Wikidata CC0 city facts, attribution retained'}
 out['reuse']['fields']['reported_metrics']={'status':'omit','basis':'Not needed for minimal discovery release; corporate scope/currency conflicts retained internally'}
 validate(out);return out


def validate_bundle(records,sectors=None):
 """Cross-record checks keep context, campus and building counts distinct."""
 ids={r['id'] for r in records}
 if len(ids)!=len(records):raise ValueError('Duplicate project identities')
 lookup={r['id']:r for r in records}
 for r in records:
  validate(r,sectors)
  seen={r['id']};parent=r['asset'].get('parent_id')
  while parent in lookup:
   if parent in seen:raise ValueError('Cyclic project/campus hierarchy')
   seen.add(parent);p=lookup[parent]
   if r['asset']['count_as_project'] and p['asset']['category']=='campus' and p['asset']['count_as_project']:raise ValueError('Campus total cannot also count child buildings as additive projects')
   parent=p['asset'].get('parent_id')
 return True
