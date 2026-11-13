import copy,importlib.util,json,unittest,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('phase2',P/'build_phase2.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Phase2Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.d=json.loads((P/'phase2-dataset.json').read_text());cls.projects=cls.d['development_records'];cls.original=cls.d['original_records']
 def project(self,needle):return next(p for p in self.projects if needle in p['id'])
 def test_old_affiliations_do_not_automatically_become_economic_links(self):
  dlr=[r for r in self.original if r['company']=='EQ:XNYS:DLR' and r['original_category']=='A']
  self.assertEqual(len(dlr),23);self.assertTrue(all(not r['economic_relationships'] for r in dlr))
 def test_owned_and_leased_are_distinct_and_both_economic(self):
  bycode={r['facility_code']:r for r in self.original}
  for code,role in [('DC2','property_owner'),('SV1','property_owner'),('DX1','lessee')]:
   r=bycode[code];self.assertEqual(r['economic_relationships'][0]['role'],role);self.assertIsNone(r['legal_property_owner'])
  r=copy.deepcopy(bycode['DX1']);c=copy.deepcopy(r['economic_relationships'][0]);c['role']='property_owner'
  with self.assertRaises(ValueError):m.validate_relationship(c,r,self.d['companies'])
 def test_no_property_percentage_from_business_jv_share(self):
  va=next(r for r in self.original if r['facility_code']=='VA1');self.assertEqual(va['jv']['AMT_common_equity_pct'],64)
  c=copy.deepcopy(va['economic_relationships'][0]);c['ownership_pct']=64
  with self.assertRaises(ValueError):m.validate_relationship(c,va,self.d['companies'])
  for r in self.projects+self.original:
   for c in r['economic_relationships']:self.assertIsNone(c['ownership_pct'])
 def test_current_conversion_does_not_use_obsolete_71_29(self):
  chains=self.d['business_chains'];operating=[c for c in chains if c['to']=='CoreSite US operating data-center business'];self.assertEqual(sorted(c['share_pct'] for c in operating),[36,64])
  denver=[c for c in chains if 'Denver' in c['to']];self.assertTrue(all(c['share_pct'] is None for c in denver))
 def test_parent_programmes_not_counted_as_projects_and_ids_unique(self):
  self.assertEqual(len(self.projects),32);self.assertEqual(sum(p['count_as_project'] for p in self.projects),26)
  self.assertEqual(len({p['id'] for p in self.projects}),len(self.projects))
  for p in self.projects:
   if p.get('parent_id'):self.assertFalse(next(r for r in self.projects if r['id']==p['parent_id'])['count_as_project'])
 def test_phase_capacity_and_campus_capacity_not_added_or_copied(self):
  phase=self.project('polaris-forge-1:building-2-phase-1');self.assertEqual(phase['capacity']['value'],75)
  campus=next(r for r in self.projects if r['id']=='project:apld:polaris-forge-1');self.assertEqual(campus['capacity']['value'],400)
  de3=self.project('coresite:DE3');self.assertEqual(de3['capacity']['value'],18);self.assertEqual(de3['campus_metric']['capacity'],60);self.assertIsNone(de3['project_area']);self.assertEqual(len(de3['area_claims']),2)
 def test_contract_revenue_and_note_proceeds_not_project_cost(self):
  delta=self.project('delta-forge-2');self.assertEqual(delta['contracted_revenue']['value'],5200000000);self.assertIsNone(delta['cost'])
  building=self.project('polaris-forge-1:building-3');self.assertEqual(building['financing']['value'],1590000000);self.assertIsNone(building['cost'])
 def test_future_and_past_targets_do_not_invent_completion(self):
  for p in self.projects:
   if p['status']=='announced' and p.get('expected_completion','') and p['expected_completion']<'2026-Q4':self.assertIn('target_warning',p)
  self.assertEqual(self.project('eqix:SG6')['status'],'opened');self.assertIsNone(self.project('eqix:SG6')['expected_completion']);self.assertTrue(self.project('eqix:SG6')['source_conflicts'])
 def test_timing_warning_and_partial_deliveries_preserved(self):
  self.assertIn('under assessment',self.project('Osaka-5x-1')['timing_warning'])
  self.assertEqual(self.project('building-2-phase-2')['status'],'ready for service 2026-10-01')
 def test_common_equity_unmapped_route_has_no_fabricated_registry_id(self):
  co=self.d['companies']['external:SEC:CIK0001144879:APLD'];self.assertEqual(co['security_type'],'common_equity');self.assertIsNone(co['registry_asset_id'])
  p=self.project('delta-forge-1');self.assertTrue(p['investment_route']['verified']);self.assertIsNone(p['investment_route']['registry_asset_id'])
 def test_name_collision_wrong_ticker_preferred_and_aggregate_links_rejected(self):
  r=self.original[-1] if self.original[-1]['economic_relationships'] else next(x for x in self.original if x['economic_relationships']);c=copy.deepcopy(r['economic_relationships'][0])
  for change in [{'company_id':'American Tower'},{'record_id':'same-name-other-project'},{'scope':'entire-business'}]:
   with self.assertRaises(ValueError):m.validate_relationship({**c,**change},r,self.d['companies'])
  cos=copy.deepcopy(self.d['companies']);cos[c['company_id']]['security_type']='preferred_stock'
  with self.assertRaises(ValueError):m.validate_relationship(c,r,cos)
 def test_proximity_shareholder_and_financial_category_do_not_prove_roles(self):
  r=next(x for x in self.original if x['economic_relationships']);c=r['economic_relationships'][0]
  for why in ['proximity','shareholder','company_brand','aggregate','financial_category_is_construction']:
   with self.assertRaises(ValueError):m.validate_relationship({**c,'inference':why},r,self.d['companies'])
 def test_donation_partner_or_adjacent_utility_not_a_documented_contractor(self):
  r=self.project('coresite:DE3');c=copy.deepcopy(r['economic_relationships'][0]);c['role']='contractor'
  with self.assertRaises(ValueError):m.validate_relationship(c,r,self.d['companies'])
 def test_public_exact_geo_imagery_gates_remain_closed(self):
  self.assertEqual(self.d['counts']['public_release_eligible_projects'],0);self.assertEqual(self.d['counts']['exact_sites_verified'],0)
  self.assertTrue(all(not p['coordinates'] for p in self.projects));self.assertEqual(self.d['integration']['safe_public_records'],[])
 def test_ny2_ny3_same_address_not_blind_duplicate_merge(self):
  p=self.project('coresite:NY3');self.assertIn('same stated address',p['related_facilities'][0]['relation'])
 def test_original_phase1_and_production_hashes_unchanged(self):
  for path,expected in json.loads((P.parent/'protected-baseline.json').read_text()).items():self.assertEqual(hashlib.sha256((m.ROOT/path).read_bytes()).hexdigest(),expected)
 def test_counts_are_distinct_records_not_claims_or_background_programmes(self):
  c=self.d['counts'];self.assertEqual(c['verified_economic_asset_or_project_records'],30);self.assertEqual(c['economic_parent_or_programme_records_not_projects'],6)
  self.assertEqual(c['verified_economic_original_records'],4);self.assertEqual(c['issuer_reported_ownership_relationship_records'],4);self.assertEqual(c['verified_legal_property_titleholders'],0)
if __name__=='__main__':unittest.main()
