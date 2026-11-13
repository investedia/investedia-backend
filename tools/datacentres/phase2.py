#!/usr/bin/env python3
"""Data Centres Phase 2: portfolio verification rules, audit corrections, filing-based developments and release tiers.

Input : data/datacentres/import/claude-dc-batch-1.json (602 records, Codex import format), candidates.json, staged matches,
        filing extracts (FY2025 10-Ks) and Wikidata city references prepared in the scratch evidence folder.
Output: data/datacentres/v2/  (import-format files per tier + AUDIT.json + MANIFEST.json)

Portfolio rules (one documented filing statement + the issuer's own facility page; never ownership):
  R-EQIX-OP  Equinix FY2025 10-K Item 2 'overview of our portfolio of IBX data centers' (255 consolidated + 25 unconsolidated,
             incl. 23 xScale). Facility page on equinix.com -> role operator. 'x' suffix = xScale joint venture (unconsolidated).
  R-DLR-OP   Digital Realty FY2025 10-K: 'We own and operate our data centers'; for unconsolidated JVs 'Generally, we serve as the
             managing member responsible for operations'. Facility page on digitalrealty.com -> role operator. Per-site
             consolidated/JV/lease status not established; JV percentages are business-level, never property stakes.
  R-AMT-OP   American Tower FY2025 10-K: '30 operating data center facilities across eleven markets in the United States'
             (CoreSite subsidiary). Facility page on coresite.com -> role operator.
  NEXTDC     No filing statement obtained in this pass -> stays directory affiliation (research_only).
  CyrusOne   Fund-manager exposure (KKR, BlackRock/GIP) -> research_only; owner decision pending.

Release tiers (no self-declared eligibility; the adapter's public_projection is the gate):
  public_candidates      every factual field from owner-approved sources (SEC filings, Wikidata CC0) -> reuse fields 'cleared';
                         a fact digest is prepared; the owner's reviewer signature is the only missing step.
  licensing_unresolved   verified relationship, but identity/location come from operator websites whose terms restrict reuse.
  internal_research      relationship not verified (NEXTDC affiliation, CyrusOne fund-level, unknown status).
  rejected               audit failures (with reason).
"""
import copy, hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EV = Path(sys.argv[1])  # scratch evidence folder (filings/, wd/, terms/)
sys.path.insert(0, str(ROOT / 'research/data-centers/phase4')); import sector_adapter as SA  # Codex's adapter, unchanged
B1 = json.loads((ROOT / 'data/datacentres/import/claude-dc-batch-1.json').read_text(encoding='utf-8'))
CAND = {c['source_url']: c for c in json.loads((ROOT / 'data/datacentres/candidates.json').read_text(encoding='utf-8'))['records']}
STAGED = json.loads((ROOT / 'data/datacentres/import/staged-matches-to-codex-61.json').read_text(encoding='utf-8'))['matches']
CODEX = json.loads((ROOT / 'research/data-centers/phase2/phase2-dataset.json').read_text(encoding='utf-8'))
DEV = json.loads((EV / 'filings/eqix-dev.json').read_text(encoding='utf-8'))
CITY = json.loads((EV / 'wd/city-refs.json').read_text(encoding='utf-8'))
H = lambda p: hashlib.sha256((EV / p).read_bytes()).hexdigest()
OUT = ROOT / 'data/datacentres/v2'; TODAY = '2026-11-13'

FIL = {
 'eqix': {'url': 'https://www.sec.gov/Archives/edgar/data/1101239/000110123926000032/eqix-20251231.htm', 'sha256': H('filings/eqix-10k.htm'),
          'locator': "FY2025 10-K Item 2: 'overview of our portfolio of IBX data centers' - 255 consolidated IBXs plus 25 unconsolidated (23 xScale, MC1, SN1)"},
 'dlr': {'url': 'https://www.sec.gov/Archives/edgar/data/1297996/000110465926015365/dlr-20251231x10k.htm', 'sha256': H('filings/dlr-10k.htm'),
         'locator': "FY2025 10-K: 'We own and operate our data centers'; unconsolidated JVs: 'Generally, we serve as the managing member responsible for operations'"},
 'coresite': {'url': 'https://www.sec.gov/Archives/edgar/data/1053507/000105350726000035/amt-20251231.htm', 'sha256': H('filings/amt-10k.htm'),
              'locator': "FY2025 10-K: '30 operating data center facilities across eleven markets in the United States' (CoreSite)"},
}
EQIX_DEV_LOC = "FY2025 10-K Item 2: 'summary of our significant IBX data center projects under construction as of December 31, 2025'"
DLR_JV = {'JP': ('MC Digital Realty', 50), 'IN': ('Digital Connexion', 33), 'ID': ('Digital Realty Bersama', 50), 'IL': ('Mivne', 50), 'NG': ('Medallion', 60)}

