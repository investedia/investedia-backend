"""Refresh the world-globe prices (assets/globe/index.html) from Yahoo Finance.

The globe page carries its data inline between /*MK*/ markers; this rewrites price, day and week change and the
one-month sparkline for every asset, keeping names and places. Assets Yahoo fails to return keep their last values.
"""
import json, re, time, urllib.request, urllib.parse, concurrent.futures as cf
from datetime import datetime, timezone

PAGES = ['assets/globe/index.html', 'docs/assets/globe/index.html']
UA = {'User-Agent': 'Mozilla/5.0'}

# Listings whose site symbol is not a Yahoo symbol keep the last known price; their currency follows the country of the listing.
CUR_BY_CC = {'de': 'EUR', 'fr': 'EUR', 'it': 'EUR', 'es': 'EUR', 'nl': 'EUR', 'ie': 'EUR', 'ch': 'CHF', 'gb': 'GBP', 'kr': 'KRW', 'in': 'INR', 'sg': 'SGD', 'au': 'AUD', 'nz': 'NZD', 'za': 'ZAR', 'eg': 'EGP', 'sa': 'SAR', 'qa': 'QAR', 'ae': 'AED', 'pe': 'PEN', 'us': 'USD', 'jp': 'JPY', 'cn': 'CNY', 'hk': 'HKD'}

def registry_listing():
    """Globe symbol -> verified Yahoo symbol for Globe stocks whose symbol is a site code (MC = LVMH -> MC.PA, AIR = Airbus -> AIR.PA).
    Without this, the bare code is priced as whichever US company has those letters (MC = Moelis & Company)."""
    try:
        import os
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'registry.json'), encoding='utf-8') as f: reg = json.load(f)['assets']
        return {a['globe_symbol']: a['px'] for a in reg.values() if a.get('globe_symbol') and a.get('px')}
    except Exception:
        return {}

LISTING = registry_listing()

def ysym(m):
    if m['t'] == 'stocks' and m['s'] in LISTING: return LISTING[m['s']]
    return m['s'] + '=X' if m['t'] == 'fx' else m['s'] + '-USD' if m['t'] == 'crypto' else m['s']

MINOR = {'GBp': ('GBP', .01), 'GBX': ('GBP', .01), 'ZAc': ('ZAR', .01), 'USX': ('USD', .01), 'ILA': ('ILS', .01), 'KWF': ('KWD', .001)}  # pence, cents, agorot, fils

def fetch(sym):
    for i in range(2):
        try:
            url = f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range=1mo&interval=1d'
            r = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20))['chart']['result'][0]
            c = [x for x in r['indicators']['quote'][0]['close'] if x is not None]
            live = r['meta'].get('regularMarketPrice')
            if live: c[-1] = live
            cur = r['meta'].get('currency')
            if cur in MINOR: cur, k = MINOR[cur]; c = [x * k for x in c]  # quoted in minor units: show the main currency (HSBC 1292.6 GBp -> 12.926 GBP)
            if len(c) >= 6 and c[-1]: return c, cur
        except Exception:
            time.sleep(1 + i)
    return None

def main():
    html = open(PAGES[0], encoding='utf-8').read()
    mk = json.loads(re.search(r'/\*MK\*/(.*?)/\*MK\*/', html, re.S).group(1))
    with cf.ThreadPoolExecutor(16) as ex:
        res = list(ex.map(lambda m: fetch(ysym(m)), mk))
    ok = 0
    for m, rc in zip(mk, res):
        if not rc: continue
        c, cur = rc
        if cur: m['cur'] = cur
        sign = -1 if m.get('inv') else 1
        m['p'] = round(c[-1], 6); m['d'] = round(sign * (c[-1] / c[-2] - 1) * 100, 2); m['w'] = round(sign * (c[-1] / c[-6] - 1) * 100, 2)
        m['sp'] = [round(x, 6) for x in c[-22:]]; ok += 1
    for m in mk:
        if m['t'] == 'stocks' and m.get('g') not in ('Index', 'Country ETF') and not m.get('cur') and CUR_BY_CC.get(m.get('cc')): m['cur'] = CUR_BY_CC[m['cc']]
    print(f'globe: {ok}/{len(mk)} assets refreshed')
    if ok < len(mk) * .5: raise SystemExit('Too many failures; keeping the previous data')
    data = json.dumps(mk, separators=(',', ':'), ensure_ascii=False)
    asof = "'" + datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ') + "'"
    for d in ('assets/globe/', 'docs/assets/globe/'):
        open(d + 'markets.json', 'w', encoding='utf-8').write('{"asof":' + json.dumps(asof.strip("'")) + ',"assets":' + data + '}')
    for p in PAGES:
        h = open(p, encoding='utf-8').read()
        h = re.sub(r'/\*MK\*/.*?/\*MK\*/', lambda _: '/*MK*/' + data + '/*MK*/', h, count=1, flags=re.S)
        h = re.sub(r'/\*ASOF\*/.*?/\*ASOF\*/', lambda _: '/*ASOF*/' + asof + '/*ASOF*/', h, count=1)
        open(p, 'w', encoding='utf-8').write(h)

if __name__ == '__main__':
    main()
