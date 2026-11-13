"""Project <-> Investedia news matching (Phase D proof of concept; local only).

python -m tools.projects.invest.news_match <frontend assets/globe dir>
A match needs ALL of: (1) every distinctive project-name word in the headline/summary (generic words such as
'solar', 'wind', 'project', company names and numbers do not count; at least 2 distinctive words or one rare word
of 6+ letters), (2) country of the project OR the listed owner/ticker named in the article, (3) energy context
(technology word or power-plant vocabulary). Phase numbers in the project name must also appear.
Status: 'confirmed' when the owner company is also named, else 'probable'. Events are detected by keywords and
never scored as positive/negative. Output: data/projects/invest/derived/project-news.json
"""
import json, re, sys
from pathlib import Path

from .engine.match import core

ROOT = Path(__file__).resolve().parents[3]
GENERIC = {'solar', 'wind', 'farm', 'park', 'project', 'power', 'plant', 'station', 'energy', 'storage', 'battery', 'hydroelectric', 'hydro',
           'generating', 'llc', 'pv', 'ipp', 'phase', 'multipurpose', 'thermal', 'super', 'renewable', 'center', 'facility', 'unit', 'units',
           'creek', 'lake', 'river', 'mountain', 'county', 'east', 'west', 'north', 'south', 'new', 'red', 'blue', 'green', 'city', 'hill', 'valley'}
TECH = {'Solar': r'solar|photovoltaic|\bpv\b', 'Wind': r'wind', 'Hydropower': r'hydro|dam\b', 'Battery storage': r'battery|storage|bess',
        'Coal': r'coal|thermal', 'Oil & gas': r'gas|combined.cycle|turbine|thermal', 'Nuclear': r'nuclear|reactor'}
POWER = r'power plant|power station|megawatt|\bmw\b|\bgw\b|generation|capacity|electricity|utility'
EVENTS = [('cancellation', r'cancel|scrap|abandon|shelve'), ('commissioning', r'commission|begins? (commercial )?operation|comes online|energi[sz]ed|synchroni[sz]'),
          ('construction_start', r'break(s)? ground|groundbreaking|construction (begins|starts|started)|foundation stone'),
          ('financing', r'financ|loan|bond|debt|funding'), ('ownership_change', r'acquir|stake|sell|sale of|divest|merger'),
          ('delay', r'delay|postpon|behind schedule|pushed back'), ('cost_increase', r'cost overrun|cost (rise|increase)|over budget|revised cost'),
          ('regulatory_approval', r'approv|clearance|permit|licen[cs]e'), ('capacity_expansion', r'expan|additional capacity|phase (ii|2|iii|3)'),
          ('announcement', r'announce|unveil|plans? to build|proposed')]


def stories(d):
    seen = {}
    for f in ('news-archive.json', 'news-live.json', 'news-48h.json'):
        p = Path(d) / f
        if p.exists():
            for s in json.loads(p.read_text()).get('stories', []):
                seen.setdefault(s['id'], s)
    return list(seen.values())


def main():
    news = stories(sys.argv[1])
    P = json.loads((ROOT / 'assets/globe/projects-invest.json').read_text())['projects']
    out, checked = [], 0
    for p in P:
        owners = {(e['verification']['identity'].get('legal_name') or '').lower() for e in p['exposures']}
        tickers = {e['verification']['listing'].get('ticker') for e in p['exposures']}
        co_words = {w for o in owners for w in core(o)}
        name = re.sub(r'\(.*?\)', ' ', p['name'])
        words = [w for w in core(name) if w not in GENERIC and w not in co_words and not w.isdigit()]
        nums = re.findall(r'\b(\d+|i{1,3}|iv|v)\b', p['name'].lower().replace('(phase', ' '))
        if not words or (len(words) < 2 and len(words[0]) < 6):
            continue  # too generic to match safely (e.g. 'Hammond'); never matched on company name alone
        base = re.sub(r'(?i)\b(llc|inc|project|solar farm|solar park|wind farm|power plant|power station|generating station|hydroelectric plant|ipp)\b|[,.]', ' ', name)
        toks = [t for t in base.split() if t]
        if len(toks) < 2 and not (toks and len(toks[0]) >= 7):
            continue  # single short word names are too ambiguous
        phrase = r'\b' + r'[\s-]+'.join(re.escape(t) for t in toks) + r'\b'
        checked += 1
        for s in news:
            text = ' '.join(str(s.get(k) or '') for k in ('headline', 'summary', 'why'))
            if not re.search(phrase, text, re.I):  # the project name must appear as a phrase, not scattered words
                continue
            if nums and not all(re.search(r'\b%s\b' % n, text.lower()) for n in nums):
                continue
            ents = json.dumps(s.get('impacts', []) + s.get('entities', [])).lower()
            owner_named = any(t and (t.lower() in ents or re.search(r'\b%s\b' % re.escape(t), text)) for t in tickers) or any(o and o.split()[0] in text.lower() for o in owners)
            country_ok = (s.get('location') or {}).get('country', '').startswith(p['country'][:6]) or p['country'].lower() in text.lower()
            energy = re.search(TECH.get(p['kind'], 'x^') + '|' + POWER, text, re.I)
            if not (energy and (country_ok or owner_named)):
                continue
            ev = [k for k, r in EVENTS if re.search(r, text, re.I)]
            out.append({'project': p['id'], 'project_name': p['name'], 'article': s['id'], 'headline': s.get('headline'),
                        'published_at': s.get('published_at'), 'source': (s.get('source') or {}).get('name'), 'url': (s.get('source') or {}).get('url'),
                        'status': 'confirmed' if owner_named else 'probable', 'events': ev,
                        'evidence': {'name_words': words, 'country_match': bool(country_ok), 'owner_named': bool(owner_named), 'energy_context': energy.group(0)},
                        'sentiment': None})
    o = ROOT / 'data/projects/invest/derived/project-news.json'
    o.write_text(json.dumps({'schema': 'investedia.projects.news.v0', 'articles_scanned': len(news), 'projects_matchable': checked, 'matches': out}, indent=1, ensure_ascii=False) + '\n')
    print({'articles': len(news), 'projects_matchable': checked, 'of': len(P), 'matches': len(out), 'projects_with_news': len({m['project'] for m in out})})
    for m in out: print(m['status'], '|', m['project_name'], '<=', m['headline'], m['events'])


if __name__ == '__main__':
    main()
