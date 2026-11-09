import sys, unittest, urllib.error
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import calendar_fred as cf

NOW = datetime(2026, 11, 10, 15, 0, tzinfo=timezone.utc)
KEY = 'abcdef0123456789abcdef0123456789'


def obs(*pairs):
    return {'observations': [{'date': d, 'value': v} for d, v in pairs]}


def cpi_event(**kw):
    return {'t': 'Consumer Price Index', 'c': 'USD', 'at': '2026-11-10T13:30:00Z', 'imp': 3, 'type': 'economic', 'actual': '', 'fc': '', 'prev': '', 'src': 'BLS', **kw}


class FakeFred:
    """Replaces calendar_fred._get; records calls and answers from a table keyed by (path, realtime_start)."""
    def __init__(self, table): self.table, self.calls = table, []
    def __call__(self, path, params, key):
        self.calls.append((path, dict(params), key))
        r = self.table.get((path, params.get('realtime_start')), self.table.get((path, None)))
        if isinstance(r, Exception): raise r
        return r


class Base(unittest.TestCase):
    def setUp(self): self._orig = cf._get
    def tearDown(self): cf._get = self._orig


class NoKey(Base):
    def test_without_a_key_nothing_is_called(self):
        cf._get = FakeFred({})
        new, failed, note = cf.enrich([cpi_event()], NOW, key='')
        self.assertEqual((new, failed), ([], []))
        self.assertIn('skipped', note)
        self.assertEqual(cf._get.calls, [])


class FillActuals(Base):
    # Latest observation as known the day before the release vs the day of the release.
    OLD = obs(('2026-09-01', '320.0'), ('2026-08-01', '319.0'), ('2026-07-01', '318.0'))
    NEW = obs(('2026-10-01', '321.28'), ('2026-09-01', '320.0'), ('2026-08-01', '319.0'))

    def test_cpi_actual_and_previous_are_month_over_month_percent(self):
        cf._get = FakeFred({('series/observations', '2026-11-10'): self.NEW, ('series/observations', '2026-11-09'): self.OLD})
        ev = cpi_event(); n, failed = cf.fill_actuals([ev], NOW, KEY)
        self.assertEqual((n, failed), (1, []))
        self.assertEqual(ev['actual'], '0.4% m/m')   # 321.28 / 320.0 - 1
        self.assertEqual(ev['prev'], '0.3% m/m')     # 320.0 / 319.0 - 1

    def test_not_published_yet_leaves_actual_empty(self):
        cf._get = FakeFred({('series/observations', '2026-11-10'): self.OLD, ('series/observations', '2026-11-09'): self.OLD})
        ev = cpi_event(); n, _ = cf.fill_actuals([ev], NOW, KEY)
        self.assertEqual((n, ev['actual']), (0, ''))

    def test_existing_previous_and_actual_are_never_overwritten(self):
        cf._get = FakeFred({('series/observations', '2026-11-10'): self.NEW, ('series/observations', '2026-11-09'): self.OLD})
        ev = cpi_event(prev='0.2% m/m'); cf.fill_actuals([ev], NOW, KEY)
        self.assertEqual(ev['prev'], '0.2% m/m')
        done = cpi_event(actual='0.5% m/m'); cf.fill_actuals([done], NOW, KEY)
        self.assertEqual(done['actual'], '0.5% m/m')

    def test_jobs_report_shows_the_change_in_thousands(self):
        cf._get = FakeFred({('series/observations', '2026-11-06'): obs(('2026-10-01', '160142'), ('2026-09-01', '160000'), ('2026-08-01', '159900')),
                            ('series/observations', '2026-11-05'): obs(('2026-09-01', '160000'), ('2026-08-01', '159900'), ('2026-07-01', '159800'))})
        ev = cpi_event(t='Employment Situation', at='2026-11-06T13:30:00Z'); n, _ = cf.fill_actuals([ev], NOW, KEY)
        self.assertEqual((n, ev['actual'], ev['prev']), (1, '+142K jobs', '+100K jobs'))

    def test_missing_values_and_too_few_observations_are_skipped(self):
        cf._get = FakeFred({('series/observations', '2026-11-10'): obs(('2026-10-01', '.'), ('2026-09-01', '320')), ('series/observations', '2026-11-09'): self.OLD})
        ev = cpi_event(); n, _ = cf.fill_actuals([ev], NOW, KEY)
        self.assertEqual((n, ev['actual']), (0, ''))

    def test_only_recent_official_events_are_touched(self):
        cf._get = FakeFred({})
        old = cpi_event(at='2026-10-01T13:30:00Z'); future = cpi_event(at='2026-11-12T13:30:00Z'); ff = cpi_event(src=''); other = cpi_event(t='Retail Sales')
        n, _ = cf.fill_actuals([old, future, ff, other], NOW, KEY)
        self.assertEqual((n, cf._get.calls), (0, []))


