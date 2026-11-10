"""Phase-01 audit collector. --fetch is for the manual Actions runner only.
No registry, production API, financial job, schedules, or secret use.
"""
import argparse,csv,hashlib,io,json,os,re,sys,time
import urllib.error,urllib.parse,urllib.request,urllib.robotparser
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.markets_audit.methods import fx_audit
UA='InvestediaRobot/1.0'

def read(path,default=None):
 p=Path(path);return json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else default

def save(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):raise ValueError('redirect_requires_review')

class Client:
 def __init__(self):self.last={};self.policies={};self.requests=0
 def raw(self,url,method='GET'):
  p=urllib.parse.urlsplit(url)
  if p.scheme!='https' or p.username or p.password:raise ValueError('public_HTTPS_required')
  wait=1-(time.monotonic()-self.last.get(p.netloc,-100))
  if wait>0:time.sleep(wait)
  self.last[p.netloc]=time.monotonic();self.requests+=1
  req=urllib.request.Request(url,method=method,headers={'User-Agent':UA,'Accept':'application/json, application/xml, text/plain, text/html;q=0.8'})
  with urllib.request.build_opener(NoRedirect()).open(req,timeout=15) as response:
   body=response.read(8_000_001)
   if len(body)>8_000_000:raise ValueError('audit_download_limit_exceeded_use_bulk_manifest')
   return body,dict(response.headers)
 def get(self,url,method='GET'):
  p=urllib.parse.urlsplit(url)
  if p.netloc not in self.policies:
   robot=urllib.robotparser.RobotFileParser()
   try:body,_=self.raw(f'https://{p.netloc}/robots.txt')
   except urllib.error.HTTPError as error:
    if error.code!=404:raise
    body=b''
   text=body.decode('utf-8-sig','replace')
   if '<html' in text.lower() or '<!doctype html' in text.lower():raise ValueError('robots_response_unverified')
   robot.parse(text.splitlines());self.policies[p.netloc]=robot
  robot=self.policies[p.netloc]
  if not robot.can_fetch(UA,url):raise ValueError('robots_disallowed')
  delay=robot.crawl_delay(UA) or robot.crawl_delay('*') or 1
  rate=robot.request_rate(UA) or robot.request_rate('*')
  if rate and rate.requests>0:delay=max(delay,rate.seconds/rate.requests)
  if delay>15:raise ValueError('rate_wait_deferred_to_bulk_review')
  wait=delay-(time.monotonic()-self.last.get(p.netloc,-100))
  if wait>0:time.sleep(wait)
  # 429/Retry-After is reported and deferred, not retried aggressively.
  return self.raw(url,method)


def ecb_xml(raw):
 result={}
 for node in ET.fromstring(raw).iter():
  day=node.get('time')
  if not day:continue
  if day in result:raise ValueError('duplicate_ECB_date')
  result[day]={'EUR':1.0}
  for child in node:
   if child.get('currency') and child.get('rate'):result[day][child.get('currency')]=float(child.get('rate'))
 return result


def source_schema(value,prefix='',depth=0):
 if depth>4:return []
 if isinstance(value,dict):
  out=[]
  for key,child in value.items():
   name=prefix+'.'+key if prefix else key;out.append(name);out+=source_schema(child,name,depth+1)
  return out[:200]
 if isinstance(value,list) and value:return source_schema(value[0],prefix+'[]',depth+1)
 return []