def ev(fil, extra=None): d = {'url': fil['url'], 'sha256': fil['sha256'], 'checked_at': TODAY, 'locator': fil['locator'], 'sha256_scope': 'source_body'}; d.update(extra or {}); return d

audit = {'status_corrections': [], 'jv_notes': [], 'country_checks': [], 'duplicates': [], 'hq': [], 'location_basis': {}, 'staged_review': []}
tiers = {'public_candidates': [], 'licensing_unresolved': [], 'internal_research': [], 'rejected': []}

# ---------------------------------------------------------------- 1. audit + upgrade the 602 directory records
seen_code = {}
for r0 in B1['records']:
    r = copy.deepcopy(r0); op = r['id'].split(':')[1]; c = CAND.get(r['identity_evidence']['url'], {})
    code = (c.get('code') or r['name'].split()[-1]).upper()
    k = (op, code)
    if k in seen_code: audit['duplicates'].append({'id': r['id'], 'same_code_as': seen_code[k]}); tiers['rejected'].append({'id': r['id'], 'reason': 'duplicate facility code within operator'}); continue
    seen_code[k] = r['id']
    # status audit: directory keyword matches are only kept when they are facility-specific
    st = r['status']['stage']
    if st in ('planning', 'under_construction'):
        keep = op == 'nextdc' or (op == 'coresite' and code in ('DE3',))
        if not keep:
            audit['status_corrections'].append({'id': r['id'], 'from': st, 'to': 'unknown', 'reason': 'matched site-wide navigation / generic wording, not this facility' if op == 'cyrusone' else 'keyword not specific to this facility (e.g. "master-planned campus")'})
            r['status'] = {'stage': 'unknown', 'label': 'listed in operator directory; development stage not established', 'as_of': r['status']['as_of'], 'certainty': 'unverified'}
    # asset type: operating directory facilities are existing assets (separate from development projects)
    if r['status']['stage'] in ('operating', 'unknown'):
        r['asset'] = {'category': 'existing_asset', 'subtype': 'Data center facility', 'parent_id': None, 'count_as_project': False,
                      'building_identity_evidence': r['asset'].get('building_identity_evidence')}
    else:
        r['asset']['category'] = 'project'; r['asset']['count_as_project'] = True
    # location basis taxonomy (proximity alone never upgrades a point)
    loc = r['location']; b = loc.get('basis', '') or ''
    basis = ('official_site_pin_consistent_with_address' if loc['precision'] == 'exact' else
             'official_site_pin_campus_level_unresolved' if 'operator pin vs geocoded' in b else
             'geocoded_locality' if 'locality' in b else 'geocoded_published_address' if 'geocoded' in b else
             'withheld' if loc['precision'] == 'unknown' else 'other')
    loc['basis_type'] = basis; audit['location_basis'][basis] = audit['location_basis'].get(basis, 0) + 1
    # portfolio rules
    if op in FIL:
        scope = {'eqix': 'Equinix IBX data center (portfolio statement in FY2025 10-K); property title/lease per site not established',
                 'dlr': 'Digital Realty portfolio data center; consolidated vs JV vs lease for this site not established',
                 'coresite': 'CoreSite data center (American Tower subsidiary); property title per site not established'}[op]
        if op == 'eqix' and code.endswith('X'):
            scope = 'Equinix xScale data center: unconsolidated joint venture per FY2025 10-K; Equinix operator; property stake not established'
        if op == 'dlr' and r.get('country_code') in DLR_JV:
            jv, pct = DLR_JV[r['country_code']]
            scope += f'; country served by JV platform {jv} ({pct}% business-level interest per 10-K) - per-site holding not established'
            audit['jv_notes'].append({'id': r['id'], 'platform': jv, 'business_interest_pct': pct})
        old = r['exposures'][0]
        r['exposures'] = [{'role': 'operator', 'label': 'Operator exposure (issuer portfolio statement + issuer facility page)', 'relationship_scope': scope,
                           'maturity': 'reported', 'property_stake': None, 'company_ref': old['company_ref'], 'evidence': ev(FIL[op]),
                           'facility_evidence': old['evidence'],
                           'investment_access': {'type': 'listed_REIT', 'verified': True, 'scope': 'Indirect listed-company equity exposure; no direct property purchase'}}]
        r['verification'] = {'classification': 'company_confirmed', 'date': TODAY, 'property_title_verified': False, 'rule': {'eqix': 'R-EQIX-OP', 'dlr': 'R-DLR-OP', 'coresite': 'R-AMT-OP'}[op]}
        tier = 'licensing_unresolved'
    else:
        tier = 'internal_research'
    r['reuse']['fields']['identity']['basis'] = {'eqix': 'equinix.com Terms s.3: all content incl. "data" may not be copied/republished without written permission',
                                                'dlr': 'digitalrealty.com Terms: may not "copy, reproduce, modify, use, republish" material from the Web Site',
                                                'nextdc': 'nextdc.com Terms: may not "commercialise any information obtained from any part of this website"',
                                                'coresite': 'No website terms of use located (privacy policy only); copyright in page text/images remains; owner review needed',
                                                'cyrusone': 'Website terms not reviewed; fund-level exposure research only'}[op]
    tiers[tier].append(r)

