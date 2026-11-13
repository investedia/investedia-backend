#!/usr/bin/env python3
"""NEXTDC development/expansion projects from the FY26 Annual Report & Appendix 4E (ASX filing, 27 Aug 2026).
Facts only (stage words, MW figures, approvals), re-expressed; city references from Wikidata (CC0).
Reuse: ASX filing facts are analogous to the owner-approved SEC scope but NOT yet approved -> 'pending' (owner decision).
Also records the filing statement that verifies NEXTDC as operator of its directory facilities (R-NXT-OP).
Output: data/datacentres/v2/nextdc-filing-developments.json (import format) + gate simulation."""
import copy, hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; EV = Path(sys.argv[1]); TODAY = '2026-11-13'
sys.path.insert(0, str(ROOT / 'research/data-centers/phase4')); import sector_adapter as SA
CITY = json.loads((EV / 'wd/city-refs.json').read_text()); REG = json.loads((EV / 'reg/registry.json').read_text())
PDF = EV / 'filings/nxt-ar.pdf'; SHA = hashlib.sha256(PDF.read_bytes()).hexdigest()
URL = 'https://announcements.asx.com.au/asxpdf/20260827/pdf/073c027z036kht.pdf'
ISO = {'Melbourne': 'AU', 'Sydney': 'AU', 'Geelong': 'AU', 'Darwin': 'AU', 'Sunshine Coast': 'AU', 'Perth': 'AU', 'Brisbane': 'AU', 'Kuala Lumpur': 'MY', 'Tokyo': 'JP', 'Auckland': 'NZ'}
# (code, scope slug, name, city, stage, label, metrics, locator)
ROWS = [
 ('M4', 'campus', 'NEXTDC M4 Melbourne', 'Melbourne', 'planning', 'Victorian Government development approval (January 2026) for a technology campus at Fishermans Bend, Port Melbourne', {'planned_capacity': {'value': 162, 'unit': 'MW', 'basis': 'campus, per annual report'}}, "Operating review: 'In January 2026, we secured Victorian Government development approval for M4 Melbourne, a 162MW technology campus at Fishermans Bend'"),
 ('KL1', 'expansion', 'NEXTDC KL1 Kuala Lumpur', 'Kuala Lumpur', 'expanding', 'Opened May 2026 with 10MW; further 15MW in progress and 15MW in plan', {'opened_capacity': {'value': 10, 'unit': 'MW'}, 'in_progress_capacity': {'value': 15, 'unit': 'MW'}, 'planned_capacity': {'value': 15, 'unit': 'MW'}}, "International segment: 'KL1 Kuala Lumpur opened with 10MW of capacity, 15MW in progress and 15MW in plan'"),
 ('TK1', 'site', 'NEXTDC TK1 Tokyo', 'Tokyo', 'under_construction', 'Preliminary site works underway (first NEXTDC facility in Japan)', {}, "Operating review: 'preliminary site works commenced at TK1 Tokyo, our first Japanese facility'"),
 ('AK1', 'site', 'NEXTDC AK1 Auckland', 'Auckland', 'planning', 'Resource consent application lodged with Auckland Council', {}, "International segment: 'a resource consent application lodged with Auckland Council for AK1 Auckland'"),
 ('S4', 'site', 'NEXTDC S4 Sydney', 'Sydney', 'under_construction', 'Construction continued during FY26', {}, "Operating review: 'continued construction at S4 Sydney, GE1 Geelong, D2 Darwin and SC2 Sunshine Coast'"),
 ('S7', 'site', 'NEXTDC S7 Sydney', 'Sydney', 'planning', 'Project under development (construction start not stated)', {}, "Sustainability: 'Projects under development including S4, S7 and M4'"),
 ('GE1', 'site', 'NEXTDC GE1 Geelong', 'Geelong', 'under_construction', 'Construction continued during FY26 (edge facility)', {}, "Operating review: 'continued construction at S4 Sydney, GE1 Geelong, D2 Darwin and SC2 Sunshine Coast'"),
 ('D2', 'site', 'NEXTDC D2 Darwin', 'Darwin', 'under_construction', 'Construction continued during FY26 (edge facility)', {}, "Operating review: 'continued construction at S4 Sydney, GE1 Geelong, D2 Darwin and SC2 Sunshine Coast'"),
 ('SC2', 'site', 'NEXTDC SC2 Sunshine Coast', 'Sunshine Coast', 'under_construction', 'Construction continued during FY26 (edge facility)', {}, "Operating review: 'continued construction at S4 Sydney, GE1 Geelong, D2 Darwin and SC2 Sunshine Coast'"),
 ('P1', 'extension', 'NEXTDC P1 Perth extension', 'Perth', 'expanding', 'Extension build commenced, adding 2MW', {'added_capacity': {'value': 2, 'unit': 'MW'}}, "Operating review: 'commenced builds to extend our existing P1 Perth and B2 Brisbane data centres, adding 2MW of additional capacity at each site'"),
 ('B2', 'extension', 'NEXTDC B2 Brisbane extension', 'Brisbane', 'expanding', 'Extension build commenced, adding 2MW', {'added_capacity': {'value': 2, 'unit': 'MW'}}, "Operating review: 'commenced builds to extend our existing P1 Perth and B2 Brisbane data centres, adding 2MW of additional capacity at each site'"),
]
nx = REG['lei:529900RTERU3X7G3D672']; recs = []
for code, scope, name, city, stage, label, metrics, loc in ROWS:
    rid = f'project:nextdc:{code}:{scope}'
    ev = {'url': URL, 'sha256': SHA, 'checked_at': TODAY, 'locator': f'NEXTDC FY26 Annual Report & Appendix 4E (ASX, 27 Aug 2026): {loc}', 'sha256_scope': 'source_body'}
    c = CITY.get(city)
    location = ({'precision': 'approximate', 'lat': c['lat'], 'lon': c['lon'], 'label': f'{city} reference', 'basis': f"Wikidata (CC0) city reference {c['qid']} ({c['label']}); not the facility site",
                 'satellite_allowed': False, 'evidence': {'url': c['source_url'], 'sha256': c['sha256'], 'checked_at': TODAY, 'locator': 'Wikidata P625 city coordinates', 'sha256_scope': 'source_body', 'record_id': rid, 'scope': 'source_reference'}}
                if c else {'precision': 'unknown', 'lat': None, 'lon': None, 'satellite_allowed': False})
    rec = {'schema': SA.SCHEMA, 'id': rid, 'source_identity': {'authority': 'asx:nxt:annual-report-fy26', 'id': f'{code}:{scope}'}, 'synthetic': False,
           'name': name, 'sector': 'data_centers', 'country_code': ISO[city], 'city': city,
           'asset': {'category': 'project', 'subtype': 'Data center ' + {'campus': 'campus', 'expansion': 'expansion', 'site': 'development', 'extension': 'extension'}[scope], 'parent_id': None, 'count_as_project': True},
           'status': {'stage': stage, 'label': label, 'as_of': '2026-08-27', 'certainty': 'company_reported', 'evidence': {k: ev[k] for k in ('url', 'sha256', 'checked_at', 'locator')}},
           'location': location, 'identity_evidence': {k: ev[k] for k in ('url', 'sha256', 'checked_at', 'locator')}, 'imagery': [],
           'exposures': [{'role': 'developer', 'label': 'Company development project (issuer annual report)', 'relationship_scope': 'NEXTDC project per FY26 annual report; property title/lease for the site not established',
                          'maturity': 'reported', 'property_stake': None, 'company_ref': 'lei:529900RTERU3X7G3D672', 'listing': copy.deepcopy(nx['listing']), 'evidence': ev,
                          'investment_access': {'type': 'public_equity', 'verified': True, 'scope': 'Indirect listed-company equity exposure (ASX: NXT); no direct property purchase'}}],
           'verification': {'classification': 'company_confirmed', 'date': TODAY, 'property_title_verified': False, 'rule': 'R-NXT-DEV (ASX annual report)'},
           'reported_metrics': metrics or {'capacity': None},
           'reuse': {'fields': {k: {'status': 'pending', 'basis': 'Facts from ASX annual report; owner approval so far covers SEC facts - ASX filing scope awaiting owner confirmation'} for k in ('identity', 'status', 'economic_relationship', 'reported_metrics')}, 'review': None},
           'preview_only': True, 'notes': [] if c else [{'field': 'location', 'disposition': 'No verified Wikidata reference resolved for this city yet; no marker'}]}
    rec['reuse']['fields']['listing'] = {'status': 'cleared', 'basis': 'ASX listing identifiers; credited'}
    rec['reuse']['fields']['location'] = {'status': 'cleared', 'basis': 'Wikidata CC0 city reference; credited'} if c else {'status': 'omit', 'basis': 'No point'}
    SA.validate(rec); recs.append(rec)
