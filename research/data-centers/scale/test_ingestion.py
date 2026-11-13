import copy,json,sys,tempfile,unittest
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from import_projects import assemble,run,materialize,ImportFailure,read_input,check_output,digest
from make_fixtures import bundle,fixture
from prepare_real import bundle as real_bundle
class IngestionTests(unittest.TestCase):
 def test_real_dc_and_real_estate_import(self):
  s,c=assemble(real_bundle());self.assertEqual(len(s['records']),15);self.assertFalse(s['synthetic']);self.assertEqual({r['sector'] for r in s['records']},{'data_centers','real_estate'})
 def test_identical_duplicate_skipped(self):
  b=bundle(2);b['records'].append(copy.deepcopy(b['records'][0]));s,c=assemble(b);self.assertEqual(c['duplicates'],1);self.assertEqual(len(s['records']),2)
 def test_conflicting_same_id_rejected(self):
  b=bundle(1);r=copy.deepcopy(b['records'][0]);r['name']='Changed duplicate';b['records'].append(r)
  with self.assertRaises(ImportFailure):assemble(b)
 def test_source_identity_collision_not_merged_by_name(self):
  b=bundle(2);b['records'][1]['sector']=b['records'][0]['sector'];b['records'][1]['source_identity']=copy.deepcopy(b['records'][0]['source_identity'])
  with self.assertRaises(ImportFailure):assemble(b)
 def test_same_name_different_buildings_retained(self):
  b=bundle(2);b['records'][1]['name']=b['records'][0]['name'];s,c=assemble(b);self.assertEqual(len(s['records']),2)
 def test_incremental_update_and_unchanged(self):
  b=bundle(3);s,_=assemble(b);b['records'][1]['name']='SYNTHETIC updated';n,c=assemble(b,s);self.assertEqual(c['updated'],1);self.assertEqual(c['unchanged'],2);self.assertEqual(len(n['records']),3)
 def test_source_identity_cannot_change_on_update(self):
  b=bundle(1);s,_=assemble(b);b['records'][0]['source_identity']['id']='different'
  with self.assertRaises(ImportFailure):assemble(b,s)
 def test_reproducible_versions_independent_of_input_order(self):
  b=bundle(5);a,_=assemble(b);b['records'].reverse();c,_=assemble(b);self.assertEqual(digest(a),digest(c))
 def test_synthetic_never_mixed_with_real(self):
  with self.assertRaises(ImportFailure):assemble(bundle(1),{'synthetic':False,'records':[]})
  b=bundle(1);b['synthetic']=False;b['records'][0]['synthetic']=False
  with self.assertRaises(ImportFailure):assemble(b)
 def test_energy_is_read_only(self):
  b=bundle(1);b['records'][0]['sector']='energy'
  with self.assertRaises(ImportFailure):assemble(b)
 def test_unknown_location_valid_no_marker(self):
  b=bundle(1);b['records'][0]['location']={'precision':'unknown','lat':None,'lon':None,'satellite_allowed':False};s,_=assemble(b);self.assertIsNone(s['records'][0]['location']['lat'])
 def test_city_cannot_become_satellite_site(self):
  b=bundle(2);b['records'][1]['location']['satellite_allowed']=True
  with self.assertRaises(ImportFailure):assemble(b)
 def test_unlicensed_imagery_rejected(self):
  b=bundle(1);b['records'][0]['imagery']=[{'url':'https://example.invalid/photo','rights_status':'pending'}]
  with self.assertRaises(ImportFailure):assemble(b)
 def test_image_with_evidence_allowed_only_correct_project(self):
  b=bundle(1);r=b['records'][0];r['imagery']=[{'url':'https://fixtures.example.invalid/photo','source_url':'https://fixtures.example.invalid/source','rights_status':'cleared','licence':'Synthetic fixture, not a real image','credit':'Test only','project_id':'wrong'}]
  with self.assertRaises(ImportFailure):assemble(b)
  r['imagery'][0]['project_id']=r['id'];assemble(b)
 def test_error_does_not_print_secret_value(self):
  b=bundle(1);b['records'][0]['api_key']='PRIVATE VALUE MUST NOT APPEAR'
  try:assemble(b);self.fail('accepted credential')
  except ImportFailure as e:self.assertNotIn('PRIVATE VALUE',json.dumps(e.errors));self.assertEqual(e.errors[0]['code'],'credential_field_forbidden')
 def test_failed_import_keeps_last_good(self):
  with tempfile.TemporaryDirectory() as d:
   inp=Path(d)/'in.json';out=Path(d)/'out';inp.write_text(json.dumps(bundle(3)));first=run(inp,out);pointer=(out/'current.json').read_bytes();bad=bundle(2);bad['records'][0]['location']['lat']=999;inp.write_text(json.dumps(bad))
   with self.assertRaises(ImportFailure):run(inp,out,True)
   self.assertEqual(pointer,(out/'current.json').read_bytes());self.assertTrue((out/'versions'/first['version']/'manifest.json').exists())
 def test_retire_keeps_auditable_record_and_needs_hash(self):
  s,_=assemble(bundle(1));r=s['records'][0];b=bundle(0);b['retire']=[{'id':r['id'],'reason':'Test retirement','as_of':'2026-11-13','expected_sha256':digest(r)}];n,c=assemble(b,s);self.assertEqual(len(n['records']),1);self.assertTrue(n['records'][0]['lifecycle']['retired'])
  b['retire'][0]['expected_sha256']='wrong'
  with self.assertRaises(ImportFailure):assemble(b,s)
 def test_catalog_shard_matches_record_and_checksum(self):
  with tempfile.TemporaryDirectory() as d:
   s,c=assemble(bundle(20));r=materialize(s,c,d);p=Path(d)/'versions'/r['version'];cat=json.loads((p/'catalog.json').read_text());self.assertEqual(len(cat['records']),20)
   for v in cat['records']:self.assertIn(v['id'],json.loads((p/'details'/f"{v['shard']}.json").read_text()))
 def test_jsonl_header_supported(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'input.jsonl';b=bundle(2);p.write_text(json.dumps({'header':{k:v for k,v in b.items() if k!='records'}})+'\n'+'\n'.join(json.dumps(r) for r in b['records']));self.assertEqual(len(read_input(p)['records']),2)
 def test_production_output_path_rejected(self):
  with self.assertRaises(ValueError):check_output('/workspace/investedia-frontend/assets/globe/scale-artifacts')
 def test_bad_source_identity_structured_errors(self):
  b=bundle(1);b['records'][0]['source_identity']['id']={}
  with self.assertRaises(ImportFailure):assemble(b)
 def test_company_reference_not_name_match(self):
  b=bundle(1);b['records'][0]['exposures'][0]['company_ref']='cik:0000000123'
  with self.assertRaises(ImportFailure):assemble(b)
 def test_reusable_company_registry(self):
  b=bundle(2);e=b['records'][0]['exposures'][0];b['companies']={'cik:0000000123':{'identity':{'scheme':'cik','value':'0000000123','evidence':e['evidence']},'listing':e['listing'],'headquarters':e['headquarters']}}
  for r in b['records']:
   r['exposures'][0]['company_ref']='cik:0000000123';r['exposures'][0].pop('listing');r['exposures'][0].pop('headquarters')
  s,_=assemble(b);self.assertEqual(s['records'][0]['exposures'][0]['listing'],s['records'][1]['exposures'][0]['listing'])
 def test_name_only_company_reference_rejected(self):
  b=bundle(1);e=b['records'][0]['exposures'][0];b['companies']={'Name only':{'identity':{'scheme':'name','value':'Name only','evidence':e['evidence']}}}
  with self.assertRaises(ImportFailure):assemble(b)
 def test_record_cap_is_hard(self):
  import import_projects as module
  old=module.MAX_RECORDS;module.MAX_RECORDS=2
  try:
   with self.assertRaises(ImportFailure):assemble(bundle(3))
  finally:module.MAX_RECORDS=old
 def test_invalid_new_company_id_rejected(self):
  b=bundle(1);ev=b['records'][0]['identity_evidence'];b['companies']={'cik:NAME':{'identity':{'scheme':'cik','value':'NAME','evidence':ev}}}
  with self.assertRaises(ImportFailure):assemble(b)
 def test_company_refresh_updates_all_references(self):
  b=bundle(1);e=b['records'][0]['exposures'][0];co={'identity':{'scheme':'cik','value':'0000000123','evidence':e['evidence']},'listing':e.pop('listing'),'headquarters':e.pop('headquarters')};b['companies']={'cik:0000000123':co};e['company_ref']='cik:0000000123';s,_=assemble(b)
  c=copy.deepcopy(co);c['listing']['name']='SYNTHETIC changed company';update=bundle(0);update['companies']={'cik:0000000123':c};n,counts=assemble(update,s);self.assertEqual(counts['company_refreshed'],1);self.assertEqual(n['records'][0]['exposures'][0]['listing']['name'],c['listing']['name'])
 def test_failed_incremental_base_checksum_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'in.json';p.write_text(json.dumps(bundle(1)));root=Path(d)/'out';r=run(p,root);(root/'versions'/r['version']/'state.json').write_text('{}')
   with self.assertRaises(ValueError):run(p,root,True)

 def test_synthetic_cannot_pass_public_review(self):
  from sector_adapter import public_projection
  with self.assertRaises(ValueError):public_projection(fixture(0))
 def test_current_import_lock_prevents_lost_updates(self):
  import fcntl
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'in.json';p.write_text(json.dumps(bundle(1)));root=Path(d)/'out';root.mkdir()
   with (root/'.import.lock').open('a') as f:
    fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
    with self.assertRaises(ImportFailure):run(p,root)
 def test_existing_corrupt_version_not_selected(self):
  with tempfile.TemporaryDirectory() as d:
   s,c=assemble(bundle(1));r=materialize(s,c,d);p=Path(d)/'versions'/r['version']/'catalog.json';p.write_text('{}')
   with self.assertRaises(ValueError):materialize(s,c,d)

if __name__=='__main__':unittest.main()

class CatalogTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);s,c=assemble(bundle(100));materialize(s,c,self.root)
  from catalog import Catalog
  self.cat=Catalog(self.root)
 def test_page_filter_search(self):
  r=self.cat.query(sector='data_centers',limit=10);self.assertEqual(r['total'],50);self.assertEqual(len(r['records']),10);self.assertTrue(r['synthetic'])
  self.assertEqual(self.cat.query(q='TEST 000001')['total'],1)
 def test_invalid_pagination_and_search(self):
  for args in [{'offset':-1},{'limit':201},{'limit':True},{'q':'x'*161}]:
   with self.assertRaises(ValueError):self.cat.query(**args)
 def test_unknown_points_not_clustered(self):
  b=bundle(2);b['records'][0]['location']={'precision':'unknown','lat':None,'lon':None,'satellite_allowed':False};s,c=assemble(b);materialize(s,c,self.root)
  from catalog import Catalog
  c=Catalog(self.root);g=c.clusters();self.assertEqual(g['unknown_not_mapped'],1);self.assertEqual(sum(x['count'] for x in g['clusters']),1)
 def test_clusters_account_for_all_points(self):self.assertEqual(sum(x['count'] for x in self.cat.clusters()['clusters']),100)
 def test_antimeridian_bounds(self):
  points=self.cat.clusters(bbox=(170,-90,-170,90));self.assertTrue(all(abs(p['lon'])>=170 for p in points['clusters']))
 def test_lazy_detail_integrity(self):
  row=self.cat.rows[0];p=self.cat.path/'details'/f"{row['shard']}.json";p.write_text('{}')
  with self.assertRaises(ValueError):self.cat.get(row['id'])
 def test_catalog_integrity(self):
  (self.cat.path/'catalog.json').write_text('{}')
  from catalog import Catalog
  with self.assertRaises(ValueError):Catalog(self.root)
 def test_retired_hidden_but_auditable(self):
  s,_=assemble(bundle(2));r=s['records'][0];b=bundle(0);b['retire']=[{'id':r['id'],'reason':'Test','as_of':'2026-11-13','expected_sha256':digest(r)}];n,c=assemble(b,s);materialize(n,c,self.root)
  from catalog import Catalog
  cat=Catalog(self.root);self.assertEqual(cat.query()['total'],1);self.assertTrue(cat.get(r['id'])['lifecycle']['retired'])

 def test_caller_cannot_mutate_cached_record(self):
  rid=self.cat.rows[0]['id'];r=self.cat.get(rid);original=r['name'];r['name']='MUTATED';self.assertEqual(self.cat.get(rid)['name'],original)
  result=self.cat.query(limit=1);result['records'][0]['name']='MUTATED';self.assertNotEqual(self.cat.query(limit=1)['records'][0]['name'],'MUTATED')
