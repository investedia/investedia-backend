#!/usr/bin/env python3
"""Real Estate Phase 5B: enrich the 163 batch-1 records in place (same ids, evidence history kept).

Inputs: data/realestate/batch1/import-batch1.json (batch 1, unchanged) + data/realestate/batch1/evidence/*.json
Outputs: data/realestate/phase5b/ (import envelope v2, retirements, events, company reconciliation, imagery,
release manifest + per-record review, stats).

Location ladder (never a city centre presented as a building):
  exact / building_point   Wikidata (CC0) building coordinate within 150 m of the company's own property pin
  exact / address_point    US Census geocode (public domain) of the company-published address, within 400 m of the
                           company pin (Host) or of an address that IS the filing's property name (BXP);
                           confidence high (<=150 m from the company pin) or medium (150-400 m / no company pin)
  approximate / city       US Census Gazetteer city point (labelled "city reference, not the building")
  unknown                  no verified point; no map pin
Company pins themselves (hosthotels.com) are kept as research evidence only (website terms unreviewed).
Usage: enrich_5b.py
"""
import copy, hashlib, json, math, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research/data-centers/phase4'))
from sector_adapter import validate, digest, public_projection  # noqa: E402

B1 = ROOT / 'data/realestate/batch1'; EVD = B1 / 'evidence'; OUT = ROOT / 'data/realestate/phase5b'; OUT.mkdir(parents=True, exist_ok=True)
J = lambda p: json.loads(Path(p).read_text(encoding='utf-8'))
env = J(B1 / 'import-batch1.json'); base = {r['id']: r for r in env['records']}; companies = env['companies']
hostp = {p['url']: p for p in J(EVD / 'host-portfolio-page.json')}; hcen = J(EVD / 'host-census-geocodes.json'); hmatch = J(EVD / 'host-name-matches.json')
bcen = J(EVD / 'bxp-census-geocodes.json'); wd = J(EVD / 'wikidata-image-matches.json'); commons = J(EVD / 'commons-licences.json')
NOW = '2026-11-14T00:00:00Z'
SRC = {
 'host_web': {'url': 'https://www.hosthotels.com/Our-Portfolio/Portfolio-Overview', 'sha256': 'd77fbacef3308cb4f53bcd219e67ef59da9431f0cf98160cd2d04c45c5d729d1', 'checked_at': '2026-11-14T03:05:00Z'},
 'hst_10q': {'url': 'https://www.sec.gov/Archives/edgar/data/0001070750/000107075026000156/hst-20260930.htm', 'sha256': 'e185f8b047a1ed9bf53604213e2477e53feee050c32bc990aa1d1a203f5e6dca', 'checked_at': '2026-11-14T03:20:00Z'},
 'bxp_10q': {'url': 'https://www.sec.gov/Archives/edgar/data/0001037540/000103754026000043/bxp-20260930.htm', 'sha256': '1ba0289c105f2d816f2c8c9804fb4295fa74ea350bab5325cd03e117112d5d9f', 'checked_at': '2026-11-14T03:20:00Z'},
 'avb_8k': {'url': 'https://www.sec.gov/Archives/edgar/data/915912/000110465926097833/tm2623381d1_8k.htm', 'sha256': 'c24565f909291f79e2a9f0d9d9391642ca341c27f48e058886f28091caab5c31', 'checked_at': '2026-11-14T03:40:00Z'},
 'vmrk_8k': {'url': 'https://www.sec.gov/Archives/edgar/data/906107/000119312526448699/vmrk-20261104.htm', 'sha256': '22e5561ef981210e280a7415eedbd8a2a937a2b12b5c4af52932929abebd3142', 'checked_at': '2026-11-14T03:40:00Z'},
}
def ev(src, locator, **kw): return {**SRC[src], 'locator': locator, 'sha256_scope': 'source_body', **kw}
def hav(a, b, c, d): p = math.radians; return 2 * 6371000 * math.asin(math.sqrt(math.sin(p(c - a) / 2) ** 2 + math.cos(p(a)) * math.cos(p(c)) * math.sin(p(d - b) / 2) ** 2))
def cen_ev(g, rid): return {'url': g['url'], 'sha256': g['sha256'], 'checked_at': '2026-11-14T03:10:00Z', 'locator': f"US Census Geocoder match: {g['matched']}", 'sha256_scope': 'source_body', 'record_id': rid, 'scope': 'specific_site'}

