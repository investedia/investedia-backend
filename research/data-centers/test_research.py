import copy,importlib.util,json,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('dc_research',HERE/'build.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ResearchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.data=json.loads((HERE/'dataset.json').read_text())
 def edge(self):return copy.deepcopy(self.data['edges'][0])
 def record(self):return copy.deepcopy(next(r for r in self.data['records'] if r['id']==self.data['edges'][0]['project']))
 def test_real_packet_integrity(self):
  for key in json.loads((HERE/'source-packets.json').read_text()):m.packet(key)
 def test_current_common_equity_identity_resolved_with_cik_and_exchange(self):
  registry=json.loads((m.ROOT/'data/registry.json').read_text());sec=m.packet('sec')[0];result=m.listed_companies(registry,sec)
  self.assertEqual(set(result),{'EQ:XNAS:EQIX','EQ:XNYS:DLR','EQ:XNYS:AMT'})
  for row in result.values():self.assertTrue(any('Common Stock' in t for t in row['security_class_evidence']['cover_row']['security_titles']))
  sec['data'][0][sec['fields'].index('cik')]=0
  with self.assertRaises(ValueError):m.listed_companies(registry,sec)
 def test_name_alone_and_ticker_collision_never_match(self):
  r=self.record();e=self.edge();e['to']='EQ:XNAS:DLR'
  with self.assertRaises(ValueError):m.validate_link(r,e,self.data['companies'])
  e['to']='Digital Realty'
  with self.assertRaises(ValueError):m.validate_link(r,e,self.data['companies'])
 def test_preferred_stock_or_notes_cannot_substitute_common_equity(self):
  companies=copy.deepcopy(self.data['companies']);companies[self.edge()['to']]['security_type']='preferred_equity'
  with self.assertRaises(ValueError):m.validate_link(self.record(),self.edge(),companies)
 def test_shareholders_are_not_direct_project_investors(self):
  for kind in ['direct_investor','owner','developer','power_supplier','headquarters']:
   e=self.edge();e['kind']=kind
   with self.assertRaises(ValueError):m.validate_link(self.record(),e,self.data['companies'])
  e=self.edge();e['exposure']='direct_project_equity'
  with self.assertRaises(ValueError):m.validate_link(self.record(),e,self.data['companies'])
 def test_no_invented_stake_or_unbound_source(self):
  for field,val in [('ownership_pct',100),('evidence_sha256','wrong'),('project','another-phase')]:
   e=self.edge();e[field]=val
   with self.assertRaises(ValueError):m.validate_link(self.record(),e,self.data['companies'])
 def test_incomplete_parent_chain_stays_internal_and_contradictions_rejected(self):
  for category in ['C','D']:
   r=self.record();r['category']=category
   with self.assertRaises(ValueError):m.validate_link(r,self.edge(),self.data['companies'])
  va=next(r for r in self.data['records'] if r['facility_code']=='VA1');self.assertEqual(va['category'],'C')
  self.assertFalse(any(e['project']==va['id'] for e in self.data['edges']))
 def test_observed_dublin_country_conflicts_not_silently_corrected(self):
  rows=[r for r in self.data['records'] if r['facility_code'] in ['DUB1','DUB10']]
  self.assertEqual(len(rows),2)
  for r in rows:self.assertEqual(r['country'],'United Kingdom');self.assertEqual(r['category'],'D');self.assertIn('Ireland',r['coordinates']['country_screen'])
 def test_no_guessed_coordinates_status_units_cost_or_imagery(self):
  for r in self.data['records']:
   self.assertIsNone(r.get('status'));self.assertIsNone(r.get('capacity'));self.assertIsNone(r.get('cost'));self.assertIsNone(r.get('imagery'))
   if r.get('coordinates'):self.assertFalse(r['coordinates']['exact_site_verified'])
 def test_no_duplicate_stable_ids_and_no_counts_as_construction_phases(self):
  ids=[r['id'] for r in self.data['records']];self.assertEqual(len(ids),len(set(ids)))
  self.assertTrue(all('record' in r['granularity'] for r in self.data['records']))
 def test_licensing_holds_prevent_public_export(self):
  self.assertEqual(self.data['counts']['public_eligible'],0)
  self.assertTrue(all(not r['public_eligible'] for r in self.data['records']))
  out=json.loads((HERE/'projects-v2-research.json').read_text())
  self.assertEqual(out['schema'],'investedia.projects.v2')
  self.assertTrue(all(r['validation_status']=='research_only' and r['own']==[] for r in out['projects']))
 def test_no_secret_values_or_prices_in_outputs(self):
  text=(HERE/'dataset.json').read_text()+ (HERE/'preview/data.json').read_text()
  for token in ['GEMINI_API_KEY','NEWS_INGEST_TOKEN','service_role','"price"','"daily_change"']:self.assertNotIn(token,text)
 def test_nonofficial_sources_and_unimplemented_regulatory_chains_fail_closed(self):
  r=self.record();r['evidence'][0]['url']='https://unrelated.test/project'
  with self.assertRaises(ValueError):m.validate_link(r,self.edge(),self.data['companies'])
  r=self.record();r['category']='B'
  with self.assertRaises(ValueError):m.validate_link(r,self.edge(),self.data['companies'])
 def test_graph_carries_exact_evidence_and_no_geometry_proximity_edges(self):
  for edge in self.data['edges']:
   r=next(r for r in self.data['records'] if r['id']==edge['project']);self.assertTrue(m.validate_link(r,edge,self.data['companies']))
   self.assertFalse(edge['direct_project_investment_verified']);self.assertIsNone(edge['ownership_pct'])

if __name__=='__main__':unittest.main()
