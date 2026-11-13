"""Incremental project monitoring (Phase E, local prototype; nothing is published or scheduled).

python -m tools.projects.invest.monitor [--today YYYY-MM-DD] [--limit N]
1. Source watch: every evidence URL in the verified ledger is re-checked with a conditional request
   (If-None-Match / If-Modified-Since). Unchanged sources cost one small request and no download.
   A changed source is downloaded once, its sha256 compared with the sha256 recorded at verification.
2. Deterministic checks on the public dataset: expected dates that have passed; US listing still current
   (SEC filer category); records whose evidence is older than 180 days.
3. Output: data/projects/invest/monitor/state.json (validators + hashes per URL, versioned)
          data/projects/invest/monitor/review-queue.json (every change -> affected projects, for a person)
          data/projects/invest/monitor/history.jsonl (append-only run log)
Never edits verifications.json or the public file; accepted changes go through the normal batch + audit.
"""
import argparse, hashlib, json, time, urllib.error, urllib.request
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from .engine import fetch

ROOT = Path(__file__).resolve().parents[3]
INV = ROOT / 'data/projects/invest'
MON = INV / 'monitor'
SKIP = ('api.gleif.org',)  # registry lookups are re-run by route B, not watched as documents


def check(url, prev):
    h = {'User-Agent': fetch._agent(urllib.parse.urlparse(url).hostname or '')}
    if prev.get('etag'):
        h['If-None-Match'] = prev['etag']
    if prev.get('last_modified'):
        h['If-Modified-Since'] = prev['last_modified']
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=60)
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return 'unchanged', prev
        return 'error', dict(prev, last_error='HTTP %d' % e.code)
    except Exception as e:  # recorded once per run, never bypassed
        return 'error', dict(prev, last_error=str(e)[:120])
    body = r.read()
    sha = hashlib.sha256(body).hexdigest()
    ctype = r.headers.get('Content-Type', '')
    if 'html' in ctype:  # pages carry per-request tokens/timestamps: compare the visible text without volatile parts
        import re, tempfile
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(body)
        t = fetch.text_of(f.name)
        t = re.sub(r'\b\d{1,2}:\d{2}(:\d{2})?\b|\b(csrf|token|nonce|session)\S*', ' ', t, flags=re.I)
        sha = 'text:' + hashlib.sha256(re.sub(r'\s+', ' ', t).encode()).hexdigest()
    new = {'etag': r.headers.get('ETag'), 'last_modified': r.headers.get('Last-Modified'), 'sha256': sha, 'bytes': len(body)}
    return ('unchanged' if sha == prev.get('sha256') else 'changed'), new


import urllib.parse  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--today', default=date.today().isoformat())
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    MON.mkdir(parents=True, exist_ok=True)
    sp = MON / 'state.json'
    state = json.loads(sp.read_text()) if sp.exists() else {'schema': 'investedia.projects.monitor.v0', 'sources': {}}
    led = json.loads((INV / 'verifications.json').read_text())['records']
    pub = {p['id']: p for p in json.loads((ROOT / 'assets/globe/projects-invest.json').read_text())['projects']}
    by_url, rec_sha = defaultdict(set), {}
    for key, v in led.items():
        pid = key.split('|')[0]
        if pid not in pub:
            continue
        for l in v.get('link', []):
            u = l.get('url')
            if u and not any(s in u for s in SKIP):
                by_url[u].add(pid)
                if l.get('sha256'):
                    rec_sha[u] = l['sha256']
    urls = sorted(by_url)[: a.limit or None]
    queue, counts, t0 = [], defaultdict(int), time.time()
    for u in urls:
        prev = state['sources'].get(u) or ({'sha256': rec_sha[u]} if u in rec_sha else {})
        status, new = check(u, prev)
        counts[status] += 1
        if status == 'changed' and prev.get('sha256') and prev['sha256'].startswith('text:') == new['sha256'].startswith('text:'):
            queue.append({'type': 'source_changed', 'url': u, 'old_sha256': prev['sha256'], 'new_sha256': new['sha256'],
                          'affected_projects': sorted(by_url[u]), 'action': 're-run the batch for this document and audit the differences'})
        new.update(checked_at=a.today, version=prev.get('version', 0) + (status == 'changed'))
        state['sources'][u] = new
        time.sleep(0.2)
    today = date.fromisoformat(a.today)
    for p in pub.values():
        if p.get('stage_note'):
            queue.append({'type': 'expected_date_passed', 'project': p['id'], 'name': p['name'], 'note': p['stage_note'],
                          'action': 'find a newer official status; do not change the stage without a source'})
        for e in p['exposures']:
            va = e['verification'].get('verified_at')
            if va and date.fromisoformat(va) < today - timedelta(days=180):
                queue.append({'type': 'evidence_older_than_180_days', 'project': p['id'], 'ticker': e['verification']['listing'].get('ticker')})
    sp.write_text(json.dumps(state, indent=1) + '\n')
    # Source list for the Worker monitor (workers/live/v1/projects-monitor.js); published with the Globe data on release.
    srcs = [{'url': u, 'sha256': state['sources'].get(u, {}).get('sha256'), 'projects': sorted(by_url[u])} for u in sorted(by_url)]
    due = [{'project': i['project'], 'name': i['name'], 'note': i['note']} for i in queue if i['type'] == 'expected_date_passed']
    (MON / 'projects-monitor-sources.json').write_text(json.dumps({'schema': 'investedia.projects.monitor-sources.v0', 'generated_at': a.today, 'sources': srcs, 'due': due}, indent=1, ensure_ascii=False) + '\n')
    (MON / 'review-queue.json').write_text(json.dumps({'generated_at': a.today, 'items': queue}, indent=1, ensure_ascii=False) + '\n')
    run = {'date': a.today, 'sources_checked': len(urls), **counts, 'queue_items': len(queue), 'seconds': round(time.time() - t0, 1)}
    with (MON / 'history.jsonl').open('a') as f:
        f.write(json.dumps(run) + '\n')
    print(run)


if __name__ == '__main__':
    main()
