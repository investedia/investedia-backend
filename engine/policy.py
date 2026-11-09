"""Frozen v4 tables and decision policy (research/ENGINE-V4.md §4-§8, §10). Changing anything here = a new engine version.
Pure functions: no network, no clock. decide() turns an extracted event + asset + market context into Long / Short / No View."""
import hashlib, json, math

ENGINE = 'pe-v4'
OUTCOME_RULE = 'outcome-v4'
TYPES = ['earnings', 'guidance', 'm&a', 'financing', 'analyst', 'product', 'legal-regulatory', 'management', 'macro-data',
         'central-bank', 'geopolitical', 'commodity-supply', 'trade-tariff', 'crypto', 'other']
CLASSES = ['equity', 'index', 'fx', 'commodity', 'crypto']
# §5 horizons: S1/S2 = close of the 1st/2nd full session after entry; 'Nh' = hours (24/7, near-24 h markets); None = no calls
H = {'earnings': ('S1', 'S1', None, None, None), 'guidance': ('S1', 'S1', None, None, None), 'financing': ('S1', 'S1', None, None, None),
     'management': ('S1', 'S1', None, None, None), 'm&a': ('S1', None, None, None, None), 'analyst': ('S2', None, None, None, None),
     'product': ('S1', None, None, None, '24h'), 'legal-regulatory': ('S1', None, None, None, '24h'),
     'macro-data': ('S1', 'S1', '6h', '6h', '6h'), 'central-bank': ('S1', 'S1', '24h', '24h', '24h'),
     'geopolitical': ('S2', 'S2', '48h', '48h', '48h'), 'trade-tariff': ('S2', 'S2', '48h', '48h', '48h'),
     'commodity-supply': ('S2', 'S2', '48h', '48h', None), 'crypto': (None, None, None, None, '24h'),
     'other': ('S1', 'S1', '24h', '24h', '24h')}
ACQUIRER_HORIZON = 'S2'
FLOOR = {'equity': .3, 'index': .2, 'fx': .1, 'commodity': .3, 'crypto': .5}           # §10 class floors, % move
SURPRISE_FLOOR = {'eps': 2.0, 'revenue': 2.0, 'guidance': 1.0, 'rate_bp': 10.0}         # §7, % (rates in bp)
DIRECT = {'subject', 'target', 'acquirer', 'counterparty', 'policy-rate', 'commodity-output', 'issuer'}
# Product tiers (research/ENGINE-V4.md §2a): No View -> Market View -> Priority Insight (a labelled subset of Views).
PRICED_IN_SIGMA = 3.0          # asset already moved >= 3 sigma in the called direction before publication: No View (substantially priced in)
PRIORITY_PRICED_SIGMA = 1.5    # >= 1.5 sigma: still an View, never Priority
PRIORITY_CONTEXT_SIGMA = -1.0  # index/sector already moved >= 1 sigma AGAINST the call: never Priority
PRIORITY_MIN_MOVE_SIGMA = 1.0  # expected move must be >= 1 sigma of normal noise over the horizon
PRIORITY_RELATIONS = {'subject', 'target', 'issuer', 'policy-rate', 'commodity-output'}
POINTS = {'expectations': 2, 'big_surprise': 1, 'direct': 1, 'single_catalyst': 1, 'context_agrees': 1, 'stance_agrees': 1, 'strong_catalyst': 1}
NEEDS_EXPECTATIONS = {'earnings', 'guidance', 'macro-data', 'central-bank'}
# strong-catalyst table for types without consensus expectations (numbers as stated in the article; missing = not strong)
STRONG = {'m&a': ('premium_pct', 15), 'financing': ('size_pct_mcap', 5), 'legal-regulatory': ('amount_pct_mcap', 1), 'product': ('value_pct_revenue', 5),
          'analyst': ('rating_notches', 1), 'commodity-supply': ('supply_change_pct', 1), 'trade-tariff': ('tariff_change_pct', 10),
          'geopolitical': ('supply_at_risk_pct', 1), 'management': (None, None), 'crypto': ('amount_usd_bn', 1), 'other': (None, None)}
