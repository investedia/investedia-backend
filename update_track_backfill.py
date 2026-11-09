"""Daily-close fallback for the live track record (schema 2). It no longer creates calls from archived articles: implications read
after the fact cannot prove when they were made. It only judges frozen pending calls that the 24-hour recorder missed.
(Earlier versions back-filled calls from archived articles; those rows stay in the ledger marked legacy.)

Old description, kept for reference:

For every archived article (news-archive.json) that implied up or down for an asset with daily history, the call is judged as:
  base = close of the session on the article's own day (never before the article's day), end = close of the NEXT session.
A move of at least 0.3% the implied way = hit, the other way = miss, smaller = no clear move.
These calls are marked basis "daily" and are shown as backfilled. Nothing is picked by result: every article that qualifies is counted,
and the run is idempotent (a call already in news-ledger.json is never added twice).
Only articles at least 72 hours old are taken, so the live recorder keeps first claim on newer ones. It runs after the price recorder in update-market.yml,
so the ledger keeps filling for every article whose asset has daily history. Run the globe-news workflow with backfill_days to bring in older articles.
Usage: python3 update_track_backfill.py
"""
import json, os, sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(ROOT, 'assets', 'globe')
HIST = os.path.join(ROOT, 'assets', 'hist')
FLAT = 0.3
MIN_AGE = timedelta(hours=72)  # younger articles belong to the live price recorder (update_news_track.py), which judges them at 24 h


def load(p, default):
    try:
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def day(ts):
    return datetime.fromtimestamp(ts, timezone.utc).date()


def judge_daily(pub_ts, direction, bars):
    """bars: [[ts, o, h, l, c, v], ...] ascending. Returns (move_pct, result) or None when the next session is not there yet."""
    bars = [b for b in bars if isinstance(b, list) and len(b) >= 5 and b[4]]
    d0 = day(pub_ts)
    base = next((i for i, b in enumerate(bars) if day(b[0]) == d0), None)
    if base is None:  # published on a day without a session (weekend/holiday): use the last session before it, which is before the article
        prior = [i for i, b in enumerate(bars) if day(b[0]) < d0]
        if not prior:
            return None
        base = prior[-1]
        nxt = next((i for i, b in enumerate(bars) if day(b[0]) > d0), None)
        if nxt is None:
            return None
        move = (bars[nxt][4] / bars[base][4] - 1) * 100
    else:
        if base + 1 >= len(bars):
            return None
        move = (bars[base + 1][4] / bars[base][4] - 1) * 100
    res = 'flat' if abs(move) < FLAT else 'hit' if (move > 0) == (direction == 'up') else 'miss'
    return round(move, 2), res


def run(write=True, now=None):
    """Finish frozen calls (schema 2) that the live recorder could not judge in time (price series trimmed after 72 h), on daily closes.
    It never creates calls: predictions come only from the frozen ledger entries, never from story implications read afterwards."""
    now = now or datetime.now(timezone.utc)
    markets = load(os.path.join(G, 'markets.json'), {}).get('assets') or []
    by = {a['s'].upper(): a for a in markets if a.get('s')}
    ledger = load(os.path.join(G, 'news-ledger.json'), {})
    if not isinstance(ledger, dict): return 0, {'calls': []}
    cache, added = {}, 0
    for c in ledger.get('calls', []):
        if c.get('res') != 'pending' or c.get('legacy'):
            continue
        try:
            pub = datetime.fromisoformat(str(c['created']).replace('Z', '+00:00')).timestamp()
        except Exception:
            continue
        if now.timestamp() - pub < MIN_AGE.total_seconds():
            continue
        a = by.get(str(c.get('sym') or '').upper()); site = a and a.get('site')
        if not site: continue
        if site not in cache:
            cache[site] = (load(os.path.join(HIST, f'{site}.json'), {}).get('daily')) or []
        r = judge_daily(pub, c['dir'], cache[site])
        if not r: continue
        c.update(move=r[0], res=r[1], basis='daily', judged=now.strftime('%Y-%m-%dT%H:%M:%SZ'))
        added += 1
    if write and added:
        for base in (G, os.path.join(ROOT, 'docs', 'assets', 'globe')):
            if os.path.isdir(base):
                with open(os.path.join(base, 'news-ledger.json'), 'w', encoding='utf-8') as f:
                    json.dump(ledger, f, separators=(',', ':'))
    return added, ledger


if __name__ == '__main__':
    n, led = run()
    c = led['calls']
    h, m, f = (sum(1 for x in c if x['res'] == k) for k in ('hit', 'miss', 'flat'))
    print(f'backfill: {n} calls added; ledger now {len(c)} calls: {h} hits, {m} misses, {f} no clear move; hit rate {h / (h + m) * 100:.0f}%' if h + m else f'backfill: {n} added')
    sys.exit(0)
