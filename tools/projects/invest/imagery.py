"""Satellite pictures for verified projects (owner decision 7): Copernicus Sentinel-2 L2A true colour, 10 m.

python -m tools.projects.invest.imagery --out <frontend>/assets/img/projects/sat
Only projects with an exact location. 'now' = latest scene since 2026-06-01; 'before' = Oct-Dec 2024 for projects
under construction or commissioning. Scenes come from the public Earth Search STAC catalogue (AWS open data);
each crop is checked for cloud/haze (too bright or too uniform) and the next scene is tried. Writes
data/projects/invest/imagery.json with scene id, date, sha256 and the credit line.
"""
import argparse, hashlib, io, json, urllib.request
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform
from rasterio.windows import from_bounds
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
STAC = 'https://earth-search.aws.element84.com/v1/search'
CREDIT = 'Contains modified Copernicus Sentinel data {year}'


def scenes(lat, lon, start, end, limit=6):
    body = {'collections': ['sentinel-2-c1-l2a'], 'intersects': {'type': 'Point', 'coordinates': [lon, lat]},
            'datetime': '%sT00:00:00Z/%sT23:59:59Z' % (start, end), 'query': {'eo:cloud_cover': {'lt': 10}},
            'sortby': [{'field': 'properties.datetime', 'direction': 'desc'}], 'limit': limit}
    req = urllib.request.Request(STAC, json.dumps(body).encode(), {'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req, timeout=60))['features']


def crop(href, lat, lon, km):
    with rasterio.open(href) as ds:
        xs, ys = transform('EPSG:4326', ds.crs, [lon], [lat])
        h = km * 500
        a = ds.read([1, 2, 3], window=from_bounds(xs[0] - h, ys[0] - h, xs[0] + h, ys[0] + h, ds.transform), boundless=True)
    return np.moveaxis(a, 0, -1)


def usable(img):
    """Reject clouds, haze, no-data and empty crops."""
    g = img.mean(axis=2)
    return img.size and (g == 0).mean() < 0.02 and (g > 215).mean() < 0.12 and g.std() > 8


def best(lat, lon, start, end, km):
    for f in scenes(lat, lon, start, end):
        try:
            img = crop(f['assets']['visual']['href'], lat, lon, km)
        except Exception:
            continue
        if usable(img):
            return f, img
    return None, None


def save(img, path):
    im = Image.fromarray(img.astype('uint8')).resize((640, 640), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=80, optimize=True)
    path.write_bytes(buf.getvalue())
    return hashlib.sha256(buf.getvalue()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--km', type=float, default=3.0)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    man_path = ROOT / 'data/projects/invest/imagery.json'
    man = json.loads(man_path.read_text()) if man_path.exists() else {'schema': 'investedia.projects.invest.imagery.v1', 'images': {}}
    projects = json.loads((ROOT / 'assets/globe/projects-invest.json').read_text())['projects']
    import threading
    from concurrent.futures import ThreadPoolExecutor
    lock = threading.Lock()
    todo = [p for p in projects if p.get('precision') == 'exact' and p['id'] not in man['images']]

    def one(p):
        rec, slug = {}, p['id'].replace(':', '-')
        for key, (start, end) in (('now', ('2026-06-01', '2026-11-12')), ('before', ('2024-10-01', '2024-12-31'))):
            if key == 'before' and p.get('stage') not in ('Under construction', 'Commissioning'):
                continue
            f, img = best(p['lat'], p['lon'], start, end, a.km)
            if f is None:
                continue
            name = '%s-%s.jpg' % (slug, key)
            sha = save(img, out / name)
            d = f['properties']['datetime'][:10]
            rec[key] = {'file': name, 'date': d, 'scene': f['id'], 'sha256': sha, 'width_km': a.km, 'resolution_m': 10,
                        'credit': CREDIT.format(year=d[:4]), 'source': 'https://earth-search.aws.element84.com/v1/collections/sentinel-2-c1-l2a'}
        with lock:
            man['images'][p['id']] = rec
            man_path.write_text(json.dumps(man, indent=1) + '\n')
            print(p['id'], p['name'], sorted(rec), flush=True)

    with ThreadPoolExecutor(8) as pool:
        list(pool.map(one, todo))


if __name__ == '__main__':
    main()