out = ROOT / 'data/datacentres/v2/nextdc-filing-developments.json'
out.write_text(json.dumps({'schema': 'investedia.projects.import.v1', 'synthetic': False, 'companies': {'lei:529900RTERU3X7G3D672': nx}, 'records': recs,
                           'operator_rule': {'id': 'R-NXT-OP', 'evidence': {'url': URL, 'sha256': SHA, 'locator': "Operating review: 'Today NEXTDC manages 18 fully operational, highly certified data centres'"}}}, ensure_ascii=False, indent=1), encoding='utf-8')
# gate simulation: if the owner confirms ASX scope (fields cleared) and signs
ok = 0; why = {}
for r in recs:
    t = copy.deepcopy(r)
    for k in t['reuse']['fields']:
        if t['reuse']['fields'][k]['status'] == 'pending': t['reuse']['fields'][k] = {'status': 'cleared', 'basis': 'simulation: owner confirms ASX filing scope'}
    f = copy.deepcopy(t); f.pop('reuse'); t['reuse']['review'] = {'fact_sha256': SA.digest(f), 'reviewer': 'simulation', 'date': TODAY, 'basis': 'simulation'}
    try: SA.public_projection(t); ok += 1
    except Exception as e: why[str(e)] = why.get(str(e), 0) + 1
print(json.dumps({'records': len(recs), 'countries': sorted({r['country_code'] for r in recs}), 'pass_after_owner_asx_ok_and_signature': ok, 'blocked': why, 'sha256_pdf': SHA}, indent=1))
