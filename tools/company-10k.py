#!/usr/bin/env python3
"""Up to 10,000 company pages (owner, 25 Nov 2026): the biggest companies on every continent, each with a sector.
Size ranking from Wikidata (employees P1128, then whether listed P414); facts from Wikidata (CC0); descriptions are
Azure gpt-4.1-mini rewrites of each company's English Wikipedia summary (skipped when the page does not clearly match).
Output: out/companies-10k.json + out/report.json (review artifact; the site is updated by a separate reviewed PR)."""
import argparse, importlib.util, json, os, sys, time, urllib.parse
spec = importlib.util.spec_from_file_location('ce', os.path.join(os.path.dirname(__file__), 'company-enrich.py'))
ce = importlib.util.module_from_spec(spec); spec.loader.exec_module(ce)

WD_LIST = 'https://raw.githubusercontent.com/investedia/investedia-frontend/main/assets/globe/companies-wd.json'
REG = {'Asia': 'Asia', 'Europe': 'Europe', 'North America': 'North America', 'Africa': 'Africa', 'South America': 'South America', 'Middle East': 'Middle East', 'Oceania': 'Oceania'}


def entities(qids):
    """Wikidata action API (not the query service): English Wikipedia title, employees, tickers, logo, founded, industry."""
    out = {}
    for i in range(0, len(qids), 50):
        r = ce.get('https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode({'action': 'wbgetentities', 'ids': '|'.join(qids[i:i + 50]),
                   'props': 'claims|sitelinks|labels', 'sitefilter': 'enwiki', 'languages': 'en', 'format': 'json'})) or {}
        for q, e in (r.get('entities') or {}).items():
            cl = e.get('claims') or {}
            emp = None
            for st in cl.get('P1128') or []:
                try: emp = max(emp or 0, int(float(st['mainsnak']['datavalue']['value']['amount'])))
                except Exception: pass
            tick = None
            for st in cl.get('P414') or []:
                for qq in (st.get('qualifiers') or {}).get('P249') or []:
                    tick = tick or (qq.get('datavalue') or {}).get('value')
            out[q] = {'wiki': ((e.get('sitelinks') or {}).get('enwiki') or {}).get('title'), 'employees': emp, 'ticker': tick, 'listed': bool(cl.get('P414')),
                      'logo_file': ce.claim(e, 'P154') if isinstance(ce.claim(e, 'P154'), str) else None,
                      'founded': ((ce.claim(e, 'P571') or {}).get('time') or '')[1:5] or None if isinstance(ce.claim(e, 'P571'), dict) else None,
                      'label': ((e.get('labels') or {}).get('en') or {}).get('value')}
        if i % 1000 == 0: print(f'wikidata {i}/{len(qids)} got {len(out)}', flush=True)
        time.sleep(1)
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out'); ap.add_argument('--target', type=int, default=9200)
    ap.add_argument('--max-usd', type=float, default=5.0); ap.add_argument('--per-country', type=int, default=400); a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True); t0 = time.time()
    have = {c['name'].lower() for c in ce.get(ce.SRC)['companies']}
    base = [c for c in ce.get(WD_LIST)['companies'] if c.get('n') and c['n'].lower() not in have and c.get('r') in REG]
    meta = entities([c['q'] for c in base]); picked = []
    for c in base:
        m = meta.get(c['q']) or {}
        if not m.get('wiki'): continue
        picked.append({'qid': c['q'], 'name': c['n'], 'country': c.get('c'), 'continent': c['r'], 'hq_city': c.get('city'), 'lat': c.get('la'), 'lon': c.get('lo'),
                       'website': c.get('w'), 'industry': c.get('i') or c.get('s'), 'list_sector': c.get('s'), 'wiki': m['wiki'], 'employees': m.get('employees'),
                       'listed': m.get('listed') or bool(c.get('l')), 'ticker': m.get('ticker'), 'logo_file': m.get('logo_file'), 'founded': m.get('founded')})
    picked.sort(key=lambda x: (not x['listed'], -(x['employees'] or 0)))  # biggest first
    picked = picked[:a.target]
    print('picked', len(picked), 'from', len(base), flush=True)
    if not picked: sys.exit('no companies: Wikidata did not answer')
    print('picked', len(picked), flush=True)
    # Wikipedia summaries, then Azure descriptions + sector
    for i, x in enumerate(picked):
        s = ce.get('https://en.wikipedia.org/api/rest_v1/page/summary/' + urllib.parse.quote(x['wiki'].replace(' ', '_')))
        x['extract'] = (s or {}).get('extract', '')[:1500] if (s or {}).get('type') == 'standard' else ''
        x['wiki_url'] = ((s or {}).get('content_urls') or {}).get('desktop', {}).get('page')
        if i % 200 == 0: print(f'wikipedia {i}/{len(picked)}', flush=True)
        time.sleep(.2)
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
        if i % 500 == 0:
            print(f'written {len(out)} skipped {skipped} ${az.usd:.3f}', flush=True)
            json.dump({'partial': True, 'companies': out}, open(f'{a.out}/companies-10k.partial.json', 'w'), ensure_ascii=False)  # survives a later crash
    rep = {'target': a.target, 'picked': len(picked), 'written': len(out), 'skipped': skipped, 'cost_usd': round(az.usd, 4), 'minutes': round((time.time() - t0) / 60, 1),
           'by_continent': {k: sum(1 for x in out if x['continent'] == k) for k in REG}, 'by_sector': {k: sum(1 for x in out if x['sector'] == k) for k in ce.SECTORS},
           'with_coords': sum(1 for x in out if x['lat'] is not None), 'with_ticker': sum(1 for x in out if x['ticker']), 'with_logo_file': sum(1 for x in out if x['logo_file'])}
    json.dump({'schema': 'investedia.companies-10k.v1', 'count': len(out), 'companies': out}, open(f'{a.out}/companies-10k.json', 'w'), ensure_ascii=False)
    json.dump(rep, open(f'{a.out}/report.json', 'w'), indent=1); print(json.dumps(rep))


if __name__ == '__main__':
    main()