def sec_presence(cik,facts,submissions):
 concepts={'revenue':['RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet','Revenue'],
 'net_income':['NetIncomeLoss','ProfitLoss'],'assets':['Assets'],'liabilities':['Liabilities'],
 'shares_instant':['EntityCommonStockSharesOutstanding'],'shares_weighted_diluted':['WeightedAverageNumberOfDilutedSharesOutstanding']}
 recent=submissions.get('filings',{}).get('recent',{});accessions=recent.get('accessionNumber',[]);docs=recent.get('primaryDocument',[])
 links=dict(zip(accessions,docs));out={}
 for label,names in concepts.items():
  found=[]
  for taxonomy,fields in facts.get('facts',{}).items():
   for name in names:
    concept=fields.get(name)
    if not concept:continue
    units=concept.get('units',{})
    sample=[]
    for unit,rows in units.items():
     for row in rows[-2:]:
      accession=row.get('accn');document=links.get(accession)
      url=(f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-","")}/{document}' if accession and document else None)
      sample.append({k:row.get(k) for k in ('start','end','fy','fp','form','filed','accn','frame') }|{'unit':unit,'filing_url':url,'filing_url_reason':None if url else 'accession_primary_document_join_not_available'})
    found.append({'taxonomy':taxonomy,'concept':name,'units':list(units),'period_examples':sample})
  out[label]={'concepts':found,'present_in_sample':bool(found)}
 return {'cik':cik,'sample_only_not_population_reliability':True,'concepts':out}


def coverage(root):
 registry=read(root/'data/registry.json',{}).get('assets',{});ex=read(root/'data/exchanges.json',{})
 iso=read(root/'assets/globe/iso.json',{});shapes=read(root/'assets/globe/countries-50m.json',[])
 companies=read(root/'data/companies.json',{}).get('companies',[])
 sector={listing['s']:company['sector'] for company in companies if company.get('sector') for listing in company.get('listings',[]) if listing.get('s')}
 equities=[a for a in registry.values() if a.get('class')=='equity']
 def metrics(rows):
  return {'observed_legacy_equities':len(rows),'observed_with_sector':sum(bool(a.get('px') in sector or a.get('sector')) for a in rows),
   'observed_with_lei':sum(bool(a.get('lei')) for a in rows),
   'observed_with_hq':sum((a.get('geo') or {}).get('src')=='sec-hq' and (a.get('geo') or {}).get('la') is not None and (a.get('geo') or {}).get('lo') is not None for a in rows),
   'verified_licensed_equities':None,'verified_with_sector':None,'verified_with_lei':None,'verified_with_hq':None,
   'published_exchange_listing_count':None,'listing_count_source':None,'coverage_share':None,
   'recommended_status':'not yet','reason':['fresh_licensed_listing_assertions_not_yet_audited','compatible_published_listing_denominator_unavailable'],
   'ownership_share_all_issuers':None,'ownership_share_lei_issuers':None,'ownership_reason':'GLEIF_relationships_not_joined_to_a_verified_issuer_population'}
 venues=[{'mic':mic,'name':v['name'],'country':v.get('country'),**metrics([a for a in equities if a.get('mic')==mic])} for mic,v in sorted(ex.items())]
 countries=[{'name':s[0],'iso2':iso.get(s[0]),**metrics([a for a in equities if iso.get(s[0]) and a.get('country')==iso.get(s[0])])} for s in shapes]
 return {'schema':'investedia.markets-feasibility/v1','scope':'audit only; legacy observations are not licensed verification',
  'countries':countries,'exchanges':venues,'totals':{'globe_shapes':len(countries),'exchanges':len(venues),'observed_equity_rows':len(equities)},
  'launch_threshold':{'licensed_current_listing_share':.8,'sector_share_of_verified':.7,'identifier_conflicts':0,'require_denominator_same_security_scope':True},
  'approved_launch_countries':[],'pilot_candidates_pending_evidence':['US','GB','CA','AU','JP'],
  'limitations':['No sample response can establish an exchange-wide denominator.','Observed HQ count uses legacy sec-hq tags, not fresh HQ verification; business address can differ. Exchange city/registered office are not HQ.','ETF/bond universe not enabled.','Countries and exchange domicile are different coverage groupings.']}


def licensing(catalogue,evidence,now):
 lines=['# Source licensing audit — phase 01','','Not investment advice.','',
  'Remote terms have not been downloaded in this sandbox. A date below distinguishes a fetched notice from a reviewed grant. No public launch or production rights are approved by HTTP success.',
  '✅ = supported within the reviewed scope; ⚠️ = conditional/pending current primary terms; ❌ = not cleared for this product, not a finding that every conceivable use is illegal.',
  '', '| Source | Exact terms URL | Date checked / method | Public access | Public domain | Free download | Commercial use | Redistribution | Attribution | Limits | Verdict |',
  '|---|---|---|---|---|---|---|---|---|---|']
 for src in catalogue:
  record=evidence.get(src['id'],{});local=src['format']=='local' and record.get('local_licence_verified') is True
  checked=now[:10]+' (local retained Apache licence)' if local else record.get('terms_fetched_at','not checked; runner required')
  commercial='yes, Apache-2.0 scope' if local else 'null — current grant not reviewed'
  redistribution='yes, retain licence/notices' if local else 'null — current grant not reviewed'
  verdict='✅ usable (calendar scope only)' if local else ('❌ not cleared' if src['expected_verdict']=='not_cleared' else '⚠️ conditions / primary notice pending')
  attribution='Apache licence + upstream notices; identify extraction changes' if local else src['expected_licence']+'; exact attribution text pending review'
  public='yes, retained public package' if local else 'documented public source; runner access status separate'
  domain='no, Apache copyrighted work' if local else ('CC0 dedication expected; current notice pending' if src['id'] in {'wikidata','gleif'} else 'null / not a blanket public-domain work')
  free='yes (retained package)' if local else ('keyless documented source; verify notice' if src['data_url'] else 'null — source access/licence not established')
  lines.append(f"| {src['name']} | {src['terms_url'] or 'null — exact reuse notice not identified'} | {checked} | {public} | {domain} | {free} | {commercial} | {redistribution} | {attribution} | {src['rate_note']} | {verdict} |")
 lines+=['','## Scope and attribution review','',
  'Wikidata: CC0 applies to structured statements, not Wikimedia images or an external cited work. A source reference does not transfer rights to that work.',
  'GLEIF: confirm CC0 against the actual LEI/Level-2 product and current notice; preserve source/update/status for auditability even where attribution is not legally required.',
  'SEC: distinguish agency-authored pages from issuer filings. Numerical XBRL facts and identifiers are the proposed scope; do not declare all submitted reports public domain or republish report prose/images.',
  'World Bank: retain indicator/dataset licence, period, unit and “World Bank, World Development Indicators” acknowledgement; check third-party exceptions per dataset.',
  'ECB: attribute “Source: European Central Bank”, preserve dates and reference-rate disclaimer; do not suggest executable prices or ECB endorsement. Current notice still requires review.',
  'UK Companies House: OGL only where explicitly attached; retain the OGL attribution text provided with that product. Company registration addresses are not headquarters. API authentication is excluded here.',
  'Nasdaq/JSE/NGX/B3/NSE: a downloadable file, official status, or free web page is not an explicit republication licence. No securities from these sources are marked cleared without a product-specific grant.',
  '', 'Exact missing terms URLs are null rather than guessed. The runner records source status, response hash and observed schema; it does not auto-approve licences. A reviewer must record the actual grant/scope before production ingestion.']
 return '\n'.join(lines)+'\n'


def render_coverage(report):
 lines=['# Markets coverage feasibility','','Not investment advice.','',
  'Counts labelled observed refer only to the existing saved registry. Fresh licensed verification counts and denominator shares remain null until the runner evidence and primary rights are reviewed.',
  'Launch proposal: >=80% of the same-scope official current common-stock listing population, >=70% of verified rows with sector, no unresolved identifier conflicts, source freshness/rights cleared. ETFs and bonds are not enabled.',
  '', '| Country | ISO2 | Observed rows | Sector | LEI | HQ | Verified licensed | Coverage | Status |', '|---|---|---:|---:|---:|---:|---|---|---|']
 for r in sorted(report['countries'],key=lambda r:(-r['observed_legacy_equities'],r['name'])):
  lines.append(f"| {r['name']} | {r['iso2'] or 'unmapped'} | {r['observed_legacy_equities']} | {r['observed_with_sector']} | {r['observed_with_lei']} | {r['observed_with_hq']} | null | null — denominator missing | not yet |")
 lines+=['','## Exchanges','', '| MIC | Exchange | Country | Observed rows | Sector / LEI / HQ | Verified / denominator | Status |','|---|---|---|---:|---|---|---|']
 for r in report['exchanges']:lines.append(f"| {r['mic']} | {r['name']} | {r['country']} | {r['observed_legacy_equities']} | {r['observed_with_sector']} / {r['observed_with_lei']} / {r['observed_with_hq']} | null / null | not yet |")
 lines+=['','## Recommended launch countries','',
  '**None currently qualify on audited evidence.** First pilot candidates: US, GB, CA, AU and JP, pending licensed primary listing assertions, a compatible denominator and sector-quality checks. These are candidates, not approved launch coverage.',
  'The rest are blocked by the same missing rights/denominators and varying identifier/HQ/sector gaps. Unsupported globe ISO mappings stay unresolved. Do not market this as worldwide-complete.',
  'No ownership percentage is estimated without a verified issuer population and a GLEIF LEI join. Missing is null, never zero. A tiny API sample cannot establish a national or exchange-wide coverage share.']
 return '\n'.join(lines)+'\n'


def fetch_audit(catalogue,limit,out):
 client=Client();evidence={};fx={};financials=[]
 for src in catalogue:
  record={'terms_url':src['terms_url'],'terms_review_status':'pending','data_status':'not_attempted'};evidence[src['id']]=record
  if src['format']=='local':record['data_status']='retained_Apache_licence';continue
  try:
   if src['terms_url']:
    raw,_=client.get(src['terms_url']);record.update(terms_fetched_at=datetime.now(timezone.utc).isoformat(),terms_sha256=hashlib.sha256(raw).hexdigest())
   else:record['terms_reason']='exact_reuse_terms_unknown_no_listing_download'
  except (OSError,ValueError) as error:record['terms_status']='unavailable_'+type(error).__name__
  url=src['data_url']
  if not url:continue
  if src['format']=='sparql':
   query='SELECT ?issuer ?listing ?exchange ?ticker ?lei ?cik ?industry ?hq ?hqPoint WHERE { ?issuer p:P414 ?listing . ?listing ps:P414 ?exchange . ?listing pq:P249 ?ticker . OPTIONAL { ?issuer wdt:P1278 ?lei } OPTIONAL { ?issuer wdt:P5531 ?cik } OPTIONAL { ?issuer wdt:P452 ?industry } OPTIONAL { ?issuer wdt:P159 ?hq . ?hq wdt:P625 ?hqPoint } } LIMIT '+str(limit)
   url+='?'+urllib.parse.urlencode({'query':query,'format':'json'})
  if src['format']=='gleif':url+='?'+urllib.parse.urlencode({'page[size]':limit})
  try:
   raw,headers=client.get(url);record.update(data_status='downloaded_for_audit_only',retrieved_at=datetime.now(timezone.utc).isoformat(),response_sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),source_url=url)
   if src['format']=='ecb':fx=fx_audit(ecb_xml(raw));record['observed_schema']=['Cube@time','Cube@currency','Cube@rate']
   elif src['format']=='directory':
    rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig')),delimiter='|'));record['observed_schema']=list(rows[0]) if rows else []
    if not {'Symbol','Security Name','ETF','Test Issue'}<=set(record['observed_schema']):raise ValueError('directory_schema_unverified')
    record['directory_rows_including_possible_footer']=len(rows);record['licence_clearance']='not_approved_no_registry_rows_exported'
   elif src['format']=='manifest':record['observed_schema']=['HTML bulk-product index; no ZIP downloaded']
   else:
    payload=json.loads(raw);record['observed_schema']=source_schema(payload)
    if src['format']=='gleif':
     probes=[]
     records=payload.get('data',[]) if isinstance(payload,dict) else []
     for row in records[:1]:
      relationships=row.get('relationships',{})
      for kind in ('direct-parent','ultimate-parent'):
       related=relationships.get(kind,{}).get('links',{}).get('related')
       if not isinstance(related,str) or urllib.parse.urlsplit(related).hostname!='api.gleif.org':continue
       try:
        parent_raw,_=client.get(related);probes.append({'kind':kind,'url':related,'status':'sampled','schema':source_schema(json.loads(parent_raw)),'sha256':hashlib.sha256(parent_raw).hexdigest()})
       except (OSError,ValueError):probes.append({'kind':kind,'url':related,'status':'not_available_in_bounded_sample'})
     record['parent_relationship_schema_probes']=probes
     record['ownership_coverage_share']=None
    if src['format']=='sec':
     if not isinstance(payload,dict) or not payload.get('cik') or not isinstance(payload.get('filings'),dict):raise ValueError('invalid_SEC_submissions')
     cik=str(payload['cik']).zfill(10)
     facts_raw,_=client.get('https://data.sec.gov/api/xbrl/companyfacts/CIK'+cik+'.json')
     facts=json.loads(facts_raw)
     if not isinstance(facts.get('facts'),dict):raise ValueError('invalid_SEC_companyfacts')
     financials.append(sec_presence(cik,facts,payload))
  except (OSError,ValueError,ET.ParseError) as error:
   record['data_status']='unavailable_'+type(error).__name__
   if isinstance(error,urllib.error.HTTPError):record['http_status']=error.code;record['retry_after']=error.headers.get('Retry-After')
 # Bulk manifest metadata only: these files can be multi-gigabyte. Never silently download them.
 for name,url in [('SEC_company_tickers_exchange','https://www.sec.gov/files/company_tickers_exchange.json'),('SEC_companyfacts_bulk','https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip'),('SEC_submissions_bulk','https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip'),('GLEIF_Golden_Copy_manifest','https://goldencopy.gleif.org/api/v2/golden-copies/publishes')]:
  try:
   raw,headers=client.get(url,'HEAD' if name.endswith('_bulk') else 'GET')
   evidence[name]={'url':url,'status':'schema_sample' if name=='SEC_company_tickers_exchange' else 'manifest_only','content_length':headers.get('Content-Length') or headers.get('content-length'),'last_modified':headers.get('Last-Modified') or headers.get('last-modified'),'response_sha256':hashlib.sha256(raw).hexdigest()}
   if name=='SEC_company_tickers_exchange':evidence[name]['observed_schema']=source_schema(json.loads(raw))
  except (OSError,ValueError) as error:evidence[name]={'url':url,'status':'unavailable_'+type(error).__name__}
 save(out/'source-evidence.json',{'sources':evidence,'http_requests':client.requests,'no_registry_written':True})
 save(out/'sec-sample.json',{'samples':financials,'population_reliability':None,'reason':'single_bounded_schema_sample_not_population_estimate'})
 return evidence,fx


