"""Country-panel compatible basics from dated saved WDI data or official API.
No missing value is estimated. A refresh artifact is not a production deployment.
"""
import argparse,json,math,urllib.request,urllib.error
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
INDICATORS={
 'gdp_usd':('NY.GDP.MKTP.CD','USD','gdp'),
 'gdp_growth':('NY.GDP.MKTP.KD.ZG','annual %','growth'),
 'inflation':('FP.CPI.TOTL.ZG','annual CPI change %','infl'),
 'unemployment':('SL.UEM.TOTL.ZS','% labour force, ILO modelled estimate','unemp'),
 'population':('SP.POP.TOTL','people','pop'),
 'government_debt_pct_gdp':('GC.DOD.TOTL.GD.ZS','% GDP; central government debt, not general government','debt'),
 'current_account_pct_gdp':('BN.CAB.XOKA.GD.ZS','% GDP','current_account')}
EXTRA=['policy_rate','central_bank','currency_code','credit_rating','next_cb_meeting']
LICENCE='CC BY 4.0';LICENCE_URL='https://datacatalog.worldbank.org/public-licenses#cc-by'

def read(path,default=None):
 p=Path(path);return json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else default

def numeric(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)

def observation(code,field,year,value,retrieved,status):
 indicator,unit,_=INDICATORS[field]
 if not numeric(value) or not str(year).isdigit() or int(year)>datetime.now(timezone.utc).year:return None
 return {'value':value,'as_of':str(year),'units':unit,'source':'World Bank — World Development Indicators',
         'source_url':f'https://api.worldbank.org/v2/country/{code}/indicator/{indicator}?format=json&source=2',
         'indicator':indicator,'licence':LICENCE,'licence_url':LICENCE_URL,'retrieved_at':retrieved,'verification':status}

def saved(economy,iso,facts):
 countries={};missing={};codes=sorted(set(iso.values()))
 for code in codes:
  ec=economy.get('countries',{}).get(code,{});row={}
  for field,(_,_,legacy) in INDICATORS.items():
   value=ec.get(legacy)
   if legacy=='growth' and value:value=value[-1]
   row[field]=observation(code,field,*value,economy.get('asof'),'saved_snapshot_not_reverified') if isinstance(value,list) and len(value)==2 else None
   # Same legacy keys/types as existing country panels; no invented sample arrays.
   if ec.get(legacy) is not None:row[legacy]=ec[legacy]
  for key in EXTRA:row[key]=None
  fact=facts.get(code,{})
  if fact.get('currency') and 'CC BY 4.0' in fact.get('attribution',''):
   row['currency_code']={'value':fact['currency'],'as_of':fact.get('checked_at'),'units':'ISO 4217 code',
     'source':'GeoNames','source_url':fact['source'],'licence':'CC BY 4.0',
     'licence_url':'https://creativecommons.org/licenses/by/4.0/','verification':'saved_metadata'}
  countries[code]=row;missing[code]=[k for k in [*INDICATORS,*EXTRA] if row[k] is None]
 return {'schema':'investedia.country-basics/v1','asof':economy.get('asof'),'source':economy.get('source'),
  'source_url':economy.get('source_url'),'license':economy.get('license'),'indicators':economy.get('indicators',{}),
  'countries':countries,'missing':missing,'unmapped_globe_shapes':[],
  'notice':'Not investment advice. Annual data are not current-month readings. Null means unavailable, not zero.'}

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args):raise ValueError('redirect_requires_review')
def get(url):
 with urllib.request.build_opener(NoRedirect()).open(urllib.request.Request(url,headers={'User-Agent':'InvestediaRobot/1.0'}),timeout=25) as r:
  raw=r.read(10_000_001)
  if len(raw)>10_000_000:raise ValueError('response_too_large')
  return json.loads(raw)

def apply_indicator(result,field,response,retrieved):
 if not isinstance(response,list) or len(response)!=2 or not isinstance(response[1],list):raise ValueError('invalid_WDI_response')
 if int(response[0].get('pages',1))>1:raise ValueError('WDI_response_is_paginated_do_not_claim_complete')
 for item in response[1]:
  code=item.get('country',{}).get('id');row=result['countries'].get(code)
  if row is None:continue # excludes regional aggregates and guessed country codes
  obs=observation(code,field,item.get('date'),item.get('value'),retrieved,'official_API')
  if not obs:continue
  current=row.get(field)
  if current and int(current['as_of'])>int(obs['as_of']):continue
  row[field]=obs;legacy=INDICATORS[field][2]
  if legacy=='growth':
   history={str(y):v for y,v in row.get('growth',[])};history[obs['as_of']]=obs['value'];row['growth']=[[int(y),v] for y,v in sorted(history.items())]
  else:row[legacy]=[int(obs['as_of']),obs['value']]


def main():
 p=argparse.ArgumentParser();p.add_argument('--fetch',action='store_true');p.add_argument('--output',type=Path,default=ROOT/'data/country-basics.json');a=p.parse_args()
 iso=read(ROOT/'assets/globe/iso.json');economy=read(ROOT/'assets/globe/economy.json');facts=read(ROOT/'data/market-country-facts.json',{})
 result=saved(economy,iso,facts);result['unmapped_globe_shapes']=[s[0] for s in read(ROOT/'assets/globe/countries-50m.json') if s[0] not in iso]
 now=datetime.now(timezone.utc).isoformat();failures=[]
 if a.fetch:
  for field,(indicator,_,_) in INDICATORS.items():
   url=f'https://api.worldbank.org/v2/country/all/indicator/{indicator}?format=json&source=2&mrnev=1&per_page=20000'
   try:apply_indicator(result,field,get(url),now)
   except (OSError,ValueError,KeyError,TypeError):failures.append({'field':field,'url':url,'reason':'unavailable_or_invalid_official_response'})
 result['missing']={code:[k for k in [*INDICATORS,*EXTRA] if row[k] is None] for code,row in result['countries'].items()}
 result['refresh']={'attempted_at':now,'requested':a.fetch,'failed_fields':failures,'gemini_calls':0}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'countries':len(result['countries']),'numeric_observations':sum(row[k] is not None for row in result['countries'].values() for k in INDICATORS),'failed_refresh_fields':len(failures),'gemini_calls':0}))
 if failures:raise SystemExit('Official refresh incomplete; saved values retained with their original dates. Artifact saved.')
if __name__=='__main__':main()
