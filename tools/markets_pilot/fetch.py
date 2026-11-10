"""Approved-source downloads for the manual runner; raw files never mix with output."""
import csv,hashlib,io,json,os,re,shutil,urllib.parse,zipfile
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
from tools.markets_audit.run import Client,ecb_xml
from tools.markets_pilot.registry import SEC_MIC,normal_id,fiscal_year

ALLOWED={'www.sec.gov','data.sec.gov','query.wikidata.org','www.wikidata.org','api.gleif.org','goldencopy.gleif.org','www.gleif.org',
 'www.ecb.europa.eu','api.worldbank.org','download.companieshouse.gov.uk','www.gov.uk','www.nationalarchives.gov.uk'}
SEC_DIRECTORY='https://www.sec.gov/files/company_tickers_exchange.json'
SEC_SUBMISSIONS='https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip'
SEC_FACTS='https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip'
OGL='https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/'

class Downloads:
 def __init__(self,directory,max_bytes=6*1024**3):
  self.root=Path(directory);self.root.mkdir(parents=True,exist_ok=True);self.client=Client();self.manifest=[];self.remaining=max_bytes
 def allowed(self,url):
  u=urllib.parse.urlsplit(url)
  if u.scheme!='https' or u.hostname not in ALLOWED or u.username or u.password:raise ValueError('source_not_approved')
 def small(self,url,name):
  self.allowed(url);raw,headers=self.client.get(url)
  self.remaining-=len(raw)
  if self.remaining<0:raise ValueError('raw_download_budget_exceeded')
  path=self.root/name;path.write_bytes(raw);self.record(url,path);return raw
 def record(self,url,path):
  h=hashlib.sha256()
  with path.open('rb') as f:
   for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
  self.manifest.append({'url':url,'file':path.name,'bytes':path.stat().st_size,'sha256':h.hexdigest(),'retrieved_at':datetime.now(timezone.utc).isoformat()})
  (self.root/'manifest.json').write_text(json.dumps(self.manifest,indent=2)+'\n')
 def bulk(self,url,name):
  import time,urllib.request
  from tools.markets_audit.run import NoRedirect,UA
  self.allowed(url)
  # Check the same robots/rate policy before streaming a large permitted bulk product.
  self.client.get(url,'HEAD');time.sleep(1)
  path=self.root/name;temporary=path.with_suffix('.part')
  request=urllib.request.Request(url,headers={'User-Agent':UA})
  try:
   with urllib.request.build_opener(NoRedirect()).open(request,timeout=120) as response,temporary.open('wb') as output:
    size=response.headers.get('Content-Length')
    if size and int(size)>self.remaining:raise ValueError('raw_download_budget_exceeded')
    while True:
     block=response.read(1024*1024)
     if not block:break
     self.remaining-=len(block)
     if self.remaining<0:raise ValueError('raw_download_budget_exceeded')
     output.write(block)
   os.replace(temporary,path);self.record(url,path);return path
  except BaseException:
   temporary.unlink(missing_ok=True);raise


def sec_directory(payload):
 fields=payload.get('fields',[])
 if not {'cik','name','ticker','exchange'}<=set(fields):raise ValueError('SEC_directory_schema_changed')
 result=[]
 for values in payload.get('data',[]):
  row=dict(zip(fields,values))
  if row.get('exchange') not in SEC_MIC:continue
  cik=normal_id('cik',row.get('cik'))
  if not cik or not isinstance(row.get('ticker'),str) or not row['ticker']:raise ValueError('invalid_SEC_listing_row')
  result.append({'cik':cik,'name':row['name'],'ticker':row['ticker'],'exchange':row['exchange']})
 if not result:raise ValueError('empty_SEC_directory')
 return result


def selected_json_zip(path,ciks,submissions=None):
 result={}
 with zipfile.ZipFile(path) as archive:
  names=set(archive.namelist())
  for cik in sorted(ciks):
   name='CIK'+cik+'.json'
   if name not in names:continue
   member=archive.getinfo(name)
   if member.file_size>32*1024**2:raise ValueError('per_issuer_JSON_size_limit')
   with archive.open(member) as f:value=json.load(f)
   if normal_id('cik',value.get('cik'))!=cik:raise ValueError('SEC_bulk_CIK_mismatch')
   if submissions is not None:
    result[cik]=fiscal_year(value,submissions[cik]);continue
   recent=value.get('filings',{}).get('recent',{});indices=[i for i,form in enumerate(recent.get('form',[])) if form=='10-K']
   latest=max(indices,key=lambda i:recent.get('filingDate',['']*(i+1))[i]) if indices else None
   compact={k:value.get(k) for k in ('cik','name','entityType','tickers','exchanges','sic','sicDescription')}
   compact['filings']={'recent':{k:[v[latest]] if latest is not None and latest<len(v) else [] for k,v in recent.items() if isinstance(v,list)}}
   result[cik]=compact
 return result


