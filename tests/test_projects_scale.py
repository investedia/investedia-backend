"""Offline current-only source, unit identity and HTTP resume fixtures. No real downloads."""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import urllib.error

from tools.projects.scale.policy import current
from tools.projects.scale.wikidata import parse
from tools.projects.scale.tabular import parse as tabular,header_hash
from tools.projects.scale.reconcile import reconcile
from tools.projects.scale.transport import Client,Deferred,BudgetExceeded
from tools.projects.scale.queries import ids,details

ASOF='2026-11-11'
FIX=Path(__file__).parent/'fixtures/projects-scale'


def row(key='Q123',**changes):
    r={'k':key,'n':'Fixture plant','t':'Wind energy','cc':'GB','c':'United Kingdom','record_level':'site',
       'la':52.1234,'lo':1.2345,'coordinate_precision':.0001,'s':'Under construction',
       'external_ids':{'wikidata':key},'src':[{'name':'Fixture source','url':'https://example.test/data','licence':'CC0 1.0','checked_at':ASOF,'field_list':['s','completion_date','status_date']}]}
    r.update(changes);return r


def bind(**values):return {key:{'value':str(value)} for key,value in values.items()}


class ScalePolicyTests(unittest.TestCase):
    def test_development_is_current_without_inventing_a_status_date(self):
        r=current(row(),ASOF);self.assertEqual(r['display_status'],'Under construction');self.assertNotIn('status_date',r)
        self.assertEqual(current(row(s='Proposed'),ASOF)['display_status'],'In development')

    def test_completed_cutoff_future_and_unknown_dates(self):
        self.assertEqual(current(row(s='Completed',completion_date='2020'),ASOF)['display_status'],'Completed 2020')
        for changes in [{'s':'Completed','completion_date':'2019'},{'s':'Completed'},{'s':'Completed','completion_date':'2027'},{'s':'Completed','completion_date':'2026'},{'s':None}]:
            with self.assertRaises(ValueError):current(row(**changes),ASOF)
        self.assertEqual(current(row(s='Completed',completion_date='2026',_explicit_operating=True),ASOF)['y'],2026)

    def test_all_excluded_states_stay_out_even_with_recent_service(self):
        for state in ['Cancelled','On hold','Decommissioned','Retired','Shelved']:
            with self.assertRaises(ValueError):current(row(s=state,completion_date='2024'),ASOF)
        with self.assertRaises(ValueError):current(row(retirement_date='2025'),ASOF)

    def test_precision_rounding_and_exact_source_quality(self):
        for changes in [{'coordinate_precision':None},{'coordinate_precision':.01},{'coordinate_precision':float('nan')},{'la':52.12},{'lo':1.0}]:
            with self.assertRaises(ValueError):current(row(**changes),ASOF)
        self.assertEqual(current(row(coordinate_precision=None,coordinate_quality='exact'),ASOF)['coordinate_quality'],'exact')

    def test_wikidata_no_inception_completion_or_build_time_status_date(self):
        b=bind(item='http://www.wikidata.org/entity/Q123',itemLabel='Fixture plant',countryLabel='United Kingdom',countryCode='GB',coord='Point(1.2345 52.1234)',precision=.0001,inception='2024-01-01T00:00:00Z')
        spec={'type':'Wind energy','name':'Wikidata fixture','checked_at':ASOF,'licence':'CC0 1.0'}
        r=parse({'results':{'bindings':[b]}},spec)[0]
        self.assertNotIn('completion_date',r);self.assertNotIn('status_date',r)
        with self.assertRaises(ValueError):current(r,ASOF)
        b.update(bind(entry='2024-01-01T00:00:00Z'))
        r=current(parse({'results':{'bindings':[b]}},spec)[0],ASOF)
        self.assertEqual(r['s'],'Completed');self.assertEqual(r['completion_date'],'2024')
        self.assertEqual(r['evidence']['completion_date']['property'],'P729')

    def test_wikidata_union_facts_have_field_provenance_and_conflicts_are_held(self):
        common=bind(item='http://www.wikidata.org/entity/Q123',itemLabel='Fixture plant')
        rows=[{**common,**bind(coord='Point(1.2345 52.1234)',precision=.0001)},
              {**common,**bind(countryLabel='United Kingdom',countryCode='GB')},
              {**common,**bind(statusLabel='building or structure under construction')}]
        spec={'type':'Wind energy','name':'Wikidata fixture','checked_at':ASOF,'licence':'CC0 1.0'}
        r=parse({'results':{'bindings':rows}},spec)[0];self.assertEqual(current(r,ASOF)['s'],'Under construction')
        for field in ['s','coordinate_precision','la','lo','cc']:self.assertIn(field,r['src'][0]['field_list'])
        rows.append({**common,**bind(coord='Point(2.3456 53.4567)')})
        r=parse({'results':{'bindings':rows}},spec)[0]
        with self.assertRaisesRegex(ValueError,'conflicting-coord'):current(r,ASOF)

    def test_queries_are_bounded_and_include_source_precision_and_retirement(self):
        self.assertIn('LIMIT 500',ids('Q123'));self.assertIn('wikibase:geoPrecision',details(['Q123']))
        self.assertIn('P730',details(['Q123']));self.assertIn('UNION',details(['Q123']))
        with self.assertRaises(ValueError):details(['Q1']*81)
        with self.assertRaises(ValueError):ids('Plant by name')


