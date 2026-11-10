import importlib.util,json,unittest
from datetime import date,time
from pathlib import Path
s=importlib.util.spec_from_file_location('hours',Path(__file__).resolve().parents[1]/'tools/coverage/exchange_hours.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class HoursTests(unittest.TestCase):
 def test_effective_hours_are_selected_without_guessing(self):
  self.assertEqual(m.active_time([(None,time(9)),(date(2026,1,1),time(9,30))],date(2026,11,10)),'09:30:00')
  self.assertIsNone(m.active_time([],date(2026,11,10)))
 def test_saved_calendar_hours_have_source_timezone_and_dated_holidays(self):
  import zoneinfo
  data=json.loads((m.ROOT/'data/exchanges.json').read_text());venues=[x for x in data.values() if x.get('calendar')]
  self.assertGreater(len(venues),20)
  for row in venues:
   zoneinfo.ZoneInfo(row['timezone']);self.assertEqual(row['calendar']['licence'],'Apache-2.0')
   self.assertTrue(row['calendar']['source_url']);self.assertTrue(row['sessions'])
   for session in row['calendar']['dated_sessions']:
    self.assertGreater(session['close'],session['open'])
  # US Thanksgiving is closed, following day is an early close in the recorded library calendar.
  ny={x['date']:x for x in data['XNYS']['calendar']['dated_sessions']}
  self.assertNotIn('2026-11-26',ny);self.assertIn('13:00:00',ny['2026-11-27']['close'])
if __name__=='__main__':unittest.main()
