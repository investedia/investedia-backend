"""Prediction Engine v4, step 1: structured extraction (research/ENGINE-V4.md §2). The LLM only extracts facts; it never decides a
direction to publish, a tier or a confidence. Every number must be stated in the input (article text or the injected calendar
expectations); anything not stated is null. validate() keeps only typed, bounded fields.
"""
import hashlib, json, re
from datetime import datetime, timedelta

from engine import policy as P

RELATIONS = ['subject', 'target', 'acquirer', 'issuer', 'counterparty', 'policy-rate', 'commodity-output', 'customer', 'supplier', 'competitor',
             'peer', 'index-constituent', 'market-benchmark', 'currency', 'other']
EXPECT_KEYS = ['eps_actual', 'eps_expected', 'revenue_actual', 'revenue_expected', 'guidance_actual', 'guidance_expected', 'actual', 'expected',
               'previous', 'rate_actual', 'rate_expected']
CATALYST_KEYS = ['premium_pct', 'size_pct_mcap', 'amount_pct_mcap', 'value_pct_revenue', 'rating_notches', 'supply_change_pct',
                 'tariff_change_pct', 'supply_at_risk_pct', 'amount_usd_bn']

PROMPT = """You extract structured facts from financial news for Investedia. You do NOT predict or recommend anything.
For each story below return one object. Use ONLY facts written in the story text or in its "calendar" block. Never estimate, never use
outside knowledge for numbers; if a value is not written, use null.

Fields:
- "i": the story number
- "event_type": one of {types}
- "commentary": true if the story is mainly opinion, analysis, a market wrap or a forecast piece rather than a new event
- "preview": true if the story is about something that has not happened yet (upcoming results, decision, data)
- "price_move_recap": true if the story mainly reports a price move without a new concrete catalyst
- "competing_catalysts": true if several different events plausibly drive the same asset in different directions
- "expectations": numbers for the event versus what was expected, each a plain number in the units written (no % sign) or null:
  eps_actual, eps_expected, revenue_actual, revenue_expected, guidance_actual, guidance_expected (same metric and period for both),
  actual, expected, previous (a macro release), rate_actual, rate_expected (a policy rate, in percent), plus
  "higher_is": "positive" | "negative" | null (for macro: is a higher value good for the economy/currency?) and
  "source": "story" | "calendar" | null (where the expected values came from)
- "catalyst": numbers as written, else null: premium_pct (offer premium), size_pct_mcap (raise/buyback/deal as % of market value),
  amount_pct_mcap (fine/settlement as % of market value), value_pct_revenue (contract as % of annual revenue), rating_notches
  (analyst rating steps, + for upgrade, - for downgrade), supply_change_pct, tariff_change_pct (percentage points), supply_at_risk_pct,
  amount_usd_bn (crypto amount in USD billions)
- "assets": up to 4 assets the story is directly about: {{"name": ..., "ticker": Yahoo Finance symbol if written or unambiguous, else null,
  "relation": one of {relations}, "stance": "positive" | "negative" | "neutral" (what the story itself implies for this asset),
  "reason": max 20 words}}
- "evidence": max 40 words quoting the numbers you used, or null

Return ONLY a JSON array.

Stories:
{stories}"""
PROMPT_ID = hashlib.sha1(PROMPT.encode()).hexdigest()[:12]


EU_MEMBERS = ['Austria', 'Belgium', 'Croatia', 'Cyprus', 'Estonia', 'Finland', 'France', 'Germany', 'Greece', 'Ireland', 'Italy', 'Latvia', 'Lithuania',
              'Luxembourg', 'Malta', 'Netherlands', 'Portugal', 'Slovakia', 'Slovenia', 'Spain']
CAL_CC = {'United States of America': 'US', 'United States': 'US', 'United Kingdom': 'GB', 'Japan': 'JP', 'Canada': 'CA', 'China': 'CN', 'Australia': 'AU',
          'New Zealand': 'NZ', 'Switzerland': 'CH', **{c: 'EU' for c in EU_MEMBERS}}


