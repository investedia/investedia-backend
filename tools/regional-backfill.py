"""Manual RSS-only regional recovery. Real feed items; existing robot generation.
Network/model work is intended for GitHub runners. Importing this module is offline.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import sys
import threading
import time
import urllib.error
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools/coverage')]
import news_core as core
import update_globe_news as robot
import events
import resolve_impacts as evidence_resolver


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


uploader = module('regional_upload', ROOT/'tools/push-news-to-worker.py')
engine = module('regional_connections', ROOT/'tools/globe-news/connections.py')
UA = 'InvestediaRobot/1.0'
MAX_NEW = 150
MAX_REPAIRS = 150
MODEL_BATCH = 25
MAX_CALLS = 20
HARD_CALL_LIMIT = 40
REGIONAL_ORDER = ('af', 'latam', 'me', 'asia', 'oc', 'eu')
MAX_OUTPUT_TOKENS = 8192
MAX_PROMPT_BYTES = 65536
ALLOWED_REPAIR_FIELDS = {'impacts', 'ripples', 'sectors'}


def stamp(value):
    try: result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, AttributeError): result = parsedate_to_datetime(value)
    if result.tzinfo is None: raise ValueError('missing_original_timezone')
    return result.astimezone(timezone.utc)


def iso(value): return value.astimezone(timezone.utc).strftime(core.ISO)
def read(path, default=None):
    return json.loads(Path(path).read_text(encoding='utf-8-sig')) if Path(path).exists() else default


def contains_secret(value):
    text = json.dumps(value, ensure_ascii=False)
    return any(os.environ.get(k) and os.environ[k] in text for k in ('GEMINI_API_KEY', 'NEWS_INGEST_TOKEN'))


def write(path, value):
    if contains_secret(value): raise ValueError('secret_like_content_rejected')
    core.atomic_write(str(path), value)


class BudgetExceeded(BaseException):
    """Escapes the legacy robot's broad retry catches without issuing another call."""


class ModelUnavailable(BaseException):
    """A pinned model failed: do not let legacy retry/fallback loops spend the budget."""


def selected_model(explicit, live, saved):
    candidates = [explicit, live.get('meta', {}).get('model'),
        saved.get('tiers', {}).get('priority', {}).get('gemini_model'),
        saved.get('tiers', {}).get('priority', {}).get('model'),
        saved.get('gemini_model') if saved.get('gemini_ok') else None]
    for candidate in candidates:
        if candidate:
            if not isinstance(candidate, str) or not re.fullmatch(r'gemini-[A-Za-z0-9._-]{1,100}', candidate):
                raise ValueError('invalid_GEMINI_MODEL_name')
            return candidate
    raise ValueError('successful_hourly_model_unknown_set_GEMINI_MODEL')


