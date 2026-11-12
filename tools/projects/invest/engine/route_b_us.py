"""Route B (regulator-confirmed), United States.

Owner: EIA-860M (monthly, planned generators) + EIA-860 annual Schedule 4 ("Ownership of generators owned
jointly or by others"). EIA instructions: Schedule 4 must list every operable or planned generator that is
jointly owned or wholly owned by an entity other than the reporting entity; a generator absent from it is
owned by the reporting entity. Generators missing from the annual file stay C (ownership not yet surveyed).
Identity: GLEIF LEI by exact legal name (suffix-insensitive), US legal address, ACTIVE. Fuzzy hits rejected.
Listed parent: GLEIF direct/ultimate parent relationship; current listing from the SEC ticker file
(company_tickers_exchange.json) or a verified listing in data/projects/invest/listings.json.
Stakes: only Schedule 4 percentages; never derived.

python -m tools.projects.invest.engine.route_b_us --monthly <860M.xlsx> --annual <dir with 3_1/4_ files> --today YYYY-MM-DD
"""
import argparse, json, math, re, time, urllib.parse
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from . import fetch
from .classify import safeguards

ROOT = Path(__file__).resolve().parents[4]
INV = ROOT / 'data/projects/invest'
SUF = {'co', 'company', 'corp', 'corporation', 'inc', 'incorporated', 'llc', 'l', 'p', 'lp', 'ltd', 'limited', 'the', 'plc', 'sa', 'ag', 'se', 'nv'}
STAGE = {'P': 'Announced', 'L': 'Pre-construction', 'T': 'Pre-construction', 'U': 'Under construction', 'V': 'Under construction', 'TS': 'Commissioning'}
KIND = {'Solar Photovoltaic': 'Solar', 'Batteries': 'Battery storage', 'Onshore Wind Turbine': 'Wind', 'Offshore Wind Turbine': 'Wind',
        'Natural Gas Fired Combined Cycle': 'Oil & gas', 'Natural Gas Fired Combustion Turbine': 'Oil & gas', 'Natural Gas Internal Combustion Engine': 'Oil & gas',
        'Conventional Hydroelectric': 'Hydropower', 'Hydroelectric Pumped Storage': 'Hydropower', 'Nuclear': 'Nuclear', 'Geothermal': 'Geothermal'}


def key(name):
    t = re.sub(r'[^a-z0-9 ]', ' ', (name or '').lower().replace('&', ' and ')).split()
    t = [w for w in t if w not in SUF and not re.fullmatch(r'[a-z]{2}', w)]
    return ' '.join(t)


def gleif(url):
    path, _, _ = fetch.fetch(url, min_interval=1.05)
    return json.loads(Path(path).read_text())


def lei_for(name):
    q = urllib.parse.quote(name)
    try:
        j = gleif('https://api.gleif.org/api/v1/lei-records?filter[entity.legalName]=%s&page[size]=20' % q)
    except Exception:
        return None, 'registry lookup failed'
    hits = [h for h in j.get('data', []) if h['attributes']['entity']['legalAddress']['country'] == 'US'
            and h['attributes']['entity']['status'] == 'ACTIVE' and key(h['attributes']['entity']['legalName']['name']) == key(name)]
    if len(hits) != 1:
        return None, 'no exact legal-entity match' if not hits else 'several exact matches'
    return hits[0], None


def parent_of(lei, rel):
    try:
        j = gleif('https://api.gleif.org/api/v1/lei-records/%s/%s' % (lei, rel))
        return j.get('data')
    except Exception:  # 404 = no parent reported
        return None