def wikidata(downloads):
 """Qualified pairs only, with end-date/deprecation and security-item type evidence."""
 rows=[];seen=set()
 # Both source statement orientations are valid; qualifiers must pair venue/ticker.
 for orientation in ('exchange','ticker'):
  offset=0
  while offset<20000:
   pattern=('?item p:P414 ?statement . ?statement ps:P414 ?venue; pq:P249 ?ticker .' if orientation=='exchange' else '?item p:P249 ?statement . ?statement ps:P249 ?ticker; pq:P414 ?venue .')
   query='''SELECT ?item ?itemLabel ?issuer ?issuerLabel ?venue ?ticker ?statement ?rank ?end ?start ?cik ?lei ?isin ?industry ?hqPoint ?country ?ch ?currency ?stock ?classLabel WHERE {
   VALUES ?venue { wd:Q13677 wd:Q82059 wd:Q846626 wd:Q171240 }
   PATTERN
   ?statement wikibase:rank ?rank .
   OPTIONAL { ?statement pq:P582 ?end } OPTIONAL { ?statement pq:P580 ?start }
   OPTIONAL { ?item wdt:P2378 ?issuer } BIND(COALESCE(?issuer,?item) AS ?company)
   OPTIONAL { ?company wdt:P5531 ?cik } OPTIONAL { ?company wdt:P1278 ?lei }
   OPTIONAL { ?item wdt:P946 ?isin } OPTIONAL { ?company wdt:P452 ?industry }
   OPTIONAL { ?company wdt:P159/wdt:P625 ?hqPoint } OPTIONAL { ?company wdt:P17 ?country }
   OPTIONAL { ?company wdt:P2622 ?ch } OPTIONAL { ?statement pq:P38/wdt:P498 ?currency }
   OPTIONAL { ?item wdt:P31 ?itemClass . ?itemClass rdfs:label ?classLabel FILTER(LANG(?classLabel)="en") }
   BIND(EXISTS { ?item wdt:P31 wd:Q134556 } AS ?stock)
   SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
   } ORDER BY ?statement ?item ?ticker ?issuer ?lei ?cik ?isin ?industry ?hqPoint ?country ?ch ?currency ?rank ?start ?end ?classLabel LIMIT 500 OFFSET OFFSET_VALUE'''.replace('PATTERN',pattern).replace('OFFSET_VALUE',str(offset))
   url='https://query.wikidata.org/sparql?'+urllib.parse.urlencode({'query':query,'format':'json'})
   data=json.loads(downloads.small(url,f'wikidata-{orientation}-{offset}.json'))
   bindings=data.get('results',{}).get('bindings')
   if not isinstance(bindings,list):raise ValueError('Wikidata_query_schema_changed')
   for b in bindings:
    value=lambda k:b.get(k,{}).get('value')
    item=(value('item') or '').rsplit('/',1)[-1];issuer=(value('issuer') or value('item') or '').rsplit('/',1)[-1]
    venue=(value('venue') or '').rsplit('/',1)[-1]
    mic={'Q13677':'XNYS','Q82059':'XNAS','Q846626':'XASE','Q171240':'XLON'}.get(venue)
    if not mic:continue
    statement=value('statement');ticker=value('ticker')
    binding_key=json.dumps(b,sort_keys=True)
    if binding_key in seen:continue
    seen.add(binding_key)
    rank=value('rank') or '';end=value('end');start=value('start')
    now=datetime.now(timezone.utc).isoformat()
    def date_value(value):
     if not value:return None
     return datetime.fromisoformat(value.lstrip('+').replace('Z','+00:00'))
    now=datetime.now(timezone.utc)
    active=not rank.endswith('DeprecatedRank') and not (end and date_value(end)<=now) and not (start and date_value(start)>now)
    hq=value('hqPoint');point=re.fullmatch(r'Point\((-?[0-9.]+) (-?[0-9.]+)\)',hq or '')
    # ISIN on an issuer item is not automatically a share-class identifier.
    nonstock=(value('classLabel') or '').lower() in {'exchange-traded fund','mutual fund','preferred stock','preference share','depositary receipt','american depositary receipt','warrant','bond','unit'}
    stock=value('stock')=='true' and not nonstock;isin=value('isin') if stock else None
    rows.append({'issuer_qid':issuer,'issuer_name':value('issuerLabel') or value('itemLabel') or issuer,
      'security_qid':item if stock else None,'security_type':'stock' if stock else ('non_stock' if nonstock else None),'statement_id':statement,
      'mic':mic,'ticker':ticker,'cik':value('cik'),'lei':value('lei'),'isin':isin,'active':active,
      'industry_qid':(value('industry') or '').rsplit('/',1)[-1] or None,'companies_house_id':value('ch'),
      'legal_country':{'Q145':'GB','Q30':'US'}.get((value('country') or '').rsplit('/',1)[-1]),
      'hq':{'lat':float(point[2]),'lon':float(point[1]),'location_kind':'headquarters','source':'Wikidata (CC0)','precision':None,'precision_reason':'source_precision_not_downloaded'} if point else None,
      'currency':value('currency') if re.fullmatch('[A-Z]{3}',value('currency') or '') else None})
   if len(bindings)<500:break
   offset+=500
  else:raise ValueError('Wikidata_pagination_limit_incomplete_snapshot')
 if not rows:raise ValueError('empty_Wikidata_listing_snapshot')
 return rows


