import json, os, tempfile, unittest
from datetime import datetime, timezone, timedelta
import update_news_track as t

NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
# outcome-v2 judges from exchange bars; in tests the recorded series stands in for them
FX = lambda series: (lambda sym, t0, t1: [(p[0] * 60, p[1]) for p in series.get(sym, []) if t0 <= p[0] * 60 <= t1])


def story(ticker, hours_ago):
    return {'published_at': (NOW - timedelta(hours=hours_ago)).strftime('%Y-%m-%dT%H:%M:%SZ'), 'impacts': [{'ticker': ticker}]}


class Track(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        t.G = self.dir

    def write(self, name, obj):
        with open(os.path.join(self.dir, name), 'w') as f:
            json.dump(obj, f)

    def test_resolve_uses_site_aliases(self):
        known = {'BTC-USD', 'EURUSD', 'META'}
        self.assertEqual(t.resolve('btc', known), 'BTC-USD')
        self.assertEqual(t.resolve('EURUSD=X', known), 'EURUSD')
        self.assertEqual(t.resolve('meta', known), 'META')
        self.assertIsNone(t.resolve('NOPE', known))
        self.assertIsNone(t.resolve(None, known))

    def test_only_recent_stories_count(self):
        known = {'A', 'B'}
        self.assertEqual(t.tracked_symbols([story('A', 5), story('B', 100)], known, NOW), {'A'})

    def test_adds_one_point_per_new_asof_and_not_twice(self):
        self.write('markets.json', {'asof': '2026-10-26T11:50:00+00:00', 'assets': [{'s': 'A', 'p': 10.123456789}]})
        self.write('news-live.json', {'stories': [story('A', 2)]})
        data, note = t.update(NOW)
        self.assertEqual(list(data['s']), ['A'])
        self.assertEqual(len(data['s']['A']), 1)
        self.assertEqual(data['s']['A'][0][1], 10.1235)
        self.write('news-track.json', data)
        data2, note2 = t.update(NOW)
        self.assertEqual(note2, 'unchanged')
        self.assertEqual(len(data2['s']['A']), 1)
        self.write('markets.json', {'asof': '2026-10-26T12:05:00+00:00', 'assets': [{'s': 'A', 'p': 10.5}]})
        data3, _ = t.update(NOW + timedelta(minutes=6))
        self.assertEqual([p[1] for p in data3['s']['A']], [10.1235, 10.5])

    def test_drops_old_points_and_unreferenced_assets(self):
        self.write('markets.json', {'asof': '2026-10-26T12:00:00+00:00', 'assets': [{'s': 'A', 'p': 1.0}, {'s': 'B', 'p': 2.0}]})
        self.write('news-live.json', {'stories': [story('A', 1)]})
        old_min = int((NOW - timedelta(hours=80)).timestamp() // 60)
        self.write('news-track.json', {'asof': 'x', 's': {'A': [[old_min, 0.9]], 'B': [[old_min, 2.0]]}})
        data, _ = t.update(NOW)
        self.assertEqual(list(data['s']), ['A'])
        self.assertEqual([p[1] for p in data['s']['A']], [1.0])

    def test_no_prices_keeps_previous(self):
        self.write('news-live.json', {'stories': [story('A', 1)]})
        data, note = t.update(NOW)
        self.assertIsNone(data)

    def test_news_prices_file_is_used_for_assets_missing_from_markets(self):
        self.write('markets.json', {'asof': '2026-10-26T12:00:00+00:00', 'assets': [{'s': 'A', 'p': 1.0}]})
        self.write('news-prices.json', {'assets': {'EB5.SI': {'p': 3.64}}})
        self.write('news-live.json', {'stories': [story('EB5.SI', 1)]})
        data, _ = t.update(NOW)
        self.assertEqual(data['s']['EB5.SI'][0][1], 3.64)


class Ledger(unittest.TestCase):
    PUB = NOW - timedelta(hours=30)
    pm = staticmethod(lambda dt: int(dt.timestamp() // 60))

    def st(self, direction, sid='n1', ticker='A', scorable=True, created=None):
        c = (created or self.PUB).strftime('%Y-%m-%dT%H:%M:%SZ')
        return {'id': sid, 'category': 'markets', 'published_at': self.PUB.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'impacts': [{'ticker': ticker, 'name': 'Asset A', 'direction': direction, 'confidence': 'medium', 'created_at': c, 'version': 'impact-gemini-v1',
                             'horizon': '24h', 'baseline_rule': 'x', 'scorable': scorable and direction in ('up', 'down')}]}

    def series(self, end_price, end_hours=25):
        pm = self.pm
        return {'A': [[pm(self.PUB + timedelta(minutes=10)), 100.0], [pm(self.PUB + timedelta(hours=end_hours)), end_price]]}

    def judge(self, story, series):
        ledger = {'schema': 2, 'calls': []}
        t.freeze([story], series, ledger, NOW, self.PUB)
        n = t.judge(series, ledger, NOW, fetch=FX(series))
        return n, ledger['calls']

    def test_hit_miss_flat(self):
        self.assertEqual(self.judge(self.st('up'), self.series(103))[1][0]['res'], 'hit')
        self.assertEqual(self.judge(self.st('down'), self.series(103))[1][0]['res'], 'miss')
        self.assertEqual(self.judge(self.st('up'), self.series(100.1))[1][0]['res'], 'flat')
        self.assertEqual(self.judge(self.st('down'), self.series(97))[1][0]['res'], 'hit')

    def test_mixed_unclear_and_unstamped_are_not_calls(self):
        self.assertEqual(self.judge(self.st('mixed'), self.series(103))[1], [])
        self.assertEqual(self.judge(self.st('unclear'), self.series(103))[1], [])
        legacy = self.st('up'); del legacy['impacts'][0]['created_at']; del legacy['impacts'][0]['scorable']
        self.assertEqual(self.judge(legacy, self.series(103))[1], [])

    def test_backfilled_implications_are_never_scored(self):
        self.assertEqual(self.judge(self.st('up', scorable=False), self.series(103))[1], [])

    def test_frozen_before_24_hours_and_judged_later(self):
        young = self.st('up', created=NOW - timedelta(hours=5))
        n, calls = self.judge(young, self.series(103))
        self.assertEqual(n, 0)
        self.assertEqual(calls[0]['res'], 'pending')
        self.assertEqual(self.judge(self.st('up'), self.series(103, end_hours=10))[1][0]['res'], 'pending')  # no price 24 h later yet
        self.assertEqual(self.judge(self.st('up'), self.series(103, end_hours=60))[1][0]['res'], 'pending')  # first later price too far away

    def test_prediction_cannot_change_after_freezing(self):
        ledger = {'schema': 2, 'calls': []}
        t.freeze([self.st('up')], self.series(103), ledger, NOW, self.PUB)
        flipped = self.st('down')  # the story is edited afterwards
        t.freeze([flipped], self.series(103), ledger, NOW, self.PUB)
        t.judge(self.series(103), ledger, NOW, fetch=FX(self.series(103)))
        self.assertEqual(len(ledger['calls']), 1)
        self.assertEqual(ledger['calls'][0]['dir'], 'up')
        self.assertEqual(ledger['calls'][0]['res'], 'hit')

    def test_a_call_is_only_judged_once(self):
        ledger = {'schema': 2, 'calls': []}
        t.freeze([self.st('up')], self.series(103), ledger, NOW, self.PUB)
        self.assertEqual(t.judge(self.series(103), ledger, NOW, fetch=FX(self.series(103))), 1)
        self.assertEqual(t.judge(self.series(90), ledger, NOW, fetch=FX(self.series(90))), 0)
        self.assertEqual(ledger['calls'][0]['move'], 3.0)

    def test_late_first_price_is_not_judged(self):
        pm = self.pm
        late = {'A': [[pm(self.PUB + timedelta(hours=5)), 100.0], [pm(self.PUB + timedelta(hours=26)), 110.0]]}
        self.assertEqual(self.judge(self.st('up'), late)[0], 0)

    def test_schema1_ledger_is_kept_and_marked_legacy(self):
        d = tempfile.mkdtemp(); t.G = d
        old = {'schema': 1, 'calls': [{'id': 'old', 'sym': 'A', 'dir': 'up', 'res': 'hit', 'move': 1.0}]}
        for name, obj in (('news-ledger.json', old), ('markets.json', {'asof': '2026-10-26T12:00:00+00:00', 'assets': [{'s': 'A', 'p': 1.0}]}),
                          ('news-live.json', {'stories': [self.st('up', created=NOW - timedelta(hours=1))]})):
            with open(os.path.join(d, name), 'w') as f: json.dump(obj, f)
        data, _ = t.update(NOW)
        led = data['_ledger']
        self.assertEqual(led['schema'], 2)
        self.assertTrue(led['calls'][0]['legacy'])
        self.assertEqual(led['calls'][0]['res'], 'hit')
        self.assertEqual(led['calls'][1]['res'], 'pending')


if __name__ == '__main__':
    unittest.main()
