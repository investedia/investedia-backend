#!/usr/bin/env python3
"""Release candidate v2: 29 Equinix (SEC 10-K) + 10 NEXTDC (ASX annual report) development projects; SC2 on hold.

Per record (Codex envelope, adapter unchanged) adds:
  states            evidence / source_licensing / publication_approval, kept separate
  capacity          operating_mw / in_progress_mw / planned_mw (never summed); Equinix: planned sellable cabinets (no MW in filing)
  presentation      one original sentence + cited facts (no filing table or marketing text reproduced)
  reuse_assessment  per field: basis, attribution, flag (none / attribution / legal_review / permission)
Location: 'exact' only where an OpenStreetMap object named for the facility identifies the site (site-identification.json);
otherwise the Wikidata city reference stays 'approximate'.
Equinix records are re-reviewed (fact digest changes); NEXTDC public use stays pending (internal research + verification only).
Outputs data/datacentres/release/v2/{public-candidates.json, hold.json, reuse-assessment.json, MANIFEST.json}"""
import copy, hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; TODAY = '2026-11-13'
sys.path.insert(0, str(ROOT / 'research/data-centers/phase4')); import sector_adapter as SA
D = ROOT / 'data/datacentres'
EQ = json.loads((D / 'release/v1/equinix-developments.json').read_text()); NX = json.loads((D / 'v2/nextdc-filing-developments.json').read_text())
SITES = json.loads((D / 'release/v1/site-identification.json').read_text())['records']
IMG = json.loads((D / 'release/v1/imagery-manifest.json').read_text())['images']
CIT = {'eqix10k': {'title': 'Equinix, Inc. Form 10-K for fiscal 2025, Item 2 (filed 11 Feb 2026)', 'url': EQ['records'][0]['identity_evidence']['url']},
       'nxtar': {'title': 'NEXTDC Limited FY26 Annual Report & Appendix 4E (ASX, 27 Aug 2026)', 'url': NX['records'][0]['identity_evidence']['url']},
       'wikidata': {'title': 'Wikidata (CC0) city reference'}, 'osm': {'title': 'OpenStreetMap (ODbL), named facility object'}}

def capacity(r):
    m = r.get('reported_metrics') or {}; v = lambda k: (m.get(k) or {}).get('value')
    if ':eqix:' in r['id']:
        return {'operating_mw': None, 'in_progress_mw': None, 'planned_mw': None, 'planned_sellable_cabinets': m.get('sellable_cabinets'),
                'note': 'Filing states sellable cabinets for this phase, not MW'}
    return {'operating_mw': v('opened_capacity'), 'in_progress_mw': v('in_progress_capacity') if 'in_progress_capacity' in m else v('added_capacity'),
            'planned_mw': v('planned_capacity'), 'note': 'Operating, in-progress and planned capacity are reported separately and never added together'}

def summary(r, cap):
    code = r['id'].split(':')[2]
    if ':eqix:' in r['id']:
        m = r['reported_metrics']; ph = r['name'].split(code, 1)[1].strip()
        return (f"Equinix is building {ph} of its {code} data center in {r['city']}. Its annual report for 2025 listed the project as under construction, "
                f"targeting opening in {m['target_open']}, with roughly US${m['total_capex']['value']} million of planned capital spending."), ['eqix10k']
    s = {'M4': 'NEXTDC received state development approval in January 2026 for its M4 campus at Fishermans Bend, Melbourne, planned at 162 MW.',
         'KL1': 'NEXTDC opened KL1 in Kuala Lumpur in May 2026 with 10 MW of capacity; a further 15 MW was under way and another 15 MW planned.',
         'TK1': 'NEXTDC has begun preliminary site works for TK1, its first data centre in Tokyo.',
         'AK1': 'NEXTDC has applied to Auckland Council for resource consent for its planned AK1 data centre.',
         'S4': 'NEXTDC continued building its S4 data centre in Sydney during the 2026 financial year.',
         'S7': 'NEXTDC lists S7 in Sydney among its projects under development; a construction start has not been reported.',
         'GE1': 'NEXTDC continued building its GE1 edge data centre in Geelong during the 2026 financial year.',
         'D2': 'NEXTDC continued building its D2 edge data centre in Darwin during the 2026 financial year.',
         'P1': 'NEXTDC began building an extension to its P1 data centre in Perth that adds 2 MW.',
         'B2': 'NEXTDC began building an extension to its B2 data centre in Brisbane that adds 2 MW.'}[code]
    return s, ['nxtar']

def reuse(r, exact):
    eq = ':eqix:' in r['id']
    src = ('Individual facts from an SEC filing, restated in original words with a citation; the filing table is not reproduced. Owner-approved SEC-fact scope.' if eq else
           'Individual facts from an ASX annual report, restated in original words with a citation. ASX publication does not by itself grant commercial redistribution rights.')
    f = {'identity': {'basis': src, 'attribution': CIT['eqix10k' if eq else 'nxtar']['title'], 'flag': 'none' if eq else 'legal_review'},
         'status_and_dates': {'basis': src, 'attribution': 'same', 'flag': 'none' if eq else 'legal_review'},
         'capacity_and_capex': {'basis': src, 'attribution': 'same', 'flag': 'none' if eq else 'legal_review'},
         'listing': {'basis': 'Exchange/SEC listing identifiers', 'attribution': 'SEC / ASX', 'flag': 'none'},
         'location': ({'basis': 'OpenStreetMap object named for the facility; single feature (insubstantial extract)', 'attribution': '© OpenStreetMap contributors, ODbL', 'flag': 'attribution'} if exact else
                      {'basis': 'Wikidata city reference', 'attribution': 'Wikidata (CC0)', 'flag': 'none'}),
         'aggregate': {'basis': 'Publishing all rows of one filing table as a dataset could be argued to reuse its selection/arrangement', 'attribution': '-', 'flag': 'legal_review' if eq else 'legal_review'}}
    return f

