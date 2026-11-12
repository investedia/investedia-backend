"""Run one verification batch from a config in data/projects/invest/batches/<name>.json.

python -m tools.projects.invest.engine.batch <name> [--today YYYY-MM-DD]
Reads the research store, fetches each document once, extracts rows, matches, classifies, writes
verified relationships (A/B) into data/projects/invest/verifications.json and a batch report with yield,
unresolved cases, cost and an audit sample. Nothing is published by this step.
"""
import argparse, json, random, time
from collections import Counter
from datetime import date
from pathlib import Path

from . import extract, fetch
from .classify import classify, safeguards
from .match import candidates_for

ROOT = Path(__file__).resolve().parents[4]
INV = ROOT / 'data/projects/invest'


def run(cfg, research, ledger, today):
    t0 = time.time()
    eids = set(cfg['company_entity_ids'])
    if cfg.get('pool') == 'by_location':
        # The company's own filing is the link; candidates are all research projects in the filing's countries.
        own = {'type': 'E1', 'listed_entity_id': cfg['company_entity_ids'][0], 'listed_name': cfg['company'], 'lei': cfg['identity']['id'],
               'cik': cfg['listing'].get('cik'), 'hq_country': cfg.get('hq_country'), 'path': [cfg['company_entity_ids'][0]],
               'path_names': [cfg['company']], 'path_edges': [], 'effective_stake': None, 'owner_match': 'document', 'owner': cfg['company'], 'owner_stake': None}
        pool = []
        for p in research:
            if p.get('country') in cfg['countries']:
                ex = [e for e in p.get('candidate_exposures', []) if e['listed_entity_id'] in eids] or [own]
                pool.append(dict(p, candidate_exposures=ex))
    else:
        pool = [p for p in research if any(e['listed_entity_id'] in eids for e in p['candidate_exposures'])]
    by_id = {p['id']: p for p in pool}
    results, docs, cost = {}, [], Counter()
    for d in cfg['documents']:
        try:
            try:
                path, sha, meta = fetch.fetch(d['url'])
            except OSError as x:  # transient network reset: one retry; HTTP refusals are not retried
                if '403' in str(x) or '404' in str(x):
                    raise
                time.sleep(5)
                path, sha, meta = fetch.fetch(d['url'])
        except Exception as x:  # recorded, never bypassed
            docs.append({'url': d['url'], 'error': str(x)})
            continue
        cost['documents'] += 1
        cost['bytes'] += meta['bytes']
        text = fetch.text_of(path)
        rows = extract.table(text, d['extract']) if d['extract']['type'] == 'table' else []
        if d['extract']['type'] == 'html_table':
            rows = extract.html_table(Path(path).read_text(encoding='utf-8', errors='ignore'), d['extract'])
        if d['extract']['type'] == 'prose':  # project pages: the page must name the candidate and the company's role
            from .match import core
            for p in pool:
                if d['extract'].get('project_ids') and p['id'] not in d['extract']['project_ids']:
                    continue
                hit = extract.prose_for(text, p['name'], core, d['extract'].get('company_words', [d['publisher']]))
                if hit:
                    rows.append(dict(hit, _project=p['id']))
        docs.append({'url': d['url'], 'sha256': sha, 'date': d['date'], 'kind': d['kind'], 'rows': len(rows)})
        doc = dict(d, sha256=sha)
        for row in rows:
            matches = [(by_id[row['_project']], 'exact')] if row.get('_project') else candidates_for(row, pool, cfg.get('company_tokens', []))
            whole = [p for p, k in matches if k == 'whole']
            whole_mw = sum(p['mw'] or 0 for p in whole)
            for p, kind in matches:
                e = next(e for e in p['candidate_exposures'] if e['listed_entity_id'] in eids)
                if kind == 'whole':  # all phases of the named plant, judged on their combined capacity
                    cat, why, stake = classify(dict(p, mw=whole_mw), e, row, 'loose', doc, today)
                    why = [w + ' (whole plant: %d phases, %s MW together)' % (len(whole), whole_mw) for w in why]
                else:
                    cat, why, stake = classify(p, e, row, kind, doc, today)
                prev = results.get(p['id'])
                rank = {'A': 0, 'B': 1, 'D': 2, 'C': 3}
                if prev and rank[prev['category']] <= rank[cat]:
                    continue
                results[p['id']] = {'project': p['id'], 'name': p['name'], 'category': cat, 'reasons': why, 'stake': stake,
                                    'exposure': e, 'row': row, 'doc': doc, 'internal_only': safeguards(e) if cat in 'AB' else []}
    if cfg.get('pool') == 'by_location':
        pool = [p for p in pool if p['id'] in results]  # report only projects the filing names
    # Expansion groups are identified by capacity only: if one row fits several groups of the same plant,
    # or several rows fit the same group, the match is ambiguous and is not verified.
    from collections import defaultdict
    fits = defaultdict(set)
    for pid, r in results.items():
        if r.get('row') and r['category'] in ('A', 'B') and by_id.get(pid, {}).get('expansion'):
            fits[(pid.rsplit(':x', 1)[0], r['row']['doc_name'])].add(pid)
    rows_per_group = defaultdict(set)
    for (plant, row_name), pids in fits.items():
        for pid in pids:
            rows_per_group[pid].add(row_name)
    for (plant, row_name), pids in fits.items():
        for pid in pids:
            if len(pids) > 1 or len(rows_per_group[pid]) > 1:
                results[pid].update(category='C', reasons=['ambiguous expansion: several unit groups of %s fit "%s" on capacity alone' % (plant, row_name)])
    for p in pool:
        results.setdefault(p['id'], {'project': p['id'], 'name': p['name'], 'category': 'C', 'reasons': ['not named in the batch documents'], 'exposure': None, 'internal_only': []})
    written = 0
    for r in results.values():
        if r['category'] not in ('A', 'B'):
            continue
        e, d = r['exposure'], r['doc']
        key = '%s|%s' % (r['project'], e['listed_entity_id'])
        ledger[key] = {'category': r['category'], 'exposure_type': 'indirect' if e['type'] != 'E1' or r['row'].get('indirect') else 'direct',
                       'identity': cfg['identity'], 'listing': cfg['listing'],
                       'link': [{'url': d['url'], 'sha256': d['sha256'], 'document_date': d['date'], 'publisher': d['publisher'],
                                 'proves': '%s names %s%s' % (d['publisher'], r['row']['doc_name'],
                                           (' with a %s%% interest' % r['stake']) if r['stake'] is not None else ''),
                                 'quote': r['row']['passage'], 'retrieved_at': today, 'edge': None}],
                       'stake': {'value': r['stake'], 'note': 'As stated in the document' if r['stake'] is not None else 'Not stated in the document'},
                       'document_row': {'name': r['row']['doc_name'], 'mw': r['row']['mw'], 'cod': r['row']['cod'], 'section': r['row']['section'], 'joint_venture': r['row'].get('joint_venture', False)},
                       'cost': r['row'].get('cost'),
                       'internal_only': r['internal_only'], 'company_states_interest': d['kind'] == 'company' and d.get('publisher_is_listed_company', False), 'batch': cfg['batch'], 'reviewer': 'engine (batch %s)' % cfg['batch'], 'verified_at': today}
        written += 1
    cats = Counter(r['category'] for r in results.values())
    unresolved = Counter(r['reasons'][0].split(':')[0] for r in results.values() if r['category'] in 'CD')
    a = sorted([r for r in results.values() if r['category'] in 'AB'], key=lambda r: r['project'])
    rng = random.Random(cfg['batch'])
    sample = rng.sample(a, min(len(a), max(5, len(a) // 5))) if a else []
    report = {'batch': cfg['batch'], 'run_at': today, 'company': cfg['company'], 'documents': docs, 'candidates': len(pool),
              'categories': dict(cats), 'verified_written': written, 'yield_pct': round(100 * (cats['A'] + cats['B']) / max(1, len(pool)), 1),
              'unresolved_reasons': dict(unresolved), 'internal_only': sum(1 for r in a if r['internal_only']),
              'cost': {'seconds': round(time.time() - t0, 1), **cost},
              'audit_sample': [{'project': r['name'], 'id': r['project'], 'document_row': r['row']['doc_name'], 'stake': r['stake'], 'passage': r['row']['passage']} for r in sample],
              'results': sorted(({k: v for k, v in r.items() if k in ('project', 'name', 'category', 'reasons', 'stake', 'internal_only')} for r in results.values()), key=lambda r: (r['category'], r['name']))}
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('batch')
    ap.add_argument('--today', default=date.today().isoformat())
    a = ap.parse_args()
    cfg = json.loads((INV / 'batches' / (a.batch + '.json')).read_text())
    research = json.loads((ROOT / 'data/projects/raw/invest/research.json').read_text())['projects']
    eia = ROOT / 'data/projects/raw/invest/research-eia.json'
    if eia.exists():
        research += [dict(p, candidate_exposures=p.get('candidate_exposures', [])) for p in json.loads(eia.read_text())['projects']]
    led_path = INV / 'verifications.json'
    led = json.loads(led_path.read_text())
    report = run(cfg, research, led['records'], a.today)
    led_path.write_text(json.dumps(led, ensure_ascii=False, indent=1) + '\n')
    (INV / 'reports').mkdir(exist_ok=True)
    (INV / 'reports' / (a.batch + '.json')).write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({k: report[k] for k in ('batch', 'candidates', 'categories', 'yield_pct', 'unresolved_reasons', 'internal_only', 'cost')}, indent=1))


if __name__ == '__main__':
    main()
