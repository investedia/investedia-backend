#!/usr/bin/env python3
"""Investedia Data Centres research pipeline (isolated; does not touch the Globe, Energy or shared sector code).

Stages (each re-runnable; raw pages are cached outside the repo):
  1. discover  - list facility pages from each listed operator's official sitemap / directory
  2. fetch     - polite cached download (robots-allowed paths only, 1 request/second)
  3. parse     - operator adapters extract facts from the official page
  4. normalise - ids, names, country, coordinates class; dedupe campuses / buildings / phases
  5. classify  - attach the listed-parent chain (verified once in parents.json) and evidence tiers
  6. write     - data/datacentres/{candidates,verified,rejected}.json + REPORT.md

Evidence tiers (never auto-promoted):
  extracted      URL found in the operator's official sitemap/directory
  substantiated  official page fetched (HTTP 200) and name + location parsed from it
  listed_rel     substantiated AND operator's listed parent verified -> relationship 'Operator exposure'
  ownership      only with per-facility documentary evidence (none of the current sources provide it)
  release        substantiated + listed_rel + coordinates exact/approximate + facts-only licence basis

Usage: python tools/datacentres/pipeline.py --cache DIR [--operators equinix,digitalrealty,...] [--limit N]
"""
import argparse, datetime as dt, hashlib, html, json, os, re, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data' / 'datacentres'
PARENTS = json.loads((Path(__file__).parent / 'parents.json').read_text(encoding='utf-8'))
UA = 'Mozilla/5.0 (compatible; InvestediaResearch/1.0; facts-only data-centre directory review)'
TODAY = dt.date.today().isoformat()

# ---------------------------------------------------------------- fetch
class Fetcher:
    def __init__(self, cache, delay=1.0):
        self.cache = Path(cache); self.cache.mkdir(parents=True, exist_ok=True); self.delay = delay; self.last = 0; self.log = []
    def get(self, url, retries=2):
        key = self.cache / (hashlib.sha1(url.encode()).hexdigest() + '.html')
        meta = key.with_suffix('.json')
        if key.exists() and meta.exists():
            m = json.loads(meta.read_text()); return m['status'], key.read_text(encoding='utf-8', errors='replace'), m['fetched']
        for attempt in range(retries + 1):
            wait = self.delay - (time.time() - self.last)
            if wait > 0: time.sleep(wait)
            self.last = time.time()
            try:
                req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'en'})
                with urllib.request.urlopen(req, timeout=40) as r:
                    body = r.read().decode('utf-8', errors='replace'); status = r.status
            except urllib.error.HTTPError as e:
                status, body = e.code, ''
                if e.code in (429, 503) and attempt < retries: time.sleep(10 * (attempt + 1)); continue
            except Exception as e:  # network error: record, do not loop forever on a blocked source
                status, body = 0, ''
                if attempt < retries: time.sleep(3); continue
            break
        fetched = dt.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
        if status == 200:
            key.write_text(body, encoding='utf-8'); meta.write_text(json.dumps({'url': url, 'status': status, 'fetched': fetched}))
        self.log.append({'url': url, 'status': status})
        return status, body, fetched

def text_of(s):
    s = re.sub(r'<script.*?</script>|<style.*?</style>', '', s, flags=re.S)
    t = html.unescape(re.sub(r'<[^>]+>', '\n', s)); return re.sub(r'\n\s*\n+', '\n', t)

def locs(xml): return re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', xml)

# ---------------------------------------------------------------- adapters
STATUS_WORDS = [('proposed', r'\b(in planning|planned|proposed)\b'), ('construction', r'\b(under construction|in development|coming soon|opening (in|soon|q[1-4]))\b')]
def status_from(text):
    low = text.lower()
    for st, rx in STATUS_WORDS:
        if re.search(rx, low): return st
    return None

