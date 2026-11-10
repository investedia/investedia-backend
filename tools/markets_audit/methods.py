"""Offline methods for the phase-01 audit. Never creates a production registry."""
import math
import re
from datetime import date
from itertools import combinations

ID_FIELDS={'legal_entity':('lei','cik','qid'),'issuer':('lei','cik','qid'),'security':('isin','qid'),'exchange':('mic','qid')}
ECB_CURRENCIES={'EUR','USD','JPY','BGN','CZK','DKK','GBP','HUF','PLN','RON','SEK','CHF','ISK','NOK','TRY','AUD','BRL','CAD','CNY','HKD','IDR','ILS','INR','KRW','MXN','MYR','NZD','PHP','SGD','THB','ZAR'}
PEGS={frozenset(('DKK','EUR')):'owner-specified low-information ERM-II pair; verify current regime',frozenset(('HKD','USD')):'owner-specified linked-rate pair; verify current regime'}

def valid_isin(value):
 if not isinstance(value,str) or not re.fullmatch('[A-Z]{2}[A-Z0-9]{9}[0-9]',value):return False
 digits=''.join(str(ord(c)-55) if c.isalpha() else c for c in value)
 return sum((int(c)*2//10+int(c)*2%10) if i%2 else int(c) for i,c in enumerate(reversed(digits)))%10==0

def normal_id(kind,value):
 value=str(value or '').strip().upper()
 if kind=='isin':return value if valid_isin(value) else None
 if kind=='lei':
  if not re.fullmatch('[A-Z0-9]{18}[0-9]{2}',value):return None
  digits=''.join(str(ord(c)-55) if c.isalpha() else c for c in value)
  return value if int(digits)%97==1 else None
 if kind=='cik':return value.zfill(10) if re.fullmatch('[0-9]{1,10}',value) and int(value)>0 else None
 if kind=='qid':return value if re.fullmatch('Q[1-9][0-9]*',value) else None
 if kind=='mic':return value if re.fullmatch('[A-Z0-9]{4}',value) else None
 return None

def match(left,right):
 kind=left.get('kind')
 if kind!=right.get('kind') or kind not in ID_FIELDS:return {'status':'no_match','reason':'different_record_types'}
 misplaced=set().union(*(set(r.get('ids',{})) for r in (left,right))) - set(ID_FIELDS[kind])
 if misplaced:return {'status':'unverified','reason':'identifier_level_mismatch','fields':sorted(misplaced)}
 for field in ('lei','cik'):
  a,b=left.get('issuer_ids',{}).get(field),right.get('issuer_ids',{}).get(field)
  if a and b:
   x,y=normal_id(field,a),normal_id(field,b)
   if not x or not y:return {'status':'unverified','reason':'invalid_issuer_identifier','fields':[field]}
   if x!=y:return {'status':'conflict','reason':'issuer_identifier_disagreement','fields':[field]}
 equal=[];conflicts=[];invalid=[]
 for field in ID_FIELDS[kind]:
  a,b=left.get('ids',{}).get(field),right.get('ids',{}).get(field)
  if not a or not b:continue
  x,y=normal_id(field,a),normal_id(field,b)
  if not x or not y:invalid.append(field)
  elif x==y:equal.append(field)
  else:conflicts.append(field)
 if invalid:return {'status':'unverified','reason':'invalid_identifier','fields':invalid}
 if conflicts:return {'status':'conflict','reason':'contradictory_identifiers','fields':conflicts}
 if equal:return {'status':'matched_identifier','via':equal[0],'publication_eligible':False}
 return {'status':'no_match','reason':'no_shared_typed_identifier_names_are_not_keys'}


def returns(series,calendar,base):
 result={}
 for currency in sorted(set().union(*(row.keys() for row in series.values())) & ECB_CURRENCIES):
  result[currency]={}
  for previous,current in zip(calendar,calendar[1:]):
   old,new=series[previous].get(currency),series[current].get(currency)
   if old is None or new is None:continue
   if base=='USD':
    old/=series[previous]['USD'];new/=series[current]['USD']
   if old>0 and new>0:result[currency][(previous,current)]=new/old-1
 return result


def pearson(a,b):
 if len(a)!=len(b) or len(a)<25:return None
 ma,mb=sum(a)/len(a),sum(b)/len(b)
 aa=sum((x-ma)**2 for x in a);bb=sum((x-mb)**2 for x in b)
 if aa<=1e-20 or bb<=1e-20:return None
 return max(-1,min(1,sum((x-ma)*(y-mb) for x,y in zip(a,b))/math.sqrt(aa*bb)))


def fx_audit(series):
 cleaned={}
 for day,row in series.items():
  date.fromisoformat(day)
  values={k:float(v) for k,v in row.items() if k in ECB_CURRENCIES and isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>0}
  if 'USD' not in values:continue
  if values.get('EUR',1.0)!=1.0:raise ValueError('invalid_EUR_base_identity')
  cleaned[day]={**values,'EUR':1.0}
 calendar=sorted(cleaned)[-31:]
 output={'schema':'investedia.fx-audit/v1','method':'Pearson of daily simple returns; latest 30 ECB observation intervals; >=25 identical intervals',
         'window':30,'minimum_aligned':25,'threshold_abs':.7,'as_of':calendar[-1] if calendar else None,
         'interpretation':'Co-movement, not capital flows and not causation.','shared_currency_policy':'one node per ISO4217; shared-currency country pairs are excluded by construction','bases':{},'comparison':{},'excluded':[]}
 for base in ('EUR','USD'):
  changes=returns(cleaned,calendar,base);positive=[];negative=[];all_pairs=[]
  for left,right in combinations(sorted(changes),2):
   if left==right:output['excluded'].append({'pair':[left,right],'reason':'shared_currency'});continue
   if frozenset((left,right)) in PEGS:
    if base=='EUR':output['excluded'].append({'pair':[left,right],'reason':PEGS[frozenset((left,right))]})
    continue
   aligned=sorted(set(changes[left])&set(changes[right]))
   corr=pearson([changes[left][d] for d in aligned],[changes[right][d] for d in aligned])
   if corr is None:continue
   pair={'currencies':[left,right],'r':corr,'observations':len(aligned),'base':base,'as_of':output['as_of']}
   all_pairs.append(pair)
   if corr>=.7:positive.append(pair)
   if corr<=-.7:negative.append(pair)
  output['bases'][base]={'positive':positive,'negative':negative,'all_valid_pairs':all_pairs}
 a={tuple(p['currencies']):p for p in output['bases']['EUR']['all_valid_pairs']};b={tuple(p['currencies']):p for p in output['bases']['USD']['all_valid_pairs']}
 common=sorted(set(a)&set(b));deltas=[{'currencies':list(k),'eur_r':a[k]['r'],'usd_r':b[k]['r'],'delta':b[k]['r']-a[k]['r']} for k in common]
 output['comparison']={'pairs_in_both_bases':len(common),'sign_changes':sum(a[k]['r']*b[k]['r']<0 for k in common),'pairs':deltas,
    'recommendation':'USD-rebased for phase 1, with base visible; keep EUR-base sensitivity. Neither base is invariant or causal.'}
 output['status']='computed_audit_only' if len(calendar)>=26 else 'insufficient_dated_ECB_observations'
 return output
