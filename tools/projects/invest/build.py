"""Build the Projects research layer and the public investment layer.

Usage:
  python -m tools.projects.invest.build --power <Global Integrated Power .xlsx> --ownership <Ownership Tracker .xlsx>

The two GEM workbooks stay private (docs-repo release gem-2026-11) and are checked by sha256.
Outputs:
  data/projects/raw/invest/research.json   every pipeline project with candidate exposures (ignored by git)
  data/projects/invest/report.json         counts and reasons (committed)
  assets/globe/projects-invest.json        public layer: only projects that pass rules.evaluate (committed)
assets/globe/projects.json is never touched. Real rows only; unknown values stay null.
"""
import argparse
import re
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from .graph import Registry, clean, split_owners
from .rules import evaluate

ROOT = Path(__file__).resolve().parents[3]
SHA256 = {'power': '34749042643b15cac4423ae67864ad36c391013aa2d5acc65ae7492c5e33ee27',
          'ownership': 'dc77b6be39ec5fc962da20f0f298c6c1bd79d12e863b034b180809b4dea6f0a5'}
POWER_HEADERS = ['Unit / Phase name', 'Type', 'Country/area', 'Plant / Project name', 'Capacity (MW)', 'Status', 'Start year', 'Owner(s)',
                 'Owner(s) GEM Entity ID', 'Latitude', 'Longitude', 'Location accuracy', 'GEM location ID', 'GEM.Wiki URL']
SOURCES = {
    'power': {'name': 'Global Energy Monitor, Global Integrated Power Tracker, September 2026 release',
              'licence': 'CC BY 4.0', 'url': 'https://globalenergymonitor.org/projects/global-integrated-power-tracker/'},
    'ownership': {'name': 'Global Energy Monitor, Global Energy Ownership Tracker, November 2026',
                  'licence': 'CC BY 4.0', 'url': 'https://globalenergymonitor.org/projects/global-energy-ownership-tracker/'}}
KIND = {'utility-scale solar': 'Solar', 'wind': 'Wind', 'hydropower': 'Hydropower', 'coal': 'Coal', 'oil/gas': 'Oil & gas',
        'nuclear': 'Nuclear', 'bioenergy': 'Bioenergy', 'geothermal': 'Geothermal'}
STAGE = {'announced': 'Announced', 'pre-construction': 'Pre-construction', 'construction': 'Under construction'}
ORDER = ['Under construction', 'Pre-construction', 'Announced']


def sheet(wb, name):
    it = wb[name].iter_rows(values_only=True)
    header = [str(h) if h is not None else '' for h in next(it)]
    for row in it:
        if row and row[0] is not None:
            yield dict(zip(header, row))


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


ROMAN = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7, 'viii': 8}


def phase_of(unit_name, kind):
    """Phase number from a GEM unit name: 'Phase II Unit 3' -> 2, 'Stage III Unit 1' -> 3; for wind/solar/
    storage a bare unit number ('3', '1-...Nairyah IPP 1') is the phase. Thermal 'Unit 4' alone is not a phase."""
    u = (clean(unit_name) or '').lower()
    m = re.search(r'(?:phase|stage|block)\s*([ivx]+|\d+)\b', u)
    if m:
        v = m.group(1)
        return ROMAN.get(v) or (int(v) if v.isdigit() else None)
    m = re.search(r'\bipp\s*(\d+)\s*$', u)
    if m:
        return int(m.group(1))
    if kind in ('Solar', 'Wind') and re.fullmatch(r'(\d+)(?:\s*-.*)?', u):
        return int(re.match(r'\d+', u).group(0))
    return None


