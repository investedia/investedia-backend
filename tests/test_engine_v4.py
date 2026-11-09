"""Prediction Engine v4: frozen tables and the decision policy (research/ENGINE-V4.md)."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine import policy as P

A = lambda **k: {'id': 'EQ:X', 'cls': 'equity', 'relation': 'subject', 'stance': 1, **k}


class Policy(unittest.TestCase):
    def test_horizons(self):
        self.assertEqual(P.horizon('earnings', 'equity'), 'S1'); self.assertEqual(P.horizon('macro-data', 'fx'), '6h')
        self.assertEqual(P.horizon('m&a', 'equity', 'acquirer'), 'S2'); self.assertIsNone(P.horizon('earnings', 'crypto'))

    CTX = {'pre_move_sigma': 0.2, 'index_pre_sigma': 0.1, 'sector_pre_sigma': 0.0, 'expected_move_sigma': 1.4, 'sigma_daily': 2.0}

    def test_earnings_follow_surprise_not_tone_and_reach_priority(self):
        ev = {'event_type': 'earnings', 'event_id': 'e1', 'expectations': {'eps_actual': 1.10, 'eps_expected': 1.00}}
        d = P.decide(ev, A(stance=-1), self.CTX)
        self.assertEqual((d['decision'], d['view_tier']), ('long', 'priority'))  # beat by 10 % = long even if the article sounds negative

    def test_no_expectations_is_a_standard_view_not_priority(self):
        d = P.decide({'event_type': 'earnings', 'expectations': {}}, A(), self.CTX)
        self.assertEqual((d['decision'], d['view_tier']), ('long', 'standard')); self.assertIn('evidence', d['priority_missing'])

    def test_conflict_without_guidance_is_no_call(self):
        ev = {'event_type': 'earnings', 'expectations': {'eps_actual': 1.1, 'eps_expected': 1, 'revenue_actual': 90, 'revenue_expected': 100}}
        self.assertEqual(P.decide(ev, A(), self.CTX)['view_tier'], 'none')
        ev['expectations'].update(guidance_actual=105, guidance_expected=100)
        self.assertEqual(P.decide(ev, A(), self.CTX)['decision'], 'long')  # guidance breaks the tie

    def test_hard_no_calls(self):
        for ev, a, ctx, why in [({'event_type': 'product', 'flags': ['commentary']}, A(), {}, 'commentary'),
                                ({'event_type': 'product'}, A(relation='competitor'), {}, 'indirect'),
                                ({'event_type': 'product'}, A(), {'pre_move_sigma': 3.2}, 'priced-in'),
                                ({'event_type': 'crypto'}, A(), {}, 'unsupported-combination')]:
            d = P.decide(ev, a, ctx); self.assertEqual(d['view_tier'], 'none'); self.assertIn(why, d['reasons'])
        self.assertIn('duplicate-event', P.decide({'event_type': 'product', 'event_id': 'e'}, A(), {}, seen={('e', 'EQ:X', 'S1')})['reasons'])

    def test_priority_gates_from_structured_features_only(self):
        ev = {'event_type': 'm&a', 'catalyst': {'premium_pct': 30}}
        self.assertEqual(P.decide(ev, A(relation='target'), self.CTX)['view_tier'], 'priority')
        moved = P.decide(ev, A(relation='target'), {**self.CTX, 'pre_move_sigma': 2.0})
        self.assertEqual(moved['view_tier'], 'standard'); self.assertIn('not-priced-in', moved['priority_missing'])  # 1.5-3 sigma: View only
        against = P.decide(ev, A(relation='target'), {**self.CTX, 'index_pre_sigma': -1.5}); self.assertIn('context-supports', against['priority_missing'])
        small = P.decide({'event_type': 'm&a', 'catalyst': {'premium_pct': 5}}, A(relation='target'), self.CTX); self.assertIn('evidence', small['priority_missing'])
        self.assertEqual(P.decide({'event_type': 'm&a', 'catalyst': {'premium_pct': None}}, A(relation='target'), self.CTX)['view_tier'], 'standard')  # missing stays missing

    def test_thresholds_after_validation(self):
        cal = lambda raw, t: .55
        d = P.decide({'event_type': 'product'}, A(), self.CTX, th={'view': .6, 'priority': .7}, calibrate=cal); self.assertEqual(d['reasons'], ['below-view-threshold'])
        d = P.decide({'event_type': 'm&a', 'catalyst': {'premium_pct': 30}}, A(relation='target'), self.CTX, th={'view': .5, 'priority': .7}, calibrate=cal)
        self.assertEqual(d['view_tier'], 'standard'); self.assertIn('priority-confidence', d['priority_missing'])

    def test_every_gate_and_reason_is_stored(self):
        d = P.decide({'event_type': 'm&a', 'catalyst': {'premium_pct': 30}}, A(relation='target'), self.CTX)
        self.assertEqual(set(d['gates']), set(P.PRIORITY_GATES)); self.assertEqual(d['tier_reasons'], ['all-gates-pass'])
        self.assertEqual(d['pending'], ['type-enabled', 'priority-confidence'])  # recorded, not blocking during shadow validation
        s = P.decide({'event_type': 'earnings', 'expectations': {}}, A(), self.CTX); self.assertEqual(s['tier_reasons'], ['evidence']); self.assertEqual(s['gates']['evidence'], 'fail')
        n = P.decide({'event_type': 'product', 'flags': ['preview']}, A(), {}); self.assertEqual(n['tier_reasons'], ['preview'])

    def test_policy_id_is_stable(self):
        self.assertEqual(len(P.POLICY_ID), 12)


if __name__ == '__main__':
    unittest.main()
