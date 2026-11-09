import json, sys, unittest
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import calendar_official as co

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
ICS = """BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART;TZID=US-Eastern:20261110T083000
SUMMARY:Consumer Price Index
END:VEVENT
BEGIN:VEVENT
DTSTART;TZID=US-Eastern:20261110T100000
SUMMARY:State Employment and Unemployment (Monthly)
END:VEVENT
BEGIN:VEVENT
DTSTART;TZID=US-Eastern:20250103T100000
SUMMARY:Employment Situation
END:VEVENT
END:VCALENDAR"""
BEA = ('<div class="release-date">October 29</div> <small class="text-muted">8:30 AM</small></td><td class="release-title x">'
       'GDP (Advance Estimate), 3rd Quarter 2026</td>'
       '<div class="release-date">December 23</div> <small class="text-muted">10:00 AM</small></td><td class="release-title x">'
       'Personal Income and Outlays, November 2026</td>')


class OfficialCalendar(unittest.TestCase):
    def test_bls_keeps_window_and_skips_regional(self):
        co._get = lambda url, headers: ICS
        ev = co.bls(NOW)
        self.assertEqual([e['t'] for e in ev], ['Consumer Price Index'])
        self.assertEqual(ev[0]['at'], '2026-11-10T13:30:00Z')  # 08:30 Eastern (EST) is 13:30 UTC
        self.assertEqual(ev[0]['imp'], 3)

    def test_bea_converts_eastern_time_across_dst(self):
        co._get = lambda url, headers: BEA
        ev = {e['t'][:3]: e for e in co.bea(NOW)}
        self.assertEqual(ev['GDP']['at'], '2026-10-29T12:30:00Z')  # EDT, UTC-4
        self.assertEqual(ev['GDP']['imp'], 3)
        self.assertEqual(ev['Per']['at'], '2026-12-23T15:00:00Z')  # EST, UTC-5

    def test_events_carry_no_invented_numbers(self):
        co._get = lambda url, headers: ICS
        e = co.bls(NOW)[0]
        self.assertEqual((e['actual'], e['fc'], e['prev']), ('', '', ''))

    def test_one_failing_source_does_not_block_others(self):
        orig = (co.bls, co.bea, co.fomc)
        try:
            co.bls = lambda now: (_ for _ in ()).throw(RuntimeError('blocked'))
            co.bea = lambda now: [{'t': 'x'}]
            co.fomc = lambda now: []
            events, failed = co.all_official(NOW)
        finally:
            co.bls, co.bea, co.fomc = orig
        self.assertEqual(len(events), 1)
        self.assertEqual(len(failed), 1)


class SavedFeeds(unittest.TestCase):
    def test_every_top30_coin_has_a_price_source(self):
        c = json.loads((ROOT / 'data/crypto-top30.json').read_text())['coins']
        self.assertEqual([x['rank'] for x in c], list(range(1, 31)))
        src = (ROOT / 'update_market.py').read_text()
        site = (ROOT / 'assets/mock.js').read_text()
        self.assertEqual([x['s'] for x in c if f'"{x["s"]}": "{x["yahoo"]}"' not in src], [])
        self.assertEqual([x['s'] for x in c if f"s: '{x['s']}'" not in site], [])


if __name__ == '__main__':
    unittest.main()
