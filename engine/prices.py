"""Price fetchers for v4 context and outcomes (network). Exchange bars come from update_news_track.bars (5-minute, session-aware);
daily closes for volatility from the same source at 1-day resolution."""
import json, urllib.parse, urllib.request
import update_news_track as T


def daily(sym):
    """Daily closes (epoch, close) for the last 6 months; None on failure."""
    if len(sym) == 6 and sym.isalpha() and sym.isupper(): sym += '=X'
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range=6mo&interval=1d'
    for _ in range(2):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=T.UA), timeout=20))['chart']['result'][0]
            return [(t, c) for t, c in zip(r['timestamp'], r['indicators']['quote'][0]['close']) if c]
        except Exception: pass
    return None


bars = T.bars
bench_of = T.bench_of
