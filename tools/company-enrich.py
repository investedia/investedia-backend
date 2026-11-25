#!/usr/bin/env python3
"""Company page enrichment (owner, 25 Nov 2026): description, sector, city, legal name, website, founded and logo file
for Investedia company pages, from Wikipedia and Wikidata. Azure OpenAI only rewrites the sourced Wikipedia summary in
plain English and picks a sector; if the source is not clearly about the company, nothing is written.
Output: out/companies-enrich.json + out/report.json (review artifact). Stdlib only; secrets never printed."""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request, urllib.error

UA = 'InvestediaCompanyBot/1.0 (https://investedia.com)'
SECTORS = ['Finance', 'Technology', 'Industrials', 'Consumer', 'Healthcare', 'Energy', 'Materials', 'Communication', 'Real Estate', 'Utilities']
PRICES = {'gpt-4.1-mini': (0.40, 1.60), 'gpt-4.1-nano': (0.10, 0.40)}
SRC = 'https://raw.githubusercontent.com/investedia/investedia-frontend/main/data/companies.json'


def get(url, tries=4):
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            time.sleep(2 * 2 ** a)
        except Exception: time.sleep(2 * 2 ** a)
    return None


def words(s): return {w for w in re.findall(r'[a-z0-9]+', (s or '').lower()) if w not in {'the', 'of', 'and', 'group', 'holdings', 'holding', 'plc', 'inc', 'ltd', 'limited', 'sa', 'ag', 'corp', 'corporation', 'company', 'co', 'nv', 'se', 'spa', 'asa', 'ab', 'oyj', 'bhd', 'tbk', 'pt'}}


def wiki(c):
    """Find the English Wikipedia page for one company; return summary dict or None."""
    names = [n for n in [c.get('legal_name'), c.get('name')] if n]
    for n in names:
        q = urllib.parse.urlencode({'action': 'query', 'list': 'search', 'srsearch': f'{n} company {c.get("country") or ""}', 'srlimit': 3, 'format': 'json'})
        r = get('https://en.wikipedia.org/w/api.php?' + q) or {}
        for hit in (r.get('query') or {}).get('search') or []:
            t = hit['title']
            if not (words(t) & words(n)): continue
            s = get('https://en.wikipedia.org/api/rest_v1/page/summary/' + urllib.parse.quote(t.replace(' ', '_')))
            if s and s.get('type') == 'standard' and s.get('extract'):
                return {'title': s['title'], 'url': (s.get('content_urls') or {}).get('desktop', {}).get('page'), 'extract': s['extract'][:1800],
                        'short': s.get('description') or '', 'qid': s.get('wikibase_item')}
        time.sleep(.2)
    return None


def claim(ent, p):
    for st in (ent.get('claims') or {}).get(p) or []:
        v = ((st.get('mainsnak') or {}).get('datavalue') or {}).get('value')
        if v is not None: return v
    return None


