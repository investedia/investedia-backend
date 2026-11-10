"""Offline synthetic inputs; no provider calls and no cloud publication."""
import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from tools.markets_pilot.registry import build,reconcile,coverage,fiscal_year,fx_relationships
from tools.markets_pilot.fetch import Downloads,confirmed_ogl,sec_directory,OGL,wikidata
from tools.markets_pilot.publish import plan,execute

FIXTURE=Path(__file__).parent/'fixtures/markets-pilot/input.json'
class MarketsPilotTests(unittest.TestCase):
 def setUp(self):
  self.raw=json.loads(FIXTURE.read_text());self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def test_duplicate_tickers_across_exchanges_stay_separate(self):
  m=reconcile(self.raw);same=[x for x in m['listings'].values() if x['ticker']=='SAME']
  self.assertEqual({'XNYS','XLON'},{x['mic'] for x in same});self.assertEqual(2,len({x['id'] for x in same}))
 def test_multi_listings_link_one_security_and_issuer(self):
  rows=[x for x in reconcile(self.raw)['listings'].values() if x['ticker']=='DUAL']
  self.assertEqual(2,len(rows));self.assertEqual(1,len({x['security_id'] for x in rows}));self.assertEqual(1,len({x['issuer_id'] for x in rows}))
 def test_no_invented_isin_or_lei(self):
  r=next(x for x in reconcile(self.raw)['listings'].values() if x['mic']=='XLON')
  self.assertIsNone(r['isin']);self.assertIsNone(r['lei']);self.assertTrue(r['isin_reason'])
 def test_name_only_matching_is_rejected(self):
  row=copy.deepcopy(self.raw['wikidata'][0]);row.update(issuer_qid='Q999999',cik=None,lei=None,mic='XLON',isin=None,security_qid=None,ticker='OTHER')
  self.raw['wikidata'].append(row);m=reconcile(self.raw)
  self.assertEqual(5,len(m['issuers']));self.assertEqual(2,len([e for e in m['entities'].values() if e['name']=='Unit issuer one']))
 def test_delisted_not_in_search_posting_lists(self):
  m,path=build(self.raw,self.root);api=json.loads((path/'api-manifest.json').read_text());ids=json.loads((path/api['filters']['all:all']).read_text())
  records=json.loads((path/'records.json').read_text());old=next(r for r in records['listings'].values() if r['ticker']=='OLD')
  self.assertFalse(old['active']);self.assertNotIn(old['id'],ids)
 def test_security_conflicts_not_selected(self):
  self.raw['wikidata'][2]['isin']=self.raw['wikidata'][0]['isin'];m=reconcile(self.raw)
  self.assertTrue(m['conflicts']);self.assertTrue(all(r['verification_status']=='conflicted' for r in m['listings'].values() if r['ticker'] in {'SAME','DUAL'} and r['country']=='US'))
 def test_identifier_conflict_quarantined(self):
  extra=copy.deepcopy(self.raw['wikidata'][0]);extra['lei']='INVALID';self.raw['wikidata'].append(extra)
  m=reconcile(self.raw);self.assertTrue(m['conflicts']);self.assertTrue(all(r['verification_status']=='conflicted' for r in m['listings'].values() if r['ticker']=='DUAL'))
 def test_unknown_security_type_hidden_unverified(self):
  self.raw['wikidata'][0]['security_type']=None;self.raw['wikidata'][1]['security_type']=None
  rows=[r for r in reconcile(self.raw)['listings'].values() if r['ticker']=='DUAL'];self.assertTrue(all(r['verification_status']=='unverified' for r in rows))
 def test_known_fund_excluded(self):
  for r in self.raw['wikidata'][:2]:r['security_type']='fund'
  self.assertFalse(any(r['ticker']=='DUAL' for r in reconcile(self.raw)['listings'].values()))
 def test_coverage_uses_unique_cik_not_listing_count(self):
  c=coverage(reconcile(self.raw));self.assertEqual(3,c['US']['listing_issuer_denominator']);self.assertAlmostEqual(200/3,c['US']['issuer_coverage_pct']);self.assertIsNone(c['GB']['issuer_coverage_pct']);self.assertIsNone(c['GB']['sector_pct_of_verified'])
 def test_failed_ingest_retains_last_good(self):
  build(self.raw,self.root);old=(self.root/'last-good.json').read_bytes();self.raw['sec']['submissions'].clear()
  with self.assertRaises(ValueError):build(self.raw,self.root)
  self.assertEqual(old,(self.root/'last-good.json').read_bytes())
 def test_older_snapshot_does_not_prune_its_active_version(self):
  first,p=build(self.raw,self.root)
  self.raw['snapshot']['retrieved_at']='2026-11-11T12:00:00Z';second,q=build(self.raw,self.root)
  self.raw['snapshot']['retrieved_at']='2026-11-09T12:00:00Z';third,r=build(self.raw,self.root)
  self.assertTrue(r.exists());self.assertTrue(q.exists());self.assertFalse(p.exists())
  self.assertEqual(third['version'],json.loads((self.root/'last-good.json').read_text())['version'])
 def test_repeat_build_is_immutable(self):
  m,p=build(self.raw,self.root);first=(p/'records.json').read_bytes();again,q=build(self.raw,self.root)
  self.assertEqual(m['version'],again['version']);self.assertEqual(p,q);self.assertEqual(first,(q/'records.json').read_bytes())
 def test_all_typed_records_have_provenance(self):
  _,p=build(self.raw,self.root);m=json.loads((p/'records.json').read_text())
  for kind in ('entities','issuers','securities','listings','exchanges'):
   for r in m[kind].values():self.assertTrue(all(r[k] for k in ('source','source_id','retrieved_at','validation_status')))
 def test_fixture_cannot_be_published(self):
  _,p=build(self.raw,self.root)
  with self.assertRaisesRegex(ValueError,'not_eligible'):plan(p,'unit-bucket','a'*32)
 def test_failed_upload_never_activates_pointer(self):
  calls=[]
  def runner(args,**kwargs):calls.append(args);return SimpleNamespace(returncode=1)
  with self.assertRaisesRegex(ValueError,'pointer_not_changed'):execute([['wrangler','r2','object','put','unit']],{},'a'*32,self.root/'pointer.json',runner)
  self.assertEqual(1,len(calls));self.assertFalse((self.root/'pointer.json').exists())
 def test_activation_is_last(self):
  calls=[]
  def runner(args,**kwargs):calls.append(args);return SimpleNamespace(returncode=0)
  execute([['wrangler','r2','object','put','unit']],{'version':'unit'},'a'*32,self.root/'pointer.json',runner)
  self.assertEqual('markets:current',calls[-1][4]);self.assertEqual('r2',calls[0][1])
 def test_checksum_tampering_rejected_by_publish_plan(self):
  _,p=build(self.raw,self.root)
  m=json.loads((p/'manifest.json').read_text());m['fixture']=False;m['publication_eligible']=True
  (p/'manifest.json').write_text(json.dumps(m));(p/'coverage.json').write_text('{}')
  with self.assertRaisesRegex(ValueError,'checksum'):plan(p,'unit-bucket','a'*32)
 def test_unapproved_source_hosts_rejected(self):
  d=Downloads(self.root)
  for host in ('www.nasdaqtrader.com','www.jse.co.za','ngxgroup.com','www.b3.com.br','www.nseindia.com'):
   with self.assertRaisesRegex(ValueError,'not_approved'):d.allowed('https://'+host+'/file')
 def test_download_budget_stops_before_saving_excess_bytes(self):
  d=Downloads(self.root,max_bytes=3)
  d.client=SimpleNamespace(get=lambda url:(b'1234',{}))
  with self.assertRaisesRegex(ValueError,'budget_exceeded'):d.small('https://www.sec.gov/unit','unit.json')
  self.assertFalse((self.root/'unit.json').exists())
 def test_companies_house_footer_not_licence_confirmation(self):
  self.assertFalse(confirmed_ogl('Free Company Data Product'+(' ' * 500)+'Open Government Licence '+OGL))
  self.assertTrue(confirmed_ogl('Free Company Data Product is under the Open Government Licence v3.0 '+OGL))
 def test_sec_directory_uses_approved_paired_file_only(self):
  rows=sec_directory({'fields':['cik','name','ticker','exchange'],'data':[[320193,'unit','DUAL','NYSE'],[320193,'unit','DUAL','Nasdaq'],[320193,'unit','DUAL','OTC']]})
  self.assertEqual(2,len(rows));self.assertTrue(all(r['cik']=='0000320193' for r in rows))
 def annual(self):
  sub=self.raw['sec']['submissions']['0000320193'];r=sub['filings']['recent'];acc=r['accessionNumber'][0];end=r['reportDate'][0]
  facts={'facts':{'us-gaap':{}}}
  for k in ('Revenues','NetIncomeLoss','Assets','Liabilities'):
   row={'val':10,'accn':acc,'end':end,'form':'10-K','fp':'FY','fy':2025}
   if k in ('Revenues','NetIncomeLoss'):row['start']='2024-10-01'
   facts['facts']['us-gaap'][k]={'units':{'USD':[row]}}
  return sub,facts
 def test_sec_keeps_period_currency_and_accession(self):
  sub,facts=self.annual();r=fiscal_year(facts,sub)['data'];self.assertEqual('2024-10-01',r['period']['start']);self.assertEqual('USD',r['currency'])
  for fact in r['facts'].values():self.assertEqual('10-K',fact['form']);self.assertEqual(r['period']['accession'],fact['accession']);self.assertIn('sec.gov/Archives/',fact['filing_url'])
 def test_sec_does_not_mix_quarter_or_currency(self):
  sub,facts=self.annual();row=facts['facts']['us-gaap']['Revenues']['units']['USD'][0];row['start']='2025-07-01'
  r=fiscal_year(facts,sub);self.assertIsNone(r['data']['facts']['Revenues']['value'])
  facts['facts']['us-gaap']['Assets']['units']={'GBP':facts['facts']['us-gaap']['Assets']['units']['USD']}
  self.assertIsNone(fiscal_year(facts,sub)['data'])
 def test_wikidata_keeps_conflicting_optional_identifier_claims(self):
  b={k:{'value':v} for k,v in {'item':'http://www.wikidata.org/entity/Q100','issuer':'http://www.wikidata.org/entity/Q200','venue':'http://www.wikidata.org/entity/Q171240','ticker':'UNIT','statement':'urn:unit:statement','stock':'true','lei':'HWUPKR0MPOU8FGXBT394','classLabel':'share'}.items()}
  other=copy.deepcopy(b);other['lei']['value']='conflicting-source-claim'
  class Fake:
   def small(self,*args):return json.dumps({'results':{'bindings':[b,other]}}).encode()
  rows=wikidata(Fake());self.assertEqual(2,len(rows));self.assertEqual({'stock'},{r['security_type'] for r in rows})
  b['classLabel']['value']='preferred stock';other['classLabel']['value']='preferred stock'
  self.assertTrue(all(r['security_type']=='non_stock' for r in wikidata(Fake())))
 def test_fx_excludes_pegged_and_euro_currencies(self):
  f=fx_relationships({});self.assertEqual('USD',f['base']);self.assertTrue({'EUR','DKK','BGN','CZK','HKD'}<=set(f['excluded_currencies']));self.assertEqual([],f['relationships'])
if __name__=='__main__':unittest.main()
