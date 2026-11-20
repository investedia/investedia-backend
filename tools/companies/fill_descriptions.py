"""Fill missing company descriptions and sectors for the companies globe (owner, 20 Nov 2026).

Reads the published assets/globe/companies-wd.json, sends companies that lack a description or a sector to
Claude Haiku in batches, and writes descriptions.json ({qid: {"d": ..., "s": ...}}) as a review artifact.
Nothing is published from here: the owner reviews the result and it is merged into the website by a PR.

Rules given to the model: one short factual sentence, no opinions, prices, forecasts or investment wording;
use the supplied facts; only add widely known facts it is sure of; otherwise return null.
Stops before the spend limit (--max-usd).
"""
import argparse, json, os, re, sys, urllib.request

SECTORS = ['AI & software', 'Semiconductors', 'Banking & fintech', 'Insurance', 'Telecoms', 'Airlines', 'Airports & ports',
           'Hotels & tourism', 'Real estate', 'Oil & gas', 'Renewables & utilities', 'Mining & metals', 'Agriculture & food',
           'Healthcare & pharma', 'Construction & cement', 'Transport & logistics', 'Automotive & EVs', 'Media & entertainment',
           'Consumer goods & retail', 'Industrials & chemicals']
PRICE_IN, PRICE_OUT = 0.10 / 1e6, 0.50 / 1e6  # Claude Haiku 5.5, prompts under 100K tokens
MODEL = 'claude-haiku-5-5'
SYSTEM = ('You write short, neutral, factual descriptions of companies for a financial news site. For each company return '
          'one sentence of at most 16 words saying what the company does and where (no opinions, prices, forecasts, rankings, '
          '"leading", or investment advice). Use the facts supplied; add only widely known facts you are sure of. If you cannot '
          'describe it reliably, use null. Also pick the best sector from the list, or null. Reply with JSON only: '
          '[{"q": "<id>", "d": "<sentence or null>", "s": "<sector or null>"}]. Sectors: ' + '; '.join(SECTORS))


def load(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'InvestediaRobot/1.0 (+https://www.investedia.com)'})
    return json.load(urllib.request.urlopen(req, timeout=120))


def facts(c):
    web = re.sub(r'^https?://(www\.)?', '', c.get('w') or '').split('/')[0]
    return {'q': c['q'], 'name': c['n'], 'country': c.get('c'), 'hq_city': c.get('city'), 'industry': c.get('i'),
            'website': web or None, 'listed_on_exchange': bool(c.get('l')), 'existing_description': c.get('d')}


def parse(text):
    m = re.search(r'\[.*\]', text, re.S)
    if not m: return []
    try: rows = json.loads(m.group(0))
    except json.JSONDecodeError: return []
    return [r for r in rows if isinstance(r, dict) and isinstance(r.get('q'), str)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default='https://www.investedia.com/assets/globe/companies-wd.json')
    ap.add_argument('--max-usd', type=float, default=1.0)
    ap.add_argument('--batch', type=int, default=40)
    ap.add_argument('--out', default='descriptions.json')
    a = ap.parse_args()
    if not 0 < a.max_usd <= 5: sys.exit('max-usd must be between 0 and 5')
    import anthropic  # official SDK, reads ANTHROPIC_API_KEY
    client = anthropic.Anthropic(max_retries=3, timeout=180.0)
    todo = [c for c in load(a.source)['companies'] if not c.get('d') or not c.get('s')]
    out, spent, calls = {}, 0.0, 0
    for k in range(0, len(todo), a.batch):
        part = todo[k:k + a.batch]
        if spent + 0.01 > a.max_usd: print(f'stop: spend ${spent:.4f} near limit ${a.max_usd}'); break
        msg = client.messages.create(model=MODEL, max_tokens=6000, system=SYSTEM, output_config={'effort': 'low'},
                                     messages=[{'role': 'user', 'content': json.dumps([facts(c) for c in part], ensure_ascii=False)}])
        calls += 1
        spent += msg.usage.input_tokens * PRICE_IN + msg.usage.output_tokens * PRICE_OUT
        if msg.stop_reason == 'refusal': continue
        text = ''.join(b.text for b in msg.content if b.type == 'text')
        ids = {c['q'] for c in part}
        for r in parse(text):
            if r['q'] not in ids: continue
            d = r.get('d') if isinstance(r.get('d'), str) and 8 <= len(r['d']) <= 160 else None
            s = r.get('s') if r.get('s') in SECTORS else None
            if d or s: out[r['q']] = {'d': d, 's': s}
        print(f'{k + len(part)}/{len(todo)} companies, {len(out)} filled, ${spent:.4f}', flush=True)
    json.dump({'model': MODEL, 'spent_usd': round(spent, 4), 'calls': calls, 'companies': out}, open(a.out, 'w'), ensure_ascii=False)
    print(json.dumps({'filled': len(out), 'asked': len(todo), 'spent_usd': round(spent, 4), 'calls': calls}))


if __name__ == '__main__':
    main()
