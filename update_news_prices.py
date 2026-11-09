"""Prices for every asset the news mentions that the main price list does not carry.

Reads assets/globe/news-live.json, finds tickers in story impacts that are missing from assets/globe/markets.json,
fetches month/week/day moves from Yahoo Finance and writes assets/globe/news-prices.json (same shape as markets.json assets).
Run after update_globe.py. Failures keep the previous file.
"""
import json, os, time, urllib.parse, urllib.request, concurrent.futures as cf
from datetime import datetime, timezone

G = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'globe')
UA = {'User-Agent': 'Mozilla/5.0'}
CRYPTO = ('-USD',)

MINOR = {'GBp': ('GBP', .01), 'GBX': ('GBP', .01), 'ZAc': ('ZAR', .01), 'USX': ('USD', .01), 'ILA': ('ILS', .01), 'KWF': ('KWD', .001)}
CUR = {}

def fetch(sym):
    for i in range(2):
        try:
            url = f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range=1mo&interval=1d'
            r = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20))['chart']['result'][0]
            c = [x for x in r['indicators']['quote'][0]['close'] if x is not None]
            live = r['meta'].get('regularMarketPrice')
            if live: c[-1] = live
            cur = r['meta'].get('currency')
            if cur in MINOR: cur, k = MINOR[cur]; c = [x * k for x in c]  # pence/cents -> main currency
            if len(c) >= 6 and c[-1]: CUR[sym] = cur; return c
        except Exception:
            time.sleep(1 + i)
    return None

# Sector ETFs (public tickers) so the Markets heatmap has a price move per sector.
SECTORS = {'Technology': 'XLK', 'Semiconductors': 'SMH', 'Energy': 'XLE', 'Banks & Finance': 'XLF', 'Healthcare': 'XLV', 'Consumer & Retail': 'XLY', 'Staples': 'XLP',
           'Industrials': 'XLI', 'Aerospace & Defence': 'ITA', 'Materials & Mining': 'XLB', 'Utilities': 'XLU', 'Real estate': 'XLRE', 'Insurance': 'KIE', 'Crypto': 'BTC-USD', 'Communication': 'XLC', 'Autos': 'CARZ'}


# Majors for the Markets page (crypto board and the three US indices missing from markets.json).
CRYPTOS = {'BTC-USD': 'Bitcoin', 'ETH-USD': 'Ethereum', 'SOL-USD': 'Solana', 'XRP-USD': 'XRP', 'BNB-USD': 'BNB', 'DOGE-USD': 'Dogecoin', 'ADA-USD': 'Cardano', 'TRX-USD': 'TRON',
           'AVAX-USD': 'Avalanche', 'LINK-USD': 'Chainlink', 'DOT-USD': 'Polkadot', 'LTC-USD': 'Litecoin'}
EXTRA_INDICES = {'^NDX': 'Nasdaq 100', '^RUT': 'Russell 2000', '^VIX': 'VIX'}


def fred(series):
    """Daily closes of a FRED series (public domain, no key), oldest first."""
    try:
        txt = urllib.request.urlopen(urllib.request.Request(f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}', headers=UA), timeout=30).read().decode()
        c = [float(r.split(',')[1]) for r in txt.strip().split('\n')[1:] if r.split(',')[1] not in ('', '.')]
        return c[-30:] if len(c) >= 6 else None
    except Exception:
        return None


def wanted_assets(news, mk):
    """Price symbol -> (name, class) for every canonical asset the news resolved to that markets.json does not price.
    Rows without a registry stamp (stories written before the registry) fall back to their raw ticker until the robot stamps them."""
    want = {}
    for s in news:
        for i in (s.get('impacts') or []) + (s.get('entities') or []):
            a = i.get('asset')
            if a and a.get('px') and a['px'] not in mk and a.get('freq') != 'monthly': want.setdefault(a['px'], (a.get('n') or a['px'], a.get('c')))
            elif not a and 'unresolved' not in i:
                t = (i.get('ticker') or '').strip()
                if t and i.get('kind') != 'country' and not alias_known(t, mk): want.setdefault(t, (i.get('name') or t, None))
    return want


def alias_known(t, known):
    return t in known or t.replace('-USD', '') in known or t.replace('=X', '') in known

def main():
    news = json.load(open(os.path.join(G, 'news-live.json'), encoding='utf-8'))['stories']
    mk = {a['s'] for a in json.load(open(os.path.join(G, 'markets.json'), encoding='utf-8'))['assets']}
    classes = {}
    want = {}
    for t, (nm, c) in wanted_assets(news, mk).items(): want[t] = nm; classes[t] = c
    try:  # every still-pending frozen call keeps its price, even after its article has left the live feed
        for c in json.load(open(os.path.join(G, 'news-ledger.json'), encoding='utf-8')).get('calls', []):
            if c.get('res') == 'pending' and not c.get('legacy') and c.get('sym') and c['sym'] not in mk and not c['sym'].startswith('FRED:'):
                want.setdefault(c['sym'], c.get('name') or c['sym'])
    except Exception: pass
    for nm, t in SECTORS.items(): want[t] = nm  # sector ETFs always fetched
    for t, nm in {**CRYPTOS, **EXTRA_INDICES}.items(): want[t] = nm
    path = os.path.join(G, 'news-prices.json')
    old = {}
    try: old = json.load(open(path, encoding='utf-8')).get('assets', {})
    except Exception: pass
    syms = list(want)
    sector_syms = set(SECTORS.values())
    with cf.ThreadPoolExecutor(8) as ex: res = list(ex.map(lambda t: fred(t[5:]) if t.startswith('FRED:') else fetch(t), syms))
    out = {}
    for t, c in zip(syms, res):
        if not c: 
            if t in old: out[t] = old[t]
            continue
        if classes.get(t) == 'rate':  # yields: change in basis points, not percent of the yield
            out[t] = {'s': t, 'n': want[t], 't': 'rate', 'u': 'bp', 'p': round(c[-1], 4), 'd': round((c[-1] - c[-2]) * 100, 1), 'w': round((c[-1] - c[-6]) * 100, 1), 'sp': [round(x, 4) for x in c[-22:]]}
            continue
        out[t] = {'s': t, 'n': want[t], **({'sector': True} if t in sector_syms else {}), **({'g': 'Index', 'cc': 'us'} if t in EXTRA_INDICES else {}), 't': 'crypto' if t.endswith(CRYPTO) else 'fx' if t.endswith('=X') else 'stocks',
                  **({'cur': CUR[t]} if CUR.get(t) else {}), 'p': round(c[-1], 6), 'd': round((c[-1] / c[-2] - 1) * 100, 2), 'w': round((c[-1] / c[-6] - 1) * 100, 2), 'sp': [round(x, 6) for x in c[-22:]]}
    print(f'news prices: {len([t for t in syms if t in out])}/{len(syms)} tickers')
    doc = json.dumps({'asof': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'assets': out}, separators=(',', ':'), ensure_ascii=False)
    for d in (G, G.replace(os.sep + 'assets' + os.sep, os.sep + 'docs' + os.sep + 'assets' + os.sep)):
        if os.path.isdir(d): open(os.path.join(d, 'news-prices.json'), 'w', encoding='utf-8').write(doc)

if __name__ == '__main__':
    main()