def eqx_discover(f):
    _, xml, _ = f.get('https://www.equinix.com/sitemap-core.xml')
    return sorted({u for u in locs(xml) if re.match(r'https://www\.equinix\.com/data-centers/[^/]+/[^/]+/[^/]+/[^/]+$', u)})

def slug_title(s): return ' '.join(w.capitalize() for w in s.split('-'))

def eqx_parse(url, s):
    parts = url.rstrip('/').split('/')
    country = slug_title(re.sub(r'-colocation$', '', parts[-3])); metro = slug_title(re.sub(r'-data-centers?$', '', parts[-2]))
    code = (re.findall(r'og:title" content="([^"]+)', s) or [parts[-1].upper()])[0].strip()
    t = text_of(s); addr = None
    m = re.search(r'\nAddress\n(.*?)\n(Useful Links|Contact|Speak to sales|Book a tour)', t, re.S)
    if m: addr = ', '.join(x.strip() for x in m.group(1).split('\n') if x.strip())
    lat = re.search(r'latitude\s*=\s*"(-?\d+\.\d+)', s); lng = re.search(r'longitude\s*=\s*"(-?\d+\.\d+)', s)
    head = t[:6000]
    return {'code': code, 'name': f'Equinix {code}', 'country': country, 'metro': metro, 'address': addr,
            'lat': float(lat.group(1)) if lat else None, 'lng': float(lng.group(1)) if lng else None,
            'coord_source': 'operator page map pin' if lat and lng else None, 'status_hint': status_from(head)}

def dlr_discover(f):
    _, xml, _ = f.get('https://www.digitalrealty.com/en-sitemap.xml')
    return sorted({u for u in locs(xml) if re.match(r'https://www\.digitalrealty\.com/data-centers/[^/]+/[^/]+/[^/]+$', u)})

def dlr_parse(url, s):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', s, re.S)
    if not m: return None
    d = json.loads(m.group(1)).get('props', {}).get('pageProps', {}).get('data') or {}
    val = lambda k: (d.get(k) or [{}])[0].get('value') if isinstance(d.get(k), list) and d.get(k) else None
    if val('field_page_type') not in ('Facility', None): return None
    addr = val('field_address_location'); addr = re.sub(r'<[^>]+>', ' ', html.unescape(addr)).strip() if addr else None
    addr = re.sub(r'\s+', ' ', addr) if addr else None
    loc = (d.get('field_facility_location') or [{}])[0].get('name') if d.get('field_facility_location') else None
    country = addr.split(',')[-1].strip() if addr and ',' in addr else None
    lat, lng = val('field_latitude'), val('field_longitude')
    intro = re.sub(r'<[^>]+>', ' ', html.unescape(val('field_intro_location') or ''))
    code = val('field_site_code_location') or d.get('title') or url.rsplit('/', 1)[-1].upper()
    size_m2 = val('field_total_building_size_in_m2')
    return {'code': code, 'name': f'Digital Realty {code}', 'country': country, 'metro': loc or slug_title(url.split('/')[-2]),
            'address': addr, 'lat': float(lat) if lat else None, 'lng': float(lng) if lng else None,
            'coord_source': 'operator page data' if lat and lng else None, 'status_hint': status_from(intro),
            'building_m2': int(size_m2) if size_m2 and size_m2.isdigit() and int(size_m2) > 0 else None}

COR_MARKETS = ['atlanta', 'orlando', 'new-york', 'miami', 'boston', 'chicago', 'los-angeles', 'northern-virginia', 'silicon-valley', 'denver', 'washington-dc']
def cor_discover(f):
    urls = set()
    _, xml, _ = f.get('https://www.coresite.com/sitemap.xml')
    urls |= {u for u in locs(xml) if re.match(r'https://www\.coresite\.com/data-center/[a-z]{2}\d+[a-z]?-[a-z-]+$', u)}
    for mk in COR_MARKETS:
        st, s, _ = f.get(f'https://www.coresite.com/data-center-locations/{mk}')
        urls |= {'https://www.coresite.com' + h for h in re.findall(r'href="(/data-center/[a-z]{2}\d+[a-z]?-[a-z-]+)"', s)}
    return sorted(urls)

