"""Isolated, offline facts/exposure audit. Never writes Projects, registry or shared pipelines."""
import copy,datetime as dt,hashlib,html,json,math,re
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
COUNTRIES={'USA':('US','North America'),'United States of America':('US','North America'),'Canada':('CA','North America'),'Brazil':('BR','Latin America'),'Mexico':('MX','Latin America'),'United Kingdom':('GB','Europe'),'Netherlands':('NL','Europe'),'Germany':('DE','Europe'),'France':('FR','Europe'),'Spain':('ES','Europe'),'Denmark':('DK','Europe'),'Japan':('JP','Asia'),'Singapore':('SG','Asia'),'Australia':('AU','Oceania'),'India':('IN','Asia'),'South Korea':('KR','Asia'),'South Africa':('ZA','Africa'),'Nigeria':('NG','Africa'),'Kenya':('KE','Africa'),'Mozambique':('MZ','Africa'),'Ghana':('GH','Africa'),'United Arab Emirates':('AE','Middle East')}
REGISTRY_IDS={'DLR':'EQ:XNYS:DLR','EQIX':'EQ:XNAS:EQIX','AMT':'EQ:XNYS:AMT'}
def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]*>',' ',str(s or '')))).strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def first(d,k):return d.get(k,[{}])[0].get('value') if d.get(k) else None
def page(key):
 p=HERE/'sources'/f'{key}.html';r=HERE/'sources'/f'{key}.receipt.json'
 receipt=json.loads(r.read_text())
 if receipt.get('sha256')!=sha(p):raise ValueError('Source hash mismatch: '+key)
 return p.read_text(),receipt

def packet(key):
 p=json.loads((HERE/'source-packets.json').read_text())[key]
 if hashlib.sha256(json.dumps(p['facts'],sort_keys=True,ensure_ascii=False).encode()).hexdigest()!=p['facts_sha256']:raise ValueError('Fact packet integrity failure')
 return copy.deepcopy(p['facts']),p['receipt']

def nextdata(s):
 m=re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',s,re.S)
 if not m:raise ValueError('Reviewed Next.js payload absent')
 return json.loads(m.group(1))['props']['pageProps']['data']

def listed_companies(registry,sec):
 rows=[dict(zip(sec['fields'],r)) for r in sec['data']];out={}
 for sym,key in REGISTRY_IDS.items():
  asset=registry['assets'][key]
  exact=[r for r in rows if r['ticker']==sym and str(r['cik']).zfill(10)==asset['cik'] and r['exchange']==('Nasdaq' if asset['mic']=='XNAS' else 'NYSE')]
  if len(exact)!=1 or asset.get('class')!='equity':raise ValueError('Current listing mismatch: '+sym)
  facts,receipt=packet(sym+'-10k');body=facts['common_stock_cover_html']
  cover=[]
  for tr in re.findall(r'<tr\b[^>]*>.*?</tr>',body,re.S|re.I):
   tags={k:[clean(v) for v in re.findall(r'<ix:nonNumeric\b[^>]*name="dei:'+k+r'"[^>]*>(.*?)</ix:nonNumeric>',tr,re.S|re.I)] for k in ['Security12bTitle','TradingSymbol','SecurityExchangeName']}
   if sym in tags['TradingSymbol'] and any(re.search(r'\bCommon Stock\b',v,re.I) for v in tags['Security12bTitle']) and len(tags['TradingSymbol'])==1:
    cover.append({'security_titles':tags['Security12bTitle'],'ticker':sym,'exchanges':tags['SecurityExchangeName']})
  if len(cover)!=1:raise ValueError('No unambiguous common-stock cover row: '+sym)
  sub,_=packet(sym+'-submissions');recent=sub['filings']['recent'];i=next(i for i,f in enumerate(recent['form']) if f=='10-K')
  out[key]={'id':key,'company_id':asset['company'],'name':asset['name'],'ticker':sym,'mic':asset['mic'],'cik':asset['cik'],
   'security_type':'common_equity','listing_checked_at':packet('sec')[1]['retrieved_at'][:10],'sec_listing_match':exact[0],
   'security_class_evidence':{'url':receipt['url'],'sha256':receipt['sha256'],'cover_row':cover[0],'form':'10-K','filing_date':recent['filingDate'][i],'accession':recent['accessionNumber'][i]},
   'hq':None,'hq_reason':'Existing registry coordinates are city-level; not a verified office site. No HQ line generated.'}
 return out

def geometry_country(lon,lat):
 # Existing Natural Earth low-resolution boundaries are a contradiction screen, not a geocoder or site validation.
 matches=[]
 for name,cx,cy,*rings in json.loads((ROOT/'assets/globe/countries-50m.json').read_text()):
  inside=False
  for packed in rings:
   x=y=0;points=[]
   for i in range(0,len(packed),2):x+=packed[i];y+=packed[i+1];points.append((x/50,y/50))
   flag=False
   for i,a in enumerate(points):
    b=points[i-1]
    if (a[1]>lat)!=(b[1]>lat) and lon<(b[0]-a[0])*(lat-a[1])/(b[1]-a[1])+a[0]:flag=not flag
   if flag:inside=True
  if inside:matches.append(name)
 return matches

