#!/usr/bin/env python3
"""Export public Data Center records for the Projects layer.
Only records that pass Codex's public_projection (reuse cleared + record-bound review) are exported.
NEXTDC (ASX facts, reuse pending) and SC2 (hold) are therefore excluded automatically.
Writes <frontend>/assets/globe/projects-datacenters.json and copies reviewed satellite images to
<frontend>/assets/img/projects/sat/. Usage: python tools/datacentres/export_frontend.py <frontend> <sat_dir>"""
import json, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research/data-centers/phase4')); import sector_adapter as SA
FE, SAT = Path(sys.argv[1]), Path(sys.argv[2])
src = json.loads((ROOT / 'data/datacentres/release/v2/public-candidates.json').read_text(encoding='utf-8'))
STAGE = {'under_construction': 'Under construction', 'planning': 'Approved', 'expanding': 'Expanding', 'operating': 'Operating'}
out, copied = [], 0
for r in src['records']:
    try: SA.public_projection(r)
    except Exception: continue
    e = r['exposures'][0]; L = e['listing']; loc = r['location']; ref = r.get('imagery_ref') or {}
    imgs = {}
    if loc['precision'] == 'exact' and loc.get('satellite_allowed'):
        for k, key in (('now', 'satellite_now'), ('before', 'satellite_before')):
            im = ref.get(key)
            if im and (SAT / im['file']).exists():
                shutil.copy2(SAT / im['file'], FE / 'assets/img/projects/sat' / im['file']); copied += 1
                imgs[k] = {'file': im['file'], 'date': im['date'], 'credit': im['credit'], 'width_km': im['width_km']}
    m = r.get('reported_metrics') or {}
    out.append({'id': r['id'], 'name': r['name'], 'city': r['city'], 'cc': r['country_code'], 'lat': loc['lat'], 'lon': loc['lon'],
                'precision': loc['precision'], 'location_label': loc.get('label'),
                'location_credit': '© OpenStreetMap contributors (ODbL)' if loc['precision'] == 'exact' else 'City reference: Wikidata (CC0)',
                'location_source': loc['evidence']['url'],
                'stage': STAGE.get(r['status']['stage'], 'Unknown'), 'stage_label': r['status']['label'], 'as_of': r['status']['as_of'],
                'summary': r['presentation']['summary'], 'capacity': r['capacity'],
                'capex_usd_m': (m.get('total_capex') or {}).get('value'), 'target_open': m.get('target_open'),
                'exposure': {'ticker': L['ticker'], 'exchange': {'XNAS': 'Nasdaq', 'XNYS': 'NYSE', 'XASX': 'ASX'}.get(L['exchange'], L['exchange']), 'name': L['name'],
                             'role': e['role'].capitalize(), 'ownership': 'Not established'},
                'sources': [{'name': c['title'], 'url': c.get('url') or r['identity_evidence']['url'], 'checked_at': r['identity_evidence']['checked_at'][:10]} for c in r['presentation']['citations'] if c.get('url')]
                           + [{'name': r['presentation']['citations'][-1]['title'], 'url': loc['evidence']['url'], 'checked_at': loc['evidence']['checked_at']}],
                'images': imgs or None})
doc = {'schema': 'investedia.projects.datacenters.v1', 'as_of': '2026-11-13', 'count': len(out),
       'credit': ['Equinix, Inc. Form 10-K (fiscal 2025), SEC', 'Locations: © OpenStreetMap contributors (ODbL) / Wikidata (CC0)', 'Imagery: contains modified Copernicus Sentinel data'],
       'projects': out}
(FE / 'assets/globe/projects-datacenters.json').write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print(json.dumps({'exported': len(out), 'images_copied': copied, 'with_images': sum(1 for p in out if p['images'])}))
