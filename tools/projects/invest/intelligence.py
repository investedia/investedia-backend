"""Investment-intelligence layer (Phase C, local only; not read by the Globe yet).

python -m tools.projects.invest.intelligence
Reads assets/globe/projects-invest.json (verified only) and writes:
  data/projects/invest/derived/projects-intel.json   per project: exposure, financials, investment access
  data/projects/invest/derived/company-portfolios.json  per listed company: every verified project + exact relationship
Rules: only fields stated in the verification evidence; unknown stays null; no estimates, no trading/offer claims.
"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'data/projects/invest/derived'


def exposure(e):
    v = e['verification']
    return {'listed_company': v['identity'].get('legal_name'), 'ticker': v['listing'].get('ticker'), 'exchange': v['listing'].get('exchange'),
            'identity': {k: v['identity'].get(k) for k in ('scheme', 'id')},
            'direct_owner': e.get('owner'), 'ownership_chain': e.get('path_names') or [],
            'relationship': 'owns the project directly' if v['exposure_type'] == 'direct' else 'owns the project through subsidiaries or joint ventures',
            'exposure_type': v['exposure_type'], 'stake_pct': v['stake'].get('value'), 'stake_note': v['stake'].get('note'),
            'confirmation': {'A': 'company-confirmed', 'B': 'regulator-confirmed owner + verified listed-parent chain'}[v['category']],
            'what_an_investor_holds': 'shares of %s (company-level exposure); this is not a direct investment in the project' % v['identity'].get('legal_name'),
            'evidence': [{'publisher': l.get('publisher'), 'url': l.get('url'), 'date': l.get('document_date')} for l in v['link']],
            'verified_at': v.get('verified_at')}


def financials(p):
    rows = [e['verification'].get('document_row') or {} for e in p['exposures']]
    sched = next((r.get('schedule') or r.get('cod') for r in rows if r.get('schedule') or r.get('cod')), None)
    c = p.get('cost')
    return {'construction_cost': {'amount': c['amount'], 'currency': c['currency'], 'basis': c.get('basis'), 'quote': c.get('quote'), 'source': c.get('source')} if c else None,
            'revised_cost': None,  # filled only when a later official document states a revision
            'completion_target': sched or p.get('expected'),
            'completion_target_source': 'company document' if sched else ('EIA-860M' if p.get('expected') else None),
            'original_completion_target': None, 'construction_status': p.get('stage'), 'status_note': p.get('stage_note'),
            'progress': p.get('progress'), 'documented_delays': []}


def access(p):
    """Never claims a direct offering. Listed exposure only where an A/B link to a listed company exists."""
    if any(e['verification']['category'] in 'AB' for e in p['exposures']):
        return {'class': 'publicly_listed_company_exposure', 'direct_offering': None,
                'note': 'Exposure is through listed shares of the companies shown; no direct project offering is verified.'}
    return {'class': 'research_only', 'direct_offering': None, 'note': 'No verified listed-company link.'}


def main():
    P = json.loads((ROOT / 'assets/globe/projects-invest.json').read_text())['projects']
    OUT.mkdir(parents=True, exist_ok=True)
    intel, port = [], defaultdict(lambda: {'company': None, 'ticker': None, 'exchange': None, 'projects': []})
    for p in P:
        ex = [exposure(e) for e in p['exposures']]
        intel.append({'id': p['id'], 'name': p['name'], 'sector': p.get('sector'), 'kind': p['kind'], 'country': p['country'],
                      'mw': p.get('mw'), 'location': {'lat': p['lat'], 'lon': p['lon'], 'precision': p.get('precision')},
                      'exposures': ex, 'other_owners_not_listed': [o['name'] for o in p.get('other_owners', [])],
                      'financials': financials(p), 'investment_access': access(p)})
        for x in ex:
            k = x['ticker'] or x['identity']['id']
            c = port[k]; c.update(company=x['listed_company'], ticker=x['ticker'], exchange=x['exchange'])
            c['projects'].append({'id': p['id'], 'name': p['name'], 'kind': p['kind'], 'country': p['country'], 'mw': p.get('mw'), 'stage': p.get('stage'),
                                  'relationship': x['relationship'], 'direct_owner': x['direct_owner'], 'stake_pct': x['stake_pct'], 'confirmation': x['confirmation']})
    for c in port.values():
        c['totals'] = {'projects': len(c['projects']), 'project_capacity_mw_not_share_weighted': round(sum(x['mw'] or 0 for x in c['projects']), 1),
                       'by_kind': dict(sorted({k: sum(1 for x in c['projects'] if x['kind'] == k) for k in {x['kind'] for x in c['projects']}}.items()))}
    (OUT / 'projects-intel.json').write_text(json.dumps({'schema': 'investedia.projects.intel.v0', 'projects': intel}, indent=1, ensure_ascii=False) + '\n')
    (OUT / 'company-portfolios.json').write_text(json.dumps({'schema': 'investedia.projects.portfolios.v0', 'companies': dict(sorted(port.items(), key=lambda kv: -kv[1]['totals']['projects']))}, indent=1, ensure_ascii=False) + '\n')
    fin = [x['financials'] for x in intel]
    print({'projects': len(intel), 'companies': len(port), 'with_cost': sum(1 for f in fin if f['construction_cost']),
           'with_completion_target': sum(1 for f in fin if f['completion_target']), 'stale_flags': sum(1 for f in fin if f['status_note'])})


if __name__ == '__main__':
    main()