GAZ = Path(sys.argv[1]) if len(sys.argv) > 1 else None  # scratch dir holding gaz/ (US Census Gazetteer)
gaz = {}
if GAZ:
    GZSHA = hashlib.sha256((GAZ / 'gaz/gaz.zip').read_bytes()).hexdigest()
    for line in (GAZ / 'gaz/2024_Gaz_place_national.txt').read_text(encoding='utf-8', errors='replace').splitlines()[1:]:
        c = line.split('\t'); nm = re.sub(r' (city|town|village|CDP|borough|municipality)$', '', c[3].strip())
        gaz.setdefault((c[0], nm.lower().replace('st. ', 'st ')), []).append((float(c[10]), float(c[11].strip()), c[3].strip(), c[1]))
def city_point(rid, city, st):
    h = gaz.get((st, city.lower().replace('st. ', 'st ')))
    if h and len(h) > 1: h = [x for x in h if not x[2].endswith(' CDP')]
    if not h or len(h) != 1: return None
    lat, lon, full, geoid = h[0]
    return {'precision': 'approximate', 'point_type': 'city_reference', 'lat': round(lat, 5), 'lon': round(lon, 5), 'label': f'{city}, {st} (city reference point, not the building)', 'basis': 'US Census 2024 Gazetteer place point for the city in the company-published address (public domain)', 'satellite_allowed': False,
            'evidence': {'url': 'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_place_national.zip', 'sha256': GZSHA, 'checked_at': '2026-11-14T02:37:00Z', 'locator': f'Gazetteer place GEOID {geoid} ({full}, {st})', 'sha256_scope': 'source_body', 'record_id': rid, 'scope': 'city_reference'}}
