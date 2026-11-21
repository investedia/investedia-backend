import importlib.util
import unittest
import hashlib,json,sys,tempfile
from unittest.mock import patch,MagicMock
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
class AuditInputTests(unittest.TestCase):
 def invoke(self,*args,fetch=None):
  with tempfile.TemporaryDirectory() as folder:
   argv=['audit.py',*args,'--output',folder]
   with patch.object(sys,'argv',argv),patch.object(m,'generate',return_value={'totals':{}}) as generate,patch.object(m,'markdown',return_value='Test-only audit report'),patch('builtins.print'),patch.object(m,'fetch_api',side_effect=fetch) as api:
    m.main()
    return generate.call_args.args,api.call_args_list
 def test_saved_input_records_provenance_without_network(self):
  path=m.ROOT/'assets/globe/news-live.json'
  args,calls=self.invoke('--live',str(path))
  self.assertEqual(calls,[])
  self.assertEqual(args[3]['requested_status'],'not_probed')
  self.assertEqual(args[3]['input_file'],str(path))
  self.assertEqual(args[3]['input_sha256'],hashlib.sha256(json.dumps(args[1],sort_keys=True).encode()).hexdigest())
  self.assertNotIn('diagnostic_source',args[3])
 def test_fetch_records_actual_success(self):
  args,calls=self.invoke('--fetch',fetch=lambda url:{'data':{'stories':[]}})
  self.assertEqual(args[3]['requested_status'],'ok');self.assertEqual(len(calls),1)
 def test_fallback_requires_explicit_opt_in(self):
  with self.assertRaises(OSError):self.invoke('--fetch',fetch=OSError('Test-only outage'))
  args,calls=self.invoke('--fetch','--diagnostic-fallback',fetch=[OSError('Test-only outage'),{'data':{'stories':[]}}])
  self.assertEqual(len(calls),2);self.assertEqual(args[3]['requested_status'],'blocked_or_unavailable')
  self.assertEqual(args[3]['diagnostic_status'],'ok')
 def test_inputs_must_be_unambiguous(self):
  for args in [[],['--live','fixture.json','--fetch'],['--live','fixture.json','--diagnostic-fallback']]:
   with self.subTest(args=args),patch.object(sys,'argv',['audit.py',*args]),patch('sys.stderr'),self.assertRaises(SystemExit):m.main()
 def test_fetch_rejects_unsafe_addresses_without_network(self):
  with patch.object(m.urllib.request,'build_opener') as opener:
   for url in ['http://example.test','https://user:password@example.test','https://example.test?token=test-only']:
    with self.assertRaises(ValueError):m.fetch_api(url)
   opener.assert_not_called()
 def test_fetch_bounds_response_size_and_refuses_redirects(self):
  response=MagicMock();response.__enter__.return_value=response;response.read.return_value=b'x'*5_000_001
  with patch.object(m.urllib.request,'build_opener') as opener:
   opener.return_value.open.return_value=response
   with self.assertRaisesRegex(ValueError,'too_large'):m.fetch_api('https://example.test/news')
   response.read.assert_called_once_with(5_000_001)
  with self.assertRaisesRegex(ValueError,'redirect_requires_review'):m.NoRedirect().redirect_request()

if __name__=='__main__':unittest.main()
