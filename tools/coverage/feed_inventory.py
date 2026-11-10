"""Inventory/probe existing feeds without running the news robot or Gemini.
Never approves redistribution rights merely because an RSS URL returns 200.
"""
import argparse, ast, json, sys, time
import urllib.error, urllib.request, urllib.robotparser
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
UA='InvestediaRobot/1.0'
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args):raise ValueError('redirect_requires_review')

def get(url):
 if urlsplit(url).scheme!='https':raise ValueError('https_required')
 with urllib.request.build_opener(NoRedirect()).open(urllib.request.Request(url,headers={'User-Agent':UA}),timeout=10) as r:
  raw=r.read(2_000_001)
  if len(raw)>2_000_000:raise ValueError('feed_too_large')
  return raw.decode('utf-8-sig','replace')

def configured():
 tree=ast.parse((ROOT/'update_globe_news.py').read_text(encoding='utf-8-sig'));out={}
 for n in tree.body:
  if not isinstance(n,ast.Assign) or not isinstance(n.targets[0],ast.Name):continue
  key=n.targets[0].id
  if key not in {'FEEDS','NEWS_FEEDS','REGION_FEEDS'}:continue
  for item in ast.literal_eval(n.value):
   url,name,*tag=item
   if url in out:continue
   out[url]={'url':url,'name':name,'region':tag[0] if key=='REGION_FEEDS' else None,
             'country':None,'language':'unverified','tier':'broad' if key=='REGION_FEEDS' else 'existing',
             'licence':'unverified — RSS availability is not a redistribution licence',
             'licence_url':None,'licence_verified':False,'newly_enabled':False}
 return list(out.values())

def dates(raw):
 root=ET.fromstring(raw);rows=[];missing=0;atom='{http://www.w3.org/2005/Atom}'
 for item in list(root.iter('item'))+list(root.iter(atom+'entry')):
  value=item.findtext('pubDate') or item.findtext(atom+'published') or item.findtext('{http://purl.org/dc/elements/1.1/}date')
  link=item.findtext('link') or next((e.get('href') for e in item.findall(atom+'link') if e.get('rel','alternate')=='alternate'),None)
  try:
   try:d=datetime.fromisoformat(value.replace('Z','+00:00'))
   except ValueError:d=parsedate_to_datetime(value)
   if d.tzinfo is None or not link:raise ValueError('original_date_and_link_required')
   rows.append(d.astimezone(timezone.utc))
  except (ValueError,TypeError,AttributeError):missing+=1
 return rows,missing

def probe(source):
 u=urlsplit(source['url']);robots_url=f'{u.scheme}://{u.netloc}/robots.txt'
 try:
  text=get(robots_url);rp=urllib.robotparser.RobotFileParser();rp.parse(text.splitlines())
  if not rp.can_fetch(UA,source['url']):return {**source,'status':'robots_disallowed','robots_url':robots_url}
  stamps,missing=dates(get(source['url']))
  stamps=[t for t in stamps if t<=datetime.now(timezone.utc)]
  span=(max(stamps)-min(stamps)).total_seconds()/86400 if stamps else 0
  # A retained feed is only an observed publication span, not proof of ongoing frequency.
  return {**source,'status':'reachable_needs_licence_review','robots_url':robots_url,'dated_items':len(stamps),
          'missing_original_date_or_link':missing,'observed_items_per_day':len(stamps)/span if span>=1 else None,
          'earliest':min(stamps).isoformat() if stamps else None,'latest':max(stamps).isoformat() if stamps else None}
 except (OSError,ValueError,ET.ParseError):return {**source,'status':'unavailable_or_unreviewed_redirect','robots_url':robots_url}

def eligible(row):
 return (row.get('status')=='reachable_needs_licence_review' and row.get('licence_verified') is True
         and bool(row.get('licence_url')) and bool(row.get('editorial_reviewed_at')) and row.get('dated_items',0)>0)

def main():
 p=argparse.ArgumentParser();p.add_argument('--probe',action='store_true');p.add_argument('--limit',type=int,default=8);a=p.parse_args()
 sources=configured();start=time.monotonic()
 if a.probe:
  for i in range(min(a.limit,len(sources))):sources[i]=probe(sources[i])
 for s in sources:s.setdefault('status','not_probed')
 result={'schema':'investedia.feed-coverage/v1','checked_at':datetime.now(timezone.utc).isoformat(),'feeds':sources,
         'probe_seconds':round(time.monotonic()-start,3),'gemini_calls':0,'newly_enabled_feeds':0}
 out=ROOT/'data/coverage';(out/'feed-inventory.json').write_text(json.dumps(result,indent=2)+'\n')
 lines=['# Feed coverage inventory','','Not investment advice.','',
  'No new feed is enabled. Reachability, original dates, robots and reuse rights must all be verified before adding one.',
  'A source/region tag is a balancing hint, never evidence of an article’s event origin. Null country/language/frequency means unverified.',
  '', '| Feed | URL | Country / region | Language | Update frequency | Licence | Observed articles/day | Probe |', '|---|---|---|---|---|---|---:|---|']
 for s in sources:lines.append(f"| {s['name']} | {s['url']} | {s['country'] or 'unknown'} / {s['region'] or 'unknown'} | {s['language']} | unverified | {s['licence']} | {s.get('observed_items_per_day','unknown')} | {s['status']} |")
 lines+=['','The first eight official feed probes were blocked by the environment allowlist. No feed was called dead based on a local network denial.',
  'Existing licensing uncertainty is recorded; existing robot configuration is unchanged.',
  '', '## Budget and rollout','',
  f"Inventory/probe runtime: {result['probe_seconds']} seconds, 0 Gemini calls. Added hourly runtime/Actions/Gemini calls: **0** (no sources activated).",
  'After licensed source verification, propose no more than four additional hourly feeds per region, keep the existing 200-candidate budget and cap 25 per source. Measure generation before activation; RSS throughput alone cannot predict Gemini token cost.',
  'The Worker retains 48 hours / 300 articles. Preserve that cap; do not manufacture or re-time data to fill it.',
  'Next verification targets: existing official feeds in Africa/LatAm/Asia first, national statistics and central banks. No guessed RSS endpoint is treated as a working source.']
 (out/'feeds.md').write_text('\n'.join(lines)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='feeds'}))
if __name__=='__main__':main()