def golden_urls(manifest):
 """Discover exact XML full-file URLs from the official Golden Copy manifest."""
 candidates={'lei':set(),'rr':set()}
 def walk(value,path=''):
  if isinstance(value,dict):
   for key,child in value.items():walk(child,path+'/'+key.lower())
  elif isinstance(value,list):
   # Select the latest publication entry before calling this function.
   for child in value:walk(child,path)
  elif isinstance(value,str) and value.startswith('https://'):
   context=(path+' '+value).lower()
   if 'full' not in context or 'xml' not in context or not (value.endswith('.zip') or value.endswith('.xml')):return
   if any(k in context for k in ('/lei2','lei-cdf','lei2-')):candidates['lei'].add(value)
   if any(k in context for k in ('/rr/','rr-cdf','/rr_','/rr-')):candidates['rr'].add(value)
 walk(manifest)
 if any(len(v)!=1 for v in candidates.values()):raise ValueError('GLEIF_manifest_ambiguous_or_changed')
 return {k:next(iter(v)) for k,v in candidates.items()}

def local(tag):return tag.rsplit('}',1)[-1]
def text(node,name):
 return next((x.text for x in node.iter() if local(x.tag)==name and x.text),None)

def xml_records(path,tag):
 with zipfile.ZipFile(path) as z:
  files=[n for n in z.namelist() if n.lower().endswith('.xml')]
  if len(files)!=1:raise ValueError('expected_single_GLEIF_XML')
  with z.open(files[0]) as stream:
   for _,element in ET.iterparse(stream,events=['end']):
    if local(element.tag)==tag:
     yield element;element.clear()

def gleif(downloads,rows):
 wanted={normal_id('lei',r.get('lei')) for r in rows if r.get('lei')};wanted.discard(None)
 if not wanted:return {},{'reason':'no_source_linked_LEIs_no_name_matching'}
 manifest=json.loads(downloads.small('https://goldencopy.gleif.org/api/v2/golden-copies/publishes','gleif-manifest.json'))
 publications=manifest.get('data') if isinstance(manifest,dict) else manifest
 if isinstance(publications,list):
  if not publications:raise ValueError('empty_GLEIF_manifest')
  publication=max(publications,key=lambda r:str(r.get('publishDate') or r.get('date') or ''))
 else:publication=manifest
 urls=golden_urls(publication);rr=downloads.bulk(urls['rr'],'gleif-rr.xml.zip')
 parents={};parent_ids=set()
 for record in xml_records(rr,'RelationshipRecord'):
  relationship=next((e for e in record.iter() if local(e.tag)=='Relationship'),None)
  if relationship is None:continue
  start=next((e for e in relationship if local(e.tag)=='StartNode'),None);end=next((e for e in relationship if local(e.tag)=='EndNode'),None)
  child=text(start,'NodeID') if start is not None else None;parent=text(end,'NodeID') if end is not None else None
  kind=text(relationship,'RelationshipType');status=text(relationship,'RelationshipStatus')
  if child not in wanted or not normal_id('lei',parent) or kind not in {'IS_DIRECTLY_CONSOLIDATED_BY','IS_ULTIMATELY_CONSOLIDATED_BY'}:continue
  parents.setdefault(child,[]).append({'lei':parent,'type':kind,'status':status,'registration_status':text(record,'RegistrationStatus'),'as_of':text(record,'LastUpdateDate'),'source_id':child+'>'+parent})
  parent_ids.add(parent)
 lei=downloads.bulk(urls['lei'],'gleif-lei.xml.zip');entities={}
 all_ids=wanted|parent_ids
 for record in xml_records(lei,'LEIRecord'):
  key=text(record,'LEI')
  if key not in all_ids:continue
  legal=next((e for e in record.iter() if local(e.tag)=='LegalAddress'),None)
  entities[key]={'legal_name':text(record,'LegalName'),'status':text(record,'EntityStatus'),'legal_country':text(legal,'Country') if legal is not None else None,
                 'parents':parents.get(key,[]),'source_updated_at':text(record,'LastUpdateDate')}
 return entities,{'publication':publication.get('publishDate') if isinstance(publication,dict) else None,'linked_LEIs':len(wanted),'found_LEIs':len(entities)}


