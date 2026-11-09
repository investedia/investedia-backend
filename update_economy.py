"""Country economy snapshot for the Globe News page -> assets/globe/economy.json
Source: World Bank, World Development Indicators (open data, CC BY 4.0, commercial use allowed with attribution). No key needed.
Annual data: each value keeps its year. Run weekly (GitHub Action) or by hand:  python3 update_economy.py"""
import json, os, time, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = [os.path.join(ROOT, 'assets/globe/economy.json'), os.path.join(ROOT, 'docs/assets/globe/economy.json')]
IND = {  # key: (World Bank indicator, label)
    'gdp': ('NY.GDP.MKTP.CD', 'GDP (current US$)'),
    'growth': ('NY.GDP.MKTP.KD.ZG', 'GDP growth (annual %)'),
    'gdppc': ('NY.GDP.PCAP.CD', 'GDP per person (current US$)'),
    'infl': ('FP.CPI.TOTL.ZG', 'Inflation, consumer prices (annual %)'),
    'unemp': ('SL.UEM.TOTL.ZS', 'Unemployment (% of labour force, ILO estimate)'),
    'pop': ('SP.POP.TOTL', 'Population'),
}
YEARS = '2014:%d' % datetime.now(timezone.utc).year


def get(url):
    for t in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'InvestediaEconomy/1.0 (https://investedia.com; info@investedia.com)'})
            return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception as e:
            err = e; time.sleep(4 * (t + 1))
    raise err


countries = {}
for key, (code, _) in IND.items():
    rows = get(f'https://api.worldbank.org/v2/country/all/indicator/{code}?format=json&date={YEARS}&per_page=20000')[1] or []
    for r in rows:
        iso2, v = r['country']['id'], r['value']
        if v is None or len(iso2) != 2 or not r['countryiso3code']:
            continue
        c = countries.setdefault(iso2, {})
        c.setdefault(key, []).append([int(r['date']), round(v, 3 if abs(v) < 1000 else 0)])

for c in countries.values():
    for k in c:
        c[k].sort()
    # keep the full growth history (for the chart); other indicators: latest value only
    for k in list(c):
        if k != 'growth':
            c[k] = c[k][-1]

data = {'asof': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), 'source': 'World Bank, World Development Indicators',
        'source_url': 'https://data.worldbank.org', 'license': 'CC BY 4.0', 'indicators': {k: v[1] for k, v in IND.items()}, 'countries': countries}
for p in OUT:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w').write(json.dumps(data, separators=(',', ':')))
print('economy.json:', len(countries), 'countries')
