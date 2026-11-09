"""outcome-v4 (research/ENGINE-V4.md §10): judges a frozen v4 Market View. Entry = first traded price at or after the proven public
time; exit by the View's horizon code (S1/S2 = close of the 1st/2nd full session after entry; '6h'/'24h'/'48h' = first price at or after);
verdict needs max(class floor, 0.5 sigma_h); also stores index, sector and relative moves and the magnitude error. Pure functions.
"""
from engine import policy as P
from engine.magnitude import HORIZON_DAYS

RULE = P.OUTCOME_RULE
GAP = 2 * 3600; MAX_WAIT = 4 * 86400


def _sessions(bars, start_i):
    """Index ranges of trading sessions (runs of bars without a 2 h gap) from start_i on."""
    out, a = [], start_i
    for k in range(start_i + 1, len(bars) + 1):
        if k == len(bars) or bars[k][0] - bars[k - 1][0] >= GAP:
            out.append((a, k - 1, k < len(bars))); a = k
    return out


def exit_bar(bars, entry_i, horizon):
    if horizon.endswith('h'):
        t = bars[entry_i][0] + float(horizon[:-1]) * 3600
        return next((b for b in bars[entry_i:] if b[0] >= t), None)
    n = int(horizon[1:])
    ss = _sessions(bars, entry_i)
    if ss and ss[0][1] - ss[0][0] >= 0 and bars[ss[0][1]][0] - bars[ss[0][0]][0] > 20 * 3600:  # near-24 h market: no session close
        return next((b for b in bars[entry_i:] if b[0] >= bars[entry_i][0] + 86400 * n), None)
    full = ss[1:]  # the session containing the entry is not a full session after entry
    if len(full) < n or not full[n - 1][2]: return None  # that session has not closed yet
    return bars[full[n - 1][1]]


def move_between(bars, t0, t1):
    a = [b for b in bars or [] if b[0] <= t0]; c = [b for b in bars or [] if b[0] <= t1]
    return None if not a or not c or c[-1][0] <= a[-1][0] else round((c[-1][1] / a[-1][1] - 1) * 100, 3)


def judge(view, bars, now, index_bars=None, sector_bars=None):
    """view: frozen record (start, decision, horizon, cls, context.sigma_daily, magnitude). Returns an outcome dict or None (not yet)."""
    t0 = view['start_ts']
    i = next((k for k, b in enumerate(bars or []) if t0 <= b[0] <= t0 + MAX_WAIT), None)
    if i is None:
        return {'res': 'unresolved', 'why': 'no traded price within 4 days', 'rule': RULE} if now > t0 + MAX_WAIT else None
    x = exit_bar(bars, i, view['horizon'])
    limit = bars[i][0] + HORIZON_DAYS.get(view['horizon'], 1) * 86400 + MAX_WAIT
    if not x or x[0] > limit:
        return {'res': 'unresolved', 'why': 'no exit price', 'rule': RULE} if now > limit else None
    e = bars[i]; mv = (x[1] / e[1] - 1) * 100
    thr = P.meaningful(mv, view['cls'], (view.get('context') or {}).get('sigma_daily'), HORIZON_DAYS.get(view['horizon'], 1))
    d = 1 if view['decision'] == 'long' else -1
    res = 'void' if abs(mv) > 50 else 'flat' if abs(mv) < thr else ('hit' if mv * d > 0 else 'miss')
    im, sm = move_between(index_bars, e[0], x[0]), move_between(sector_bars, e[0], x[0])
    bench = sm if sm is not None else im
    mag = (view.get('magnitude') or {}).get('expected_pct')
    return {'res': res, 'rule': RULE, 'entry': [int(e[0]), round(e[1], 6)], 'exit': [int(x[0]), round(x[1], 6)], 'move_pct': round(mv, 3), 'threshold_pct': round(thr, 3),
            'index_move_pct': im, 'sector_move_pct': sm, 'relative_move_pct': None if bench is None else round(mv - bench, 3),
            'relative_res': None if bench is None or abs(mv - bench) < thr else ('hit' if (mv - bench) * d > 0 else 'miss'),
            'magnitude_error_pct': None if mag is None else round(mv - mag, 3)}
