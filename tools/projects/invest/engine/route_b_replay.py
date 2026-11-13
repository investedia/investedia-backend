"""Offline replay of route B (US) from the committed, audited ownership chains.

Why: the live route needs the SEC ticker list (blocked for automated access from some networks), an approved SEC contact
and about 1,000 GLEIF lookups. The verified result is already committed: every B project in assets/globe/projects-invest.json
carries its owner, registry chain, listed company and ticker (audited 100/100 on 12 Nov 2026).

This module runs the REAL route-B code (tools.projects.invest.engine.route_b_us.run) on the raw EIA files, but answers the
registry, parent and SEC lookups ONLY from those committed chains. Consequences, all intended:
  * project rows (name, location, MW, stage, expected date, owners and stakes) come fresh from EIA-860M and EIA-860;
  * a plant is B only if its owner and chain are already in the committed audited set; every other plant stays C;
  * nothing is newly verified and no chain is invented. Freshness (new delistings, parent changes) is NOT rechecked.
Run the live route (route_b_us) when the sources are reachable to refresh the chains.

python -m tools.projects.invest.engine.route_b_replay --monthly <860M.xlsx> --annual <860 dir> --today YYYY-MM-DD [--year 2025]
Writes data/projects/raw/invest/research-eia.json (git-ignored). Does not touch the ledger or the public layer.
"""
import argparse, json, tempfile
from pathlib import Path

from . import fetch, route_b_us as rb

ROOT = Path(__file__).resolve().parents[4]
LAYER = ROOT / 'assets/globe/projects-invest.json'


def chains(layer):
    owners, parents, listings = {}, {}, {}
    for p in layer['projects']:
        if not p['id'].startswith('eia:'):
            continue
        for e in p['exposures']:
            v = e.get('verification') or {}
            if v.get('category') != 'B' or not e.get('path'):
                continue
            path, names = e['path'], e['path_names']
            owners[e['owner']] = {'id': path[0], 'attributes': {'entity': {'legalName': {'name': names[0]}}}}
            for i, lei in enumerate(path[:-1]):
                parents[lei] = {'direct-parent': {'id': path[i + 1], 'name': names[i + 1]}, 'ultimate-parent': {'id': path[-1], 'name': names[-1]}}
            lst = v.get('listing') or {}
            listings[str(e['cik'])] = {'cik': e['cik'], 'name': e['listed_name'], 'ticker': lst.get('ticker'), 'exchange': lst.get('exchange')}
    return owners, parents, listings


def run(monthly, annual, today, year=2025, layer_path=LAYER):
    layer = json.loads(Path(layer_path).read_text())
    owners, parents, listings = chains(layer)

    def lei_for(name):
        hit = owners.get(name)
        return (hit, None) if hit else (None, 'not in the committed audited chains')

    def parent_of(lei, rel):
        p = parents.get(lei, {}).get(rel)
        return {'id': p['id'], 'attributes': {'entity': {'legalName': {'name': p['name']}}}} if p else None

    def sec_sub(cik):
        l = listings.get(str(int(cik)))
        return {'category': 'Large accelerated filer', 'tickers': [l['ticker']], 'exchanges': [l['exchange']]} if l and l['ticker'] else None

    tick = Path(tempfile.mkdtemp()) / 'tickers.json'
    tick.write_text(json.dumps({'data': [[l['cik'], l['name'], l['ticker'], l['exchange']] for l in listings.values()]}))
    saved = (rb.lei_for, rb.parent_of, rb.sec_sub, fetch.fetch)
    rb.lei_for, rb.parent_of, rb.sec_sub = lei_for, parent_of, sec_sub
    fetch.fetch = lambda url, **k: (tick, 'replay', {}) if url.endswith('company_tickers_exchange.json') else saved[3](url, **k)
    try:
        return rb.run(monthly, annual, today, year)
    finally:
        rb.lei_for, rb.parent_of, rb.sec_sub, fetch.fetch = saved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--monthly', required=True)
    ap.add_argument('--annual', required=True)
    ap.add_argument('--today', required=True)
    ap.add_argument('--year', type=int, default=2025)
    a = ap.parse_args()
    records, ledger, stats = run(a.monthly, a.annual, a.today, a.year)
    out = ROOT / 'data/projects/raw/invest/research-eia.json'
    out.write_text(json.dumps({'projects': records}, ensure_ascii=False) + '\n')
    print(json.dumps({'plants': stats['plants'], 'B plants': stats['B plants'], 'b_links': len(ledger), 'stats': dict(stats)}, indent=1))


if __name__ == '__main__':
    main()
