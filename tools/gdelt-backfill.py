"""Manual months-back article backfill (Aug-Oct 2026) discovered through GDELT.

GDELT DOC 2.0 is used only to DISCOVER article links, titles, crawl dates and the
publisher's country. Everything published comes from the publisher itself:
- the original publication time is read from the article page's own metadata
  (GDELT's seendate is a crawl time and is never used as the publication date);
- the short description the summary is written from is the page's own meta
  description, exactly like the broad robot's describe() step;
- robots.txt is honoured for every page, known paywalled publishers and pages
  marked isAccessibleForFree=false are skipped, and no article body is stored.

Generation goes through the same path as tools/regional-backfill.py: the
existing robot prompt (update_globe_news.pick_stories with preserve_source,
feed_only and backfill), the same validation, the same evidence rules, no photos,
and a fixed Gemini call budget. Backfilled articles keep their original
published_at, carry backfilled=true and are never sent to the live 48-hour feed:
when not a dry run they go to the Worker's article library (/v1/ingest/library,
merged with what each day already holds) and to the shared events day files.

Importing this module is offline; network and model work is meant for the
manual GitHub workflow .github/workflows/gdelt-backfill.yml.
"""
import argparse
import copy
import hashlib
import html
import importlib.util
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.robotparser
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


regional = _module('gdelt_regional_base', ROOT/'tools/regional-backfill.py')
core, robot, events, uploader = regional.core, regional.robot, regional.events, regional.uploader

UA = regional.UA
VERSION = 'gdelt-backfill-v1'
GDELT_API = 'https://api.gdeltproject.org/api/v2/doc/doc'
GDELT_INTERVAL = 5.5          # GDELT asks for at most one request every 5 seconds
GDELT_MAX_RECORDS = 250       # DOC 2.0 artlist maximum
GDELT_HORIZON_DAYS = 89       # DOC 2.0 searches roughly the last three months only
ALLOWED_START = '2026-08-01'
ALLOWED_END = '2026-10-15'    # inclusive day; the live library starts around 15 October
DEFAULT_CALLS = 40
HARD_CALL_LIMIT = 80
MODEL_BATCH = 25
DEFAULT_GDELT_REQUESTS = 180
MAX_GDELT_REQUESTS = 400
SLICE_DAYS = 3
RATE_LIMIT_RETRIES = 2      # per request, with growing pauses
RATE_LIMIT_STOP = 6         # consecutive 429s end discovery for this run (cache keeps what was found)
PAGE_LIMIT = 400_000
LIBRARY_DAY_LIMIT = 1500      # Worker /v1/ingest/library row limit per day (no truncation here)
LIBRARY_DAYS_PER_REQUEST = 3
TRANSIENT = re.compile(r'^(page_unavailable|robots_unavailable|page_http_(5\d\d|429|408)|too_many_redirects)$')
THEMES = '(economy OR business OR market OR markets OR bank OR investment OR inflation OR trade OR currency OR oil OR shares OR exports)'

# Thin regions first. FIPS 10-4 codes, as GDELT's sourcecountry filter expects.
# The source country only balances discovery; it is never an event location.
REGIONS = {
    'middle_east': {'label': 'Middle East', 'balance': 'me',
                    'fips': ['AE', 'SA', 'QA', 'KU', 'BA', 'MU', 'IS', 'JO', 'LE', 'IZ', 'TU', 'IR']},
    'oceania': {'label': 'Oceania', 'balance': 'oc', 'fips': ['AS', 'NZ', 'FJ', 'PP']},
    'asia': {'label': 'Asia', 'balance': 'asia',
             'fips': ['IN', 'CH', 'JA', 'KS', 'SN', 'MY', 'ID', 'TH', 'RP', 'VM', 'BG', 'CE', 'HK', 'TW', 'PK']},
    'central_asia': {'label': 'Central Asia', 'balance': 'asia',
                     'fips': ['KZ', 'UZ', 'KG', 'TI', 'TX', 'AJ', 'GG', 'AM', 'MG']},
    'east_africa': {'label': 'East Africa', 'balance': 'af',
                    'fips': ['KE', 'TZ', 'UG', 'ET', 'RW', 'MZ', 'ZA', 'MI']},
    'eastern_europe': {'label': 'Eastern Europe', 'balance': 'eu',
                       'fips': ['PL', 'EZ', 'HU', 'RO', 'BU', 'UP', 'LO', 'LH', 'LG', 'EN', 'MD']},
    'southern_europe': {'label': 'Southern Europe', 'balance': 'eu',
                        'fips': ['IT', 'SP', 'PO', 'GR', 'HR', 'SI', 'RI', 'CY', 'MT']},
    'caribbean': {'label': 'Caribbean', 'balance': 'latam',
                  'fips': ['JM', 'TD', 'BB', 'BF', 'DR', 'CJ', 'RQ', 'HA']},
}
# Hard paywalls: never fetched, even for the meta description.
PAYWALLED_HOSTS = {'wsj.com', 'ft.com', 'bloomberg.com', 'economist.com', 'barrons.com', 'nikkei.com',
                   'thetimes.co.uk', 'telegraph.co.uk', 'nytimes.com', 'washingtonpost.com', 'theaustralian.com.au',
                   'afr.com', 'businessinsider.com', 'haaretz.com', 'scmp.com', 'theinformation.com'}