def regional_candidates(candidates, now, limit=MAX_NEW):
    """Source tags balance selection; they are never event-location evidence."""
    groups = {region: [] for region in REGIONAL_ORDER}
    other = []
    for candidate in sorted(candidates, key=lambda c: core.score(c, now), reverse=True):
        region = candidate.get('feed_region')
        (groups[region] if region in groups else other).append(candidate)
    selected = []
    while len(selected) < limit and any(groups.values()):
        for region in REGIONAL_ORDER:
            if groups[region] and len(selected) < limit:
                selected.append(groups[region].pop(0))
    # Global publishers cannot consume regional reserves when regional feeds are thin.
    fallback = min(limit - len(selected), limit // 10, len(selected) // 4)
    return selected + other[:fallback]


class ModelBudget:
    def __init__(self, transport, limit=MAX_CALLS, deadline=None):
        if not 1 <= limit <= HARD_CALL_LIMIT: raise ValueError('gemini_calls_must_be_1_to_40')
        self.limit=limit;self.deadline=deadline;self.context={};self.call_log=[]
        self.transport = transport; self.calls = 0; self.discovery = 0; self.stop_reason = None
        self.usage=Counter(); self.usage_known_calls=0; self.by_model={}
    def get(self, url, data=None, headers=None, timeout=40, raw=False):
        if urlsplit(url).hostname != 'generativelanguage.googleapis.com':
            raise ValueError('regional_robot_cannot_fetch_article_pages_or_photos')
        if self.deadline is not None and time.monotonic() >= self.deadline:
            self.stop_reason='run_deadline_reached';raise BudgetExceeded(self.stop_reason)
        if ':generateContent' in url:
            if self.calls >= self.limit:
                self.stop_reason='fixed_model_call_budget_exhausted';raise BudgetExceeded(self.stop_reason)
            body = json.loads(data)
            prompt = body['contents'][0]['parts'][0]['text']
            if len(prompt.encode()) > MAX_PROMPT_BYTES:
                self.stop_reason='model_prompt_limit';raise BudgetExceeded(self.stop_reason)
            body.setdefault('generationConfig', {})['maxOutputTokens'] = MAX_OUTPUT_TOKENS
            data = json.dumps(body).encode(); self.calls += 1
            model=url.rsplit('/models/',1)[-1].split(':',1)[0]
            self.by_model.setdefault(model,Counter())['attempts']+=1
            self.call_log.append({'call':self.calls,'model':model,**self.context})
        else:
            if self.discovery >= 1: raise BudgetExceeded('model_discovery_already_completed')
            self.discovery += 1
        try:result=self.transport(url, data=data, headers=headers, timeout=min(timeout, 90), raw=raw)
        except (OSError, urllib.error.HTTPError) as error:
            if ':generateContent' not in url:raise
            self.stop_reason='configured_model_unavailable';raise ModelUnavailable('configured_model_request_failed') from None
        if ':generateContent' in url:
            try:
                usage=json.loads(result).get('usageMetadata')
                if isinstance(usage,dict):
                    self.usage_known_calls+=1
                    for key in ('promptTokenCount','candidatesTokenCount','thoughtsTokenCount','totalTokenCount'):
                        value=usage.get(key,0)
                        if isinstance(value,int) and value>=0:
                            self.usage[key]+=value;self.by_model[model][key]+=value
            except (ValueError,TypeError,AttributeError):pass
        return result


CLAUDE_PRICES = {'claude-haiku-5-5': (0.10, 0.50)}  # US$ per million input / output tokens
CLAUDE_MAX_TOKENS = 16000


class ClaudeWriter:
    """Optional stand-in for update_globe_news.gemini(prompt) (owner request 12 Nov 2026: catch-up with the Claude key,
    leaving the Gemini quota to live news). Same prompt, same call budget/deadline/prompt limits, plus a dollar cap."""
    def __init__(self, client, model, budget, max_usd):
        if model not in CLAUDE_PRICES: raise ValueError('unsupported_claude_model')
        self.client, self.model, self.budget, self.max_usd, self.spent = client, model, budget, float(max_usd), 0.0
    def cost(self, t_in, t_out):
        p_in, p_out = CLAUDE_PRICES[self.model]; return t_in*p_in/1e6 + t_out*p_out/1e6
    def __call__(self, prompt):
        b = self.budget
        if b.deadline is not None and time.monotonic() >= b.deadline: b.stop_reason='run_deadline_reached'; raise BudgetExceeded(b.stop_reason)
        if b.calls >= b.limit: b.stop_reason='fixed_model_call_budget_exhausted'; raise BudgetExceeded(b.stop_reason)
        if len(prompt.encode()) > MAX_PROMPT_BYTES: b.stop_reason='model_prompt_limit'; raise BudgetExceeded(b.stop_reason)
        if self.spent + self.cost(len(prompt.encode())//2, CLAUDE_MAX_TOKENS) > self.max_usd: b.stop_reason='dollar_cap_reached'; raise BudgetExceeded(b.stop_reason)
        b.calls += 1; b.by_model.setdefault(self.model, Counter())['attempts'] += 1
        b.call_log.append({'call': b.calls, 'model': self.model, **b.context})
        try: r = self.client.messages.create(model=self.model, max_tokens=CLAUDE_MAX_TOKENS, output_config={'effort': 'low'},
                                             messages=[{'role': 'user', 'content': prompt}])
        except Exception as e:
            code = getattr(e, 'status_code', None)
            b.by_model[self.model]['error_http_%s' % code] += 1
            b.stop_reason='configured_model_unavailable'; raise ModelUnavailable('configured_model_request_failed') from None
        u = getattr(r, 'usage', None); t_in, t_out = int(getattr(u, 'input_tokens', 0) or 0), int(getattr(u, 'output_tokens', 0) or 0)
        b.usage['input_tokens'] += t_in; b.usage['output_tokens'] += t_out; b.usage_known_calls += 1
        self.spent += self.cost(t_in, t_out); robot.status['gemini_model'] = self.model
        if r.stop_reason != 'end_turn': return []
        text = ''.join(getattr(x, 'text', '') for x in r.content if getattr(x, 'type', '') == 'text')
        try: return json.loads(re.sub(r'^```(json)?|```$', '', text.strip()))
        except ValueError: return []


BIG_ECONOMIES = {'United States of America', 'United Kingdom', 'Germany', 'France', 'Canada', 'Netherlands', 'Switzerland',
                 'Belgium', 'Austria', 'Ireland', 'Sweden', 'Denmark', 'Norway', 'Finland', 'Luxembourg'}
EXTRA_COUNTRY_CAP = 15


def thin_and_capped(stories, report):
    """Thin-region feeds (owner 12 Nov 2026): skip big-economy articles; at most EXTRA_COUNTRY_CAP per country per run."""
    kept=[];per=Counter();dropped=Counter()
    for s in stories:
        country=(s.get('location') or {}).get('country')
        if country in BIG_ECONOMIES:dropped['big_economy']+=1;continue
        if per[country]>=EXTRA_COUNTRY_CAP:dropped['country_cap']+=1;continue
        per[country]+=1;kept.append(s)
    report['thin_filter_dropped']=dict(dropped);return kept


HEADLINE_PROMPT = ('Below are news headlines. For each one NOT in English, translate it faithfully into clear English '
                   '(keep names, numbers, currencies and dates exactly; add nothing). Return only a JSON array of '
                   '{"i": <same i>, "english": "<English headline>"} for the non-English ones; omit English ones.\n\nHeadlines: ')


def english_headlines(writer, stories):
    """Owner request 12 Nov 2026: English headlines; the original is kept and the article marked translated."""
    listing=json.dumps([{'i':i,'headline':s['headline']} for i,s in enumerate(stories)],ensure_ascii=False)
    try:got=writer(HEADLINE_PROMPT+listing)
    except BudgetExceeded:return 0
    done=0
    for row in got if isinstance(got,list) else []:
        try:i,t=int(row['i']),str(row['english']).strip()
        except (KeyError,TypeError,ValueError):continue
        if 0<=i<len(stories) and 12<=len(t)<=300 and t!=stories[i]['headline'] and not stories[i].get('headline_translated'):
            s=stories[i];s.update(original_headline=s['headline'],headline=t,headline_translated=True);done+=1
    return done


def request(url, data=None, headers=None, timeout=15, raw=False):
    u = urlsplit(url)
    if u.scheme != 'https' or u.username or u.password: raise ValueError('public_https_required')
    req = urllib.request.Request(url, data=data, headers={**(headers or {}), 'User-Agent': UA})
    with urllib.request.build_opener(uploader.NoRedirect()).open(req, timeout=timeout) as response:
        content = response.read(2_000_001)
        if len(content) > 2_000_000: raise ValueError('response_too_large')
    return content if raw else content.decode('utf-8-sig', 'replace')


# Owner request 12 Nov 2026 ("add 6" + "check africa batch"): thin-region feeds checked live that day (feed works,
# robots.txt allows feed and articles, pages carry a publish date, no paywall). Used only by this tool, never the hourly robot.
EXTRA_FEEDS_2026_11_12 = [
    ('https://www.jamaicaobserver.com/feed/', 'Jamaica Observer', 'latam'),
    ('https://www.diariolibre.com/rss/portada.xml', 'Diario Libre', 'latam'),
    ('https://barbadostoday.bb/feed/', 'Barbados Today', 'latam'),
    ('https://24.kg/rss', '24.kg', 'asia'),
    ('https://www.gazeta.uz/oz/rss/', 'Gazeta.uz', 'asia'),
    ('https://islandsbusiness.com/feed/', 'Islands Business', 'oc'),
    ('https://rss.punchng.com/v1/category/latest_news', 'Punch Nigeria', 'af'),
    ('https://capitalethiopia.com/feed/', 'Capital Ethiopia', 'af'),
    ('https://www.tanzaniainvest.com/feed', 'TanzaniaInvest', 'af'),
    ('https://www.lusakatimes.com/feed/', 'Lusaka Times', 'af'),
    ('https://www.ktpress.rw/feed/', 'KT Press Rwanda', 'af'),
    ('https://www.independent.co.ug/feed/', 'The Independent Uganda', 'af'),
]
SOURCE_SETS = {'all': None, 'official-2026-11-11': lambda: {u for u,_,_ in robot.OFFICIAL_REGION_FEEDS_2026_11_11},
               'extra-2026-11-12': lambda: {u for u,_,_ in EXTRA_FEEDS_2026_11_12}}  # named sets for --sources


def feed_sources(inventory, only=None):
    health = {r['url']: r for r in inventory.get('feeds', [])}
    if not health and only is None: raise ValueError('feed_inventory_required_run_coverage_fetch_first')
    configured = [(u,n,'',r) for u,n,r in robot.REGION_FEEDS]
    configured += [(u,n,h,None) for u,n,h in robot.FEEDS if robot.OFFICIAL_RE.search(n)]
    if only is not None: configured += [(u,n,'',r) for u,n,r in EXTRA_FEEDS_2026_11_12]  # only through a named set
    if only is not None: configured = [c for c in configured if c[0] in only]  # a named set: feeds added after the last coverage inventory
    seen = set(); enabled = []; skipped = []
    for url,name,hint,region in configured:
        if url in seen: continue
        seen.add(url); meta = health.get(url,{})
        status = str(meta.get('status',''))
        blocked = (meta.get('enabled') is False or meta.get('robots_allowed') is False
                   or 'robots_disallow' in status or 'unavailable' in status or status == 'dead')
        row = {'url':url,'name':name,'hint':hint,'region':region}
        (skipped if blocked else enabled).append({**row, 'reason':status or 'disabled'} if blocked else row)
    return enabled, skipped


def parse_feed(raw, source, now, days):
    if not 1 <= days <= 30: raise ValueError('days_must_be_1_to_30')
    root = ET.fromstring(raw); atom = '{http://www.w3.org/2005/Atom}'
    rows = []; rejected = Counter(); all_dates = []
    items = list(root.iter('item')) + list(root.iter(atom+'entry'))
    for item in items[:1000]:
        title = item.findtext('title') or item.findtext(atom+'title') or ''
        url = item.findtext('link') or next((e.get('href','') for e in item.findall(atom+'link') if e.get('rel','alternate') == 'alternate'), '')
        raw_date = item.findtext('pubDate') or item.findtext(atom+'published') or item.findtext('{http://purl.org/dc/elements/1.1/}date')
        try:
            t = stamp(raw_date)
            u = urlsplit(url)
            if not title.strip() or u.scheme not in {'http','https'} or not u.hostname or u.username or u.password:
                raise ValueError('invalid_original_link_or_title')
        except (ValueError, TypeError, AttributeError):
            rejected['invalid_original_date_link_or_title'] += 1; continue
        if t > now: rejected['future_original_date'] += 1; continue
        all_dates.append(t)
        if t < now-timedelta(days=days): rejected['outside_requested_days'] += 1; continue
        desc = item.findtext('description') or item.findtext(atom+'summary') or ''
        desc = re.sub(r'<[^>]+>', ' ', robot.html.unescape(desc)).strip()[:400]
        row = {'title':robot.html.unescape(title).strip(),'url':url.strip(),'source':source['name'],
               'published':iso(t),'kind':'official' if source['hint'] or robot.OFFICIAL_RE.search(source['name']) else 'news',
               'hint':source['hint'],'desc':desc,'feed_url':source['url'], 'feed_region':source['region']}
        if source['region']: row['region'] = source['region'] # balancing only; not passed as event location
        if contains_secret(row): rejected['secret_like_content'] += 1; continue
        row['chash'] = core.content_hash(row); rows.append(row)
    meta = {'name':source['name'],'url':source['url'],'region_hint':source['region'], 'items_in_window':len(rows),
            'oldest_original_date_reached':iso(min(all_dates)) if all_dates else None,
            'latest_original_date':iso(max(all_dates)) if all_dates else None,
            'oldest_at_or_before_window_start':bool(all_dates and min(all_dates) <= now-timedelta(days=days)),
            'rejected':dict(rejected),'status':'fetched'}
    if len(items)>1000:meta['rejected']['feed_item_safety_limit']=len(items)-1000
    return rows,meta


class FeedFetcher:
    def __init__(self, get=request):
        self.get=get; self.locks={}; self.lock=threading.Lock(); self.policies={}; self.last={}
    def one(self, source, now, days):
        host=urlsplit(source['url']).netloc
        with self.lock: lock=self.locks.setdefault(host,threading.Lock())
        with lock:
            try:
                if host not in self.policies:
                    rp=urllib.robotparser.RobotFileParser()
                    try:raw=self.get('https://'+host+'/robots.txt')
                    except urllib.error.HTTPError as e:
                        if e.code != 404:raise
                        raw=''
                    if '<html' in raw.lower() or '<!doctype html' in raw.lower():raise ValueError('invalid_robots_response')
                    rp.parse(raw.splitlines());self.policies[host]=rp
                rp=self.policies[host]
                if not rp.can_fetch(UA,source['url']):return [],{**source,'status':'robots_disallowed'}
                delay=max(1,rp.crawl_delay(UA) or rp.crawl_delay('*') or 0)
                rate=rp.request_rate(UA) or rp.request_rate('*')
                if rate:delay=max(delay,rate.seconds/rate.requests)
                wait=delay-(time.monotonic()-self.last.get(host,time.monotonic()))
                if wait>15:return [],{**source,'status':'rate_limit_wait_deferred'}
                if wait>0:time.sleep(wait)
                raw=self.get(source['url']);self.last[host]=time.monotonic()
                return parse_feed(raw,source,now,days)
            except (OSError,ValueError,ET.ParseError):return [],{**source,'status':'unavailable_or_redirect_requires_review'}


def source_urls(article):
    return [s['url'] for s in [article.get('source') or {},*(article.get('sources') or [])] if s.get('url')]


def unique_articles(rows):
    # Prefer full API/current records over compact 48h duplicates.
    result={}
    for row in rows:
        if row.get('id') and (row['id'] not in result or len(json.dumps(row))>len(json.dumps(result[row['id']]))):result[row['id']]=row
    return list(result.values())


def dedupe(candidates, articles, seen):
    ids={s['id'] for s in articles}; urls={core.canon(u) for s in articles for u in source_urls(s)}
    out=[];rejected=Counter()
    for c in candidates:
        sid='n'+hashlib.md5(c['url'].encode()).hexdigest()[:10];url=core.canon(c['url'])
        if sid in ids or url in urls:rejected['duplicate_id_or_source_url']+=1;continue
        if url in seen and seen[url].get('h')==c['chash']:rejected['seen_unchanged_candidate']+=1;continue
        ids.add(sid);urls.add(url);out.append(c)
    return out,dict(rejected)


def split48(rows,now):
    recent=[];history=[]
    for s in rows:
        t=stamp(s['published_at'])
        if t>now:raise ValueError('future_publication')
        (recent if t>=now-timedelta(hours=48) else history).append(s)
    return recent,history


def region_of(row): return (row.get('location') or {}).get('region') or 'none'

def protected(row): return {k:v for k,v in row.items() if k not in ALLOWED_REPAIR_FIELDS}
def batches(rows):
    batch=[]
    for row in rows:
        if len(json.dumps(row).encode())>350_000:raise ValueError('article_exceeds_ingest_size_limit')
        if batch and (len(batch)>=80 or len(json.dumps(batch+[row]).encode())>350_000):yield batch;batch=[]
        batch.append(row)
    if batch:yield batch


def named_asset(article, impact):
    fields=('headline','_feed_description') if '_feed_description' in article else ('headline','summary')
    text=' '.join(str(article.get(k) or '') for k in fields)
    name=impact.get('name','')
    if len(name)>=3 and re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',text,re.I):return True
    ticker=impact.get('ticker') or ''
    return bool(len(ticker)>=2 and re.search(r'(?<!\w)'+re.escape(ticker)+r'(?!\w)',text))


def evidence(articles,now,registry,prices,licences):
    resolved,_=evidence_resolver.resolve(articles,registry,prices,licences,now)
    reasons={}
    for s in resolved:
        accepted=[];reject=[]
        for i in s.get('impacts') or []:
            if not named_asset(s,i):reject.append({'asset':i.get('name'),'reason':'no_named_asset_in_reporting'});continue
            a=i.get('asset') or {};asset=registry.get(a.get('id'),{});px=asset.get('px') or a.get('px')
            price=prices.get(px,{}).get('p')
            if not isinstance(price,(int,float)) or isinstance(price,bool) or not math.isfinite(price) or price<=0:
                reject.append({'asset':i.get('name'),'reason':'no_real_price_data'});continue
            if i.get('kind')=='sector' or i.get('confidence')=='low' or not a.get('id'):
                reject.append({'asset':i.get('name'),'reason':'unresolved_or_broad_sector_relationship'});continue
            i['scorable']=False;accepted.append(i)
        s['impacts']=accepted
        if not accepted and not reject:reject=[{'reason':'no_named_asset_or_supported_impact'}]
        reasons[s['id']]=reject
    return resolved,reasons


def generate_new(candidates,now,box,by_iso,sym,batch_size=MODEL_BATCH,budget=None):
    out=[];processed=[]
    if not 1 <= batch_size <= 40:raise ValueError('batch_size_must_be_1_to_40')
    balanced=regional_candidates(candidates,now)
    for start in range(0,len(balanced),batch_size):
        part=balanced[start:start+batch_size]
        if budget is not None:budget.context={'purpose':'new_articles','input_candidates':len(part),'by_feed_region':dict(Counter(c.get('feed_region') or 'global' for c in part))}
        robot.status['gemini_ok']=False
        try:
            got=robot.pick_stories(part,box,by_iso,sym,set(by_iso),min(batch_size,MAX_NEW-len(out)),
                                   preserve_source=True,feed_only=True,backfill=True)
        except BudgetExceeded:break
        if not robot.status.get('gemini_ok'):break
        lookup={'n'+hashlib.md5(c['url'].encode()).hexdigest()[:10]:c for c in part}
        for s in got[:MAX_NEW-len(out)]:
            original=lookup.get(s['id'])
            if not original or s['headline']!=original['title'] or s['published_at']!=original['published'] or s['source']['url']!=original['url']:raise ValueError('source_identity_changed')
            s.update(backfilled=True,backfilled_at=iso(now),backfill_provenance={'version':'regional-backfill-v1',
                     'original_published_at':s['published_at'],'feed_url':original['feed_url']})
            s['_feed_description']=original['desc'];out.append(s)
        processed.extend(part)
    return out,processed


def repair_existing(rows,by_iso,attempts,budget=None):
    pending=[s for s in rows if not s.get('impacts') and attempts.get(s['id']) != core.content_hash({'title':s.get('headline'),'desc':s.get('summary')})][:MAX_REPAIRS]
    changed=[];checked=[]
    for start in range(0,len(pending),40):
        part=pending[start:start+40];copies=copy.deepcopy(part)
        if budget is not None:budget.context={'purpose':'connection_repairs','input_candidates':len(part)}
        completed=[]
        try:robot.backfill_impacts(copies,set(by_iso),limit=len(copies),include_empty=True,completed_ids=completed)
        except BudgetExceeded:break
        for old,new in zip(part,copies):
            if old['id'] not in completed:continue
            patched=copy.deepcopy(old)
            for key in ALLOWED_REPAIR_FIELDS:
                if key in new:patched[key]=copy.deepcopy(new[key])
            if protected(old)!=protected(patched):raise ValueError('immutable_article_fields_changed')
            checked.append(old['id']);changed.append(patched)
    return changed,checked


def draw_connections(rows,prices):
    previous=engine.load
    def load(name,default):
        if name=='markets.json':return {'assets':[x for x in prices if isinstance(x.get('p'),(int,float)) and not isinstance(x['p'],bool) and math.isfinite(x['p']) and x['p']>0]}
        return previous(name,default)
    engine.load=load
    try:return engine._rules(read(ROOT/'assets/globe/iso.json',{}),prices,rows)
    finally:engine.load=previous


def plan(rows,cap,now,days,connections_only=False):
    recent,older=split48(rows,now)
    known=set(cap.get('history_ids',[]))
    count=cap.get('history_count')
    room=max(0,int(cap.get('history_capacity',240))-int(count)) if count is not None else None
    accepted=[];deferred=[]
    for row in older:
        needed=0 if row['id'] in known else 1
        if needed and (room is None or room<=0):
            deferred.append({'id':row['id'],'reason':'history_capacity_unknown_requires_updated_Worker' if room is None else 'history_capacity_240_no_truncation'});continue
        accepted.append(row)
        if needed:room-=1
    return recent,accepted,deferred


def publish(rows,worker,now,days,connections_only,cap,acknowledged,originals=None):
    if not rows:return []
    _,all_older=split48(rows,now)
    if all_older and cap.get('regional_backfill_version')!=1:raise ValueError('Worker_regional_history_support_requires_separate_approved_deployment')
    recent,older,deferred=plan(rows,cap,now,days,connections_only)
    if older and cap.get('regional_backfill_version')!=1:raise ValueError('Worker_regional_history_support_requires_separate_approved_deployment')
    if older and connections_only and cap.get('history_connections_version')!=1:raise ValueError('Worker_history_connection_updates_not_supported')
    # Capacity rejections are explicit and returned; never evict or truncate history.
    current=json.loads(request(worker+'/v1/news?regional_read='+str(time.time_ns())))
    generated=current.get('meta',{}).get('fetched_at')
    if not generated:raise ValueError('current_feed_timestamp_unknown')
    for mode,items in [('history',older),('rolling',recent)]:
        def send(part):
            body={'stories':part,'generated_at':generated}
            if mode=='history':
                body={'mode':'gap-history-v1','purpose':'regional-backfill','connections_only':connections_only,
                      'window':{'start':iso(now-timedelta(days=days)),'end':iso(now)},'stories':part}
                if connections_only:body['originals']={s['id']:protected(originals[s['id']]) for s in part}
            if len(json.dumps(body).encode())>350000:
                if len(part)<2:raise ValueError('article_exceeds_ingest_size_limit')
                mid=len(part)//2;send(part[:mid]);send(part[mid:]);return
            result=uploader.push(worker,os.environ.get('NEWS_INGEST_TOKEN',''),body)
            if not result.get('ok'):raise ValueError('ingest_not_acknowledged')
            acknowledged(part)
        for part in batches(items):send(part)
    return deferred


def cached_patch(original,patch):
    result=copy.deepcopy(original)
    for field in ALLOWED_REPAIR_FIELDS:
        if field not in patch:continue
        if field=='impacts':
            if original.get('impacts'):continue
            result[field]=[copy.deepcopy(i) for i in patch[field] if named_asset(original,i)]
        else:result[field]=copy.deepcopy(patch[field])
    return result


def archive(rows,base,now):
    # Existing compact event metadata is immutable too: update only asset fields.
    old={}
    for path in base.glob('????-??-??.json'):
        old.update({e['id']:e for e in read(path,{}).get('events',[])})
    copies=copy.deepcopy(rows)
    for row in copies:
        if row['id'] in old:row['published_at']=old[row['id']]['at']
    events.upsert(copies,base=str(base))
    for day in {row['published_at'][:10] for row in copies}:
        path=base/(day+'.json');data=read(path,{})
        for i,event in enumerate(data.get('events',[])):
            if event['id'] in old:
                data['events'][i]={**old[event['id']],'assets':event['assets'],'cos':event['cos']}
        events._write(str(path),data)
    events.write_threads(30,now,base=str(base),out=str(base.parent/'threads.json'),reg=robot.R.get())


def run(days,dry_run,connections_only,inventory,output,worker,gemini_model=None,gemini_calls=MAX_CALLS,batch_size=MODEL_BATCH,sources_set='all',writer=None,max_usd=1.0,claude_client=None):
    if not 1<=days<=30:raise ValueError('days_must_be_1_to_30')
    if not 1<=gemini_calls<=HARD_CALL_LIMIT:raise ValueError('gemini_calls_must_be_1_to_40')
    if not 1<=batch_size<=40:raise ValueError('batch_size_must_be_1_to_40')
    now=datetime.now(timezone.utc);start=time.monotonic();output.mkdir(parents=True,exist_ok=True)
    report={'schema':'investedia.regional-backfill/v1','notice':'Not investment advice.','days':days,'dry_run':dry_run,
            'connections_only':connections_only,'started_at':iso(now),'gemini_call_limit':gemini_calls,'model_batch_size':batch_size,'gemini_calls':0,
            'feeds':[],'rejections':{},'state':'incomplete','articles_checked':0}
    budget=ModelBudget(request,gemini_calls,deadline=start+24*60);old_get,old_log,old_err=robot.get,robot.log,robot.err
    robot.get=budget.get;robot.UA=UA;robot.log=lambda *args:None
    errors=Counter();robot.err=lambda msg:errors.update(['robot_validation_or_provider_error'])
    robot.NOW=now;robot.ISO_NOW=iso(now)
    original_models=robot.gemini_models;original_gemini=robot.gemini
    pinned=[];claude=None
    if writer:
        claude=ClaudeWriter(claude_client,writer,budget,max_usd);robot.gemini=claude
    robot.gemini_models=lambda:list(pinned)
    try:
        worker=uploader.validate_url(worker)
        live=json.loads(request(worker+'/v1/news?regional_read='+str(time.time_ns())))
        caps=json.loads(request(worker+'/v1/ingest/news/capabilities'))
        pinned.append(writer if writer else selected_model(gemini_model,live,read(ROOT/'assets/globe/news-status.json',{})))
        report['selected_model']=pinned[0]
        report['inventory_checked_at']=inventory.get('checked_at')
        report['inventory_sha256']=hashlib.sha256(json.dumps(inventory,sort_keys=True).encode()).hexdigest()
        report['historical_capacity']=caps
        if not dry_run and days>2 and caps.get('regional_backfill_version')!=1:
            raise ValueError('Worker_regional_history_support_requires_separate_approved_deployment')
        local=[]
        report['repair_sources']={}
        for name in ('news-live.json','news-48h.json','news-archive.json','news-gap-history-cache.json'):
            path=ROOT/'assets/globe'/name;rows=read(path,{}).get('stories',[])
            report['repair_sources'][name]={'present':path.exists(),'articles':len(rows)};local+=rows
        current=live.get('data',{}).get('stories',[])
        if not current or not live.get('meta',{}).get('fetched_at'):raise ValueError('valid_live_worker_feed_required')
        # Current API record is authoritative for repairs; never hydrate a compact record over it.
        combined={s['id']:s for s in unique_articles(local)};combined.update({s['id']:s for s in current});existing=list(combined.values())
        report['repair_sources']['Worker_feed_including_gap_history']={'articles':len(current)}
        repair_rows=[s for s in existing if now-timedelta(days=30)<=stamp(s['published_at'])<=now]
        seen=read(ROOT/'assets/globe/news-seen.json',{}).get('items',{})
        attempts=read(ROOT/'assets/globe/regional-backfill-state.json',{}).get('connection_attempts',{})
        box,by_iso,sym=robot.load_ref();registry=read(ROOT/'data/registry.json')['assets'];mk=read(ROOT/'assets/globe/markets.json')['assets']
        prices={a['s']:a for a in mk};prices.update(read(ROOT/'assets/globe/news-prices.json')['assets']);licences=read(ROOT/'data/coverage/price-licences.json',{})
        new=[];processed=[];duplicates={};candidates=[]
        # Repair first: previously generation consumed every call before this step.
        missing=[s for s in repair_rows if not s.get('impacts')]
        repairs,checked=repair_existing(repair_rows,by_iso,attempts,budget=budget)
        if not connections_only:
            only=SOURCE_SETS[sources_set];sources,skipped=feed_sources(inventory,only() if only else None);report['sources_set']=sources_set;report['feeds']=[{**s,'status':'skipped_inventory'} for s in skipped]
            fetcher=FeedFetcher();raw=[]
            with ThreadPoolExecutor(6) as pool:
                for rows,meta in pool.map(lambda s:fetcher.one(s,now,days),sources):raw.extend(rows);report['feeds'].append(meta)
            candidates,duplicates=dedupe(raw,existing,seen);report['fetched_candidates']=len(raw);report['deduped_candidates']=len(candidates)
            useful=[c for c in candidates if not robot.NOISE.search(c['title'])]
            duplicates['existing_robot_noise_rule']=len(candidates)-len(useful);candidates=useful
            report['candidate_cap_deferred']=len(candidates)-len(regional_candidates(candidates,now))
            new,processed=generate_new(candidates,now,box,by_iso,sym,batch_size,budget)
        processed_ids={c['url'] for c in processed}
        report['processed_by_region']=dict(Counter(c.get('feed_region') or 'global' for c in processed))
        report['deferred_by_region']=dict(Counter(c.get('feed_region') or 'global' for c in candidates if c['url'] not in processed_ids))
        report['repair_missing_impacts_scanned']=len(missing)
        report['repair_model_completed']=len(checked)
        report['repair_cache_unchanged']=sum(attempts.get(s['id'])==core.content_hash({'title':s.get('headline'),'desc':s.get('summary')}) for s in missing)
        proposals,new_reasons=evidence(new+repairs,now,registry,prices,licences)
        for row in proposals:row.pop('_feed_description',None)
        new_ids={s['id'] for s in new};new=[s for s in proposals if s['id'] in new_ids]
        if sources_set=='extra-2026-11-12':new=thin_and_capped(new,report)
        if claude and new:report['headlines_translated']=english_headlines(claude,new)
        repairs=[s for s in proposals if s['id'] not in new_ids and s.get('impacts')]
        for s in repairs:
            if protected(s)!=protected(combined[s['id']]):raise ValueError('protected_fields_changed')
        conns,rejected,_=draw_connections(proposals,mk)
        before_conns,_,_=draw_connections([combined[s['id']] for s in proposals if s['id'] not in new_ids],mk)
        prior_ids={c['id'] for c in before_conns};added_connections=[c for c in conns if c['id'] not in prior_ids]
        connected={c['event'] for c in conns}
        report.update(new_articles=len(new),articles_checked=len(missing),repairs_with_asset_impacts=len(repairs),connections_added=len(added_connections),
            articles_still_without_links=[{'id':s['id'],'reasons':new_reasons.get(s['id']) or [{'reason':'same_place_dot_or_existing_connection_rule'}]} for s in proposals if s['id'] not in connected],
            rejections={**duplicates,**dict(errors),'connection_rules':dict(rejected)},
            by_feed=dict(Counter(s['backfill_provenance']['feed_url'] for s in new)),by_region=dict(Counter(s['location'].get('region','none') for s in new)),
            by_country=dict(Counter(s['location']['country'] for s in new)),by_day=dict(Counter(s['published_at'][:10] for s in new)),
            connection_percent_by_region={region:{'articles':sum(region_of(s)==region for s in proposals),
                'with_drawable_lines':sum(region_of(s)==region and s['id'] in connected for s in proposals),
                'pct':100*sum(region_of(s)==region and s['id'] in connected for s in proposals)/sum(region_of(s)==region for s in proposals)} for region in sorted({region_of(s) for s in proposals})},
            sample_articles=[{'id':s['id'],'headline':s['headline'],'published_at':s['published_at'],'source':s['source']} for s in new[:10]],
            historical_capacity=caps,worker_fetched_at=live['meta']['fetched_at'])
        examined_ids={s['id'] for s in proposals}
        for row in missing:
            if row['id'] not in examined_ids:
                reason='unchanged_previously_checked' if attempts.get(row['id'])==core.content_hash({'title':row.get('headline'),'desc':row.get('summary')}) else 'not_processed_budget_or_no_valid_model_response'
                report['articles_still_without_links'].append({'id':row['id'],'reasons':[{'reason':reason}]})
        roll,history,deferred=plan(new,caps,now,days)
        repair_cap={**caps}
        if repair_cap.get('history_count') is not None:repair_cap['history_count']+=len(history)
        repair_cap['history_ids']=[*caps.get('history_ids',[]),*[s['id'] for s in history]]
        repair_roll,repair_history,repair_deferred=plan(repairs,repair_cap,now,30,True)
        report['routing']={'rolling_new':len(roll),'history_new':len(history),'rolling_repairs':len(repair_roll),'history_repairs':len(repair_history),'deferred':deferred+repair_deferred}
        write(output/'new-articles.json',new);write(output/'connection-repairs.json',repairs);write(output/'connections.json',{'connections':conns})
        state_root=ROOT/'assets/globe';archive_base=output/'events'
        if (state_root/'events').exists():shutil.copytree(state_root/'events',archive_base,dirs_exist_ok=True)
        archive(new+repairs,archive_base,now)
        if errors and not new and not checked:raise ValueError('existing_robot_generation_failed_report_saved')
        if not dry_run:
            acknowledged_ids=set()
            def acknowledged(rows):
                # Persist only acknowledged records. Each batch survives a later upload failure.
                archive(rows,state_root/'events',now)
                previous=read(state_root/'news-gap-history-cache.json',{}).get('stories',[])
                joined={s['id']:s for s in previous}
                for row in rows:joined[row['id']]=cached_patch(joined[row['id']],row) if row['id'] in joined else row
                write(state_root/'news-gap-history-cache.json',{'stories':list(joined.values())})
                acknowledged_ids.update(s['id'] for s in rows)
                write(output/'acknowledged.json',{'ids':sorted(acknowledged_ids)})
                # Patch each cached representation without replacing its editorial fields.
                patches={s['id']:s for s in rows}
                for name in ('news-live.json','news-48h.json','news-archive.json'):
                    path=state_root/name;data=read(path,{})
                    if not data:continue
                    for old in data.get('stories',[]):
                        new_row=patches.get(old.get('id'))
                        if not new_row:continue
                        patched=cached_patch(old,new_row);old.clear();old.update(patched)
                    if name=='news-archive.json':
                        have={s['id'] for s in data.get('stories',[])}
                        data.setdefault('stories',[]).extend(copy.deepcopy(s) for s in rows if s['id'] not in have)
                    write(path,data)
            ingest_deferred=publish(new,worker,now,days,False,caps,acknowledged)
            # Capacity is refreshed after new-article ingestion before corrections.
            refreshed=json.loads(request(worker+'/v1/ingest/news/capabilities')) if new else caps
            ingest_deferred+=publish(repairs,worker,now,30,True,refreshed,acknowledged,combined)
            for c in processed:
                sid='n'+hashlib.md5(c['url'].encode()).hexdigest()[:10]
                if sid in new_ids and sid not in acknowledged_ids:continue
                seen[core.canon(c['url'])]={'h':c['chash'],'t':iso(now)}
            repaired_ids={s['id'] for s in repairs}
            for sid in checked:
                if sid in repaired_ids and sid not in acknowledged_ids:continue
                attempts[sid]=core.content_hash({'title':combined[sid].get('headline'),'desc':combined[sid].get('summary')})
            report['ingestion_deferred']=ingest_deferred
            report['acknowledged_article_ids']=sorted(acknowledged_ids)
            report['connections_added_proposed']=report['connections_added']
            report['connections_added']=sum(c['event'] in acknowledged_ids for c in added_connections)
            write(state_root/'news-seen.json',{'schema':'investedia.news.seen/v1','updated_at':iso(now),'items':seen})
            write(state_root/'regional-backfill-state.json',{'connection_attempts':attempts})
            write(output/'acknowledged.json',{'ids':sorted(acknowledged_ids),'judgements_persisted':True})
        report['coverage_is_complete']=False # RSS retention and the fixed budget never establish complete history.
        report['feed_failures']=sum(f.get('status')=='unavailable_or_redirect_requires_review' for f in report['feeds'])
        report['candidates_processed']=len(processed);report['not_selected_by_existing_robot']=len(processed)-len(new)
        report['state']=('dry_run_partial_generation' if errors or budget.stop_reason else 'dry_run_complete') if dry_run else ('ingestion_acknowledged_partial_capacity' if report.get('ingestion_deferred') else 'ingestion_acknowledged')
    except ModelUnavailable:
        report['failure']='configured_model_unavailable_set_successful_hourly_GEMINI_MODEL'
        raise ValueError('configured_model_unavailable_report_saved') from None
    except BudgetExceeded:
        report['failure']='fixed_Gemini_budget_exhausted_no_further_model_requests'
        raise ValueError('fixed_Gemini_budget_exhausted_report_saved') from None
    except (OSError,ValueError,KeyError,TypeError) as error:
        reason=str(error)
        report['failure']=reason if isinstance(error,ValueError) and re.fullmatch(r'[A-Za-z0-9_]{1,160}',reason) and not contains_secret(reason) else type(error).__name__
        raise ValueError('regional_backfill_incomplete_report_saved') from None
    finally:
        report.update(gemini_calls=budget.calls,gemini_calls_detail=budget.call_log,actual_model_used=robot.status.get('gemini_model') if budget.calls else None,model_discovery_requests=budget.discovery,model_budget_stop=budget.stop_reason,gemini_usage_reported=dict(budget.usage),gemini_by_model={k:dict(v) for k,v in budget.by_model.items()},gemini_calls_without_usage=budget.calls-budget.usage_known_calls,elapsed_seconds=round(time.monotonic()-start,3))
        if claude:report.update(writer=writer,cost_usd=round(claude.spent,6),max_usd=max_usd)
        write(output/'report.json',report)
        robot.get=old_get;robot.log=old_log;robot.err=old_err;robot.gemini_models=original_models;robot.gemini=original_gemini
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--days',type=int,default=7);p.add_argument('--confirm',required=True)
    p.add_argument('--dry-run',choices=['true','false'],default='true');p.add_argument('--connections-only',choices=['true','false'],default='false')
    p.add_argument('--gemini-model',default=os.environ.get('GEMINI_MODEL') or None);p.add_argument('--gemini-calls',type=int,default=MAX_CALLS);p.add_argument('--batch-size',type=int,default=MODEL_BATCH)
    p.add_argument('--sources',choices=sorted(SOURCE_SETS),default='all');p.add_argument('--inventory',type=Path,required=True);p.add_argument('--output',type=Path,default=ROOT/'.local/regional-backfill')
    p.add_argument('--writer',choices=['gemini']+sorted(CLAUDE_PRICES),default='gemini');p.add_argument('--max-usd',type=float,default=1.0)
    a=p.parse_args()
    if not 0<a.max_usd<=10:p.error('max_usd_must_be_above_0_and_at_most_10')
    if a.confirm!='BACKFILL':p.error('confirm_must_equal_BACKFILL')
    if not 1<=a.days<=30:p.error('days_must_be_1_to_30')
    if not 1<=a.gemini_calls<=HARD_CALL_LIMIT:p.error('gemini_calls_must_be_1_to_40')
    if not 1<=a.batch_size<=40:p.error('batch_size_must_be_1_to_40')
    claude=a.writer!='gemini'
    required=(['ANTHROPIC_API_KEY'] if claude else ['GEMINI_API_KEY'])+['WORKER_URL']+(['NEWS_INGEST_TOKEN'] if a.dry_run=='false' else [])
    missing=[key for key in required if not os.environ.get(key)]
    if missing:p.error('missing_required_settings: '+', '.join(missing))
    try:
        result=run(a.days,a.dry_run=='true',a.connections_only=='true',read(a.inventory,{}),a.output,os.environ.get('WORKER_URL',''),a.gemini_model,a.gemini_calls,a.batch_size,a.sources,
                 writer=a.writer if claude else None,max_usd=a.max_usd,claude_client=__import__('anthropic').Anthropic() if claude else None)
        print(json.dumps({k:result[k] for k in ('state','new_articles','articles_checked','connections_added','gemini_calls','elapsed_seconds')}));return 0
    except (ValueError,OSError):print('Regional backfill incomplete; inspect the saved report. No success claimed.',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