def wikidata(qids):
    out, need = {}, set()
    for i in range(0, len(qids), 40):
        r = get('https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode({'action': 'wbgetentities', 'ids': '|'.join(qids[i:i + 40]), 'props': 'claims|labels', 'languages': 'en', 'format': 'json'})) or {}
        for q, e in (r.get('entities') or {}).items():
            hq, ind = claim(e, 'P159'), claim(e, 'P452')
            inc = claim(e, 'P571'); logo = claim(e, 'P154'); web = claim(e, 'P856')
            d = {'hq_q': hq.get('id') if isinstance(hq, dict) else None, 'industry_q': ind.get('id') if isinstance(ind, dict) else None,
                 'founded': (inc or {}).get('time', '')[1:5] if isinstance(inc, dict) else None,
                 'logo_file': logo if isinstance(logo, str) else None, 'website': web if isinstance(web, str) else None}
            out[q] = d; need |= {d['hq_q'], d['industry_q']} - {None}
        time.sleep(.3)
    labels, need = {}, list(need)
    for i in range(0, len(need), 50):
        r = get('https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode({'action': 'wbgetentities', 'ids': '|'.join(need[i:i + 50]), 'props': 'labels', 'languages': 'en', 'format': 'json'})) or {}
        for q, e in (r.get('entities') or {}).items(): labels[q] = ((e.get('labels') or {}).get('en') or {}).get('value')
        time.sleep(.3)
    for d in out.values():
        d['hq_city'] = labels.get(d.pop('hq_q')); d['industry'] = labels.get(d.pop('industry_q'))
    return out


class Azure:
    def __init__(s, model, max_usd):
        ep = '/'.join(os.environ['AZURE_OPENAI_ENDPOINT'].strip().split('/')[:3])
        s.url = f'{ep}/openai/deployments/{os.environ.get("AZURE_DEPLOYMENT", model)}/chat/completions?api-version=2024-10-21'
        s.key, s.model, s.max = os.environ['AZURE_OPENAI_API_KEY'], model, max_usd; s.tin = s.tout = 0

    @property
    def usd(s): pi, po = PRICES.get(s.model, PRICES['gpt-4.1-mini']); return (s.tin * pi + s.tout * po) / 1e6

    def ask(s, sysm, user):
        if s.usd > s.max - 0.05: raise RuntimeError('budget_reached')
        body = json.dumps({'messages': [{'role': 'system', 'content': sysm}, {'role': 'user', 'content': user}], 'max_tokens': 6000, 'temperature': 0.1,
                           'response_format': {'type': 'json_object'}}).encode()
        for a in range(5):
            try:
                req = urllib.request.Request(s.url, data=body, method='POST', headers={'Content-Type': 'application/json', 'api-key': s.key})
                with urllib.request.urlopen(req, timeout=180) as r: res = json.loads(r.read().decode()); break
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and a < 4: time.sleep(3 * 2 ** a); continue
                print('azure error', e.code, e.read()[:300].decode('utf-8', 'replace')); raise RuntimeError('azure_http_%d' % e.code)
            except Exception:
                if a < 4: time.sleep(3 * 2 ** a); continue
                raise
        u = res.get('usage') or {}; s.tin += u.get('prompt_tokens', 0); s.tout += u.get('completion_tokens', 0)
        try: return json.loads(res['choices'][0]['message']['content'])
        except Exception: return {}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out'); ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--max-usd', type=float, default=3.0); ap.add_argument('--model', default='gpt-4.1-mini'); a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    cos = get(SRC)['companies']; cos = cos[:a.limit] if a.limit else cos
    rep = {'companies': len(cos), 'notice': 'Descriptions rewrite Wikipedia summaries; facts from Wikidata. Not investment advice.'}
    found = {}
    for i, c in enumerate(cos):
        w = wiki(c)
        if w: found[c['slug']] = w
        if i % 50 == 0: print(f'wikipedia {i}/{len(cos)} found {len(found)}', flush=True)
        time.sleep(.15)
    wd = wikidata(sorted({w['qid'] for w in found.values() if w.get('qid')}))
    az = Azure(a.model, a.max_usd)
    sysm = ('You write short company descriptions for Investedia, a financial news site. Use ONLY facts in the given Wikipedia summary. '
            'No opinions, no advice, no share prices, no figures that are not in the summary. Reply with JSON only.')
    out, skipped = [], []
    items = [c for c in cos if c['slug'] in found]
    for i in range(0, len(items), 10):
        part = items[i:i + 10]
        payload = [{'slug': c['slug'], 'name': c['name'], 'country': c.get('country'), 'tickers': [l.get('s') for l in c.get('listings') or []][:2],
                    'wikipedia_title': found[c['slug']]['title'], 'wikipedia_summary': found[c['slug']]['extract'],
                    'industry': (wd.get(found[c['slug']].get('qid')) or {}).get('industry')} for c in part]
        try:
            r = az.ask(sysm, 'For each company: "match" (true only if the Wikipedia summary is clearly about this same company, checking name, country and business), '
                       '"description" (2-3 plain-English sentences, 35-70 words: what the company does, where it is based, and one notable fact from the summary), '
                       '"sector" (one of: ' + ', '.join(SECTORS) + '). JSON: {"results":[{"slug":"...","match":true,"description":"...","sector":"..."}]}\n\n' + json.dumps(payload, ensure_ascii=False))
        except RuntimeError as e: rep['stop'] = str(e); break
        res = {x.get('slug'): x for x in r.get('results') or []}
        for c in part:
            x = res.get(c['slug']) or {}; w = found[c['slug']]; d = wd.get(w.get('qid')) or {}
            if not x.get('match') or not x.get('description') or x.get('sector') not in SECTORS: skipped.append(c['slug']); continue
            out.append({'slug': c['slug'], 'name': c['name'], 'description': x['description'].strip(), 'sector': x['sector'], 'hq_city': d.get('hq_city'),
                        'industry': d.get('industry'), 'founded': d.get('founded'), 'website': d.get('website'), 'logo_file': d.get('logo_file'),
                        'sources': [s for s in [w.get('url'), w.get('qid') and 'https://www.wikidata.org/wiki/' + w['qid']] if s]})
        print(f'written {len(out)} skipped {len(skipped)} ${az.usd:.3f}', flush=True)
    rep.update(wikipedia_found=len(found), written=len(out), skipped=len(skipped), skipped_slugs=skipped[:200], not_found=[c['slug'] for c in cos if c['slug'] not in found][:300],
               with_city=sum(1 for x in out if x['hq_city']), with_logo_file=sum(1 for x in out if x['logo_file']), cost_usd=round(az.usd, 4), model=a.model)
    json.dump({'schema': 'investedia.company-enrich.v1', 'count': len(out), 'companies': out}, open(f'{a.out}/companies-enrich.json', 'w'), ensure_ascii=False, indent=1)
    json.dump(rep, open(f'{a.out}/report.json', 'w'), indent=1)
    print(json.dumps({k: rep[k] for k in ('companies', 'wikipedia_found', 'written', 'skipped', 'with_city', 'with_logo_file', 'cost_usd')}))


if __name__ == '__main__':
    main()
