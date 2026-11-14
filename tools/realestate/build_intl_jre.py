#!/usr/bin/env python3
"""International pilot: Japan Real Estate Investment Corporation (TSE 8952), properties held at 31 Mar 2026.

Sources: JRE official portfolio data workbook (English + Japanese editions, sha256 recorded), JRE home page
(TSE code 8952; news: Daido Seimei Niigata Building disposition completed), GSI address search (Geospatial
Information Authority of Japan; government content, attribution required).
- Relationship: JRE reports holding the property (real estate or trust beneficiary interest) with a stated
  "ratio of share of ownership" -> property_stake for that specific property. Legal title registry not checked.
- Location: GSI geocode of the Japanese official address; "exact/address_point" only when the block and lot
  numbers returned match the address; otherwise "approximate" (district point).
- Carried figure: acquisition price (company-published, JPY). No rents, NOI, appraisal values or occupancy.
- Reuse: JRE disclaimer page does not grant reuse rights -> identity/status/relationship "pending";
  GSI location "cleared" with attribution; listing "pending" (exchange source not yet cross-checked).
Usage: build_intl_jre.py
"""
import json, re, sys, unicodedata
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research/data-centers/phase4'))
from sector_adapter import SCHEMA, validate, digest  # noqa: E402
OUT = ROOT / 'data/realestate/intl'; D = json.loads((OUT / 'evidence/jre-held-geocoded.json').read_text(encoding='utf-8'))
WB_EN = {'url': 'https://www.j-re.co.jp/file/en-portfolio_statement_excel-577b451f22aa79125522e7cabbc9beed09852a8e.xlsx', 'sha256': '19674cd3209b548917f03e5820baf62d1225bb4d1dafa28f39f89d92c319fc8b', 'checked_at': '2026-11-14T05:10:00Z'}
WB_JA = {'url': 'https://www.j-re.co.jp/file/portfolio_statement_excel-eb04ad8c3bd2b77b7e6f436eab4b677f27b99dc3.xlsx', 'sha256': 'c63ffe02d376652246b5cbcf1a20c398d448daea2343bfafc2d11a7525069b31', 'checked_at': '2026-11-14T05:20:00Z'}
HOME = {'url': 'https://www.j-re.co.jp/en/', 'sha256': '377b7d67fd200f15374107b8ca9a11cb24a0e70cf2cd127dde6fdbf693d52f6a', 'checked_at': '2026-11-14T05:25:00Z'}
REF = 'registry:tse:8952'
company = {'identity': {'scheme': 'registry', 'value': 'tse:8952', 'evidence': {**HOME, 'locator': 'Home page: Japan Real Estate Investment Corporation (TSE code: 8952)'}},
           'listing': {'name': 'Japan Real Estate Investment Corporation', 'ticker': '8952', 'exchange': 'XTKS', 'exchange_mic': 'XTKS', 'security_type': 'reit_investment_units', 'evidence': {**HOME, 'locator': 'Home page: (TSE code: 8952)'}},
           'headquarters': None}
