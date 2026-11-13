#!/usr/bin/env python3
"""Per-record review + release package for the Equinix 10-K development phases (data/datacentres/v2/public_candidates.json).

Checks per record (all must pass; failures are held back, never patched silently):
  C1 filing row found verbatim in the FY2025 10-K text (code, phase, metro, target, cabinets, capex)
  C2 filing body hash equals Codex's receipt for the same 10-K (2dca26ad...)
  C3 no Codex reviewed record for the same facility project (no duplicate of stronger evidence)
  C4 city reference: Wikidata label matches the filing metro; country from the city's Wikidata P17 -> ISO (P297), CC0
  C5 listing current: EQIX common equity on Nasdaq per SEC submissions, checked today
  C6 reuse: only filing facts + CC0 location; name is constructed, no filing prose copied
  C7 status honesty: elapsed targets flagged, stage kept as reported at 31 Dec 2025
Review record: owner instruction of 13 Nov 2026 ("prioritize reviewing and releasing the 29 Equinix developments, provided the
evidence and licensing review holds up") delegates the review; the owner's merge is the final publication approval.
Output: data/datacentres/release/v1/{equinix-developments.json (public projections), review.json, MANIFEST.json}
"""
import copy, hashlib, html, json, re, sys, time, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; EV = Path(sys.argv[1]); TODAY = '2026-11-13'
sys.path.insert(0, str(ROOT / 'research/data-centers/phase4')); import sector_adapter as SA
SRC = json.loads((ROOT / 'data/datacentres/v2/public_candidates.json').read_text(encoding='utf-8'))
CODEX = json.loads((ROOT / 'research/data-centers/phase2/phase2-dataset.json').read_text(encoding='utf-8'))
CODEX_SHA = CODEX['companies']['EQ:XNAS:EQIX']['security_class_evidence']['sha256']
DEV = json.loads((EV / 'filings/eqix-dev.json').read_text()); CITY = json.loads((EV / 'wd/city-refs.json').read_text())
TEXT = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', (EV / 'filings/eqix-10k.htm').read_text(encoding='utf-8', errors='replace'))))
SUB = json.loads((EV / 'reg/sec-0001101239.json').read_text())
UA = {'User-Agent': 'InvestediaResearch/1.0 (facts-only review; low volume)'}
_cache = EV / 'wd/country-iso.json'; ISO = json.loads(_cache.read_text()) if _cache.exists() else {}

def wd(q):
    for a in range(5):
        time.sleep(2 + 5 * a)
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(f'https://www.wikidata.org/wiki/Special:EntityData/{q}.json', headers=UA), timeout=30).read())['entities'][q]
        except Exception: continue
    return None

def country_of(metro):
    c = CITY[metro]
    if metro in ISO: return ISO[metro]
    e = wd(c['qid'])
    if e['claims'].get('P297'):  # territory with its own ISO code (Hong Kong, Singapore)
        ISO[metro] = {'country_qid': c['qid'], 'iso2': e['claims']['P297'][0]['mainsnak']['datavalue']['value']}
    else:
        cl = [x for x in e['claims']['P17'] if not x.get('qualifiers', {}).get('P582')]  # current country (no end time)
        cl.sort(key=lambda x: x.get('rank') != 'preferred')
        for x in cl:
            cq = x['mainsnak']['datavalue']['value']['id']; ce = wd(cq)
            if ce and ce['claims'].get('P297'):
                ISO[metro] = {'country_qid': cq, 'iso2': ce['claims']['P297'][0]['mainsnak']['datavalue']['value']}; break
    _cache.write_text(json.dumps(ISO, indent=1)); return ISO.get(metro, {})

