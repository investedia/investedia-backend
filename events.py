"""Event metadata archive: one normalised, compact record per published story, kept far longer than the curated news files.
Stored as day files assets/globe/events/YYYY-MM-DD.json (UTC publication day), so a run only rewrites today's (and rarely
yesterday's) file and older days never change. No article text is stored: title, source and link, time, cluster, companies,
canonical assets, implications (direction only), place, category and event family.

Story threads are computed from this archive (not from the 160-story live feed): two events are threaded when they name the same
canonical asset, belong to the same event family and were published 1-96 hours apart (earlier -> later)."""
import json, os, re
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(ROOT, 'assets', 'globe', 'events')
SCHEMA = 'investedia.events/v1'
THREAD_MIN_H, THREAD_MAX_H = 1, 96

# Event family from the headline (deterministic; the editor's event_type is preferred when present)
FAMILIES = [
    ('earnings', r'\b(earnings|results|quarterly|q[1-4]\b|profit|revenue|sales (rose|fell|grew|jumped|slumped)|beats?|miss(es|ed)? (estimates|forecasts)|eps)\b'),
    ('guidance', r'\b(guidance|outlook|forecasts? (raised|cut|lowered)|raises? (its )?forecast|cuts? (its )?forecast|profit warning)\b'),
    ('m&a', r'\b(acqui(re|res|red|sition)|merger|merge|takeover|buyout|to buy|bid for|deal to buy|stake in|divest|spin.?off)\b'),
    ('rates', r'\b(rate (cut|hike|decision)|interest rates?|central bank|fed\b|federal reserve|ecb|bank of (england|japan|canada|korea)|rba|rbi|copom|monetary policy|policy rate|yields?|treasur(y|ies)|bonds?)\b'),
    ('macro-data', r'\b(inflation|cpi|ppi|gdp|jobs report|payrolls|unemployment|pmi|retail sales|trade (deficit|surplus)|industrial production|consumer confidence)\b'),
    ('trade', r'\b(tariffs?|sanctions?|export (ban|controls?)|import duties|trade (war|deal|talks))\b'),
    ('regulation', r'\b(regulat\w*|antitrust|lawsuit|sued|court|fine[ds]?|probe|investigation|approval|approves?|ban(s|ned)?|license)\b'),
    ('energy-supply', r'\b(opec|oil (output|production|supply)|pipeline|refinery|lng|crude (stocks|inventories)|output cuts?)\b'),
    ('capital', r'\b(ipo|listing|share (sale|offering)|buyback|dividend|bond (sale|issue)|raises? \$|funding round|capital raise)\b'),
    ('crypto', r'\b(bitcoin|ethereum|crypto\w*|stablecoins?|token|etf inflows)\b'),
    ('labor', r'\b(workers.? strike|on strike|strike action|walkouts?|layoffs?|job cuts|unions?|buyouts? to|voluntary (exit|redundanc)\w*|staff cuts|headcount)\b'),
    ('geopolitics', r'\b(war|attack|missile|ceasefire|election|coup|protest)\b'),
]
FAMILIES = [(f, re.compile(p, re.I)) for f, p in FAMILIES]

def family(headline, category=None, event_type=None):
    if event_type: return event_type
    for f, rx in FAMILIES:
        if rx.search(headline or ''): return f
    return {'crypto': 'crypto', 'commodities': 'commodity-prices', 'economy': 'macro-data', 'geopolitics': 'geopolitics'}.get(category, 'other')

def record(s):
    """Story -> compact archive record (no article text)."""
    assets = []
    for kind_src, rows in (('impact', s.get('impacts') or []), ('entity', s.get('entities') or [])):
        for r in rows:
            a = r.get('asset') or {}
            row = {k: v for k, v in {'id': a.get('id'), 'n': r.get('name'), 't': r.get('ticker'), 'k': r.get('kind') or 'company', 'src': kind_src,
                                     'dir': r.get('direction'), 'role': r.get('role'), 'rel': r.get('relation'), 'conf': r.get('confidence'),
                                     'why': (r.get('why') or '')[:160] or None, 'u': r.get('unresolved')}.items() if v is not None}
            if kind_src == 'entity' and any(x.get('id') and x.get('id') == row.get('id') for x in assets): continue
            assets.append(row)
    loc = s.get('location') or {}
    return {'id': s['id'], 'at': s['published_at'], 'title': s.get('headline'), 'src': (s.get('source') or {}).get('name'),
            'url': (s.get('source') or {}).get('url'), 'n_src': len(s.get('sources') or []) or 1, 'cluster': s.get('cluster') or s['id'],
            'cat': s.get('category'), 'fam': family(s.get('headline'), s.get('category'), s.get('event_type')), 'imp': s.get('importance'),
            'mm': bool(s.get('market_moving')), 'loc': {k: loc.get(k) for k in ('place', 'country', 'lat', 'lon', 'region')},
            'cos': sorted({a['id'] for a in assets if a.get('id', '').startswith('EQ:')}), 'assets': assets}