class ScaleReconciliationTests(unittest.TestCase):
    def test_different_wikidata_ids_are_not_collapsed_by_near_names(self):
        out,_,merges,_=reconcile([row(),row('Q124')]);self.assertEqual(len(out),2);self.assertEqual(merges,[])

    def test_two_real_units_on_one_site_stay_separate(self):
        a=row('gem:1',record_level='unit',external_ids={'gem:unit':'1','gem:site':'S1'})
        b=row('gem:2',record_level='unit',external_ids={'gem:unit':'2','gem:site':'S1'})
        self.assertEqual(len(reconcile([a,b])[0]),2)

    def test_exact_cross_source_id_merges_and_preserves_sources(self):
        a=row();b=row('gem:X',external_ids={'wikidata':'Q123','gem:site':'X'})
        b['src']=[{**b['src'][0],'name':'Second fixture source'}]
        out,_,merges,_=reconcile([a,b]);self.assertEqual(len(out),1);self.assertEqual(merges[0]['rule'],'exact-id');self.assertEqual(len(out[0]['src']),2)

    def test_cross_source_conflicts_are_not_reactivated_by_a_third_copy(self):
        a=row();b=row('gem:X',la=53.2345,external_ids={'wikidata':'Q123'})
        c=row('z-source:Y',external_ids={'wikidata':'Q123'})
        out,conflicts,_,drops=reconcile([a,b,c]);self.assertEqual(out,[]);self.assertTrue(conflicts);self.assertEqual(len(drops),3)

    def test_conflicting_capacity_is_withheld_not_added_back(self):
        a=row(cap={'value':100,'unit':'MW'});b=row('gem:X',cap={'value':200,'unit':'MW'},external_ids={'wikidata':'Q123'})
        c=row('z-source:Y',cap={'value':100,'unit':'MW'},external_ids={'wikidata':'Q123'})
        out,conflicts,_,_=reconcile([a,b,c]);self.assertEqual(len(out),1);self.assertNotIn('cap',out[0]);self.assertTrue(conflicts)


class TabularScaleTests(unittest.TestCase):
    def spec(self,filename,source):
        with (FIX/filename).open() as f:headers=next(csv.reader(f))
        columns={'unit_id':'GEM unit ID','plant_id':'GEM location ID','name':'Unit name','country':'Country/Area','latitude':'Latitude','longitude':'Longitude','status':'Status','capacity':'Capacity (MW)','commissioning_year':'Start year','coordinate_quality':'Location accuracy'} if source=='gem' else {'unit_id':'Generator ID','plant_id':'Plant ID','name':'Plant Name','latitude':'Latitude','longitude':'Longitude','status':'Status','capacity':'Nameplate Capacity (MW)','planned_year':'Planned Operation Year','coordinate_quality':'Location quality'}
        return {'source':source,'source_version':'synthetic fixture v1','schema_review':{'reviewer':'fixture only','header_sha256':header_hash(headers)},'tracker':'fixture','threshold_reviewed':True,
                'columns':columns,'type':'Solar energy','capacity_unit':'MW','name':'Fixture source','url':'https://example.test/data','licence':'CC BY 4.0','checked_at':ASOF,
                'status_values':{'construction':'Under construction','operating':'Operational','cancelled':'Cancelled','fixture-plan':'Proposed','fixture-build':'Under construction'},
                'coordinate_quality_values':{'exact':'exact','approximate':'approximate'},'country_scope':{'reviewed':True,'name':'United States of America','iso2':'US'}}

    def test_gem_units_native_status_cutoff_and_source_columns(self):
        spec=self.spec('gem-units.csv','gem');rows=tabular(FIX/'gem-units.csv',spec)
        self.assertEqual(current(rows[0],ASOF)['s'],'Under construction')
        with self.assertRaisesRegex(ValueError,'completed-before-cutoff'):current(rows[1],ASOF)
        with self.assertRaises(ValueError):current(rows[2],ASOF)
        self.assertEqual(rows[0]['external_ids']['gem:site'],'TEST-S1');self.assertIn('cap',rows[0]['src'][0]['field_list'])

    def test_eia_generator_id_is_namespaced_by_plant_and_planned_date_is_not_completion(self):
        spec=self.spec('eia-generators.csv','eia');rows=tabular(FIX/'eia-generators.csv',spec)
        self.assertNotEqual(rows[0]['k'],rows[1]['k']);self.assertNotIn('completion_date',rows[0])
        self.assertEqual(current(rows[0],ASOF)['s'],'Proposed')

    def test_schema_changes_unknown_codes_and_missing_reviews_fail_closed(self):
        spec=self.spec('gem-units.csv','gem');spec['schema_review']['header_sha256']='bad'
        with self.assertRaises(ValueError):tabular(FIX/'gem-units.csv',spec)
        spec=self.spec('gem-units.csv','gem');spec['status_values']={'different-native-code':'Proposed'}
        with self.assertRaisesRegex(ValueError,'unknown-native-status'):current(tabular(FIX/'gem-units.csv',spec)[0],ASOF)
        spec=self.spec('gem-units.csv','gem');spec.pop('source_version')
        with self.assertRaises(ValueError):tabular(FIX/'gem-units.csv',spec)


