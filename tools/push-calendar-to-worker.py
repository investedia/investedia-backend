"""Push assets/calendar-live.json to the Worker (POST /v1/ingest/calendar). Uses WORKER_URL + NEWS_INGEST_TOKEN; never prints them."""
import json, os, sys, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def main():
    url = os.environ.get('WORKER_URL', '').strip().rstrip('/'); tok = os.environ.get('NEWS_INGEST_TOKEN', '').strip()
    if not url.startswith('https://') or not tok: print('calendar push: WORKER_URL/NEWS_INGEST_TOKEN missing', file=sys.stderr); return 1
    body = json.loads((ROOT / 'assets/calendar-live.json').read_text())
    req = urllib.request.Request(url + '/v1/ingest/calendar', data=json.dumps(body).encode(), method='POST', headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + tok, 'User-Agent': 'InvestediaRobot/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: res = json.loads(r.read(100000))
    except Exception as e: print('calendar push failed:', type(e).__name__, getattr(e, 'code', ''), file=sys.stderr); return 1
    print(json.dumps({'ok': res.get('ok'), 'count': res.get('count')})); return 0 if res.get('ok') else 1
if __name__ == '__main__': sys.exit(main())
