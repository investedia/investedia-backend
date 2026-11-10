"""Bounded, manual primary-notice collection. Evidence is not a licence decision.
No feed/article ingestion, authenticated API, model calls or publication.
"""
import argparse
import hashlib
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import os
import time
import ipaddress
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import update_globe_news as robot

UA = 'InvestediaRobot/1.0'
MAX_BYTES = 1_000_000
TERM_WORDS = re.compile(r'terms|copyright|licen[cs]|legal|reuse|re-use', re.I)
SIGNALS = re.compile(r'.{0,100}(?:non-commercial|commercial use|reproduction.{0,30}prohibited|all rights reserved|creative commons|public domain|redistribut).{0,150}', re.I)
RATES = [
    {'name': 'FRED: Treasury 2Y/10Y and Fed funds target',
     'source_url': 'https://fred.stlouisfed.org/',
     'terms_url': 'https://fred.stlouisfed.org/legal/',
     'datasets': ['DGS2', 'DGS10', 'DFEDTARL', 'DFEDTARU'],
     'scope': 'Source-specific series rights must be reviewed; a FRED API key is not a blanket redistribution grant.'},
    {'name': 'ECB: deposit facility rate',
     'source_url': 'https://data.ecb.europa.eu/',
     'terms_url': 'https://www.ecb.europa.eu/services/disclaimer/html/index.en.html',
     'datasets': ['FM.B.U2.EUR.4F.KR.DFR.LEV'],
     'scope': 'Name ECB; verify the current notice and any series-specific exception.'},
]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def get(url):
    u = urllib.parse.urlsplit(url)
    if u.scheme != 'https' or u.username or u.password or not u.hostname or u.port not in {None,443} or u.hostname in {'localhost', '127.0.0.1'}:
        raise ValueError('public_https_required')
    try:
        if not ipaddress.ip_address(u.hostname).is_global:raise ValueError('public_https_required')
    except ValueError as error:
        if str(error)=='public_https_required':raise
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html,text/plain;q=0.9'})
    with urllib.request.build_opener(NoRedirect()).open(req, timeout=15) as response:
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError('notice_size_limit')
        return body.decode('utf-8', 'replace')


def active_sources():
    rows = {}
    for url, name, region in robot.REGION_FEEDS:
        rows.setdefault(url, {'name': name, 'source_url': url, 'regions': [], 'tiers': []})
        rows[url]['regions'].append(region)
        rows[url]['tiers'].append('regional_broad')
        if robot.OFFICIAL_RE.search(name):
            rows[url]['tiers'].append('official_hourly')
    for url, name, hint in robot.FEEDS:
        rows.setdefault(url, {'name': name, 'source_url': url, 'regions': [], 'tiers': []})
        if 'official_hourly' not in rows[url]['tiers']:
            rows[url]['tiers'].append('official_hourly')
    return list(rows.values())


class LegalLinks(HTMLParser):
    def __init__(self, base):
        super().__init__(); self.base = base; self.links = []; self.current = None
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.current = [dict(attrs).get('href', ''), '']
    def handle_data(self, data):
        if self.current is not None:
            self.current[1] += data
    def handle_endtag(self, tag):
        if tag != 'a' or self.current is None:
            return
        href, text = self.current; self.current = None
        u = urllib.parse.urlsplit(urllib.parse.urljoin(self.base, href))
        host = urllib.parse.urlsplit(self.base).hostname
        if u.scheme == 'https' and u.hostname == host and u.port in {None,443} and not u.username and not u.password and TERM_WORDS.search(text + ' ' + u.path):
            url = urllib.parse.urlunsplit((u.scheme, u.netloc, u.path, '', ''))
            if url not in self.links:
                self.links.append(url)


def restriction_signals(raw):
    text = re.sub(r'<[^>]*>', ' ', raw)
    text = re.sub(r'\s+', ' ', text)
    return list(dict.fromkeys(m.group(0).strip() for m in SIGNALS.finditer(text)))[:12]


def contains_secret(text):
    return any(value and len(value)>=8 and value in text for key in
        ('GEMINI_API_KEY','NEWS_INGEST_TOKEN','FRED_API_KEY','GH_TOKEN','GITHUB_TOKEN')
        if (value:=os.environ.get(key)))


