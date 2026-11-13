#!/usr/bin/env python3
"""Convert the official-directory extraction (data/datacentres/candidates.json) into Codex's
investedia.projects.import.v1 envelope (research/data-centers/scale/import.schema.json).

Rules followed (research/data-centers/CLAUDE-HANDOFF.md):
- Stable ids in Codex's scheme: dc:dlr:<Drupal node id>, dc:eqix:<IBX>, dc:coresite:<code>, dc:nextdc:<code>, dc:cyrusone:<code>.
- source_identity = {authority: <operator site + identifier kind>, id: <official identifier>}.
- Records already reviewed by Codex (61 rows) are NOT re-emitted: they are matched on provider + official
  site code / IBX (never name, address or city) and written to a staging file with the new evidence beside the
  old, for field-by-field review. Stronger existing evidence is never overwritten.
- Directory listing = role "affiliation" (official facility record links the listed issuer); never an owner label.
- Location: "exact" only when the operator pin and the geocoded published address agree within 150 m at
  building/address level (validate_pins.py); 150 m-1 km or locality geocodes = "approximate"; disagreement or
  no comparison = "unknown" (no marker). satellite_allowed is always false here (imagery not reviewed).
- Corporate-page reuse stays "pending" (Equinix / Digital Realty terms unresolved); SEC listing ids "cleared".
- preview_only true; imagery empty; production_approved stays false in the importer.
"""
import hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = Path(sys.argv[1]) if len(sys.argv) > 1 else None
CAND = ROOT / 'data/datacentres/candidates.json'
CODEX = ROOT / 'research/data-centers/phase2/phase2-dataset.json'
REG = Path(sys.argv[2]) if len(sys.argv) > 2 else None
OUTDIR = ROOT / 'data/datacentres/import'
TODAY = '2026-11-13'

ISO = {'United States': 'US', 'Canada': 'CA', 'Mexico': 'MX', 'Brazil': 'BR', 'Chile': 'CL', 'Colombia': 'CO', 'Peru': 'PE', 'Argentina': 'AR',
       'United Kingdom': 'GB', 'Ireland': 'IE', 'France': 'FR', 'Germany': 'DE', 'Netherlands': 'NL', 'Belgium': 'BE', 'Luxembourg': 'LU', 'Switzerland': 'CH', 'Austria': 'AT',
       'Italy': 'IT', 'Spain': 'ES', 'Portugal': 'PT', 'Denmark': 'DK', 'Sweden': 'SE', 'Norway': 'NO', 'Finland': 'FI', 'Poland': 'PL', 'Czech Republic': 'CZ', 'Czechia': 'CZ',
       'Bulgaria': 'BG', 'Croatia': 'HR', 'Greece': 'GR', 'Romania': 'RO', 'Serbia': 'RS', 'Türkiye': 'TR', 'Israel': 'IL', 'United Arab Emirates': 'AE', 'Saudi Arabia': 'SA',
       'Oman': 'OM', 'Bahrain': 'BH', 'Qatar': 'QA', 'South Africa': 'ZA', 'Nigeria': 'NG', 'Ghana': 'GH', 'Kenya': 'KE', 'Mozambique': 'MZ', 'Morocco': 'MA', 'Egypt': 'EG',
       "Côte D'ivoire": 'CI', 'Cote D Ivoire': 'CI', "Cote D'ivoire": 'CI', 'Ivory Coast': 'CI', 'Australia': 'AU', 'New Zealand': 'NZ', 'Japan': 'JP', 'Singapore': 'SG', 'Hong Kong': 'HK', 'China': 'CN',
       'South Korea': 'KR', 'India': 'IN', 'Indonesia': 'ID', 'Malaysia': 'MY', 'Philippines': 'PH', 'Thailand': 'TH', 'Taiwan': 'TW', 'Vietnam': 'VN', 'Cyprus': 'CY', 'Iceland': 'IS'}
AUTH = {'equinix': ('equinix.com:ibx', 'eqix'), 'digitalrealty': ('digitalrealty.com:node', 'dlr'), 'coresite': ('coresite.com:facility-code', 'coresite'),
        'nextdc': ('nextdc.com:facility-code', 'nextdc'), 'cyrusone': ('cyrusone.com:facility-code', 'cyrusone')}
COMPANY_REF = {'equinix': 'cik:0001101239', 'digitalrealty': 'cik:0001297996', 'coresite': 'cik:0001053507', 'nextdc': 'lei:529900RTERU3X7G3D672'}

def body_and_hash(url):
    """sha256 of the exact cached response body used for extraction (the cache is keyed by URL)."""
    key = CACHE / (hashlib.sha1(url.encode()).hexdigest() + '.html')
    if not key.exists(): return None, None
    b = key.read_bytes(); return b, hashlib.sha256(b).hexdigest()

DLR_NODES = json.loads((Path(sys.argv[3])).read_text()) if len(sys.argv) > 3 else {}
def dlr_node(code):
    # node id from the official global directory (same body hash as Codex's dlr-global receipt); only unambiguous codes
    v = DLR_NODES.get(code.upper()) or []
    return v[0] if len(v) == 1 else None

