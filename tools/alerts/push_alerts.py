"""Smart alerts: send the newest articles to Supabase, which matches them against users' follows.

Runs after each news robot run. Safe by default:
- without ALERTS_INGEST_TOKEN it only prints what it would send (nothing leaves the runner);
- with the token it calls the database function ingest_alert_articles, which stores at most one alert per user and
  article and sends emails only when the owner has set alert_config.sending = true in Supabase.
The Supabase URL and publishable key are public values (the website uses the same ones); the token is a GitHub secret.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUPABASE_URL = os.environ.get('SUPABASE_URL') or 'https://lfjyoeusblhfpmgwbrhj.supabase.co'
PUBLISHABLE_KEY = os.environ.get('SUPABASE_PUBLISHABLE_KEY') or 'sb_publishable_kqozWiWcKHNqendoiWxsMA_ro7DfTQF'
WINDOW_HOURS = 6        # recent articles only; the database ignores repeats
MAX_ARTICLES = 300


def load(path, default):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def payload(stories, iso, now, hours=WINDOW_HOURS):
    """Turn robot articles into the small shape the database function matches on."""
    out, seen = [], set()
    for s in stories:
        sid = s.get('id')
        if not sid or sid in seen:
            continue
        try:
            t = datetime.fromisoformat(str(s.get('retrieved_at') or s.get('published_at')).replace('Z', '+00:00'))
        except ValueError:
            continue
        if t.tzinfo is None or now - t > timedelta(hours=hours):
            continue
        seen.add(sid)
        loc = s.get('location') or {}
        country = iso.get(loc.get('country') or '', '')
        assets = set()
        for i in (s.get('impacts') or []) + (s.get('entities') or []):
            tk = (i or {}).get('ticker')
            if tk:
                assets.add(str(tk).upper())
        src = s.get('source') or {}
        out.append({'id': sid, 'headline': s.get('headline') or '', 'source': src.get('name') or '', 'url': src.get('url') or '',
                    'published_at': s.get('published_at'), 'country': country, 'assets': sorted(assets),
                    'topic': (s.get('category') or '').lower(), 'importance': s.get('importance')})
    return out[:MAX_ARTICLES]


def send(articles, token, dry_run):
    body = json.dumps({'token': token, 'articles': articles, 'dry_run': dry_run}).encode()
    req = urllib.request.Request(SUPABASE_URL + '/rest/v1/rpc/ingest_alert_articles', data=body, method='POST', headers={
        'apikey': PUBLISHABLE_KEY, 'Authorization': 'Bearer ' + PUBLISHABLE_KEY, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b'{}')


def main(argv=None):
    now = datetime.now(timezone.utc)
    stories = (load(ROOT / 'assets/globe/news-live.json', {}) or {}).get('stories') or []
    iso = load(ROOT / 'assets/globe/iso.json', {})
    articles = payload(stories, iso, now)
    token = os.environ.get('ALERTS_INGEST_TOKEN', '').strip()
    print(f'smart alerts: {len(articles)} recent articles ready')
    if not token:
        print('smart alerts: ALERTS_INGEST_TOKEN not set; nothing sent (owner has not enabled alerts yet).')
        return 0
    try:
        result = send(articles, token, dry_run=os.environ.get('ALERTS_DRY_RUN', '').lower() == 'true')
    except Exception as e:  # alerts must never break the news robot
        print(f'smart alerts: not delivered ({type(e).__name__}); news run unaffected.')
        return 0
    print('smart alerts:', json.dumps(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
