"""Evidence-based globe connections + coverage diagnostics (deterministic, no AI calls).

Reads the published articles (assets/globe/news-live.json + news-archive.json) and the priced assets (markets.json) and writes
assets/globe/connections.json:
  connections: one record per drawable line
    {id, event, origin{place,country,lat,lon}, dest{name,country,lat,lon,asset}, type, tier, confidence, evidence, explanation}
  rejected:    counts of candidate lines that were NOT drawn, by reason
  diag:        coverage diagnostics (articles per region/country, geolocation rate, connections per event, duplicates, feed failures)

Rules (see design/GLOBE-COVERAGE-UPGRADE.md):
  * Only relationships the article itself states (its impacts: subject, acquirer/target, supplier/customer, policy rate, currency,
    commodity input/output, regulator action...). Never "same broad sector" (sector impacts are rejected).
  * A country impact is anchored to that country's main market (currency for currency effects, main index otherwise) - a real,
    priced place, never an invented coordinate.
  * Lines shorter than MIN_KM (event and affected asset in the same city/area) are not drawn; the event dot already shows them.
  * Crypto has no legitimate place: no line.
  * Article coordinates are never changed.
"""
import json, math, os, re, sys, collections as C
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
G = os.path.join(ROOT, 'assets', 'globe')
MIN_KM = 100  # only same-city pairs (identical dots) are skipped
CONF = {'high': .9, 'medium': .7, 'low': .4}
MIN_CONF = .25  # below this: logged, not drawn. Between .25 and .55: drawn only as a secondary (thin, dashed) line
DIRECT_CONF = .55
TYPE = {  # relation -> (relationship type, tier 1 = direct / 2 = secondary, weight)
    'subject': ('direct', 1, 1.0), 'parent': ('direct', 1, .9), 'acquirer': ('acquisition', 1, 1.0), 'target': ('acquisition', 1, 1.0),
    'supplier': ('supply-chain', 1, .9), 'customer': ('supply-chain', 1, .9), 'partner': ('partnership', 2, .8), 'counterparty': ('partnership', 2, .8),
    'policy-rate': ('central-bank', 1, 1.0), 'yield': ('central-bank', 1, .9), 'currency': ('currency', 1, .95), 'market-benchmark': ('market', 2, .85),
    'commodity-output': ('commodity', 1, .95), 'commodity-input': ('commodity', 2, .85), 'regulator-action': ('regulatory', 1, .95),
    'competitor': ('named-peer', 2, .7), 'index-constituent': ('market', 2, .6), 'other': ('direct', 2, .6),
}
WHY = {
    'direct': 'The article reports a development at {d}.',
    'acquisition': 'Deal between the parties: {d} is named as the {rel} in the article.',
    'supply-chain': '{d} is named as a {rel} of the company in the article.',
    'partnership': '{d} is named as a {rel} in the article.',
    'central-bank': 'Monetary-policy decision with a stated effect on {d}.',
    'currency': 'The article states an effect on {d}.',
    'market': 'The article states an effect on {d}, the benchmark market.',
    'commodity': 'The article states an effect on {d}.',
    'regulatory': 'Regulatory action that the article says affects {d}.',
    'named-peer': '{d} is named in the article as a directly affected competitor (not inferred from the sector).',
}


BENCH = {  # headline words -> markets.json symbol (benchmarks only; a headline must name it explicitly)
    'nikkei': '^N225', 'topix': '^N225', 'kospi': '^KS11', 'sensex': '^BSESN', 'nifty': '^NSEI', 'hang seng': '^HSI', 'taiex': '^TWII',
    'asx': '^AXJO', 'nzx': '^NZ50', 'straits times index': '^STI', 'jakarta composite': '^JKSE', 'klci': '^KLSE', 'shanghai composite': '000001.SS',
    'csi 300': '000001.SS', 'jse': '^J203.JO', 'tadawul': 'KSA', 'tasi': 'KSA', 'bist': 'XU100.IS', 'borsa istanbul': 'XU100.IS',
    'nasdaq': '^IXIC', 's&p 500': '^GSPC', 'dow jones': '^DJI', 'wall street': '^GSPC', 'ftse 100': '^FTSE', 'dax': '^GDAXI', 'cac 40': '^FCHI',
    'stoxx 600': '^STOXX50E', 'euro stoxx': '^STOXX50E', 'ibovespa': '^BVSP', 'bovespa': '^BVSP', 'merval': '^MERV', 'ipsa': 'ECH', 'tsx': '^GSPTSE',
    'smi': '^SSMI', 'omx': '^OMX', 'ibex': '^IBEX'}