records, approx, skipped = [], [], []
for o in D:
    if 'NIIGATA' in o['name']: skipped.append({'name': o['name'], 'reason': 'Disposition completed after 31 Mar 2026 (JRE home page news)'}); continue
    slug = re.sub(r'[^a-z0-9]+', '-', o['name'].lower()).strip('-'); rid = f're:jre:{slug}'
    g = o['gsi']; pref = o['address_en'].split(',')[-1].strip()
    ev = {**WB_EN, 'locator': f"Basic data sheet: {o['name']} | {o['address_en']} | ownership ratio {o['ownership_ratio']}", 'sha256_scope': 'source_body'}
    gev = {'url': g['url'], 'sha256': g['sha256'], 'checked_at': '2026-11-14T05:30:00Z', 'locator': f"GSI address search: {g['title']}", 'sha256_scope': 'source_body', 'record_id': rid}
    if g['lat'] is None: skipped.append({'name': o['name'], 'reason': 'no GSI result'}); continue
    if g['block_match']:
        loc = {'precision': 'exact', 'point_type': 'address_point', 'confidence': 'medium', 'lat': g['lat'], 'lon': g['lon'], 'label': f"{o['address_en']} (address point)", 'basis': 'GSI geocode of the official Japanese address; block and lot numbers match', 'satellite_allowed': False, 'evidence': {**gev, 'scope': 'specific_site'}}
    else:
        loc = {'precision': 'approximate', 'point_type': 'district_reference', 'lat': g['lat'], 'lon': g['lon'], 'label': f"{o['address_en']} (district point, not the building)", 'basis': 'GSI geocode resolved only to the district/block, not the lot', 'satellite_allowed': False, 'evidence': {**gev, 'scope': 'district_reference'}}
    stake = round(o['ownership_ratio'] * 100, 4) if isinstance(o['ownership_ratio'], (int, float)) else None
    exp = {'role': 'reported_group_owner', 'label': 'Held in the REIT\'s portfolio (company data file)', 'relationship_scope': 'Company-reported holding of this named property' + (f'; company-stated ownership share {stake:g}%' if stake is not None else '') + '; title registry not checked',
           'property_stake': stake, 'company_ref': REF, 'listing': company['listing'], 'headquarters': None, 'evidence': ev,
           'investment_access': {'type': 'listed_REIT', 'verified': True, 'scope': 'Indirect listed-REIT investment-unit exposure only; buying units gives no title to this property'}}
    if stake is not None: exp.update(stake_scope='specific_property', property_evidence={**ev, 'record_id': rid, 'scope': 'specific_property'})
    r = {'schema': SCHEMA, 'id': rid, 'source_identity': {'authority': 'j-re.co.jp:portfolio-data', 'id': slug}, 'synthetic': False, 'name': o['name'].title().replace('Jre ', 'JRE '), 'sector': 'real_estate', 'country_code': 'JP', 'city': pref.replace(' Prefecture', ''),
         'asset': {'category': 'building', 'subtype': 'Commercial building', 'parent_id': None, 'count_as_project': True, 'building_identity_evidence': ev},
         'status': {'stage': 'operating', 'label': f"Held at 31 Mar 2026; building completed {o['completion'] or 'date not stated'}", 'as_of': '2026-03-31', 'certainty': 'company_reported'},
         'location': loc, 'identity_evidence': ev, 'identity': {'aliases': [o['name_ja']], 'address_ja': o['address_ja']}, 'exposures': [exp], 'imagery': [],
         'verification': {'classification': 'company_confirmed', 'date': '2026-11-14', 'property_title_verified': False},
         'reported_metrics': {'acquisition_price_jpy': o['acq_price_jpy'], 'basis': 'Company-published total acquisition price (not a valuation)'},
         'reuse': {'fields': {'identity': {'status': 'pending', 'basis': 'JRE website disclaimer does not grant reuse; ask JRE or rely on TDnet filings'}, 'status': {'status': 'pending', 'basis': 'same'}, 'economic_relationship': {'status': 'pending', 'basis': 'same'},
                              'listing': {'status': 'pending', 'basis': 'Company page only; cross-check with JPX listing data'}, 'location': {'status': 'cleared', 'basis': 'GSI (Geospatial Information Authority of Japan) content, attribution "出典：国土地理院"'},
                              'reported_metrics': {'status': 'pending', 'basis': 'company figure; reuse pending'}}, 'review': {}},
         'monitoring': {'stable_id': rid, 'evidence_refs': [{'url': WB_EN['url'], 'sha256': WB_EN['sha256']}, {'url': g['url'], 'sha256': g['sha256']}], 'last_verified_at': '2026-11-14T00:00:00Z', 'enabled': False},
         'preview_only': True}
    r['monitoring']['fact_fingerprint'] = digest({k: v for k, v in r.items() if k not in ('reuse', 'monitoring')})
    validate(r); (records if loc['precision'] == 'exact' else approx).append(r)
pilot = records[:50]
env = {'schema': 'investedia.projects.import.v1', 'synthetic': False, 'companies': {REF: company}, 'records': pilot}
(OUT / 'import-jre-pilot.json').write_text(json.dumps(env, indent=1, ensure_ascii=False))
(OUT / 'jre-approximate-research.json').write_text(json.dumps(approx, indent=1, ensure_ascii=False)); (OUT / 'jre-skipped.json').write_text(json.dumps(skipped, indent=1, ensure_ascii=False))
from collections import Counter
print(json.dumps({'pilot': len(pilot), 'approx_research': len(approx), 'skipped': len(skipped), 'by_region': Counter(r['city'] for r in pilot), 'partial_ownership': sum(1 for r in pilot if (r['exposures'][0]['property_stake'] or 100) < 100)}, indent=1, ensure_ascii=False))
