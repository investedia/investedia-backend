"""Small manual evidence-reviewed pilot; no directory-wide import or external writes."""
import json
from pathlib import Path
from sector_adapter import SCHEMA,validate,validate_bundle
P=Path(__file__).resolve().parent

def receipt(n):return json.loads((P/'sources'/f'{n}.receipt.json').read_text())
def evidence(n,locator):
 r=receipt(n)
 if r.get('status')!=200:raise ValueError('Source unavailable: '+n)
 return {'url':r['url'],'sha256':r['sha256'],'checked_at':r['retrieved_at'],'locator':locator}

def build():
 # Short original factual observations, not source descriptions or copied portfolio tables.
 reviewed=[
 ('segro-bologna','SEGRO Bologna Interport delivered building','SEGRO','IT','Bologna','building','completed','Company reports delivery on 2 November 2026','developer','Named delivery announcement: SEGRO built and delivered a new logistics building',None),
 ('segro-northern-italy','SEGRO Calvenzano logistics development','SEGRO','IT','Calvenzano','building','under_construction','Work started; completion targeted November 2027, not guaranteed','developer','15 October 2026 announcement: SEGRO construction start, Calvenzano municipality',None),
 ('wdp-hazeldonk-project','WDP LogiLink Hazeldonk redevelopment','WDP','NL','Breda / Hazeldonk','project','unknown','Company markets redevelopment and future availability; construction milestone not independently confirmed','developer','Named project description: redevelopment by WDP, multi-tenant logistics facility',None),
 ('montea-quartz','Logistic Park Glassworks DC Quartz','Montea','NL','Tiel','building','unknown','Company reports leased building and remaining availability; leasing is not an operating-status audit','affiliation','Named DC Quartz page, location Tiel, leased status and redevelopment context','campus:montea:glassworks'),
 ('montea-silica','Logistic Park Glassworks DC Silica','Montea','NL','Tiel','building','planning','Land for development; planned warehouse, not confirmed construction','affiliation','Distinct named DC Silica page; land-for-development label','campus:montea:glassworks'),
 ('montea-combronde',"Combronde ZAC du Parc de l’Aize development land",'Montea','FR','Combronde','project','planning','Land for development, company-reported','affiliation','Named address/site and land-for-development label',None),
 ('montea-echt','Echt Fahrenheitstraat development land','Montea','NL','Echt','project','planning','Future brownfield potential subject to planning; no construction claim','affiliation','Named site and planning/permitting qualification',None),
 ('montea-puurs','Puurs Rijksweg 85–89 development site','Montea','BE','Puurs','project','planning','Marketed build-to-suit opportunity; no construction start established','affiliation','Named address and land-for-development classification',None),
 ('montea-lummen','Lummen Dellestraat 20 Lumineus','Montea','BE','Lummen','project','planning','Marketed build-to-suit opportunity; no construction start established','affiliation','Named Lumineus project and Dellestraat 20 address',None),
 ('montea-grimbergen','Grimbergen Oostvaartdijk development site','Montea','BE','Grimbergen','project','planning','Company markets land for development; exact stage unresolved','affiliation','Named Oostvaartdijk site and land-for-development classification',None)]
 rows=[]
 for n,name,co,cc,city,category,stage,label,role,locator,parent in reviewed:
  ev=evidence(n,locator);asset={'category':category,'subtype':'Logistics real estate','parent_id':parent,'count_as_project':True}
  if category=='building':asset['building_identity_evidence']=ev
  r={'schema':SCHEMA,'id':'re:'+n,'name':name,'sector':'real_estate','country_code':cc,'city':city,'asset':asset,'status':{'stage':stage,'label':label,'as_of':'2026-11-13'},'location':{'precision':'unknown','lat':None,'lon':None,'label':city+'; no checked point','satellite_allowed':False},'identity_evidence':ev,'exposures':[{'role':role,'label':'Company-confirmed developer' if role=='developer' else 'Portfolio affiliation only; economic role not established','relationship_scope':'Specific named development' if role=='developer' else 'Company markets this property; title, lessor and development entity unresolved','property_stake':None,'listing':None,'evidence':ev,'headquarters':None,'investment_access':{'type':'research_only','verified':False,'scope':'Current security mapping/asset-level chain pending; no investable property route asserted'}}],'imagery':[],'verification':{'classification':'company_confirmed' if role=='developer' else 'research_only_affiliation','property_title_verified':False,'company':co},'reuse':{'fields':{k:{'status':'pending','basis':'Source-specific commercial factual reuse/access/database conditions unresolved'} for k in ['identity','status','economic_relationship','listing','location']},'review':None},'preview_only':True,'blockers':['commercial_reuse_pending','current_listing_mapping_pending','exact_economic_chain_pending','coordinates_unverified']+(['economic_role_not_proven'] if role=='affiliation' else [])}
  validate(r);rows.append(r)
 companies=[
 {'name':'Prologis','documents':['prologis-investors','prologis-presentation','prologis-sec'],'result':'Issuer listing PLD on NYSE confirmed by current SEC submissions; accessible presentation/supplement contain regional/portfolio aggregates, not enough to create named property ownership links. Corporate development/UK property URLs returned HTTP405.','property_records':0,'listing_verified':True,'listing':{'ticker':'PLD','mic':'XNYS','security_type':'common_equity','evidence':evidence('prologis-sec','SEC submissions tickers/exchanges: PLD/NYSE')},'next_step':'Use an accessible official project announcement or property-specific planning/ownership document; no regional aggregate becomes a property.'},
 {'name':'SEGRO','documents':['segro-bologna','segro-northern-italy','segro-disclaimer'],'result':'Two specifically named developer relationships verified; no property title or stake established. Official release confirms company REIT/listed status; exact current ticker/MIC mapping remains pending after guessed share URL404.','property_records':2,'listing_verified':False},
 {'name':'Goodman Group','documents':['goodman-q1fy27','goodman-portfolio','goodman-terms'],'result':'Official Q1 FY27 logistics discussion is aggregate; named project table concerns Data Centers, not logistics properties. Public property page is script-only in this request. No invented property rows. Preserve stapled-security distinction; current security URL404.','property_records':0,'listing_verified':False,'next_step':'Seek official property-level logistics case study and current ASX stapled-security evidence; do not use portfolio totals or DC projects as Real Estate pilot properties.'},
 {'name':'WDP','documents':['wdp-hazeldonk','wdp-hazeldonk-project','wdp-share','wdp-disclaimer'],'result':'One specific redevelopment relationship verified, no title/stake. Official share page confirms Euronext listings; precise current share class/ticker/MIC mapping still requires identifier evidence.','property_records':1,'listing_verified':False},
 {'name':'Montea','documents':['montea-quartz','montea-silica','montea-share','montea-disclaimer','montea-italy'],'result':'Seven property-specific candidates; portfolio marketing is not ownership/developer proof. Share page links BE0003853703-XBRU; no live price data consumed. Italy transaction is separate context, not ten verified properties or a completed-acquisition claim.','property_records':7,'listing_verified':False}]
 pld=json.loads((P/'prologis-listing.json').read_text());assert 'PLD' in pld['tickers'] and 'NYSE' in pld['exchanges']
 validate_bundle(rows)
 out={'schema':'investedia.real-estate.pilot.research.v1','prerequisites':{'sector_adapter_tests_passed':True,'five_dc_candidate_reviews_completed':True,'production_approval':False},'counts':{'property_candidates':len(rows),'verified_specific_developer_relationships':3,'portfolio_affiliations_only':7,'verified_property_ownership':0,'verified_property_investment_routes':0,'public_release_eligible':0,'companies_with_property_candidates':3,'companies_source_audited':5},'companies':companies,'projects':rows,'notice':'Internal verification pilot. Ten reviewed candidates are not ten verified investments. Not investment advice.'}
 (P/'real-estate-pilot.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out['counts']))
 return out
if __name__=='__main__':build()