class ScaleTransportTests(unittest.TestCase):
    def response(self,body=b'{}'):
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        response.read.return_value=body;response.headers={'ETag':'"fixture-v1"'};return response

    def test_cache_resume_and_conditional_304(self):
        with tempfile.TemporaryDirectory() as temp:
            c=Client(temp,hosts={'example.test'});c.opener=Mock();c.opener.open.return_value=self.response()
            first,receipt=c.get('https://example.test/data');self.assertEqual(c.get('https://example.test/data')[0],first);self.assertEqual(c.requests,1)
            c.opener.open.side_effect=urllib.error.HTTPError('https://example.test/data',304,'Not modified',{},None)
            self.assertEqual(c.get('https://example.test/data',refresh=True)[0],first)
            request=c.opener.open.call_args.args[0];self.assertEqual(request.get_header('If-none-match'),'"fixture-v1"')

    def test_cooldown_persists_and_source_budget_is_bounded(self):
        with tempfile.TemporaryDirectory() as temp:
            c=Client(temp,hosts={'example.test'});c.opener=Mock();c.opener.open.side_effect=urllib.error.HTTPError('https://example.test/data',429,'Limited',{'Retry-After':'120'},None)
            with self.assertRaises(Deferred):c.get('https://example.test/data')
            second=Client(temp,hosts={'example.test'});second.opener=Mock()
            with self.assertRaises(Deferred):second.get('https://example.test/data')
            second.opener.open.assert_not_called()
        with tempfile.TemporaryDirectory() as temp:
            c=Client(temp,seconds=0,hosts={'example.test'})
            with self.assertRaises(BudgetExceeded):c.get('https://example.test/data')

    def test_no_unreviewed_hosts_or_corrupt_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            c=Client(temp,hosts={'example.test'});c.opener=Mock();c.opener.open.return_value=self.response()
            with self.assertRaises(ValueError):c.get('https://other.test/data')
            c.get('https://example.test/data');next(Path(temp).glob('*.body')).write_bytes(b'changed')
            with self.assertRaises(ValueError):c.get('https://example.test/data')


class ScaleArtifactTests(unittest.TestCase):
    def test_current_artifact_is_reproducible_and_every_published_field_has_evidence(self):
        from tools.projects import build_projects as builder
        manifest=builder.ROOT/'data/projects/scale-manifest.json'
        with tempfile.TemporaryDirectory() as temp:
            builder.build(manifest_path=manifest,output=Path(temp))
            paths=list(Path(temp).rglob('*.json'));before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
            builder.build(manifest_path=manifest,output=Path(temp))
            self.assertEqual(before,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
            data=json.loads((Path(temp)/'assets/globe/projects-v2.json').read_text())
            for project in data['projects']:
                self.assertIn(project['s'],['Proposed','Approved','Under construction','In development','Completed'])
                if project['s']=='Completed':self.assertGreaterEqual(int(project['completion_date'][:4]),2020)
                for field in set(project)-{'src','upd','validation_status'}:self.assertTrue(builder.covered(project,field),(project['k'],field))

    def test_slim_copy_preserves_free_basic_facts_without_inventing_pro_data(self):
        from tools.projects.slim_projects import slim
        r=row();r['validation_status']='verified';r['own']=[{'name':'Fixture owner','role':'owner'}]
        r['src'][0]['field_list']=list(r)
        document={'schema':'investedia.projects.v2','build_date':ASOF,'projects':[r]}
        before=copy.deepcopy(document);small=slim(document)
        self.assertEqual(small['projects'][0]['k'],r['k']);self.assertEqual(small['projects'][0]['la'],r['la'])
        self.assertNotIn('own',small['projects'][0]);self.assertEqual(document,before)