def run(monthly, annual, today):
    m = pd.read_excel(monthly, sheet_name='Planned', header=2)
    m = m[pd.to_numeric(m['Plant ID'], errors='coerce').notna()].copy()
    m['mw'] = pd.to_numeric(m['Nameplate Capacity (MW)'], errors='coerce')
    gen = pd.read_excel(Path(annual) / '3_1_Generator_Y2024.xlsx', sheet_name=None, header=1)
    known = set()
    for sh in ('Operable', 'Proposed'):
        g = gen[sh]
        g = g[pd.to_numeric(g['Plant Code'], errors='coerce').notna()]
        known |= {(int(a), str(b)) for a, b in zip(g['Plant Code'], g['Generator ID'])}
    own = pd.read_excel(Path(annual) / '4___Owner_Y2024.xlsx', header=1)
    own = own[pd.to_numeric(own['Plant Code'], errors='coerce').notna()]
    owners = defaultdict(list)
    for r in own.itertuples():
        pct = pd.to_numeric(r[14], errors='coerce')  # blank or text stays unknown
        owners[(int(r[3]), str(r[6]))].append((r[8], r[13], None if pct != pct else float(pct)))
    sec_path, _, _ = fetch.fetch('https://www.sec.gov/files/company_tickers_exchange.json')
    sec = json.loads(Path(sec_path).read_text())
    sec_by_key = defaultdict(list)
    for cik, name, ticker, exch in sec['data']:
        sec_by_key[key(name)].append({'cik': cik, 'name': name, 'ticker': ticker, 'exchange': exch})
    listings = json.loads((INV / 'listings.json').read_text())['by_lei'] if (INV / 'listings.json').exists() else {}
    records, ledger, stats, lei_cache = [], {}, Counter(), {}
    for pid, g in m.groupby('Plant ID'):
        mw = g.mw.sum()
        if not mw or mw < 20:
            continue
        r0 = g.iloc[0]
        st = g['Status'].str.extract(r'\((\w+)\)')[0].mode()
        status = st.iloc[0] if len(st) else None
        tech = g['Technology'].mode().iloc[0] if g['Technology'].notna().any() else None
        py = int(g['Planned Operation Year'].max())
        pm = int(g[g['Planned Operation Year'] == py]['Planned Operation Month'].max())
        rec = {'id': 'eia:%d' % pid, 'name': r0['Plant Name'], 'sector': 'Energy & Utilities', 'kind': KIND.get(tech, tech), 'technology': tech,
               'country': 'United States', 'cc': 'US', 'state': r0['Plant State'], 'lat': float(r0['Latitude']), 'lon': float(r0['Longitude']),
               'precision': 'exact', 'mw': round(float(mw), 1), 'stage': STAGE.get(status), 'eia_status': status, 'expected': '%d-%02d' % (py, pm),
               'expected_year': py, 'cost': None, 'progress': None, 'owners': [],
               'source': {'name': 'U.S. Energy Information Administration, EIA-860M (September 2026)', 'licence': 'US public domain',
                          'url': 'https://www.eia.gov/electricity/data/eia860m/'}, 'route_b': None}
        stats['plants'] += 1
        gens = [(int(pid), str(x)) for x in g['Generator ID']]
        if not all(k in known for k in gens):
            rec['route_b'] = {'category': 'C', 'reason': 'generator newer than the EIA-860 2024 ownership survey'}
            records.append(rec); stats['C newer than ownership survey'] += 1
            continue
        sets = {tuple(sorted(owners.get(k, [(r0['Entity Name'], int(r0['Entity ID']), None)]))) for k in gens}
        if len(sets) != 1:
            rec['route_b'] = {'category': 'C', 'reason': 'generators of this plant have different owners'}
            records.append(rec); stats['C mixed owners'] += 1
            continue
        plant_owners = list(next(iter(sets)))
        rec['owners'] = [{'name': n, 'eia_id': i, 'stake': round(p * 100, 2) if p is not None else None} for n, i, p in plant_owners]
        verified = []
        for o in rec['owners']:
            if o['name'] not in lei_cache:
                lei_cache[o['name']] = lei_for(o['name'])
            hit, why = lei_cache[o['name']]
            if not hit:
                continue
            ent = hit['attributes']['entity']['legalName']['name']
            chain = [{'lei': hit['id'], 'name': ent}]
            listed = sec_by_key.get(key(ent))
            if not listed:
                for rel in ('direct-parent', 'ultimate-parent'):
                    par = parent_of(hit['id'], rel)
                    if par and par['id'] != chain[-1]['lei']:
                        chain.append({'lei': par['id'], 'name': par['attributes']['entity']['legalName']['name'], 'relationship': rel})
                for c in chain[1:]:
                    listed = sec_by_key.get(key(c['name'])) or ([listings[c['lei']]] if c['lei'] in listings else None)
                    if listed:
                        chain = chain[:chain.index(c) + 1]
                        break
            if not listed or len(listed) != 1 and len({x['cik'] for x in listed}) != 1:
                continue
            L = listed[0]
            verified.append({'owner': o, 'chain': chain, 'listing': L})
        if not verified:
            rec['route_b'] = {'category': 'C', 'reason': 'owner has no exact registry identity or no currently listed parent'}
            records.append(rec); stats['C no listed identity'] += 1
            continue
        stats['B plants'] += 1
        rec['route_b'] = {'category': 'B', 'links': []}
        for v in verified:
            o, chain, L = v['owner'], v['chain'], v['listing']
            exposure = {'type': 'E1' if len(chain) == 1 else 'E3', 'listed_entity_id': 'lei:' + chain[-1]['lei'], 'listed_name': L['name'],
                        'lei': chain[-1]['lei'], 'cik': L.get('cik'), 'hq_country': None, 'path': [c['lei'] for c in chain],
                        'path_names': [c['name'] for c in chain], 'path_edges': [[a['lei'], b['lei']] for a, b in zip(chain, chain[1:])],
                        'effective_stake': o['stake'] if len(chain) == 1 else None, 'owner_match': 'id', 'owner': o['name'], 'owner_stake': o['stake']}
            rec.setdefault('candidate_exposures', []).append(exposure)
            evidence = [{'url': 'https://www.eia.gov/electricity/data/eia860m/', 'document_date': '2026-09-30', 'publisher': 'U.S. EIA',
                         'proves': 'EIA-860M lists %s (plant %d) as planned, status %s, reported by %s' % (rec['name'], pid, status, r0['Entity Name']), 'retrieved_at': today},
                        {'url': 'https://www.eia.gov/electricity/data/eia860/', 'document_date': '2025-09-30', 'publisher': 'U.S. EIA',
                         'proves': ('EIA-860 2024 Schedule 4 lists %s as owner (%s%%)' % (o['name'], o['stake']) if o['stake'] is not None
                                    else 'EIA-860 2024 Schedule 4 lists no other owner, so the reporting entity %s owns the generators (EIA instructions, Schedule 4 item 1)' % o['name']),
                         'retrieved_at': today},
                        {'url': 'https://api.gleif.org/api/v1/lei-records/%s' % chain[0]['lei'], 'publisher': 'GLEIF', 'document_date': today,
                         'proves': 'Legal entity %s, LEI %s' % (chain[0]['name'], chain[0]['lei']), 'retrieved_at': today}]
            for a, b in zip(chain, chain[1:]):
                evidence.append({'url': 'https://api.gleif.org/api/v1/lei-records/%s/%s' % (a['lei'], b['relationship']), 'publisher': 'GLEIF', 'document_date': today,
                                 'proves': '%s reports %s as its %s' % (a['name'], b['name'], b['relationship'].replace('-', ' ')), 'retrieved_at': today, 'edge': [a['lei'], b['lei']]})
            evidence.append({'url': 'https://www.sec.gov/files/company_tickers_exchange.json', 'publisher': 'U.S. SEC', 'document_date': today,
                             'proves': '%s is currently listed: %s on %s (CIK %s)' % (L['name'], L['ticker'], L['exchange'], L.get('cik')), 'retrieved_at': today})
            ledger['%s|%s' % (rec['id'], exposure['listed_entity_id'])] = {
                'category': 'B', 'exposure_type': 'direct' if exposure['type'] == 'E1' else 'indirect',
                'identity': {'scheme': 'LEI', 'id': chain[-1]['lei'], 'legal_name': chain[-1]['name'], 'source_url': 'https://api.gleif.org/api/v1/lei-records/' + chain[-1]['lei'], 'checked_at': today},
                'listing': {'ticker': L['ticker'], 'exchange': L['exchange'], 'cik': L.get('cik'), 'source_url': 'https://www.sec.gov/files/company_tickers_exchange.json', 'checked_at': today},
                'link': evidence, 'stake': {'value': o['stake'], 'note': 'EIA-860 Schedule 4 percentage' if o['stake'] is not None else 'Not stated by EIA (sole owner by reporting rule; no percentage published)'},
                'internal_only': safeguards(exposure), 'company_states_interest': False, 'batch': 'route-b-us-2026-11', 'reviewer': 'engine (route B, US)', 'verified_at': today}
        records.append(rec)
    return records, ledger, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--monthly', required=True)
    ap.add_argument('--annual', required=True)
    ap.add_argument('--today', required=True)
    a = ap.parse_args()
    t0 = time.time()
    records, ledger, stats = run(a.monthly, a.annual, a.today)
    out = ROOT / 'data/projects/raw/invest/research-eia.json'
    out.write_text(json.dumps({'projects': records}, ensure_ascii=False) + '\n')
    led_path = INV / 'verifications.json'
    led = json.loads(led_path.read_text())
    led['records'] = {k: v for k, v in led['records'].items() if v.get('batch') != 'route-b-us-2026-11'}
    led['records'].update(ledger)
    led_path.write_text(json.dumps(led, ensure_ascii=False, indent=1) + '\n')
    rep = {'batch': 'route-b-us-2026-11', 'stats': dict(stats), 'b_links': len(ledger), 'seconds': round(time.time() - t0)}
    (INV / 'reports').mkdir(exist_ok=True)
    (INV / 'reports/route-b-us-2026-11.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps(rep, indent=1))


if __name__ == '__main__':
    main()
