"""Price recorder for "since the news".

Every time the price robot runs, this appends one price point for each asset that a recent story names (story impacts, last 72 hours)
to assets/globe/news-track.json. The site draws the since-the-news chart from it: price when the article appeared, and every run after.
Prices come from files the price robot has just written (markets.json, news-prices.json), so no extra network calls are made.
A point is added only when those files carry a new "asof" time, so a failed price run never adds a fake flat line. Failures keep the previous file.
Format: {"schema":1,"updated":"...","asof":"...","s":{"BZ=F":[[epoch_minute, price], ...]}}

Track record (schema 2): every implication stamped at creation (created_at, version, confidence, horizon, scorable) is copied into
assets/globe/news-ledger.json as a frozen "pending" call the first time a run sees it; later runs judge that frozen copy, never the current
story, so a call cannot be changed after the outcome. Back-filled implications are not scorable. Schema-1 calls are kept and marked legacy.
The call is the direction the article implied (up or down; mixed and unclear are not calls).
Outcome rule (outcome-v3, from 2026-10-31; outcome-v2 verdicts are kept under 'prev'):
- start = the later of created_at and the first time the call is provably public (git history / the news file it was first seen in);
  nothing is ever scored from an earlier time than we can prove.
- entry = the first traded price AT OR AFTER start, from the asset's own exchange session bars (Yahoo 5-minute chart), so no price
  movement that happened before publication (overnight or after-hours gaps) is ever credited; none within 4 days = "unresolved".
- end = the first traded price at least 24 hours after the entry, at most 4 calendar days after that; none by then = "unresolved".
- benchmark: the move of the asset's market index over the same entry -> end window ('mkt'), where a relevant index exists.
"hit" = the asset moved the implied way by at least 0.3%, "miss" = it moved the other way by at least 0.3%, "flat" = it moved less
than 0.3% either way (not counted in the hit rate). The ledger, not the live news file, decides which symbols are still tracked:
every pending call is recorded and judged until it is hit, miss, flat or unresolved, even after its article has left the feed.
The price path around each judged call (exchange bars, never interpolated) is kept permanently in call-paths.json.
Format: {"schema":1,"since":"...","horizon_h":24,"calls":[{"id","h","sym","name","dir","pub":epoch_min,"move":pct,"res":"hit|miss|flat"}]}
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(ROOT, 'assets', 'globe')
KEEP = timedelta(hours=72)
HORIZON = timedelta(hours=24)
MAX_AGE = timedelta(days=4)   # end price must exist within 4 calendar days of start, else the call is unresolved
RULE = 'outcome-v3'
# market index per listing (benchmark: did the call beat simply following the market?)
BENCH_SUFFIX = {'.L': '^FTSE', '.PA': '^FCHI', '.DE': '^GDAXI', '.AS': '^AEX', '.MC': '^IBEX', '.MI': 'FTSEMIB.MI', '.SW': '^SSMI', '.SA': '^BVSP', '.MX': '^MXX',
                '.HK': '^HSI', '.T': '^N225', '.KS': '^KS11', '.TO': '^GSPTSE', '.AX': '^AXJO', '.NS': '^NSEI', '.SS': '000001.SS', '.SZ': '399001.SZ', '.ST': '^OMX', '.HE': '^OMXH25', '.AT': 'GD.AT'}


def bench_of(sym):
    if sym.startswith('^') or sym.endswith(('=F', '=X')) or (len(sym) == 6 and sym.isalpha() and sym.isupper()): return None  # indices, futures, FX: no separate market
    if sym.endswith('-USD'): return None if sym == 'BTC-USD' else 'BTC-USD'
    for suf, ix in BENCH_SUFFIX.items():
        if sym.endswith(suf): return ix
    return None if '.' in sym else '^GSPC'
UA = {'User-Agent': 'Mozilla/5.0'}
MINOR = {'GBp': .01, 'GBX': .01, 'ZAc': .01, 'USX': .01, 'ILA': .01, 'KWF': .001}  # minor units -> main currency, as in update_news_prices
FLAT = 0.3
LATE = timedelta(minutes=90)


def load(name, default):
    try:
        with open(os.path.join(G, name), encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def parse(ts):
    return datetime.fromisoformat(str(ts).replace('Z', '+00:00')).astimezone(timezone.utc)


def resolve(ticker, known):
    """Same aliasing as the site: SYMBOL, SYMBOL-USD, or SYMBOL without =X."""
    t = str(ticker or '').upper()
    for c in (t, t + '-USD', t[:-2] if t.endswith('=X') else None):
        if c and c in known:
            return c
    return None


def resolve_row(row, known):
    """Price symbol of an implication's CANONICAL asset (registry stamp). A row the registry could not resolve is never priced:
    a raw ticker string can name another company (e.g. MC = Moelis & Company, not LVMH). Rows written before the registry
    (no stamp at all) keep the old symbol aliasing so already-frozen behaviour does not change."""
    row = row or {}
    a = row.get('asset')
    if a: return a.get('px') if a.get('px') in known and a.get('freq') != 'monthly' else None
    if 'unresolved' in row: return None
    return resolve(row.get('ticker'), known)


def pending_symbols(ledger, known):
    """Symbols of every frozen call that is still pending: they stay tracked whether or not the article is still in the feed."""
    return {c['sym'] for c in (ledger or {}).get('calls', []) if c.get('res') == 'pending' and not c.get('legacy') and c.get('sym') in known}


def tracked_symbols(stories, known, now):
    out = set()
    for s in stories:
        try:
            if now - parse(s['published_at']) > KEEP:
                continue
        except Exception:
            continue
        for i in s.get('impacts') or []:
            sym = resolve_row(i, known)
            if sym:
                out.add(sym)
    return out


def freeze(stories, series, ledger, now, seen_at=None):
    """Copy every new scorable implication into the ledger as a frozen, pending call, the first time it is seen.
    Only implications stamped at creation (created_at, scorable) qualify; back-filled ones never do. Returns how many were frozen."""
    done = {(c.get('id'), c.get('sym')) for c in ledger.get('calls', [])}
    known, added = set(series), 0
    for s in stories:
        for i in s.get('impacts') or []:
            i = i or {}
            if not i.get('scorable') or not i.get('created_at') or i.get('direction') not in ('up', 'down'):
                continue
            sym = resolve_row(i, known)
            if not sym or (s.get('id'), sym) in done:
                continue
            try:
                created = parse(i['created_at'])
            except Exception:
                continue
            public = max(created, seen_at or now)  # first time this run can prove the call was public (the news file it was read from)
            ledger.setdefault('calls', []).append({'id': s.get('id'), 'sym': sym, **({'aid': i['asset']['id']} if i.get('asset') else {}), 'name': (i.get('name') or sym)[:60], 'dir': i['direction'], 'conf': i.get('confidence'),
                                                   'created': i['created_at'], 'ver': i.get('version'), 'model': i.get('model'), 'horizon': i.get('horizon'),
                                                   'baseline_rule': i.get('baseline_rule'), 'pub': int(created.timestamp() // 60), 'res': 'pending',
                                                   'frozen': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'public': public.strftime('%Y-%m-%dT%H:%M:%SZ'),
                                                   'start': max(created, public).strftime('%Y-%m-%dT%H:%M:%SZ'), 'rule': RULE,
                                                   'cat': s.get('category'), 'art': s.get('published_at'), 'h': str(s.get('headline') or '')[:140]})
            done.add((s.get('id'), sym))
            added += 1
    return added


def bars(sym, t0, t1):
    """Exchange session bars (epoch seconds, close in the main currency) between t0 and t1; None when the source fails."""
    if sym.startswith('FRED:'): return None
    if len(sym) == 6 and sym.isalpha() and sym.isupper(): sym += '=X'  # site FX code (USDBRL) -> exchange symbol (USDBRL=X), as update_globe.ysym
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?period1={int(t0)}&period2={int(t1)}&interval=5m'
    for i in range(2):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20))['chart']['result'][0]
            k = MINOR.get(r['meta'].get('currency'), 1)
            return [(t, c * k) for t, c in zip(r.get('timestamp') or [], r['indicators']['quote'][0].get('close') or []) if c]
        except Exception:
            time.sleep(1 + i)
    return None


def call_start(c):
    return parse(c.get('start') or c['created'])


def judge(series, ledger, now, paths=None, fetch=bars):
    """Judge pending calls from their FROZEN fields (direction, symbol, proven start time), never from the current story.
    Only outcome fields (move, res, base, end, judged, rule) are written; prediction fields are never edited. Returns how many were judged."""
    judged, bench = 0, {}
    for c in ledger.get('calls', []):
        if c.get('res') != 'pending' or c.get('legacy'):
            continue
        t0 = call_start(c).timestamp()
        if now.timestamp() - t0 < HORIZON.total_seconds():
            continue
        pts = fetch(c['sym'], t0 - 6 * 3600, min(now.timestamp(), t0 + 2 * MAX_AGE.total_seconds() + HORIZON.total_seconds()) + 3600)
        if pts is None:  # source failed: retry next run; give up only well after the window has closed
            if now.timestamp() - t0 > 2 * MAX_AGE.total_seconds() + HORIZON.total_seconds() + 2 * 86400:
                c.update(res='unresolved', why='no price data available', rule=RULE, judged=now.strftime('%Y-%m-%dT%H:%M:%SZ')); judged += 1
            continue
        base = next((p for p in pts if t0 <= p[0] <= t0 + MAX_AGE.total_seconds()), None)  # entry: first traded price at or after publication
        if not base:
            if now.timestamp() - t0 > MAX_AGE.total_seconds():
                c.update(res='unresolved', why='no traded price within 4 days of the call', rule=RULE, judged=now.strftime('%Y-%m-%dT%H:%M:%SZ')); judged += 1
            continue
        end = next((p for p in pts if base[0] + HORIZON.total_seconds() <= p[0] <= base[0] + HORIZON.total_seconds() + MAX_AGE.total_seconds()), None)
        if not end:
            if now.timestamp() - base[0] > HORIZON.total_seconds() + MAX_AGE.total_seconds():
                c.update(res='unresolved', why='no traded price within 4 days after the 24-hour horizon', rule=RULE, judged=now.strftime('%Y-%m-%dT%H:%M:%SZ')); judged += 1
            continue
        move = (end[1] / base[1] - 1) * 100
        out = dict(base=[int(base[0] // 60), round(base[1], 6)], end=[int(end[0] // 60), round(end[1], 6)], rule=RULE, judged=now.strftime('%Y-%m-%dT%H:%M:%SZ'))
        if abs(move) > 50:  # a price-series break (unit change, split, wrong instrument), never a real 24 h move
            c.update(res='void', why='price series break (|move| > 50%)', **out)
        else:
            c.update(move=round(move, 2), res='flat' if abs(move) < FLAT else 'hit' if (move > 0) == (c['dir'] == 'up') else 'miss', **out)
            bx = bench_of(c['sym'])
            if bx:  # benchmark: the market index over the same window (prevailing index price at entry and at end)
                bp = bench.get(bx) if bx in bench else bench.setdefault(bx, fetch(bx, now.timestamp() - 20 * 86400, now.timestamp()))
                b0 = [p for p in bp or [] if p[0] <= base[0]]; b1 = [p for p in bp or [] if p[0] <= end[0]]
                if b0 and b1 and b1[-1][0] > b0[-1][0]: c['mkt'] = {'sym': bx, 'move': round((b1[-1][1] / b0[-1][1] - 1) * 100, 2)}
        if paths is not None:  # the verified path around the call, kept permanently (exchange bars only, thinned to ~30-minute steps)
            win = [p for p in pts if t0 - 6 * 3600 <= p[0] <= end[0]]; keep, last = [], None
            for p in win:
                if last is None or p[0] - last >= 1800 or p is win[-1]: keep.append([int(p[0] // 60), round(p[1], 6)]); last = p[0]
            paths[c['id'] + '|' + c['sym']] = {'src': 'exchange bars (Yahoo 5-minute chart)', 'pts': keep}
        judged += 1
    return judged


def update(now=None):
    now = now or datetime.now(timezone.utc)
    markets = load('markets.json', {})
    extra = load('news-prices.json', {})
    prices = {}
    for src in (extra.get('assets') or {}, ):
        for k, a in (src.items() if isinstance(src, dict) else []):
            if isinstance(a, dict) and isinstance(a.get('p'), (int, float)):
                prices[k] = a['p']
    for a in markets.get('assets') or []:
        if isinstance(a, dict) and isinstance(a.get('p'), (int, float)):
            prices[a['s']] = a['p']
    asof_raw = markets.get('asof') or extra.get('asof')
    if not prices or not asof_raw:
        return None, 'no prices'
    asof = parse(asof_raw)
    stories = (load('news-live.json', {}).get('stories')) or []
    ledger = load('news-ledger.json', {})
    syms = tracked_symbols(stories, set(prices), now) | pending_symbols(ledger, set(prices))
    old = load('news-track.json', {})
    series = {k: v for k, v in (old.get('s') or {}).items() if k in syms and isinstance(v, list)}
    minute = int(asof.timestamp() // 60)
    unchanged = old.get('asof') == asof.isoformat() and set(series) == set(syms)
    cutoff = int((now - KEEP).timestamp() // 60)
    added = 0
    for sym in sorted(syms):
        pts = [p for p in series.get(sym, []) if isinstance(p, list) and len(p) == 2 and p[0] >= cutoff]
        if old.get('asof') != asof.isoformat() and (not pts or pts[-1][0] < minute):
            pts.append([minute, float(f'{prices[sym]:.6g}')])
            added += 1
        series[sym] = pts
    out = old if unchanged else {'schema': 1, 'updated': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'asof': asof.isoformat(), 'every_min': 15, 's': series}
    if not isinstance(ledger, dict) or ledger.get('schema') not in (1, 2):
        ledger = {'schema': 2, 'since': now.strftime('%Y-%m-%d'), 'horizon_h': 24, 'calls': []}
    if ledger.get('schema') == 1:  # schema 2: calls are frozen when first seen; schema-1 calls stay as they were (marked legacy)
        for c in ledger.get('calls', []): c.setdefault('legacy', True)
        ledger.update(schema=2, live_since=now.strftime('%Y-%m-%dT%H:%M:%SZ'))
    try: seen_at = parse(load('news-live.json', {}).get('updated_at'))
    except Exception: seen_at = None
    frozen = freeze(stories, series, ledger, now, seen_at)
    paths = load('call-paths.json', {})
    judged = judge(series, ledger, now, paths)  # judging no longer waits for a new price file: closed markets still resolve on schedule
    out['_ledger'] = ledger if frozen or judged else None
    out['_paths'] = paths if judged else None
    if unchanged and not frozen and not judged:
        return out, 'unchanged'
    return out, f'{len(syms)} assets, {added} new points, {frozen} calls frozen, {judged} calls judged'


def main():
    try:
        data, note = update()
        if data is None:
            print('news track:', note); return 0
        ledger, paths = data.pop('_ledger', None), data.pop('_paths', None)
        if paths:
            for d in (G, os.path.join(ROOT, 'docs', 'assets', 'globe')):
                if os.path.isdir(d):
                    pp = os.path.join(d, 'call-paths.json'); pt = pp + '.tmp'
                    with open(pt, 'w', encoding='utf-8') as f:
                        json.dump(paths, f, separators=(',', ':'))
                    os.replace(pt, pp)
        if ledger:
            for d in (G, os.path.join(ROOT, 'docs', 'assets', 'globe')):
                if os.path.isdir(d):
                    lp = os.path.join(d, 'news-ledger.json'); lt = lp + '.tmp'
                    with open(lt, 'w', encoding='utf-8') as f:
                        json.dump(ledger, f, separators=(',', ':'))
                    os.replace(lt, lp)
        path = os.path.join(G, 'news-track.json')
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, separators=(',', ':'))
        os.replace(tmp, path)
        print('news track:', note)
    except Exception as e:
        print('news track failed, keeping the previous file:', type(e).__name__, e)
    return 0


if __name__ == '__main__':
    sys.exit(main())
