"""Prediction Engine v5, live (research/ENGINE-V5-CANDIDATE.md). Every new story since V5_LIVE_SINCE goes through the v4 pipeline
(extraction, frozen policy, publication-time context); the v5 rule then publishes a Market View only when the price has not already
moved in the call's direction before publication. Records are frozen once (append-only, git-timestamped) and judged once with
outcome-v4. Writes assets/globe/v5-records.json (every record, incl. No View, for coverage) and assets/globe/v5-ledger.json
(published calls in the site's call format).  python3 -m engine.live_v5"""
import json, os, sys, time
from datetime import datetime, timezone
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
import registry, update_globe_news as robot
from engine import extract as X, run as RUN, context as C, prices as PX, shadow as SH

LIVE_SINCE = os.environ.get('V5_LIVE_SINCE', '2026-10-31T17:30:00Z')
RULE = 'v5-not-priced-in'
MAX_STORIES = int(os.environ.get('V5_MAX', 60)); BATCH = 10
G = os.path.join(ROOT, 'assets', 'globe'); DOCS = os.path.join(ROOT, 'docs', 'assets', 'globe')
P = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()
ISO = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def v5(r):
    """The v5 rule on a v4 record: (published?, reason)."""
    if r.get('view_tier') not in ('standard', 'priority'): return False, 'no-v4-view'
    s = (r.get('context') or {}).get('pre_move_sigma')
    if s is None: return False, 'no-pre-move'
    return ((1 if r['decision'] == 'long' else -1) * s <= 0), 'priced-in-before-publication'


def call_of(r):
    """A published v5 record in the site's call format (assets/calls-ui.js)."""
    o = r.get('outcome') or {}
    res = o.get('res') if o.get('res') in ('hit', 'miss', 'flat', 'unresolved') else 'pending'
    m = lambda p: [round(p[0] / 60), p[1]] if p else None
    return {'id': r['article_id'], 'rid': r['id'], 'sym': r['symbol'], 'aid': r['asset_id'], 'name': r['asset_name'], 'dir': 'up' if r['decision'] == 'long' else 'down',
            'conf': 'priority' if r['view_tier'] == 'priority' else None, 'tier': r['view_tier'], 'h': r['headline'], 'created': r['start'], 'start': r['start'],
            'public': r.get('frozen'), 'art': r.get('article_at') or r['start'], 'horizon': r['horizon'], 'ver': 'pe-v5', 'rule': o.get('rule') or 'outcome-v4', 'res': res,
            'move': o.get('move_pct'), 'mkt': o.get('index_move_pct'), 'rel': o.get('relative_move_pct'), 'base': m(o.get('entry')), 'end': m(o.get('exit')),
            'why': r.get('stance_reason'), 'evidence': r.get('evidence'), 'event_type': r['event_type'], 'judged': o.get('judged')}


def main():
    path = os.path.join(G, 'v5-records.json'); led = SH.load(path); led.setdefault('done', []); led['note'] = 'Prediction Engine v5 live records (all, incl. No View)'
    done = set(led['done']); now = time.time()
    arch = {}
    for f in ('news-archive.json', 'news-live.json'):  # the live feed is updated every ~10 min, the archive less often
        try: arch.update({x['id']: x for x in json.load(open(os.path.join(G, f))).get('stories', []) if x.get('id')})
        except Exception: pass
    arch = list(arch.values())
    new = sorted((s for s in arch if s.get('published_at', '') >= LIVE_SINCE and s['id'] not in done and not s.get('demo')), key=lambda s: s['published_at'])[:MAX_STORIES]
    R = registry.get(); IND = json.load(open(os.path.join(DOCS, 'industries.json'))).get('by', {})
    try: cal = json.load(open(os.path.join(DOCS, '..', 'calendar-live.json')))
    except Exception: cal = {}
    def resolve(a):
        ids = R.ids_for_ticker(a['ticker']) if a.get('ticker') else []
        aid = ids[0] if ids else (R.resolve(name=a['name'], ticker=a.get('ticker'), kind='company') or {}).get('id')
        return dict(R.assets[aid], id=aid) if aid and aid in R.assets else None
    BARS, DAILY = {}, {}
    def series(sym, t):
        if sym not in BARS: BARS[sym] = PX.bars(sym, t - 6 * 86400, now) or []
        if sym not in DAILY: DAILY[sym] = PX.daily(sym) or []
        return [b for b in BARS[sym] if b[0] <= t], [d for d in DAILY[sym] if d[0] < t]  # nothing after publication is read
    def context_of(reg, t):
        px = reg.get('px'); b, d = series(px, t)
        ix = PX.bench_of(px) if reg.get('class') in ('equity', 'crypto') else None
        sec = C.sector_etf((IND.get(px) or {}).get('sic')) if ix == '^GSPC' else None
        ib, idd = series(ix, t) if ix else (None, None); sb, sd = series(sec, t) if sec else (None, None)
        f = C.features(t, b, d, ib, idd, sb, sd); f['benchmark'] = {'index': ix, 'sector': sec}
        return f
    seen = {(r.get('event_id'), r.get('asset_id'), r.get('horizon')) for r in led['records'] if r.get('view_tier') in ('standard', 'priority')}
    added = 0
    for i in range(0, len(new), BATCH):
        batch = new[i:i + BATCH]
        try: ex = X.validate(robot.gemini(X.build_prompt(batch, cal)), len(batch))
        except Exception as e: print('batch error', e); continue
        recs = []
        for k, s in enumerate(batch, 1):
            led['done'].append(s['id'])
            if k not in ex: continue
            _, src = X.calendar_expectations(s, cal)
            # the call starts when v5 makes it (now), not at publication: context and entry are taken at call time, so no move before
            # the call is credited and "already priced in" is measured up to the moment of the call
            for r in RUN.records(s, ex[k], resolve, context_of, s.get('cluster') or s['id'], ISO(now), now, seen,
                                 model=robot.status.get('gemini_model'), calendar_sources=src):
                r['article_at'] = s['published_at']; ok, why = v5(r); r['v5'] = 'view' if ok else 'none'
                if not ok: r['v5_reason'] = why
                recs.append(r)
        added += SH.freeze(led, recs, ISO(now))
    judged = SH.judge(led, now)
    calls = [call_of(r) for r in led['records'] if r.get('v5') == 'view']
    out = {'schema': 2, 'engine': 'pe-v5', 'rule': RULE, 'live_since': LIVE_SINCE, 'policy': RUN.P.POLICY_ID, 'prompt': X.PROMPT_ID,
           'outcome_rule': {'id': 'outcome-v4', 'doc': 'research/ENGINE-V4.md', 'publish_rule': 'research/ENGINE-V5-CANDIDATE.md'},
           'updated': ISO(now), 'stories_seen': len(led['done']), 'records': len(led['records']), 'calls': sorted(calls, key=lambda c: c['start'])}
    for d in (G, DOCS):
        if os.path.isdir(d):
            json.dump(led, open(os.path.join(d, 'v5-records.json'), 'w'), separators=(',', ':'))
            json.dump(out, open(os.path.join(d, 'v5-ledger.json'), 'w'), separators=(',', ':'))
    print(f'{len(new)} new stories, {added} records frozen, {judged} judged, {len(calls)} v5 calls')


if __name__ == '__main__':
    main()