# ---------------------------------------------------------------- 2. Equinix 10-K development table -> filing-based project records
codex_ids = {x['id'] for x in CODEX['original_records'] + CODEX['development_records']}
existing = {r['id']: r for t in ('licensing_unresolved', 'internal_research') for r in tiers[t]}
for code, phase, metro, target, cabinets, capex in DEV['rows']:
    pslug = re.sub(r'[^a-z0-9]+', '-', phase.lower()).strip('-')
    pid = f'project:eqix:{code}:{pslug}'
    if f'project:eqix:{code}' in codex_ids:
        audit['staged_review'].append({'filing_row': f'{code} {phase}', 'existing_codex_id': f'project:eqix:{code}', 'action': 'not imported: Codex reviewed record holds stronger, newer evidence; add filing row as supporting evidence on review'}); continue
    city = CITY[metro]
    parent = f'dc:eqix:{code}' if f'dc:eqix:{code}' in existing and existing[f'dc:eqix:{code}']['status']['stage'] in ('operating', 'unknown') else None
    fe = ev({'url': DEV['source'], 'sha256': DEV['sha256'], 'locator': f"{EQIX_DEV_LOC}: row '{code} {phase}, {metro}, target open {target}'"})
    rec = {'schema': SA.SCHEMA, 'id': pid, 'source_identity': {'authority': 'sec:eqix:10-K-2025:projects-under-construction', 'id': f'{code}:{pslug}'}, 'synthetic': False,
           'name': f'Equinix {code} {phase}', 'sector': 'data_centers', 'country_code': None, 'city': metro,
           'asset': {'category': 'project', 'subtype': 'Data center construction phase' if phase != 'redevelopment' else 'Data center redevelopment', 'parent_id': parent, 'count_as_project': True},
           'status': {'stage': 'under_construction', 'label': f'Under construction at 31 Dec 2025; target opening {target} (company target, not a completion)', 'as_of': '2025-12-31', 'certainty': 'company_reported',
                      'evidence': {k: fe[k] for k in ('url', 'sha256', 'checked_at', 'locator')}},
           'location': {'precision': 'approximate', 'lat': city['lat'], 'lon': city['lon'], 'label': f"{metro} metro reference", 'basis': f"Wikidata (CC0) city reference {city['qid']} ({city['label']}); not the facility site",
                        'basis_type': 'city_reference', 'satellite_allowed': False,
                        'evidence': {'url': city['source_url'], 'sha256': city['sha256'], 'checked_at': TODAY, 'locator': 'Wikidata P625 city coordinates', 'sha256_scope': 'source_body', 'record_id': pid, 'scope': 'source_reference'}},
           'identity_evidence': {k: fe[k] for k in ('url', 'sha256', 'checked_at', 'locator')}, 'imagery': [],
           'exposures': [{'role': 'developer', 'label': 'Company development project (issuer filing)', 'relationship_scope': 'Equinix project under construction per FY2025 10-K; property title/JV for the site not established',
                          'maturity': 'reported', 'property_stake': None, 'company_ref': 'cik:0001101239', 'evidence': fe,
                          'investment_access': {'type': 'listed_REIT', 'verified': True, 'scope': 'Indirect listed-company equity exposure; no direct property purchase'}}],
           'verification': {'classification': 'company_confirmed', 'date': TODAY, 'property_title_verified': False, 'rule': 'R-EQIX-DEV (SEC filing table)'},
           'reported_metrics': {'target_open': target, 'sellable_cabinets': int(cabinets.replace(',', '')), 'total_capex': {'value': int(capex.replace(',', '')), 'unit': 'USD million', 'basis': 'approximate per filing footnote (1)'}},
           'reuse': {'fields': {k: {'status': 'cleared', 'basis': 'Facts from SEC filing (owner-approved SEC scope); no prose copied; Equinix credited'} for k in ('identity', 'status', 'economic_relationship', 'listing', 'reported_metrics')}, 'review': None},
           'preview_only': True, 'notes': [{'field': 'country', 'disposition': 'Filing gives the metro only; country left null rather than inferred'}]}
    rec['reuse']['fields']['location'] = {'status': 'cleared', 'basis': 'Wikidata CC0 city reference; credited'}
    if target < 'Q4 2026' and target.split()[1] <= '2026':
        rec['notes'].append({'field': 'status', 'disposition': f'Target {target} may have elapsed; an elapsed target never proves completion. Stage stays as reported at 31 Dec 2025.'})
    for _e in rec['exposures']: _e['listing'] = copy.deepcopy(B1['companies'][_e['company_ref']]['listing'])  # inline, identical to registry
    fact = copy.deepcopy(rec); fact.pop('reuse', None)
    rec['reuse']['review'] = {'fact_sha256': SA.digest(fact), 'reviewer': None, 'date': None, 'basis': 'Prepared for owner sign-off: all fields from SEC filing / Wikidata CC0'}
    _t = copy.deepcopy(rec)
    for _e in _t['exposures']: _e['listing'] = B1['companies'][_e['company_ref']]['listing']
    SA.validate(_t)
    tiers['public_candidates'].append(rec)