US_STATES = {'AL','AK','AZ','AR','CA','CO','CT','DE','DC','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY'}
def cor_parse(url, s):
    slug = url.rsplit('/', 1)[-1]; code = slug.split('-')[0].upper()
    addr = re.findall(r'class="address-text">\s*([^<]+)', s)
    title = (re.findall(r'<title>([^<]+)', s) or [''])[0]
    st = slug.split('-')[-1].upper()
    return {'code': code, 'name': f'CoreSite {code}', 'country': 'United States' if st in US_STATES else None,
            'metro': slug_title('-'.join(slug.split('-')[1:-1])), 'address': re.sub(r'\s+', ' ', addr[0]).strip().title() if addr else None,
            'lat': None, 'lng': None, 'coord_source': None, 'status_hint': status_from(text_of(s)[:5000]), 'page_title': title.strip()}

def nxt_discover(f):
    _, xml, _ = f.get('https://www.nextdc.com/sitemap.xml')
    return sorted({u for u in locs(xml) if re.match(r'https://www\.nextdc\.com/data-centres/[a-z-]+-data-centres/[a-z0-9-]+$', u)})

NXT_COUNTRY = {'kuala-lumpur': 'Malaysia', 'tokyo': 'Japan', 'singapore': 'Singapore', 'auckland': 'New Zealand', 'new-zealand': 'New Zealand'}
def nxt_parse(url, s):
    slug = url.rsplit('/', 1)[-1]; metro_slug = url.split('/')[-2].replace('-data-centres', '')
    code = slug.split('-')[0].upper(); t = text_of(s)
    title = (re.findall(r'og:title" content="([^"]+)', s) or re.findall(r'<title>([^<]+)', s) or [slug])[0]
    sub = re.search(r'Rack Capacity\n([^\n]{2,40})\nLocation', t)
    mw = re.search(r'\n([\d.,]+)\s?MW\nIT Capacity', t)
    # the site navigation marks each facility's stage, e.g. "M4 Port Melbourne (In Development)"
    nav = re.search(re.escape(code) + r'\s[^|\n()]{0,40}\((In Planning|In Development)\)', t)
    status = {'In Planning': 'proposed', 'In Development': 'construction'}.get(nav.group(1)) if nav else None
    return {'code': code, 'name': f'NEXTDC {code}', 'country': NXT_COUNTRY.get(metro_slug, 'Australia'), 'metro': slug_title(metro_slug),
            'address': (sub.group(1).strip() + ', ' + slug_title(metro_slug)) if sub else None, 'locality_only': True,
            'lat': None, 'lng': None, 'coord_source': None, 'status_hint': status, 'capacity_mw': float(mw.group(1).replace(',', '')) if mw else None,
            'page_title': title.strip()}

ADAPTERS = {'equinix': (eqx_discover, eqx_parse), 'digitalrealty': (dlr_discover, dlr_parse), 'coresite': (cor_discover, cor_parse), 'nextdc': (nxt_discover, nxt_parse)}