def calendar_expectations(story, cal, window_h=6):
    """Expectations from the economic calendar (ForexFactory consensus, Nasdaq EPS estimates) for this story, as a text block.
    Macro: releases of the story's country within [-window_h, +1 h] of publication with a forecast. Earnings: the company's estimate
    within 3 days. Returns (text, sources) or ('', [])."""
    try: t = datetime.fromisoformat(story['published_at'].replace('Z', '+00:00'))
    except Exception: return '', []
    loc = story.get('location') or {}
    cc = (loc.get('iso') or loc.get('cc') or CAL_CC.get(loc.get('country') or '', '')).upper()
    lines, src = [], []
    for e in (cal or {}).get('events') or []:
        try: at = datetime.fromisoformat(e['at'].replace('Z', '+00:00'))
        except Exception: continue
        if not e.get('fc') or not (t - timedelta(hours=window_h) <= at <= t + timedelta(hours=1)): continue
        if not cc or e.get('country') != cc: continue  # only the story's own economy
        lines.append(f"{e['t']} ({e.get('country')}, {at:%Y-%m-%d %H:%M}Z): forecast {e['fc']}, previous {e.get('prev') or 'n/a'}"); src.append('calendar:' + e.get('src', 'forexfactory'))
    syms = {((i.get('asset') or {}).get('px') or i.get('ticker') or '').upper() for i in story.get('impacts') or []} - {''}
    for e in (cal or {}).get('earnings') or []:
        try: d = datetime.fromisoformat(e['date'] + 'T12:00:00+00:00')
        except Exception: continue
        if e.get('s', '').upper() in syms and abs((d - t).days) <= 3 and e.get('eps'):
            lines.append(f"{e.get('n')} ({e['s']}) earnings {e['date']} {e.get('when') or ''}: consensus EPS {e['eps']}"); src.append('calendar:nasdaq-earnings')
    return ('\n'.join(lines[:6]), src)


def story_block(i, s, cal=None):
    text = ' '.join(x for x in [s.get('headline'), s.get('summary'), s.get('why_moved')] if x)
    known = [((x.get('asset') or {}).get('n') or x.get('name')) for x in s.get('impacts') or [] if x.get('asset')]
    cal_text, _ = calendar_expectations(s, cal)
    return (f"Story {i} ({s.get('published_at', '')[:16]}Z, {(s.get('source') or {}).get('name', '')}): {text}"
            + (f"\n  assets already identified: {', '.join(known[:6])}" if known else '')
            + (f"\n  calendar: {cal_text}" if cal_text else ''))


def build_prompt(stories, cal=None):
    return PROMPT.format(types=', '.join(P.TYPES), relations=', '.join(RELATIONS),
                         stories='\n'.join(story_block(k, s, cal) for k, s in enumerate(stories, 1)))


def _num(v):
    if v is None or isinstance(v, bool): return None
    try:
        x = float(str(v).replace(',', '').replace('%', '').replace('$', '').strip())
        return x if x == x and abs(x) < 1e12 else None
    except ValueError:
        return None


def validate(raw, n):
    """Parsed model output -> {story number: extraction} with only typed, bounded fields."""
    out = {}
    for o in raw if isinstance(raw, list) else []:
        if not isinstance(o, dict): continue
        try: k = int(o.get('i'))
        except (TypeError, ValueError): continue
        if not 1 <= k <= n or k in out: continue
        ex = o.get('expectations') if isinstance(o.get('expectations'), dict) else {}
        ca = o.get('catalyst') if isinstance(o.get('catalyst'), dict) else {}
        assets = []
        for a in o.get('assets') if isinstance(o.get('assets'), list) else []:
            if not isinstance(a, dict) or not isinstance(a.get('name'), str): continue
            tk = a.get('ticker') if isinstance(a.get('ticker'), str) and re.fullmatch(r'[A-Za-z0-9.^=_-]{1,32}', a['ticker']) else None
            assets.append({'name': a['name'][:80], 'ticker': tk, 'relation': a.get('relation') if a.get('relation') in RELATIONS else 'other',
                           'stance': {'positive': 1, 'negative': -1}.get(a.get('stance'), 0), 'reason': str(a.get('reason') or '')[:160]})
            if len(assets) == 4: break
        out[k] = {'event_type': o.get('event_type') if o.get('event_type') in P.TYPES else 'other',
                  'flags': [f for f, key in (('commentary', 'commentary'), ('preview', 'preview'), ('price-move-recap', 'price_move_recap'),
                                             ('competing-catalysts', 'competing_catalysts')) if o.get(key) is True],
                  'expectations': {**{x: _num(ex.get(x)) for x in EXPECT_KEYS}, 'higher_is': ex.get('higher_is') if ex.get('higher_is') in ('positive', 'negative') else None,
                                   'source': ex.get('source') if ex.get('source') in ('story', 'calendar') else None},
                  'catalyst': {x: _num(ca.get(x)) for x in CATALYST_KEYS},
                  'assets': assets, 'evidence': str(o.get('evidence') or '')[:300] or None}
    return out
