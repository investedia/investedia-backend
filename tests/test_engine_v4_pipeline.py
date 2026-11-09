"""Engine v4 pipeline: extraction validation, publication-time context (no look-ahead), outcome-v4 exits, runner records."""
import os, sys, unittest
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine import extract as X, context as C, outcome as O, magnitude as M, run as RUN

E = lambda s: datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()


def session(day, o=14.5, c=21.0, p0=100.0, step=0.0):
    t, out, p = E(day + 'T00:00') + o * 3600, [], p0
    while t <= E(day + 'T00:00') + c * 3600: out.append((t, p)); t += 300; p += step
    return out


class Extraction(unittest.TestCase):
    def test_validate_keeps_only_typed_fields(self):
        raw = [{'i': 1, 'event_type': 'earnings', 'commentary': False, 'preview': 'yes', 'expectations': {'eps_actual': '1.10', 'eps_expected': '$1.00', 'source': 'story', 'higher_is': 'up'},
                'catalyst': {'premium_pct': '25%'}, 'assets': [{'name': 'Intel', 'ticker': 'INTC', 'relation': 'subject', 'stance': 'negative'}, {'name': 'X', 'ticker': 'bad ticker!', 'relation': 'boss'}]},
               {'i': 9}, {'i': 1, 'event_type': 'earnings'}]
        v = X.validate(raw, 2)
        self.assertEqual(list(v), [1]); e = v[1]
        self.assertEqual(e['expectations']['eps_actual'], 1.1); self.assertEqual(e['expectations']['eps_expected'], 1.0); self.assertIsNone(e['expectations']['higher_is'])
        self.assertEqual(e['flags'], []); self.assertEqual(e['catalyst']['premium_pct'], 25.0); self.assertIsNone(e['catalyst']['size_pct_mcap'])
        self.assertEqual(e['assets'][0]['stance'], -1); self.assertIsNone(e['assets'][1]['ticker']); self.assertEqual(e['assets'][1]['relation'], 'other')

    def test_calendar_expectations_are_injected_only_when_relevant(self):
        cal = {'events': [{'t': 'CPI y/y', 'country': 'US', 'at': '2026-10-30T12:30:00Z', 'fc': '3.1%', 'prev': '3.0%', 'src': 'BLS'},
                          {'t': 'GDP', 'country': 'US', 'at': '2026-10-20T12:30:00Z', 'fc': '2%'}], 'earnings': [{'s': 'INTC', 'n': 'Intel', 'date': '2026-10-30', 'eps': '$0.20'}]}
        s = {'published_at': '2026-10-30T13:00:00Z', 'location': {'country': 'United States of America'}, 'impacts': [{'ticker': 'INTC'}]}
        txt, src = X.calendar_expectations(s, cal)
        self.assertIn('CPI y/y', txt); self.assertNotIn('GDP', txt); self.assertIn('consensus EPS $0.20', txt); self.assertEqual(len(src), 2)
        self.assertIn('{', X.PROMPT); self.assertEqual(len(X.PROMPT_ID), 12)
        self.assertEqual(X.calendar_expectations({**s, 'location': {'country': 'Brazil'}}, {'events': cal['events']})[0], '')  # other economies get no macro consensus


class Context(unittest.TestCase):
    def test_no_look_ahead_and_sigma_units(self):
        daily = [(E(f'2026-10-{d:02d}T21:00'), 100 * (1.01 if d % 2 else 1)) for d in range(1, 30)]
        bars = session('2026-10-30', p0=101, step=0.01)
        t = E('2026-10-30T16:00')
        f = C.features(t, bars + [(E('2026-10-30T20:00'), 500.0)], daily)
        self.assertLess(f['price'], 200)  # the later 500 print is never read
        self.assertIsNotNone(f['sigma_daily']); self.assertAlmostEqual(f['pre_move_sigma'], f['pre_move_pct'] / f['sigma_daily'], 2)
        self.assertEqual(C.sector_etf('3674'), 'XLK'); self.assertEqual(C.sector_etf('2834'), 'XLV'); self.assertIsNone(C.sector_etf(None))


    def test_weekend_publication_measures_the_last_session(self):
        daily = [(E(f'2026-10-{d:02d}T13:30'), 100.0) for d in range(1, 30)] + [(E('2026-10-30T13:30'), 110.0)]
        bars = session('2026-10-30', p0=110)
        f = C.features(E('2026-10-31T12:00'), bars, daily)  # Saturday: Friday closed at 110 vs Thursday 100
        self.assertEqual(f['session'], 'closed'); self.assertAlmostEqual(f['pre_move_pct'], 10.0, 1)


