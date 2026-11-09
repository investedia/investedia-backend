"""Shadow check from the command line: Worker /v1/prices versus the static GitHub prices (assets/quotes.js).
Usage: python3 tools/compare-worker-prices.py [worker-base-url]   (default: the investedia-live workers.dev URL)
Prints which endpoints answer, example rows, state/age, the price difference between the two sources and the KV/cron counters."""
import json, re, statistics, sys, urllib.request
BASE = (sys.argv[1] if len(sys.argv) > 1 else 'https://investedia-live.adonaykabeya10.workers.dev').rstrip('/')
def get(p):
    req = urllib.request.Request(BASE + p, headers={'Origin': 'https://investedia.com', 'User-Agent': 'Investedia-check'})
    try:
        with urllib.request.urlopen(req, timeout=15) as r: return r.status, r.headers, json.loads(r.read())
    except urllib.error.HTTPError as e: return e.code, e.headers, None
    except Exception as e: return 0, {}, str(e)
for p in ('/ticker', '/v1/prices', '/v1/prices?group=indices', '/v1/status'):
    s, h, j = get(p); print(f'{p:28} HTTP {s}', '' if s == 200 else f'-> {str(j)[:80]}')
s, h, j = get('/v1/prices')
if s != 200: sys.exit('prices not available yet')
print('meta:', json.dumps(j['meta'])); print('examples:', {k: j['data'][k] for k in list(j['data'])[:4]})
q = json.loads(re.sub(r'^window\.QUOTES=', '', open('assets/quotes.js').read().strip().rstrip(';')))
d = []; miss = 0; big = []
for k, v in q['q'].items():
    r = j['data'].get(k)
    if not r: miss += 1; continue
    x = abs(r[0] / v['p'] - 1) * 100; d.append(x)
    if x > 2: big.append((k, round(x, 1), v['p'], r[0]))
print(f"compared {len(d)}, missing in worker {miss}, median diff {statistics.median(d):.3f}%, p95 {sorted(d)[int(len(d)*.95)]:.3f}%, over 2%: {big[:10]}")
s, h, st = get('/v1/status'); print('status:', json.dumps(st, indent=1))