records = {}; research = []; stats_loc = {}
# ---------------- locations + identity ----------------
for rid, r0 in base.items():
    r = copy.deepcopy(r0); hist = {'batch1_location': r0['location'], 'batch1_fact_sha256': digest({k: v for k, v in r0.items() if k != 'reuse'})}
    loc = None; aliases = set(); pin = None
    m = hmatch.get(rid)
    if m and m[1] >= 0.6:
        p = hostp[m[0]]; pin = (p['lat'], p['lon']); aliases.add(p['name'].strip())
        r['address'] = {'text': p['address'].strip(), 'source': 'company website portfolio page', 'evidence': ev('host_web', f"Portfolio page entry {p['url']}: address")}
        r['research'] = {'company_pin': {'lat': p['lat'], 'lon': p['lon'], 'evidence': ev('host_web', f"Portfolio page entry {p['url']}: latitude/longitude"), 'reuse': 'pending (website terms not reviewed); internal cross-check only'}}
        g = hcen.get(m[0], {})
        w = wd.get(rid)
        if w and hav(p['lat'], p['lon'], w['wd_lat'], w['wd_lon']) <= 150:
            loc = {'precision': 'exact', 'point_type': 'building_point', 'confidence': 'high', 'lat': round(w['wd_lat'], 6), 'lon': round(w['wd_lon'], 6),
                   'label': f"{p['address'].strip()} (building point)", 'basis': f"Wikidata {w['qid']} coordinate (CC0) within {round(hav(p['lat'], p['lon'], w['wd_lat'], w['wd_lon']))} m of the company's own property pin", 'satellite_allowed': True,
                   'evidence': {'url': f"https://www.wikidata.org/wiki/{w['qid']}", 'sha256': hashlib.sha256(json.dumps(w, sort_keys=True).encode()).hexdigest(), 'checked_at': '2026-11-14T04:00:00Z', 'locator': f"Wikidata {w['qid']} P625 ({w['label']})", 'sha256_scope': 'query_result_row', 'record_id': rid, 'scope': 'specific_site'}}
        elif 'lat' in g and g['dist_m'] <= 400:
            loc = {'precision': 'approximate', 'point_type': 'address_point', 'confidence': 'high' if g['dist_m'] <= 150 else 'medium', 'lat': round(g['lat'], 6), 'lon': round(g['lon'], 6),
                   'label': f"{g['matched'].title()} (verified address point, not a building outline)", 'basis': f"US Census geocode of the company-published address; {g['dist_m']} m from the company's own pin", 'satellite_allowed': False, 'evidence': cen_ev(g, rid)}
        else:
            reason = 'Census geocode disagrees with the company pin by more than 400 m' if 'lat' in g else 'no Census match' if 'skip' not in g else 'non-US address (no public-domain geocoder used)'
            r['research']['location_gap'] = reason
            cm = re.search(r',\s*([^,]+),\s*([A-Z]{2})\s+\d{5}', p['address'])
            cp = city_point(rid, cm.group(1).strip(), cm.group(2)) if cm else None
            if cp: loc = cp
    elif rid in bcen and 'lat' in bcen[rid]:
        g = bcen[rid]; w = wd.get(rid)
        conf = 'high' if (w and hav(g['lat'], g['lon'], w['wd_lat'], w['wd_lon']) <= 150) else 'medium'
        loc = {'precision': 'approximate', 'point_type': 'address_point', 'confidence': conf, 'lat': round(g['lat'], 6), 'lon': round(g['lon'], 6),
               'label': f"{g['matched'].title()} (verified address point, not a building outline)", 'basis': 'US Census geocode of the street address that is the property name in the 10-K' + ('; Wikidata building coordinate within 150 m' if conf == 'high' else '; single geocode, no second point'),
               'satellite_allowed': False, 'evidence': cen_ev(g, rid)}
        r['address'] = {'text': g['matched'].title(), 'source': '10-K property name geocoded by US Census', 'evidence': cen_ev(g, rid)}
    if loc: r['location'] = loc
    if rid in wd: aliases.add(wd[rid]['label'])
    aliases.discard(r['name'])
    if aliases: r['identity'] = {'aliases': sorted(aliases), 'normalized_name': re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', r['name'].lower())).strip()}
    r['history'] = hist
    records[rid] = r

# ---------------- post-FY2025 events (Q3 2026 10-Qs) ----------------
events = []
def event(rid, kind, date, src, locator, effect):
    e = {'event_id': f'{rid}#{kind}#{date}', 'property_id': rid, 'type': kind, 'event_date': date, 'evidence': ev(src, locator), 'effect': effect, 'review': 'proposed (human review required)'}
    events.append(e); return e
retire = []
for rid, date, loc in [('re:hst:sheraton-parsippany-hotel', '2026-06-30', 'MD&A: sales of ... and the Sheraton Parsippany Hotel during the first half of 2026'),
                       ('re:bxp:sumner-square', '2026-08-05', 'Dispositions table: Sumner Square, Washington, DC, August 5, 2026'),
                       ('re:bxp:1330-connecticut-avenue', '2026-09-23', 'Dispositions table: 1330 Connecticut Avenue, Washington, DC, September 23, 2026'),
                       ('re:bxp:the-lofts-at-atlantic-wharf', '2026-02-25', 'Dispositions table: The Lofts at Atlantic Wharf, Boston, MA, February 25, 2026')]:
    src = 'hst_10q' if 'hst' in rid else 'bxp_10q'
    event(rid, 'disposal', date, src, loc, 'company no longer holds the property; record retired (history kept)')
    retire.append({'id': rid, 'reason': f'Disposed by the company ({date[:7] if "parsippany" in rid else date}); {loc}', 'as_of': '2026-09-30'})
event('re:bxp:121-broadway', 'duplicate_merged', '2025-12-31', 'bxp_10q', 'Construction/Redevelopment table: 121 Broadway Street (439 units) - same project as the Schedule III row "121 Broadway"', 'merged into re:bxp:121-broadway-street')
retire.append({'id': 're:bxp:121-broadway', 'reason': 'Duplicate identity: Schedule III row for the 121 Broadway Street development (kept as re:bxp:121-broadway-street)', 'as_of': '2026-11-14'})
records['re:bxp:121-broadway-street'].setdefault('identity', {}).setdefault('aliases', []).append('121 Broadway')
event('re:bxp:kingstowne-towne-center', 'partial_disposal', '2026-04-17', 'bxp_10q', 'Dispositions table: Kingstowne Retail, Alexandria, VA, April 17, 2026', 'retail component sold; office record kept, flagged for review')
records['re:bxp:kingstowne-towne-center'].setdefault('flags', []).append('Kingstowne Retail (88,300 sq ft) sold 17 Apr 2026; confirm what remains')
for rid, date, loc in [('re:bxp:reston-next-retail', '2026-01-16', 'Development: on January 16, 2026, the Company fully placed in-service Reston Next Retail'),
                       ('re:bxp:290-binney-street', '2026-04-30', 'Development: on April 30, 2026, the Company fully placed in-service 290 Binney Street (55% consolidated JV)')]:
    event(rid, 'development_completed', date, 'bxp_10q', loc, 'status -> completed')
    r = records[rid]; r['status'] = {'stage': 'completed', 'label': f'Placed in service {date} (company-reported)', 'as_of': '2026-09-30', 'certainty': 'company_reported', 'evidence': ev('bxp_10q', loc)}
    r['history']['batch1_status'] = base[rid]['status']
# construction table refresh (target dates as of 30 Sep 2026)
for rid, tgt, loc in [('re:bxp:725-12th-street', 'Q3 2029', '725 12th Street (Redevelopment) Q3 2029 Washington, DC'), ('re:bxp:343-madison-avenue', 'Q2 2031', '343 Madison Avenue (89.45% ownership) Q2 2031'),
                      ('re:bxp:17-hartwell-avenue', 'Q2 2028', 'Reverie - 17 Hartwell Avenue (312 units) (20% ownership) Q2 2028'), ('re:bxp:121-broadway-street', 'Q2 2029', '121 Broadway Street (439 units) Q2 2029'),
                      ('re:bxp:290-coles-street', 'Q3 2029', '290 Coles Street (670 Units) (19.46% ownership) Q3 2029')]:
    r = records[rid]; old = r['status']['label']
    r['status'] = {**r['status'], 'label': re.sub(r'stabilization Q\d \d{4}', f'stabilization {tgt}', old), 'as_of': '2026-09-30', 'evidence': ev('bxp_10q', f'Construction/Redevelopment table at September 30, 2026: {loc}')}
    if old != r['status']['label']: event(rid, 'target_date_change', '2026-09-30', 'bxp_10q', loc, f'{old} -> {r["status"]["label"]}')
records['re:bxp:651-gateway']['status'] = {'stage': 'unknown', 'label': 'Not listed in the 30 Sep 2026 construction table and not otherwise mentioned in the 10-Q; status unresolved', 'as_of': '2026-09-30', 'certainty': 'unresolved'}
event('re:bxp:651-gateway', 'status_unresolved', '2026-09-30', 'bxp_10q', 'Absent from Construction/Redevelopment table at September 30, 2026', 'status -> unknown pending a source')
# stated JV shares (mortgage notes table) -> specific-property stake
for rid, pct in [('re:bxp:767-fifth-avenue-the-general-motors-building', 60.0), ('re:bxp:601-lexington-avenue', 55.0), ('re:bxp:343-madison-avenue', 89.45)]:
    r = records[rid]; e = r['exposures'][0]; pev = ev('bxp_10q', f'Mortgage notes table, Consolidated Joint Ventures: {r["name"]} ({pct:g}% ownership)', record_id=rid, scope='specific_property')
    e.update(property_stake=pct, stake_scope='specific_property', property_evidence=pev, relationship_scope=e['relationship_scope'].split(';')[0] + f'; company-stated {pct:g}% ownership through a consolidated joint venture')
    event(rid, 'ownership_share_documented', '2026-09-30', 'bxp_10q', pev['locator'], f'stake {pct:g}%')
# acquisitions (new records)
hst_ref = [k for k, v in companies.items() if v['listing']['ticker'] == 'HST'][0]
for name, slug, date, role, interest, url in [('Renaissance Dallas at Plano Legacy West Hotel', 'renaissance-dallas-at-plano-legacy-west-hotel', '2026-10-14', 'reported_group_owner', 'fee simple interest', '/Properties/Domestic/Texas/Renaissance-Dallas-at-Plano-Legacy-West-Hotel'),
                                               ('1 Hotel Brooklyn Bridge', '1-hotel-brooklyn-bridge', '2026-10-30', 'lessee', 'leasehold interest', '/Properties/Domestic/New-York/1-Hotel-Brooklyn-Bridge')]:
    rid = f're:hst:{slug}'; p = hostp[url]; g = hcen[url]; loc_ev = f'Subsequent events: on {date}, we acquired the {interest} in the {name}'
    e0 = ev('hst_10q', loc_ev)
    r = {'schema': base['re:hst:the-don-cesar']['schema'], 'id': rid, 'source_identity': {'authority': 'sec.gov:10-Q:HST', 'id': slug}, 'synthetic': False, 'name': name, 'sector': 'real_estate', 'country_code': 'US', 'city': None,
         'asset': {'category': 'existing_asset', 'subtype': 'Hotel', 'parent_id': None, 'count_as_project': True}, 'status': {'stage': 'operating', 'label': f'Acquired {date} (company-reported)', 'as_of': '2026-11-06', 'certainty': 'company_reported'},
         'location': {'precision': 'approximate', 'point_type': 'address_point', 'confidence': 'high' if g['dist_m'] <= 150 else 'medium', 'lat': round(g['lat'], 6), 'lon': round(g['lon'], 6), 'label': f"{g['matched'].title()} (verified address point, not a building outline)", 'basis': f"US Census geocode of the company-published address; {g['dist_m']} m from the company's own pin", 'satellite_allowed': False, 'evidence': cen_ev(g, rid)},
         'identity_evidence': e0, 'exposures': [{'role': role, 'label': 'Acquired hotel (fee simple)' if role != 'lessee' else 'Acquired leasehold interest (not freehold)', 'relationship_scope': f'Company-reported acquisition of the {interest}; holding entity not established', 'property_stake': None, 'company_ref': hst_ref, 'evidence': e0, 'listing': companies[hst_ref]['listing'], 'headquarters': None, 'investment_access': {'type': 'listed_REIT', 'verified': True, 'scope': 'Indirect listed-REIT equity exposure only; buying shares gives no title to this property'}}],
         'imagery': [], 'verification': {'classification': 'company_confirmed', 'date': '2026-11-14', 'property_title_verified': False}, 'address': {'text': p['address'].strip(), 'source': 'company website portfolio page', 'evidence': ev('host_web', f'Portfolio page entry {url}: address')},
         'reuse': copy.deepcopy(base['re:hst:the-don-cesar']['reuse']), 'preview_only': True, 'history': {'created': 'phase5b acquisition event'}}
    records[rid] = r; event(rid, 'acquisition', date, 'hst_10q', loc_ev, 'new record')
for nm in ['Hyatt Place Nashville Downtown', 'Fort Lauderdale Marriott Harbor Beach Resort & Spa']:
    research.append({'name': nm, 'company': 'HST', 'reason': 'On the company website only; not in the FY2025 10-K consolidated table or the Q3 2026 10-Q acquisitions (may be unconsolidated / managed)'})

# ---------------- imagery (Wikimedia Commons, visually checked) ----------------
REJECT = {'re:hst:fairmont-kea-lani-maui': 'interior garden view; does not identify the building', 're:hst:tampa-airport-marriott': 'lobby interior; does not identify the building'}
OKLIC = re.compile(r'^(CC BY(-SA)? [0-9.]+|CC0|Public domain)$', re.I)
img_audit = {}
for rid, c in commons.items():
    if rid not in records: continue
    st = 'rejected: ' + REJECT[rid] if rid in REJECT else 'pending: licence checked, image not yet downloaded/visually checked (Commons rate limit)' if 'thumb_sha256' not in c else 'rejected: licence not commercial-compatible' if not OKLIC.match(c['licence']) else 'accepted'
    img_audit[rid] = {**c, 'status': st, 'wikidata': wd.get(rid, {}).get('qid')}
    if st == 'accepted':
        r = records[rid]
        r['imagery'] = [{'type': 'photo', 'project_id': rid, 'url': c['thumb'], 'source_url': c['page'], 'rights_status': 'cleared', 'licence': c['licence'], 'licence_url': c['licence_url'],
                         'credit': f"{c['artist'] or 'Unknown'} / Wikimedia Commons, {c['licence']}", 'capture_date': c['date'][:10] or None, 'sha256': c['thumb_sha256'],
                         'identity_check': f"Commons file is the Wikidata image (P18) of {wd[rid]['qid']} '{wd[rid]['label']}', {wd[rid]['dist_m']} m from the property point; visually checked 2026-11-14", 'geo_accuracy': 'building photo'}]
        r['reuse']['fields']['imagery'] = {'status': 'cleared', 'basis': f"{c['licence']} with attribution; share-alike applies to the image file only" if 'SA' in c['licence'] else f"{c['licence']} with attribution"}

# ---------------- monitoring compatibility (no monitoring activated) ----------------
for rid, r in records.items():
    refs = sorted({json.dumps({'url': x['url'], 'sha256': x['sha256']}, sort_keys=True) for x in [r['identity_evidence'], *[e['evidence'] for e in r['exposures']], r['location'].get('evidence') or r['identity_evidence'], r['status'].get('evidence') or r['identity_evidence']]})
    fact = {k: v for k, v in r.items() if k not in ('reuse', 'monitoring', 'history')}
    r['monitoring'] = {'stable_id': rid, 'evidence_refs': [json.loads(x) for x in refs], 'last_verified_at': NOW, 'fact_fingerprint': digest(fact), 'watch': ['status', 'ownership', 'acquisition_disposal', 'evidence_hash'], 'enabled': False}
    validate(r)

# ---------------- company reconciliation ----------------
recon = {'as_of': '2026-11-14', 'companies': [
  {'name': 'BXP, Inc.', 'ticker': 'BXP', 'exchange': 'XNYS', 'status': 'listed', 'former_names': ['Boston Properties, Inc.'], 'records': sum(k.startswith('re:bxp') for k in records)},
  {'name': 'Host Hotels & Resorts, Inc.', 'ticker': 'HST', 'exchange': 'XNAS', 'status': 'listed', 'former_names': ['Host Marriott Corp'], 'records': sum(k.startswith('re:hst') for k in records)},
  {'name': 'Vivmark Residential', 'ticker': 'VMRK', 'exchange': 'XNYS', 'status': 'listed', 'former_names': [{'name': 'Equity Residential', 'until': '2026-08-12', 'ticker': 'EQR'}],
   'events': [{'type': 'rename', 'date': '2026-08-12', 'detail': 'Equity Residential renamed Vivmark Residential (SEC former-name record ends 2026-08-12)'},
              {'type': 'merger', 'date': '2026-08-17', 'detail': 'AvalonBay Communities merged into a Vivmark subsidiary; each AVB share converted into 2.793 Vivmark common shares', 'evidence': ev('avb_8k', 'Introductory Note / Item 2.01: closing on August 17, 2026; exchange ratio 2.793')}],
   'evidence': ev('vmrk_8k', '8-K cover: Common Shares of Beneficial Interest, VMRK, New York Stock Exchange'), 'records': 0, 'next': 'AvalonBay (316) and Equity Residential FY2025 Schedule III communities map to Vivmark only after a post-merger Vivmark property list confirms current holding'},
  {'name': 'AvalonBay Communities, Inc.', 'ticker': 'AVB', 'status': 'delisted 2026-08-17 (merged into Vivmark)', 'evidence': ev('avb_8k', 'Item 3.01: shares removed from trading on the NYSE prior to market open on August 17, 2026'), 'live_exposure': False},
]}
# ---------------- release proposal ----------------
def score(r):
    l = r['location']; s = 0
    s += {'building_point': 40, 'address_point': 30}.get(l.get('point_type'), 0) + (10 if l.get('confidence') == 'high' else 0)
    s += 25 if r['imagery'] else 0; s += 10 if r['status']['stage'] in ('under_construction', 'completed') else 0
    s += 5 if r['exposures'][0].get('property_stake') else 0
    return s
retired = {x['id'] for x in retire}
pool = [r for r in records.values() if (r['imagery'] or r['status']['stage'] in ('under_construction', 'completed') or 'evelopment' in r['asset']['subtype']) and r['id'] not in retired and not r.get('flags') and r['status']['stage'] != 'unknown' and r['location'].get('point_type') in ('building_point', 'address_point')]  # owner rule: picture or development plan
pool.sort(key=lambda r: (-score(r), r['id'])); chosen = pool[:45]
review = []
for r in sorted(records.values(), key=lambda r: r['id']):
    blockers = []
    if r['id'] in retired: blockers.append('disposed (retired)')
    if r.get('flags'): blockers += r['flags']
    if r['status']['stage'] == 'unknown': blockers.append('status unresolved')
    if r['location'].get('point_type') not in ('building_point', 'address_point'): blockers.append(f"location {r['location'].get('point_type') or r['location']['precision']}")
    if any(f['status'] != 'cleared' for f in r['reuse']['fields'].values()): blockers.append('reuse pending')
    blockers.append('owner record-bound review not signed')
    review.append({'id': r['id'], 'name': r['name'], 'company': r['exposures'][0]['listing']['ticker'], 'role': r['exposures'][0]['role'], 'stake': r['exposures'][0].get('property_stake'),
                   'stage': r['status']['stage'], 'location': f"{r['location']['precision']}/{r['location'].get('point_type', '-')}/{r['location'].get('confidence', '-')}", 'image': bool(r['imagery']),
                   'proposed_release': r in chosen, 'score': score(r), 'blockers': blockers, 'fact_sha256': digest({k: v for k, v in r.items() if k not in ('reuse', 'legacy_energy')})})
manifest = {'schema': 'investedia.realestate.release-proposal.v1', 'created': '2026-11-14', 'status': 'PROPOSED - not published; needs owner sign-off per record',
            'count': len(chosen), 'records': [{'id': r['id'], 'fact_sha256': next(x['fact_sha256'] for x in review if x['id'] == r['id'])} for r in chosen],
            'gates': ['verified listing (10-K cover = current SEC)', 'company-confirmed relationship', 'exact address/building point', 'status known and not disposed', 'all reuse fields cleared', 'owner signs fact_sha256']}
# ---------------- write ----------------
sys.path.insert(0, str(ROOT / 'research/data-centers/scale'))
from import_projects import resolve_companies  # noqa: E402  (retirement hash = stored, company-resolved batch-1 version)
resolved = {r['id']: r for r in resolve_companies(list(base.values()), companies, refresh=True)}
out = {'schema': 'investedia.projects.import.v1', 'synthetic': False, 'companies': companies, 'records': sorted((r for r in records.values() if r['id'] not in retired), key=lambda r: r['id']),
       'retire': [{**x, 'expected_sha256': digest(resolved[x['id']])} for x in retire]}
(OUT / 'retired-records.json').write_text(json.dumps([records[x['id']] for x in retire], indent=1, ensure_ascii=False))
for name, obj in [('import-phase5b.json', out), ('events.json', events), ('company-reconciliation.json', recon), ('imagery-audit.json', img_audit), ('release-manifest.json', manifest), ('release-review.json', review), ('research-candidates.json', research)]:
    (OUT / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False))
