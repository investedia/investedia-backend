#!/usr/bin/env python3
"""Up to 10,000 company pages (owner, 25 Nov 2026): the biggest companies on every continent, each with a sector.
Size ranking from Wikidata (employees P1128, then whether listed P414); facts from Wikidata (CC0); descriptions are
Azure gpt-4.1-mini rewrites of each company's English Wikipedia summary (skipped when the page does not clearly match).
Output: out/companies-10k.json + out/report.json (review artifact; the site is updated by a separate reviewed PR)."""
import argparse, importlib.util, json, os, sys, time, urllib.parse
spec = importlib.util.spec_from_file_location('ce', os.path.join(os.path.dirname(__file__), 'company-enrich.py'))
ce = importlib.util.module_from_spec(spec); spec.loader.exec_module(ce)

SPARQL = 'https://query.wikidata.org/sparql'
# Continent share of the target (owner: companies a bit everywhere, biggest first)
QUOTA = {'Asia': .27, 'Europe': .22, 'North America': .18, 'Africa': .11, 'South America': .09, 'Middle East': .07, 'Oceania': .06}
ME = {'Q851', 'Q878', 'Q846', 'Q817', 'Q398', 'Q842', 'Q801', 'Q810', 'Q822', 'Q796', 'Q794', 'Q858', 'Q805', 'Q43', 'Q229', 'Q219060'}
CONT = {'Q48': 'Asia', 'Q46': 'Europe', 'Q49': 'North America', 'Q15': 'Africa', 'Q18': 'South America', 'Q538': 'Oceania', 'Q55643': 'Oceania'}


def sparql(q):
    for a in range(5):
        try:
            u = SPARQL + '?' + urllib.parse.urlencode({'query': q, 'format': 'json'})
            r = ce.get(u)
            if r: return r['results']['bindings']
        except Exception: pass
        time.sleep(5 * (a + 1))
    return []


def countries():
    rows = sparql('SELECT ?c ?cLabel ?cont WHERE { ?c wdt:P31 wd:Q3624078; wdt:P30 ?cont. FILTER NOT EXISTS {?c wdt:P576 ?e} '
                  'SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } }')
    out = {}
    for r in rows:
        q = r['c']['value'].rsplit('/', 1)[-1]; ct = CONT.get(r['cont']['value'].rsplit('/', 1)[-1])
        if not ct: continue
        out[q] = {'name': r['cLabel']['value'], 'cont': 'Middle East' if q in ME else ct}
    return out


