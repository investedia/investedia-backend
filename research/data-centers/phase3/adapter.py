"""Isolated Data Centers adapter; never writes or invokes Energy/production code.
Normalized project shape is shared; economic role labels remain sector-specific.
"""
import copy,json,math,re,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
CATEGORIES={
 'verified_direct_property_ownership':'Direct property ownership verified',
 'verified_subsidiary_or_jv_ownership':'Subsidiary/JV property ownership verified',
 'verified_listed_company_development':'Company-confirmed development exposure',
 'verified_lease_or_operational_exposure':'Company-confirmed lease/operating exposure',
 'verified_contractual_exposure':'Company-confirmed contractual exposure',
 'research_only_affiliation':'Research-only affiliation',
 'qualified_group_ownership':'Issuer-reported group ownership; legal title chain unresolved'}

def classify(record):
 claims=record.get('economic_relationships',[])
 if not claims:return 'research_only_affiliation'
 roles={c['role'] for c in claims}
 proof=record.get('direct_title_evidence')
 title_valid=isinstance(proof,dict) and proof.get('record_id')==record['id'] and proof.get('owner_registry_id')==record.get('company') and bool(re.fullmatch('[0-9a-f]{64}',proof.get('source_sha256',''))) and str(proof.get('source_url','')).startswith('https://') and bool(proof.get('locator'))
 if title_valid and record.get('legal_property_owner')==record.get('company'):
  return 'verified_direct_property_ownership'
 chain=record.get('project_ownership_chain')
 chain_valid=isinstance(chain,list) and bool(chain) and all(isinstance(e,dict) and e.get('scope')=='specific_property' and e.get('record_id')==record['id'] and bool(re.fullmatch('[0-9a-f]{64}',e.get('source_sha256',''))) and str(e.get('source_url','')).startswith('https://') for e in chain)
 if chain_valid and record.get('property_chain_verified') is True:
  return 'verified_subsidiary_or_jv_ownership'
 if record.get('contracted_revenue') and record.get('scope')=='campus development':
  return 'verified_contractual_exposure'
 if record.get('project_type')!='existing_asset' and roles & {'developer','investor','property_owner'}:
  return 'verified_listed_company_development'
 if 'operator' in roles or 'lessee' in roles:
  return 'verified_lease_or_operational_exposure'
 if 'property_owner' in roles:return 'qualified_group_ownership'
 return 'research_only_affiliation'

def image_allowed(location):return location.get('precision')=='exact' and location.get('exact_site_verified') is True

def fact_digest(record):return hashlib.sha256(json.dumps(record,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def normalize(record,company,location,hq,release,for_public=False):
 if for_public:
  review=release.get('review',{})
  if (not release.get('eligible') or release.get('blockers') or release.get('rights_status')!='cleared' or release.get('contract_status')!='approved' or review.get('record_id')!=record['id'] or review.get('fact_sha256')!=fact_digest(record) or not review.get('reviewer') or not review.get('reviewed_at') or not review.get('basis')):raise ValueError('Record not cleared for public export')
 if not company.get('listing_verified') or company.get('security_type')!='common_equity':raise ValueError('Current common equity not verified')
 if location.get('precision') not in ('city_reference','exact'):raise ValueError('Unclassified location')
 if location.get('precision')=='exact' and not (location.get('exact_site_verified') is True and isinstance(location.get('site_evidence'),dict) and location['site_evidence'].get('record_id')==record['id'] and location['site_evidence'].get('source_sha256')):raise ValueError('City pin cannot become an exact site by changing its label')
 if location.get('precision')=='city_reference' and (location.get('licence')!='CC0 1.0' or not location.get('source_url','').startswith('https://www.wikidata.org/entity/Q')):raise ValueError('City-reference source/rights not verified')
 for field in ('lat','lon'):
  if not isinstance(location.get(field),(float,int)) or not math.isfinite(location[field]):raise ValueError('Invalid coordinates')
 if abs(location['lat'])>90 or abs(location['lon'])>180:raise ValueError('Coordinate outside world')
 if location.get('precision')=='city_reference' and location.get('country_qid')!={'US':'Q30','ES':'Q29','SG':'Q334'}.get(record.get('country_code')):raise ValueError('City reference does not match checked project country')
 cat=classify(record)
 if cat=='research_only_affiliation':raise ValueError('Affiliation is not an investment relationship')
 sources=[]
 for c in record.get('economic_relationships',[]):
  e=c['evidence'];sources.append({'name':'Official issuer/company evidence','url':e['url'],'checked_at':e['retrieved_at'][:10],'locator':e['locator']})
 for key in ('source_evidence','status_evidence'):
  if record.get(key):
   e=record[key];sources.append({'name':'Official project evidence','url':e['url'],'checked_at':e['retrieved_at'][:10],'locator':e['locator']})
 sources.append({'name':'Wikidata (CC0) city reference','url':location['source_url'],'checked_at':location['checked_at']})
 roles=[c['role'] for c in record.get('economic_relationships',[])]
 role_labels=['Issuer-reported group-owned; legal title entity unverified' if r=='property_owner' else r.replace('_',' ') for r in roles]
 maturity='planned operating role; not confirmed open' if record['id']=='project:coresite:DE3' else 'source-qualified disclosed role'
 exposure={'ticker':company['ticker'],'exchange':company['mic'],'name':company['name'],'category':cat,'category_label':CATEGORIES[cat],
  'role':roles,'role_labels':role_labels,'maturity':maturity,'direct':False,'path':[company['name']],'stake':None,'stake_note':'No property percentage established. Business/JV shares remain scoped separately.',
  'hq':copy.deepcopy(hq),'evidence':sources,'investment_route':copy.deepcopy(record['investment_route'])}
 result={'id':record['id'],'name':record['name'],'country':{'US':'United States','ES':'Spain','SG':'Singapore'}.get(record.get('country_code'),record.get('country_code')),'cc':record.get('country_code'),
  'location':location.get('label') or record.get('city') or record.get('address'),'reported_project_area':record.get('city'),'lat':location['lat'],'lon':location['lon'],'sector':'Data Centers','type':'Data Centers',
  'energy':None,'stage':record.get('status'),'expected_completion':record.get('expected_completion'),'start_year':None,'status_year':None,'milestones':[],
  'sources':sources,'featured':False,'verified':True,'capacity':copy.deepcopy(record.get('capacity')),
  'cost':copy.deepcopy(record.get('cost')) if record.get('cost',{} ) and record['cost'].get('currency') else None,
  'owners':[],'listed':None,'listed_exposure':{'ticker':company['ticker'],'name':company['name'],'role':roles},
  'location_accuracy':copy.deepcopy(location),'invest':{'exposures':[exposure],'precision':location['precision'],'stage_note':record.get('target_warning')},
  'satellite':None,'photo':None,'images':[],'imagery_status':'not used; city-level reference cannot generate site imagery',
  'release':copy.deepcopy(release),'local_research_preview':not for_public,
  'relationship_notes':record.get('source_conflicts',[]),'business_jv':copy.deepcopy(record.get('jv'))}
 # Never fill the legacy `listed owner` object for an economic exposure, even a grouped-owner report.
 # The live legacy formatter would otherwise describe a lessee/operator/developer as the listed owner.
 return result