_F = None
def reverse_country(lat, lng):
    global _F
    sys.path.insert(0, str(Path(__file__).parent)); from pipeline import Fetcher
    _F = _F or Fetcher(CACHE)
    st, body, _ = _F.get(f'https://nominatim.openstreetmap.org/reverse?format=json&zoom=3&lat={lat}&lon={lng}')
    try: return (json.loads(body).get('address', {}).get('country_code') or '').upper() or None
    except Exception: return None

def stage(st):
    if st.startswith('operational'): return 'operating', 'listed as a facility in the operator directory'
    return {'construction': ('under_construction', 'in development per operator page'), 'proposed': ('planning', 'in planning per operator page')}.get(st, ('unknown', st))

def main():
    cand = json.loads(CAND.read_text(encoding='utf-8'))['records']
    codex = json.loads(CODEX.read_text(encoding='utf-8'))
    existing = {}
    for r in codex['original_records'] + codex['development_records']:
        prov = (r.get('company') or r.get('listed_parent') or r.get('id') or '')
        p = 'dlr' if 'DLR' in prov or r['id'].startswith('dc:dlr') else 'eqix' if 'EQIX' in prov or ':eqix:' in r['id'] else 'coresite' if 'coresite' in r['id'] or 'AMT' in prov else None
        code = (r.get('facility_code') or r['id'].rsplit(':', 1)[-1]).strip().upper()
        if p: existing.setdefault((p, code), []).append(r['id'])
    companies = json.loads(REG.read_text(encoding='utf-8')) if REG else {}
    records, staged, skipped = [], [], []
    for c in cand:
        op = c['operator_key']; auth, short = AUTH[op]; code = (c.get('code') or '').strip().upper()
        body, sha = body_and_hash(c['source_url'])
        if not sha: skipped.append({'id': c['id'], 'reason': 'cached source body missing; cannot hash evidence'}); continue
        sid = code
        if op == 'digitalrealty':
            nid = dlr_node(code)
            if not nid: skipped.append({'id': c['id'], 'reason': 'Digital Realty node id not found in page data'}); continue
            sid = nid
        rid = f'dc:{short}:{sid}'
        match = existing.get((short, code))
        if match:
            staged.append({'existing_ids': match, 'new_source_identity': {'authority': auth, 'id': sid}, 'match_basis': f'same provider + official site code {code}',
                           'new_evidence': {'url': c['source_url'], 'sha256': sha, 'checked_at': c['source_fetched'], 'address': c.get('address'), 'country': c.get('country'),
                                            'coordinates': c['coordinates']}, 'action': 'review field by field; do not overwrite stronger reviewed evidence'})
            continue
        if not c['evidence']['substantiated'] and not (c.get('name') and (c.get('address') or c.get('metro')) and c['coordinates'].get('lat') is not None):
            skipped.append({'id': rid, 'reason': 'not substantiated (missing name/location/country)'}); continue
        country_code = ISO.get(c.get('country'))
        notes = []
        if not country_code and c['coordinates'].get('lat') is not None:
            cc = reverse_country(c['coordinates']['lat'], c['coordinates']['lng'])
            if cc:
                country_code = cc; notes.append({'field': 'country', 'disposition': 'Country not stated on the page; derived from the operator-published coordinates by OpenStreetMap reverse geocoding (ODbL).'})
        addr = c.get('address') or ''
        if c.get('country') == 'United Kingdom' and re.search(r'\bDublin\b|\bIreland\b|\bCo\. ', addr):
            notes.append({'field': 'country', 'disposition': 'Conflict retained: directory country United Kingdom vs Irish address; country withheld pending review.'}); country_code = None
        ev = {'url': c['source_url'], 'sha256': sha, 'checked_at': c['source_fetched'], 'locator': f'Official facility page: site code {code}, address/locality', 'sha256_scope': 'source_body'}
        co = c['coordinates']; cls = co.get('class')
        if cls == 'exact':
            loc = {'precision': 'exact', 'lat': co['lat'], 'lon': co['lng'], 'label': c.get('address') or c.get('metro'),
                   'basis': 'Operator-published map pin agreeing with the geocoded published address (' + (co.get('validation') or '') + ')', 'satellite_allowed': False,
                   'evidence': {**ev, 'record_id': rid, 'scope': 'specific_site', 'locator': f'Official facility page map pin for site {code}; cross-checked against published address'}}
        elif cls == 'approximate':
            loc = {'precision': 'approximate', 'lat': co['lat'], 'lon': co['lng'], 'label': (c.get('metro') or '') + ' reference',
                   'basis': co.get('validation') or co.get('source') or 'approximate', 'satellite_allowed': False, 'evidence': {**ev, 'record_id': rid, 'scope': 'source_reference'}}
        else:
            loc = {'precision': 'unknown', 'lat': None, 'lon': None, 'satellite_allowed': False}
            if co.get('validation'): notes.append({'field': 'location', 'disposition': 'Withheld: ' + co['validation']})
        st, lab = stage(c['status'])
        if op == 'cyrusone':
            expo = [{'role': 'investor', 'label': 'Fund-manager exposure (indirect): CyrusOne is owned by funds managed by KKR and GIP (BlackRock)',
                     'relationship_scope': 'Fund-level; shareholders of KKR/BlackRock do not own CyrusOne or this facility', 'maturity': 'reported', 'property_stake': None,
                     'company_ref': ref, 'evidence': {'url': u, 'sha256': h, 'checked_at': TODAY, 'locator': loc_txt},
                     'investment_access': {'type': 'research_only', 'verified': False, 'scope': 'Fund investors, not listed-equity holders, hold the economics; owner decision pending'}}
                    for ref, u, h, loc_txt in [('cik:0001404912', 'https://www.sec.gov/Archives/edgar/data/1553023/000110465922038090/tm229713d1_ex99-1.htm', companies.get('_evidence', {}).get('cyrusone_exhibit'), 'CyrusOne 8-K Ex. 99.1: acquisition by funds managed by KKR and GIP completed 25 Mar 2022'),
                                               ('cik:0002012383', 'https://www.sec.gov/Archives/edgar/data/2012383/000095017024114208/blk-ex99_1.htm', companies.get('_evidence', {}).get('blk_gip_exhibit'), 'BlackRock 8-K Ex. 99.1: closed acquisition of GIP on 1 Oct 2024')]]
            classification = 'research_only_affiliation'
        else:
            expo = [{'role': 'affiliation', 'label': 'Facility listed in the listed issuer\'s official facility directory',
                     'relationship_scope': 'Directory affiliation; operator/owner/lease scope of this site not established', 'maturity': 'reported', 'property_stake': None,
                     'company_ref': COMPANY_REF[op], 'evidence': ev,
                     'investment_access': {'type': 'research_only', 'verified': False,
                                           'scope': 'Directory affiliation with a verified listed issuer; operator/lease/ownership of this site not yet documented (contract: affiliation is not verified investment exposure)'}}]
            classification = 'company_confirmed'
        rec = {'schema': 'investedia.projects.sector-envelope.proposal.v2', 'id': rid, 'source_identity': {'authority': auth, 'id': sid}, 'synthetic': False,
               'name': c['name'], 'sector': 'data_centers', 'country_code': country_code, 'city': c.get('metro'),
               'asset': {'category': 'building', 'subtype': 'Data center facility', 'parent_id': None, 'count_as_project': True,
                         'building_identity_evidence': {**ev, 'locator': f'Official facility page dedicated to site code {code}'}},
               'status': {'stage': st, 'label': lab, 'as_of': c['source_fetched'][:10], 'certainty': 'company_reported'},
               'location': loc, 'identity_evidence': {k: ev[k] for k in ('url', 'sha256', 'checked_at', 'locator')}, 'exposures': expo, 'imagery': [],
               'verification': {'classification': classification, 'date': TODAY, 'property_title_verified': False},
               'reuse': {'fields': {'identity': {'status': 'pending', 'basis': 'Corporate source terms unresolved (handoff: Equinix/Digital Realty/CoreSite terms)'},
                                    'status': {'status': 'pending', 'basis': 'Corporate source terms unresolved'},
                                    'economic_relationship': {'status': 'pending', 'basis': 'Corporate source terms unresolved'},
                                    'listing': {'status': 'cleared', 'basis': 'SEC / exchange listing identifiers; sources credited'},
                                    'location': {'status': 'pending', 'basis': 'Operator pin (corporate page) and OpenStreetMap geocode (ODbL attribution) not yet cleared for release'},
                                    'reported_metrics': {'status': 'omit', 'basis': 'Corporate capacity/size metrics excluded from the discovery export'}}, 'review': None},
               'preview_only': True, 'notes': notes}
        if c.get('campus'): rec['notes'].append({'field': 'campus', 'disposition': 'Shares a published address with ' + ', '.join(c['campus']['buildings_at_address']) + '; kept as separate buildings (no merge on shared address).'})
        records.append(rec)
    # dedupe on sector + authority + id (importer key)
    seen, uniq, dups = set(), [], 0
    for r in records:
        k = (r['sector'], r['source_identity']['authority'], r['source_identity']['id'])
        if k in seen: dups += 1; continue
        seen.add(k); uniq.append(r)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    comp = {k: v for k, v in companies.items() if not k.startswith('_')}
    (OUTDIR / 'claude-dc-batch-1.json').write_text(json.dumps({'schema': 'investedia.projects.import.v1', 'synthetic': False, 'companies': comp, 'records': uniq}, ensure_ascii=False, indent=1), encoding='utf-8')
    (OUTDIR / 'staged-matches-to-codex-61.json').write_text(json.dumps({'note': 'Matches to existing reviewed rows. Not imported; review field by field.', 'matches': staged}, ensure_ascii=False, indent=1), encoding='utf-8')
    (OUTDIR / 'skipped.json').write_text(json.dumps(skipped, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'input_candidates': len(cand), 'new_records': len(uniq), 'duplicate_source_identities_dropped': dups, 'matched_existing_codex_rows': len(staged), 'skipped': len(skipped)}, indent=1))

if __name__ == '__main__':
    main()