pub, hold, assess = [], [], {}
for r0 in EQ['records'] + NX['records']:
    r = copy.deepcopy(r0); code = r['id'].split(':')[2]
    if code == 'SC2':
        hold.append({'id': r['id'], 'reason': 'Site/city location not sufficiently verified (owner: keep on hold)', 'record': r}); continue
    site = (SITES.get(r['id']) or {}).get('site'); exact = bool(site)
    if exact:
        r['location'] = {'precision': 'exact', 'lat': site['lat'], 'lon': site['lon'], 'label': site['name'],
                         'basis': f"OpenStreetMap object named '{site['name']}' ({site['class']}); {('building' if site['class'].startswith('building') else 'campus/site')} level",
                         'satellite_allowed': True,
                         'evidence': {'url': site['source'], 'sha256': hashlib.sha256(json.dumps(site, sort_keys=True).encode()).hexdigest(), 'checked_at': TODAY,
                                      'locator': 'Nominatim search result (name match: operator + facility code)', 'sha256_scope': 'verified_input_snapshot',
                                      'snapshot_path': 'data/datacentres/release/v1/site-identification.json', 'record_id': r['id'], 'scope': 'specific_site'}}
    cap = capacity(r); text, cites = summary(r, cap)
    r['capacity'] = cap
    r['presentation'] = {'summary': text, 'citations': [CIT[c] for c in cites] + [CIT['osm' if exact else 'wikidata']], 'original_wording': True}
    eq = ':eqix:' in r['id']
    r['states'] = {'evidence': 'verified (issuer filing)', 'source_licensing': 'cleared: owner-approved SEC-fact scope' if eq else 'unresolved: ASX filing facts - internal research/verification only until permission or legal review',
                   'publication_approval': 'awaiting owner approval'}
    ra = reuse(r, exact); r['reuse_assessment'] = ra; assess[r['id']] = {'name': r['name'], **{k: v['flag'] for k, v in ra.items()}}
    img = IMG.get(r['id'], {})
    r['imagery_ref'] = {k: v for k, v in {'satellite_now': (img.get('images') or {}).get('now'), 'satellite_before': (img.get('images') or {}).get('before'), 'photo': img.get('photo')}.items() if v} or None
    # Codex reuse fields: NEXTDC stays pending; Equinix location basis updated
    if exact: r['reuse']['fields']['location'] = {'status': 'cleared', 'basis': 'OpenStreetMap (ODbL), single named feature, attribution shown'}
    if eq:
        fact = copy.deepcopy(r); fact.pop('reuse', None)
        r['reuse']['review'] = {'fact_sha256': SA.digest(fact), 'reviewer': 'Claude (research agent), delegated by owner instruction 2026-11-13; owner approval required to publish',
                                'date': TODAY, 'basis': 'v1 checks C1-C7 + OSM site identification (where present) + original presentation'}
    pub.append(r)
out = D / 'release/v2'; out.mkdir(parents=True, exist_ok=True)
companies = {**EQ['companies'], **NX['companies']}
(out / 'public-candidates.json').write_text(json.dumps({'schema': 'investedia.projects.import.v1', 'synthetic': False, 'companies': companies, 'records': pub}, ensure_ascii=False, indent=1), encoding='utf-8')
(out / 'hold.json').write_text(json.dumps(hold, ensure_ascii=False, indent=1), encoding='utf-8')
(out / 'reuse-assessment.json').write_text(json.dumps(assess, ensure_ascii=False, indent=1), encoding='utf-8')
gate = {'pass': [], 'blocked': {}}
for r in pub:
    try: SA.public_projection(r); gate['pass'].append(r['id'])
    except Exception as e: gate['blocked'][str(e)] = gate['blocked'].get(str(e), 0) + 1
m = {'release': 'data-centres-v2-candidate', 'date': TODAY, 'candidates': len(pub), 'hold': len(hold), 'exact_sites': sum(r['location']['precision'] == 'exact' for r in pub),
     'with_satellite_now': sum(1 for r in pub if (r['imagery_ref'] or {}).get('satellite_now')), 'with_before_after': sum(1 for r in pub if (r['imagery_ref'] or {}).get('satellite_now') and (r['imagery_ref'] or {}).get('satellite_before')),
     'with_photo': sum(1 for r in pub if (r['imagery_ref'] or {}).get('photo')), 'placeholder_only': sum(1 for r in pub if not r['imagery_ref']),
     'gate_pass_now': len(gate['pass']), 'gate_blocked': gate['blocked'], 'publication': 'Not published. Owner approval required; NEXTDC additionally needs permission/legal review.'}
(out / 'MANIFEST.json').write_text(json.dumps(m, indent=1), encoding='utf-8'); print(json.dumps(m, indent=1))