def day_path(day): return os.path.join(DIR, f'{day}.json')

def _write(path, obj):
    """Atomic write, mirrored into docs/ (the published copy) when the path is under assets/."""
    text = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    targets = [path]
    rel = os.path.relpath(path, ROOT)
    if rel.startswith('assets' + os.sep) and os.path.isdir(os.path.join(ROOT, 'docs', 'assets')): targets.append(os.path.join(ROOT, 'docs', rel))
    for t in targets:
        os.makedirs(os.path.dirname(t), exist_ok=True)
        with open(t + '.tmp', 'w', encoding='utf-8') as f: f.write(text)
        os.replace(t + '.tmp', t)

def load_days(days=30, now=None, base=None):
    now = now or datetime.now(timezone.utc); out = []
    for k in range(days + 1):
        p = os.path.join(base or DIR, f"{(now - timedelta(days=k)):%Y-%m-%d}.json")
        if os.path.exists(p):
            try: out += json.load(open(p, encoding='utf-8')).get('events', [])
            except Exception: pass
    return out

def upsert(stories, base=None):
    """Adds or refreshes records for these stories in their day files. A record keeps its first resolution unless the new one has more."""
    base = base or DIR; os.makedirs(base, exist_ok=True)
    by_day = {}
    for s in stories: by_day.setdefault(s['published_at'][:10], []).append(record(s))
    changed = 0
    for day, recs in by_day.items():
        p = os.path.join(base, f'{day}.json')
        cur = {}
        if os.path.exists(p):
            try: cur = {e['id']: e for e in json.load(open(p, encoding='utf-8')).get('events', [])}
            except Exception: cur = {}
        for r in recs:
            if cur.get(r['id']) != r: cur[r['id']] = r; changed += 1
        evs = sorted(cur.values(), key=lambda e: e['at'])
        _write(p, {'schema': SCHEMA, 'day': day, 'events': evs})
    return changed

def _t(e): return datetime.fromisoformat(e['at'].replace('Z', '+00:00'))

def threads(events, drawable=lambda a: True, max_per_asset=None):
    """[(earlier, later, asset id)] for events naming the same canonical asset, same family, 1-96 h apart; each event links to the next one only."""
    by = {}
    for e in events:
        if e.get('fam') in (None, 'other'): continue
        for a in e.get('assets', []):
            if a.get('id') and a.get('src', 'impact') == 'impact' and drawable(a): by.setdefault((a['id'], e['fam']), {})[e['id']] = e
    out = []
    for (aid, fam), evs in by.items():
        evs = sorted(evs.values(), key=_t)
        for x, y in zip(evs, evs[1:]):
            h = (_t(y) - _t(x)).total_seconds() / 3600
            if THREAD_MIN_H <= h <= THREAD_MAX_H and x.get('cluster') != y.get('cluster'): out.append((x['id'], y['id'], aid))
    return out


def write_threads(days=30, now=None, base=None, out=None, reg=None):
    """assets/globe/threads.json: story threads over the last `days` days of the archive (both ends' places, the shared asset, the family)."""
    evs = load_days(days, now, base)
    by = {e['id']: e for e in evs}
    verified = (lambda a: reg.verified(a['id'])) if reg else (lambda a: True)  # threads join articles' places, so a non-geographic asset (crypto) threads too
    th = threads(evs, verified)
    pick = lambda e: {'id': e['id'], 'at': e['at'], 'title': e.get('title'), 'la': (e.get('loc') or {}).get('lat'), 'lo': (e.get('loc') or {}).get('lon'),
                      'country': (e.get('loc') or {}).get('country')}
    rows = [{'a': pick(by[x]), 'b': pick(by[y]), 'asset': aid, 'fam': by[x]['fam']} for x, y, aid in th]
    rows.sort(key=lambda r: r['b']['at'], reverse=True)
    path = out or os.path.join(ROOT, 'assets', 'globe', 'threads.json')
    _write(path, {'schema': 'investedia.threads/v1', 'rule': f'same canonical asset + same event family, {THREAD_MIN_H}-{THREAD_MAX_H} h apart, earlier -> later',
                  'days': days, 'threads': rows})
    return len(rows)
