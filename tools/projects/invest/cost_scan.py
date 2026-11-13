"""Find construction costs stated by listed companies in their latest SEC 10-K (local research; nothing published).

python -m tools.projects.invest.cost_scan
For every public project with a US-SEC-listed company, fetch that company's latest 10-K main document once
(cached), split into sentences, and keep sentences that name the project (full name phrase without
LLC/Solar/etc. suffixes, or the EIA plant name) AND state a dollar amount with cost wording. Output is a
candidate list for manual review: data/projects/invest/derived/cost-candidates.json
"""
import json, re
from collections import defaultdict
from pathlib import Path

from .engine import fetch

ROOT = Path(__file__).resolve().parents[3]
COST = re.compile(r'(estimated|expected|total|projected|approximately|capital)[^.]{0,80}?(cost|investment|capital expenditure)s?[^.]{0,60}?\$\s?[\d.,]+\s?(billion|million)|\$\s?[\d.,]+\s?(billion|million)[^.]{0,80}?(cost|investment|to construct|to build)', re.I)


def ten_k(cik):
    s = json.loads(Path(fetch.fetch('https://data.sec.gov/submissions/CIK%010d.json' % int(cik))[0]).read_text())
    r = s['filings']['recent']
    for i, f in enumerate(r['form']):
        if f == '10-K':
            acc = r['accessionNumber'][i].replace('-', '')
            return 'https://www.sec.gov/Archives/edgar/data/%d/%s/%s' % (int(cik), acc, r['primaryDocument'][i]), r['filingDate'][i]
    return None, None


def phrase(name):
    b = re.sub(r'(?i)\b(llc|inc|project|solar farm|solar park|wind farm|power plant|power station|generating station|energy storage|storage project|ipp)\b|\(.*?\)|[,.]', ' ', name).split()
    return re.compile(r'\b' + r'[\s-]+'.join(map(re.escape, b)) + r'\b', re.I) if b and (len(b) >= 2 or len(b[0]) >= 6) else None


def main():
    P = json.loads((ROOT / 'assets/globe/projects-invest.json').read_text())['projects']
    by_cik = defaultdict(list)
    for p in P:
        for e in p['exposures']:
            cik = e['verification']['listing'].get('cik')
            if cik:
                by_cik[cik].append(p)
    out = []
    for cik, projects in by_cik.items():
        url, date = ten_k(cik)
        if not url:
            continue
        sents = re.split(r'(?<=[.;])\s+', re.sub(r'\s+', ' ', fetch.text_of(fetch.fetch(url)[0])))
        for p in {x['id']: x for x in projects}.values():
            ph = phrase(p['name'])
            if not ph:
                continue
            for s in sents:
                if ph.search(s) and COST.search(s):
                    out.append({'project': p['id'], 'name': p['name'], 'company_cik': cik, 'filing': url, 'filing_date': date, 'sentence': s[:500], 'review': None})
        print(cik, len(projects), 'projects;', sum(1 for o in out if o['company_cik'] == cik), 'cost sentences', flush=True)
    o = ROOT / 'data/projects/invest/derived/cost-candidates.json'
    o.write_text(json.dumps({'candidates': out}, indent=1, ensure_ascii=False) + '\n')
    print('total', len(out), 'for', len({x['project'] for x in out}), 'projects')


if __name__ == '__main__':
    main()