def collect(source, fetch, inventory=None):
    transport=fetch
    def checked_fetch(url):
        body=transport(url)
        if contains_secret(body):raise ValueError('secret_like_response_rejected')
        return body
    fetch=checked_fetch
    row = {**source, 'licence_review': 'pending_primary_notice_review',
           'commercial_headlines_summaries_links': None, 'notices': [], 'robots': None}
    known = inventory or {}
    status = str(known.get('status', ''))
    if known.get('robots_allowed') is False or known.get('enabled') is False or any(s in status for s in ('robots_disallow', 'unavailable')) or status == 'dead':
        row['collection_status'] = 'skipped_inventory_disallowed_or_unavailable'
        return row, {}
    url = source['source_url']; u = urllib.parse.urlsplit(url)
    home = urllib.parse.urlunsplit((u.scheme, u.netloc, '/', '', ''))
    raw = {}
    rp = urllib.robotparser.RobotFileParser()
    try:
        robots = fetch(home + 'robots.txt')
        if any(marker in robots.lower() for marker in ('<html','<!doctype html')):
            raise ValueError('invalid_robots_response')
        rp.parse(robots.splitlines()); raw[home + 'robots.txt'] = robots
    except urllib.error.HTTPError as error:
        if error.code != 404:
            row['collection_status'] = 'robots_unavailable'; return row, raw
        rp.parse([])
    except (OSError, ValueError):
        row['collection_status'] = 'robots_unavailable'; return row, raw
    row['robots'] = {'url': home + 'robots.txt', 'source_path_allowed': rp.can_fetch(UA, url)}
    if not rp.can_fetch(UA, url):
        row['collection_status'] = 'robots_disallowed'; return row, raw
    # Strict per-host bounds. Crawl delays needing a later request are deferred,
    # rather than silently violating the site's policy or sleeping indefinitely.
    if rp.crawl_delay(UA) or rp.crawl_delay('*') or rp.request_rate(UA) or rp.request_rate('*'):
        row['collection_status'] = 'crawl_policy_requires_manual_spaced_review'; return row, raw
    try:
        terms = source.get('terms_url')
        if terms:
            candidates = [terms]
        elif rp.can_fetch(UA, home):
            html = fetch(home); raw[home] = html
            parser = LegalLinks(home); parser.feed(html)
            candidates = parser.links[:2]
        else:
            candidates = []
        for notice in candidates:
            notice_host = urllib.parse.urlsplit(notice).hostname
            # Explicit ECB legal notice lives on a different official hostname.
            # Its robots policy is checked independently, not inherited.
            policy = rp
            if notice_host != u.hostname:
                target = urllib.parse.urlsplit(notice)
                robots_url = urllib.parse.urlunsplit((target.scheme, target.netloc, '/robots.txt', '', ''))
                try:
                    text = fetch(robots_url)
                except urllib.error.HTTPError as error:
                    if error.code != 404:
                        raise
                    text = ''
                if any(marker in text.lower() for marker in ('<html','<!doctype html')):raise ValueError('invalid_robots_response')
                policy = urllib.robotparser.RobotFileParser(); policy.parse(text.splitlines()); raw[robots_url] = text
            if not policy.can_fetch(UA, notice) or policy.crawl_delay(UA) or policy.crawl_delay('*') or policy.request_rate(UA) or policy.request_rate('*'):
                row['notices'].append({'url': notice, 'status': 'robots_or_crawl_policy_deferred'}); continue
            body = fetch(notice); raw[notice] = body
            signals = restriction_signals(body)
            row['notices'].append({'url': notice, 'sha256': hashlib.sha256(body.encode()).hexdigest(),
                'status': 'fetched_requires_human_scope_review', 'licensing_text_signals': signals})
        row['collection_status'] = 'collected_pending_review' if row['notices'] else 'no_same_host_primary_terms_link_identified'
    except (OSError, ValueError):
        row['collection_status'] = 'primary_notice_unavailable_or_redirect_requires_review'
    return row, raw


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fetch', action='store_true')
    p.add_argument('--output', type=Path, default=ROOT / '.local/source-licensing')
    p.add_argument('--inventory', type=Path, default=ROOT / 'data/coverage/feed-inventory.json')
    args = p.parse_args()
    if args.fetch and not args.inventory.exists():raise ValueError('coverage_inventory_required_before_provider_requests')
    inventory = json.loads(args.inventory.read_text()) if args.inventory.exists() else {}
    known = {r['url']: r for r in inventory.get('feeds', [])}
    sources = active_sources() + RATES
    rows = []; raw = {};responses={};retrieved={};last={};deadline=time.monotonic()+12*60
    def cached_fetch(url):
        if url not in responses:
            host=urllib.parse.urlsplit(url).hostname;wait=1-(time.monotonic()-last.get(host,0))
            if wait>0:time.sleep(wait)
            responses[url]=get(url);last[host]=time.monotonic();retrieved[url]=datetime.now(timezone.utc).isoformat()
        return responses[url]
    for source in sources:
        if args.fetch and time.monotonic()>=deadline:
            row={**source,'collection_status':'run_budget_deferred','licence_review':'pending_primary_notice_review','commercial_headlines_summaries_links':None,'notices':[]}
        elif args.fetch:
            row, bodies = collect(source, cached_fetch, known.get(source['source_url']))
            raw.update(bodies)
        else:
            row = {**source, 'collection_status': 'not_fetched_in_blocked_sandbox',
                'licence_review': 'pending_primary_notice_review', 'commercial_headlines_summaries_links': None, 'notices': []}
        rows.append(row)
    args.output.mkdir(parents=True, exist_ok=True)
    raw_dir = args.output / 'raw'; raw_dir.mkdir(exist_ok=True)
    index = {}
    for url, body in raw.items():
        name = hashlib.sha256(url.encode()).hexdigest() + '.txt'
        (raw_dir / name).write_text(body, encoding='utf-8'); index[url] = {'file':name,'retrieved_at':retrieved.get(url),'sha256':hashlib.sha256(body.encode()).hexdigest()}
    for row in rows:
        for notice in row.get('notices',[]):notice['retrieved_at']=retrieved.get(notice['url'])
    result = {'configuration_as_of':'2026-11-10','schema': 'investedia.source-licensing-review/v1', 'notice': 'Not investment advice.',
        'scope': 'Evidence only; no source enabled, licence granted, data ingested or rates published.',
        'sources': rows, 'raw_index': index, 'gemini_calls': 0, 'secrets_used': []}
    text=json.dumps(result,indent=2)
    if contains_secret(text):raise ValueError('secret_like_report_rejected')
    (args.output / 'report.json').write_text(text+'\n')
    print(json.dumps({'sources': len(rows), 'notices_collected': len(raw), 'gemini_calls': 0}))
    if args.fetch and not any(n.get('status')=='fetched_requires_human_scope_review' for row in rows for n in row.get('notices',[])):
        raise SystemExit('No primary notices collected; inspect the review artifact. No rights cleared.')


if __name__ == '__main__':
    main()
