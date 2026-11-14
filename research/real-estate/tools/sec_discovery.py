"""Milestone 2 discovery from SEC EDGAR (US government site; facts only, no document redistribution).

For each listed issuer: resolve CIK, fetch the latest annual report (10-K / 20-F / 40-F), cache it locally
(cache is git-ignored), and extract sentences that describe a hotel/resort/food-led development event.
Output: research/real-estate/discovery/sec-candidates.json with url, sha256, retrieved_at and the sentence locator.
Polite: 1 request/second, declared User-Agent (owner-approved 14 Nov 2026), stops for a host on 403/429.
"""
import hashlib, html, json, re, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'sources' / 'sec' / 'cache'; CACHE.mkdir(parents=True, exist_ok=True)
UA = 'Investedia info@investedia.com'
TICKERS = sys.argv[1:] or ['HST','RHP','PK','PEB','SHO','DRH','XHR','APLE','RLJ','INN','CLDT','BHR','AHT','SVC','H','WYNN','MGM','LVS','VICI','GLPI','CZR','BYD','RRR','PENN','MTN','VAC','HGV','HHH','SPHR','MLCO','HTHT','ATAT','GHG','FUN','SEAS','PRKS','MSGE','JOE','ALEX','FOR','STRS','AMH','SKT','MAC','SPG','FRT','KIM','REG','BXP','VNO','SLG','CTO','PLYA','SOHO','BRX','TRNO','HPP','KRC','ESRT','CDP']
EVENT = re.compile(r'(under construction|broke ground|groundbreaking|expected to open|scheduled to open|anticipated (?:opening|completion)|expected (?:completion|to be completed)|commenced construction|began construction|redevelop|transformational|development pipeline|opened in (?:2024|2025|2026)|completed (?:the )?(?:construction|development|renovation|expansion)|expansion of|new (?:hotel|resort|tower)|pre-development|entitle)', re.I)
ASSET = re.compile(r'(hotel|resort|casino|lodging|convention|food hall|restaurant|dining|entertainment district|mixed-use|mixed use|residences|tower|theme park|arena|waterpark)', re.I)
stopped = set()

def get(url):
    host = url.split('/')[2]
    if host in stopped: return None
    key = CACHE / (hashlib.sha256(url.encode()).hexdigest()[:24] + '.bin')
    if key.exists(): return key.read_bytes()
    time.sleep(1.0)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Encoding': 'identity'}), timeout=60) as r: b = r.read()
    except urllib.error.HTTPError as e:
        if e.code in (403, 429): stopped.add(host); print('STOP', host, e.code, flush=True)
        return None
    except Exception as e:
        print('ERR', url, type(e).__name__, flush=True); return None
    key.write_bytes(b); return b

def text_of(b):
    s = b.decode('utf-8', 'replace')
    s = re.sub(r'(?is)<(script|style|ix:header).*?</\1>', ' ', s)
    s = re.sub(r'(?i)</(p|div|tr|li|h\d)>|<br\s*/?>', '\n', s)
    s = html.unescape(re.sub(r'<[^>]+>', ' ', s))
    return re.sub(r'[ \t\xa0]+', ' ', s)

def main():
    tk = get('https://www.sec.gov/files/company_tickers.json')
    if not tk: sys.exit('SEC refused the ticker list; stopping (no retry).')
    by = {v['ticker']: v for v in json.loads(tk).values()}
    out = []
    for t in TICKERS:
        c = by.get(t)
        if not c: print('no CIK for', t, flush=True); continue
        cik = int(c['cik_str'])
        sub = get(f'https://data.sec.gov/submissions/CIK{cik:010d}.json')
        if not sub: continue
        sub = json.loads(sub); r = sub['filings']['recent']
        idx = next((i for i, f in enumerate(r['form']) if f in ('10-K', '20-F', '40-F')), None)
        if idx is None: print('no annual report', t, flush=True); continue
        acc = r['accessionNumber'][idx].replace('-', ''); doc = r['primaryDocument'][idx]
        url = f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}'
        b = get(url)
        if not b: continue
        sha = hashlib.sha256(b).hexdigest(); n = 0
        for para in text_of(b).split('\n'):
            para = para.strip()
            if not (80 <= len(para) <= 1400) or not EVENT.search(para) or not ASSET.search(para): continue
            for sent in re.split(r'(?<=[.;])\s+(?=[A-Z])', para):
                if EVENT.search(sent) and ASSET.search(sent) and 60 <= len(sent) <= 600:
                    out.append({'ticker': t, 'issuer': sub['name'], 'cik': f'{cik:010d}', 'exchanges': sub.get('exchanges'), 'form': r['form'][idx], 'filed': r['filingDate'][idx], 'period': r['reportDate'][idx], 'url': url, 'sha256': sha, 'retrieved_at': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'sentence': sent.strip()}); n += 1
        print(t, sub['name'], r['form'][idx], r['filingDate'][idx], n, flush=True)
    d = ROOT / 'discovery'; d.mkdir(exist_ok=True)
    (d / 'sec-candidates.json').write_text(json.dumps({'schema': 'investedia.realestate.discovery.sec.v1', 'note': 'Discovery only: sentences are short factual locators for review, not publishable text.', 'issuers': len({o['ticker'] for o in out}), 'sentences': len(out), 'stopped_hosts': sorted(stopped), 'items': out}, ensure_ascii=False, indent=1))
    print('done', len(out), 'sentences', 'stopped:', sorted(stopped))

if __name__ == '__main__': main()
