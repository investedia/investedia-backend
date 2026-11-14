#!/usr/bin/env python3
"""Per-record owner approval manifest for the 20 owner-selected first-release candidates (owner decision 14 Nov 2026).

For each record: identity, company relationship, qualification evidence (verified photograph or documented development
plan), coordinates with class, licensing per field, attribution lines, fact_sha256 and blockers. "owner_approval" is
null for every record; nothing is published until the owner fills it in per record.
Usage: approval_manifest.py
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research/data-centers/phase4'))
from sector_adapter import digest  # noqa: E402
P5 = ROOT / 'data/realestate/phase5b'
ids = json.loads((P5 / 'owner-selected-20.json').read_text())
HOLDS = json.loads((P5 / 'holds.json').read_text())
recs = {r['id']: r for r in json.loads((P5 / 'import-phase5b.json').read_text())['records']}
CLASS = {'building_point': 'Building point', 'address_point': 'Verified address point (not a building outline)', 'city_reference': 'Approximate city point', 'district_reference': 'Approximate district point'}
LOC_CREDIT = {'building_point': 'Location: Wikidata (CC0)', 'address_point': 'Location: US Census Geocoder (public domain)', 'city_reference': 'Location: US Census Gazetteer (public domain)'}
out, md = [], []
for rid in ids:
    r = recs[rid]; e = r['exposures'][0]; l = r['location']; pt = l.get('point_type') or ('city_reference' if l['precision'] == 'approximate' else None)
    photo = r['imagery'][0] if r['imagery'] else None
    plan = r['status']['stage'] in ('under_construction', 'completed') or 'evelopment' in r['asset']['subtype']
    qual = []
    if photo: qual.append({'type': 'verified_photograph', 'file_page': photo['source_url'], 'licence': photo['licence'], 'licence_url': photo.get('licence_url'), 'author_credit': photo['credit'], 'capture_date': photo.get('capture_date'), 'identity_check': photo['identity_check'], 'local_copy_sha256': photo['sha256']})
    if plan: qual.append({'type': 'development_plan', 'stage': r['status']['stage'], 'statement': r['status']['label'], 'as_of': r['status']['as_of'], 'evidence': r['status'].get('evidence') or r['identity_evidence']})
    fields = r['reuse']['fields']
    NICE = {'HOST HOTELS & RESORTS, INC.': 'Host Hotels & Resorts, Inc.'}
    attribution = [f"Facts: {NICE.get(e['listing']['name'], e['listing']['name'])} SEC filings (Form 10-K FY2025" + (', Form 10-Q Q3 2026' if r['status'].get('evidence') else '') + ')', LOC_CREDIT.get(pt, 'Location: none shown')]
    if photo: attribution.append(f"Photo: {HOLDS['retained_historical_photos'].get(rid, {}).get('credit_override') or photo['credit'].split(' / ')[0]}, {photo['licence']}, via Wikimedia Commons" + (f" ({HOLDS['retained_historical_photos'][rid]['label']})" if rid in HOLDS['retained_historical_photos'] else ''))
    blockers = []
    if rid in HOLDS['holds']: blockers.append('OWNER HOLD (' + HOLDS['holds'][rid]['type'] + '): ' + HOLDS['holds'][rid]['reason'])
    if rid in HOLDS['retained_historical_photos']: blockers.append('Historical photo retained: label "' + HOLDS['retained_historical_photos'][rid]['label'] + '" must be shown')
    if pt not in ('building_point', 'address_point'): blockers.append(f'Location is only an {CLASS.get(pt, "unknown location").lower()}; the marker will show the city, not the building')
    if any(v['status'] == 'pending' for v in fields.values()): blockers.append('A reuse field is pending')
    blockers.append('Owner approval not yet given for this record')
    fact = digest({k: v for k, v in r.items() if k not in ('reuse', 'legacy_energy')})
    rec = {'id': rid, 'name': r['name'], 'aliases': (r.get('identity') or {}).get('aliases', []), 'address': (r.get('address') or {}).get('text'),
           'company': {'name': e['listing']['name'], 'ticker': e['listing']['ticker'], 'exchange': e['listing']['exchange'], 'listing_evidence': e['listing']['evidence']},
           'relationship': {'role': e['role'], 'label': e['label'], 'scope': e['relationship_scope'], 'stated_share_pct': e.get('property_stake'), 'evidence': e['evidence'], 'title_claimed': False,
                            'investor_note': 'Buying shares gives exposure to the company only, not title to this property'},
           'qualifies_by': qual, 'coordinates': {'class': CLASS.get(pt, 'Unknown'), 'lat': l.get('lat'), 'lon': l.get('lon'), 'label': l['label'], 'basis': l.get('basis'), 'evidence': l.get('evidence')},
           'licensing': {k: v for k, v in fields.items()}, 'attribution': attribution, 'fact_sha256': fact, 'hold': HOLDS['holds'].get(rid), 'blockers': blockers, 'owner_approval': None}
    out.append(rec)
    md.append(f"| {rid} | {r['name']} | {e['listing']['ticker']} | {e['role']}{' ' + str(e['property_stake']) + '%' if e.get('property_stake') else ''} | {' + '.join('photo' if q['type'] == 'verified_photograph' else 'plan: ' + q['stage'] for q in qual)} | {CLASS.get(pt, 'Unknown')} | {'; '.join(b for b in blockers if not b.startswith('Owner'))or '-'} | `{fact[:12]}` |")
doc = {'schema': 'investedia.realestate.approval-manifest.v1', 'created': '2026-11-14', 'status': 'AWAITING OWNER APPROVAL PER RECORD - nothing published', 'count': len(out),
       'how_to_approve': 'Set owner_approval to {"approved": true, "date": "YYYY-MM-DD"} on each record you approve. The fact_sha256 must still match at release time; any change to a record needs re-approval.',
       'records': out}
(P5 / 'approval-manifest.json').write_text(json.dumps(doc, indent=1, ensure_ascii=False))
(P5 / 'APPROVAL-MANIFEST.md').write_text('# First Real Estate release: per-record approval (20 owner-selected candidates)\n\nNothing is published. Approve each record individually in `approval-manifest.json` (`owner_approval`).\n\n'
    '| id | property | ticker | relationship | qualifies by | coordinates | blockers besides approval | fact_sha256 |\n|---|---|---|---|---|---|---|---|\n' + '\n'.join(md) + '\n\nFull per-record detail (identity, evidence URLs and hashes, licences, attribution lines) is in approval-manifest.json.\n')
from collections import Counter
print(len(out), Counter(q['type'] for r in out for q in r['qualifies_by']), Counter(r['coordinates']['class'] for r in out), sum(len(r['blockers']) > 1 for r in out), 'with extra blockers')
