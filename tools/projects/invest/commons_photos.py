"""Wikimedia Commons photo candidates for verified projects (owner instructions 13 Nov 2026).

python -m tools.projects.invest.commons_photos [--all] [--max-minutes N]
  default: only projects with no satellite picture (exact-site satellite stays preferred; photos are alternatives).
Resumable: each project is written to the checkpoint as soon as it is done; finished projects are skipped.
API responses are cached in .local/commons-cache (git-ignored), so re-runs cost no requests.
Buckets in data/projects/invest/commons/: found (auto-checks passed, awaiting a person), verified, rejected,
unresolved (no usable candidate or search not finished). NOTHING here is published automatically.
"""
import argparse, hashlib, json, math, re, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

from .engine.match import core

ROOT = Path(__file__).resolve().parents[3]
API = 'https://commons.wikimedia.org/w/api.php'
UA = {'User-Agent': 'Investedia-research/1.0 (verified projects map; https://investedia.com)'}
CACHE = ROOT / '.local/commons-cache'
OUT = ROOT / 'data/projects/invest/commons'
BUCKETS = ('found', 'verified', 'rejected', 'unresolved')
FREE = re.compile(r'^(cc0|public domain|cc by(-sa)? \d(\.\d)?( [a-z-]+)?)$', re.I)  # commercial reuse allowed; no NC/ND
GENERIC = {'solar', 'farm', 'park', 'wind', 'power', 'plant', 'station', 'hydroelectric', 'pv', 'ipp', 'phase', 'project', 'multipurpose'}


class RateLimited(Exception):
    pass


def text(v):
    """Commons extmetadata values can be str, number, None, list or {'value': ...}; always return plain text."""
    if v is None:
        return ''
    if isinstance(v, dict):
        return text(v.get('value'))
    if isinstance(v, (list, tuple)):
        return ' '.join(text(x) for x in v)
    return re.sub(r'\s+', ' ', re.sub('<[^>]+>', ' ', str(v))).strip()


def api(params, max_wait=900):
    params = dict(params, format='json', formatversion=2, maxlag=5)
    key = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()
    f = CACHE / f'{key}.json'
    if f.exists():
        return json.loads(f.read_text())
    waited, delay = 0, 30
    while True:
        time.sleep(3)  # well under Commons' anonymous request guidance
        try:
            r = urllib.request.urlopen(urllib.request.Request(API + '?' + urllib.parse.urlencode(params), headers=UA), timeout=60)
            data = json.load(r)
            if data.get('error', {}).get('code') == 'maxlag':
                raise urllib.error.HTTPError(API, 503, 'maxlag', {}, None)
            CACHE.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(data))
            return data
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or waited >= max_wait:
                raise RateLimited(f'HTTP {e.code} after waiting {waited}s') if e.code in (429, 503) else e
            ra = e.headers.get('Retry-After') if e.headers else None
            d = int(ra) if ra and ra.isdigit() else delay
            time.sleep(d); waited += d; delay = min(delay * 2, 300)


def km(a, b, c, d):
    return 6371 * math.hypot(math.radians(d - b) * math.cos(math.radians((a + c) / 2)), math.radians(c - a))


def load():
    OUT.mkdir(parents=True, exist_ok=True)
    return {b: (json.loads((OUT / f'{b}.json').read_text()) if (OUT / f'{b}.json').exists() else {}) for b in BUCKETS}


def save(st):
    for b in BUCKETS:
        tmp = OUT / f'{b}.json.tmp'
        tmp.write_text(json.dumps(st[b], indent=1, ensure_ascii=False, sort_keys=True) + '\n')
        tmp.replace(OUT / f'{b}.json')


def candidates(p, words, radius_km):
    titles = set()
    # 1) files geotagged near the project point; 2) files whose text names the project
    geo = api({'action': 'query', 'list': 'geosearch', 'gsnamespace': 6, 'gslimit': 100,
               'gscoord': f"{p['lat']}|{p['lon']}", 'gsradius': int(min(radius_km, 10) * 1000)})
    titles |= {g['title'] for g in geo.get('query', {}).get('geosearch', [])}
    srch = api({'action': 'query', 'list': 'search', 'srnamespace': 6, 'srlimit': 30, 'srsearch': ' '.join(words)})
    titles |= {s['title'] for s in srch.get('query', {}).get('search', [])}
    out, titles = [], sorted(titles)
    for i in range(0, len(titles), 40):
        info = api({'action': 'query', 'titles': '|'.join(titles[i:i + 40]), 'prop': 'imageinfo|coordinates',
                    'iiprop': 'url|extmetadata|sha1|size|mime', 'iiurlwidth': 800})
        out += info.get('query', {}).get('pages', [])
    return out