def dlr_candidate(summary):
 key=str(summary['node_id']);d,receipt=packet(key)
 if str(d['node_id'])!=key or d['title']!=summary['title']:raise ValueError('Facility identity changed: '+key)
 lon=float(first(d,'field_longitude'));lat=float(first(d,'field_latitude'))
 country=d.get('country');cc,region=COUNTRIES.get(country,(None,'Unresolved'))
 reasons=[];category='A'
 if not cc:reasons.append('country-not-reviewed');category='C'
 # An observed official-source contradiction, not a silently corrected country assignment.
 gis=geometry_country(lon,lat)
 if d.get('metro')=='Dublin' and country=='United Kingdom' and 'Ireland' in gis:
  reasons.append('official-directory-country-UK-contradicts-Dublin-address-and-Ireland-polygon');category='D'
 if not math.isfinite(lon) or not math.isfinite(lat) or not -180<=lon<=180 or not -90<=lat<=90:category='D';reasons.append('invalid-coordinate')
 if '+' in d['title']:category='C';reasons.append('combined-facilities-not-separated')
 intro=clean(first(d,'field_intro_location'));address=clean(first(d,'field_address_location'))
 if not address:reasons.append('facility-address-missing');category='C' if category!='D' else category
 # Capacity field has no reviewed unit contract. Retain raw source field for research, never silently call it MW.
 utility=first(d,'field_utility_power_capacity')
 evidence={'url':receipt['url'],'retrieved_at':receipt['retrieved_at'],'sha256':receipt['sha256'],'published_at':None,
  'source_type':'official-company-facility-page','node_id':key,
  'facts':{'name':d['title'],'country':country,'city':d.get('metro'),'address':address,'latitude':lat,'longitude':lon,'utility_power_capacity_raw':utility},
  'field_pointers':{f:'$.props.pageProps.data.'+f for f in ['title','country','metro','field_address_location','field_latitude','field_longitude','field_utility_power_capacity']},
  'relationship_scope':'Official Digital Realty facility-directory membership/service portfolio; not a land-title or ownership-percentage claim.'}
 return {'id':'dc:dlr:'+key,'name':d['title'],'facility_code':d['title'],'source_id':key,'country':country,'cc':cc,'city':d.get('metro'),'region':region,
  'address':address,'coordinates':{'lat':lat,'lon':lon,'quality':'company-reported map pin; building/site precision not independently verified','exact_site_verified':False,'country_screen':gis},
  'granularity':'facility-directory record; campus/building/phase boundary unconfirmed','category':category,'review_reasons':reasons,
  'listed_company':REGISTRY_IDS['DLR'],'relationship':'portfolio_association','owner':None,'operator':None,'developer':None,
  'status':None,'completion_date':None,'capacity':None,'cost':None,'milestones':[], 'imagery':None,
  'evidence':[evidence], 'licensing':{'commercial_redistribution':None,'state':'not-cleared; website terms restrict copying and republication','terms_url':'https://www.digitalrealty.com/about/legal/terms'},
  'public_eligible':False,'research_scope':'A establishes portfolio/business affiliation only. Ownership, operating status and direct project investment are not verified.'}

def eqix_candidate(code):
 facts,receipt=packet('eqix-'+code.lower())
 def val(name):return facts.get(name)
 lon=float(val('longitude'));lat=float(val('latitude'));address=', '.join(v for v in [val('address1'),val('address2'),val('city'),val('country')] if v)
 return {'id':'dc:eqix:'+code,'name':'Equinix '+code,'facility_code':code,'source_id':code,'country':val('country'),'cc':COUNTRIES[val('country')][0],'city':val('city'),'region':COUNTRIES[val('country')][1],
  'address':address,'coordinates':{'lat':lat,'lon':lon,'quality':'company-reported map pin; site precision not independently verified','exact_site_verified':False},
  'granularity':'facility-directory record; campus/building/phase boundary unconfirmed','category':'A','review_reasons':[],
  'listed_company':REGISTRY_IDS['EQIX'],'relationship':'portfolio_association','owner':None,'operator':None,'developer':None,
  'status':None,'completion_date':None,'capacity':None,'cost':None,'milestones':[],'imagery':None,
  'evidence':[{'url':receipt['url'],'sha256':receipt['sha256'],'retrieved_at':receipt['retrieved_at'],'published_at':None,'source_type':'official-company-facility-page',
   'facts':{'name':code,'address':address,'latitude':lat,'longitude':lon},'field_pointers':{'latitude':'inline ibxMapDataGlobal const latitude','longitude':'inline ibxMapDataGlobal const longitude','address':'inline address1/address2/city/country'},
   'relationship_scope':'Official Equinix IBX directory/business portfolio, not property ownership.'}],
  'licensing':{'commercial_redistribution':False,'state':'not-cleared; restrictive website terms','terms_url':'https://www.equinix.com/about/legal/terms'},'public_eligible':False,
  'research_scope':'Portfolio/business affiliation only; no verified direct project ownership or investment right.'}