HARD = ['commentary', 'preview', 'price-move-recap', 'indirect', 'competing-catalysts', 'stance-neutral', 'unsupported-combination',
        'duplicate-event', 'priced-in', 'below-view-threshold']
PRIORITY_GATES = ['direct-subject', 'evidence', 'single-catalyst', 'not-priced-in', 'context-supports', 'move-above-noise', 'data-complete',
                  'type-enabled', 'priority-confidence']
POLICY_ID = hashlib.sha1(json.dumps([TYPES, H, ACQUIRER_HORIZON, FLOOR, SURPRISE_FLOOR, sorted(DIRECT), PRICED_IN_SIGMA, PRIORITY_PRICED_SIGMA,
                                     PRIORITY_CONTEXT_SIGMA, PRIORITY_MIN_MOVE_SIGMA, sorted(PRIORITY_RELATIONS), POINTS, sorted(NEEDS_EXPECTATIONS), STRONG],
                                    sort_keys=True).encode()).hexdigest()[:12]


def horizon(event_type, asset_class, relation=None):
    if event_type not in H or asset_class not in CLASSES: return None
    if event_type == 'm&a' and asset_class == 'equity' and relation == 'acquirer': return ACQUIRER_HORIZON
    return H[event_type][CLASSES.index(asset_class)]


def _pct(actual, expected):
    try:
        a, e = float(actual), float(expected)
        return None if e == 0 else (a - e) / abs(e) * 100
    except (TypeError, ValueError):
        return None


def surprise_sign(ev):
    """(sign, big, conflict) from structured expectations; sign 0 = no usable surprise. Missing values stay missing."""
    x = ev.get('expectations') or {}; t = ev.get('event_type')
    if t == 'central-bank':
        a, e = x.get('rate_actual'), x.get('rate_expected')
        if a is None or e is None: return 0, False, False
        bp = (float(a) - float(e)) * 100
        return (0, False, False) if abs(bp) < SURPRISE_FLOOR['rate_bp'] else (1 if bp > 0 else -1, abs(bp) >= 2 * SURPRISE_FLOOR['rate_bp'], False)
    if t == 'macro-data':
        a, e = x.get('actual'), x.get('expected')
        s = _pct(a, e)
        if s is None or s == 0: return 0, False, False
        return (1 if s > 0 else -1) * (1 if x.get('higher_is') != 'negative' else -1), abs(s) >= 10, False
    signs, big = [], False
    for k, fl in (('eps', SURPRISE_FLOOR['eps']), ('revenue', SURPRISE_FLOOR['revenue']), ('guidance', SURPRISE_FLOOR['guidance'])):
        s = _pct(x.get(k + '_actual'), x.get(k + '_expected'))
        if s is not None and abs(s) >= fl: signs.append((k, 1 if s > 0 else -1)); big = big or abs(s) >= 2 * fl
    if not signs: return 0, False, False
    vals = {v for _, v in signs}
    if len(vals) == 1: return signs[0][1], big, False
    g = [v for k, v in signs if k == 'guidance']
    return (g[0], big, False) if g else (0, False, True)


def strong_catalyst(ev):
    f, th = STRONG.get(ev.get('event_type'), (None, None))
    v = (ev.get('catalyst') or {}).get(f) if f else None
    try: return v is not None and abs(float(v)) >= th
    except (TypeError, ValueError): return False