# ---------------------------------------------------------------- 3. staged matches (33) - reviewed, never overwritten
for m in STAGED:
    audit['staged_review'].append({'existing_codex_ids': m['existing_ids'], 'new_source_identity': m['new_source_identity'], 'basis': m['match_basis'],
                                   'disposition': 'Kept Codex record; new directory evidence attached for field-by-field review'})

# ---------------------------------------------------------------- 4. write versioned outputs (import format) + public gate test
OUT.mkdir(parents=True, exist_ok=True)
companies = B1['companies']; manifest = {'version': 'v2', 'generated': TODAY, 'tiers': {}, 'gate': {}}
for name, recs in tiers.items():
    if name == 'rejected':
        (OUT / 'rejected.json').write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding='utf-8'); manifest['tiers'][name] = len(recs); continue
    body = {'schema': 'investedia.projects.import.v1', 'synthetic': False, 'companies': companies, 'records': recs}
    p = OUT / f'{name}.json'; p.write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding='utf-8')
    manifest['tiers'][name] = len(recs); manifest.setdefault('sha256', {})[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
# gate: would each public candidate pass public_projection once the owner signs?
signed = 0; blocked = {}
for r in tiers['public_candidates']:
    t = copy.deepcopy(r); t['reuse']['review'].update(reviewer='OWNER (simulation only)', date=TODAY)
    try: SA.public_projection(t); signed += 1
    except Exception as x: blocked[str(x)] = blocked.get(str(x), 0) + 1
manifest['gate'] = {'public_candidates_pass_after_owner_signature': signed, 'blocked': blocked, 'signed_now': 0}
(OUT / 'AUDIT.json').write_text(json.dumps(audit, ensure_ascii=False, indent=1), encoding='utf-8')
(OUT / 'MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps({'tiers': manifest['tiers'], 'gate': manifest['gate'], 'status_corrections': len(audit['status_corrections']), 'jv_notes': len(audit['jv_notes']),
                  'duplicates': len(audit['duplicates']), 'location_basis': audit['location_basis'], 'staged_review': len(audit['staged_review'])}, indent=1))