def validate_link(record,edge,companies):
 if record['category'] not in ('A','B'):raise ValueError('Unverified or contradictory project cannot generate an investment link')
 if record['category']=='B':raise ValueError('Regulatory ownership-chain adapter not implemented; category B held')
 source=record['evidence'][0];u=urlsplit(source['url'])
 trusted={REGISTRY_IDS['DLR']:'www.digitalrealty.com',REGISTRY_IDS['EQIX']:'www.equinix.com'}
 if source.get('source_type')!='official-company-facility-page' or u.scheme!='https' or u.username or u.password or u.hostname!=trusted.get(record['listed_company']):raise ValueError('Not a reviewed official facility source for this listed company')
 if edge['to'] not in companies or companies[edge['to']]['security_type']!='common_equity':raise ValueError('Target not verified listed common equity')
 if edge.get('project')!=record['id'] or edge['to']!=record['listed_company']:raise ValueError('Identifier mismatch')
 if edge.get('kind')!='portfolio_association' or edge.get('exposure')!='indirect_corporate_equity':raise ValueError('Unproved owner/developer/power/HQ/direct-investor link')
 if edge.get('ownership_pct') is not None:raise ValueError('No ownership percentage established')
 if edge.get('evidence_sha256')!=record['evidence'][0]['sha256']:raise ValueError('Unbound relationship evidence')
 return True

def build():
 registry=json.loads((ROOT/'data/registry.json').read_text());sec=packet('sec')[0];companies=listed_companies(registry,sec)
 summaries=packet('selected')[0];records=[];failures=[]
 for summary in summaries:
  try:records.append(dlr_candidate(summary))
  except (ValueError,OSError,KeyError) as e:failures.append({'source_id':str(summary['node_id']),'reason':str(e)})
 records += [eqix_candidate(c) for c in ['DC2','SV1','DX1']]
 # CoreSite is a real facility candidate, but its parent chain and exact facility role are not concluded from a logo.
 _,receipt=packet('coresite-va1')
 records.append({'id':'dc:coresite:VA1','name':'CoreSite VA1','facility_code':'VA1','country':'United States','cc':'US','city':'Reston','region':'North America','category':'C',
  'listed_company':REGISTRY_IDS['AMT'],'relationship':None,'coordinates':None,'owner':None,'operator':None,'developer':None,'status':None,'cost':None,'capacity':None,'milestones':[],'imagery':None,
  'granularity':'facility-directory record','public_eligible':False,'review_reasons':['CoreSite branding says American Tower company; legal ownership chain/JV interests not yet verified','Do not use Organization structured address: it describes Denver corporate office, not Virginia facility'],
  'evidence':[{'url':receipt['url'],'sha256':receipt['sha256'],'retrieved_at':receipt['retrieved_at'],'published_at':None,'source_type':'official-company-facility-page'}],
  'licensing':{'state':'not-cleared','commercial_redistribution':None}})
 unique={}
 for r in records:
  if r['id'] in unique and unique[r['id']]!=r:raise ValueError('Conflicting stable facility ID')
  unique[r['id']]=r
 records=list(unique.values());edges=[]
 for r in records:
  if r['category'] not in ('A','B'):continue
  edge={'project':r['id'],'to':r['listed_company'],'kind':'portfolio_association','exposure':'indirect_corporate_equity','ownership_pct':None,
   'evidence_sha256':r['evidence'][0]['sha256'],'direct_project_investment_verified':False,'public_eligible':False}
  validate_link(r,edge,companies);edges.append(edge)
 result={'schema':'investedia.data-centers.research.v1','as_of':packet('sec')[1]['retrieved_at'][:10],'notice':'INTERNAL RESEARCH PREVIEW. No commercial reuse cleared. No verified direct project ownership. Not investment advice.',
  'companies':companies,'records':records,'edges':edges,'failed_fetch_or_parse':failures,
  'counts':{'discovered_official_dlr_directory_records':packet('directory-count')[0]['count'],'sampled_records':len(records),'deduplicated':len(records),'by_category':{c:sum(r['category']==c for r in records) for c in 'ABCD'},'public_eligible':0,'verified_ownership_links':0,'portfolio_links':len(edges)}}
 (HERE/'dataset.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 (HERE/'preview/data.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
 # Compatibility projection only; no new shared schema and no publication permission implied.
 projection=[]
 for r in records:
  if r['category'] not in ('A','B') or not r.get('coordinates'):continue
  fields={'k':r['id'],'n':r['name'],'t':'Data centres','c':r['country'],'cc':r['cc'],'la':r['coordinates']['lat'],'lo':r['coordinates']['lon'],'own':[],
   'coordinate_quality':'company map pin; exact site unverified','validation_status':'research_only',
   'src':[{'name':'Official company facility directory','url':r['evidence'][0]['url'],'licence':'Commercial redistribution not cleared','checked_at':result['as_of'],'field_list':['k','n','t','c','cc','la','lo']}]}
  projection.append(fields)
 (HERE/'projects-v2-research.json').write_text(json.dumps({'schema':'investedia.projects.v2','projects':projection,'notice':result['notice']},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result['counts']))

if __name__=='__main__':build()
