#!/usr/bin/env python3
"""Reconcile head-office cities for the 10K company list (owner, 25 Nov 2026: "fix the cities").
For each company: read its English Wikipedia summary, have Azure gpt-4.1-mini return the head-office city the text states
(or null). When it differs from the list's city, use the text's city and take coordinates from that city's Wikipedia page.
Output: out/companies-10k-fixed.json + out/report.json (review artifact). Progress saved every 500."""
import argparse, importlib.util, json, os, time, urllib.parse
spec = importlib.util.spec_from_file_location('ce', os.path.join(os.path.dirname(__file__), 'company-enrich.py'))
ce = importlib.util.module_from_spec(spec); spec.loader.exec_module(ce)


def summary(title):
    s = ce.get('https://en.wikipedia.org/api/rest_v1/page/summary/' + urllib.parse.quote(title.replace(' ', '_')))
    return s if (s or {}).get('type') == 'standard' else None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--inp', default='tools/data/companies-10k.json'); ap.add_argument('--out', default='out')
    ap.add_argument('--max-usd', type=float, default=1.5); a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    cos = json.load(open(a.inp))['companies']; az = ce.Azure('gpt-4.1-mini', a.max_usd); geo = {}
    stats = {'checked': 0, 'same': 0, 'changed': 0, 'no_city_in_text': 0, 'changed_no_coords': 0}; changes = []
    for i in range(0, len(cos), 25):
        part = cos[i:i + 25]; pay = []
        for c in part:
            s = summary(c.get('wiki') or c['name']); time.sleep(.1)
            if s: pay.append({'id': c['qid'], 'name': c['name'], 'country': c['country'], 'summary': s['extract'][:1200]})
        if not pay: continue
        try:
            r = az.ask('You extract facts from text. Reply with JSON only.',
                       'For each company, give the head-office city exactly as the summary states it ("headquartered in X", "based in X"). '
                       'Return only the city name (no country, no street, no building). If the summary does not state it, return null. '
                       'JSON: {"results":[{"id":"...","city":"..."|null}]}\n\n' + json.dumps(pay, ensure_ascii=False))
        except RuntimeError as e: print('stop', e); break
        got = {x.get('id'): x.get('city') for x in (r.get('results') or []) if isinstance(x, dict)}
        for c in part:
            if c['qid'] not in got: continue
            stats['checked'] += 1; city = (got[c['qid']] or '').strip()
            if not city: stats['no_city_in_text'] += 1; continue
            old = (c.get('hq_city') or '').strip()
            if old and (city.lower() in old.lower() or old.lower() in city.lower()): stats['same'] += 1; continue
            key = f'{city}, {c["country"]}'
            if key not in geo:
                g = summary(key) or summary(city); time.sleep(.1)
                co = (g or {}).get('coordinates') or {}
                geo[key] = (co.get('lat'), co.get('lon')) if co.get('lat') is not None else None
            if not geo[key]: stats['changed_no_coords'] += 1; c['hq_city'] = city; changes.append([c['name'], old, city, None]); continue
            c['hq_city'], (c['lat'], c['lon']) = city, geo[key]; c['hq_source'] = 'Wikipedia summary (city), Wikipedia (coordinates)'
            stats['changed'] += 1; changes.append([c['name'], old, city, geo[key]])
        if i % 500 == 0:
            print(i, stats, f'${az.usd:.3f}', flush=True)
            json.dump({'partial': True, 'companies': cos}, open(f'{a.out}/companies-10k-fixed.partial.json', 'w'), ensure_ascii=False)
    stats['cost_usd'] = round(az.usd, 4); stats['sample_changes'] = changes[:80]
    json.dump({'schema': 'investedia.companies-10k.v1', 'count': len(cos), 'companies': cos}, open(f'{a.out}/companies-10k-fixed.json', 'w'), ensure_ascii=False)
    json.dump(stats, open(f'{a.out}/report.json', 'w'), indent=1, ensure_ascii=False); print({k: v for k, v in stats.items() if k != 'sample_changes'})


if __name__ == '__main__':
    main()
