#!/usr/bin/env python3
"""Investedia Education glossary builder (owner, 25 Nov 2026).

Writes a beginner / intermediate / expert investing glossary with the owner's Azure OpenAI deployment:
  1. term list per topic, 2. one entry per term, 3. a separate checking pass that fixes or drops entries.
Output: out/glossary.json (entries) and out/report.json (counts, tokens, cost). Educational only: not investment advice.
Stdlib only. Secrets come from the environment and are never printed.
"""
import argparse, json, os, re, sys, time, urllib.error, urllib.request

API_VERSION = '2024-10-21'
PRICES = {'gpt-4.1-mini': (0.40, 1.60), 'gpt-4.1-nano': (0.10, 0.40), 'gpt-4.1': (2.00, 8.00), 'gpt-4o-mini': (0.15, 0.60)}  # USD per 1M tokens in/out
LEVELS = ('beginner', 'intermediate', 'expert')
TOPICS = {
    'start': 'getting started with investing', 'personal': 'personal finance, saving, budgeting, debt',
    'stocks': 'stocks and stock markets', 'funds': 'ETFs, index funds and mutual funds', 'bonds': 'bonds, interest rates and credit',
    'crypto': 'crypto assets and blockchains', 'currencies': 'currencies and forex', 'commodities': 'commodities: energy, metals, agriculture',
    'realestate': 'real estate and REITs', 'charts': 'charts and technical analysis', 'fundamentals': 'company fundamentals, accounts and valuation',
    'accounts': 'investment accounts, orders and taxes (general, not country-specific advice)', 'macro': 'macroeconomics, central banks and inflation',
    'derivatives': 'options, futures and other derivatives', 'risk': 'risk, portfolios and diversification', 'emerging': 'emerging and frontier markets',
}
EXISTING = ["Asset", "Bear market", "Bond", "Broker", "Bull market", "Candlestick", "Compound interest", "Diversification", "Dividend", "DCA", "ETF",
            "Expense ratio", "Index", "Inflation", "Liquidity", "Market cap", "P/E ratio", "Portfolio", "REIT", "Stablecoin", "Volatility", "Yield"]
RULES = ("Rules: plain English for a general reader; UK/US neutral spelling is fine. Facts must be standard textbook knowledge. "
         "Never give advice or tell the reader what to buy or sell. Never state current or recent prices, rates or statistics as facts. "
         "Examples are clearly illustrative (\"Imagine...\", round numbers) and never name a real price as current. No hype, no promises of returns.")


class Azure:
    def __init__(self, endpoint, key, deployment, model, max_usd):
        self.url = '%s/openai/deployments/%s/chat/completions?api-version=%s' % (endpoint.rstrip('/'), deployment, API_VERSION)
        self.key, self.model, self.max_usd = key, model, max_usd
        self.tin = self.tout = self.calls = 0

    @property
    def usd(self):
        pi, po = PRICES.get(self.model, PRICES['gpt-4.1-mini'])
        return (self.tin * pi + self.tout * po) / 1e6

    def ask(self, system, user, max_tokens=6000):
        if self.usd + max_tokens * PRICES.get(self.model, PRICES['gpt-4.1-mini'])[1] / 1e6 * 1.2 > self.max_usd:
            raise RuntimeError('budget_reached')
        body = json.dumps({'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
                           'max_tokens': max_tokens, 'temperature': 0.2, 'response_format': {'type': 'json_object'}}).encode()
        for attempt in range(5):
            req = urllib.request.Request(self.url, data=body, method='POST', headers={'Content-Type': 'application/json', 'api-key': self.key})
            try:
                with urllib.request.urlopen(req, timeout=180) as resp: r = json.loads(resp.read().decode())
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and attempt < 4: time.sleep(3 * 2 ** attempt); continue
                try: print('azure error', e.code, e.read()[:400].decode('utf-8', 'replace'), flush=True)
                except Exception: pass
                raise RuntimeError('azure_http_%d' % e.code) from None
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt < 4: time.sleep(3 * 2 ** attempt); continue
                raise RuntimeError('azure_unreachable') from None
        u = r.get('usage') or {}
        self.tin += int(u.get('prompt_tokens') or 0); self.tout += int(u.get('completion_tokens') or 0); self.calls += 1
        try: return json.loads(r['choices'][0]['message']['content'])
        except (KeyError, IndexError, ValueError): return {}