def plants(rows, iso, registry=None):
    """Group unit rows by GEM location ID. Pipeline units only are kept, split so nothing is counted twice:
    - units with phase labels -> one record per phase ('gem:<loc>:p<n>');
    - otherwise, a plant that also has operating units -> 'expansion' records, one per pipeline stage group;
    - otherwise one plant record ('gem:<loc>')."""
    groups = defaultdict(list)
    for r in rows:
        if clean(r.get('GEM location ID')):
            groups[(r['GEM location ID'], r['Type'])].append(r)
    multi_type = Counter(l for l, t in groups)
    for (loc, typ), all_units in groups.items():
        kind = KIND.get(str(typ), str(typ))
        units = [u for u in all_units if STAGE.get(str(u.get('Status')))]
        if not units:
            continue
        operating = any(str(u.get('Status')) == 'operating' for u in all_units)
        base_id = 'gem:' + loc + ('' if multi_type[loc] == 1 else ':' + kind)
        phases = defaultdict(list)
        for u in units:
            phases[phase_of(u.get('Unit / Phase name'), kind)].append(u)
        if None not in phases and len(units) > 0 and (len(phases) > 1 or operating or any(phase_of(u.get('Unit / Phase name'), kind) for u in all_units if u not in units)):
            for n, us in sorted(phases.items()):
                yield record(base_id + ':p%d' % n, us, kind, iso, registry, phase=n)
        elif operating:
            by_stage = defaultdict(list)
            for u in units:
                by_stage[STAGE[str(u['Status'])]].append(u)
            for st, us in by_stage.items():
                suffix = '' if len(by_stage) == 1 else ':' + st.lower().replace(' ', '-')
                yield record(base_id + ':x' + suffix, us, kind, iso, registry, expansion=True)
        else:
            yield record(base_id, units, kind, iso, registry)


def record(pid, units, kind, iso, registry, phase=None, expansion=False):
    first = units[0]
    lat, lon = num(first.get('Latitude')), num(first.get('Longitude'))
    stage = min((STAGE[str(u['Status'])] for u in units), key=ORDER.index)
    years = [int(y) for y in (num(u.get('Start year')) for u in units) if y]
    owners, seen = [], set()
    for u in units:
        for o in split_owners(u.get('Owner(s)'), u.get('Owner(s) GEM Entity ID'), registry):
            if (o['name'], o['entity_id']) not in seen:
                seen.add((o['name'], o['entity_id']))
                owners.append(o)
    mw = [num(u.get('Capacity (MW)')) for u in units]
    acc = (clean(first.get('Location accuracy')) or '').lower()
    name = clean(first.get('Plant / Project name'))
    return {'id': pid, 'name': name + (' (phase %d)' % phase if phase else ''), 'plant_name': name, 'phase': phase, 'expansion': expansion,
            'units_named': [clean(u.get('Unit / Phase name')) for u in units], 'sector': 'Energy & Utilities', 'kind': kind,
            'country': clean(first.get('Country/area')), 'cc': iso.get(clean(first.get('Country/area'))),
            'lat': lat, 'lon': lon, 'precision': acc if acc in ('exact', 'approximate') else None,
            'mw': round(sum(m for m in mw if m), 1) if any(mw) else None, 'stage': stage,
            'expected_year': max(years) if years else None, 'units': len(units), 'owners': owners,
            'cost': None, 'progress': None, 'wiki': clean(first.get('GEM.Wiki URL')), 'source': SOURCES['power']}


def ledger_exposures(pid, known, ledger):
    """Exposures proven by a document that names the project directly (e.g. a company filing), which the
    GEM/EIA owner fields did not show. Built only from verified ledger records."""
    out = []
    for key, rec in ledger.items():
        p, eid = key.split('|', 1)
        if p != pid or eid in known:
            continue
        out.append({'type': 'E1' if rec.get('exposure_type') == 'direct' else 'E3', 'listed_entity_id': eid,
                    'listed_name': rec['identity'].get('legal_name'), 'lei': rec['identity'].get('id'), 'cik': rec['listing'].get('cik'),
                    'hq_country': rec.get('hq_country'), 'path': [eid], 'path_names': [rec['identity'].get('legal_name')], 'path_edges': [],
                    'effective_stake': (rec.get('stake') or {}).get('value'), 'owner_match': 'document', 'owner': rec['identity'].get('legal_name'), 'owner_stake': None})
    return out


