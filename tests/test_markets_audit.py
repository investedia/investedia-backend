"""Offline policy/math tests. Synthetic FX curves are never exported as market data."""
import json,math,unittest
from datetime import date,timedelta
from pathlib import Path
from tools.markets_audit import methods as m
from tools.markets_audit import run
ROOT=Path(__file__).resolve().parents[1]

class IdentifierTests(unittest.TestCase):
 def test_reference_matching_and_no_name_merge(self):
  fixture=json.loads((ROOT/'tests/fixtures/markets-audit/matching.json').read_text())
  for case in fixture['cases']:
   result=m.match(case['left'],case['right']);self.assertEqual(result['status'],case['status'])
   if 'via' in case:self.assertEqual(result['via'],case['via']);self.assertFalse(result['publication_eligible'])
 def test_identifier_checksums_and_typed_scope(self):
  self.assertTrue(m.valid_isin('US0378331005'));self.assertFalse(m.valid_isin('US0378331006'))
  self.assertIsNone(m.normal_id('lei','0'*20));self.assertEqual(m.normal_id('cik','320193'),'0000320193')
  self.assertIsNone(m.normal_id('cik','0'));self.assertIsNone(m.normal_id('qid','Q0'))
  # A real-looking checksum validates format only, never allocation or a listing.
  payload='TEST'+'0'*14;digits=''.join(str(ord(c)-55) if c.isalpha() else c for c in payload)
  lei=payload+str(98-int(digits+'00')%97).zfill(2);self.assertEqual(m.normal_id('lei',lei),lei)
  a={'kind':'security','ids':{'isin':'US0378331005','cik':'320193'}}
  self.assertEqual(m.match(a,a)['reason'],'identifier_level_mismatch')
 def test_same_security_but_conflicting_issuer_is_quarantined(self):
  a={'kind':'security','ids':{'isin':'US0378331005'},'issuer_ids':{'cik':'320193'}}
  b={**a,'issuer_ids':{'cik':'789019'}};self.assertEqual(m.match(a,b)['status'],'conflict')
  b['issuer_ids']['cik']='not-a-cik';self.assertEqual(m.match(a,b)['status'],'unverified')

class FXTests(unittest.TestCase):
 def data(self):
  # Deliberately synthetic publication dates and levels, not real ECB observations.
  result={}
  for i in range(31):
   usd=1.2*(1+.05*math.sin(i/2));gbp=.8*(1+.002*math.sin(i));jpy=150*(1-.002*math.sin(i))
   result[(date(2026,1,1)+timedelta(days=i)).isoformat()]={'USD':usd,'GBP':gbp*usd,'JPY':jpy*usd,'DKK':7.46,'HKD':7.8*usd,'RUB':100}
  return result
 def pair(self,result,base):
  return next(p for p in result['bases'][base]['all_valid_pairs'] if p['currencies']==['GBP','JPY'])
 def test_common_base_effect_and_rebase_before_returns(self):
  out=m.fx_audit(self.data());self.assertGreater(self.pair(out,'EUR')['r'],.9);self.assertLess(self.pair(out,'USD')['r'],-.99)
  self.assertEqual(self.pair(out,'USD')['observations'],30);self.assertGreater(out['comparison']['sign_changes'],0)
  self.assertTrue(out['bases']['EUR']['positive']);self.assertTrue(out['bases']['USD']['negative'])
 def test_at_least_25_aligned_intervals_not_25_levels(self):
  data=self.data()
  for i in (10,15,20):data[(date(2026,1,1)+timedelta(days=i)).isoformat()].pop('GBP')
  result=m.fx_audit(data)
  self.assertFalse(any(p['currencies']==['GBP','JPY'] for p in result['bases']['USD']['all_valid_pairs']))
  short=dict(list(self.data().items())[:25]);self.assertEqual(m.fx_audit(short)['bases']['EUR']['all_valid_pairs'],[])
 def test_missing_days_are_not_forward_filled(self):
  data=self.data()
  for i in (10,11):data[(date(2026,1,1)+timedelta(days=i)).isoformat()].pop('GBP')
  self.assertEqual(self.pair(m.fx_audit(data),'USD')['observations'],27)
 def test_pegs_shared_currency_zero_variance_and_non_ecb_codes(self):
  result=m.fx_audit(self.data())
  for base in result['bases'].values():
   for pair in base['all_valid_pairs']:
    self.assertNotEqual(*pair['currencies']);self.assertNotIn('RUB',pair['currencies']);self.assertNotIn(frozenset(pair['currencies']),m.PEGS)
  self.assertIsNone(m.pearson([1]*30,list(range(30))))
  self.assertEqual(len(result['excluded']),2)
 def test_empty_sample_never_uses_math_fixtures_as_real_data(self):
  r=m.fx_audit({});self.assertIsNone(r['as_of']);self.assertEqual(r['status'],'insufficient_dated_ECB_observations')
  self.assertEqual(r['bases']['USD']['positive'],[])

class AuditScopeTests(unittest.TestCase):
 def test_coverage_is_all_countries_exchanges_and_unknown_not_fake_zero(self):
  report=run.coverage(ROOT);self.assertEqual(len(report['countries']),240);self.assertEqual(len(report['exchanges']),63)
  for row in report['countries']+report['exchanges']:
   self.assertIsNone(row['verified_licensed_equities']);self.assertIsNone(row['coverage_share']);self.assertIsNone(row['ownership_share_all_issuers'])
  self.assertFalse(report['approved_launch_countries'])
 def test_manual_only_workflow_no_secrets_or_writes(self):
  text=(ROOT/'.github/workflows/markets-audit.yml').read_text()
  self.assertIn('workflow_dispatch:',text);self.assertNotIn('schedule:',text);self.assertNotIn('secrets.',text);self.assertNotIn('contents: write',text);self.assertNotIn('deploy',text)
 def test_sec_units_period_and_document_join_preserved_no_values_inferred(self):
  # Minimal schema fixture, not a financial figure published to the product.
  facts={'facts':{'us-gaap':{'Assets':{'units':{'USD':[{'end':'2025-12-31','fy':2025,'fp':'FY','form':'10-K','accn':'0000000001-26-000001','val':42}]}}}}}
  r=run.sec_presence('0000000001',facts,{'filings':{'recent':{'accessionNumber':['0000000001-26-000001'],'primaryDocument':['actual.htm']}}})
  assets=r['concepts']['assets'];self.assertTrue(assets['present_in_sample']);self.assertIn('/actual.htm',assets['concepts'][0]['period_examples'][0]['filing_url'])
  self.assertFalse(r['concepts']['revenue']['present_in_sample']);self.assertEqual(assets['concepts'][0]['units'],['USD'])


class RunnerBoundaryTests(unittest.TestCase):
 def test_local_fetch_flag_is_rejected_before_any_download(self):
  import contextlib,io,os,sys
  from unittest.mock import patch
  with patch.dict(os.environ,{'GITHUB_ACTIONS':'false'}),patch.object(sys,'argv',['markets-audit','--fetch']),patch.object(run.Client,'get') as get,contextlib.redirect_stderr(io.StringIO()):
   with self.assertRaises(SystemExit):run.main()
   get.assert_not_called()

if __name__=='__main__':unittest.main()