def main():
 p=argparse.ArgumentParser();p.add_argument('--fetch',action='store_true');p.add_argument('--sample-limit',type=int,default=25);p.add_argument('--output',type=Path,default=ROOT/'data/markets-audit');a=p.parse_args()
 if not 1<=a.sample_limit<=100:p.error('sample_limit_must_be_1_to_100')
 if a.fetch and os.environ.get('GITHUB_ACTIONS')!='true':p.error('downloads_are_reserved_for_the_manual_GitHub_Actions_runner')
 a.output.mkdir(parents=True,exist_ok=True);catalogue=read(ROOT/'data/markets-audit/sources.json')['sources']
 evidence,fx=fetch_audit(catalogue,a.sample_limit,a.output) if a.fetch else ({},{})
 now=datetime.now(timezone.utc).isoformat()
 for src in catalogue:
  record=evidence.setdefault(src['id'],{'terms_url':src['terms_url'],'terms_review_status':'pending','data_status':'not_downloaded_manual_runner_required'})
  licence=ROOT/'data/coverage/third-party/exchange-calendars-LICENSE.txt'
  local=src['id']=='exchange_calendars' and licence.exists() and 'Apache License' in licence.read_text() and 'Version 2.0' in licence.read_text()
  record['rights']={'commercial_use_allowed':True if local else None,'redistribution_allowed':True if local else None,
                   'public_domain':False if local else None,'free_download':True if local else None,
                   'reason':None if local else 'current_product_specific_primary_grant_not_reviewed'}
  if local:record.update(local_licence_verified=True,checked_at=now,local_licence_path=str(licence.relative_to(ROOT)),licence_sha256=hashlib.sha256(licence.read_bytes()).hexdigest())
 stored=read(a.output/'source-evidence.json',{});stored.update(sources=evidence,no_registry_written=True)
 save(a.output/'source-evidence.json',stored)
 report=coverage(ROOT);report['audited_at']=now
 save(a.output/'coverage.json',report);(a.output/'COVERAGE.md').write_text(render_coverage(report))
 (a.output/'LICENSING.md').write_text(licensing(catalogue,evidence,now))
 if not fx:fx=fx_audit({});fx['reason']='No dated ECB snapshot locally; use the manual runner. Mathematical test fixtures are not market data.'
 fx['source_url']='https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml';fx['licence_review_status']='pending_current_primary_notice_review'
 save(a.output/'fx-sample.json',fx)
 print(json.dumps({'countries':report['totals']['globe_shapes'],'exchanges':report['totals']['exchanges'],'fetch_requested':a.fetch,'registry_build':False,'launch_countries':[]}))
if __name__=='__main__':main()
