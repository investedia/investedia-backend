"""Exact sites from OpenStreetMap (owner decision 13 Nov 2026; ODbL, separate layer, credit required).

python -m tools.projects.invest.osm_sites
For projects with an approximate (town-level) location only. Nominatim search near the GEM point (+-0.35 deg),
accepting a result only if it is a mapped power facility (class power / plant:source / generator) whose name
contains the project's distinctive name words. Never used as ownership evidence. Usage policy: 1 request/s max,
identified client. Writes data/projects/invest/osm-sites.json.
"""
import json, re, time, urllib.parse, urllib.request
from pathlib import Path

from .engine.match import core

ROOT = Path(__file__).resolve().parents[3]
UA = {'User-Agent': 'Investedia-research/1.0 (verified projects map)'}
TECH = {'Solar': 'solar', 'Wind': 'wind', 'Hydropower': 'hydro', 'Oil & gas': 'gas', 'Coal': 'coal'}


def search(q, lat, lon, cc):
    d = 0.35
    params = {'q': q, 'format': 'jsonv2', 'limit': 10, 'extratags': 1, 'namedetails': 1, 'bounded': 1, 'countrycodes': cc.lower(),
              'viewbox': '%f,%f,%f,%f' % (lon - d, lat + d, lon + d, lat - d)}
    time.sleep(1.5)
    return json.load(urllib.request.urlopen(urllib.request.Request('https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(params), headers=UA), timeout=60))


def main():
    projects = json.loads((ROOT / 'assets/globe/projects-invest.json').read_text())['projects']
    out_path = ROOT / 'data/projects/invest/osm-sites.json'
    out = json.loads(out_path.read_text()) if out_path.exists() else {'schema': 'investedia.projects.invest.osm-sites.v1', 'licence': 'ODbL 1.0',
                                                                      'credit': '© OpenStreetMap contributors', 'licence_url': 'https://www.openstreetmap.org/copyright', 'sites': {}}
    seen = {}
    for p in projects:
        if p.get('precision') != 'approximate' or p['id'] in out['sites']:
            continue
        base = re.sub(r'\s*\(phase \d+\)$', '', p['name'])
        key = (base, round(p['lat'], 3), round(p['lon'], 3))
        if key not in seen:
            words = [w for w in core(base) if not w.isdigit() and w not in ('ntpc', 'acwa', 'scatec', 'nhpc')]
            hits, tried = [], []
            for q in [' '.join(words) + ' ' + TECH.get(p['kind'], ''), ' '.join(words)]:
                if not words or q in tried:
                    continue
                tried.append(q)
                for r in search(q.strip(), p['lat'], p['lon'], p['cc']):
                    tags = r.get('extratags') or {}
                    power = r.get('category') == 'power' or 'plant:source' in tags or 'generator:source' in tags or tags.get('power') in ('plant', 'generator')
                    name = ' '.join([r.get('name') or ''] + list((r.get('namedetails') or {}).values()))
                    if power and set(words) <= set(core(name)):
                        hits.append({'osm_type': r['osm_type'], 'osm_id': r['osm_id'], 'name': r.get('name'), 'lat': float(r['lat']), 'lon': float(r['lon']),
                                     'class': r.get('category'), 'type': r.get('type'), 'tags': {k: v for k, v in tags.items() if k.startswith(('plant', 'generator', 'power', 'operator'))},
                                     'url': 'https://www.openstreetmap.org/%s/%s' % (r['osm_type'], r['osm_id'])})
                if hits:
                    break
            uniq = {(h['osm_type'], h['osm_id']): h for h in hits}
            seen[key] = list(uniq.values())
        hits = seen[key]
        rec = {'name': p['name'], 'gem_point': [p['lat'], p['lon']], 'checked_at': time.strftime('%Y-%m-%d'), 'matches': hits,
               'status': 'matched' if len(hits) == 1 else 'ambiguous' if hits else 'not found'}
        out['sites'][p['id']] = rec
        out_path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
        print(p['name'], '|', rec['status'], '|', [(h['name'], h['type'], round(h['lat'], 4), round(h['lon'], 4)) for h in hits], flush=True)


if __name__ == '__main__':
    main()
