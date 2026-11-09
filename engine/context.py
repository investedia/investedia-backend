"""Prediction Engine v4, step 4: market context at publication time (research/ENGINE-V4.md §2). Pure functions over price bars
[(epoch_s, price)] that end at or before the publication time t: nothing after t is ever read.
"""
import math, statistics as st

# US sector ETFs by SEC SIC code prefix (registry industries); non-US equities have no sector benchmark in v4
SECTOR = [(('283', '384', '80'), 'XLV'), (('357', '367', '366', '737', '738', '48'), 'XLK'), (('13', '29', '46'), 'XLE'), (('60', '61', '62', '63', '64', '67'), 'XLF'),
          (('65',), 'XLRE'), (('49',), 'XLU'), (('20', '21'), 'XLP'), (('52', '53', '54', '56', '57', '58', '59', '70', '79', '371', '372'), 'XLY'),
          (('10', '12', '14', '24', '26', '28', '32', '33'), 'XLB'), (('78', '481', '483', '484'), 'XLC'), (('34', '35', '36', '37', '38', '40', '41', '42', '44', '45', '47', '87'), 'XLI')]


def sector_etf(sic):
    s = str(sic or '')
    best = None
    for prefixes, etf in SECTOR:
        for p in prefixes:
            if s.startswith(p) and (best is None or len(p) > best[0]): best = (len(p), etf)
    return best[1] if best else None


def sigma_daily(daily, t, days=20):
    """Standard deviation of daily log returns (%) over the `days` closes before t."""
    px = [c for ts, c in daily if ts < t][-(days + 1):]
    if len(px) < 10: return None
    return st.pstdev([math.log(b / a) for a, b in zip(px, px[1:])]) * 100


def _last(bars, t):
    p = [b for b in bars if b[0] <= t]
    return p[-1] if p else None


def session_start(bars, last, gap_h=2):
    """Start time of the trading session that contains the bar `last` (runs of bars without a gap of gap_h hours)."""
    ts = [b[0] for b in bars if b[0] <= last[0]]
    k = len(ts) - 1
    while k > 0 and ts[k] - ts[k - 1] < gap_h * 3600: k -= 1
    return ts[k] if ts else last[0]


def features(t, bars, daily, index_bars=None, index_daily=None, sector_bars=None, sector_daily=None, gap_h=2):
    """Context at publication time t. Moves are signed %, and in sigma units of the asset's own daily volatility."""
    out = {'t': int(t), 'price': None, 'session': None, 'sigma_daily': sigma_daily(daily or [], t), 'pre_move_pct': None, 'pre_move_sigma': None,
           'move_24h_pct': None, 'trend_5d_pct': None, 'index_pre_pct': None, 'index_pre_sigma': None, 'sector_pre_pct': None, 'sector_pre_sigma': None}
    last = _last(bars or [], t)
    if not last: return out
    out['price'] = last[1]; out['session'] = 'open' if t - last[0] <= 15 * 60 else 'closed'
    s0 = session_start(bars, last)
    prev_close = next((c for ts, c in reversed(daily or []) if ts < s0 - 3600), None)  # the daily close before the latest session began
    def mv(a, b): return None if not a or not b else (b / a - 1) * 100
    d24 = _last(bars, t - 86400); out['move_24h_pct'] = mv(d24[1] if d24 else None, last[1])
    out['pre_move_pct'] = out['move_24h_pct'] if last[0] - s0 > 20 * 3600 else mv(prev_close, last[1])  # 24/7 markets: the last 24 h
    d5 = [c for ts, c in (daily or []) if ts <= t - 5 * 86400]; out['trend_5d_pct'] = mv(d5[-1] if d5 else None, last[1])
    sg = out['sigma_daily']
    if sg and out['pre_move_pct'] is not None: out['pre_move_sigma'] = out['pre_move_pct'] / sg
    for key, b, d in (('index', index_bars, index_daily), ('sector', sector_bars, sector_daily)):
        if not b: continue
        lb = _last(b, t); pc = next((c for ts, c in reversed(d or []) if lb and ts < session_start(b, lb) - 3600), None)
        m = mv(pc, lb[1] if lb else None); s2 = sigma_daily(d or [], t)
        out[key + '_pre_pct'] = m
        if m is not None and s2: out[key + '_pre_sigma'] = m / s2
    for k, v in out.items():
        if isinstance(v, float): out[k] = round(v, 4)
    return out
