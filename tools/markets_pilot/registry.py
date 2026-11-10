"""Typed reconciliation and immutable artifact generation from approved source facts."""
import copy,hashlib,json,math,os,re,shutil
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from tools.markets_audit.methods import normal_id,fx_audit

CREDITS=['Wikidata (CC0)','GLEIF (CC0)','SEC EDGAR','World Bank (CC BY 4.0)','ECB']
MIC_COUNTRY={'XNYS':'US','XNAS':'US','XASE':'US','XLON':'GB'}
SEC_MIC={'NYSE':'XNYS','Nasdaq':'XNAS','NYSE American':'XASE'}
FX_EXCLUDED={'EUR':'shared/euro base','DKK':'ERM-II euro-linked','BGN':'euro-linked/shared transition','CZK':'conservative euro-tracker exclusion','HKD':'USD linked-rate system'}
MAX_ROWS=20000

def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def ident(prefix,value):return prefix+':'+hashlib.sha256(value.encode()).hexdigest()[:20]
def write(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n')
def read(path):return json.loads(Path(path).read_text())
def provenance(source,source_id,retrieved_at,validation_status='validated',**extra):
 return {'source':source,'source_id':source_id,'retrieved_at':retrieved_at,'validation_status':validation_status,**extra}
def finite(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)

def fiscal_year(facts,submissions):
 """Only facts from the latest actual 10-K, same accession/end/unit and flow start."""
 recent=submissions.get('filings',{}).get('recent',{})
 filings=[]
 for i,form in enumerate(recent.get('form',[])):
  if form!='10-K':continue
  def field(k):return (recent.get(k,[])+[None]*(i+1))[i]
  if field('accessionNumber') and field('reportDate') and field('primaryDocument'):
   filings.append({'filed':field('filingDate'),'end':field('reportDate'),'accn':field('accessionNumber'),'document':field('primaryDocument')})
 if not filings:return {'data':None,'reason':'no_10_K_in_submissions_snapshot'}
 filing=max(filings,key=lambda x:x['filed'] or '')
 concepts={'Revenues':['RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet','Revenue'],
           'NetIncomeLoss':['NetIncomeLoss','ProfitLoss'],'Assets':['Assets'],'Liabilities':['Liabilities']}
 candidates={}
 for metric,names in concepts.items():
  selected=[]
  for name in names:
   for taxonomy in ('us-gaap','ifrs-full'):
    entry=facts.get('facts',{}).get(taxonomy,{}).get(name,{})
    for unit,rows in entry.get('units',{}).items():
     if not re.fullmatch('[A-Z]{3}',unit):continue
     for row in rows:
      if row.get('form')!='10-K' or row.get('fp')!='FY' or row.get('accn')!=filing['accn'] or row.get('end')!=filing['end'] or not finite(row.get('val')):continue
      if metric in ('Revenues','NetIncomeLoss'):
       try:days=(datetime.fromisoformat(row['end'])-datetime.fromisoformat(row['start'])).days
       except (KeyError,ValueError):continue
       if not 330<=days<=400:continue
      selected.append({**row,'currency':unit,'concept':name,'taxonomy':taxonomy})
   if selected:break
  candidates[metric]=selected
 available=[{r['currency'] for r in rows} for rows in candidates.values() if rows]
 units=set.intersection(*available) if available else set()
 if len(units)!=1:return {'data':None,'reason':'missing_or_incompatible_reporting_currency'}
 currency=next(iter(units))
 flows=[{r['start'] for r in candidates[k] if r['currency']==currency} for k in ('Revenues','NetIncomeLoss') if candidates[k]]
 starts=set.intersection(*flows) if flows else set()
 if flows and len(starts)!=1:return {'data':None,'reason':'incompatible_or_ambiguous_annual_periods'}
 start=next(iter(starts)) if starts else None
 cik=normal_id('cik',submissions.get('cik'))
 accession=filing['accn'];document=filing['document']
 if not cik or not re.fullmatch(r'\d{10}-\d{2}-\d{6}',accession) or not re.fullmatch(r'[A-Za-z0-9_.-]+',document):return {'data':None,'reason':'invalid_filing_identity'}
 url=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-","")}/{document}'
 values={}
 for metric,rows in candidates.items():
  rows=[r for r in rows if r['currency']==currency and (metric not in ('Revenues','NetIncomeLoss') or r['start']==start)]
  distinct={(r['val'],r.get('start'),r['end'],r['concept'],r['taxonomy']) for r in rows}
  if len(distinct)!=1:values[metric]={'value':None,'reason':'conflicting_or_missing_reported_fact'};continue
  row=rows[0];values[metric]={'value':row['val'],'currency':currency,'concept':row['concept'],'taxonomy':row['taxonomy'],
       'start':row.get('start'),'end':row['end'],'fy':row.get('fy'),'fp':'FY','form':'10-K','accession':accession,'filing_url':url,'filed':filing['filed'],'source':'SEC EDGAR'}
 return {'data':{'period':{'start':start,'end':filing['end'],'form':'10-K','accession':accession},'currency':currency,'filing_url':url,'facts':values},'reason':None}


def fx_relationships(series):
 audit=fx_audit(series);kept=[];excluded=[]
 excluded_codes=dict(FX_EXCLUDED)
 for base,anchor in [('USD','EUR'),('EUR','USD')]:
  for pair in audit['bases'][base]['all_valid_pairs']:
   if anchor in pair['currencies'] and abs(pair['r'])>=.95:
    code=next(c for c in pair['currencies'] if c!=anchor)
    if code not in {'EUR','USD'}:excluded_codes.setdefault(code,f'low-information tracker screen: abs(r) with {anchor} >= 0.95, base {base}; not proof of a legal peg')
 for pair in audit['bases']['USD']['positive']+audit['bases']['USD']['negative']:
  reasons={c:excluded_codes[c] for c in pair['currencies'] if c in excluded_codes}
  if reasons:excluded.append({'currencies':pair['currencies'],'reasons':reasons});continue
  kept.append(pair)
 return {'schema':'markets.fx/v1','method':audit['method'],'base':'USD','as_of':audit['as_of'],'source':'ECB','credit':'ECB',
         'source_url':'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml','interpretation':audit['interpretation'],'reference_rate_notice':'ECB reference rates; not executable prices. USD has constant returns in the USD base, so no USD correlation edge is invented.',
         'relationships':kept,'excluded_currencies':excluded_codes,'excluded_pairs':excluded,'eur_base_sensitivity':audit['comparison'],
         'eur_results':audit['bases']['EUR'],'status':audit['status']}


def reconcile(raw):
 """SEC paired listings + qualified Wikidata statements; never merge by a label."""
 stamp=raw['snapshot']['retrieved_at'];datetime.fromisoformat(stamp.replace('Z','+00:00'))
 sec=raw['sec'];sub=sec['submissions'];facts=sec.get('companyfacts',{})
 directory=sec['directory'];denominator={normal_id('cik',r['cik']) for r in directory if r.get('exchange') in SEC_MIC}
 if None in denominator:raise ValueError('invalid_SEC_denominator_CIK')
 wikidata=raw['wikidata'];gleif=raw.get('gleif',{});entities={};issuers={};securities={};listings={};conflicts=[];excluded=[]
 by_cik=defaultdict(list);by_qid=defaultdict(list)
 for row in wikidata:
  qid=normal_id('qid',row.get('issuer_qid'))
  if not qid:continue
  by_qid[qid].append(row)
  if row.get('cik'):
   cik=normal_id('cik',row['cik'])
   if not cik:conflicts.append({'source_id':qid,'reason':'invalid_CIK'});continue
   by_cik[cik].append(row)
 # Reconcile typed issuer identifiers transitively. Labels are never edges.
 parent={}
 def find(key):
  parent.setdefault(key,key)
  if parent[key]!=key:parent[key]=find(parent[key])
  return parent[key]
 def union(a,b):
  x,y=find(a),find(b)
  if x!=y:parent[max(x,y)]=min(x,y)
 for row in wikidata:
  keys=[kind+':'+normal_id(kind,row.get(field)) for kind,field in [('qid','issuer_qid'),('cik','cik'),('lei','lei')] if normal_id(kind,row.get(field))]
  for key in keys:find(key)
  for key in keys[1:]:union(keys[0],key)
 groups=defaultdict(list)
 for row in wikidata:
  qid=normal_id('qid',row.get('issuer_qid'))
  if qid:groups[find('qid:'+qid)].append(row)
 def entity(cik,qid,name):
  lookup='cik:'+cik if cik else 'qid:'+qid
  rows=groups.get(find(lookup),[])
  all_ciks={normal_id('cik',r.get('cik')) for r in rows if normal_id('cik',r.get('cik'))}
  if cik:all_ciks.add(cik)
  if len(all_ciks)==1:cik=next(iter(all_ciks))
  qids={r['issuer_qid'] for r in rows};leis={r['lei'] for r in rows if r.get('lei')}
  bad=(len(all_ciks)>1 or len(qids)>1 or len(leis)>1 or any(not normal_id('lei',x) for x in leis))
  lei=next(iter(leis)) if len(leis)==1 and not bad else None
  qid=next(iter(qids)) if len(qids)==1 else qid
  key=('CONFLICT:'+digest(find(lookup)) if bad else ('LEI:'+lei if lei else ('CIK:'+cik if cik else 'QID:'+qid)))
  eid=ident('E',key);iid=ident('I',key)
  source=[provenance('SEC EDGAR',cik,stamp)] if cik in sub else []
  if qid:source.append(provenance('Wikidata (CC0)',qid,stamp,'conflicted' if bad else 'validated'))
  g=gleif.get(lei,{}) if lei else {}
  if lei and g:
   source.append(provenance('GLEIF (CC0)',lei,stamp))
  hqs=[r.get('hq') for r in rows if isinstance(r.get('hq'),dict) and r['hq'].get('location_kind')=='headquarters']
  hqs=[h for h in hqs if finite(h.get('lat')) and finite(h.get('lon')) and abs(h['lat'])<=90 and abs(h['lon'])<=180]
  unique={json.dumps(h,sort_keys=True):h for h in hqs};hq=next(iter(unique.values())) if len(unique)==1 else None
  company=raw.get('companies_house',{});ch=None
  if company.get('licence_confirmed'):
   ids={r.get('companies_house_id') for r in rows if r.get('legal_country')=='GB' and r.get('companies_house_id')}
   if len(ids)==1:ch=company.get('records',{}).get(next(iter(ids)))
  if ch:source.append(provenance('Companies House (OGL v3.0)',ch['company_number'],stamp))
  relationships=[]
  for parent in g.get('parents',[]):
   if not normal_id('lei',parent.get('lei')):continue
   relationships.append({**parent,'child_lei':lei,'source':'GLEIF (CC0)','label':'Reported parent / subsidiary relationship'})
  status='conflicted' if bad else 'verified'
  entities[eid]={'id':eid,'name':(ch or {}).get('name') or g.get('legal_name') or sub.get(cik,{}).get('name') or name,'lei':lei,'cik':cik if len(all_ciks)<=1 else None,'qid':qid if len(qids)<=1 else None,
      'identifier_assertions':{'cik':sorted(all_ciks),'qid':sorted(qids),'lei':sorted(leis)},'registered_status':(ch or {}).get('status') or g.get('status'),'legal_country':g.get('legal_country') or next((r.get('legal_country') for r in rows if r.get('legal_country')),None),
      'hq':hq,'hq_reason':None if hq else 'no_unambiguous_explicit_headquarters_coordinates',
      'reported_relationships':relationships,'source':source,'source_id':key,'retrieved_at':stamp,'validation_status':status,'verification_status':status}
  report=sub.get(cik,{}) if cik else {}
  industry={'code':str(report['sic']),'name':report.get('sicDescription'),'taxonomy':'SEC SIC','source':'SEC EDGAR'} if report.get('sic') else None
  if industry is None and ch and ch.get('sic'):industry={'code':ch['sic'],'name':ch.get('sic_description'),'taxonomy':'UK SIC','source':'Companies House (OGL v3.0)'}
  if industry is None:
   values={r.get('industry_qid') for r in rows if r.get('industry_qid')}
   if len(values)==1:industry={'code':next(iter(values)),'name':None,'taxonomy':'Wikidata industry QID','source':'Wikidata (CC0)'}
  issuers[iid]={'id':iid,'entity_id':eid,'name':entities[eid]['name'],'sector':industry,'financials':raw['sec'].get('financials',{}).get(cik) or fiscal_year(facts.get(cik,{}),report) if cik in sub else {'data':None,'reason':'not_SEC_filer'},
       'source':source,'source_id':key,'retrieved_at':stamp,'validation_status':status,'verification_status':status}
  if bad:conflicts.append({'issuer_id':iid,'reason':'conflicting_or_invalid_entity_identifiers'})
  return iid,rows,bad
 def listing(iid,rows,mic,ticker,source,active=True):
  if mic not in MIC_COUNTRY or not ticker:return
  paired=[r for r in rows if r.get('mic')==mic and r.get('ticker')==ticker]
  classifications={r.get('security_type') for r in paired if r.get('security_type')}
  if classifications and not classifications.intersection({'stock'}):excluded.append({'mic':mic,'ticker':ticker,'reason':'not_stock'});return
  isins={r.get('isin') for r in paired if r.get('isin')}
  conflict=(len(classifications)>1 or len(isins)>1 or any(not normal_id('isin',s) for s in isins) or issuers[iid]['verification_status']=='conflicted')
  isin=next(iter(isins)) if len(isins)==1 and not conflict else None
  security_qids={r.get('security_qid') for r in paired if r.get('security_qid')}
  sqid=next(iter(security_qids)) if len(security_qids)==1 else None
  if len(security_qids)>1:conflict=True
  sid=ident('S','ISIN:'+isin if isin else ('QID:'+sqid if sqid else f'{iid}:{mic}:{ticker}'))
  previous=securities.get(sid)
  if previous and previous['issuer_id']!=iid:conflict=True;conflicts.append({'security_id':sid,'reason':'security_identifies_multiple_issuers'})
  asserted_qids=set((previous or {}).get('identifier_assertions',{}).get('qid',[]))|{x for x in [sqid,(previous or {}).get('qid')] if x}
  if len(asserted_qids)>1:conflict=True;conflicts.append({'security_id':sid,'reason':'ISIN_has_conflicting_security_QIDs'})
  if previous and previous['verification_status']=='conflicted':conflict=True
  verified=active and 'stock' in classifications and not conflict
  status='conflicted' if conflict else ('verified' if verified else 'unverified')
  sources=[source]+[provenance('Wikidata (CC0)',r.get('statement_id') or r['issuer_qid'],stamp) for r in paired]
  record={'id':sid,'issuer_id':iid,'isin':isin,'identifier_assertions':{'isin':sorted(isins),'qid':sorted(asserted_qids)},'qid':sqid if len(asserted_qids)<=1 else None,'type':'stock' if 'stock' in classifications else None,
       'type_reason':None if classifications=={'stock'} else 'security_type_unverified','source':sources,'source_id':isin or sqid or f'{mic}:{ticker}',
       'retrieved_at':stamp,'validation_status':status,'verification_status':status}
  if previous and previous['issuer_id']!=iid:
   record={**previous,'issuer_id':None,'issuer_conflicts':sorted(set(previous.get('issuer_conflicts',[])+[previous.get('issuer_id'),iid])-{None}),'verification_status':'conflicted','validation_status':'conflicted','source':previous['source']+sources}
  if previous:record['source']=previous['source']+sources
  securities[sid]=record
  lid=ident('L',f'{sid}:{mic}:{ticker}')
  currency_values={r.get('currency') for r in paired if r.get('currency')}
  currency=next(iter(currency_values)) if len(currency_values)==1 else None
  listings[lid]={'id':lid,'issuer_id':iid,'issuer_name':issuers[iid]['name'],'security_id':sid,'ticker':ticker,'mic':mic,
       'country':MIC_COUNTRY[mic],'sector':issuers[iid]['sector'],'currency':currency,'currency_reason':None if currency else 'listing_currency_not_reported_by_approved_sources','isin':isin,'isin_reason':None if isin else 'no_unambiguous_source_ISIN','lei':entities[issuers[iid]['entity_id']]['lei'],
       'type':securities[sid]['type'],'active':active,'verification_status':status,'validation_status':status,
       'reason':'delisted_or_no_longer_in_submissions' if not active else ('identifier_conflict' if conflict else (None if verified else 'security_type_not_explicitly_stock')),
       'source':sources,'source_id':f'{mic}:{ticker}','retrieved_at':stamp,'stale':False}
  if conflict:conflicts.append({'listing_id':lid,'reason':'conflicting_security_or_issuer_identifiers'})
 for row in directory:
  mic=SEC_MIC.get(row.get('exchange'))
  if not mic:continue
  cik=normal_id('cik',row['cik']);report=sub.get(cik)
  if not report:raise ValueError('required_SEC_submission_missing:'+cik)
  iid,rows,bad=entity(cik,None,row['name'])
  ticker=row['ticker'];active=ticker in report.get('tickers',[])
  listing(iid,rows,mic,ticker,provenance('SEC EDGAR',f'{cik}:{mic}:{ticker}',stamp),active)
 for qid,rows in by_qid.items():
  uk=[r for r in rows if r.get('mic')=='XLON']
  if not uk:continue
  ciks={normal_id('cik',r.get('cik')) for r in rows if r.get('cik')}
  cik=next(iter(ciks)) if len(ciks)==1 else None
  iid,associated,bad=entity(cik,qid,uk[0].get('issuer_name') or qid)
  for row in uk:
   listing(iid,associated,'XLON',row['ticker'],provenance('Wikidata (CC0)',row.get('statement_id') or qid,stamp),row.get('active') is True)
 if len(listings)>MAX_ROWS:raise ValueError('pilot_row_limit_requires_review')
 # Retroactively quarantine all references to a conflicting shared security.
 for conflict in conflicts:
  if conflict.get('security_id'):
   sid=conflict['security_id'];securities[sid]['verification_status']='conflicted';securities[sid]['validation_status']='conflicted'
   for l in listings.values():
    if l['security_id']==sid:l['verification_status']='conflicted';l['validation_status']='conflicted';l['reason']=conflict['reason']
 # Include reported parent legal entities without inventing listed issuers for them.
 lei_entities={e['lei']:eid for eid,e in entities.items() if e.get('lei')}
 for entity_row in list(entities.values()):
  for relation in entity_row['reported_relationships']:
   parent_lei=relation['lei'];parent_id=lei_entities.get(parent_lei) or ident('E','LEI:'+parent_lei)
   if parent_id not in entities:
    g=gleif.get(parent_lei,{})
    entities[parent_id]={'id':parent_id,'name':g.get('legal_name'),'lei':parent_lei,'cik':None,'qid':None,'hq':None,
      'registered_status':g.get('status'),'reported_relationships':[],'source':[provenance('GLEIF (CC0)',parent_lei,stamp)],
      'source_id':parent_lei,'retrieved_at':stamp,'validation_status':'validated' if g else 'unverified','verification_status':'verified' if g else 'unverified'}
   relation.update(child_entity_id=entity_row['id'],parent_entity_id=parent_id,parent_name=entities[parent_id]['name'])
 return {'entities':entities,'issuers':issuers,'securities':securities,'listings':listings,'conflicts':conflicts,'excluded':excluded,
         'us_denominator_ciks':sorted(denominator),'retrieved_at':stamp,'fixture':raw['snapshot'].get('fixture',False)}


def coverage(model):
 result={}
 for country in ('US','GB'):
  rows=[r for r in model['listings'].values() if r['country']==country and r['active']]
  verified=[r for r in rows if r['verification_status']=='verified'];issuer_ids={r['issuer_id'] for r in verified}
  sectors=sum(bool(r['sector']) for r in verified);leis=sum(bool(r['lei']) for r in verified)
  hqs=sum(bool(model['entities'][model['issuers'][r['issuer_id']]['entity_id']]['hq']) for r in verified)
  issuer_sector=sum(bool(model['issuers'][iid]['sector']) for iid in issuer_ids)
  issuer_lei=sum(bool(model['entities'][model['issuers'][iid]['entity_id']]['lei']) for iid in issuer_ids)
  issuer_hq=sum(bool(model['entities'][model['issuers'][iid]['entity_id']]['hq']) for iid in issuer_ids)
  denom=len(model['us_denominator_ciks']) if country=='US' else None
  # US denominator is filers, not number of tickers/share classes.
  share=len(issuer_ids)/denom if denom else None
  sector=sectors/len(verified) if verified else None
  passed=bool(country=='US' and share is not None and share>=.8 and sector is not None and sector>=.7 and not model['conflicts'])
  result[country]={'verified_listed_stocks':len(verified),'verified_issuers':len(issuer_ids),'unverified':sum(r['verification_status']=='unverified' for r in rows),
    'conflicted':sum(r['verification_status']=='conflicted' for r in rows),'with_sector':sectors,'with_lei':leis,'with_hq':hqs,
    'sector_pct_of_verified':100*sector if country=='US' and sector is not None else None,'lei_pct_of_verified':100*leis/len(verified) if country=='US' and verified else None,'hq_pct_of_verified':100*hqs/len(verified) if country=='US' and verified else None,
    'issuers_with_sector':issuer_sector,'issuers_with_lei':issuer_lei,'issuers_with_hq':issuer_hq,
    'sector_pct_of_SEC_denominator':100*issuer_sector/denom if denom else None,'lei_pct_of_SEC_denominator':100*issuer_lei/denom if denom else None,'hq_pct_of_SEC_denominator':100*issuer_hq/denom if denom else None,
    'listing_issuer_denominator':denom,'issuer_coverage_pct':100*share if share is not None else None,'passes_launch_threshold':passed,
    'status':'launch' if passed else ('partial' if verified else 'not yet'),
    'denominator_reason':'SEC unique CIK filers with paired XNYS/XNAS/XASE directory listings; includes classification-pending filers' if country=='US' else 'No licensed official LSE listing denominator; no percentage inferred'}
 return result


def validate_model(model):
 for kind in ('entities','issuers','securities','listings','exchanges'):
  for key,row in model[kind].items():
   if not all(row.get(k) is not None for k in ('source','source_id','retrieved_at','validation_status')) or not row['source']:raise ValueError('missing_record_provenance')
   if datetime.fromisoformat(row['retrieved_at'].replace('Z','+00:00')).tzinfo is None:raise ValueError('provenance_requires_timezone')
 for row in model['issuers'].values():
  if row['entity_id'] not in model['entities']:raise ValueError('dangling_entity')
 for row in model['listings'].values():
  if row['issuer_id'] not in model['issuers'] or row['security_id'] not in model['securities']:raise ValueError('dangling_listing_reference')
  if row['verification_status']=='verified' and (not row['active'] or row['type']!='stock'):raise ValueError('verified_listing_must_be_active_stock')
  if row['isin'] and normal_id('isin',row['isin'])!=row['isin']:raise ValueError('invalid_ISIN')
  if row['lei'] and normal_id('lei',row['lei'])!=row['lei']:raise ValueError('invalid_LEI')
  if MIC_COUNTRY.get(row['mic'])!=row['country']:raise ValueError('invalid_pilot_market')


def build(raw,workspace):
 workspace=Path(workspace);workspace.mkdir(parents=True,exist_ok=True)
 # All validation/normalisation happens before touching last-good.json.
 model=reconcile(raw)
 model['exchanges']={mic:{**v,'mic':mic,'source':[provenance('exchange-calendars (Apache-2.0)',mic,model['retrieved_at'])],'source_id':mic,'retrieved_at':model['retrieved_at'],'validation_status':'validated' if v.get('timezone') and v.get('sessions') else 'unverified'} for mic,v in raw['exchanges'].items() if mic in MIC_COUNTRY}
 validate_model(model)
 if not model['listings']:raise ValueError('empty_registry_not_a_good_version')
 report=coverage(model)
 write(workspace/'reports/coverage-attempt.json',report)
 if not model['fixture'] and not any(c['verified_listed_stocks'] for c in report.values()):raise ValueError('no_verified_pilot_stocks_not_publishable')
 fx=fx_relationships(raw.get('ecb',{}));snapshot=model['retrieved_at']
 version=datetime.fromisoformat(snapshot.replace('Z','+00:00')).astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+digest({'model':model,'fx':fx,'economy':raw.get('economy',{})})[:12]
 target=workspace/'versions'/version;staging=workspace/('staging-'+version)
 if staging.exists():shutil.rmtree(staging)
 staging.mkdir()
 listing_rows=sorted(model['listings'].values(),key=lambda r:(r['issuer_name'].casefold(),r['id']))
 index={};shards=defaultdict(dict)
 for row in listing_rows:
  shards['rows/'+row['id'].split(':')[1][0]+'.json'][row['id']]=row
  if not row['active']:continue
  if row['verification_status'] not in ('verified','unverified','conflicted'):continue
  values={'all':'all','country':row['country'],'exchange':row['mic'],'currency':row['currency'],
          'sector':row['sector']['code'] if row['sector'] else None,'verified':'true' if row['verification_status']=='verified' else 'false'}
  for field,value in values.items():
   if value is None:continue
   key=field+':'+str(value);index.setdefault(key,[]).append(row['id'])
 filters={}
 for key,ids in index.items():
  path='filters/'+digest(key)[:20]+'.json';write(staging/path,ids);filters[key]=path
 for path,rows in shards.items():write(staging/path,rows)
 for iid,issuer in model['issuers'].items():
  entity=model['entities'][issuer['entity_id']]
  owned=[r for r in listing_rows if r['issuer_id']==iid]
  write(staging/('company/'+iid+'.json'),{'legal_entity':entity,'issuer':issuer,'securities':[s for s in model['securities'].values() if s['id'] in {r['security_id'] for r in owned}],
        'listings':owned,'reported_relationships':entity['reported_relationships'],'financials':issuer['financials'],'verification_status':issuer['verification_status']})
 exchanges=model['exchanges']
 for country in ('US','GB'):
  write(staging/('country/'+country+'.json'),{'iso2':country,'name':'United States' if country=='US' else 'United Kingdom',
        'exchanges':[v for mic,v in exchanges.items() if MIC_COUNTRY.get(mic)==country],
        'currency':'USD' if country=='US' else 'GBP','economy':raw.get('economy',{}).get(country,{}),
        'coverage':report[country],'hidden_unverified':report[country]['unverified']+report[country]['conflicted'],'verification_status':'verified' if report[country]['passes_launch_threshold'] else 'unverified','updated_at':snapshot})
  corporate=[]
  for row in listing_rows:
   if row['country']==country and row['verification_status']=='verified':
    for relation in model['entities'][model['issuers'][row['issuer_id']]['entity_id']]['reported_relationships']:
     if relation.get('status')=='ACTIVE' and relation.get('registration_status')=='PUBLISHED' and relation not in corporate:corporate.append(relation)
  write(staging/('connections/'+country+'.json'),{'corporate':corporate,'currency':[p for p in fx['relationships'] if ('USD' if country=='US' else 'GBP') in p['currencies']],
     'verification_status':'verified','hidden_unverified':report[country]['unverified']+report[country]['conflicted'],'method':fx['method'],'base':'USD','as_of':fx['as_of'],'source':['GLEIF (CC0)','ECB'],'interpretation':fx['interpretation']})
 write(staging/'fx-relationships.json',fx);write(staging/'coverage.json',report)
 # Typed records remain distinct in artifact; the API loads only bounded shards.
 write(staging/'records.json',model)
 runtime={'schema':'markets.registry/v1','version':version,'updated_at':snapshot,'countries':['US','GB'],'mic_allowlist':list(MIC_COUNTRY),'source_credits':CREDITS+(['Companies House (OGL v3.0)'] if raw.get('companies_house',{}).get('licence_confirmed') else []),'freshness':{'listings_as_of':snapshot,'ecb_as_of':fx['as_of'],'wdi_periods':{c:{k:v.get('period') for k,v in fields.items()} for c,fields in raw.get('economy',{}).items()},'calendars':{mic:{'as_of':e.get('calendar',{}).get('as_of'),'through':e.get('calendar',{}).get('valid_through')} for mic,e in exchanges.items()}},'publication_eligible':not model['fixture'],'fixture':model['fixture'],'filters':filters,'currencies':sorted({r['currency'] for r in listing_rows if r['currency']}),'coverage':report}
 write(staging/'api-manifest.json',runtime)
 files={str(p.relative_to(staging)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in staging.rglob('*.json')}
 manifest={'schema':'markets.registry/v1','version':version,'updated_at':snapshot,'countries':['US','GB'],'mic_allowlist':list(MIC_COUNTRY),
  'source_credits':CREDITS+(['Companies House (OGL v3.0)'] if raw.get('companies_house',{}).get('licence_confirmed') else []),
  'publication_eligible':not model['fixture'],'fixture':model['fixture'],'filters':filters,'files':files,
  'coverage':report,'counts':{kind:len(model[kind]) for kind in ('entities','issuers','securities','listings','exchanges')},'rows':len(listing_rows),'stored_bytes':sum(x['bytes'] for x in files.values()),
  'gleif_status':raw.get('gleif_report',{}),'companies_house_status':raw.get('companies_house',{}).get('reason','not_requested'),'source_manifest':raw.get('source_manifest',[])}
 write(staging/'manifest.json',manifest)
 target.parent.mkdir(exist_ok=True)
 if target.exists():
  for name,info in files.items():
   if not (target/name).exists() or hashlib.sha256((target/name).read_bytes()).hexdigest()!=info['sha256']:raise ValueError('existing_version_checksum_conflict')
  shutil.rmtree(staging)
 else:os.replace(staging,target)
 previous=read(workspace/'last-good.json').get('version') if (workspace/'last-good.json').exists() else None
 temp=workspace/'last-good.tmp';write(temp,{'version':version});os.replace(temp,workspace/'last-good.json')
 # A manual build cache retains only the last two immutable versions.
 versions=sorted((workspace/'versions').iterdir(),key=lambda p:p.name,reverse=True)
 keep={version,previous} if previous else {version}
 for old in versions:
  if old.name in keep:continue
  if len(keep)<2:keep.add(old.name);continue
  try:shutil.rmtree(old)
  except OSError:pass
 return manifest,target
