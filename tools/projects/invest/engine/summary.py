"""Summary across batches: yield, unresolved reasons, audit accuracy and cost. Read-only."""
import json
from collections import Counter
from pathlib import Path

INV = Path(__file__).resolve().parents[4] / 'data/projects/invest'


def main():
    rows, unresolved, audit = [], Counter(), Counter()
    for f in sorted(x for x in (INV / 'reports').glob('*.json') if not x.name.startswith('_')):
        r = json.loads(f.read_text())
        a = INV / 'audits' / f.name
        aud = json.loads(a.read_text()) if a.exists() else None
        if aud:
            audit['checked'] += aud['checked']
            audit['correct'] += aud['correct']
        for k, v in r.get('unresolved_reasons', {}).items():
            unresolved[k.split(' (')[0]] += v
        rows.append({'batch': r['batch'], 'candidates': r.get('candidates'), 'categories': r.get('categories', r.get('stats')),
                     'yield_pct': r.get('yield_pct'), 'seconds': (r.get('cost') or {}).get('seconds', r.get('seconds')),
                     'audit': '%d/%d' % (aud['correct'], aud['checked']) if aud else 'pending'})
    out = {'batches': rows, 'unresolved': dict(unresolved.most_common()), 'audit_total': dict(audit)}
    (INV / 'reports' / '_summary.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