def km(a, b, c, d):
    p = math.radians
    h = math.sin(p(c - a) / 2) ** 2 + math.cos(p(a)) * math.cos(p(c)) * math.sin(p(d - b) / 2) ** 2
    return 6371 * 2 * math.asin(min(1, math.sqrt(h)))


def load(name, default):
    try: return json.load(open(os.path.join(G, name)))
    except Exception: return default


def history(iso, mk, _unused):
    """Read-only article inputs; deterministic historical output using the live rules."""
    byday = C.defaultdict(dict)
    for filename in sorted(os.listdir(os.path.join(G, 'library'))):
        if not filename.endswith('.json'): continue
        with open(os.path.join(G, 'library', filename)) as handle:
            article = json.load(handle)
        day = (article.get('published_at') or '')[:10]
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', day) and article.get('location', {}).get('lat') is not None:
            byday[day][article['id']] = article
    total = days = 0
    for day, articles in sorted(byday.items()):
        events = load('events/' + day + '.json', {}).get('events', [])
        available = {event['id'] for event in events}
        arts = [a for key, a in sorted(articles.items()) if key in available]
        if not arts: continue
        conns, rejected, _ = _rules(iso, mk, arts)
        conns.sort(key=lambda c: (-c['score'], c['published_at'] or '', c['id']))
        raw = json.dumps({'schema': 'investedia.connections-history/v1', 'day': day,
                          'connections': conns, 'rejected': dict(sorted(rejected.items()))}, separators=(',', ':'))
        for directory in (G,):
            out = os.path.join(directory, 'connections-history')
            os.makedirs(out, exist_ok=True)
            target = os.path.join(out, day + '.json')
            with open(target + '.tmp', 'w') as handle: handle.write(raw)
            os.replace(target + '.tmp', target)
        days += 1
        total += len(conns)
    print(json.dumps({'days': days, 'connections': total}))