class Outcome(unittest.TestCase):
    def test_s1_is_the_close_of_the_first_full_session_after_entry(self):
        bars = session('2026-10-29', p0=100) + session('2026-10-30', p0=101, step=.01)
        v = {'start_ts': E('2026-10-29T20:00'), 'decision': 'long', 'horizon': 'S1', 'cls': 'equity', 'context': {'sigma_daily': 1.0}, 'magnitude': {'expected_pct': 1.0}}
        o = O.judge(v, bars + [(E('2026-11-02T14:30'), 102)], E('2026-11-02T15:00'))
        self.assertEqual(o['exit'][0], int(bars[-1][0])); self.assertEqual(o['res'], 'hit')
        self.assertIsNone(O.judge(v, bars, E('2026-10-30T22:00')))  # last session not known to be closed yet

    def test_hours_horizon_relative_move_and_magnitude_error(self):
        bars = [(E('2026-10-30T12:00') + k * 300, 100 + k * .01) for k in range(200)]
        idx = [(E('2026-10-30T11:00') + k * 300, 50 + k * .02) for k in range(220)]
        v = {'start_ts': E('2026-10-30T12:00'), 'decision': 'short', 'horizon': '6h', 'cls': 'fx', 'context': {'sigma_daily': 0.2}, 'magnitude': {'expected_pct': -0.5}}
        o = O.judge(v, bars, E('2026-10-31T00:00'), index_bars=idx)
        self.assertEqual(o['res'], 'miss'); self.assertIsNotNone(o['relative_move_pct']); self.assertIsNotNone(o['magnitude_error_pct'])

    def test_magnitude_range(self):
        m = M.expected('earnings', 'S1', 2.0, 'short', True); self.assertLess(m['high_pct'], m['low_pct']); self.assertEqual(m['move_sigma'], 2.25)


class Runner(unittest.TestCase):
    def test_records_include_no_view_with_reasons_and_gates(self):
        ex = {'event_type': 'earnings', 'flags': [], 'expectations': {'eps_actual': 1.1, 'eps_expected': 1.0}, 'catalyst': {}, 'evidence': 'EPS $1.10 vs $1.00',
              'assets': [{'name': 'Intel', 'ticker': 'INTC', 'relation': 'subject', 'stance': -1, 'reason': ''}, {'name': 'Unknown Co', 'ticker': None, 'relation': 'subject', 'stance': 1, 'reason': ''}]}
        reg = {'Intel': {'id': 'EQ:XNAS:INTC', 'class': 'equity', 'px': 'INTC'}}
        recs = RUN.records({'id': 'n1', 'headline': 'h'}, ex, lambda a: reg.get(a['name']), lambda r, t: {'sigma_daily': 2.0, 'pre_move_sigma': 0.1, 'index_pre_sigma': 0.0},
                           'e1', '2026-10-30T20:00:00Z', 0, set())
        a, b = recs
        self.assertEqual((a['decision'], a['view_tier']), ('long', 'priority')); self.assertEqual(set(a['gates'].values()) - {'pass', 'pending'}, set())
        self.assertEqual(b['view_tier'], 'none'); self.assertEqual(b['tier_reasons'], ['unresolved-asset'])
        for k in ('engine', 'policy', 'prompt', 'outcome_rule', 'expectations_available', 'magnitude', 'context'): self.assertIn(k, a)


if __name__ == '__main__':
    unittest.main()


class Shadow(unittest.TestCase):
    def test_frozen_records_are_never_rewritten_and_judged_once(self):
        from engine import shadow as SH
        L = SH.load('/nonexistent')
        rec = {'id': 'v4-1', 'view_tier': 'standard', 'decision': 'long', 'horizon': '6h', 'cls': 'fx', 'start_ts': E('2026-10-30T12:00'), 'symbol': 'X',
               'context': {'sigma_daily': 0.2}, 'magnitude': {'expected_pct': 0.3}, 'benchmark': {}}
        self.assertEqual(SH.freeze(L, [rec], 't1'), 1); self.assertEqual(SH.freeze(L, [{**rec, 'decision': 'short'}], 't2'), 0)
        self.assertEqual(L['records'][0]['decision'], 'long')
        bars = [(E('2026-10-30T12:00') + k * 300, 100 + k * .01) for k in range(200)]
        self.assertEqual(SH.judge(L, E('2026-10-31T00:00'), fetch=lambda s, a, b: bars), 1)
        first = dict(L['records'][0]['outcome'])
        SH.judge(L, E('2026-11-01T00:00'), fetch=lambda s, a, b: [(t, p * 2) for t, p in bars]); self.assertEqual(L['records'][0]['outcome'], first)
