#!/usr/bin/env python3
"""Sentinel-2 imagery for Data Center development sites that are independently identified (site-identification.json).
Same method as tools/projects/invest/imagery.py (Energy): Earth Search STAC, sentinel-2-c1-l2a 'visual' 10 m,
cloud/haze rejection. 'now' = latest usable scene 2026-06-01..2026-11-12; 'before' = 2024-10-01..2024-12-31 for
projects in construction/expansion. Crop 1.5 km wide (data-center scale). Writes JPEGs to the frontend image folder
only via --out, and a manifest with scene id, date, sha256, credit, site evidence and corroboration.
Usage: python tools/datacentres/dc_imagery.py --out <dir>"""
import argparse, hashlib, io, json, math, urllib.request
from pathlib import Path
import numpy as np, rasterio
from rasterio.warp import transform
from rasterio.windows import from_bounds
from PIL import Image
ROOT = Path(__file__).resolve().parents[2]
STAC = 'https://earth-search.aws.element84.com/v1/search'

def scenes(lat, lon, start, end, limit=15, cc=20):
    body = {'collections': ['sentinel-2-c1-l2a'], 'intersects': {'type': 'Point', 'coordinates': [lon, lat]},
            'datetime': f'{start}T00:00:00Z/{end}T23:59:59Z', 'query': {'eo:cloud_cover': {'lt': cc}},
            'sortby': [{'field': 'properties.datetime', 'direction': 'desc'}], 'limit': limit}
    return json.load(urllib.request.urlopen(urllib.request.Request(STAC, json.dumps(body).encode(), {'Content-Type': 'application/json'}), timeout=60))['features']

def crop(href, lat, lon, km):
    with rasterio.open(href) as ds:
        xs, ys = transform('EPSG:4326', ds.crs, [lon], [lat]); h = km * 500
        a = ds.read([1, 2, 3], window=from_bounds(xs[0] - h, ys[0] - h, xs[0] + h, ys[0] + h, ds.transform), boundless=True)
    return np.moveaxis(a, 0, -1)

def usable(img):
    g = img.mean(axis=2)
    # data centres have large white roofs: allow more bright pixels, but reject near-uniform bright crops (cloud) and no-data
    return img.size and (g == 0).mean() < 0.02 and (g > 215).mean() < 0.30 and (g > 240).mean() < 0.15 and g.std() > 12

def best(lat, lon, start, end, km):
    for f in scenes(lat, lon, start, end):
        try: img = crop(f['assets']['visual']['href'], lat, lon, km)
        except Exception: continue
        if usable(img): return f, img
    return None, None

def save(img, path):
    im = Image.fromarray(img.astype('uint8')).resize((640, 640), Image.LANCZOS); buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=82, optimize=True); path.write_bytes(buf.getvalue()); return hashlib.sha256(buf.getvalue()).hexdigest()

def dist(a, b, c, d):
    R = 6371000; p1, p2 = math.radians(a), math.radians(c)
    return 2 * R * math.asin(math.sqrt(math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(d - b) / 2) ** 2))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); ap.add_argument('--km', type=float, default=1.5); a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    sites = json.loads((ROOT / 'data/datacentres/release/v1/site-identification.json').read_text())['records']
    recs = {r['id']: r for f in ('release/v1/equinix-developments.json', 'v2/nextdc-filing-developments.json') for r in json.loads((ROOT / 'data/datacentres' / f).read_text())['records']}
    pins = {r['id']: r for r in json.loads((ROOT / 'data/datacentres/v2/licensing_unresolved.json').read_text())['records']}
    old = json.loads((ROOT / 'data/datacentres/release/v1/imagery-manifest.json').read_text()) if (ROOT / 'data/datacentres/release/v1/imagery-manifest.json').exists() else {}
    man = {'schema': 'investedia.datacentres.imagery.v1', 'method': __doc__.strip().splitlines()[0], 'images': {}}
    for pid, s in sites.items():
        site = s['site']
        if not site: continue
        prev = old.get('images', {}).get(pid)
        if prev and all(prev['images'].get(k) for k in prev['images']): man['images'][pid] = prev; continue
        r = recs[pid]; code = pid.split(':')[2]; slug = pid.replace(':', '-')
        pin = pins.get(f'dc:eqix:{code}', {}).get('location', {})
        corro = None
        if pin.get('precision') == 'exact':
            corro = {'official_pin_distance_m': round(dist(site['lat'], site['lon'], pin['lat'], pin['lon'])), 'note': 'Equinix-published pin vs OSM-named object (internal corroboration; pin not republished)'}
        rec = {'project_id': pid, 'name': r['name'], 'site': site, 'site_level': 'building' if site['class'].startswith('building') else 'campus/site',
               'corroboration': corro, 'images': {}}
        windows = [('now', ('2026-06-01', '2026-11-12'))] + ([('before', ('2024-10-01', '2024-12-31'))] if r['status']['stage'] in ('under_construction', 'expanding', 'planning') else [])
        for key, (start, end) in windows:
            f, img = best(site['lat'], site['lon'], start, end, a.km)
            if f is None: rec['images'][key] = None; continue
            name = f'{slug}-{key}.jpg'; sha = save(img, out / name); d = f['properties']['datetime'][:10]
            rec['images'][key] = {'file': name, 'date': d, 'scene': f['id'], 'sha256': sha, 'width_km': a.km, 'resolution_m': 10,
                                  'credit': f'Contains modified Copernicus Sentinel data {d[:4]}', 'licence': 'Copernicus Sentinel data terms (free, full and open; attribution)',
                                  'source': 'https://earth-search.aws.element84.com/v1/collections/sentinel-2-c1-l2a', 'is_current': key == 'now'}
        man['images'][pid] = rec
        print(pid, s['site']['name'], {k: (v or {}).get('date') for k, v in rec['images'].items()}, corro, flush=True)
    p = ROOT / 'data/datacentres/release/v1/imagery-manifest.json'; p.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding='utf-8')

if __name__ == '__main__':
    main()
