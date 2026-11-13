import copy,hashlib,importlib.util,json,sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
from adapter import classify,normalize,image_allowed,fact_digest
class Phase3Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.matrix=json.loads((P/'blocker-matrix.json').read_text());cls.preview=json.loads((P/'adapter-preview.json').read_text())['projects'];cls.data=json.loads((P.parent/'phase2/phase2-dataset.json').read_text());cls.records=cls.data['original_records']+cls.data['development_records'];cls.companies=cls.data['companies']
 def sample(self):
  p=self.preview[0];r=next(r for r in self.records if r['id']==p['id']);return r,self.companies[r['company']],copy.deepcopy(p['location_accuracy']),copy.deepcopy(p['invest']['exposures'][0]['hq']),copy.deepcopy(p['release'])
 def test_every_existing_record_has_individual_blockers(self):
  self.assertEqual(len(self.matrix['records']),61);self.assertEqual({r['id'] for r in self.matrix['records']},{r['id'] for r in self.records})
  self.assertTrue(all(r['blockers'] and all(b['detail'] for b in r['blockers']) for r in self.matrix['records']))
 def test_priority_five_resolve_geo_and_mapping_but_not_approval(self):
  rows=[r for r in self.matrix['records'] if r['priority']==1];self.assertEqual(len(rows),5)
  for r in rows:self.assertEqual({b['code'] for b in r['blockers']},{'source_reuse_decision_pending','sector_contract_approval_pending'});self.assertEqual(r['location']['precision'],'city_reference');self.assertFalse(r['public_release_eligible'])
 def test_city_reference_and_hq_not_exact_or_satellite_sites(self):
  for p in self.preview:
   self.assertFalse(p['location_accuracy']['exact_site']);self.assertFalse(image_allowed(p['location_accuracy']));self.assertIsNone(p['satellite']);self.assertEqual(p['images'],[])
   self.assertFalse(p['invest']['exposures'][0]['hq']['exact_office']);self.assertEqual(p['invest']['exposures'][0]['hq']['precision'],'city_reference')
 def test_city_country_conflict_not_silently_relocated(self):
  r,c,loc,hq,release=self.sample();loc['country_qid']='Q145'
  with self.assertRaises(ValueError):normalize(r,c,loc,hq,release)
 def test_relabelled_city_pin_cannot_become_exact(self):
  r,c,loc,hq,release=self.sample();loc.update(precision='exact',exact_site_verified=True)
  with self.assertRaises(ValueError):normalize(r,c,loc,hq,release)
 def test_lease_operator_developer_not_legacy_listed_owner(self):
  for p in self.preview:self.assertIsNone(p['listed']);self.assertFalse(p['invest']['exposures'][0]['direct']);self.assertEqual(p['owners'],[])
  dx=next(r for r in self.records if r.get('facility_code')=='DX1');self.assertEqual(classify(dx),'verified_lease_or_operational_exposure')
 def test_group_owned_not_direct_title_or_subsidiary_chain(self):
  r=copy.deepcopy(next(r for r in self.records if r.get('facility_code')=='SV1'))
  self.assertEqual(classify(r),'qualified_group_ownership');r['direct_title_evidence']=True;r['legal_property_owner']=r['company'];self.assertNotEqual(classify(r),'verified_direct_property_ownership')
  r['project_ownership_chain']=[{'scope':'business','share':64}];r['property_chain_verified']=True;self.assertNotEqual(classify(r),'verified_subsidiary_or_jv_ownership')
 def test_structured_specific_property_proof_supported(self):
  r=copy.deepcopy(next(r for r in self.records if r.get('facility_code')=='SV1'));r['legal_property_owner']=r['company'];r['direct_title_evidence']={'record_id':r['id'],'owner_registry_id':r['company'],'source_sha256':'a'*64,'source_url':'https://example.invalid/synthetic-title','locator':'Synthetic unit fixture only'}
  self.assertEqual(classify(r),'verified_direct_property_ownership')
  r['direct_title_evidence']=None;r['property_chain_verified']=True;r['project_ownership_chain']=[{'scope':'specific_property','record_id':r['id'],'source_sha256':'b'*64,'source_url':'https://example.invalid/synthetic-chain'}];self.assertEqual(classify(r),'verified_subsidiary_or_jv_ownership')
 def test_contractual_scope_separate_from_ownership(self):
  r=next(r for r in self.records if r['id']=='project:apld:delta-forge-2');self.assertEqual(classify(r),'verified_contractual_exposure');self.assertIsNone(r['legal_property_owner'])
 def test_source_publication_cannot_be_overridden_by_one_flag(self):
  r,c,loc,hq,release=self.sample()
  with self.assertRaises(ValueError):normalize(r,c,loc,hq,release,for_public=True)
  release.update(eligible=True,blockers=[])
  with self.assertRaises(ValueError):normalize(r,c,loc,hq,release,for_public=True)
  release.update(rights_status='cleared',contract_status='approved')
  with self.assertRaises(ValueError):normalize(r,c,loc,hq,release,for_public=True)
 def test_approval_binds_exact_record_facts_and_cannot_follow_changed_record(self):
  r,c,loc,hq,_=self.sample();r=copy.deepcopy(r);review={'record_id':r['id'],'fact_sha256':fact_digest(r),'reviewer':'Synthetic unit fixture, not real approval','reviewed_at':'2026-11-13','basis':'Synthetic fixture only'};release={'eligible':True,'blockers':[],'rights_status':'cleared','contract_status':'approved','review':review}
  out=normalize(r,c,loc,hq,release,for_public=True);self.assertFalse(out['local_research_preview'])
  r['status']='Changed unreviewed fact'
  with self.assertRaises(ValueError):normalize(r,c,loc,hq,release,for_public=True)
 def test_no_fake_public_release_or_real_estate_pilot(self):
  self.assertEqual(json.loads((P/'public-export.json').read_text())['projects'],[]);self.assertEqual(self.matrix['counts']['public_cleared'],0);self.assertFalse((P/'real-estate-projects.json').exists())
 def test_external_registry_and_nonproject_blockers_preserved(self):
  apld=[r for r in self.matrix['records'] if r['id'].startswith('project:apld:')]
  self.assertTrue(all('shared_registry_mapping_missing' in [b['code'] for b in r['blockers']] for r in apld))
  ctx=[r for r in self.matrix['records'] if r['scope']=='joint_venture_programme'];self.assertEqual(len(ctx),3);self.assertTrue(all('context_not_individual_project' in [b['code'] for b in r['blockers']] for r in ctx))
 def test_energy_sector_contract_never_inferred(self):
  for p in self.preview:self.assertEqual(p['sector'],'Data Centers');self.assertIsNone(p['energy']);self.assertNotIn('mw',p)
  report=json.loads((P/'compatibility-report.json').read_text());self.assertTrue(report['normalized_shape_pass']);self.assertFalse(report['drop_in_compatibility']);self.assertEqual(report['legacy_loader_sector'],'Energy')
 def test_scope_business_stakes_not_facility_stakes(self):
  for p in self.preview:self.assertIsNone(p['invest']['exposures'][0]['stake'])
 def test_no_affiliation_only_record_normalized(self):
  r=copy.deepcopy(next(r for r in self.records if r['id']=='dc:dlr:2256'));c=self.companies[r['company']];loc=self.preview[0]['location_accuracy']
  with self.assertRaises(ValueError):normalize(r,c,loc,None,{'eligible':False})
if __name__=='__main__':unittest.main()