def _rules(iso, mk, stories):
    # company registry (data/registry.json): exact normalised-name match to a listed company with a verified place. No fuzzy matching,
    # no AI; a name that matches nothing (private companies such as OpenAI, ByteDance, Pemex) stays unlocated.
    try: REG = json.load(open(os.path.join(ROOT, 'data', 'registry.json')))
    except Exception: REG = {'assets': {}, 'names': {}}
    norm = lambda x: re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', (x or '').lower())).strip()
    SUF = re.compile(r'\b(inc|corp|corporation|plc|ltd|limited|sa|ag|nv|co|company|group|holdings|holding)\b')
    def reg_place(name):
        for n in (norm(name), re.sub(r'\s+', ' ', SUF.sub('', norm(name))).strip()):
            ids = [a for a in REG['names'].get(n, []) if (REG['assets'].get(a, {}).get('geo') or {}).get('la') is not None]
            if len({REG['assets'][a]['geo']['city'] for a in ids}) == 1:  # unambiguous: every match points to the same place
                a = REG['assets'][ids[0]]; return {'name': a.get('name') or name, 'lat': a['geo']['la'], 'lon': a['geo']['lo'], 'asset': a.get('px') or a['id'], 'via': 'registry-name'}
        return None
    mk = load('markets.json', {}).get('assets', [])
    anchor_idx, anchor_fx = {}, {}
    alias = {'United States': 'US', 'Eurozone': 'EU', 'Hong Kong': 'HK', 'Czech Republic': 'CZ', 'Dominican Republic': 'DO', 'Macau': 'MO',
             'North Macedonia': 'MK', 'Cape Verde': 'CV', 'DR Congo': 'CD', 'Eswatini': 'SZ', 'Cayman Islands': 'KY'}
    for a in mk:
        cc = iso.get(a.get('k')) or alias.get(a.get('k'))
        if not cc or a.get('la') is None: continue
        if a.get('g') == 'Index' and (cc not in anchor_idx or a.get('m') and not anchor_idx[cc].get('m')): anchor_idx[cc] = a
        if a.get('t') == 'fx' and cc not in anchor_fx: anchor_fx[cc] = a
    if 'EU' not in anchor_fx and any(a.get('s') == 'EURUSD' for a in mk): anchor_fx['EU'] = next(a for a in mk if a.get('s') == 'EURUSD')

    bysym = {a['s']: a for a in mk if a.get('la') is not None}
    bench_re = re.compile(r'\b(' + '|'.join(re.escape(k) for k in sorted(BENCH, key=len, reverse=True)) + r')\b', re.I)
    conns, rej, seen = [], C.Counter(), {}
    market_refs = 0
    for s in stories:
        L = s.get('location') or {}
        if L.get('lat') is None: rej['event-not-geolocated'] += 1; continue
        occ = iso.get(L.get('country'))
        for i in s.get('impacts') or []:
            rel = i.get('relation') or 'other'
            if i.get('kind') == 'sector': rej['sector-too-broad'] += 1; continue
            typ, tier, w = TYPE.get(rel, TYPE['other'])
            r = i.get('asset') or {}
            if typ == 'direct' and r.get('c') == 'commodity': typ = 'commodity'
            if typ == 'direct' and (i.get('kind') == 'country' or r.get('c') in ('index', 'fx', 'rate')): typ = 'market'
            if r.get('c') == 'crypto': rej['crypto-no-place'] += 1; continue
            if r.get('la') is not None:
                dest = {'name': r.get('n') or i.get('name'), 'country': i.get('country'), 'lat': r['la'], 'lon': r['lo'], 'asset': r.get('px') or r.get('id')}
            elif i.get('kind') == 'country':
                cc = i.get('country'); a = (anchor_fx.get(cc) or anchor_idx.get(cc)) if rel == 'currency' else (anchor_idx.get(cc) or anchor_fx.get(cc))
                if not a: rej['country-without-market'] += 1; continue
                dest = {'name': a['n'], 'country': i.get('country'), 'lat': a['la'], 'lon': a['lo'], 'asset': a['s']}
            elif i.get('kind') == 'company' and reg_place(i.get('name')):
                g = reg_place(i.get('name')); dest = {'name': g['name'], 'country': i.get('country'), 'lat': g['lat'], 'lon': g['lon'], 'asset': g['asset'], 'resolved': g['via']}
            else:
                rej['company-without-location'] += 1; continue
            conf = round(CONF.get(i.get('confidence'), .6) * w, 2)
            if conf < MIN_CONF: rej['low-confidence'] += 1; continue
            if conf < DIRECT_CONF: tier = 2
            dist = km(L['lat'], L['lon'], dest['lat'], dest['lon'])
            if dist < MIN_KM: rej['same-place-shown-as-dot'] += 1; continue
            key = (s['id'], round(dest['lat'], 1), round(dest['lon'], 1))
            if key in seen: rej['duplicate-line'] += 1; continue
            cross = dest['country'] != occ
            rec = {'id': f"{s['id']}>{dest['asset']}", 'event': s['id'], 'published_at': s.get('published_at'),
                   'origin': {'place': L.get('place'), 'country': occ, 'lat': L['lat'], 'lon': L['lon']}, 'dest': dest,
                   'type': typ, 'relation': rel, 'tier': tier, 'cross_border': cross, 'km': round(dist),
                   'confidence': conf, 'importance': s.get('importance') or 1,
                   'evidence': {'impact': i.get('name'), 'why': i.get('why'), 'direction': i.get('direction'), 'source': (s.get('source') or {}).get('name'), 'headline': s.get('headline')},
                   'explanation': WHY.get(typ, WHY['direct']).format(d=dest['name'], rel=rel.replace('-', ' '))}
            rec['score'] = round(conf * (1 + .25 * (rec['importance'] - 1)) * (1.15 if cross else 1) * (1 if tier == 1 else .8), 3)
            seen[key] = rec; conns.append(rec)
    # headline-named benchmarks (deterministic, explicit mention only; stored here, never added to the article's frozen implications)
    for s_ in stories:
        L = s_.get('location') or {}
        if L.get('lat') is None: continue
        named = {BENCH[m.group(1).lower()] for m in bench_re.finditer(s_.get('headline') or '')}
        have = {c['dest']['asset'] for c in conns if c['event'] == s_['id']}
        for sym in sorted(named - have):
            a = bysym.get(sym)
            if not a: continue
            market_refs += 1
            dist = km(L['lat'], L['lon'], a['la'], a['lo'])
            if dist < MIN_KM: rej['same-place-shown-as-dot'] += 1; continue
            occ = iso.get(L.get('country')); dcc = iso.get(a.get('k')) or a.get('k')
            rec = {'id': f"{s_['id']}>{sym}", 'event': s_['id'], 'published_at': s_.get('published_at'),
                   'origin': {'place': L.get('place'), 'country': occ, 'lat': L['lat'], 'lon': L['lon']},
                   'dest': {'name': a['n'], 'country': dcc, 'lat': a['la'], 'lon': a['lo'], 'asset': sym},
                   'type': 'market', 'relation': 'named-in-headline', 'tier': 2, 'cross_border': dcc != occ, 'km': round(dist), 'confidence': .6,
                   'importance': s_.get('importance') or 1,
                   'evidence': {'impact': a['n'], 'why': 'Named in the headline: "' + (s_.get('headline') or '')[:140] + '"', 'direction': None,
                                'source': (s_.get('source') or {}).get('name'), 'headline': s_.get('headline')},
                   'explanation': f"The headline names {a['n']}; the line links the event to that market."}
            rec['score'] = round(.6 * (1 + .25 * (rec['importance'] - 1)) * (1.15 if rec['cross_border'] else 1) * .8, 3)
            conns.append(rec)
    conns.sort(key=lambda c: (-c['score'], c['published_at'] or ''), reverse=False)

    return conns, rej, market_refs


