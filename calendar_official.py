"""Official US release schedules for the economic calendar (public-domain US government sources).

Sources: BLS release calendar (iCalendar), BEA release schedule (HTML), Federal Reserve FOMC calendar (HTML).
They list dates and times only: no forecasts, no actuals. Used by update_calendar.py to cover the weeks and months
that the weekly ForexFactory feed does not reach, and to keep working if that feed changes its terms.
Each source is fetched separately; one failing never blocks the others."""
import html, re, urllib.request
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo('America/New_York')
# BLS asks automated clients to identify themselves with contact details.
UA = {'User-Agent': 'Investedia calendar updater (info@investedia.com)', 'Accept-Language': 'en-US,en;q=0.9'}
BROWSER_UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'}
MONTHS = {m: i for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'], 1)}

# (title keywords, impact 1-3, keyword that identifies the same release in the ForexFactory feed)
IMPACT = [
    ('Employment Situation', 3, 'Non-Farm'), ('Consumer Price Index', 3, 'CPI'), ('Gross Domestic Product', 3, 'GDP'),
    ('GDP (', 3, 'GDP'), ('Personal Income and Outlays', 3, 'PCE'), ('FOMC', 3, 'FOMC'),
    ('Producer Price Index', 2, 'PPI'), ('Job Openings', 2, 'JOLTS'), ('Employment Cost Index', 2, 'Employment Cost'),
    ('Import and Export Price', 2, 'Import Prices'), ('Productivity and Costs', 2, 'Productivity'),
    ('International Trade in Goods and Services', 2, 'Trade Balance'), ('Real Earnings', 1, 'Real Earnings'),
]
SKIP = ('State', 'County', 'Metropolitan', 'Workplace Injuries', 'Business Employment Dynamics')


def _get(url, headers):
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=40).read().decode('utf-8', 'replace')


def _event(title, local_dt, source):
    imp, key = next(((i, k) for t, i, k in IMPACT if t.lower() in title.lower()), (1, ''))
    return {'t': title, 'c': 'USD', 'at': local_dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'imp': imp, 'type': 'economic',
            'country': 'US', 'actual': '', 'fc': '', 'prev': '', 'src': source, 'ff': key}


def bls(now):
    out = []
    for block in re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', _get('https://www.bls.gov/schedule/news_release/bls.ics', UA), re.S):
        start = re.search(r'DTSTART[^:\n]*:(\d{8}T\d{6})', block)
        title = re.search(r'SUMMARY:(.*)', block)
        if not start or not title: continue
        title = html.unescape(title.group(1).strip().replace('\\,', ','))
        if any(s in title for s in SKIP): continue
        d = datetime.strptime(start.group(1), '%Y%m%dT%H%M%S').replace(tzinfo=ET)
        if now - timedelta(days=30) <= d <= now + timedelta(days=120): out.append(_event(title, d, 'BLS'))
    return out


def _text(fragment):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', fragment))).strip()


def bea(now):
    page = _get('https://www.bea.gov/news/schedule/full', BROWSER_UA)
    rows = re.findall(r'<div class="release-date">(.*?)</div>\s*<small class="text-muted">(.*?)</small>.*?release-title[^>]*>(.*?)</td>', page, re.S)
    year, last_month, out = now.year, 0, []
    # Rows run January to December of one year with no year printed; a drop in month number starts the next year.
    if rows and MONTHS.get(_text(rows[0][0]).split()[0]) == 1 and now.month == 12: year = now.year + 1
    for date, clock, title in rows:
        month_name, day = _text(date).split()[:2]
        month = MONTHS.get(month_name)
        t = re.match(r'(\d{1,2}):(\d{2})\s*([AP]M)', _text(clock))
        if not month or not t: continue
        if month < last_month: year += 1
        last_month = month
        hour = int(t.group(1)) % 12 + (12 if t.group(3) == 'PM' else 0)
        title = _text(title)
        if any(s in title for s in SKIP): continue
        d = datetime(year, month, int(day), hour, int(t.group(2)), tzinfo=ET)
        if now - timedelta(days=30) <= d <= now + timedelta(days=120): out.append(_event(title, d, 'BEA'))
    return out


def fomc(now):
    page = re.sub(r'\s+', ' ', _get('https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm', BROWSER_UA))
    out = []
    for year in {now.year, now.year + 1}:
        i = page.find(f'{year} FOMC Meetings')
        if i < 0: continue
        j = page.find(' FOMC Meetings', i + 20)
        seg = page[i:j if j > 0 else i + 12000]
        for month, days in re.findall(r'<strong>\s*([A-Z][a-z]+(?:/[A-Z][a-z]+)?)\s*</strong>.*?(\d{1,2}(?:-\d{1,2})?)\*?\s*</div>', seg):
            last_month = MONTHS.get(month.split('/')[-1])
            if not last_month: continue
            d = datetime(year, last_month, int(days.split('-')[-1]), 14, 0, tzinfo=ET)
            if now - timedelta(days=30) <= d <= now + timedelta(days=365): out.append(_event('FOMC Statement and Rate Decision', d, 'Federal Reserve'))
    return out


def all_official(now):
    events, failed = [], []
    for name, fn in (('BLS', bls), ('BEA', bea), ('Federal Reserve', fomc)):
        try: events += fn(now)
        except Exception as e: failed.append(f'{name}: {e}')
    return events, failed
