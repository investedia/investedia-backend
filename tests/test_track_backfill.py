import os, sys, unittest
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import update_track_backfill as b

ts = lambda y, m, d, h=13: int(datetime(y, m, d, h, 30, tzinfo=timezone.utc).timestamp())
BARS = [[ts(2026, 10, 19), 0, 0, 0, 100.0, 0], [ts(2026, 10, 20), 0, 0, 0, 100.0, 0], [ts(2026, 10, 21), 0, 0, 0, 103.0, 0], [ts(2026, 10, 22), 0, 0, 0, 102.0, 0]]


class Daily(unittest.TestCase):
    def test_uses_the_article_day_close_then_the_next_close(self):
        self.assertEqual(b.judge_daily(ts(2026, 10, 20, 15), 'up', BARS), (3.0, 'hit'))
        self.assertEqual(b.judge_daily(ts(2026, 10, 20, 15), 'down', BARS), (3.0, 'miss'))
        self.assertEqual(b.judge_daily(ts(2026, 10, 21, 15), 'down', BARS), (-0.97, 'hit'))

    def test_small_moves_are_no_clear_move(self):
        bars = [[ts(2026, 10, 20), 0, 0, 0, 100.0, 0], [ts(2026, 10, 21), 0, 0, 0, 100.2, 0]]
        self.assertEqual(b.judge_daily(ts(2026, 10, 20), 'up', bars)[1], 'flat')

    def test_not_judged_until_the_next_session_exists(self):
        self.assertIsNone(b.judge_daily(ts(2026, 10, 22, 15), 'up', BARS))

    def test_article_on_a_non_session_day_uses_the_last_close_before_it(self):
        sat = ts(2026, 10, 24, 10)
        bars = BARS + [[ts(2026, 10, 26), 0, 0, 0, 110.0, 0]]
        self.assertEqual(b.judge_daily(sat, 'up', bars), (7.84, 'hit'))

    def test_run_only_finishes_frozen_pending_calls_and_never_creates_calls(self):
        import json, tempfile
        d = tempfile.mkdtemp(); g = os.path.join(d, 'g'); h = os.path.join(d, 'h'); os.makedirs(g); os.makedirs(h)
        json.dump({'assets': [{'s': 'AAA', 'site': 'AAA', 'n': 'Aaa'}]}, open(os.path.join(g, 'markets.json'), 'w'))
        json.dump({'daily': BARS}, open(os.path.join(h, 'AAA.json'), 'w'))
        # an archived story with an implication but no frozen call: must NOT become a call
        json.dump({'stories': [{'id': 'story', 'published_at': '2026-10-20T15:00:00Z', 'impacts': [{'ticker': 'AAA', 'direction': 'up'}]}]}, open(os.path.join(g, 'news-archive.json'), 'w'))
        call = lambda i, t, **k: {'id': i, 'sym': 'AAA', 'dir': 'up', 'created': t, 'res': 'pending', **k}
        json.dump({'schema': 2, 'calls': [call('old', '2026-10-20T15:00:00Z'), call('young', '2026-10-24T10:00:00Z'), call('legacy', '2026-10-20T15:00:00Z', legacy=True)]},
                  open(os.path.join(g, 'news-ledger.json'), 'w'))
        b.G, b.HIST, b.ROOT = g, h, d  # never touch the real site files
        self.assertEqual(b.run(False, datetime(2026, 10, 22, 16, tzinfo=timezone.utc))[0], 0)  # 49 h: still the live recorder's
        n, led = b.run(True, datetime(2026, 10, 24, 16, tzinfo=timezone.utc))
        self.assertEqual(n, 1)
        by = {c['id']: c for c in led['calls']}
        self.assertEqual(len(led['calls']), 3)
        self.assertEqual((by['old']['res'], by['old']['basis'], by['old']['dir']), ('hit', 'daily', 'up'))
        self.assertEqual(by['young']['res'], 'pending')
        self.assertEqual(by['legacy']['res'], 'pending')
        self.assertEqual(b.run(True, datetime(2026, 10, 24, 17, tzinfo=timezone.utc))[0], 0)  # never judged twice


if __name__ == '__main__':
    unittest.main()
