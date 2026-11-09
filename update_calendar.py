"""Upcoming economic events + company earnings for the homepage -> assets/calendar-live.json
Sources (free, no key): official US schedules (BLS, BEA, Federal Reserve; see calendar_official.py), the ForexFactory weekly calendar feed
(faireconomy.media, adds forecasts/actuals and non-US events) and the Nasdaq earnings calendar.
Runs with the globe-news workflow. If a source fails, the previous data stays.
Note: both are public feeds without a formal licence; check their terms before using them in a paid product."""
import json, os, sys, time, urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import calendar_fred, calendar_official
OUT = [os.path.join(ROOT, 'assets/calendar-live.json'), os.path.join(ROOT, 'docs/assets/calendar-live.json')]
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36', 'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'en-US,en;q=0.9'}
NOW = datetime.now(timezone.utc)


def get(url):
    for t in range(3):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40))
        except Exception as e:
            err = e; time.sleep(5 * (t + 1))
    raise err


prev = {}
if os.path.exists(OUT[0]):
    try: prev = json.load(open(OUT[0]))
    except Exception: pass
out = {'updated_at': NOW.strftime('%Y-%m-%dT%H:%M:%SZ'), 'events': prev.get('events', []), 'earnings': prev.get('earnings', []),
       'sources': {'events': 'US BLS, BEA and Federal Reserve schedules; ForexFactory calendar', 'earnings': 'Nasdaq earnings calendar'}}

# Economic releases: both weeks, all impacts, retain released values for 30 days.
try:
    ev = []
    for f in ('ff_calendar_thisweek.json', 'ff_calendar_nextweek.json'):
        try: ev += get('https://nfs.faireconomy.media/' + f)
        except Exception: pass
    keep = []
    for e in ev:
        try: d = datetime.fromisoformat(e['date'])
        except Exception: continue
        if d.astimezone(timezone.utc) < NOW - timedelta(days=30) or e.get('impact') not in ('High', 'Medium', 'Low'): continue
        keep.append({'t': e['title'], 'c': e['country'], 'at': d.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                     'imp': {'High': 3, 'Medium': 2, 'Low': 1}[e['impact']], 'type': 'economic',
                     'country': {'USD':'US','EUR':'EU','GBP':'GB','JPY':'JP','CNY':'CN','CHF':'CH','CAD':'CA','AUD':'AU','NZD':'NZ'}.get(e['country'], ''),
                     'actual': e.get('actual') or '', 'fc': e.get('forecast') or '', 'prev': e.get('previous') or ''})
    # Official US schedules fill the weeks ahead (the weekly feed only covers this and next week). Where the feed already lists
    # the same release on the same day, keep the feed row because it carries forecast and actual values.
    official, failed = calendar_official.all_official(NOW)
    for msg in failed: print('official schedule failed:', msg)
    ff_by_day = {}
    for e in keep: ff_by_day.setdefault((e['at'][:10], e['c']), []).append(e['t'].lower())
    for o in official:
        key = o.pop('ff', '').lower()
        if key and any(key in t for t in ff_by_day.get((o['at'][:10], o['c']), [])): continue
        keep.append(o)
    # Optional FRED enrichment (only when the FRED_API_KEY secret exists): fills Actual after BLS/BEA releases and adds date-only releases.
    fred_new, fred_failed, fred_note = calendar_fred.enrich(keep, NOW)
    print(fred_note)
    for msg in fred_failed: print('FRED failed:', msg)
    keep.extend(fred_new)
    if fred_note.startswith('FRED:'): out['sources']['events'] += '; FRED (St. Louis Fed)'
    # Merge by release identity; a later empty feed field must not erase an actual.
    merged = {}
    for e in prev.get('events', []):
        try:
            if datetime.fromisoformat(e['at'].replace('Z', '+00:00')) >= NOW - timedelta(days=30): merged[(e['at'], e['c'], e['t'])] = e
        except (ValueError, KeyError): pass
    for e in keep:
        key = (e['at'], e['c'], e['t'])
        if not e['actual']: e['actual'] = merged.get(key, {}).get('actual', '')
        merged[key] = e
    out['events'] = sorted(merged.values(), key=lambda e: e['at'])
except Exception as e: print('events failed:', e)

# earnings: next 10 days, the largest companies each day
try:
    ern = []
    for i in range(0, 10):
        day = (NOW + timedelta(days=i)).date()
        if day.weekday() > 4: continue
        rows = (get(f'https://api.nasdaq.com/api/calendar/earnings?date={day.isoformat()}').get('data') or {}).get('rows') or []
        def cap(r):
            try: return float(r['marketCap'].replace('$', '').replace(',', ''))
            except Exception: return 0
        for r in sorted(rows, key=cap, reverse=True)[:6]:
            if cap(r) < 20e9: continue
            ern.append({'type': 'earnings', 'c': 'USD', 's': r['symbol'], 'n': r['name'].replace(' (The)', '').replace(', Inc.', '').replace(' Inc.', '').replace(' Corporation', '').replace(' Company', '').replace(' Inc', '').replace(' SE', '').replace(' plc', '').strip(),
                        'date': day.isoformat(), 'when': {'time-pre-market': 'Before open', 'time-after-hours': 'After close'}.get(r.get('time'), ''),
                        'eps': r.get('epsForecast') or '', 'cap': cap(r)})
        time.sleep(1)
    if ern: out['earnings'] = ern[:30]
except Exception as e: print('earnings failed:', e)

for p in OUT:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w').write(json.dumps(out, separators=(',', ':')))
print('calendar:', len(out['events']), 'events,', len(out['earnings']), 'earnings')