def km(a, b):
    import math
    if None in (a.get('lat'), a.get('lon'), b.get('lat'), b.get('lon')):
        return 1e9
    dx = math.radians(b['lon'] - a['lon']) * math.cos(math.radians((a['lat'] + b['lat']) / 2))
    return 6371 * math.hypot(dx, math.radians(b['lat'] - a['lat']))


def build(power_rows, iso, registry, ledger, today, extra=()):
    research, public, why, cand = [], [], Counter(), Counter()
    def projects():
        for p in plants(power_rows, iso, registry):
            yield p, [dict(e, owner=o['name'], owner_stake=o['stake']) for o in p['owners'] for e in registry.exposures(o)]
        for p in extra:  # EIA research records (route B and filings)
            yield {k: v for k, v in p.items() if k != 'candidate_exposures'}, list(p.get('candidate_exposures', []))
    for p, exposures in projects():
        exposures = exposures + ledger_exposures(p['id'], {e['listed_entity_id'] for e in exposures}, ledger)
        ok, reasons, verified = evaluate(p, exposures, ledger, today)
        research.append(dict(p, candidate_exposures=exposures, public=ok, reasons=reasons))
        for r in reasons:
            why[r] += 1
        if exposures:
            cand['projects_with_candidate'] += 1
            cand['by_type_' + '+'.join(sorted({e['type'] for e in exposures}))] += 1
            cand['by_kind_' + p['kind']] += 1
            cand['by_stage_' + p['stage']] += 1
            if all(e['owner_match'] == 'id' for e in exposures):
                cand['matched_by_gem_id'] += 1
            if any(e['lei'] or e['cik'] for e in exposures):
                cand['listed_company_has_lei_or_cik'] += 1
            if p['precision'] == 'exact':
                cand['exact_location'] += 1
        if ok:
            costs = [e['verification']['cost'] for e in verified if e['verification'].get('cost')]
            if costs:  # only a cost stated in a verified company document, with its quote; never estimated
                p = dict(p, cost=dict(costs[0], source=next(e['verification']['link'][0]['url'] for e in verified if e['verification'].get('cost'))))
            public.append(dict({k: v for k, v in p.items() if k not in ('owners', 'route_b')}, exposures=verified,
                               other_owners=[o for o in p.get('owners', []) if o['name'] not in {v['owner'] for v in verified}]))
    # Company headquarters for relationship lines: matched by LEI (Wikidata P1278), else by ticker. No HQ, no line.
    hq_path = ROOT / 'data/projects/invest/company-hq.json'
    HQ = json.loads(hq_path.read_text()) if hq_path.exists() else {'by_lei': {}, 'by_ticker': {}}
    for p in public:
        for e in p['exposures']:
            v = e['verification']
            e['hq'] = HQ['by_lei'].get(v['identity'].get('id')) or HQ['by_ticker'].get(v['listing'].get('ticker'))
    # Owner-approved location corrections (location-overrides.json); GEM's point is kept for reference.
    lo_path = ROOT / 'data/projects/invest/location-overrides.json'
    LO = json.loads(lo_path.read_text())['overrides'] if lo_path.exists() else {}
    for p in public:
        if p['id'] in LO:
            o = LO[p['id']]
            p.update(lat=o['lat'], lon=o['lon'], precision=o['precision'], location_note={'gem_point': o['gem_point'], 'method': o['method'], 'sources': o['sources']})
    # Satellite pictures (tools/projects/invest/imagery.py): exact or satellite-confirmed sites only.
    im_path = ROOT / 'data/projects/invest/imagery.json'
    IM = json.loads(im_path.read_text())['images'] if im_path.exists() else {}
    for p in public:
        if p.get('precision') in ('exact', 'site') and IM.get(p['id']):  # 'site' = site identity confirmed on imagery, coordinate not official
            p['images'] = IM[p['id']]
    # One public record per physical plant: GEM and EIA describe some US plants twice.
    public.sort(key=lambda p: (-len(p['exposures']), p['id'].startswith('gem:')))
    kept = []
    for p in public:
        dup = next((k for k in kept if k['kind'] == p['kind'] and k['id'].split(':')[0] != p['id'].split(':')[0] and km(k, p) < 2.0), None)  # same plant in GEM and EIA; never merge within one source
        if dup:
            dup.setdefault('also_listed_as', []).append(p['id'])
            seen = {e['listed_entity_id'] for e in dup['exposures']}
            dup['exposures'] += [e for e in p['exposures'] if e['listed_entity_id'] not in seen]
        else:
            kept.append(p)
    public = kept
    companies = Counter(e['listed_name'] for r in research for e in r['candidate_exposures'])
    report = {'as_of': today, 'pipeline_projects': len(research), 'public_projects': len(public),
              'not_public_reasons': dict(why.most_common()), 'candidates': dict(sorted(cand.items())),
              'candidate_listed_companies': len(companies), 'top_candidate_companies': companies.most_common(25),
              'missing_country_code': sum(1 for r in research if not r['cc']), 'sources': SOURCES,
              'notice': 'Candidates are not verified. Only public_projects are shown. Not investment advice.'}
    from .engine.classify import quarter_end
    for p in public:  # an expected date that has passed means the stage needs a fresh source; flag, never guess
        cods = [e['verification'].get('document_row', {}).get('cod') for e in p['exposures']]
        due = [c for c in cods if c and quarter_end(c) < date.fromisoformat(today)]
        if due:
            p['stage_note'] = 'Expected %s according to the source; current status to be re-checked' % due[0]
    cats = Counter(e['verification'].get('category', 'A') for p in public for e in p['exposures'])
    report['public_by_category'] = dict(cats)
    report['public_by_sector_kind'] = dict(Counter(p['kind'] for p in public))
    export = {'schema': 'investedia.projects.invest.v1', 'as_of': today,
              'credit': [s['name'] + ' (' + s['licence'] + ')' for s in SOURCES.values()] +
                        (['Source: U.S. Energy Information Administration, EIA-860M (September 2026) and EIA-860 (2024)'] if extra else []),
              'projects': public}
    return research, report, export


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    import openpyxl
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--power', required=True)
    ap.add_argument('--ownership', required=True)
    ap.add_argument('--today', default=date.today().isoformat())
    a = ap.parse_args()
    for key, path in (('power', a.power), ('ownership', a.ownership)):
        if sha256(path) != SHA256[key]:
            raise SystemExit('%s workbook does not match the reviewed sha256; review headers before changing it' % key)
    pw = openpyxl.load_workbook(a.power, read_only=True)
    ow = openpyxl.load_workbook(a.ownership, read_only=True)
    header = [str(c) for c in next(pw['Power facilities'].iter_rows(values_only=True))]
    missing = [h for h in POWER_HEADERS if h not in header]
    if missing:
        raise SystemExit('power workbook headers changed: %s' % missing)
    iso = {clean(r.get('GEM Standard Country Name/Area')): clean(r.get('ISO-alpha2 Code')) for r in sheet(pw, 'Regions, area, and countries')}
    registry = Registry(sheet(ow, 'All Entities'), sheet(ow, 'Entity Ownership'))
    al_path = ROOT / 'data/projects/invest/owner-aliases.json'
    if al_path.exists():
        registry.aliases = {k: v['entity_id'] for k, v in json.loads(al_path.read_text())['aliases'].items()}
    ledger = json.loads((ROOT / 'data/projects/invest/verifications.json').read_text())['records']
    eia_path = ROOT / 'data/projects/raw/invest/research-eia.json'
    extra = json.loads(eia_path.read_text())['projects'] if eia_path.exists() else []
    research, report, export = build(sheet(pw, 'Power facilities'), iso, registry, ledger, a.today, extra)
    for path, value in ((ROOT / 'data/projects/raw/invest/research.json', {'projects': research}),
                        (ROOT / 'data/projects/invest/report.json', report), (ROOT / 'assets/globe/projects-invest.json', export)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=None if 'raw' in str(path) else 1, sort_keys=True) + '\n')
    print(json.dumps({k: report[k] for k in ('pipeline_projects', 'public_projects', 'candidate_listed_companies', 'missing_country_code', 'candidates')}, indent=1))


if __name__ == '__main__':
    main()
