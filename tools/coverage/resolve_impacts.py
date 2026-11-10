"""Resolve existing, explicit article impacts to priced registry assets.
Never infer bank/sector/commodity effects from an article's country alone.
"""
import argparse,copy,json,math,re,time
from collections import Counter
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def read(path,default=None):
 p=Path(path);return json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else default

def eligible(asset,prices,licences,now):
 row=prices.get(asset.get('px'),{});value=row.get('p');lic=licences.get(asset.get('px'),{})
 if not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or value<=0:return 'missing_real_price'
 if lic.get('redistribution_allowed') is not True or not lic.get('licence_url') or not lic.get('source_url'):return 'unverified_price_licence'
 try:stamp=datetime.fromisoformat(lic['as_of'].replace('Z','+00:00'))
 except (ValueError,KeyError):return 'missing_price_timestamp'
 if stamp.tzinfo is None or not now-timedelta(days=7)<=stamp<=now:return 'stale_or_future_price'
 geo=asset.get('geo') or {}
 if geo.get('la') is None or geo.get('lo') is None:return 'missing_verified_coordinates'
 return None

def choose(impact,registry):
 country=impact.get('country');kind=impact.get('kind');name=impact.get('name','').casefold()
 candidates=[]
 for a in registry.values():
  if a.get('country')!=country:continue
  names={str(n).casefold() for n in [a.get('name'),a.get('official'),*(a.get('names') or [])] if n}
  if kind=='company' and a.get('class')=='equity' and (name in names or (impact.get('ticker') and impact['ticker']==a.get('sym'))):candidates.append(a)
  elif kind=='asset' and (name in names or impact.get('ticker')==a.get('px')):candidates.append(a)
  elif kind=='country' and impact.get('relation')=='currency' and a.get('class')=='fx':candidates.append(a)
 # An index/bond must actually be named; a rate decision alone never creates a stock effect.
 exact=[a for a in candidates if a.get('name','').casefold()==name]
 candidates=exact or candidates
 return candidates[0] if len(candidates)==1 else None

def resolve(articles,registry,prices,licences,now):
 out=copy.deepcopy(articles);reasons=Counter();added=0
 for article in out:
  for i in article.get('impacts',[]):
   if i.get('asset',{}).get('id'):continue
   if i.get('kind')=='sector':reasons['sector_requires_named_explicit_asset']+=1;continue
   if not i.get('why') or i.get('confidence')=='low':reasons['insufficient_relationship_evidence']+=1;continue
   asset=choose(i,registry)
   if not asset:reasons['ambiguous_or_missing_registry_asset']+=1;continue
   reason=eligible(asset,prices,licences,now)
   if reason:reasons[reason]+=1;continue
   g=asset['geo'];i['asset']={'id':asset['id'],'n':asset['name'],'c':asset['class'],'px':asset['px'],'la':g['la'],'lo':g['lo']};added+=1
 return out,{'resolved_impacts':added,'rejected':dict(reasons),'gemini_calls':0}

def country_map(registry):
 out={}
 for a in registry.values():
  code=a.get('country')
  if not code:continue
  c=out.setdefault(code,{'indices':[],'currencies':[],'rates':[],'listed_companies_unranked':[]})
  field={'index':'indices','fx':'currencies','rate':'rates','equity':'listed_companies_unranked'}.get(a.get('class'))
  if field:c[field].append(a['id'])
 return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--file',type=Path,default=ROOT/'assets/globe/news-live.json');p.add_argument('--write',action='store_true');a=p.parse_args();start=time.monotonic()
 reg=read(ROOT/'data/registry.json')['assets'];prices={a['s']:a for a in read(ROOT/'assets/globe/markets.json')['assets']};prices.update(read(ROOT/'assets/globe/news-prices.json')['assets']);licences=read(ROOT/'data/coverage/price-licences.json',{})
 data=read(a.file);rows,report=resolve(data['stories'],reg,prices,licences,datetime.now(timezone.utc));report['articles']=len(rows);report['seconds']=round(time.monotonic()-start,4)
 if a.write and report['resolved_impacts']:
  data['stories']=rows;a.file.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
 out=ROOT/'data/coverage';(out/'connection-country-map.json').write_text(json.dumps(country_map(reg),indent=2)+'\n');(out/'connections-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
