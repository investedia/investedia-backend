import importlib.util
import unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('audit',Path(__file__).resolve().parents[1]/'tools/coverage/audit.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class AuditTests(unittest.TestCase):
 def test_missing_and_invalid_prices_are_not_coverage(self):
  a={'px':'X'}
  for v in [None,0,-1,float('nan'),True]:self.assertFalse(m.price_available(a,{'X':{'p':v}}))
  self.assertTrue(m.price_available(a,{'X':{'p':1.2}}))
 def test_real_snapshot_audit_covers_all_globe_shapes_and_unknown_30d(self):
  r=m.generate(m.ROOT,{},m.date('2026-11-10T00:00:00Z'),{})
  names={x[0] for x in m.read(m.ROOT/'assets/globe/countries-50m.json')}
  self.assertEqual({x['country'] for x in r['countries']},names)
  self.assertGreater(len(names),170)
  for c in r['countries']:
   self.assertIsNone(c['news']['30']['exact_count']);self.assertFalse(c['news']['30']['complete_window'])
if __name__=='__main__':unittest.main()
