"""Wikimedia Commons photo candidates for verified projects (owner decision 13 Nov 2026).

python -m tools.projects.invest.commons_photos [--only-missing]
Finds files whose title/description name the project; keeps only CC0, CC BY, CC BY-SA (no NC/ND/fair use);
if the file has coordinates they must be within 25 km of the project point. Writes CANDIDATES to
data/projects/invest/commons-candidates.json. Nothing is published until a person confirms the photo shows
this project (field 'confirmed').
"""
import argparse, json, math, re, time, urllib.parse, urllib.request
from pathlib import Path

from .engine.match import core

ROOT = Path(__file__).resolve().parents[3]
API = 'https://commons.wikimedia.org/w/api.php'
UA = {'User-Agent': 'Investedia-research/1.0 (verified projects map; contact via investedia.com)'}
OK = re.compile(r'^(CC0|Public domain|CC BY(-SA)? ?\d(\.\d)?.*)$', re.I)


def api(params):
    params = dict(params, format='json', maxlag=5)
    for i in range(8):
        time.sleep(4)
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(API + '?' + urllib.parse.urlencode(params), headers=UA), timeout=60))
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503):
                raise
            time.sleep(60 * (i + 1))
    raise SystemExit('Commons still rate limiting; try later')


def km(a, b, c, d):
    return 6371 * math.hypot(math.radians(d - b) * math.cos(math.radians((a + c) / 2)), math.radians(c - a))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only-missing', action='store_true')
    a = ap.parse_args()
    projects = json.loads((ROOT / 'assets/globe/projects-invest.json').read_text())['projects']
    out_path = ROOT / 'data/projects/invest/commons-candidates.json'
    out = json.loads(out_path.read_text()) if out_path.exists() else {'schema': 'investedia.projects.invest.commons.v1', 'candidates': {}}
    done = set()
    for p in projects:
        if a.only_missing and p.get('images', {}).get('now'):
            continue
        base = re.sub(r'\s*\(phase \d+\)$', '', p['name'])
        if p['id'] in out['candidates'] or base in done:
            continue
        done.add(base)
        words = [w for w in core(base) if not w.isdigit() and w not in ('ntpc', 'acwa', 'scatec', 'nhpc')]
        if len(words) < 2:  # one-word names (e.g. 'Hammond') match unrelated files
            continue
        res = api({'action': 'query', 'list': 'search', 'srnamespace': 6, 'srlimit': 15, 'srsearch': ' '.join(words) + ' ' + p['kind'].split()[0]})
        titles = [r['title'] for r in res.get('query', {}).get('search', [])]
        cands = []
        if titles:
            info = api({'action': 'query', 'titles': '|'.join(titles), 'prop': 'imageinfo|coordinates', 'iiprop': 'url|extmetadata|sha1|size', 'iiurlwidth': 800})
            for pg in info.get('query', {}).get('pages', {}).values():
                ii = (pg.get('imageinfo') or [{}])[0]
                md = {k: re.sub('<[^>]+>', '', str(v.get('value', ''))) for k, v in (ii.get('extmetadata') or {}).items()}
                lic = md.get('LicenseShortName', '')
                text = ' '.join([pg['title'], md.get('ImageDescription', ''), md.get('Categories', '')])
                if not OK.match(lic) or re.search(r'\b(NC|ND)\b', lic) or not set(words) <= set(core(text)):
                    continue
                co = (pg.get('coordinates') or [{}])[0]
                dist = round(km(p['lat'], p['lon'], co['lat'], co['lon']), 1) if 'lat' in co else None
                if dist is None or dist > 25:  # a photo must carry coordinates near the project
                    continue
                cands.append({'title': pg['title'], 'file_page': ii.get('descriptionurl'), 'thumb': ii.get('thumburl'), 'original': ii.get('url'),
                              'licence': lic, 'licence_url': md.get('LicenseUrl'), 'author': md.get('Artist', '').strip()[:200],
                              'description': md.get('ImageDescription', '')[:300], 'sha1': ii.get('sha1'), 'distance_km': dist, 'confirmed': None})
        out['candidates'][p['id']] = {'name': p['name'], 'checked_at': time.strftime('%Y-%m-%d'), 'candidates': cands}
        out_path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
        print(p['name'], len(cands), [c['title'][:60] for c in cands[:3]], flush=True)


if __name__ == '__main__':
    main()