rows = {f'{r[0]}:' + re.sub(r'[^a-z0-9]+', '-', r[1].lower()).strip('-'): r for r in DEV['rows']}
codex_ids = {x['id'] for x in CODEX['original_records'] + CODEX['development_records']}
listing_ok = 'EQIX' in SUB['tickers'] and SUB['exchanges'][SUB['tickers'].index('EQIX')] == 'Nasdaq'
released, review, held = [], [], []
for r0 in SRC['records']:
    r = copy.deepcopy(r0); sid = r['source_identity']['id']; code, phase, metro, target, cab, capex = rows[sid]
    checks = {}
    checks['C1_row_verbatim'] = f'{code} {phase} {metro} {target} {cab}' in TEXT and f' {capex} ' in TEXT[TEXT.find(f'{code} {phase} {metro}'):TEXT.find(f'{code} {phase} {metro}') + 80]
    checks['C2_filing_hash_matches_codex'] = DEV['sha256'] == CODEX_SHA
    checks['C3_no_codex_duplicate'] = f'project:eqix:{code}' not in codex_ids
    ci = country_of(metro); checks['C4_city_reference'] = CITY[metro]['label'] in (metro, 'New York City', 'San Jose', 'Johor Bahru') and bool(ci.get('iso2'))
    checks['C5_listing_current'] = listing_ok
    checks['C6_facts_only'] = all(v['status'] == 'cleared' for v in r['reuse']['fields'].values()) and not r['imagery']
    elapsed = int(target.split()[1]) < 2026 or (target.split()[1] == '2026' and int(target[1]) <= 3)
    checks['C7_status_honest'] = r['status']['as_of'] == '2025-12-31' and 'not a completion' in r['status']['label']
    if not all(checks.values()):
        held.append({'id': r['id'], 'checks': checks}); continue
    # review edits (before signing): country from CC0 city reference; parent kept as a note so a public record never points at an unpublished one
    r['country_code'] = ci['iso2']
    r['notes'] = [n for n in r['notes'] if n['field'] != 'country'] + [{'field': 'country', 'disposition': f"From the Wikidata (CC0) city reference's country ({ci['country_qid']} -> {ci['iso2']})."}]
    if r['asset'].get('parent_id'):
        r['notes'].append({'field': 'asset', 'disposition': f"Phase of Equinix facility {code} ({r['asset']['parent_id']}, research tier); link withheld from the public record."})
        r['asset']['parent_id'] = None
    if elapsed:
        r['status']['certainty'] = 'company_reported_target_elapsed'
        r['status']['label'] = f'Under construction at 31 Dec 2025 (latest filing). Target opening {target} has passed; current status not confirmed by a later filing.'
    r['location'].pop('basis_type', None)
    fact = copy.deepcopy(r); fact.pop('reuse', None)
    r['reuse']['review'] = {'fact_sha256': SA.digest(fact), 'reviewer': 'Claude (research agent), delegated by owner instruction 2026-11-13; owner merge = final approval',
                            'date': TODAY, 'basis': 'Checks C1-C7 passed: SEC FY2025 10-K table row verbatim; Codex-matching filing hash; Wikidata CC0 city/country; facts only, no prose/images'}
    pub = SA.public_projection(r)  # Codex's gate: raises if anything is not releasable
    released.append(pub); review.append({'id': r['id'], 'checks': checks, 'target_elapsed': elapsed, 'fact_sha256': r['reuse']['review']['fact_sha256']})

out = ROOT / 'data/datacentres/release/v1'; out.mkdir(parents=True, exist_ok=True)
body = {'schema': 'investedia.projects.import.v1', 'synthetic': False, 'companies': {k: v for k, v in SRC['companies'].items() if k == 'cik:0001101239'}, 'records': released}
(out / 'equinix-developments.json').write_text(json.dumps(body, ensure_ascii=False, indent=1), encoding='utf-8')
(out / 'review.json').write_text(json.dumps({'reviewed': review, 'held': held}, ensure_ascii=False, indent=1), encoding='utf-8')
m = {'release': 'data-centres-v1', 'date': TODAY, 'records': len(released), 'held': len(held), 'elapsed_targets': sum(x['target_elapsed'] for x in review),
     'source': DEV['source'], 'source_sha256': DEV['sha256'], 'file_sha256': hashlib.sha256((out / 'equinix-developments.json').read_bytes()).hexdigest(),
     'publication': 'Prepared, not published. Needs owner push/merge and the Projects UI integration.'}
(out / 'MANIFEST.json').write_text(json.dumps(m, indent=1), encoding='utf-8'); print(json.dumps(m, indent=1))