from collections import Counter
live = [r for r in records.values() if r['id'] not in retired]
st = {'records_total': len(records), 'retired_disposed': len(retired), 'live': len(live), 'new_acquisitions': 2,
      'location': Counter(f"{r['location']['precision']}/{r['location'].get('point_type', '-')}/{r['location'].get('confidence', '-')}" for r in live),
      'precision': Counter(r['location']['precision'] for r in live), 'location_class': Counter({'building_point': 'building point', 'address_point': 'verified address point', 'city_reference': 'approximate city point', 'district_reference': 'approximate district point'}.get(r['location'].get('point_type'), 'approximate city point' if r['location']['precision'] == 'approximate' else 'unknown') for r in live), 'with_address': sum('address' in r for r in live), 'with_aliases': sum('identity' in r for r in live),
      'imagery': Counter(v['status'].split(':')[0] for v in img_audit.values()), 'records_with_photo': sum(bool(r['imagery']) for r in live),
      'stage': Counter(r['status']['stage'] for r in live), 'roles': Counter(r['exposures'][0]['role'] for r in live), 'stated_stakes': sum(r['exposures'][0].get('property_stake') is not None for r in live),
      'events': Counter(e['type'] for e in events), 'release_proposed': len(chosen), 'release_proposed_with_photo': sum(bool(r['imagery']) for r in chosen)}
(OUT / 'stats.json').write_text(json.dumps(st, indent=1))
print(json.dumps(st, indent=1))
