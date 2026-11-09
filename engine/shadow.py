"""Prediction Engine v4 shadow ledger (research/ENGINE-V4.md §9): assets/globe/v4-shadow.json. Not shown on the site until v4 is
promoted; published in git so every record's creation time is provable. Records are appended once and never rewritten; judging only
adds an `outcome` object (outcome-v4). No View records are kept too, so coverage and abstention are measurable.
"""
import json, os
from datetime import datetime, timezone
from engine import outcome as OUT, prices as PX

NAME = 'v4-shadow.json'


def load(path):
    try: return json.load(open(path, encoding='utf-8'))
    except Exception: return {'schema': 1, 'note': 'Prediction Engine v4 shadow ledger: forward evidence, not shown on the site', 'records': []}


def freeze(ledger, recs, now_iso):
    """Append new records; an existing id is never touched (a prediction cannot change after it is frozen). Returns how many were added."""
    have = {r['id'] for r in ledger['records']}; n = 0
    for r in recs:
        if r['id'] in have: continue
        ledger['records'].append({**r, 'frozen': now_iso}); have.add(r['id']); n += 1
    return n


def judge(ledger, now_ts, fetch=PX.bars):
    """Judge due Market Views (not No View records) with outcome-v4; adds `outcome` once, never changes it afterwards."""
    cache, n = {}, 0
    def series(sym, t0):
        if not sym: return None
        if sym not in cache: cache[sym] = fetch(sym, t0 - 86400, now_ts)
        return cache[sym]
    for r in ledger['records']:
        if r.get('view_tier') not in ('standard', 'priority') or r.get('outcome'): continue
        if now_ts - r['start_ts'] < 6 * 3600: continue
        b = series(r.get('symbol'), r['start_ts'])
        if b is None: continue
        bm = r.get('benchmark') or {}
        o = OUT.judge(r, b, now_ts, index_bars=series(bm.get('index'), r['start_ts']), sector_bars=series(bm.get('sector'), r['start_ts']))
        if o: r['outcome'] = {**o, 'judged': datetime.fromtimestamp(now_ts, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}; n += 1
    return n


def save(ledger, base_dirs):
    for d in base_dirs:
        if os.path.isdir(d):
            p = os.path.join(d, NAME); tmp = p + '.tmp'
            json.dump(ledger, open(tmp, 'w', encoding='utf-8'), separators=(',', ':')); os.replace(tmp, p)