class ReleaseDates(Base):
    PAYLOAD = {'release_dates': [
        {'release_id': 9, 'release_name': 'Advance Monthly Sales for Retail and Food Services', 'date': '2026-11-17'},
        {'release_id': 13, 'release_name': 'G.17 Industrial Production and Capacity Utilization', 'date': '2026-11-17'},
        {'release_id': 99, 'release_name': 'Some Obscure Regional Survey', 'date': '2026-11-18'},
        {'release_id': 9, 'release_name': 'Advance Monthly Sales for Retail and Food Services', 'date': 'bad'},
    ]}

    def test_only_listed_releases_become_date_only_rows(self):
        cf._get = FakeFred({('releases/dates', '2026-11-10'): self.PAYLOAD})
        new = cf.release_events(NOW, KEY, [])
        self.assertEqual([e['t'] for e in new], ['US retail sales', 'US industrial production'])
        e = new[0]
        self.assertEqual((e['at'], e['dateOnly'], e['src'], e['actual'], e['fc'], e['prev']), ('2026-11-17T12:00:00Z', True, 'FRED', '', '', ''))

    def test_asks_for_the_next_120_days_including_future_dates(self):
        cf._get = FakeFred({('releases/dates', '2026-11-10'): {'release_dates': []}}); cf.release_events(NOW, KEY, [])
        p = cf._get.calls[0][1]
        self.assertEqual((p['realtime_start'], p['realtime_end'], p['include_release_dates_with_no_data']), ('2026-11-10', '2027-03-10', 'true'))

    def test_one_date_per_release_per_month(self):
        rows = [{'release_name': 'New Residential Construction', 'date': d} for d in ('2026-11-18', '2026-11-25', '2026-12-17')]
        cf._get = FakeFred({('releases/dates', '2026-11-10'): {'release_dates': rows}})
        self.assertEqual([e['at'][:10] for e in cf.release_events(NOW, KEY, [])], ['2026-11-18', '2026-12-17'])

    def test_releases_already_listed_by_another_source_are_not_duplicated(self):
        cf._get = FakeFred({('releases/dates', '2026-11-10'): self.PAYLOAD})
        existing = [{'t': 'Retail Sales m/m', 'c': 'USD', 'at': '2026-11-17T13:30:00Z'}]
        self.assertEqual([e['t'] for e in cf.release_events(NOW, KEY, existing)], ['US industrial production'])


class Safety(Base):
    def test_errors_never_contain_the_key_or_url(self):
        def boom(req, timeout=0): raise urllib.error.HTTPError(req.full_url, 400, 'Bad Request', {}, None)
        orig = urllib.request.urlopen; urllib.request.urlopen = boom
        try:
            with self.assertRaises(cf.FredError) as cm: cf._get('releases/dates', {}, KEY)
        finally: urllib.request.urlopen = orig
        self.assertNotIn(KEY, str(cm.exception)); self.assertNotIn('http', str(cm.exception)); self.assertIn('400', str(cm.exception))

    def test_one_failing_call_does_not_block_the_other(self):
        cf._get = FakeFred({('releases/dates', '2026-11-10'): cf.FredError('releases/dates: HTTP 500'),
                            ('series/observations', '2026-11-10'): FillActuals.NEW, ('series/observations', '2026-11-09'): FillActuals.OLD})
        ev = cpi_event(); new, failed, note = cf.enrich([ev], NOW, key=KEY)
        self.assertEqual((new, ev['actual']), ([], '0.4% m/m'))
        self.assertEqual(failed, ['releases/dates: HTTP 500'])


import urllib.request  # noqa: E402  (used by Safety)
if __name__ == '__main__': unittest.main()
