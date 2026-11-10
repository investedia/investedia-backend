"""Read-only, per-globe-country coverage audit. Counts are observed lower bounds."""
import argparse
import hashlib
import json
import math
import urllib.request
import urllib.error
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASIC=['gdp_usd','gdp_growth','inflation','policy_rate','central_bank','unemployment','currency_code','population','government_debt_pct_gdp','current_account_pct_gdp','credit_rating','next_cb_meeting']
MARKET=['main_index','currency_usd','bond_10y','main_exchange','trading_hours','time_zone','top_companies']

def read(path,default=None):
    p=Path(path)
    return json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else default

def finite(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def date(x):return datetime.fromisoformat(x.replace('Z','+00:00'))
def positive(x):return finite(x) and x>0

def assets_for(code,markets,registry):
    if not code: return []
    symbols={a.get('px') for a in registry.values() if a.get('country')==code}
    return [a for a in markets if str(a.get('cc','')).upper()==code or a.get('s') in symbols]

def price_available(asset,prices):
    row=prices.get(asset.get('px'),{})
    return positive(row.get('p'))

def generate(root,live,now,endpoint_status):
    iso=read(root/'assets/globe/iso.json',{})
    shapes=read(root/'assets/globe/countries-50m.json',[])
    names={s[0] for s in shapes}
    reg=read(root/'data/registry.json',{}).get('assets',{})
    markets=read(root/'assets/globe/markets.json',{}).get('assets',[])
    prices=read(root/'assets/globe/news-prices.json',{}).get('assets',{})
    ex=read(root/'data/exchanges.json',{})
    econ=read(root/'assets/globe/economy.json',{}).get('countries',{})
    facts=read(root/'data/market-country-facts.json',{})
    basics=read(root/'data/country-basics.json',{}).get('countries',{})
    wb=read(root/'tools/globe-news/wb-countries.json',[{},[]])[1]
    regions={c['iso2Code']:c.get('region',{}).get('value') for c in wb}
    source_rows=live.get('data',{}).get('stories',[])
    dedup={}
    for s in source_rows:
        if s.get('id'):dedup[s['id']]=s
    rows=list(dedup.values());result=[]
    for name in sorted(names):
        code=iso.get(name);country_assets=assets_for(code,markets,reg)
        venues=[(mic,x) for mic,x in ex.items() if code and x.get('country')==code]
        ec=econ.get(code,{})
        known=basics.get(code,{})
        # Recognise documented aliases, not substrings or publisher origins.
        aliases={name}
        if code=='US':aliases|={'United States','USA'}
        if code=='GB':aliases|={'UK','Britain'}
        owned=[s for s in rows if s.get('location',{}).get('country') in aliases]
        recent={}
        for days in (7,30):
            selected=[]
            for s in owned:
                try:t=date(s['published_at'])
                except (ValueError,KeyError,TypeError):continue
                if now-timedelta(days=days)<=t<=now:selected.append(s)
            linked=[s for s in selected if any(isinstance(i,dict) and i.get('asset',{}).get('id') for i in s.get('impacts',[]))]
            recent[str(days)]={'observed_articles':len(selected),'observed_with_asset_impacts':len(linked),
                'share_with_asset_impacts':len(linked)/len(selected) if selected else None,
                'sources':dict(Counter(s.get('source',{}).get('name','unknown') for s in selected)),
                'complete_window':False,'exact_count':None}
        eq=[a for a in reg.values() if code and a.get('country')==code and a.get('class')=='equity']
        mk={'main_index':any(a.get('g')=='Index' and a.get('m') and positive(a.get('p')) for a in country_assets),
            'currency_usd':any(a.get('t')=='fx' and 'USD' in a.get('s','') and positive(a.get('p')) for a in country_assets),
            'bond_10y':any(code and a.get('class')=='rate' and a.get('country')==code and ('10' in a.get('name','') or '10' in a.get('px','')) and price_available(a,prices) for a in reg.values()),
            'main_exchange':bool(venues),'trading_hours':any(x.get('sessions') or (x.get('open') and x.get('close')) for _,x in venues),
            'time_zone':any(x.get('timezone') for _,x in venues),
            'top_companies':False}
        # A registered issuer is not proof of top-by-market-cap coverage.
        top_status='priced_listings_present_rank_unverified' if any(price_available(a,prices) for a in eq) else 'missing'
        bs={k:False for k in BASIC}
        for field,key in [('gdp_usd','gdp'),('gdp_growth','growth'),('inflation','infl'),('unemployment','unemp'),('population','pop')]:
            value=ec.get(key)
            if key=='growth' and value:value=value[-1]
            bs[field]=isinstance(value,list) and len(value)==2 and finite(value[1])
        bs['central_bank']=any(x.get('central_bank') for _,x in venues)
        bs['currency_code']=bool(facts.get(code,{}).get('currency') or any(x.get('currency') for _,x in venues))
        for k in BASIC:
            if isinstance(known.get(k),dict) and known[k].get('value') is not None:bs[k]=True
        n=recent['30']['observed_articles'];flags=[]
        if not code:flags.append('missing_iso_mapping_no_country_inferred')
        if n==0:flags.append('no_articles_observed_in_retained_feed')
        elif n<3:flags.append('fewer_than_3_observed_not_a_complete_30d_count')
        if n and not recent['30']['observed_with_asset_impacts']:flags.append('articles_but_no_verified_asset_connections')
        gdp=ec.get('gdp',[None,None])[1]
        result.append({'country':name,'iso2':code,'region':regions.get(code,'Unmapped / territory'),'news':recent,'markets':mk,'top_companies_status':top_status,
            'basics':bs,'flags':flags,'gdp_for_priority':gdp,'missing_markets':[k for k,v in mk.items() if not v],
            'missing_basics':[k for k,v in bs.items() if not v],
            'price_licensing':'legacy_saved_quotes_present_licence_unverified_not_eligible_for_new_links'})
    result.sort(key=lambda r:(-(r['gdp_for_priority'] or 0),-len(r['missing_markets']),r['country']))
    return {'schema':'investedia.coverage-audit/v1','audited_at':now.isoformat(),'api':endpoint_status,
        'limitations':['Live API retains at most 300 articles in a 48-hour window, not a complete 7/30-day archive.',
          'Zero observations are not proof of zero articles during 30 days.',
          'Source names are observed; the API does not identify the specific RSS feed for legacy records.',
          'Legacy quote presence does not establish redistribution rights, freshness, or top-company rank.'],
        'live_meta':live.get('meta',{}),'observed_live_articles':len(rows),'countries':result,
        'regions':{region:{'countries':sum(r['region']==region for r in result),'without_observed_articles':sum(r['region']==region and not r['news']['30']['observed_articles'] for r in result)} for region in sorted({r['region'] for r in result})},
        'totals':{'countries':len(result),'countries_with_observed_articles':sum(r['news']['30']['observed_articles']>0 for r in result),
            'missing_market_fields':sum(len(r['missing_markets']) for r in result),
            'missing_basic_fields':sum(len(r['missing_basics']) for r in result)}}

def markdown(report):
    out=['# Country coverage audit','', 'Not investment advice.','',
        'All article counts below are **observed lower bounds**, not complete 7/30-day counts. Live API retention is only 48 hours / 300 articles.',
        'The requested API hostname is recorded separately from the diagnostic workers.dev read. No live writes were performed.',
        '', 'Big economies are listed first using the saved, dated GDP snapshot. Regions with sparse observations must be reviewed next; territories remain in the table.',
        '', '| Country | ISO | Observed 7d / 30d | Asset links % | Markets present / 7 | Basics present / 12 | Missing markets | Missing basics |',
        '|---|---|---:|---:|---:|---:|---|---|']
    for r in report['countries']:
        share=r['news']['30']['share_with_asset_impacts'];pct='—' if share is None else f'{share*100:.1f}'
        out.append(f"| {r['country']} | {r['iso2']} | {r['news']['7']['observed_articles']} / {r['news']['30']['observed_articles']} | {pct} | {sum(r['markets'].values())} | {sum(r['basics'].values())} | {', '.join(r['missing_markets'])} | {', '.join(r['missing_basics'])} |")
    out+=['','## Regional priorities','', '| Region | Countries | No articles observed |','|---|---:|---:|']
    out += [f"| {region} | {counts['countries']} | {counts['without_observed_articles']} |" for region,counts in report['regions'].items()]
    out+=['','## Measurement limits','']+['- '+x for x in report['limitations']]
    out+=['','Full per-country source names, flags and per-field booleans are in `audit.json`.',
          '', '## Before / after status','',
          'This is the baseline. Proposed branches are not deployed; live before/after counts are unchanged. A complete 30-day comparison requires a licensed retained archive. Do not substitute saved historical feeds for live counts.',
          '', '## Cost and blockers','',
          'Audit: 0 Gemini calls, no scheduler, no paid service. Existing data and snapshots are read-only. api.investedia.com and official provider access are blocked by the current environment allowlist. No new secrets are needed for the audit.',
          'New feed sources and new market prices remain ineligible until reachability, robots/terms and redistribution licensing are verified. Existing Yahoo-derived quotes are not used for new connections.']
    return '\n'.join(out)+'\n'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args):raise ValueError('redirect_requires_review')

