"""Prediction Engine v4 runner: extraction + registry + market context -> frozen shadow records (research/ENGINE-V4.md §9).
One record per (story, asset) the extraction names, including No View records with their reasons, so coverage is measurable.
"""
import hashlib
from engine import policy as P, magnitude as M
from engine.extract import PROMPT_ID

CLASS = {'equity': 'equity', 'index': 'index', 'fx': 'fx', 'commodity': 'commodity', 'crypto': 'crypto'}
MAP = {('macro-data', 'fx'): 1, ('macro-data', 'index'): -1, ('macro-data', 'commodity'): -1, ('central-bank', 'fx'): 1,
       ('central-bank', 'index'): -1, ('central-bank', 'commodity'): -1, ('central-bank', 'equity'): -1}  # §7 macro/rates asset mapping


def records(story, ex, resolve, context_of, event_id, start_iso, start_ts, seen, model=None, calendar_sources=()):
    """story: news story; ex: validated extraction; resolve(asset) -> registry asset or None; context_of(asset, start_ts) -> ctx dict."""
    out = []
    for a in ex['assets']:
        reg = resolve(a)
        rid = 'v4-' + hashlib.sha1(f"{story['id']}|{(reg or {}).get('id') or a['name']}".encode()).hexdigest()[:12]
        rec = {'id': rid, 'event_id': event_id, 'article_id': story['id'], 'headline': (story.get('headline') or '')[:160], 'start': start_iso,
               'start_ts': start_ts, 'engine': P.ENGINE, 'prompt': PROMPT_ID, 'policy': P.POLICY_ID, 'model': model, 'outcome_rule': P.OUTCOME_RULE,
               'calibration': None, 'event_type': ex['event_type'], 'flags': ex['flags'], 'expectations': ex['expectations'],
               'expectations_available': any(ex['expectations'].get(k) is not None for k in ('eps_expected', 'revenue_expected', 'guidance_expected', 'expected', 'rate_expected')),
               'expectation_sources': list(calendar_sources), 'catalyst': ex['catalyst'], 'evidence': ex['evidence'],
               'asset_name': a['name'], 'ticker': a['ticker'], 'relation': a['relation'], 'stance': a['stance'], 'stance_reason': a['reason']}
        if not reg or CLASS.get(reg.get('class')) is None:
            rec.update(asset_id=None, view_tier='none', decision='none', reasons=['unsupported-combination' if reg else 'unresolved-asset'],
                       tier_reasons=['unsupported-combination' if reg else 'unresolved-asset'])
            out.append(rec); continue
        cls = CLASS[reg['class']]
        ctx = context_of(reg, start_ts) or {}
        ev = {'event_id': event_id, 'event_type': ex['event_type'], 'flags': ex['flags'], 'expectations': ex['expectations'], 'catalyst': ex['catalyst']}
        asset = {'id': reg['id'], 'cls': cls, 'relation': a['relation'], 'stance': a['stance'], 'map': MAP.get((ex['event_type'], cls), 1)}
        pre = P.decide(ev, asset, ctx, seen=seen)  # first pass for the direction, then the expected move, then the gates
        mag = M.expected(ex['event_type'], pre['horizon'], ctx.get('sigma_daily'), pre['decision'], P.strong_catalyst(ev) or P.surprise_sign(ev)[1])
        ctx2 = {**ctx, 'expected_move_sigma': mag['move_sigma'] if mag else None}
        d = P.decide(ev, asset, ctx2, seen=seen)
        if d['decision'] != 'none': seen.add((event_id, reg['id'], d['horizon']))
        rec.update(asset_id=reg['id'], symbol=reg.get('px'), cls=cls, horizon=d['horizon'], decision=d['decision'], view_tier=d['view_tier'],
                   reasons=d['reasons'], tier_reasons=d['tier_reasons'], gates=d['gates'], pending_gates=d['pending'], raw_score=d['raw'],
                   confidence=d['confidence'], magnitude=mag if d['decision'] != 'none' else None, context=ctx2, benchmark=ctx.get('benchmark'))
        out.append(rec)
    return out
