"""One bounded outage recovery. Stage by default; confirm requires the reviewed artifact.
No Gemini calls, generation jobs, financial jobs or saved-feed writes.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import news_core as core
from news_gap_history import reference, locate

spec = importlib.util.spec_from_file_location('news_uploader', ROOT / 'tools/push-news-to-worker.py')
uploader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(uploader)
LIMIT_START = '2026-11-08T16:00:00Z'
LIMIT_END = '2026-11-09T21:30:00Z'
# Reuse the priority robot's source definitions without importing its executable globals.
import ast
module = ast.parse((ROOT / 'update_globe_news.py').read_text(encoding='utf-8-sig'))
DEFS = {n.targets[0].id: ast.literal_eval(n.value) for n in module.body
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id in {'FEEDS', 'NEWS_FEEDS'}}
SOURCES = [(u, n) for u, n, *_ in DEFS['FEEDS'] if n in {'European Central Bank', 'Federal Reserve'}]
SOURCES += [(u, n) for u, n in DEFS['NEWS_FEEDS'] if n in {'BBC News', 'The Guardian', 'MarketWatch'}]
ARTICLE_HOSTS = {
    'BBC News': {'www.bbc.co.uk', 'www.bbc.com', 'bbc.co.uk', 'bbc.com'},
    'The Guardian': {'www.theguardian.com'}, 'MarketWatch': {'www.marketwatch.com'},
    'European Central Bank': {'www.ecb.europa.eu'}, 'Federal Reserve': {'www.federalreserve.gov'}}
_LAST_REQUEST = {}



def timestamp(value):
    try:
        d = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        d = parsedate_to_datetime(value)
    if d.tzinfo is None:
        raise ValueError('missing_timezone')
    return d.astimezone(timezone.utc)


def window(start, end):
    a, b = timestamp(start), timestamp(end)
    if not timestamp(LIMIT_START) <= a < b <= timestamp(LIMIT_END):
        raise ValueError('window_outside_approved_gap')
    return a, b


def in_window(value, start, end):
    # Half-open UTC windows: adjacent slices never duplicate boundary articles.
    return timestamp(start) <= timestamp(value) < timestamp(end)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def keys(row):
    if '_dedupe_keys' in row: return {tuple(k) for k in row['_dedupe_keys']}
    source = row.get('source') or {}
    if not isinstance(source, dict): source = {}
    return {('id', str(row.get('id') or '')), ('url', core.canon(source.get('url', row.get('url', '')))),
            ('headline', re.sub(r'\W+', ' ', row.get('headline', row.get('title', '')).casefold()).strip())} - {('id', ''), ('url', ''), ('headline', '')}


def dedupe(rows, existing):
    seen = set().union(*(keys(x) for x in existing)) if existing else set()
    kept, count = [], 0
    for row in rows:
        k = keys(row)
        if k & seen:
            count += 1
        else:
            kept.append(row)
            seen.update(k)
    return kept, count


def provenance(row, at, feed):
    return {**row, 'backfilled': True, 'backfilled_at': at,
            'backfill_provenance': {'version': 'outage-gap-v1', 'feed_url': feed,
                                    'original_published_at': row['published_at']}}


def get(url, limit=4_000_000):
    u = urlsplit(url)
    if u.scheme != 'https' or u.username or u.password:
        raise ValueError('unsafe_source_url')
    wait = 6 - (time.monotonic() - _LAST_REQUEST.get(u.hostname, -1e9))
    if wait > 0: time.sleep(wait)
    _LAST_REQUEST[u.hostname] = time.monotonic()
    req = urllib.request.Request(url, headers={'User-Agent': 'InvestediaGapRecovery/1.0 (+https://investedia.com)'})
    with urllib.request.build_opener(uploader.NoRedirect()).open(req, timeout=15) as r:
        if r.status != 200:
            raise ValueError('source_not_200')
        raw = r.read(limit + 1)
        if len(raw) > limit:
            raise ValueError('response_too_large')
        return raw.decode('utf-8-sig', 'replace')


class ArticleText(HTMLParser):
    def __init__(self):
        super().__init__(); self.skip = 0; self.depth = 0; self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'nav', 'footer', 'header'}: self.skip += 1
        if tag in {'article', 'main'}: self.depth += 1
    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'nav', 'footer', 'header'}: self.skip = max(0, self.skip-1)
        if tag in {'article', 'main'}: self.depth = max(0, self.depth-1)
    def handle_data(self, value):
        if self.depth and not self.skip: self.parts.append(value)


def parse_feed(raw, name, feed_url):
    root = ET.fromstring(raw)
    rows, rejected = [], Counter()
    atom = '{http://www.w3.org/2005/Atom}'
    for item in list(root.iter('item')) + list(root.iter(atom + 'entry')):
        title = item.findtext('title') or item.findtext(atom+'title') or ''
        link = item.findtext('link') or ''
        if not link:
            link = next((e.get('href', '') for e in item.findall(atom+'link') if e.get('rel', 'alternate') == 'alternate'), '')
        # Never use Atom updated, GDELT seendate, retrieval time, or a missing-date fallback.
        date = item.findtext('pubDate') or item.findtext(atom+'published') or item.findtext('{http://purl.org/dc/elements/1.1/}date')
        try:
            published = timestamp(date).strftime(core.ISO)
            if not title.strip() or not link.strip(): raise ValueError('missing_metadata')
        except (ValueError, TypeError, AttributeError):
            rejected['invalid_original_publication_or_metadata'] += 1; continue
        rows.append({'title': title.strip(), 'url': link.strip(), 'source': name,
                     'published': published, 'feed_url': feed_url})
    return rows, rejected


def articles(document):
    return document.get('stories', document.get('data', {}).get('stories', []))


def quality(artifact, review):
    n = len(artifact['stories'])
    if not n or review.get('artifact_sha256') != digest(artifact):
        raise ValueError('review_not_bound_to_artifact')
    rows = review.get('articles', [])
    if len(rows) != n or {r.get('id') for r in rows} != {s['id'] for s in artifact['stories']}:
        raise ValueError('review_must_cover_every_article')
    if not review.get('reviewer') or any(type(r.get(k)) is not bool for r in rows for k in ('relevant', 'correct_country')):
        raise ValueError('human_review_incomplete')
    relevant = sum(r['relevant'] for r in rows) / n
    country = sum(r['correct_country'] for r in rows) / n
    if relevant < .90 or country < .95: raise ValueError('quality_gate_failed')
    # A batch passing the audit still never uploads known bad individual records.
    allowed = {r['id'] for r in rows if r['relevant'] and r['correct_country']}
    return [s for s in artifact['stories'] if s['id'] in allowed]


def stage(start, end, worker, archive_paths, output):
    window(start, end)
    if not SOURCES: raise ValueError('no_configured_sources')
    existing, archives = [], []
    for path in archive_paths:
        raw = json.loads(path.read_text(encoding='utf-8-sig'))
        existing.extend(articles(raw))
        archives.append({'path': path.name, 'sha256': digest(raw), 'updated_at': raw.get('updated_at'), 'count': len(articles(raw))})
    live = json.loads(get(uploader.validate_url(worker) + '/v1/news'))
    if not articles(live): raise ValueError('worker_feed_unavailable')
    existing.extend(articles(live))
    raw_candidates, rejected, sources = [], Counter(), []
    for url, name in SOURCES:
        try:
            rows, invalid = parse_feed(get(url), name, url)
            rejected.update(invalid); raw_candidates.extend(rows)
            sources.append({'name': name, 'url': url, 'status': 'ok', 'items': len(rows)})
        except (OSError, ValueError, ET.ParseError):
            sources.append({'name': name, 'url': url, 'status': 'unavailable'})
    selected = []
    for row in raw_candidates:
        if in_window(row['published'], start, end): selected.append(row)
        else: rejected['outside_window'] += 1
    selected, duplicates = dedupe(selected, existing)
    iso, places = reference(ROOT)
    accepted = []
    at = datetime.now(timezone.utc).strftime(core.ISO)
    for c in selected[:80]:
        try:
            if urlsplit(c['url']).hostname not in ARTICLE_HOSTS[c['source']]:
                raise ValueError('source_article_host_not_approved')
            text = ArticleText(); text.feed(get(c['url']))
            body = ' '.join(text.parts).strip()
            if len(body) < 100: raise ValueError('no_article_body')
            if not (core.RELEVANT.search(c['title'] + ' ' + body) or core.MACRO.search(c['title'])):
                raise ValueError('not_financially_relevant')
            loc = locate({'text': c['title'] + ' ' + body}, iso, places)
            row = {'id': 'bf'+hashlib.sha256(core.canon(c['url']).encode()).hexdigest()[:16],
                   'headline': c['title'], 'published_at': c['published'], 'category': 'economy',
                   'location': loc, 'source': {'name': c['source'], 'url': c['url']},
                   'importance': 1, 'market_moving': False, 'impacts': [], 'links': [],
                   'ai_summary': False}
            accepted.append(provenance(row, at, c['feed_url']))
        except (OSError, ValueError) as e:
            reason = str(e) if isinstance(e, ValueError) else 'source_url_unavailable'
            rejected[reason] += 1
    rejected['bounded_limit'] += max(0, len(selected)-80)
    artifact = {'schema': 'investedia.news-gap/v1', 'window': {'start': start, 'end': end},
                'staged_at': at, 'stories': accepted,
                'evidence': {'worker_meta': live.get('meta'), 'archives': archives, 'sources': sources},
                'counts': {'feed_items': len(raw_candidates), 'candidates': len(raw_candidates)-rejected['outside_window'],
                           'source_failures': sum(s['status'] != 'ok' for s in sources),
                           'accepted': len(accepted), 'duplicates': duplicates, 'rejected': dict(rejected)},
                'gemini_calls': 0, 'source_scan_complete': all(s['status'] == 'ok' for s in sources),
                'quality': 'pending-human-review'}
    output.mkdir(parents=True, exist_ok=True)
    (output/'staged.json').write_text(json.dumps(artifact, indent=2)+'\n')
    review = {'artifact_sha256': digest(artifact), 'reviewer': '',
              'boundaries_verified': False, 'boundary_evidence': '',
              'articles': [{'id': s['id'], 'relevant': None, 'correct_country': None} for s in accepted]}
    (output/'review-template.json').write_text(json.dumps(review, indent=2)+'\n')
    print(json.dumps({k:v for k,v in artifact.items() if k != 'stories'}, indent=2))
    if any(s['status'] != 'ok' for s in sources):
        raise ValueError('source_scan_incomplete_report_saved_do_not_claim_coverage')
    return artifact


def confirm(artifact, review, worker):
    window(**artifact['window'])
    if artifact.get('schema') != 'investedia.news-gap/v1' or not artifact.get('source_scan_complete'):
        raise ValueError('incomplete_or_invalid_staging_scan')
    if review.get('boundaries_verified') is not True or not review.get('boundary_evidence'):
        raise ValueError('verify_archive_and_first_successful_run_boundaries_before_ingest')
    rows = quality(artifact, review)
    # Re-read the feed immediately; history merge also deduplicates server-side.
    live = json.loads(get(uploader.validate_url(worker)+'/v1/news'))
    capabilities = json.loads(get(uploader.validate_url(worker)+'/v1/ingest/news/capabilities'))
    if capabilities.get('history_ingest_version') != 1:
        raise ValueError('worker_history_capability_missing_requires_separate_approved_deployment')
    rows, _ = dedupe(rows, articles(live))
    if not rows: return {'ok': True, 'written': False, 'reason': 'all_duplicates'}
    for row in rows:
        if not in_window(row['published_at'], **artifact['window']) or row.get('backfilled') is not True:
            raise ValueError('invalid_staged_provenance')
    return uploader.push(worker, os.environ.get('NEWS_INGEST_TOKEN', ''),
                         {'mode': 'gap-history-v1', 'window': artifact['window'], 'stories': rows})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--start', default=LIMIT_START); p.add_argument('--end', default=LIMIT_END)
    p.add_argument('--worker', default=os.environ.get('WORKER_URL', 'https://api.investedia.com'))
    p.add_argument('--archive', type=Path, action='append', required=True)
    p.add_argument('--output', type=Path, default=ROOT/'.local/news-gap')
    p.add_argument('--confirm', action='store_true'); p.add_argument('--review', type=Path)
    a = p.parse_args()
    try:
        if a.confirm:
            if not a.review: raise ValueError('review_required')
            result = confirm(json.loads((a.output/'staged.json').read_text()), json.loads(a.review.read_text()), a.worker)
            print(json.dumps(result))
        else: stage(a.start, a.end, a.worker, a.archive, a.output)
    except (OSError, ValueError, KeyError) as e:
        print('News gap recovery failed: '+ (str(e) if isinstance(e, ValueError) else type(e).__name__), file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__': sys.exit(main())