# ---------------------------------------------------------------- normalise / classify
REGION = {'United States': 'North America', 'Canada': 'North America', 'Mexico': 'Latin America', 'Brazil': 'Latin America', 'Chile': 'Latin America', 'Colombia': 'Latin America', 'Peru': 'Latin America', 'Argentina': 'Latin America',
          'United Arab Emirates': 'Middle East', 'Saudi Arabia': 'Middle East', 'Oman': 'Middle East', 'Israel': 'Middle East', 'Turkey': 'Europe', 'Türkiye': 'Europe', 'Bahrain': 'Middle East', 'Qatar': 'Middle East',
          'South Africa': 'Africa', 'Nigeria': 'Africa', 'Ghana': 'Africa', "Côte D'ivoire": 'Africa', 'Cote D Ivoire': 'Africa', 'Ivory Coast': 'Africa', 'Kenya': 'Africa', 'Mozambique': 'Africa', 'Morocco': 'Africa', 'Egypt': 'Africa',
          'Australia': 'Asia-Pacific', 'New Zealand': 'Asia-Pacific', 'Japan': 'Asia-Pacific', 'Singapore': 'Asia-Pacific', 'Hong Kong': 'Asia-Pacific', 'China': 'Asia-Pacific', 'South Korea': 'Asia-Pacific', 'Korea': 'Asia-Pacific', 'India': 'Asia-Pacific',
          'Indonesia': 'Asia-Pacific', 'Malaysia': 'Asia-Pacific', 'Philippines': 'Asia-Pacific', 'Thailand': 'Asia-Pacific', 'Taiwan': 'Asia-Pacific', 'Vietnam': 'Asia-Pacific'}
COUNTRY_FIX = {'Uk': 'United Kingdom', 'United Kingdom': 'United Kingdom', 'Usa': 'United States', 'Us': 'United States', 'The Netherlands': 'Netherlands', 'Uae': 'United Arab Emirates', 'Republic Of Korea': 'South Korea', 'Korea': 'South Korea', 'Turkiye': 'Türkiye', 'Turkey': 'Türkiye'}
def region_of(c): return REGION.get(c, 'Europe' if c else None)

def norm_country(c):
    if not c: return None
    c = re.sub(r'\s+', ' ', c.strip()).title(); return COUNTRY_FIX.get(c, c)

def coord_class(r):
    if r.get('lat') is not None and r.get('lng') is not None and -90 <= r['lat'] <= 90 and -180 <= r['lng'] <= 180 and not (r['lat'] == 0 and r['lng'] == 0):
        return 'exact'  # operator-published point for this facility
    return 'unknown'

def build(cache, operators, limit=None):
    f = Fetcher(cache); recs, rejected, blocked = [], [], {}
    for op in operators:
        disc, parse = ADAPTERS[op]; par = PARENTS['operators'][op]
        urls = disc(f)[: limit or None]
        print(f'{op}: {len(urls)} facility URLs', flush=True)
        for i, u in enumerate(urls):
            st, s, fetched = f.get(u)
            base = {'id': None, 'operator_key': op, 'source_url': u, 'source_fetched': fetched, 'http_status': st}
            if st != 200:
                rejected.append({**base, 'reason': f'official page not retrievable (HTTP {st})'}); blocked[op] = blocked.get(op, 0) + 1; continue
            try: p = parse(u, s)
            except Exception as e: p = None; err = repr(e)[:120]
            if not p:
                rejected.append({**base, 'reason': 'page is not a single-facility page or could not be parsed'}); continue
            r = {**base, **p}
            r['country'] = norm_country(r.get('country')); r['region'] = region_of(r['country'])
            r['id'] = 'dc-' + op + '-' + re.sub(r'[^a-z0-9]+', '-', (r['code'] or '').lower()).strip('-') + ('-' + re.sub(r'[^a-z0-9]+', '-', (r['metro'] or '').lower())[:20] if op == 'equinix' else '')
            r['coordinates'] = {'lat': r.pop('lat'), 'lng': r.pop('lng'), 'class': coord_class(r) if True else None, 'source': r.pop('coord_source')}
            r['coordinates']['class'] = 'exact' if r['coordinates']['lat'] is not None and r['coordinates']['lng'] is not None else 'unknown'
            r['operator'] = par['operator']; r['developer'] = None
            r['legal_owner'] = None; r['ownership_status'] = 'not established'
            r['listed_parent'] = par['listed_parent']; r['parent_chain'] = par['parent_chain']; r['listing'] = par['listing']
            r['listing_evidence'] = par['listing_evidence']
            r['relationship_type'] = 'Operator exposure'; r['relationship_basis'] = par['relationship_basis']
            r['status'] = r.pop('status_hint') or 'operational (listed in operator directory)'
            r['verified_on'] = TODAY
            r['licence'] = {'basis': 'facts only (name, location, operator, status) re-expressed; source linked; no text or images copied', 'images': 'none collected: neutral placeholder'}
            recs.append(r)
            if (i + 1) % 50 == 0: print(f'  {op} {i+1}/{len(urls)}', flush=True)
    return dedupe(recs), rejected, blocked, f.log