iso = regional.iso
stamp = regional.stamp
read = regional.read
write = regional.write
BudgetExceeded = regional.BudgetExceeded
ModelUnavailable = regional.ModelUnavailable


def day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value): raise ValueError('dates_must_be_YYYY-MM-DD')
    try: result = datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    except (TypeError, ValueError): raise ValueError('dates_must_be_YYYY-MM-DD') from None
    return result


def window(start, end):
    """Inclusive day range inside Aug 1 - Oct 15 2026 -> half-open UTC datetimes."""
    a, b = day(start), day(end)
    if not day(ALLOWED_START) <= a <= b <= day(ALLOWED_END): raise ValueError('window_outside_2026-08-01_to_2026-10-15')
    return a, b + timedelta(days=1)


def regions_from(value):
    names = [x.strip() for x in (value or '').split(',') if x.strip()] or list(REGIONS)
    if 'all' in names: names = list(REGIONS)
    unknown = [x for x in names if x not in REGIONS]
    if unknown: raise ValueError('unknown_region')
    return list(dict.fromkeys(names))


def query(region):
    countries = ' OR '.join('sourcecountry:' + code for code in REGIONS[region]['fips'])
    return f'{THEMES} ({countries}) sourcelang:english'


def slices(start, end, now, size=SLICE_DAYS):
    """Oldest first: GDELT forgets the oldest days first. Parts older than its horizon are reported, not queried."""
    horizon = (now - timedelta(days=GDELT_HORIZON_DAYS)).replace(hour=0, minute=0, second=0, microsecond=0)
    out, skipped = [], []
    cursor = start
    while cursor < end:
        stop = min(cursor + timedelta(days=size), end)
        if stop <= horizon: skipped.append((cursor, stop))
        else: out.append((max(cursor, horizon), stop))
        cursor = stop
    return out, skipped


def plan_requests(regions, parts):
    # Round-robin by region inside each time slice so a request cap still covers every region.
    return [(region, a, b) for a, b in parts for region in regions]


def gdelt_url(region, start, end):
    params = {'query': query(region), 'mode': 'ArtList', 'format': 'json', 'maxrecords': GDELT_MAX_RECORDS,
              'sort': 'HybridRel', 'startdatetime': start.strftime('%Y%m%d%H%M%S'),
              'enddatetime': (end - timedelta(seconds=1)).strftime('%Y%m%d%H%M%S')}
    return GDELT_API + '?' + urllib.parse.urlencode(params)


class GdeltClient:
    """One request every >= 5.5 s, every valid response cached on disk, resumable."""
    def __init__(self, get, cache_dir, max_requests=DEFAULT_GDELT_REQUESTS, clock=time.monotonic, sleep=time.sleep, interval=GDELT_INTERVAL):
        if not 1 <= max_requests <= MAX_GDELT_REQUESTS: raise ValueError('gdelt_requests_must_be_1_to_400')
        self.get, self.cache, self.max, self.clock, self.sleep, self.interval = get, Path(cache_dir), max_requests, clock, sleep, interval
        self.cache.mkdir(parents=True, exist_ok=True)
        self.requests = 0; self.cache_hits = 0; self.slept = 0.0; self.rate_limited = 0; self.errors = Counter()
        self.last = None; self.stopped = None; self.consecutive_429 = 0

    def path(self, url): return self.cache/(hashlib.sha256(url.encode()).hexdigest()[:32] + '.json')

    def _wait(self):
        if self.last is not None:
            wait = self.interval - (self.clock() - self.last)
            if wait > 0: self.sleep(wait); self.slept += wait

    def _once(self, url):
        self._wait()
        self.requests += 1
        try: text = self.get(url, timeout=30)
        finally: self.last = self.clock()
        stripped = text.lstrip()
        if stripped.startswith('{'): return json.loads(stripped)
        if 'limit requests' in stripped.lower(): raise urllib.error.HTTPError(url, 429, 'rate limited', None, None)
        raise ValueError('gdelt_non_json_response')

    def fetch(self, url):
        path = self.path(url)
        if path.exists():
            self.cache_hits += 1
            return read(path).get('articles', []), 'cache'
        if self.stopped: return [], self.stopped
        for attempt in range(RATE_LIMIT_RETRIES + 1):
            if self.requests >= self.max: self.stopped = 'gdelt_request_budget_reached'; return [], self.stopped
            try:
                payload = self._once(url); self.consecutive_429 = 0; break
            except urllib.error.HTTPError as e:
                if e.code != 429: self.errors['http_%d' % e.code] += 1; return [], 'error'
                self.rate_limited += 1; self.consecutive_429 += 1
                if self.consecutive_429 >= RATE_LIMIT_STOP: self.stopped = 'gdelt_rate_limited_stop'; return [], self.stopped
                pause = self.interval * 6 * (attempt + 1)  # 33 s, 66 s, 99 s: well above GDELT's 5 s rule
                self.sleep(pause); self.slept += pause; self.last = self.clock()
                if attempt == RATE_LIMIT_RETRIES: return [], 'rate_limited'
            except (OSError, ValueError) as e:
                self.errors[type(e).__name__ if not isinstance(e, ValueError) else str(e)[:60]] += 1; return [], 'error'
        articles = payload.get('articles', []) if isinstance(payload, dict) else []
        if not isinstance(articles, list): articles = []
        write(path, {'url': url, 'fetched_at': iso(datetime.now(timezone.utc)), 'articles': articles[:GDELT_MAX_RECORDS]})
        return articles[:GDELT_MAX_RECORDS], 'fetched'


