import copy,importlib.util,json,sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from sector_adapter import validate,public_projection,digest,SCHEMA,validate_bundle
class SectorTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.rows=json.loads((P/'sector-records.json').read_text())['projects']
 def dc(self):return copy.deepcopy(next(r for r in self.rows if r['sector']=='data_centers'))
 def test_existing_energy_outputs_preserved(self):
  snap=json.loads((P/'energy-snapshot.json').read_text());pairs={r['raw']['id']:r for r in snap['projects']}
  for row in self.rows:
   if row['sector']=='energy':self.assertEqual(row['legacy_energy'],pairs[row['id']]['normalized'])
 def test_actual_energy_verification_categories_preserved(self):
  snap=json.loads((P/'energy-snapshot.json').read_text());pairs={r['raw']['id']:r['raw'] for r in snap['projects']}
  for row in self.rows:
   if row['sector']=='energy':
    for exposure,original in zip(row['exposures'],pairs[row['id']]['exposures']):self.assertEqual(exposure['verification'],original['verification'])
 def test_sector_categories_distinct(self):
  self.assertEqual({r['sector'] for r in self.rows},{'energy','data_centers'})
  for r in self.rows:self.assertTrue(validate(r));self.assertNotEqual(r['sector'],'real_estate')
 def test_additional_sector_requires_registration(self):
  r=self.dc();r['sector']='ports'
  with self.assertRaises(ValueError):validate(r)
  self.assertTrue(validate(r,{'ports':'Ports'}))
 def test_real_estate_contract_without_fake_property(self):
  # Synthetic schema transformation only; never included in research output.
  r=self.dc();r['sector']='real_estate';r['asset']['subtype']='Synthetic logistics fixture';self.assertTrue(validate(r))
 def test_building_campus_and_programme_not_collapsed(self):
  r=self.dc();r['asset'].update(category='programme',count_as_project=True)
  with self.assertRaises(ValueError):validate(r)
  r['asset']['count_as_project']=False;self.assertTrue(validate(r))
  r['asset']['category']='building';r['asset'].pop('building_identity_evidence',None)
  with self.assertRaises(ValueError):validate(r)
 def test_unknown_location_has_no_marker(self):
  r=self.dc();r['location']={'precision':'unknown','lat':None,'lon':None,'satellite_allowed':False};self.assertTrue(validate(r))
  r['location']['lat']=0
  with self.assertRaises(ValueError):validate(r)
 def test_approximate_not_exact_by_label_change(self):
  r=self.dc();r['location']['precision']='exact'
  with self.assertRaises(ValueError):validate(r)
 def test_invalid_coordinates(self):
  for val in [True,float('nan'),float('inf'),91]:
   r=self.dc();r['location']['lat']=val
   with self.assertRaises(ValueError):validate(r)
 def test_no_site_imagery_from_city(self):
  r=self.dc();r['location']['satellite_allowed']=True
  with self.assertRaises(ValueError):validate(r)
 def test_unlicensed_or_wrong_project_image_rejected(self):
  r=self.dc();r['imagery']=[{'type':'photo','source_url':'https://example.invalid/image','rights_status':'pending'}]
  with self.assertRaises(ValueError):validate(r)
 def test_operating_not_property_ownership(self):
  r=self.dc();r['exposures'][0]['role']='direct_property_owner'
  with self.assertRaises(ValueError):validate(r)
  r['exposures'][0]['role']='indirect_property_owner'
  with self.assertRaises(ValueError):validate(r)
 def test_scoped_property_proof_and_indirect_chain_supported(self):
  # Synthetic ownership proof exercises the contract only; never saved as real data.
  r=self.dc();r['id']='synthetic:property-proof';e=r['exposures'][0]
  proof={'url':'https://example.invalid/title','sha256':'a'*64,'checked_at':'2026-11-13','locator':'Synthetic title fixture','record_id':r['id'],'scope':'specific_property'}
  e.update(role='direct_property_owner',property_evidence=proof);self.assertTrue(validate(r))
  e.update(role='indirect_property_owner',property_chain=[{'from':'synthetic:sub','to':'synthetic:parent','scope':'company'}])
  with self.assertRaises(ValueError):validate(r)
  e['property_chain']=[{'from':'synthetic:sub','to':'synthetic:parent','scope':'specific_property','record_id':r['id'],'evidence':proof}];self.assertTrue(validate(r))
 def test_business_share_not_facility_share(self):
  r=self.dc();e=r['exposures'][0];e.update(property_stake=64,stake_scope='company')
  with self.assertRaises(ValueError):validate(r)
 def test_affiliation_not_investment_route(self):
  r=self.dc();r['exposures'][0]['role']='affiliation'
  with self.assertRaises(ValueError):validate(r)
 def test_listing_evidence_required(self):
  r=self.dc();r['exposures'][0]['listing']['evidence']['sha256']=''
  with self.assertRaises(ValueError):validate(r)
 def test_stapled_security_preserved(self):
  r=self.dc();r['exposures'][0]['investment_access']['type']='listed_stapled_security'
  with self.assertRaises(ValueError):validate(r)
  r['exposures'][0]['listing']['security_type']='stapled_security';self.assertTrue(validate(r))
 def test_hq_city_not_exact_office(self):
  r=self.dc();r['exposures'][0]['headquarters']['precision']='exact'
  with self.assertRaises(ValueError):validate(r)
 def test_no_unreviewed_public_export(self):
  r=self.dc();r['reuse']['review']=None
  with self.assertRaises(ValueError):public_projection(r)
 def test_review_tied_to_exact_facts(self):
  r=copy.deepcopy(next(r for r in self.rows if r['id'].endswith('NY3')))
  # Test positive only if the real bounded factual review is present.
  if not r['reuse'].get('review'):self.skipTest('NY3 bounded review not completed')
  out=public_projection(r);self.assertNotIn('reported_metrics',out);r['name']='Changed after review'
  with self.assertRaises(ValueError):public_projection(r)
 def test_data_vs_integration_approval(self):
  bundle=json.loads((P/'dc-data-ready.json').read_text());self.assertIn('no shared integration',bundle['status'])
 def test_duplicate_identity_rejected(self):
  r=self.dc()
  with self.assertRaises(ValueError):validate_bundle([r,copy.deepcopy(r)])
 def test_campus_building_counts_not_additive(self):
  child=self.dc();parent=copy.deepcopy(child);parent['id']='synthetic:campus';parent['asset'].update(category='campus',parent_id=None,count_as_project=True);child['asset']['parent_id']=parent['id']
  with self.assertRaises(ValueError):validate_bundle([parent,child])
  parent['asset']['count_as_project']=False;self.assertTrue(validate_bundle([parent,child]))
 def test_hierarchy_cycle_rejected(self):
  a=self.dc();b=copy.deepcopy(a);b['id']='synthetic:cycle';a['asset']['parent_id']=b['id'];b['asset']['parent_id']=a['id']
  with self.assertRaises(ValueError):validate_bundle([a,b])
 def test_all_prior_rows_retained(self):
  self.assertEqual(len(json.loads((P/'blocker-matrix.json').read_text())['records']),61)
if __name__=='__main__':unittest.main()
