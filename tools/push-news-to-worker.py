"""Pushes the newest articles from assets/globe/news-live.json to the Cloudflare Worker (POST /v1/ingest/news), so the site can read fresh news
without waiting for a GitHub commit and a Pages deploy. Safe by design: does nothing without WORKER_URL and NEWS_INGEST_TOKEN, never raises (the old
GitHub path keeps working), never sends an empty list. The token is read from the environment only."""
import json, os, sys, urllib.request, urllib.error
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def payload(path=None, limit=40):
    d = json.load(open(path or os.path.join(ROOT, 'assets/globe/news-live.json')))
    st = sorted(d.get('stories', []), key=lambda s: s['published_at'], reverse=True)[:limit]
    if not st: raise ValueError('no stories to send')
    return {'generated_at': d.get('updated_at'), 'stories': st}

def push(url, token, body, timeout=20):
    req = urllib.request.Request(url.rstrip('/') + '/v1/ingest/news', data=json.dumps(body, ensure_ascii=False).encode(), method='POST',
                                 headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token, 'User-Agent': 'InvestediaRobot/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())

if __name__ == '__main__':
    url, token = os.environ.get('WORKER_URL', '').strip(), os.environ.get('NEWS_INGEST_TOKEN', '').strip()
    if not url or not token: print('worker ingest not configured: skipped'); sys.exit(0)
    try: print('worker ingest:', push(url, token, payload()))
    except Exception as e: print('worker ingest failed (GitHub path unaffected):', str(e)[:200])
    sys.exit(0)
