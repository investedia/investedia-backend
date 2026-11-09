"""Writes data/companies.json: Investedia's company directory, built only from data we already have.

A company is the business; a listing (stock) is a tradable instrument of that business. One company can have several listings
(e.g. a home-market share and a US ADR), and a company without any listing can still be added later (public: false).

Sources (no API calls):
  - assets/globe/markets.json   listed stocks: name, country, sector group, ticker, currency
  - assets/globe/logos.json     company logos already used on the site
  - tools/companies-extra.json  optional hand-checked facts (description, website, HQ, industry, founded, story, related, videos),
                                each with a source URL. Empty fields stay null: nothing is guessed.
Run: python3 tools/gen-companies.py   (fast; safe to run in the market robot after markets.json is updated)"""
import json, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECTORS = {'Finance', 'Technology', 'Consumer', 'Industrials', 'Utilities', 'Healthcare', 'Energy', 'Materials', 'Real Estate', 'Communication'}
NOT_COMPANY = re.compile(r'\b(ETF|Fund|Trust|Index|iShares|SPDR|Vanguard)\b', re.I)
# Exchange from the ticker suffix (Yahoo Finance conventions). No suffix = a US listing (exchange not recorded in our data).
EXCH = {'DE': 'Xetra', 'F': 'Frankfurt', 'PA': 'Euronext Paris', 'AS': 'Euronext Amsterdam', 'BR': 'Euronext Brussels', 'LS': 'Euronext Lisbon',
        'MI': 'Borsa Italiana', 'MC': 'Bolsa de Madrid', 'L': 'London Stock Exchange', 'SW': 'SIX Swiss Exchange', 'ST': 'Nasdaq Stockholm',
        'HE': 'Nasdaq Helsinki', 'CO': 'Nasdaq Copenhagen', 'OL': 'Oslo Børs', 'VI': 'Vienna', 'WA': 'Warsaw', 'IR': 'Euronext Dublin',
        'SA': 'B3', 'MX': 'BMV', 'TO': 'Toronto Stock Exchange', 'V': 'TSX Venture', 'AX': 'ASX', 'NZ': 'NZX', 'T': 'Tokyo Stock Exchange',
        'HK': 'Hong Kong Exchange', 'SS': 'Shanghai Stock Exchange', 'SZ': 'Shenzhen Stock Exchange', 'KS': 'Korea Exchange', 'KQ': 'KOSDAQ',
        'TW': 'Taiwan Stock Exchange', 'TWO': 'Taipei Exchange', 'SI': 'Singapore Exchange', 'NS': 'NSE India', 'BO': 'BSE India',
        'JO': 'Johannesburg Stock Exchange', 'SR': 'Saudi Exchange', 'QA': 'Qatar Exchange', 'IS': 'Borsa Istanbul', 'TA': 'Tel Aviv Stock Exchange',
        'JK': 'Indonesia Stock Exchange', 'BK': 'Stock Exchange of Thailand', 'KL': 'Bursa Malaysia', 'CA': 'Egyptian Exchange'}
SUFFIX = re.compile(r'\b(incorporated|inc|corp(oration)?|co|company|ltd|limited|plc|ag|sa|se|nv|n\.v|spa|s\.p\.a|ab|asa|oyj|holdings?|group|class [abc]|adr|the)\b\.?', re.I)

def clean(name):
    """'Alphabet Inc' -> 'Alphabet'. Used for grouping listings and for the URL slug."""
    n = SUFFIX.sub(' ', name.replace('&', ' and '))
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s-]', ' ', n)).strip()

TAIL = re.compile(r'[\s,]+(incorporated|inc|corp(oration)?|co|company|ltd|limited|plc|ag|sa|se|nv|n\.v\.?|spa|s\.p\.a\.?|ab|asa|oyj|holdings?|group|class [abc]|adr)\.?$', re.I)
def display(name):
    """'Alphabet Inc' -> 'Alphabet', keeping the company's own spelling (L'Oréal, AT&T)."""
    n = name.strip()
    while TAIL.search(n): n = TAIL.sub('', n).strip()
    return n or name

def slugify(name):
    s = unicodedata.normalize('NFKD', clean(name)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-') or 'company'

def exchange(sym):
    return EXCH.get(sym.rsplit('.', 1)[1]) if '.' in sym else 'US listing'

def main():
    assets = json.load(open(os.path.join(ROOT, 'assets/globe/markets.json')))['assets']
    logos = json.load(open(os.path.join(ROOT, 'assets/globe/logos.json')))
    extra_path = os.path.join(ROOT, 'tools/companies-extra.json')
    extra = json.load(open(extra_path)) if os.path.exists(extra_path) else {}
    groups = {}
    for a in assets:
        if a.get('t') != 'stocks' or a.get('g') in ('Index', 'Country ETF') or NOT_COMPANY.search(a.get('n', '')): continue
        key = (slugify(a['n']), a.get('k'))  # same cleaned name in the same country = same company
        groups.setdefault(key, []).append(a)
    out, used = [], set()
    for (slug, country), ls in sorted(groups.items(), key=lambda kv: kv[0][0]):
        ls.sort(key=lambda a: (('.' in a['s']), -int(a.get('m') or 0)))  # US listing / major first
        sector = next((a['g'] for a in ls if a.get('g') in SECTORS), None)
        name = min((display(a['n']) for a in ls), key=len)  # shortest form: 'Alphabet', not 'Alphabet Inc'
        full = max((a['n'] for a in ls), key=len)
        s = slug if slug not in used else f"{slug}-{(ls[0].get('cc') or 'x')}"
        used.add(s)
        x = extra.get(s, {})
        out.append({
            'slug': s, 'name': x.get('name') or name, 'legal_name': x.get('legal_name') or full,
            'country': country, 'cc': ls[0].get('cc'), 'region': ls[0].get('r'),
            'sector': x.get('sector') or sector, 'industry': x.get('industry'),
            'public': True, 'hq': x.get('hq'), 'website': x.get('website'), 'description': x.get('description'),
            'founded': x.get('founded'), 'story': x.get('story', []), 'related': x.get('related', []), 'videos': x.get('videos', []),
            'sources': x.get('sources', []),
            'logo': next((logos[a['s']].replace('../', 'assets/') for a in ls if a['s'] in logos), None),
            'listings': [{'s': a['s'], 'name': (x.get('listing_names') or {}).get(a['s'], a['n']), 'exchange': (x.get('exchanges') or {}).get(a['s'], exchange(a['s'])), 'cur': a.get('cur'), 'tracked': True} for a in ls]
                        + [dict(l, tracked=False) for l in x.get('more_listings', [])],  # real listings whose price we do not track yet
        })
    data = {'about': 'Investedia company directory. A company is the business; listings are its tradable stocks. Built from markets.json; '
                      'facts beyond name, country, sector and listings come only from tools/companies-extra.json with sources.',
            'count': len(out), 'companies': out}
    for d in ('data', 'docs/data'):
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)
        json.dump(data, open(os.path.join(ROOT, d, 'companies.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    print(len(out), 'companies')

if __name__ == '__main__':
    main()
