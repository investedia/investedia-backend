"""Official FX adapter and dated index-return correlations. No Yahoo requests."""
import argparse,json,math,itertools,urllib.request,urllib.error
import xml.etree.ElementTree as ET
from datetime import date,datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ECB='https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml'
NOTICE='https://www.ecb.europa.eu/services/disclaimer/html/index.en.html'

def valid(x):return isinstance(x,(float,int)) and not isinstance(x,bool) and math.isfinite(x) and x>0

def ecb_rates(raw):
 """Return currencies per USD, dated exactly as ECB observations, never invert silently."""
 root=ET.fromstring(raw);out={}
 for node in root.iter():
  day=node.get('time')
  if not day:continue
  date.fromisoformat(day);rates={'EUR':1.0}
  for c in node:
   if c.get('currency') and c.get('rate'):
    value=float(c.get('rate'))
    if valid(value):rates[c.get('currency')]=value
  usd=rates.get('USD')
  if not valid(usd):continue
  for code,value in rates.items():
   if code=='USD':continue
   out.setdefault('USD'+code,[]).append({'date':day,'close':value/usd})
 for rows in out.values():rows.sort(key=lambda x:x['date'])
 return out

def dated(rows):
 out={}
 for row in rows:
  day=row['date'];date.fromisoformat(day)
  if day in out:raise ValueError('duplicate_observation_date')
  if not valid(row.get('close')):raise ValueError('invalid_close')
  out[day]=row['close']
 return out

def correlation(a,b):
 """Require 31 shared observations -> exactly 30 aligned daily returns."""
 a,b=dated(a),dated(b);days=sorted(set(a)&set(b))[-31:]
 if len(days)<31:return None
 # Each return must span adjacent recorded trading observations in both series.
 # A missing intervening observation must not be relabelled a daily return.
 da,db=sorted(a),sorted(b)
 if any(da.index(y)!=da.index(x)+1 or db.index(y)!=db.index(x)+1 for x,y in zip(days,days[1:])):return None
 x=[a[v]/a[u]-1 for u,v in zip(days,days[1:])];y=[b[v]/b[u]-1 for u,v in zip(days,days[1:])]
 mx,my=sum(x)/30,sum(y)/30;vx=sum((v-mx)**2 for v in x);vy=sum((v-my)**2 for v in y)
 if vx<=1e-20 or vy<=1e-20:return None
 return {'correlation':sum((u-mx)*(v-my) for u,v in zip(x,y))/math.sqrt(vx*vy),'observations':30,'start':days[0],'end':days[-1]}

def exchange_connections(exchanges,series):
 moves={};pairs=[];missing={}
 for mic in exchanges:
  item=series.get(mic,{})
  if not item.get('source_url') or not item.get('licence_url') or item.get('redistribution_allowed') is not True:
   missing[mic]='no_licensed_dated_benchmark_series';continue
  values=dated(item.get('prices',[]));days=sorted(values)
  if len(days)<2:missing[mic]='insufficient_dated_observations';continue
  moves[mic]={'daily_pct':(values[days[-1]]/values[days[-2]]-1)*100,'as_of':days[-1],
              'source_url':item['source_url'],'licence_url':item['licence_url']}
 for left,right in itertools.combinations(sorted(moves),2):
  result=correlation(series[left]['prices'],series[right]['prices'])
  if result and result['correlation']>=.6:pairs.append({'from':left,'to':right,**result})
 return {'schema':'investedia.exchange-correlations/v1','method':'Pearson correlation of 30 aligned daily simple returns; at least 31 dated closes; threshold >= 0.6',
         'exchanges':moves,'pairs':pairs,'missing':missing}

class NoRedirect(urllib.request.HTTPRedirectHandler):
 # Same-site HTTPS redirects only (e.g. www.ecb.europa.eu -> ecb.europa.eu path moves); anything else still needs review.
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  from urllib.parse import urlsplit
  a,b=urlsplit(req.full_url),urlsplit(newurl)
  same=lambda h:'.'.join((h or '').split('.')[-3:])
  if b.scheme=='https' and same(a.hostname)==same(b.hostname):return super().redirect_request(req,fp,code,msg,headers,newurl)
  raise ValueError('redirect_requires_review')
def fetch(url):
 with urllib.request.build_opener(NoRedirect()).open(urllib.request.Request(url,headers={'User-Agent':'InvestediaRobot/1.0'}),timeout=20) as r:
  raw=r.read(5_000_001)
  if len(raw)>5_000_000:raise ValueError('source_too_large')
  return raw.decode('utf-8-sig')

def main():
 p=argparse.ArgumentParser();p.add_argument('--ecb-file',type=Path);p.add_argument('--fetch',action='store_true');p.add_argument('--series',type=Path);p.add_argument('--output',type=Path,default=ROOT/'data/coverage');a=p.parse_args()
 status='not_requested';fx={}
 try:
  if a.fetch:
   # Read the provider's own notice before preparing data for licensing review.
   fetch(NOTICE);fx=ecb_rates(fetch(ECB));status='fetched_pending_licence_review'
  elif a.ecb_file:fx=ecb_rates(a.ecb_file.read_text());status='offline_input_pending_licence_review'
 except (OSError,ValueError,ET.ParseError):status='blocked_or_unavailable'
 # Parsing a file never certifies its licence. This artifact is staging only.
 result={'schema':'investedia.official-market-staging/v1','source':ECB,'licence_notice':NOTICE,
         'status':status,'licence_reviewed':False,'data_mode':'staging_not_production','fx_series':fx,
         'index_prices':[],'bond_10y_prices':[],'gemini_calls':0}
 exchanges=json.loads((ROOT/'data/exchanges.json').read_text());series=json.loads(a.series.read_text()) if a.series else {}
 output=exchange_connections(exchanges,series);a.output.mkdir(parents=True,exist_ok=True)
 (a.output/'official-market-prices.json').write_text(json.dumps(result,indent=2)+'\n')
 (a.output/'exchange-correlations.json').write_text(json.dumps(output,indent=2)+'\n')
 print(json.dumps({'source_status':status,'fx_series':len(fx),'exchange_moves':len(output['exchanges']),'correlation_pairs':len(output['pairs']),'gemini_calls':0}))
if __name__=='__main__':main()