def slug(t): return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')[:80]


def clean(e, known_topics):
    """Validate one entry; return a tidy dict or None."""
    if not isinstance(e, dict): return None
    term = str(e.get('term') or '').strip()
    lvl = str(e.get('level') or '').lower().strip()
    short, plain = str(e.get('short') or '').strip(), str(e.get('plain') or '').strip()
    if not term or lvl not in LEVELS or not (8 <= len(short.split()) <= 40) or len(plain.split()) < 25: return None
    tps = [t for t in (e.get('topics') or []) if t in known_topics][:3]
    mistakes = [str(m).strip() for m in (e.get('mistakes') or []) if str(m).strip()][:3]
    related = [str(r).strip() for r in (e.get('related') or []) if str(r).strip() and str(r).strip().lower() != term.lower()][:6]
    out = {'term': term, 'slug': slug(term), 'level': lvl, 'topics': tps or ['start'], 'short': short, 'plain': plain,
           'example': str(e.get('example') or '').strip(), 'mistakes': mistakes, 'related': related}
    if e.get('aka'): out['aka'] = [str(a).strip() for a in e['aka'] if str(a).strip()][:4]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='out'); ap.add_argument('--max-usd', type=float, default=3.0)
    ap.add_argument('--per-topic', type=int, default=60); ap.add_argument('--limit', type=int, default=1000)
    ap.add_argument('--batch', type=int, default=12)
    a = ap.parse_args()
    endpoint, key = os.environ.get('AZURE_OPENAI_ENDPOINT', ''), os.environ.get('AZURE_OPENAI_API_KEY', '')
    dep = (os.environ.get('AZURE_DEPLOYMENT') or 'gpt-4.1-mini').strip()
    if not endpoint or not key: sys.exit('missing Azure endpoint or key')
    az = Azure(endpoint, key, dep, os.environ.get('AZURE_MODEL') or dep, a.max_usd)
    os.makedirs(a.out, exist_ok=True)
    report = {'model': az.model, 'started': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'notice': 'Educational only. Not investment advice.'}
    sysmsg = 'You write an investing glossary for Investedia, a financial news site. ' + RULES + ' Reply with JSON only.'

    # 1. term list
    seen, terms = {}, []
    for t in EXISTING: seen[t.lower()] = 1; terms.append({'term': t, 'level': '', 'topic': ''})
    for k, desc in TOPICS.items():
        try:
            r = az.ask(sysmsg, f'List {a.per_topic} important glossary terms for the topic "{desc}", spread across levels: about 30% beginner, 45% intermediate, 25% expert. '
                               'Use the common name (with abbreviation in brackets when people use it, e.g. "Price-to-earnings ratio (P/E)"). No duplicates, no people or company names. '
                               'JSON: {"terms":[{"term":"...","level":"beginner|intermediate|expert"}]}', 4000)
        except RuntimeError as e: report['stop'] = str(e); break
        for x in r.get('terms') or []:
            t = str((x or {}).get('term') or '').strip(); base = re.sub(r'\s*\(.*?\)', '', t).lower()
            if t and t.lower() not in seen and base not in seen and len(t) < 70:
                seen[t.lower()] = seen[base] = 1; terms.append({'term': t, 'level': str(x.get('level') or ''), 'topic': k})
    terms = terms[:a.limit]; report['terms_listed'] = len(terms)

    # 2. write entries
    entries, failed = [], []
    for i in range(0, len(terms), a.batch):
        part = terms[i:i + a.batch]
        lst = '\n'.join(f'- {x["term"]}' + (f' (suggested level {x["level"]}, topic {x["topic"]})' if x['level'] else '') for x in part)
        try:
            r = az.ask(sysmsg, 'Write a glossary entry for each term below.\n' + lst + '\n\nFor each: "term" (as given), "aka" (other names, may be empty), '
                               '"level" (beginner|intermediate|expert: how advanced the idea is), "topics" (1-3 of: ' + ', '.join(TOPICS) + '), '
                               '"short" (one-sentence definition, 12-30 words), "plain" (plain-English explanation, 50-90 words), '
                               '"example" (one short illustrative example, starts with "Imagine" or "For example"), '
                               '"mistakes" (2 common misunderstandings, one sentence each), "related" (3-6 related glossary terms). '
                               'JSON: {"entries":[...]}', 9000)
        except RuntimeError as e: report['stop'] = str(e); break
        got = {(c or {}).get('term', '').lower(): c for c in r.get('entries') or []}
        for x in part:
            c = clean(got.get(x['term'].lower()), TOPICS)
            (entries.append(c) if c else failed.append(x['term']))
        print(f'written {len(entries)}/{len(terms)}  ${az.usd:.3f}', flush=True)
    report['written'] = len(entries); report['write_failed'] = failed

    # 3. checking pass: a second reading that fixes or rejects
    checked, dropped, fixed = [], [], 0
    for i in range(0, len(entries), a.batch):
        part = entries[i:i + a.batch]
        try:
            r = az.ask('You are a strict finance editor checking a glossary for accuracy and tone. ' + RULES + ' Reply with JSON only.',
                       'Check each entry. If it is correct and follows the rules, verdict "ok". If it has a fixable problem (factual slip, advice-like wording, '
                       'a stated current price or statistic, wrong level), verdict "fix" and return the corrected full entry with the same fields. '
                       'If the term is not a real or useful investing term, verdict "drop". '
                       'JSON: {"results":[{"slug":"...","verdict":"ok|fix|drop","reason":"short","entry":{...only when fix}}]}\n\n' + json.dumps(part, ensure_ascii=False), 9000)
        except RuntimeError as e:
            report['stop'] = str(e); checked += [dict(x, checked=False) for x in entries[i:]]; break
        res = {(x or {}).get('slug'): x for x in r.get('results') or []}
        for e in part:
            v = res.get(e['slug']) or {}
            if v.get('verdict') == 'drop': dropped.append({'term': e['term'], 'reason': v.get('reason', '')}); continue
            if v.get('verdict') == 'fix':
                f = clean(dict(v.get('entry') or {}, term=e['term']), TOPICS)
                if f: fixed += 1; checked.append(dict(f, checked=True)); continue
            checked.append(dict(e, checked=bool(v)))
        print(f'checked {len(checked)}/{len(entries)}  ${az.usd:.3f}', flush=True)

    checked.sort(key=lambda e: e['term'].lower())
    known = {e['term'].lower() for e in checked}
    for e in checked: e['related'] = [r for r in e['related'] if r.lower() in known] or e['related'][:3]
    by = {l: sum(1 for e in checked if e['level'] == l) for l in LEVELS}
    report.update(final=len(checked), by_level=by, fixed=fixed, dropped=dropped, calls=az.calls, input_tokens=az.tin, output_tokens=az.tout,
                  cost_usd=round(az.usd, 4), finished=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    json.dump({'schema': 'investedia.glossary.v1', 'notice': 'Educational only. Not investment advice. Written with AI and checked by a second AI pass.',
               'count': len(checked), 'entries': checked}, open(os.path.join(a.out, 'glossary.json'), 'w'), ensure_ascii=False, indent=1)
    json.dump(report, open(os.path.join(a.out, 'report.json'), 'w'), indent=1)
    print(json.dumps({k: report[k] for k in ('final', 'by_level', 'fixed', 'cost_usd')}))


if __name__ == '__main__':
    main()
