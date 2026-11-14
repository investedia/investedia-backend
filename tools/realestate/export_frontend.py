#!/usr/bin/env python3
"""Export Real Estate records to the frontend file assets/globe/projects-realestate.json (LOCAL PREVIEW).

Nothing here publishes anything: the owner has not signed the record-bound reviews. Each exported record carries
release_status ("proposed" = in the 30-50 release manifest; "research" = not proposed) so the preview can be checked
against the manifest. Only records with a map point (exact or approximate) are exported; unknown locations stay out.
Usage: export_frontend.py <frontend repo> <photo source dir (scratch img/dl)>
"""
import json, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; FE = Path(sys.argv[1]); PH = Path(sys.argv[2])
P5 = json.loads((ROOT / 'data/realestate/phase5b/import-phase5b.json').read_text()); JRE = json.loads((ROOT / 'data/realestate/intl/import-jre-pilot.json').read_text())
MAN = {m['id'] for m in json.loads((ROOT / 'data/realestate/phase5b/release-manifest.json').read_text())['records']}
EXCH = {'XNYS': 'NYSE', 'XNAS': 'Nasdaq', 'XTKS': 'Tokyo', 'XLON': 'London', 'XBRU': 'Euronext Brussels'}
ROLE = {'reported_group_owner': 'Portfolio holding', 'developer': 'Developer', 'lessee': 'Leasehold'}
CREDIT = {'district_reference': 'District reference: Wikidata (CC0)', 'address_point': 'Address point: US Census Geocoder (public domain)', 'building_point': 'Building point: Wikidata (CC0)', 'city_reference': 'City reference: US Census Gazetteer (public domain)'}
photo_dir = FE / 'assets/img/projects/photo'; photo_dir.mkdir(parents=True, exist_ok=True)
out = []
EU = json.loads((ROOT / 'data/realestate/intl/import-eu-pilot.json').read_text())
for r in P5['records'] + JRE['records'] + EU['records']:
    l = r['location']
    if l['precision'] == 'unknown': continue
    plans = r['status']['stage'] in ('under_construction', 'completed', 'planning') or 'evelopment' in r['asset']['subtype']
    if r['status']['stage'] == 'unknown': continue
    if not r['exposures'][0]['investment_access']['verified']: continue  # no documented ticker -> not shown
    if not (r['imagery'] or plans): continue  # owner rule 14 Nov 2026: only properties with a picture or a development plan
    e = r['exposures'][0]; li = e['listing']; jp = r['country_code'] == 'JP'; eu = r['source_identity']['authority'].startswith('company-results')
    src = [{'name': ('Company property data file' if jp else 'Company results release' if eu else 'SEC filing (' + r['identity_evidence']['url'].rsplit('/', 1)[-1] + ')'), 'url': r['identity_evidence']['url'], 'checked_at': r['identity_evidence']['checked_at'][:10]}]
    if r['status'].get('evidence') and r['status']['evidence']['url'] != src[0]['url']:
        src.append({'name': 'SEC Form 10-Q (30 Sep 2026)', 'url': r['status']['evidence']['url'], 'checked_at': r['status']['evidence']['checked_at'][:10]})
    stage = {'operating': 'Operating', 'completed': 'Completed', 'under_construction': 'Under construction', 'planning': 'Planned (consented)', 'unknown': 'Status unresolved'}.get(r['status']['stage'], 'Operating')
    if 'edevelopment' in r['asset']['subtype']: stage = 'Redevelopment' if stage == 'Under construction' else stage
    p = {'id': r['id'], 'name': r['name'], 'city': r.get('city') or (r.get('address', {}).get('text', '').split(',')[-2].strip() if r.get('address') else None), 'cc': r['country_code'],
         'lat': l['lat'], 'lon': l['lon'], 'precision': l['precision'], 'point_type': l.get('point_type') or ('city_reference' if l['precision'] == 'approximate' else None), 'location_class': {'building_point': 'building', 'address_point': 'address', 'city_reference': 'city', 'district_reference': 'district'}.get(l.get('point_type') or 'city_reference'), 'location_label': l['label'],
         'location_credit': 'GSI address search (出典：国土地理院)' if jp else ('Building point: Wikidata (CC0)' if l.get('point_type') == 'building_point' else 'Reference point: Wikidata (CC0)') if eu else CREDIT.get(l.get('point_type') or 'city_reference', 'US Census (public domain)'), 'location_source': l['evidence']['url'],
         'address': (r.get('address') or {}).get('text') or (r.get('identity') or {}).get('address_ja') and l['label'].replace(' (address point)', ''),
         'subtype': r['asset']['subtype'], 'stage': stage, 'stage_label': r['status']['label'], 'as_of': r['status']['as_of'],
         'exposure': {'ticker': li['ticker'], 'exchange': EXCH.get(li['exchange'], li['exchange']), 'name': li['name'].replace('INC.', 'Inc.').replace('HOST HOTELS & RESORTS, Inc.', 'Host Hotels & Resorts, Inc.'), 'security': li['security_type'],
                      'role': ROLE.get(e['role'], e['role']), 'scope': e['relationship_scope'], 'stake': e.get('property_stake')},
         'figures': [{'label': 'Acquisition price (company-published)', 'value': f"¥{r['reported_metrics']['acquisition_price_jpy'] / 1e8:,.1f} hundred million" if False else f"JPY {r['reported_metrics']['acquisition_price_jpy'] / 1e9:,.2f} billion"}] if r.get('reported_metrics', {}).get('acquisition_price_jpy') else [{'label': r['reported_metrics']['label'], 'value': r['reported_metrics']['value']}] if r.get('reported_metrics', {}).get('value') else [],
         'sources': src, 'release_status': 'proposed' if r['id'] in MAN else 'research', 'aliases': (r.get('identity') or {}).get('aliases', [])}
    if r['imagery']:
        im = r['imagery'][0]; fn = 're-' + r['id'].split(':', 1)[1].replace(':', '-') + '.jpg'
        shutil.copyfile(PH / (r['id'].replace(':', '_') + '.jpg'), photo_dir / fn)
        p['photo'] = {'file': '../img/projects/photo/' + fn, 'source_url': im['source_url'], 'author': im['credit'].split(' / ')[0], 'licence': im['licence'], 'date': im.get('capture_date')}
    out.append(p)
doc = {'schema': 'investedia.projects.realestate.v1', 'as_of': '2026-11-14', 'preview': True, 'count': len(out),
       'note': 'LOCAL PREVIEW - not approved for publication. release_status marks the proposed first release.',
       'credit': ['BXP, Inc. and Host Hotels & Resorts, Inc. Forms 10-K (FY2025) and 10-Q (Q3 2026), SEC', 'Japan Real Estate Investment Corporation portfolio data', 'Locations: US Census (public domain), Wikidata (CC0), GSI Japan', 'Photos: Wikimedia Commons contributors (licences per image)'],
       'projects': out}
(FE / 'assets/globe/projects-realestate.json').write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')))
print(len(out), 'exported;', sum(1 for p in out if p.get('photo')), 'with photos;', sum(p['release_status'] == 'proposed' for p in out), 'proposed')