def fetch_api(url):
    from urllib.parse import urlsplit
    u=urlsplit(url)
    if u.scheme!='https' or u.username or u.password or u.query:raise ValueError('public_https_base_required')
    req=urllib.request.Request(url,headers={'User-Agent':'InvestediaRobot/1.0'})
    with urllib.request.build_opener(NoRedirect()).open(req,timeout=20) as response:
        raw=response.read(5_000_001)
        if len(raw)>5_000_000:raise ValueError('API_response_too_large')
        return json.loads(raw)

def main():
    p=argparse.ArgumentParser();p.add_argument('--live',type=Path);p.add_argument('--fetch',action='store_true')
    p.add_argument('--diagnostic-fallback',action='store_true');p.add_argument('--output',type=Path,default=ROOT/'data/coverage');p.add_argument('--now');a=p.parse_args()
    if not a.live and not a.fetch:p.error('choose --live FILE or --fetch')
    now=date(a.now) if a.now else datetime.now(timezone.utc)
    status={'requested':'https://api.investedia.com/v1/news','requested_status':'not_probed'}
    live=read(a.live,{}) if a.live else {}
    if a.fetch:
        try:live=fetch_api(status['requested']);status['requested_status']='ok'
        except (OSError,ValueError):
            status['requested_status']='blocked_or_unavailable'
            if not a.diagnostic_fallback:raise
            status['diagnostic_source']='https://investedia-live.adonaykabeya10.workers.dev/v1/news'
            live=fetch_api(status['diagnostic_source'])
    status['input_sha256']=hashlib.sha256(json.dumps(live,sort_keys=True).encode()).hexdigest()
    r=generate(ROOT,live,now,status)
    a.output.mkdir(parents=True,exist_ok=True);(a.output/'audit.json').write_text(json.dumps(r,indent=2)+'\n');(a.output/'AUDIT.md').write_text(markdown(r))
    print(json.dumps(r['totals']))
if __name__=='__main__':main()