def parse_articles(articles, region, start, end):
    """GDELT rows -> discovery records. seendate is kept for audit only, never as publication time."""
    rows, rejected = [], Counter()
    for a in articles:
        try:
            url, title = str(a.get('url') or '').strip(), html.unescape(str(a.get('title') or '')).strip()
            seen = datetime.strptime(a['seendate'], '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
            u = urlsplit(url)
        except (KeyError, TypeError, ValueError, AttributeError):
            rejected['invalid_gdelt_record'] += 1; continue
        if (a.get('language') or 'English') != 'English': rejected['not_english'] += 1; continue
        if u.scheme != 'https' or not u.hostname or u.username or u.password: rejected['not_public_https_url'] += 1; continue
        if len(title) < 12: rejected['missing_title'] += 1; continue
        if not start <= seen < end + timedelta(days=1): rejected['gdelt_record_outside_slice'] += 1; continue
        rows.append({'title': title, 'url': url, 'domain': str(a.get('domain') or u.hostname).lower(), 'gdelt_seen': iso(seen),
                     'gdelt_country': str(a.get('sourcecountry') or '')[:60], 'gdelt_region': region,
                     'feed_region': REGIONS[region]['balance']})
    return rows, rejected


def headline_key(text): return re.sub(r'\W+', ' ', str(text or '').casefold()).strip()
def sid(url): return 'n' + hashlib.md5(url.encode()).hexdigest()[:10]


def known_keys(articles, event_rows, library_ids, processed):
    ids = {s.get('id') for s in articles} | {e.get('id') for e in event_rows} | set(library_ids)
    urls = {core.canon(u) for s in articles for u in regional.source_urls(s)} | {core.canon(e['url']) for e in event_rows if e.get('url')}
    urls |= set(processed)
    heads = {headline_key(s.get('headline')) for s in articles} | {headline_key(e.get('title')) for e in event_rows}
    return {'ids': ids - {None, ''}, 'urls': urls - {''}, 'heads': heads - {''}}


def dedupe(rows, known):
    """Against existing article ids, source URLs, headlines and earlier processed GDELT URLs; also within this run."""
    out, rejected = [], Counter()
    ids, urls, heads = set(known['ids']), set(known['urls']), set(known['heads'])
    for row in rows:
        url, key = core.canon(row['url']), headline_key(row['title'])
        if sid(row['url']) in ids or url in urls:  # remember variants of a known article too (amp, www, fragments)
            rejected['duplicate_id_or_source_url'] += 1; urls.add(url); heads.add(key); continue
        if key in heads: rejected['duplicate_headline'] += 1; continue
        if robot.NOISE.search(row['title']): rejected['existing_robot_noise_rule'] += 1; continue
        ids.add(sid(row['url'])); urls.add(url); heads.add(key); out.append(row)
    return out, rejected


def order(rows, regions):
    """Round-robin regions (thin first); inside a region round-robin crawl days, so one busy day cannot take the budget."""
    per = {}
    for region in regions:
        days = defaultdict(list)
        for row in rows:
            if row['gdelt_region'] == region: days[row['gdelt_seen'][:10]].append(row)
        queue, keys = [], sorted(days)
        while any(days[k] for k in keys):
            for k in keys:
                if days[k]: queue.append(days[k].pop(0))
        per[region] = queue
    out = []
    while any(per.values()):
        for region in regions:
            if per[region]: out.append(per[region].pop(0))
    return out


# ---------- publisher pages: robots.txt, paywall, own metadata ----------
META = r'<meta\b[^>]*?(?:property|name|itemprop)\s*=\s*["\']{key}["\'][^>]*?content\s*=\s*["\']([^"\']{{1,800}})["\']'
META_REV = r'<meta\b[^>]*?content\s*=\s*["\']([^"\']{{1,800}})["\'][^>]*?(?:property|name|itemprop)\s*=\s*["\']{key}["\']'
DATE_KEYS = ('article:published_time', 'og:article:published_time', 'datePublished', 'pubdate', 'publishdate',
             'DC.date.issued', 'dcterms.created', 'parsely-pub-date')


def meta(page, *keys):
    for key in keys:
        for pattern in (META, META_REV):
            m = re.search(pattern.format(key=re.escape(key)), page, re.I)
            if m: return html.unescape(m.group(1)).strip()
    return None


def published_time(page):
    """Only the page's own publication metadata; naive or date-only values are rejected, never guessed."""
    values = [meta(page, k) for k in DATE_KEYS]
    values += re.findall(r'"datePublished"\s*:\s*"([^"]{8,40})"', page)
    for value in values:
        if not value: continue
        try: return stamp(value.strip())
        except (ValueError, TypeError, AttributeError, IndexError): continue
    return None


def paywalled(page):
    return bool(re.search(r'"isAccessibleForFree"\s*:\s*"?(false|False)"?', page))


def paywalled_host(host):
    host = (host or '').lower()
    return any(host == h or host.endswith('.' + h) for h in PAYWALLED_HOSTS)


def same_site(a, b):
    strip = lambda h: (h or '').lower().removeprefix('www.')
    return strip(a) == strip(b)


def clean_title(title, site):
    if site:
        for sep in (' | ', ' - ', ' — ', ' – '):
            if title.endswith(sep + site): return title[:-len(sep + site)].strip()
    return title


def enrich_page(row, page, start, end):
    """Discovery record + publisher page -> robot candidate (or a rejection reason)."""
    if paywalled(page): return None, 'paywalled_page'
    published = published_time(page)
    if not published: return None, 'no_original_publication_time_on_page'
    if not start <= published < end: return None, 'original_date_outside_requested_window'
    if published > stamp(row['gdelt_seen']) + timedelta(days=1): return None, 'page_date_after_discovery_likely_modified'
    desc = meta(page, 'og:description', 'description', 'twitter:description')
    desc = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', desc or '')).strip()[:400]
    if len(desc) < 40: return None, 'no_source_description'
    site = (meta(page, 'og:site_name') or '').strip()[:80]
    title = clean_title(meta(page, 'og:title') or row['title'], site)[:300]
    if len(title) < 12: return None, 'missing_title'
    c = {'title': title, 'url': row['url'], 'source': site or row['domain'], 'published': iso(published), 'kind': 'news', 'hint': '',
         'desc': desc, 'feed_url': GDELT_API, 'feed_region': row['feed_region'], 'gdelt_region': row['gdelt_region'],
         'gdelt_seen': row['gdelt_seen'], 'gdelt_country': row['gdelt_country']}
    if regional.contains_secret(c): return None, 'secret_like_content'
    c['chash'] = core.content_hash(c)
    return c, None


class PageFetcher:
    """Per-host robots.txt and politeness; at most two same-site https redirects, each robots-checked."""
    def __init__(self, get=regional.request, clock=time.monotonic, sleep=time.sleep):
        self.get, self.clock, self.sleep = get, clock, sleep
        self.lock = threading.Lock(); self.locks = {}; self.policies = {}; self.last = {}; self.pages = 0

    def policy(self, host):
        if host not in self.policies:
            try: raw = self.get('https://' + host + '/robots.txt', timeout=10)
            except urllib.error.HTTPError as e:
                if e.code not in (404, 410): raise ValueError('robots_unavailable') from None
                raw = ''
            except OSError: raise ValueError('robots_unavailable') from None
            if '<html' in raw[:2000].lower(): raise ValueError('robots_unavailable')
            rp = urllib.robotparser.RobotFileParser(); rp.parse(raw.splitlines()); self.policies[host] = rp
        return self.policies[host]

    def page(self, url):
        host = urlsplit(url).hostname
        with self.lock: lock = self.locks.setdefault(host, threading.Lock())
        with lock:
            for _ in range(3):
                rp = self.policy(host)
                if not rp.can_fetch(UA, url): raise ValueError('robots_disallowed')
                delay = max(1.0, float(rp.crawl_delay(UA) or rp.crawl_delay('*') or 0))
                if delay > 15: raise ValueError('crawl_delay_too_long')
                if host in self.last:
                    wait = delay - (self.clock() - self.last[host])
                    if wait > 0: self.sleep(wait)
                try:
                    self.pages += 1
                    text = self.get(url, timeout=12)
                    return text[:PAGE_LIMIT]
                except urllib.error.HTTPError as e:
                    if e.code in (301, 302, 303, 307, 308) and e.headers and e.headers.get('Location'):
                        nxt = urljoin(url, e.headers['Location'])
                        if urlsplit(nxt).scheme != 'https' or not same_site(urlsplit(nxt).hostname, host): raise ValueError('redirect_to_other_site')
                        url = nxt; continue
                    raise ValueError('page_http_%d' % e.code) from None
                except OSError: raise ValueError('page_unavailable') from None
                finally: self.last[host] = self.clock()
            raise ValueError('too_many_redirects')

    def enrich(self, row, start, end):
        if paywalled_host(urlsplit(row['url']).hostname): return None, 'paywalled_publisher'
        try: page = self.page(row['url'])
        except ValueError as e: return None, str(e)
        return enrich_page(row, page, start, end)


# ---------- generation through the existing robot ----------
class Budget(regional.ModelBudget):
    """regional-backfill's Gemini guard (no page or photo fetches through the model client), with this tool's 1-80 cap."""
    def __init__(self, transport, limit=DEFAULT_CALLS, deadline=None):
        if not 1 <= limit <= HARD_CALL_LIMIT: raise ValueError('gemini_calls_must_be_1_to_80')
        super().__init__(transport, 1, deadline); self.limit = limit


def provenance(story, original, now):
    if story['headline'] != original['title'] or story['published_at'] != original['published'] or story['source']['url'] != original['url']:
        raise ValueError('source_identity_changed')
    story.pop('score', None)
    story.update(backfilled=True, backfilled_at=iso(now),
                 backfill_provenance={'version': VERSION, 'original_published_at': story['published_at'], 'feed_url': GDELT_API,
                                      'discovered_via': 'GDELT DOC 2.0', 'gdelt_seen': original['gdelt_seen'],
                                      'publisher_country_gdelt': original['gdelt_country'], 'description_from': 'publisher page metadata'})
    story['_feed_description'] = original['desc']
    return story


def generate(rows, start, end, now, ref, budget, fetcher, batch_size=MODEL_BATCH, deadline=None, workers=8):
    """Enrich lazily, one model batch at a time; stop when the call budget, deadline or rows run out."""
    if not 1 <= batch_size <= 40: raise ValueError('batch_size_must_be_1_to_40')
    box, by_iso, sym = ref
    out, sent, rejected, judged = [], [], Counter(), []
    cursor, max_pages = 0, budget.limit * batch_size * 4
    attempted = 0
    with ThreadPoolExecutor(workers) as pool:
        while cursor < len(rows) and budget.calls < budget.limit and attempted < max_pages:
            if deadline is not None and time.monotonic() >= deadline: rejected['run_deadline_reached'] += 1; break
            part = []
            while len(part) < batch_size and cursor < len(rows) and attempted < max_pages:
                take = rows[cursor:cursor + min(workers * 2, batch_size - len(part) + workers)]
                cursor += len(take); attempted += len(take)
                for row, (c, reason) in zip(take, pool.map(lambda r: fetcher.enrich(r, start, end), take)):
                    if c: part.append(c); continue
                    rejected[reason] += 1
                    if not TRANSIENT.match(reason): judged.append(row['url'])  # stable rule: do not fetch again next run
            if not part: break
            budget.context = {'purpose': 'gdelt_backfill', 'input_candidates': len(part),
                              'by_gdelt_region': dict(Counter(c['gdelt_region'] for c in part))}
            robot.status['gemini_ok'] = False
            try: got = robot.pick_stories(part, box, by_iso, sym, set(by_iso), len(part), preserve_source=True, feed_only=True, backfill=True)
            except BudgetExceeded: break
            if not robot.status.get('gemini_ok'): break
            lookup = {sid(c['url']): c for c in part}
            for s in got:
                if s['id'] not in lookup: raise ValueError('source_identity_changed')
                out.append(provenance(s, lookup[s['id']], now))
            sent.extend(part)
    rejected['not_reached_budget_or_page_cap'] += max(0, len(rows) - cursor)
    return out, sent, rejected, judged


# ---------- library rows and ingestion (never the live 48-hour feed) ----------
def library_row(s):
    loc = s.get('location') or {}
    return {'id': s['id'], 'h': s['headline'], 'c': s.get('category') or 'news', 't': s['published_at'], 's': (s.get('source') or {}).get('name'),
            'n': loc.get('country'), 'g': loc.get('region'), 'k': len(s.get('sources') or []) or 1}


def library_days(stories):
    days = defaultdict(list)
    for s in stories: days[s['published_at'][:10]].append(library_row(s))
    return {d: sorted(rows, key=lambda r: r['t'], reverse=True) for d, rows in sorted(days.items())}


def ingest_library(worker, token, days, read_day, push, acknowledged):
    """Merge each day with what the Worker already holds (its key is replaced per day), at most 3 days a request."""
    deferred, done = [], []
    merged = {}
    for d, rows in days.items():
        current = read_day(d)
        have = {r.get('id') for r in current}
        joined = current + [r for r in rows if r['id'] not in have]
        if len(joined) > LIBRARY_DAY_LIMIT: deferred.append({'day': d, 'reason': 'library_day_limit_1500_no_truncation'}); continue
        if len(joined) == len(current): acknowledged(rows); done.append(d); continue  # every row already in the library
        merged[d] = joined
    keys = sorted(merged)
    for i in range(0, len(keys), LIBRARY_DAYS_PER_REQUEST):
        group = {d: merged[d] for d in keys[i:i + LIBRARY_DAYS_PER_REQUEST]}
        result = push(worker, token, group)
        if not isinstance(result, dict) or result.get('ok') is not True: raise ValueError('library_ingest_not_acknowledged')
        acknowledged([r for d in group for r in days[d]]); done.extend(group)
    return done, deferred


def worker_day_reader(worker):
    def read_day(d):
        try: body = json.loads(regional.request(worker + '/v1/library?day=' + d))
        except urllib.error.HTTPError as e:
            if e.code == 404: return []
            raise
        rows = (body.get('data') or {}).get('rows')
        if not isinstance(rows, list): raise ValueError('library_day_unreadable')
        return rows
    return read_day


def local_events(base):
    rows = []
    for path in sorted(Path(base).glob('????-??-??.json')): rows += read(path, {}).get('events', [])
    return rows


def valid_backfilled(s, now):
    p = s.get('backfill_provenance') or {}
    t = stamp(s['published_at'])
    return (s.get('backfilled') is True and p.get('version') == VERSION and p.get('original_published_at') == s['published_at']
            and day(ALLOWED_START) <= t < day(ALLOWED_END) + timedelta(days=1) and t <= now
            and urlsplit((s.get('source') or {}).get('url', '')).scheme == 'https' and (s.get('source') or {}).get('name')
            and not any(i.get('scorable') is True for i in s.get('impacts') or []) and not s.get('image'))


def ingest_artifact(output, worker, state_root, now, library_push=None):
    """Second step (short, holds the news-production lock): library + shared day files. Never the live feed."""
    output, state_root = Path(output), Path(state_root)
    new = read(output/'new-articles.json', []) or []; judged = read(output/'judged.json', {}) or {}
    if any(not valid_backfilled(s, now) for s in new): raise ValueError('invalid_backfill_provenance_or_date')
    state = read(state_root/'gdelt-backfill-state.json', {}) or {}; processed = state.get('processed', {})
    present = local_events(state_root/'events')  # the hourly robot may have run since generation
    ids = {e.get('id') for e in present}; urls = {core.canon(e['url']) for e in present if e.get('url')}
    fresh = [s for s in new if s['id'] not in ids and core.canon(s['source']['url']) not in urls]
    acked = set()
    def acknowledged(rows):
        got = {r['id'] for r in rows}; batch = [s for s in fresh if s['id'] in got]
        regional.archive(batch, state_root/'events', now)  # shared day files: totals and threads include them
        acked.update(got); write(output/'acknowledged.json', {'ids': sorted(acked)})
    done, deferred = [], []
    if fresh:
        worker = uploader.validate_url(worker)
        push = library_push or (lambda url, token, group: uploader.push_library(url, token, group))
        done, deferred = ingest_library(worker, os.environ.get('NEWS_INGEST_TOKEN', ''), library_days(fresh), worker_day_reader(worker), push, acknowledged)
    new_ids = {s['id'] for s in fresh}
    for url in judged.get('sent', []) + judged.get('judged', []):
        if sid(url) in new_ids and sid(url) not in acked: continue  # un-acknowledged articles stay retryable
        processed[core.canon(url)] = iso(now)
    write(state_root/'gdelt-backfill-state.json', {'schema': 'investedia.gdelt-backfill-state/v1', 'updated_at': iso(now), 'processed': processed})
    write(output/'acknowledged.json', {'ids': sorted(acked), 'judgements_persisted': True})
    return {'days': done, 'deferred': deferred, 'acknowledged_articles': len(acked), 'already_present': len(new) - len(fresh)}


# ---------- run ----------
def run(start, end, regions, dry_run, output, worker, cache_dir, gemini_model=None, gemini_calls=DEFAULT_CALLS,
        batch_size=MODEL_BATCH, gdelt_requests=DEFAULT_GDELT_REQUESTS, max_minutes=100, now=None,
        gdelt_get=None, page_get=None, model_get=None, library_push=None, sleep=time.sleep, state_root=None, ingest=True):
    a, b = window(start, end); regions = regions_from(','.join(regions) if isinstance(regions, list) else regions)
    if not 1 <= gemini_calls <= HARD_CALL_LIMIT: raise ValueError('gemini_calls_must_be_1_to_80')
    if not 1 <= batch_size <= 40: raise ValueError('batch_size_must_be_1_to_40')
    if not 1 <= gdelt_requests <= MAX_GDELT_REQUESTS: raise ValueError('gdelt_requests_must_be_1_to_400')
    now = now or datetime.now(timezone.utc); clock0 = time.monotonic(); deadline = clock0 + max_minutes * 60
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    state_root = Path(state_root or ROOT/'assets/globe'); reference = ROOT/'assets/globe'
    report = {'schema': 'investedia.gdelt-backfill/v1', 'notice': 'Not investment advice.', 'window': {'start': iso(a), 'end_exclusive': iso(b)},
              'regions': regions, 'dry_run': dry_run, 'started_at': iso(now), 'gemini_call_limit': gemini_calls, 'model_batch_size': batch_size,
              'gdelt_request_limit': gdelt_requests, 'state': 'incomplete', 'new_articles': 0, 'gemini_calls': 0,
              'rules': ['GDELT used for discovery only; seendate is never the publication date',
                        'publication time and description come from the publisher page metadata',
                        'robots.txt honoured; paywalled publishers/pages skipped; no article body stored',
                        'same robot prompt and validation as regional-backfill; no photos',
                        'never sent to the live 48-hour feed']}
    budget = Budget(model_get or regional.request, gemini_calls, deadline=deadline)
    saved = (robot.get, robot.log, robot.err, robot.gemini_models, robot.NOW, robot.ISO_NOW)
    errors = Counter(); pinned = []
    robot.get = budget.get; robot.UA = UA; robot.log = lambda *args: None
    robot.err = lambda msg: errors.update(['robot_validation_or_provider_error'])
    robot.NOW = now; robot.ISO_NOW = iso(now); robot.gemini_models = lambda: list(pinned)
    client = None
    try:
        worker = uploader.validate_url(worker)
        live = json.loads(regional.request(worker + '/v1/news?gdelt_read=' + str(time.time_ns())))
        current = live.get('data', {}).get('stories', [])
        if not current or not live.get('meta', {}).get('fetched_at'): raise ValueError('valid_live_worker_feed_required')
        pinned.append(regional.selected_model(gemini_model, live, read(reference/'news-status.json', {})))
        report['selected_model'] = pinned[0]
        local = []
        for name in ('news-live.json', 'news-48h.json', 'news-archive.json', 'news-gap-history-cache.json'):
            local += read(state_root/name, {}).get('stories', [])
        state = read(state_root/'gdelt-backfill-state.json', {}) or {}
        processed = state.get('processed', {})
        library_ids = [p.stem for p in (state_root/'library').glob('*.json')] if (state_root/'library').exists() else []
        event_rows = local_events(state_root/'events')
        known = known_keys(regional.unique_articles(local + current), event_rows, library_ids, processed)
        report['dedupe_sources'] = {'articles': len(local) + len(current), 'event_records': len(event_rows), 'library_files': len(library_ids),
                                    'earlier_gdelt_processed_urls': len(processed)}
        # Discovery
        parts, too_old = slices(a, b, now)
        report['gdelt_slices_outside_search_horizon'] = [{'start': iso(x), 'end_exclusive': iso(y)} for x, y in too_old]
        client = GdeltClient(gdelt_get or regional.request, cache_dir, gdelt_requests, sleep=sleep)
        found, parse_rejected = [], Counter()
        discovery = Counter(); requests_plan = plan_requests(regions, parts)
        report['gdelt_requests_planned'] = len(requests_plan)
        for region, x, y in requests_plan:
            if time.monotonic() >= deadline: parse_rejected['run_deadline_reached_during_discovery'] += 1; break
            articles, status = client.fetch(gdelt_url(region, x, y))
            discovery[status] += 1
            rows, bad = parse_articles(articles, region, x, y)
            found += rows; parse_rejected.update(bad)
        candidates, dup = dedupe(found, known)
        ordered = order(candidates, regions)
        report.update(gdelt={'requests': client.requests, 'cache_hits': client.cache_hits, 'slept_seconds': round(client.slept, 1),
                             'rate_limited': client.rate_limited, 'errors': dict(client.errors), 'stop': client.stopped,
                             'outcomes': dict(discovery)},
                      discovered=len(found), discovered_by_region=dict(Counter(r['gdelt_region'] for r in found)),
                      after_dedupe=len(candidates), after_dedupe_by_region=dict(Counter(r['gdelt_region'] for r in candidates)))
        # Generation
        ref = robot.load_ref()
        fetcher = PageFetcher(page_get or regional.request, sleep=sleep)
        new, sent, enrich_rejected, judged = generate(ordered, a, b, now, ref, budget, fetcher, batch_size, deadline)
        registry = read(ROOT/'data/registry.json')['assets']; mk = read(reference/'markets.json')['assets']
        prices = {x['s']: x for x in mk}; prices.update(read(reference/'news-prices.json')['assets'])
        licences = read(ROOT/'data/coverage/price-licences.json', {})
        proposals, reasons = regional.evidence(new, now, registry, prices, licences)
        for row in proposals: row.pop('_feed_description', None)
        new = proposals
        for s in new:
            if not a <= stamp(s['published_at']) < b: raise ValueError('original_date_outside_window')
        days = library_days(new)
        found_region = {c['url']: c['gdelt_region'] for c in sent}
        report.update(new_articles=len(new), pages_fetched=fetcher.pages, sent_to_model=len(sent),
                      sent_to_model_by_region=dict(Counter(c['gdelt_region'] for c in sent)),
                      not_selected_by_existing_robot=len(sent) - len(new),
                      by_discovery_region=dict(Counter(found_region.get(s['source']['url'], 'unknown') for s in new)),
                      by_region=dict(Counter(regional.region_of(s) for s in new)),
                      by_country=dict(Counter(s['location']['country'] for s in new).most_common()),
                      by_day=dict(sorted(Counter(s['published_at'][:10] for s in new).items())),
                      with_asset_impacts=sum(bool(s.get('impacts')) for s in new),
                      rejections={'gdelt_records': dict(parse_rejected), 'dedupe': dict(dup), 'pages_and_rules': dict(enrich_rejected), **dict(errors)},
                      impact_rejections={k: v for k, v in reasons.items() if v},
                      sample_articles=[{'id': s['id'], 'headline': s['headline'], 'summary': s.get('summary'), 'published_at': s['published_at'],
                                        'country': s['location']['country'], 'source': s['source']} for s in new[:30]],
                      library_rows_by_day={d: len(r) for d, r in days.items()})
        write(output/'new-articles.json', new); write(output/'library-rows.json', {'days': days})
        events.upsert(copy.deepcopy(new), base=str(output/'events'))
        if errors and not new: raise ValueError('existing_robot_generation_failed_report_saved')
        write(output/'judged.json', {'sent': [c['url'] for c in sent], 'judged': judged})
        if not dry_run and ingest:
            report['ingestion'] = ingest_artifact(output, worker, state_root, now, library_push)
        report['coverage_is_complete'] = False  # GDELT's index, robots rules and the fixed budget never establish complete history.
        if dry_run: report['state'] = 'dry_run_partial' if budget.stop_reason or errors else 'dry_run_complete'
        elif not ingest: report['state'] = 'generated_awaiting_ingest_job'
        else: report['state'] = 'ingestion_acknowledged_partial' if report['ingestion']['deferred'] else 'ingestion_acknowledged'
    except ModelUnavailable:
        report['failure'] = 'configured_model_unavailable_set_successful_hourly_GEMINI_MODEL'
        raise ValueError('configured_model_unavailable_report_saved') from None
    except BudgetExceeded:
        report['failure'] = 'fixed_Gemini_budget_exhausted_no_further_model_requests'
        raise ValueError('fixed_Gemini_budget_exhausted_report_saved') from None
    except (OSError, ValueError, KeyError, TypeError) as error:
        reason = str(error)
        report['failure'] = reason if isinstance(error, ValueError) and re.fullmatch(r'[A-Za-z0-9_]{1,160}', reason) and not regional.contains_secret(reason) else type(error).__name__
        raise ValueError('gdelt_backfill_incomplete_report_saved') from None
    finally:
        report.update(gemini_calls=budget.calls, gemini_calls_detail=budget.call_log, model_budget_stop=budget.stop_reason,
                      gemini_usage_reported=dict(budget.usage), elapsed_seconds=round(time.monotonic() - clock0, 3))
        write(output/'report.json', report)
        robot.get, robot.log, robot.err, robot.gemini_models, robot.NOW, robot.ISO_NOW = saved
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--start', default=ALLOWED_START); p.add_argument('--end', default=ALLOWED_END)
    p.add_argument('--regions', default='all'); p.add_argument('--confirm', required=True)
    p.add_argument('--dry-run', choices=['true', 'false'], default='true')
    p.add_argument('--gemini-model', default=os.environ.get('GEMINI_MODEL') or None)
    p.add_argument('--gemini-calls', type=int, default=DEFAULT_CALLS); p.add_argument('--batch-size', type=int, default=MODEL_BATCH)
    p.add_argument('--gdelt-requests', type=int, default=DEFAULT_GDELT_REQUESTS); p.add_argument('--max-minutes', type=int, default=100)
    p.add_argument('--phase', choices=['all', 'generate', 'ingest'], default='all')
    p.add_argument('--cache', type=Path, default=ROOT/'.local/gdelt-cache'); p.add_argument('--output', type=Path, default=ROOT/'.local/gdelt-backfill')
    a = p.parse_args(argv)
    if a.confirm != 'BACKFILL': p.error('confirm_must_equal_BACKFILL')
    if not 1 <= a.gemini_calls <= HARD_CALL_LIMIT: p.error('gemini_calls_must_be_1_to_80')
    if not 1 <= a.batch_size <= 40: p.error('batch_size_must_be_1_to_40')
    if not 1 <= a.gdelt_requests <= MAX_GDELT_REQUESTS: p.error('gdelt_requests_must_be_1_to_400')
    if not 5 <= a.max_minutes <= 170: p.error('max_minutes_must_be_5_to_170')
    try: window(a.start, a.end); regions_from(a.regions)
    except ValueError as e: p.error(str(e))
    if a.phase == 'ingest':
        if a.dry_run != 'false': p.error('ingest_phase_requires_dry_run_false')
        missing = [k for k in ('WORKER_URL', 'NEWS_INGEST_TOKEN') if not os.environ.get(k)]
        if missing: p.error('missing_required_settings: ' + ', '.join(missing))
        try:
            result = ingest_artifact(a.output, os.environ['WORKER_URL'], ROOT/'assets/globe', datetime.now(timezone.utc))
            report = read(a.output/'report.json', {}) or {}
            report['ingestion'] = result
            report['state'] = 'ingestion_acknowledged_partial' if result['deferred'] else 'ingestion_acknowledged'
            write(a.output/'report.json', report); print(json.dumps(result)); return 0
        except (ValueError, OSError, KeyError, TypeError) as e:
            print('GDELT backfill ingestion incomplete: ' + (str(e) if isinstance(e, ValueError) and re.fullmatch(r'[A-Za-z0-9_]{1,160}', str(e)) else type(e).__name__), file=sys.stderr)
            return 1
    required = ['GEMINI_API_KEY', 'WORKER_URL'] + (['NEWS_INGEST_TOKEN'] if a.dry_run == 'false' and a.phase == 'all' else [])
    missing = [k for k in required if not os.environ.get(k)]
    if missing: p.error('missing_required_settings: ' + ', '.join(missing))
    try:
        r = run(a.start, a.end, a.regions, a.dry_run == 'true', a.output, os.environ['WORKER_URL'], a.cache, a.gemini_model,
                a.gemini_calls, a.batch_size, a.gdelt_requests, a.max_minutes, ingest=a.phase == 'all')
        print(json.dumps({k: r.get(k) for k in ('state', 'new_articles', 'by_region', 'gemini_calls', 'elapsed_seconds')}))
        return 0
    except (ValueError, OSError):
        print('GDELT backfill incomplete; inspect the saved report. No success claimed.', file=sys.stderr); return 1


if __name__ == '__main__': sys.exit(main())
