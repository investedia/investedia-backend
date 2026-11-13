"""Offline enrichment sidecar. Original batch, shared schemas and production remain untouched."""
import copy,datetime as dt,hashlib,html,json,re
from pathlib import Path
P=Path(__file__).resolve().parent
BASE=P.parent
ROOT=BASE.parents[1]
def read(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def evidence(source,locator,sources):
 s=sources[source]
 return {'source':source,'url':s['url'],'response_sha256':s['sha256'],'retrieved_at':s['retrieved_at'],'locator':locator,'publication_date':s.get('publication_date')}

def validate_relationship(claim,record,companies):
 if claim['record_id']!=record['id']:raise ValueError('Cross-project evidence')
 co=companies.get(claim['company_id'])
 if not co or co.get('security_type')!='common_equity' or not co.get('listing_verified'):raise ValueError('Unverified investment-route target')
 if claim['role'] not in ('property_owner','developer','operator','lessee','investor','contractor'):raise ValueError('Invalid economic role')
 if claim['role'] not in record.get('documented_roles',[]):raise ValueError('Role not established in the record-level manual evidence review')
 if not claim.get('evidence') or not claim['evidence'].get('response_sha256') or not claim['evidence'].get('locator'):raise ValueError('Unbound claim')
 if claim.get('scope')!='specific_record':raise ValueError('Aggregate business share cannot become a property claim')
 if claim.get('ownership_pct') is not None and not claim.get('percentage_evidence_scope')==record['id']:raise ValueError('Percentage is not documented for this record')
 if claim['role']=='property_owner' and not record.get('ownership_classification')=='issuer-reported owned':raise ValueError('No record-level ownership evidence')
 if claim['role']=='lessee' and record.get('ownership_classification')!='issuer-reported leased':raise ValueError('No record-level lease evidence')
 if claim.get('inference') in ('proximity','shareholder','company_brand','aggregate','financial_category_is_construction'):raise ValueError('Unsupported relationship inference')
 return True

def route(company):
 if not company.get('listing_verified'):return {'type':'research_only','verified':False}
 return {'type':'listed_REIT' if company.get('reit_verified') else 'public_equity','verified':True,'scope':'indirect company-level equity exposure; not direct project investment',
         'registry_asset_id':company.get('registry_asset_id'),'external_listing_id':company.get('external_listing_id'),'security_type':'common_equity','listing_as_of':company['listing_as_of']}

def owned_lease_claim(record,role,source,locator,sources):
 record['ownership_classification']='issuer-reported owned' if role=='property_owner' else 'issuer-reported leased'
 record['legal_property_owner']=None
 return {'record_id':record['id'],'company_id':record['company'],'role':role,'scope':'specific_record','ownership_pct':None,
  'qualified_label':'Issuer reports ownership; legal title entity unverified' if role=='property_owner' else 'Issuer reports leased facility; landlord/title owner unverified',
  'evidence':evidence(source,locator,sources),'verification_date':sources[source]['retrieved_at'][:10],'ownership_basis':'issuer asset schedule, not land registry'}

def derive():
 base=read(BASE/'dataset.json');pack=read(P/'evidence-packets.json');sources=read(P/'sources-index.json')
 for key,value in pack.items():
  if canonical(value['facts'])!=value['facts_sha256']:raise ValueError('Packet checksum mismatch: '+key)
 companies=pack['companies']['facts'];original=[];relations=[]
 for r in base['records']:
  row={'id':r['id'],'name':r['name'],'facility_code':r['facility_code'],'company':r['listed_company'],
       'project_type':'existing_asset','affiliation_verified':r['category']=='A','original_category':r['category'],
       'legal_property_owner':None,'operator':None,'developer':None,'listed_parent':r['listed_company'],
       'country_code':r.get('cc'),'address':r.get('address'),'coordinates':r.get('coordinates'),
       'ownership_classification':None,'jv':None,'status':None,'economic_relationships':[],
       'public_eligible':False,'phase2_review':{'sources_checked':['DLR-10k-full','DLR-latest-10q'] if r['listed_company']=='EQ:XNYS:DLR' else ['eqix-q3-presentation','EQIX-latest-10q'] if r['listed_company']=='EQ:XNAS:EQIX' else ['AMT-latest-10q','coresite-va1-current'],
       'disposition':'Portfolio affiliation only. Aggregate metro fee-simple/lease statements do not establish this facility’s legal owner/operator/developer. No financial upgrade.'}}
  if r['id'] in ('dc:eqix:DC2','dc:eqix:SV1','dc:eqix:DX1'):
   role='lessee' if r['facility_code']=='DX1' else 'property_owner'
   claim=owned_lease_claim(row,role,'eqix-q3-presentation','Portfolio Composition pp35–36, '+r['facility_code']+' in '+('Leased' if role=='lessee' else 'Owned')+' column',sources)
   row['economic_relationships']=[claim];row['status']='Portfolio-listed asset as of 2026-09-30; operating/construction stage not independently confirmed'
   row['phase2_review']['disposition']='Specific issuer asset schedule establishes '+role+' classification. No legal titleholder or 100% equity percentage inferred.'
   if r['facility_code']=='DC2':row['phase2_review']['financial_category']='Expansion in portfolio composition is a financial classification, not proof of an active construction phase.'
  if r['facility_code']=='VA1':
   row.update(affiliation_verified=True,operator='CoreSite',status='service facility; operational relationship documented; construction stage unverified',
     jv={'parent_business':'AMT US data center business','AMT_common_equity_pct':64,'Stonepeak_common_equity_pct':36,'as_of':'2026-09-30','scope':'business level only; not a facility stake'})
   row['phase2_review']['disposition']='CoreSite official specific service facility + current AMT subsidiary/business chain evidence; accepted indirect operating exposure. Property owner remains unknown.'
   row['economic_relationships']=[{'record_id':row['id'],'company_id':row['company'],'role':'operator','scope':'specific_record','ownership_pct':None,
    'qualified_label':'AMT indirect operating-business exposure via CoreSite, not title ownership',
    'evidence':evidence('coresite-va1-current','Official VA1 service facility / CoreSite operator',sources),'chain_evidence':evidence('AMT-latest-10q','Notes 1 and11; current US data center business control/Stonepeak conversion',sources)}]
  if r['category']=='D':row['phase2_review']['disposition']='Retained rejected original source-country contradiction; not corrected by guessing.'
  row['documented_roles']=[c['role'] for c in row['economic_relationships']]
  row['investment_route']=route(companies.get(row['company'],{}));original.append(row)
 projects=read(P/'reviewed-developments.json')
 for p in projects:
  p['affiliation_verified']=True;p['economic_relationships']=[];p['legal_property_owner']=None;p['investment_route']=route(companies.get(p['company'],{}));p['verification_date']=sources[p.get('status_source',p['source'])]['retrieved_at'][:10]
  claim={'record_id':p['id'],'company_id':p['company'],'role':p['economic_role'],'scope':'specific_record','ownership_pct':None,
         'evidence':evidence(p['source'],p['locator'],sources),'qualified_label':'Disclosed '+p['economic_role']+' exposure; property/phase/JV scope retained'}
  if p.get('ownership_classification')=='issuer-reported owned':claim=owned_lease_claim(p,'property_owner',p['ownership_evidence_source'],p['ownership_locator'],sources)
  if p['company']=='EQ:XNYS:AMT':claim['chain_evidence']=evidence('AMT-latest-10q','US operating business chain; separate minority development JV not assumed to be DE3',sources)
  claim['maturity']='announced_development_intent' if p['source']=='eqix-expansions' and p.get('economic_role')!='property_owner' else 'issuer_disclosed_economic_role'
  p['documented_roles']=[claim['role']]
  p['economic_relationships'].append(claim)
  p['source_evidence']=evidence(p['source'],p['locator'],sources)
  if p.get('status_source'):p['status_evidence']=evidence(p['status_source'],'Explicit facility opening announcement',sources)
  # Future target dates or an Expansion financial category cannot turn into completed construction.
  if p['status']=='announced' and p.get('expected_completion') and p['expected_completion']<'2026-Q4':p['target_warning']='Past target; no completion inferred'
 all_records=original+projects;ids=[r['id'] for r in all_records]
 if len(ids)!=len(set(ids)):raise ValueError('Duplicate canonical research record')
 for r in all_records:
  for c in r['economic_relationships']:validate_relationship(c,r,companies);relations.append(c)
 # Distinct record counts, not number of claims or one percentage repeated across buildings.
 economic={c['record_id'] for c in relations};ownership={c['record_id'] for c in relations if c['role']=='property_owner'}
 result={'schema':'investedia.data-centers.phase2-research.v1','notice':'Private research. No public licensing approval. Not investment advice.',
  'before':base['counts'],'companies':companies,'original_records':original,'development_records':projects,'relationships':relations,
  'business_chains':pack['business-chains']['facts'],
  'counts':{'reviewed_records':len(all_records),'additional_reviewed_records':len(projects),'verified_facility_affiliations_original':sum(r['affiliation_verified'] for r in original),
   'verified_economic_relationship_records':len(economic),'verified_economic_original_records':sum(r['id'] in economic for r in original),
   'verified_economic_asset_or_project_records':sum(r['id'] in economic for r in original)+sum(p['id'] in economic and p['count_as_project'] for p in projects),
   'economic_parent_or_programme_records_not_projects':sum(p['id'] in economic and not p['count_as_project'] for p in projects),
   'issuer_reported_ownership_relationship_records':len(ownership),'verified_legal_property_titleholders':0,
   'countable_development_or_phase_records':sum(p['count_as_project'] for p in projects),'noncounting_parent_or_programme_records':sum(not p['count_as_project'] for p in projects),
   'public_release_eligible_projects':0,'exact_sites_verified':0,'licensed_project_imagery':0},
  'integration':{'safe_public_records':[],'research_only_records':[r['id'] for r in all_records],
    'reasons':['Corporate-source commercial redistribution not approved','Exact sites/imagery unresolved','Shared schema and adapters not changed','APLD listing verified externally but registry mapping absent']}}
 (P/'phase2-dataset.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 (P/'preview/data.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
 (P/'network.json').write_text(json.dumps({'nodes':[{'id':r['id'],'kind':r['project_type']} for r in all_records]+list(companies.values()),'edges':relations,'business_chain_edges':result['business_chains'],'notice':result['notice']},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result['counts']))
 return result
if __name__=='__main__':derive()
