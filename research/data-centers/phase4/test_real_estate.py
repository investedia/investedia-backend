import copy,json,sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from sector_adapter import validate,public_projection
class RealEstateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.data=json.loads((P/'real-estate-pilot.json').read_text());cls.rows=cls.data['projects']
 def test_ten_individual_candidates_not_ten_investments(self):
  self.assertEqual(len(self.rows),10);self.assertEqual(len({r['id'] for r in self.rows}),10);self.assertEqual(self.data['counts']['verified_property_investment_routes'],0)
 def test_only_three_developer_claims(self):
  self.assertEqual(sum(r['exposures'][0]['role']=='developer' for r in self.rows),3)
  self.assertEqual(sum(r['exposures'][0]['role']=='affiliation' for r in self.rows),7)
 def test_five_source_audits_not_invented_properties(self):
  self.assertEqual(len(self.data['companies']),5)
  for c in self.data['companies']:
   if c['name'] in {'Goodman Group','Prologis'}:self.assertEqual(c['property_records'],0)
 def test_common_contract_works_for_real_estate(self):
  for r in self.rows:self.assertTrue(validate(r))
 def test_all_unknown_points_excluded_from_site_imagery(self):
  for r in self.rows:self.assertEqual(r['location']['precision'],'unknown');self.assertIsNone(r['location']['lat']);self.assertEqual(r['imagery'],[])
 def test_no_research_property_published(self):
  for r in self.rows:
   with self.assertRaises(ValueError):public_projection(r)
 def test_distinct_tiel_buildings_share_context_not_identity(self):
  a,b=[r for r in self.rows if r['city']=='Tiel'];self.assertNotEqual(a['id'],b['id']);self.assertEqual(a['asset']['parent_id'],b['asset']['parent_id']);self.assertEqual(a['asset']['category'],'building')
 def test_no_ownership_or_direct_investment_inferred(self):
  for r in self.rows:
   e=r['exposures'][0];self.assertIsNone(e['property_stake']);self.assertFalse(e['investment_access']['verified']);self.assertNotIn(e['role'],{'direct_property_owner','indirect_property_owner'})
 def test_property_evidence_has_exact_document_hash(self):
  for r in self.rows:self.assertRegex(r['identity_evidence']['sha256'],r'^[0-9a-f]{64}$');self.assertTrue(r['identity_evidence']['locator'])
 def test_available_land_not_completed_building(self):
  for r in self.rows:
   if r['id'] in {'re:montea-echt','re:montea-combronde','re:montea-puurs','re:montea-grimbergen'}:self.assertEqual(r['status']['stage'],'planning')
if __name__=='__main__':unittest.main()