def check(p, pg, words, radius_km):
    ii = (pg.get('imageinfo') or [{}])[0]
    md = {k: text(v) for k, v in (ii.get('extmetadata') or {}).items()}
    lic = md.get('LicenseShortName', '')
    co = (pg.get('coordinates') or [{}])[0]
    dist = round(km(p['lat'], p['lon'], co['lat'], co['lon']), 1) if 'lat' in co else None
    named = set(words) <= set(core(' '.join([pg.get('title', ''), md.get('ImageDescription', ''), md.get('ObjectName', ''), md.get('Categories', '')])))
    rec = {'title': pg.get('title'), 'file_page': ii.get('descriptionurl'), 'original': ii.get('url'), 'thumb': ii.get('thumburl'),
           'mime': ii.get('mime'), 'sha1': ii.get('sha1'), 'licence': lic, 'licence_url': md.get('LicenseUrl') or None,
           'creator': md.get('Artist', '')[:300] or None, 'credit': md.get('Credit', '')[:300] or None,
           'attribution': md.get('Attribution', '')[:300] or None, 'attribution_required': md.get('AttributionRequired') == 'true',
           'description': md.get('ImageDescription', '')[:400], 'date': md.get('DateTimeOriginal', '') or None, 'distance_km': dist}
    if not ii.get('url') or not (ii.get('mime') or '').startswith('image/'):
        return 'skip', rec
    why = []
    if not FREE.match(lic.strip()) or re.search(r'\b(nc|nd)\b|fair use|non-?free', lic, re.I):
        why.append(f'licence not cleared for commercial reuse: {lic or "none"}')
    if not lic.lower().startswith(('cc0', 'public domain')) and not rec['creator']:
        why.append('no creator for required attribution')
    if not named:
        why.append('file does not name the project')
    if dist is not None and dist > radius_km:
        why.append(f'{dist} km from project point')
    rec['auto_reasons'] = why
    if not named and (dist is None or dist > radius_km):
        return 'skip', rec  # unrelated file (other city/facility) - not worth a human look
    return ('found' if not why else 'rejected'), rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--max-minutes', type=float, default=90)
    a = ap.parse_args()
    t0 = time.time()
    st = load()
    projects = json.loads((ROOT / 'assets/globe/projects-invest.json').read_text())['projects']
    todo = [p for p in projects if a.all or not (p.get('images') or {}).get('now')]
    for p in todo:
        pid = p['id']
        if any(pid in st[b] and st[b][pid].get('status') == 'done' for b in ('found', 'unresolved')) or pid in st['verified']:
            continue
        if time.time() - t0 > a.max_minutes * 60:
            print('time budget reached; resume later'); break
        words = [w for w in core(re.sub(r'\(.*?\)', '', p['name'])) if w not in GENERIC and not w.isdigit()]
        radius = 25 if p.get('precision') == 'approximate' else 10
        base = {'name': p['name'], 'country': p['country'], 'lat': p['lat'], 'lon': p['lon'], 'precision': p.get('precision'),
                'checked_at': time.strftime('%Y-%m-%d'), 'name_words': words}
        if not words:
            st['unresolved'][pid] = dict(base, status='done', reason='name has no distinctive word to match'); save(st); continue
        try:
            pages = candidates(p, words, radius)
        except RateLimited as e:
            st['unresolved'][pid] = dict(base, status='pending', reason=f'Commons rate limit ({e}); resume later'); save(st)
            print('rate limited; stopping, progress saved'); break
        found, rej = [], []
        for pg in pages:
            b, rec = check(p, pg, words, radius)
            (found if b == 'found' else rej if b == 'rejected' else []).append(rec)
        if rej:
            st['rejected'][pid] = dict(base, files=rej)
        if found:
            st['found'][pid] = dict(base, status='done', files=found, verification='awaiting manual check: must show this project, not the town or a similar plant')
            st['unresolved'].pop(pid, None)
        else:
            st['unresolved'][pid] = dict(base, status='done', reason='no Commons file both names the project and passes licence/location checks')
        save(st)
        print(p['country'], '|', p['name'], '| found', len(found), '| auto-rejected', len(rej), flush=True)


if __name__ == '__main__':
    main()