def main():
    iso = load('iso.json', {})
    live, arch = load('news-live.json', {}).get('stories', []), load('news-archive.json', {}).get('stories', [])
    stories = list({s['id']: s for s in arch + live}.values())
    if os.environ.get('CONN_HISTORY'):  # historical days: the full article library (same rules, one file per day)
        return history(iso, load('markets.json', {}).get('assets', []), stories)
    mk = load('markets.json', {}).get('assets', [])
    conns, rej, market_refs = _rules(iso, mk, stories)
    # ---- diagnostics (measured from the published data + the last robot status)
    st = load('news-status.json', {})
    reg = C.Counter((s.get('location') or {}).get('region') or 'none' for s in stories)
    per_ev = C.Counter(c['event'] for c in conns)
    creg = C.Counter()
    for c in conns: creg[next(((s.get('location') or {}).get('region') for s in stories if s['id'] == c['event']), 'none')] += 1
    diag = {
        'articles': len(stories), 'by_region': dict(reg.most_common()),
        'by_country_top': C.Counter((s.get('location') or {}).get('country') for s in stories).most_common(30),
        'geolocated_pct': round(100 * sum(1 for s in stories if (s.get('location') or {}).get('lat') is not None) / max(1, len(stories)), 1),
        'multi_source_events': sum(1 for s in stories if len(s.get('sources') or []) > 1),
        'events_with_connection': len(per_ev), 'connections': len(conns), 'connections_by_region': dict(creg.most_common()),
        'cross_border_pct': round(100 * sum(c['cross_border'] for c in conns) / max(1, len(conns)), 1),
        'connections_per_event': round(len(conns) / max(1, len(per_ev)), 2),
        'by_type': dict(C.Counter(c['type'] for c in conns).most_common()),
        'rejected': dict(rej.most_common()), 'headline_benchmarks_found': market_refs,
        'feeds_failed_last_run': (st.get('tiers', {}).get('broad', {}) or {}).get('sources_failed', []),
        'last_run': {k: st.get(k) for k in ('fetched', 'skipped_seen', 'deduped', 'candidates', 'new_stories')},
    }
    out = {'schema': 'investedia.connections.v1', 'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
           'rules': {'min_km': MIN_KM, 'min_confidence': MIN_CONF, 'sector_lines': False}, 'connections': conns, 'rejected': dict(rej), 'diag': diag}
    raw = json.dumps(out, separators=(',', ':'))
    for d in (G, os.path.join(ROOT, 'docs', 'assets', 'globe')):  # site copy + GitHub Pages copy, each written atomically (temp file + rename)
        if not os.path.isdir(d): continue
        tmp = os.path.join(d, '.connections.json.tmp'); open(tmp, 'w').write(raw); os.replace(tmp, os.path.join(d, 'connections.json'))
    print(json.dumps(diag, indent=1)[:2500])


if __name__ == '__main__':
    main()