def dedupe(recs):
    """Same operator + same code = same facility (keep first). Different codes at one address = separate buildings of one campus."""
    seen, out = {}, []
    for r in recs:
        k = (r['operator_key'], (r['code'] or '').upper(), (r.get('metro') or '').lower() if r['operator_key'] == 'equinix' else '')
        if k in seen: seen[k].setdefault('duplicate_urls', []).append(r['source_url']); continue
        seen[k] = r; out.append(r)
    by_addr = {}
    for r in out:
        a = re.sub(r'[^a-z0-9]', '', (r.get('address') or '').lower())[:40]
        if a and not r.get('locality_only'): by_addr.setdefault((r['operator_key'], a), []).append(r)
    for grp in by_addr.values():
        if len(grp) > 1:
            cid = 'campus-' + hashlib.sha1(grp[0]['address'].encode()).hexdigest()[:8]
            for r in grp: r['campus'] = {'id': cid, 'buildings_at_address': sorted(x['code'] for x in grp)}
    return out

def tiers(r):
    sub = bool(r.get('name') and (r.get('address') or r.get('metro')) and r.get('country'))
    rel = sub and r.get('relationship_type') == 'Operator exposure' and bool(r.get('listing_evidence'))
    coords_ok = r['coordinates']['class'] in ('exact', 'approximate')
    return {'extracted': True, 'substantiated': sub, 'listed_relationship_verified': rel, 'ownership_verified': False,
            'release_eligible': sub and rel and coords_ok}

def write(recs, rejected, blocked, log, operators):
    OUT.mkdir(parents=True, exist_ok=True)
    for r in recs: r['evidence'] = tiers(r)
    verified = [r for r in recs if r['evidence']['listed_relationship_verified']]
    unresolved = [r for r in recs if not r['evidence']['listed_relationship_verified']]
    meta = {'schema': 'investedia.datacentres.v1', 'generated': TODAY, 'operators': operators, 'parents': 'tools/datacentres/parents.json'}
    (OUT / 'candidates.json').write_text(json.dumps({**meta, 'records': recs}, ensure_ascii=False, indent=1), encoding='utf-8')
    (OUT / 'verified.json').write_text(json.dumps({**meta, 'records': verified}, ensure_ascii=False, indent=1), encoding='utf-8')
    rej = rejected + [{'id': r['id'], 'source_url': r['source_url'], 'reason': 'unresolved: missing country/location or listing evidence'} for r in unresolved]
    rej += [{'operator': v['operator'], 'source_url': v['directory'], 'reason': v['reason']} for v in PARENTS['not_listed'].values()]
    (OUT / 'rejected.json').write_text(json.dumps({**meta, 'records': rej}, ensure_ascii=False, indent=1), encoding='utf-8')
    return verified, unresolved, rej

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--cache', required=True); ap.add_argument('--operators', default=','.join(ADAPTERS)); ap.add_argument('--limit', type=int)
    a = ap.parse_args(); ops = a.operators.split(',')
    recs, rej, blocked, log = build(a.cache, ops, a.limit)
    v, u, rj = write(recs, rej, blocked, log, ops)
    print(json.dumps({'candidates': len(recs), 'verified_listed_relationship': len(v), 'unresolved': len(u), 'rejected_or_blocked': len(rj), 'blocked_pages': blocked}, indent=1))