def confirmed_ogl(page):
 # A generic footer is insufficient: require a dataset-specific licence assertion.
 plain=re.sub('<[^>]+>',' ',page)
 return OGL in page and bool(re.search(r'(Free Company Data Product.{0,400}Open Government Licence|Open Government Licence.{0,400}Free Company Data Product)',plain,re.I|re.S))

def companies_house(downloads,rows):
 page=downloads.small('https://download.companieshouse.gov.uk/en_output.html','companies-house-product.html').decode('utf-8','replace')
 if not confirmed_ogl(page):return {'licence_confirmed':False,'reason':'OGL_v3_not_confirmed_for_official_Free_Company_Data_Product','records':{}}
 links=re.findall(r'href=["\']([^"\']+BasicCompanyDataAsOneFile[^"\']+\.zip)["\']',page,re.I)
 if len(links)!=1:return {'licence_confirmed':False,'reason':'unambiguous_official_bulk_file_not_found','records':{}}
 url=urllib.parse.urljoin('https://download.companieshouse.gov.uk/en_output.html',links[0]);path=downloads.bulk(url,'companies-house.zip')
 wanted={r['companies_house_id'] for r in rows if r.get('legal_country')=='GB' and r.get('companies_house_id')};records={}
 with zipfile.ZipFile(path) as archive:
  files=[n for n in archive.namelist() if n.lower().endswith('.csv')]
  if len(files)!=1:raise ValueError('Companies_House_bulk_schema_changed')
  with archive.open(files[0]) as f:
   for row in csv.DictReader(io.TextIOWrapper(f,encoding='utf-8-sig')):
    number=(row.get('CompanyNumber') or '').strip()
    if number not in wanted:continue
    sic=row.get('SICCode.SicText_1') or '';sic_code=re.match(r'\s*(\d{4,5})\b',sic)
    records[number]={'company_number':number,'name':row.get('CompanyName'),'status':row.get('CompanyStatus'),'sic':sic_code[1] if sic_code else None,'sic_description':sic or None}
 return {'licence_confirmed':True,'licence_url':OGL,'reason':None,'records':records}


def collect(downloads,exchanges):
 stamp=datetime.now(timezone.utc).isoformat()
 directory=sec_directory(json.loads(downloads.small(SEC_DIRECTORY,'sec-directory.json')));ciks={r['cik'] for r in directory}
 submissions=selected_json_zip(downloads.bulk(SEC_SUBMISSIONS,'sec-submissions.zip'),ciks)
 missing=ciks-set(submissions)
 if missing:raise ValueError('SEC_submissions_incomplete_for_denominator')
 financials=selected_json_zip(downloads.bulk(SEC_FACTS,'sec-companyfacts.zip'),ciks,submissions)
 rows=wikidata(downloads);entities,gleif_report=gleif(downloads,rows)
 try:ch=companies_house(downloads,rows)
 except (OSError,ValueError):ch={'licence_confirmed':False,'reason':'official_product_licence_or_bulk_unavailable','records':{}}
 ecb=ecb_xml(downloads.small('https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml','ecb.xml'))
 economy={c:{} for c in ('US','GB')}
 for field,indicator in [('gdp','NY.GDP.MKTP.CD'),('growth','NY.GDP.MKTP.KD.ZG'),('inflation','FP.CPI.TOTL.ZG'),('population','SP.POP.TOTL')]:
  url='https://api.worldbank.org/v2/country/US;GB/indicator/'+indicator+'?format=json&source=2&mrnev=1&per_page=100'
  payload=json.loads(downloads.small(url,'wdi-'+field+'.json'))
  if not isinstance(payload,list) or len(payload)!=2 or payload[0].get('pages')!=1:raise ValueError('WDI_incomplete_response')
  for row in payload[1] or []:
   code=row['country']['id']
   if code not in economy:continue
   economy[code][field]={'value':row.get('value'),'period':row['date'],'unit':{'gdp':'USD','growth':'annual %','inflation':'CPI annual %','population':'people'}[field],
      'source':'World Bank','credit':'World Bank (CC BY 4.0)','source_id':indicator,'retrieved_at':stamp,'validation_status':'validated'}
 return {'snapshot':{'retrieved_at':stamp,'fixture':False},'sec':{'directory':directory,'submissions':submissions,'financials':financials},
   'wikidata':rows,'gleif':entities,'gleif_report':gleif_report,'companies_house':ch,'ecb':ecb,'economy':economy,
   'exchanges':exchanges,'source_manifest':downloads.manifest}
