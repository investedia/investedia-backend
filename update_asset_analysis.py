"""Big-move analysis for every tracked asset (free, refreshed with the price robot).

For assets whose move is large against their own recent volatility, writes a short factual note from the price data and the
articles that name the asset. Gemini (GEMINI_API_KEY) phrases it when available; otherwise a deterministic template is used.
Output: assets/globe/analysis.json  {asof, items: {SYMBOL: {t, z, d, w, m, text, ai, articles:[ids]}}}
"""
import json, os, re, statistics, sys, time, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__)); G = os.path.join(ROOT, 'assets', 'globe')
GEMINI = os.environ.get('GEMINI_API_KEY', '').strip()
MAX_AI, MIN_Z, MIN_MOVE = 12, 2.0, 1.5
MAJOR_FX = {'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD', 'USDCNY', 'USDINR', 'USDMXN', 'USDBRL', 'USDTRY', 'USDZAR'}

def load(name, default):
    try: return json.load(open(os.path.join(G, name), encoding='utf-8'))
    except Exception: return default

def vol(sp):
    r = [(b / a - 1) * 100 for a, b in zip(sp, sp[1:]) if a]
    return statistics.pstdev(r) if len(r) >= 8 else None

def related(a, stories):
    sym = a['s'].upper(); base = sym.replace('-USD', '').replace('=X', ''); name = (a.get('n') or '').lower()
    out = []
    for s in stories:
        for i in s.get('impacts') or []:
            t = str(i.get('ticker') or '').upper()
            if t in (sym, base) or (name and len(name) > 3 and name == str(i.get('name') or '').lower()):
                out.append((s, i)); break
    return sorted(out, key=lambda x: x[0]['published_at'], reverse=True)[:5]

def template(a, z, d, w, m, arts):
    dirw = 'up' if d > 0 else 'down'
    t = f"{a['n']} is {dirw} {abs(d):.2f}% today, {abs(z):.1f}x its typical daily move"
    t += f" ({w:+.1f}% over the week, {m:+.1f}% over the month)."
    if arts: t += f" {len(arts)} recent article{'s' if len(arts) != 1 else ''} name it; the latest is “{arts[0][0]['headline']}”."
    else: t += " No article in our feed names it, so there is no news catalyst to point to."
    return t

def ai(a, z, d, w, m, arts):
    if not GEMINI: return None
    ctx = {'asset': a['n'], 'symbol': a['s'], 'move_today_pct': round(d, 2), 'sigma': round(z, 1), 'week_pct': round(w, 2), 'month_pct': round(m, 2),
           'articles': [{'headline': s['headline'], 'why': i.get('why', ''), 'direction': i.get('direction', '')} for s, i in arts]}
    prompt = ("You are a financial newsroom editor. Write 2 sentences (max 55 words) analysing this price move for professional investors. Use ONLY the facts below. "
              "State how large the move is against normal volatility, and name the related articles if any. Never claim the articles caused the move; say 'coincides with' or 'follows'. "
              "No advice, no predictions. If there are no articles say no catalyst was found. Return plain text only.\n" + json.dumps(ctx))
    try:
        req = urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent', data=json.dumps({'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {'temperature': 0.2, 'maxOutputTokens': 160}}).encode(), headers={'Content-Type': 'application/json', 'x-goog-api-key': GEMINI})
        r = json.load(urllib.request.urlopen(req, timeout=25)); txt = r['candidates'][0]['content']['parts'][0]['text'].strip()
        return re.sub(r'\s+', ' ', txt)[:420] if 20 < len(txt) < 600 else None
    except Exception as e:
        print('gemini skipped:', str(e)[:80]); return None

def main():
    assets = {a['s']: a for a in load('markets.json', {}).get('assets', [])}; assets.update(load('news-prices.json', {}).get('assets', {}))
    stories = (load('news-archive.json', {}).get('stories') or load('news-live.json', {}).get('stories') or [])
    old = load('analysis.json', {}).get('items', {}); cutoff = time.time() - 48 * 3600
    cand = []
    for s, a in assets.items():
        sp = a.get('sp') or []; v = vol(sp[-22:]) if sp else None
        if not v or a.get('d') is None or abs(a['d']) > 25 or (a.get('t') == 'fx' and s not in MAJOR_FX) or re.search(r'[.]\w+$', s) and a.get('t') == 'stocks' and abs(a['d']) > 15: continue
        z = a['d'] / v
        if abs(z) >= MIN_Z and abs(a['d']) >= (MIN_MOVE if a.get('t') != 'fx' else .5): cand.append((abs(z), s, a, z))
    cand.sort(reverse=True); items = {k: x for k, x in old.items() if x.get('ts', 0) > cutoff and k not in {c[1] for c in cand}}
    for n, (_, s, a, z) in enumerate(cand[:60]):
        arts = related(a, stories); d, w, m = a['d'], a.get('w') or 0, (a['sp'][-1] / a['sp'][0] - 1) * 100 if a.get('sp') and a['sp'][0] else 0
        prev = old.get(s); same = prev and abs(prev.get('d', 0) - d) < 0.3 and prev.get('articles') == [x[0]['id'] for x in arts]
        text, used = (prev['text'], prev.get('ai', False)) if same else (None, False)
        if text is None:
            text = ai(a, z, d, w, m, arts) if n < MAX_AI else None; used = bool(text)
            text = text or template(a, z, d, w, m, arts)
        items[s] = {'ts': int(time.time()), 'z': round(z, 2), 'd': round(d, 2), 'w': round(w, 2), 'm': round(m, 2), 'text': text, 'ai': used, 'articles': [x[0]['id'] for x in arts]}
    doc = json.dumps({'asof': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'items': items}, separators=(',', ':'), ensure_ascii=False)
    for d in (G, os.path.join(ROOT, 'docs', 'assets', 'globe')):
        if os.path.isdir(d): open(os.path.join(d, 'analysis.json'), 'w', encoding='utf-8').write(doc)
    print(f'analysis: {len(items)} assets ({sum(1 for x in items.values() if x["ai"])} AI-phrased)')

if __name__ == '__main__':
    try: main()
    except Exception as e: print('analysis failed:', e); sys.exit(0)