def decide(ev, asset, ctx, th=None, calibrate=None, seen=(), type_enabled=None):
    """ev: extracted event {event_id, event_type, flags, expectations, catalyst}; asset: {id, cls, relation, stance (+1/-1/0), map};
    ctx: {pre_move_sigma, index_pre_sigma, sector_pre_sigma, expected_move_sigma} (signed, sigma units; None = unavailable).
    th: frozen thresholds {view, priority} on calibrated confidence (None before validation: tiers come from the rules only).
    Returns {decision long|short|none, view_tier none|standard|priority, reasons (why No View), priority_missing (gates not met), raw, confidence, horizon}."""
    t, cls, rel, flags = ev.get('event_type'), asset.get('cls'), asset.get('relation'), set(ev.get('flags') or [])
    out = {'decision': 'none', 'view_tier': 'none', 'reasons': [], 'tier_reasons': [], 'gates': {}, 'priority_missing': [], 'pending': [], 'raw': 0, 'confidence': None, 'horizon': horizon(t, cls, rel)}
    r = out['reasons']
    for f in ('commentary', 'preview', 'price-move-recap', 'competing-catalysts'):
        if f in flags: r.append(f)
    if out['horizon'] is None: r.append('unsupported-combination')
    if rel not in DIRECT: r.append('indirect')
    if (ev.get('event_id'), asset.get('id'), out['horizon']) in seen: r.append('duplicate-event')
    s, big, conflict = surprise_sign(ev)
    if conflict and 'competing-catalysts' not in r: r.append('competing-catalysts')
    stance = asset.get('stance') or 0
    uses_surprise = t in NEEDS_EXPECTATIONS and s != 0
    d = s * (asset.get('map') or 1) if uses_surprise else stance  # without expectations an View may still follow the stance
    if d == 0 and 'competing-catalysts' not in r: r.append('stance-neutral')
    pre = ctx.get('pre_move_sigma')
    if d and pre is not None and pre * d >= PRICED_IN_SIGMA: r.append('priced-in')
    strong = strong_catalyst(ev)
    raw = 0
    if uses_surprise: raw += POINTS['expectations'] + (POINTS['big_surprise'] if big else 0)
    if strong: raw += POINTS['strong_catalyst']
    if rel in DIRECT: raw += POINTS['direct']
    if 'competing-catalysts' not in r: raw += POINTS['single_catalyst']
    if d and pre is not None and pre * d < PRIORITY_PRICED_SIGMA: raw += POINTS['context_agrees']
    if d and stance and uses_surprise and stance == s: raw += POINTS['stance_agrees']
    out['raw'] = raw
    if calibrate: out['confidence'] = calibrate(raw, t)
    if not r and th and th.get('view') is not None and (out['confidence'] is None or out['confidence'] < th['view']): r.append('below-view-threshold')
    if r or not d:
        out['tier_reasons'] = list(r) or ['stance-neutral']
        return out
    out['decision'] = 'long' if d > 0 else 'short'; out['view_tier'] = 'standard'
    g = out['gates'] = {}  # every Priority gate individually: pass | fail | pending (not decidable yet, e.g. before validation)
    g['direct-subject'] = 'pass' if rel in PRIORITY_RELATIONS else 'fail'
    g['evidence'] = 'pass' if ((uses_surprise and big) or (t not in NEEDS_EXPECTATIONS and strong)) else 'fail'
    g['single-catalyst'] = 'fail' if 'competing-catalysts' in flags else 'pass'
    g['not-priced-in'] = 'fail' if (pre is None or pre * d >= PRIORITY_PRICED_SIGMA) else 'pass'
    g['context-supports'] = 'fail' if any(ctx.get(k) is not None and ctx[k] * d <= PRIORITY_CONTEXT_SIGMA for k in ('index_pre_sigma', 'sector_pre_sigma')) else 'pass'
    em = ctx.get('expected_move_sigma')
    g['move-above-noise'] = 'pass' if em is not None and em >= PRIORITY_MIN_MOVE_SIGMA else 'fail'
    g['data-complete'] = 'pass' if pre is not None and ctx.get('index_pre_sigma') is not None and ctx.get('sigma_daily') else 'fail'
    g['type-enabled'] = 'pending' if type_enabled is None else ('pass' if type_enabled(t) else 'fail')
    g['priority-confidence'] = 'pending' if not (th and th.get('priority') is not None) else ('pass' if out['confidence'] is not None and out['confidence'] >= th['priority'] else 'fail')
    out['priority_missing'] = [k for k in PRIORITY_GATES if g[k] == 'fail']
    out['pending'] = [k for k in PRIORITY_GATES if g[k] == 'pending']
    if not out['priority_missing']: out['view_tier'] = 'priority'  # pending gates do not block during shadow validation; they are recorded
    out['tier_reasons'] = out['priority_missing'] or ['all-gates-pass']
    return out


def meaningful(move_pct, cls, sigma_daily, horizon_days):
    """outcome-v4: the minimum move that counts as a hit or a miss."""
    return max(FLOOR.get(cls, .3), .5 * (sigma_daily or 0) * math.sqrt(max(horizon_days, .25)))
