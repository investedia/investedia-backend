#!/usr/bin/env python3
"""UK/European pilot (Phase 5B): development plans and recent completions from official company results documents.

Sources (sha256 recorded; facts only, no tables or prose copied):
  British Land FY26 results (31 Mar 2026) - committed developments (BL share %, practical completion), completions, consents
  Landsec FY26 results (31 Mar 2026) - committed pipeline (TDC), pre-development assets (planning status), retail projects on site
  SEGRO H1 2026 results (30 Jun 2026) - named completions and pre-let agreements (narrative only; tables are aggregate)
  Montea Q3 2026 interim release (29 Oct 2026) - four projects under construction with completion dates and budgets
  WDP: Q3 2026 PDF blocked (HTTP 403) -> no records; WDP-ARGAN merger (announced 23 Jul 2026, completion expected Q1 2027) noted.
Rules: only records with a documented development plan or completion (owner rule) - none qualify by photo yet.
No ERV, rents, yields, market values or returns are carried. Published development cost (TDC / budget) is carried as a
company-published investment figure. Listings are "verified" only where a company document states the ticker
(Montea: "Euronext Brussels (MONT)"; British Land: share-price tool code UK-BLND on its own site). Landsec and SEGRO
tickers were not found in the fetched documents -> research_only access until checked.
Locations: Wikidata (CC0) building item -> building_point (exact); Wikidata district item -> approximate district point;
otherwise Wikidata city point (approximate). No address geocoding outside the US/Japan in this pilot.
Usage: build_intl_eu.py <scratch intl dir>
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research/data-centers/phase4'))
from sector_adapter import SCHEMA, validate, digest  # noqa: E402
EV = Path(sys.argv[1]); OUT = ROOT / 'data/realestate/intl'; OUT.mkdir(parents=True, exist_ok=True)
W = json.loads((EV / 'eu/wikidata-points.json').read_text(encoding='utf-8'))
T = '2026-11-14T06:00:00Z'
S = {
 'bl': {'url': 'https://www.britishland.com/media/5vqpkh3q/fy26-press-release-vfinal.pdf', 'sha256': 'bff158b356c3841ece48f930199f41a6328a9eddb87ea74e787d9681255ef8d2', 'checked_at': T, 'name': 'British Land FY26 results (31 Mar 2026)'},
 'bl_share': {'url': 'https://www.britishland.com/investors/shareholder-information/share-price-tools/', 'sha256': '1d67753cecde56f3323deb79125b6372273f15f95e1d0e854ca1bb2042b9ac15', 'checked_at': T, 'name': 'British Land share price tools page'},
 'ls': {'url': 'https://content.landsec.com/media/w4xfozna/results-for-the-year-ended-31-march-2026-announcement.pdf', 'sha256': 'cc3e555c6255666aff5cd8ba8629ee708ef47b763194ab2d4867a73ec2239278', 'checked_at': T, 'name': 'Landsec FY26 results (31 Mar 2026)'},
 'sg': {'url': 'https://www.segro.com/media/xlibxjqh/press-release-full-version-final.pdf', 'sha256': '485dca20de026388b38483f5b4c96743c8676a92acc76d056ba488eadf16abaf', 'checked_at': T, 'name': 'SEGRO H1 2026 results'},
 'mt': {'url': 'https://cdn.craft.cloud/4a7b09b1-5035-4e87-85b5-d0881d103040/assets/documents/20261029Press-Release-EN.pdf', 'sha256': '93e323a1c9460878a733e972d6766463e027749e50099ae2bc4ca1c3a60aa1df', 'checked_at': T, 'name': 'Montea interim release Q3 2026 (29 Oct 2026)'},
}
def ev(k, loc, **kw): s = S[k]; return {'url': s['url'], 'sha256': s['sha256'], 'checked_at': s['checked_at'], 'locator': loc, 'sha256_scope': 'source_body', **kw}
COS = {
 'registry:lse:BLND': {'name': 'The British Land Company PLC', 'ticker': 'BLND', 'exchange': 'XLON', 'verified': True, 'ev': ('bl_share', 'Company share-price tool embeds company code UK-BLND (London Stock Exchange)')},
 'registry:lse:LAND': {'name': 'Land Securities Group PLC', 'ticker': None, 'exchange': 'XLON', 'verified': False, 'ev': ('ls', 'Results announcement names LAND SECURITIES GROUP PLC; ticker not stated in fetched documents')},
 'registry:lse:SGRO': {'name': 'SEGRO plc', 'ticker': None, 'exchange': 'XLON', 'verified': False, 'ev': ('sg', 'Results state listing on the London Stock Exchange and Euronext Paris; ticker not stated')},
 'registry:euronext:MONT': {'name': 'Montea NV', 'ticker': 'MONT', 'exchange': 'XBRU', 'verified': True, 'ev': ('mt', 'About Montea: listed on Euronext Brussels (MONT) and Euronext Paris (MONTP)')},
}
def pt(s): m = re.match(r'Point\(([-\d.e]+) ([-\d.e]+)\)', s); return float(m.group(2)), float(m.group(1))
def city(name):
    for q, (lab, c) in W['cities'].items():
        if lab == name: return q, pt(c)
    hits = W.get('cities2', {}).get(name, {})
    if len(hits) == 1: q, c = next(iter(hits.items())); return q, pt(c)
    return None, None
def wd_ev(q, rid, scope, label): return {'url': f'https://www.wikidata.org/wiki/{q}', 'sha256': digest({'qid': q, 'label': label}), 'checked_at': T, 'locator': f'Wikidata {q} P625 ({label})', 'sha256_scope': 'query_result_row', 'record_id': rid, 'scope': scope}
# (company_ref, slug, name, cc, city, subtype, stage, status label, as_of, stake, figure, source key, locator, building/district wikidata label)
P = [
 ('registry:lse:BLND', '2-finsbury-avenue', '2 Finsbury Avenue', 'GB', 'London', 'Office development', 'under_construction', 'Committed development; practical completion targeted Q2 2027 (company target)', '2026-03-31', 25, None, 'bl', 'Committed Developments table: 2 Finsbury Avenue | Office | BL share 25% | PC Q2 2027', None),
 ('registry:lse:BLND', 'broadgate-tower', 'Broadgate Tower (refurbishment)', 'GB', 'London', 'Office redevelopment', 'under_construction', 'Major refurbishment; completion targeted Q1 2027 (company target)', '2026-03-31', 50, None, 'bl', 'Committed Developments table: Broadgate Tower | Office | BL share 50% | PC Q1 2027; text: major refurbishment rather than a new build', 'Broadgate Tower'),
 ('registry:lse:BLND', '1-appold-street', '1 Appold Street', 'GB', 'London', 'Office development', 'under_construction', 'Committed development; construction well underway, completion targeted Q1 2029 (company target)', '2026-03-31', 50, None, 'bl', 'Committed Developments table: 1 Appold Street | Office | BL share 50% | PC Q1 2029', None),
 ('registry:lse:BLND', 'west-one', 'West One (Oxford Street)', 'GB', 'London', 'Mixed-use development', 'under_construction', 'Committed March 2026 with Norges; completion targeted Q1 2029 (company target)', '2026-03-31', 25, None, 'bl', 'Committed Developments table: West One | Office | BL share 25% | PC Q1 2029; text: above Bond Street station on Oxford Street', None),
 ('registry:lse:BLND', 'the-founding-canada-water', 'The Founding, Canada Water', 'GB', 'London', 'Residential development', 'completed', 'Completed Q1 2026 (Canada Water Masterplan Phase 1)', '2026-03-31', None, None, 'bl', 'Text: final buildings of Phase 1 of the Canada Water Masterplan completed in Q1 2026 - The Founding (35-storey, 186 apartments)', 'Canada Water'),
 ('registry:lse:BLND', 'three-deal-porters-canada-water', 'Three Deal Porters, Canada Water', 'GB', 'London', 'Mixed-use development', 'completed', 'Completed Q1 2026 (Canada Water Masterplan Phase 1)', '2026-03-31', None, None, 'bl', 'Text: Phase 1 completed in Q1 2026 - Three Deal Porters (ground-floor retail and five floors of workspace)', 'Canada Water'),
 ('registry:lse:BLND', 'euston-tower', 'Euston Tower', 'GB', 'London', 'Office redevelopment', 'planning', 'Planning consent for a 568,000 sq ft office and innovation tower (medium-term pipeline; not committed)', '2026-03-31', None, None, 'bl', 'Medium Term Pipeline text: Euston Tower, planning consent for a 568,000 sq ft office and innovation tower', 'Euston Tower'),
 ('registry:lse:LAND', 'thirty-high-sw1', 'Thirty High, SW1', 'GB', 'London', 'Office development', 'under_construction', 'Committed pipeline; estimated completion Q2 FY27 (company estimate)', '2026-03-31', None, ('Total development cost (company-published)', 'GBP 446 million'), 'ls', 'Table 4 Committed pipeline: Thirty High, SW1 | Office | Q2 FY27 | TDC £446m', None),
 ('registry:lse:LAND', 'republic-manchester', 'Republic, Mayfield, Manchester', 'GB', 'Manchester', 'Office development', 'under_construction', 'Committed pipeline; estimated completion Q4 FY28 (company estimate)', '2026-03-31', None, ('Total development cost (company-published)', 'GBP 154 million'), 'ls', 'Table 4 Committed pipeline: Republic, Manchester | Office | Q4 FY28 | TDC £154m; text: £154m development at Mayfield, Manchester', None),
 ('registry:lse:LAND', 'timber-square-se1', 'Timber Square, SE1', 'GB', 'London', 'Office development', 'completed', 'Completed during FY26 (company-reported)', '2026-03-31', None, None, 'ls', 'Text: following the completion of Timber Square, committed development exposure down from £1.1bn to £0.6bn', None),
 ('registry:lse:LAND', 'bluewater-next', 'Bluewater: former House of Fraser repositioning for Next', 'GB', 'Greenhithe', 'Retail redevelopment', 'under_construction', 'On site: repositioning of the former House of Fraser store for a new 133,000 sq ft Next store', '2026-03-31', None, None, 'ls', 'Text: on site with smaller retail projects including the repositioning of the former House of Fraser department store at Bluewater for a new 133,000 sq ft Next store', None),
 ('registry:lse:LAND', 'white-rose-primark-extension', 'White Rose, Leeds: Primark extension', 'GB', 'Leeds', 'Retail redevelopment', 'under_construction', "On site: extension of Primark's store at White Rose to double its footprint", '2026-03-31', None, None, 'ls', "Text: the extension of Primark's store at White Rose, Leeds to double its footprint", None),
 ('registry:lse:LAND', 'trinity-leeds-dining', 'Trinity Leeds: social eating destination', 'GB', 'Leeds', 'Retail redevelopment', 'under_construction', 'On site: creation of a new social eating destination', '2026-03-31', None, None, 'ls', 'Text: the creation of a new social eating destination at Trinity, Leeds', 'Trinity Leeds'),
 *[('registry:lse:LAND', s, n, 'GB', c, sub, 'planning', f'Pre-development asset; planning status: {st}', '2026-03-31', None, None, 'ls', f'Table 5 Pre-development assets: {n} | {st}', None) for s, n, c, sub, st in [
   ('old-broad-street-ec2', 'Old Broad Street, EC2', 'London', 'Office development', 'Consented'), ('liberty-of-southwark-se1', 'Liberty of Southwark, SE1', 'London', 'Office development', 'Consented'),
   ('hill-house-ec4', 'Hill House, EC4', 'London', 'Office development', 'Consented'), ('nova-place-sw1', 'Nova Place, SW1', 'London', 'Office development', 'Consented'),
   ('timber-square-phase-2-se1', 'Timber Square Phase 2, SE1', 'London', 'Office development', 'Consented'), ('mayfield-manchester-residential', 'Mayfield, Manchester (residential-led)', 'Manchester', 'Residential development', 'Consented; potential start 2027'),
   ('finchley-road-nw3', 'Finchley Road, NW3', 'London', 'Residential development', 'Consented; potential start 2027'), ('lewisham-se13', 'Lewisham, SE13', 'London', 'Residential development', 'Consented; potential start 2028'),
   ('mediacity-phase-2-salford', 'MediaCity Phase 2, Salford', 'Salford', 'Residential development', 'Design')]],
 ('registry:lse:SGRO', 'segro-park-coventry-prelet', 'SEGRO Park Coventry (pre-let warehouses)', 'GB', 'Coventry', 'Logistics development', 'planning', 'Agreements signed in H1 2026 to develop logistics warehouses (pre-let)', '2026-06-30', None, None, 'sg', 'Text: we also signed agreements to develop logistics warehouses at SEGRO Park Coventry', None),
 ('registry:lse:SGRO', 'segro-park-dortmund-prelet', 'SEGRO Park Dortmund (pre-let warehouses)', 'DE', 'Dortmund', 'Logistics development', 'planning', 'Agreements signed in H1 2026 to develop logistics warehouses (pre-let)', '2026-06-30', None, None, 'sg', 'Text: agreements to develop logistics warehouses at SEGRO Park Coventry and at SEGRO Park Dortmund', None),
 ('registry:lse:SGRO', 'smartparc-segro-derby-unit', 'SmartParc SEGRO Derby (food campus unit)', 'GB', 'Derby', 'Logistics development', 'completed', 'Unit completed in H1 2026 (company-reported)', '2026-06-30', None, None, 'sg', 'Text: completed big box developments during the period, including a unit on our food campus, SmartParc SEGRO Derby', None),
 ('registry:lse:SGRO', 'segro-park-amsterdam-airport-spec', 'SEGRO Park Amsterdam Airport (speculative unit)', 'NL', 'Amsterdam', 'Logistics development', 'completed', 'Small speculative development completed in H1 2026 (company-reported)', '2026-06-30', None, None, 'sg', 'Text: and a small speculative development in SEGRO Park Amsterdam Airport', None),
 ('registry:euronext:MONT', 'halle-noorderstraat-solucious', 'Halle, Noorderstraat (Solucious distribution centre)', 'BE', 'Halle', 'Logistics development', 'under_construction', 'Construction started Q4 2025; completion expected Q4 2026 (company)', '2026-09-30', None, ('Estimated investment budget, plot + development (company)', 'c. EUR 34 million'), 'mt', 'Brand new logistics center in Halle (BE): Noorderstraat; start Q4 2025; expected completion Q4 2026; budget ca. €34 million', None),
 ('registry:euronext:MONT', 'tiel-glassworks-arjo', 'Logistic Park Glassworks, Tiel (Arjo)', 'NL', 'Tiel', 'Logistics development', 'under_construction', 'Construction started Q2 2026; completion expected Q1 2027 (company)', '2026-09-30', None, ('Estimated investment budget, plot + development (company)', 'c. EUR 6 million'), 'mt', 'Tiel: 4,000 m² distribution center for Arjo AB; start Q2 2026; expected completion Q1 2027; budget ca. €6 million', None),
 ('registry:euronext:MONT', 'tiel-glassworks-dc-quartz', 'DC Quartz, Logistic Park Glassworks, Tiel', 'NL', 'Tiel', 'Logistics development', 'under_construction', 'Construction started Q3 2026; completion expected Q4 2027 (company)', '2026-09-30', None, ('Estimated investment budget, plot + development (company)', 'c. EUR 69 million'), 'mt', 'DC Quartz: 67,400 m², 70% pre-let to BSH Home Appliances; start Q3 2026; expected completion Q4 2027; budget ca. €69 million', None),
 ('registry:euronext:MONT', 'liege-skechers', 'Skechers European distribution centre, Liège', 'BE', 'Liège', 'Logistics development', 'under_construction', 'Joint development with Weerts Group; rent commencement expected end 2027 (company)', '2026-09-30', 40, ('Montea maximum project exposure (company)', 'EUR 167 million'), 'mt', 'Skechers, Liège: Montea holds a 40% stake in the project company (increase to 49% announced 29 Oct 2026); 230,000 m²; total project capex = maximum exposure €167 million', None),
]
records, notes = [], []
for ref, slug, name, cc, cty, sub, stage, label, as_of, stake, fig, sk, locator, wdl in P:
    co = COS[ref]; rid = f"re:{ref.split(':')[-1].lower()}:{slug}"; e0 = ev(sk, locator)
    b = (W['buildings'].get(wdl) or [None])[0] if wdl else None
    if b and wdl in ('Broadgate Tower', 'Euston Tower', 'Trinity Leeds'):
        la, lo = pt(b['c']); loc = {'precision': 'exact', 'point_type': 'building_point', 'confidence': 'medium', 'lat': la, 'lon': lo, 'label': f'{wdl} (building point)', 'basis': f"Wikidata {b['qid']} coordinate (CC0) for the named building; not cross-checked against a company pin", 'satellite_allowed': False, 'evidence': wd_ev(b['qid'], rid, 'specific_site', wdl)}
    elif b:
        la, lo = pt(b['c']); loc = {'precision': 'approximate', 'point_type': 'district_reference', 'lat': la, 'lon': lo, 'label': f'{wdl} (district point, not the building)', 'basis': f"Wikidata {b['qid']} (CC0) district coordinate", 'satellite_allowed': False, 'evidence': wd_ev(b['qid'], rid, 'district_reference', wdl)}
    else:
        q, c = city(cty)
        loc = {'precision': 'approximate', 'point_type': 'city_reference', 'lat': c[0], 'lon': c[1], 'label': f'{cty} (city reference point, not the building)', 'basis': f'Wikidata {q} city coordinate (CC0)', 'satellite_allowed': False, 'evidence': wd_ev(q, rid, 'city_reference', cty)} if q else {'precision': 'unknown', 'lat': None, 'lon': None, 'label': f'{cty}; no verified point', 'satellite_allowed': False}
    listing = {'name': co['name'], 'ticker': co['ticker'], 'exchange': co['exchange'], 'exchange_mic': co['exchange'], 'security_type': 'common_equity' if ref != 'registry:euronext:MONT' else 'reit_shares', 'evidence': ev(*co['ev'])}
    role = 'developer'
    exp = {'role': role, 'label': 'Company-reported developer' + (' (joint venture)' if stake else ''), 'relationship_scope': f'Named project in the company results' + (f'; company-stated share {stake}%' if stake else '; share not stated') + '; title not checked',
           'property_stake': stake, 'company_ref': ref, 'listing': listing, 'headquarters': None, 'evidence': e0,
           'investment_access': {'type': 'listed_REIT', 'verified': True, 'scope': 'Indirect listed-company equity exposure only; buying shares gives no title to this property'} if co['verified'] else {'type': 'research_only', 'verified': False, 'scope': 'Ticker not yet documented from a company source; no title to this property'}}
    if stake: exp.update(stake_scope='specific_property', property_evidence={**e0, 'record_id': rid, 'scope': 'specific_property'})
    r = {'schema': SCHEMA, 'id': rid, 'source_identity': {'authority': f"company-results:{ref.split(':')[-1]}", 'id': slug}, 'synthetic': False, 'name': name, 'sector': 'real_estate', 'country_code': cc, 'city': cty,
         'asset': {'category': 'project', 'subtype': sub, 'parent_id': None, 'count_as_project': True}, 'status': {'stage': stage, 'label': label, 'as_of': as_of, 'certainty': 'company_reported', 'evidence': e0},
         'location': loc, 'identity_evidence': e0, 'exposures': [exp], 'imagery': [], 'verification': {'classification': 'company_confirmed', 'date': '2026-11-14', 'property_title_verified': False},
         'reuse': {'fields': {'identity': {'status': 'pending', 'basis': 'Company results document; corporate website terms not reviewed'}, 'status': {'status': 'pending', 'basis': 'same'}, 'economic_relationship': {'status': 'pending', 'basis': 'same'},
                              'listing': {'status': 'pending' if not co['verified'] else 'pending', 'basis': 'company page; exchange data source not yet cross-checked'}, 'location': {'status': 'cleared' if loc['precision'] != 'unknown' else 'omit', 'basis': 'Wikidata (CC0)'}}, 'review': {}},
         'preview_only': True}
    if fig: r['reported_metrics'] = {'label': fig[0], 'value': fig[1], 'basis': 'company-published investment figure (not a valuation)'}; r['reuse']['fields']['reported_metrics'] = {'status': 'pending', 'basis': 'company figure'}
    r['monitoring'] = {'stable_id': rid, 'evidence_refs': [{'url': e0['url'], 'sha256': e0['sha256']}], 'last_verified_at': T, 'enabled': False, 'fact_fingerprint': digest({k: v for k, v in r.items() if k not in ('reuse', 'monitoring')})}
    validate(r); records.append(r)
links = {'re:mont:tiel-glassworks-dc-quartz': "Codex pilot record for DC Quartz (phase4/real-estate-pilot.json) - same building; Codex record unchanged, this one adds the Q3 2026 construction start"}
for k, v in links.items(): next(r for r in records if r['id'] == k).setdefault('identity', {})['related_records'] = [v]
companies = {ref: {'identity': {'scheme': 'registry', 'value': ref.split(':', 1)[1], 'evidence': ev(*c['ev'])}, 'listing': {'name': c['name'], 'ticker': c['ticker'], 'exchange': c['exchange'], 'exchange_mic': c['exchange'], 'security_type': 'common_equity' if ref != 'registry:euronext:MONT' else 'reit_shares', 'evidence': ev(*c['ev'])}, 'headquarters': None} for ref, c in COS.items()}
env = {'schema': 'investedia.projects.import.v1', 'synthetic': False, 'companies': companies, 'records': records}
(OUT / 'import-eu-pilot.json').write_text(json.dumps(env, indent=1, ensure_ascii=False))
audit = {'as_of': '2026-11-14', 'sources': {k: {kk: v[kk] for kk in ('name', 'url', 'sha256')} for k, v in S.items()},
         'blocked': {'WDP': 'Q3 2026 results PDF returns HTTP 403 to scripted download (page text readable: WDP-ARGAN all-share merger announced 23 Jul 2026, EGMs 20/24 Nov 2026, completion expected Q1 2027)',
                     'SEGRO property-level': 'H1 2026 Property Analysis Report gives regional development totals only; named projects come from narrative text, without addresses',
                     'Landsec/SEGRO tickers': 'not stated in fetched company documents; access left research_only'},
         'excluded_figures': 'ERV, rents, yields on cost, market values and occupancy present in the sources were deliberately not carried'}
(OUT / 'eu-source-audit.json').write_text(json.dumps(audit, indent=1, ensure_ascii=False))
from collections import Counter
print(json.dumps({'records': len(records), 'by_company': Counter(r['id'].split(':')[1] for r in records), 'by_country': Counter(r['country_code'] for r in records), 'stage': Counter(r['status']['stage'] for r in records),
                  'location': Counter(r['location'].get('point_type') or r['location']['precision'] for r in records), 'verified_listing': sum(r['exposures'][0]['investment_access']['verified'] for r in records), 'stated_stakes': sum(r['exposures'][0]['property_stake'] is not None for r in records)}, indent=1))
