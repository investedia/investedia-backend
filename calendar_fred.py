"""FRED (St. Louis Fed) enrichment for the economic calendar. Optional: runs only when the FRED_API_KEY environment variable is set.

Two jobs, both isolated so a failure never blocks the calendar:
1. release_events(): date-only rows for major US releases that no other source lists (retail sales, housing starts, ...).
2. fill_actuals(): after a BLS or BEA release, fill "Actual" and "Previous" from the matching FRED series. FRED vintages
   ("as known on date X") tell us whether the new number has been published yet, so we never show last month's value as today's.
The key is read from the environment only and never printed; errors are reduced to a status code or an exception name."""
import json, os, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

API = 'https://api.stlouisfed.org/fred/'
UA = {'User-Agent': 'Investedia calendar updater (info@investedia.com)'}

# (fragment of the FRED release name, title shown, impact 1-3, words that identify the same release in other sources)
RELEASES = [
    ('Advance Monthly Sales for Retail', 'US retail sales', 3, ['retail sales']),
    ('Industrial Production', 'US industrial production', 2, ['industrial production']),
    ('New Residential Construction', 'US housing starts', 2, ['housing starts', 'building permits']),
    ('Durable Goods', 'US durable goods orders', 2, ['durable goods']),
    ('New Residential Sales', 'US new home sales', 2, ['new home sales']),
]
# Official-source events whose Actual can be filled: (title fragment, FRED series, calculation, unit shown after the number)
SERIES = [
    ('Consumer Price Index', 'CPIAUCSL', 'pct_m', '% m/m'),
    ('Producer Price Index', 'PPIFIS', 'pct_m', '% m/m'),
    ('Employment Situation', 'PAYEMS', 'diff', 'K jobs'),
    ('GDP (', 'A191RL1Q225SBEA', 'level', '% q/q ann.'),
    ('Personal Income and Outlays', 'PCEPILFE', 'pct_m', '% core PCE m/m'),
]
FILL_SOURCES = ('BLS', 'BEA')


class FredError(Exception):
    pass


def _get(path, params, key):
    """One FRED call. Errors never contain the URL (it holds the key)."""
    q = urllib.parse.urlencode({**params, 'api_key': key, 'file_type': 'json'})
    try:
        with urllib.request.urlopen(urllib.request.Request(API + path + '?' + q, headers=UA), timeout=40) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise FredError(f'{path}: HTTP {e.code}') from None
    except Exception as e:
        raise FredError(f'{path}: {type(e).__name__}') from None


def _day(d):
    return d.strftime('%Y-%m-%d')


def covered(title_words, day, existing):
    """True when another source already lists this release on the same day (US events only)."""
    return any(e.get('c') == 'USD' and e['at'][:10] == day and any(w in e['t'].lower() for w in title_words) for e in existing)


def release_events(now, key, existing):
    rows = _get('releases/dates', {'realtime_start': _day(now), 'realtime_end': _day(now + timedelta(days=120)),
                                  'include_release_dates_with_no_data': 'true', 'order_by': 'release_date', 'sort_order': 'asc', 'limit': 1000}, key)
    out = []
    for r in rows.get('release_dates') or []:
        name, day = str(r.get('release_name', '')), str(r.get('date', ''))
        hit = next((x for x in RELEASES if x[0].lower() in name.lower()), None)
        if not hit or len(day) != 10 or covered(hit[3], day, existing + out): continue
        out.append({'t': hit[1], 'c': 'USD', 'at': day + 'T12:00:00Z', 'imp': hit[2], 'type': 'economic', 'country': 'US', 'actual': '', 'fc': '', 'prev': '',
                    'src': 'FRED', 'dateOnly': True, 'when': 'Time not published'})
    # FRED can list several dates for one release in a month (catch-up or revision dates). Keep the earliest per title and month
    # rather than show dates we cannot confirm against the agency's own schedule.
    first = {}
    for e in sorted(out, key=lambda e: e['at']): first.setdefault((e['t'], e['at'][:7]), e)
    return sorted(first.values(), key=lambda e: e['at'])


def _obs(series, as_of, key):
    """Last 3 observations of a series as FRED knew them on `as_of`, newest first. Missing values (".") are dropped."""
    data = _get('series/observations', {'series_id': series, 'realtime_start': as_of, 'realtime_end': as_of, 'sort_order': 'desc', 'limit': 3, 'observation_start': (datetime.fromisoformat(as_of) - timedelta(days=800)).strftime('%Y-%m-%d')}, key)
    rows = []
    for o in data.get('observations') or []:
        try: rows.append((o['date'], float(o['value'])))
        except (KeyError, ValueError, TypeError): continue
    return rows


def _calc(kind, rows):
    """(actual, previous) from newest-first observations, or None when there are too few."""
    v = [x[1] for x in rows]
    if kind == 'level': return (v[0], v[1]) if len(v) >= 2 else None
    if kind == 'diff': return (v[0] - v[1], v[1] - v[2]) if len(v) >= 3 else None
    if kind == 'pct_m': return ((v[0] / v[1] - 1) * 100, (v[1] / v[2] - 1) * 100) if len(v) >= 3 and v[1] and v[2] else None
    return None


def _fmt(kind, x, unit):
    if kind == 'diff': return f'{x:+,.0f}{unit}'
    return f'{x:.1f}{unit}'


def fill_actuals(events, now, key):
    """Fill actual/prev on released BLS/BEA events. Returns (number filled, failure messages)."""
    filled, failed = 0, []
    for e in events:
        if e.get('actual') or e.get('src') not in FILL_SOURCES: continue
        at = datetime.fromisoformat(e['at'].replace('Z', '+00:00'))
        if not (timedelta(0) <= now - at <= timedelta(days=5)): continue
        m = next((s for s in SERIES if s[0].lower() in e['t'].lower()), None)
        if not m: continue
        try:
            day, before = _day(at), _day(at - timedelta(days=1))
            new, old = _obs(m[1], day, key), _obs(m[1], before, key)
            # Only when the latest observation changed between yesterday's and today's vintage has the new number been published.
            if not new or (old and old[0][0] == new[0][0]): continue
            res = _calc(m[2], new)
            if not res: continue
            e['actual'], e['prev'] = _fmt(m[2], res[0], m[3]), (e.get('prev') or _fmt(m[2], res[1], m[3]))
            filled += 1
        except FredError as err:
            failed.append(str(err))
    return filled, failed


def enrich(events, now, key=None):
    """Mutates `events` (fills actuals) and returns (new date-only events, failure messages, one-line note)."""
    key = key if key is not None else os.environ.get('FRED_API_KEY', '')
    if not key: return [], [], 'FRED_API_KEY not set; FRED skipped'
    failed, new = [], []
    try: new = release_events(now, key, events)
    except FredError as err: failed.append(str(err))
    n, f = fill_actuals(events, now, key)
    return new, failed + f, f'FRED: {len(new)} releases added, {n} actuals filled'