def top(cq, n):
    q = f'''SELECT ?co ?coLabel ?emp ?listed ?hqLabel ?coord ?indLabel ?web ?logo ?inc ?tick ?exLabel ?art WHERE {{
      {{ SELECT ?co (MAX(?e) AS ?emp) (SAMPLE(?x) AS ?listed) WHERE {{
          ?co wdt:P17 wd:{cq}; wdt:P31/wdt:P279* wd:Q4830453.
          OPTIONAL {{ ?co wdt:P1128 ?e }} OPTIONAL {{ ?co wdt:P414 ?x }}
          FILTER NOT EXISTS {{ ?co wdt:P576 ?d }}
        }} GROUP BY ?co ORDER BY DESC(BOUND(?x)) DESC(?emp) LIMIT {n} }}
      ?art schema:about ?co; schema:isPartOf <https://en.wikipedia.org/>.
      OPTIONAL {{ ?co wdt:P159 ?hq. OPTIONAL {{ ?hq wdt:P625 ?coord }} }}
      OPTIONAL {{ ?co wdt:P452 ?ind }} OPTIONAL {{ ?co wdt:P856 ?web }} OPTIONAL {{ ?co wdt:P154 ?logo }} OPTIONAL {{ ?co wdt:P571 ?inc }}
      OPTIONAL {{ ?co p:P414 ?st. ?st ps:P414 ?ex. OPTIONAL {{ ?st pq:P249 ?tick }} }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}'''
    seen = {}
    for r in sparql(q):
        k = r['co']['value'].rsplit('/', 1)[-1]
        if k in seen: continue
        v = lambda f: r.get(f, {}).get('value')
        lat = lon = None
        if v('coord'):
            try: lon, lat = map(float, v('coord').split('(')[1].rstrip(')').split())
            except Exception: pass
        seen[k] = {'qid': k, 'name': v('coLabel'), 'employees': int(float(v('emp'))) if v('emp') else None, 'listed': bool(v('listed')),
                   'hq_city': v('hqLabel'), 'lat': lat, 'lon': lon, 'industry': v('indLabel'), 'website': v('web'),
                   'logo_file': urllib.parse.unquote(v('logo').rsplit('/', 1)[-1]) if v('logo') else None, 'founded': (v('inc') or '')[:4] or None,
                   'ticker': v('tick'), 'exchange': v('exLabel'), 'wiki': urllib.parse.unquote(v('art').rsplit('/', 1)[-1]).replace('_', ' ')}
    return list(seen.values())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out'); ap.add_argument('--target', type=int, default=9200)
    ap.add_argument('--max-usd', type=float, default=5.0); ap.add_argument('--per-country', type=int, default=400); a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True); t0 = time.time()
    have = {c['name'].lower() for c in ce.get(ce.SRC)['companies']}
    cs = countries(); print('countries', len(cs), flush=True)
    pool = {k: [] for k in QUOTA}
    for i, (cq, c) in enumerate(cs.items()):
        for x in top(cq, a.per_country):
            if x['name'] and x['name'].lower() not in have and not x['name'].startswith('Q'): x.update(country=c['name'], continent=c['cont']); pool[c['cont']].append(x)
        if i % 20 == 0: print(f'country {i}/{len(cs)}', {k: len(v) for k, v in pool.items()}, flush=True)
        time.sleep(1)
    # pick biggest first per continent: listed, then most employees; countries interleaved so small countries also appear
    picked = []
    for ct, share in QUOTA.items():
        L = sorted(pool[ct], key=lambda x: (not x['listed'], -(x['employees'] or 0)))
        by = {}
        for x in L: by.setdefault(x['country'], []).append(x)
        n, rr = int(a.target * share), []
        while len(rr) < n and any(by.values()):
            for k in list(by):
                if by[k]: rr.append(by[k].pop(0))
                if len(rr) >= n: break
        picked += rr
    print('picked', len(picked), flush=True)
    # Wikipedia summaries, then Azure descriptions + sector
    for i, x in enumerate(picked):
        s = ce.get('https://en.wikipedia.org/api/rest_v1/page/summary/' + urllib.parse.quote(x['wiki'].replace(' ', '_')))
        x['extract'] = (s or {}).get('extract', '')[:1500] if (s or {}).get('type') == 'standard' else ''
        x['wiki_url'] = ((s or {}).get('content_urls') or {}).get('desktop', {}).get('page')
        if i % 200 == 0: print(f'wikipedia {i}/{len(picked)}', flush=True)
        time.sleep(.1)
    az = ce.Azure('gpt-4.1-mini', a.max_usd)
    sysm = ('You write short company descriptions for Investedia, a financial news site. Use ONLY facts in the given Wikipedia summary. '
            'No opinions, no advice, no share prices, no figures that are not in the summary. Reply with JSON only.')
    items = [x for x in picked if x['extract']]; out, skipped = [], 0
    for i in range(0, len(items), 10):
        part = items[i:i + 10]
        pay = [{'slug': x['qid'], 'name': x['name'], 'country': x['country'], 'industry': x['industry'], 'wikipedia_summary': x['extract']} for x in part]
        try:
            r = az.ask(sysm, 'For each company: "match" (true only if the summary is clearly about this same company), "description" (2-3 plain-English sentences, 35-70 words: '
                       'what it does, where it is based, one notable fact from the summary), "sector" (one of: ' + ', '.join(ce.SECTORS) + '). '
                       'JSON: {"results":[{"slug":"...","match":true,"description":"...","sector":"..."}]}\n\n' + json.dumps(pay, ensure_ascii=False))
        except RuntimeError as e: print('stop', e); break
        res = {y.get('slug'): y for y in (r.get('results') or []) if isinstance(y, dict)}
        for x in part:
            y = res.get(x['qid']) or {}
            if not y.get('match') or y.get('sector') not in ce.SECTORS or not y.get('description'): skipped += 1; continue
            x.update(description=y['description'].strip(), sector=y['sector']); x.pop('extract', None)
            x['sources'] = [s for s in [x.get('wiki_url'), 'https://www.wikidata.org/wiki/' + x['qid']] if s]; out.append(x)
        if i % 500 == 0: print(f'written {len(out)} skipped {skipped} ${az.usd:.3f}', flush=True)
    rep = {'target': a.target, 'picked': len(picked), 'written': len(out), 'skipped': skipped, 'cost_usd': round(az.usd, 4), 'minutes': round((time.time() - t0) / 60, 1),
           'by_continent': {k: sum(1 for x in out if x['continent'] == k) for k in QUOTA}, 'by_sector': {k: sum(1 for x in out if x['sector'] == k) for k in ce.SECTORS},
           'with_coords': sum(1 for x in out if x['lat'] is not None), 'with_ticker': sum(1 for x in out if x['ticker']), 'with_logo_file': sum(1 for x in out if x['logo_file'])}
    json.dump({'schema': 'investedia.companies-10k.v1', 'count': len(out), 'companies': out}, open(f'{a.out}/companies-10k.json', 'w'), ensure_ascii=False)
    json.dump(rep, open(f'{a.out}/report.json', 'w'), indent=1); print(json.dumps(rep))


if __name__ == '__main__':
    main()
