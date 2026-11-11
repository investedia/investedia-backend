"""Offline contract tests. Synthetic rows are fixtures, never published project facts."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from tools.projects import build_projects as b
from tools.projects.status_map import normalize
from tools.projects.news_links import candidates, connections, fingerprint, review_passes
from tools.projects.sources import wikidata, eia, world_bank, nga, ourairports


def row(key='Q123', **changes):
    r={'k':key,'n':'Fixture nuclear development','lo':1.0,'la':52.0,'c':'United Kingdom','t':'Nuclear energy',
       's':'construction','y':2024,'cap':{'value':100,'unit':'MW'}}
    r.update(changes)
    r['src']=[{'name':'Fixture CC0','url':'https://example.test/dataset','licence':'CC0 1.0',
               'checked_at':'2026-11-11','field_list':list(r)}]
    return r


class ProjectsPipelineTests(unittest.TestCase):
    def normal(self,r): return b.normalise(r,{'United Kingdom':'GB'},{},'2026-11-11',True)

    def test_status_exact_no_guess(self):
        self.assertEqual(normalize('OPERATING'),'Operational')
        self.assertEqual(normalize('shelved'),'On hold')
        self.assertIsNone(normalize('completed soon'))
        self.assertIsNone(normalize(None))
        self.assertNotIn('s',self.normal(row(s='completed soon')))

    def test_offline_hash_identical(self):
        with tempfile.TemporaryDirectory() as temp:
            b.build(output=Path(temp));first={str(p.relative_to(temp)):b.digest(p) for p in Path(temp).rglob('*.json')}
            b.build(output=Path(temp));second={str(p.relative_to(temp)):b.digest(p) for p in Path(temp).rglob('*.json')}
            self.assertEqual(first,second)

    def test_provenance_every_field_and_inherited_not_verified(self):
        with tempfile.TemporaryDirectory() as temp:
            report=b.build(output=Path(temp));self.assertEqual(report['retained_unverified'],631)
            for p in b.read(Path(temp)/'assets/globe/projects.json')['projects']:
                # Inherited snapshot rows never count as verified; verified rows come only from licence-reviewed fetches.
                inherited=any('Inherited' in (x.get('review') or '') for x in p['src'])
                self.assertEqual(p['validation_status'],'retained_unverified' if inherited and len(p['src'])==1 else p['validation_status'])
                if p['validation_status']=='verified': self.assertTrue(any('fetched 11 Nov 2026' in x['name'] for x in p['src']),p['k'])
                for field in set(p)-{'upd','validation_status','src'}: self.assertTrue(b.covered(p,field),(p['k'],field))
            self.assertGreater(report['omitted_legacy_inception_years'],0)

    def test_unsourced_optional_rejected(self):
        for field,value in [('s','operational'),('y',2024),('cap',{'value':10,'unit':'MW'}),('cost',{'value':2,'currency':'USD','year':2024})]:
            r=row();r['src'][0]['field_list'].remove(field) if field in r['src'][0]['field_list'] else None
            r[field]=value
            with self.assertRaisesRegex(ValueError,'unsourced-'+field): self.normal(r)

    def test_country_and_bad_coordinates(self):
        for change in ({'c':'unknown'},{'la':float('nan')},{'lo':181},{'cc':'FR'}):
            with self.assertRaises(ValueError): self.normal(row(**change))
        with self.assertRaisesRegex(ValueError,'country-centroid'):
            b.normalise(row(),{'United Kingdom':'GB'},{'GB':[[52,1]]},'2026-11-11',True)

    def test_cancellation_and_decommissioning_rules(self):
        for kwargs in ({'s':'Cancelled','y':2019},{'s':'Cancelled','y':None},{'s':'Decommissioned'},{'s':'Decommissioned','t':'Wind energy','active_decommissioning_verified':True}):
            with self.assertRaises(ValueError): self.normal(row(**kwargs))
        self.assertEqual(self.normal(row(s='Cancelled',y=2021))['s'],'Cancelled')
        self.assertEqual(self.normal(row(s='Decommissioned',active_decommissioning_verified=True))['s'],'Decommissioned')

    def test_same_id_or_near_identical_name_merge_newer_fields(self):
        a=self.normal(row());a['src'][0]['checked_at']='2026-11-10'
        c=self.normal(row('gem:1',n='Fixture nuclear development',s='Operational',la=52.001))
        out,conflicts,merged=b.merge_rows([a,c]);self.assertEqual(len(out),1)
        self.assertEqual(out[0]['s'],'Operational');self.assertEqual(len(out[0]['src']),2)
        self.assertEqual(len(merged),1);self.assertTrue(conflicts)
        far=self.normal(row('gem:2',la=53));self.assertEqual(len(b.merge_rows([a,far])[0]),2)
        with self.assertRaisesRegex(ValueError,'Conflicting identity'): b.merge_rows([a,self.normal(row(la=54))])

    def test_country_only_world_bank_and_context_ports_not_points(self):
        for change,reason in [({'t':'Development finance'},'physical-location-not-verified'),({'t':'Airports'},'not-verified-development'),({'t':'Ports & logistics'},'not-verified-development')]:
            with self.assertRaisesRegex(ValueError,reason): self.normal(row(**change))
        self.assertEqual(self.normal(row(t='Development finance',precise_physical_location_verified=True))['cc'],'GB')
        self.assertEqual(self.normal(row(t='Airports',development_evidence=True))['t'],'Airports')

    def test_invalid_capacity_and_currency_no_silent_conversion(self):
        for change in ({'cap':{'value':float('nan'),'unit':'MW'}},{'cap':{'value':0,'unit':'MW'}},{'cost':{'value':5,'currency':'dollars','year':2024}}):
            with self.assertRaises(ValueError): self.normal(row(**change))
        self.assertEqual(self.normal(row(cost={'value':5,'currency':'GBP','year':2024}))['cost']['currency'],'GBP')

    def test_licence_before_new_ingestion_and_failure_keeps_last_good(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);(d/'old.json').write_text('last good')
            with self.assertRaisesRegex(ValueError,'licence'): b.licence_gate({'source':'gem'},d)
            before=b.digest(d/'old.json')
            manifest=b.read(b.ROOT/'data/projects/manifest.json');manifest['sources'][0]['sha256']='bad'
            # Use the original manifest folder, without changing tracked inputs.
            original=b.digest(b.ROOT/'assets/globe/projects.json')
            with self.assertRaises(ValueError): b.licence_gate(manifest['sources'][0],b.ROOT/'data/projects')
            self.assertEqual(original,b.digest(b.ROOT/'assets/globe/projects.json'))
            self.assertEqual(before,b.digest(d/'old.json'))

    def test_company_links_exact_and_verified_only(self):
        p=self.normal(row(own=[{'name':'Fixture Holdings','role':'owner','qid':'Q987'}]))
        asset={'class':'equity','site':'FCT','qid':'Q987','official':'Different legal name','validation_status':'verified'}
        reg={'assets':{'a':asset}};markets={'assets':[{'site':'FCT'}]}
        links,_=b.company_links([p],reg,markets);self.assertEqual(links[0]['method'],'exact-qid')
        asset.pop('qid');self.assertEqual(b.company_links([p],reg,markets)[0],[])
        asset['official']='Fixture Holdings';self.assertEqual(b.company_links([p],reg,markets)[0][0]['method'],'exact-registry-name')
        asset['validation_status']='unverified';self.assertEqual(b.company_links([p],reg,markets)[0],[])

    def test_ambiguous_listed_match_not_guessed(self):
        p=self.normal(row(own=[{'name':'Fixture Holdings','role':'owner'}]));a={'class':'equity','official':'Fixture Holdings','site':'FCT','validation_status':'verified'}
        self.assertEqual(b.company_links([p],{'assets':{'a':a,'b':a}},{'assets':[{'site':'FCT'}]})[0],[])

    def test_news_exact_country_unique_and_gate_off(self):
        p=self.normal(row(aliases=['Fixture reactor']))
        article={'id':'fixture-article','headline':'Fixture reactor construction begins','summary':'','location':{'place':'Fixture place','country':'United Kingdom','lat':52,'lon':1}}
        rows=candidates([article],[p],{'United Kingdom':'GB'});self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['dest']['project'],p['k'])
        self.assertEqual(connections([article],[p],{'United Kingdom':'GB'},{}),[])
        bad=copy.deepcopy(article);bad['location']['country']='France'
        self.assertEqual(candidates([bad],[p],{'France':'FR'}),[])
        self.assertEqual(candidates([article],[p,self.normal(row('Q124',aliases=['Fixture reactor']))],{'United Kingdom':'GB'}),[])
        bad['headline']='Fixture reactors';self.assertEqual(candidates([bad],[p],{'United Kingdom':'GB'}),[])

    def test_100_real_match_review_required(self):
        p=self.normal(row());review={'enabled':True,'reviewer':'fixture reviewer','checked_at':'2026-11-11','dataset_sha256':fingerprint([p]),
             'sample':[{'event':str(i),'project':p['k'],'source_url':'https://example.test/'+str(i),'correct':i<90} for i in range(100)]}
        self.assertTrue(review_passes(review,[p]));review['sample'].pop();self.assertFalse(review_passes(review,[p]))
        review['sample']*=2;self.assertFalse(review_passes(review,[p]))

    def test_wikidata_query_bounded_and_inception_not_status_year(self):
        q=wikidata.query('Q123');self.assertIn('LIMIT 100',q);self.assertIn('P2109',q)
        with self.assertRaises(ValueError): wikidata.query('unreviewed class')
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'raw.json';v={k:{'value':v} for k,v in {'item':'http://www.wikidata.org/entity/Q123','itemLabel':'Fixture','countryLabel':'United Kingdom','countryCode':'GB','coord':'Point(1 52)','inception':'2000-01-01'}.items()}
            path.write_text(json.dumps({'results':{'bindings':[v]}}))
            result=wikidata.parse(path,{'type':'Nuclear energy','name':'Wikidata','licence':'CC0 1.0','checked_at':'2026-11-11'})[0]
            self.assertNotIn('y',result);self.assertNotIn('s',result)

    def test_reviewed_tabular_adapters_thresholds_and_context_exclusion(self):
        from tools.projects.sources import gem, wri
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'rows.json';rows=[{'id':str(i),'name':'Fixture development','lat':52,'lon':1,'country':'United Kingdom','mw':mw,'status':'construction','size':'L','airport_type':'large_airport'} for i,mw in enumerate([49,50,100])]
            path.write_text(json.dumps(rows))
            spec={'source':'eia','name':'Fixture EIA','url':'https://example.test/data','licence':'Public domain','checked_at':'2026-11-11','type':'Solar energy','capacity_unit':'MW',
                  'columns':{'source_id':'id','n':'name','la':'lat','lo':'lon','c':'country','capacity':'mw','s':'status','size':'size','airport_type':'airport_type'}}
            self.assertEqual(len(eia.parse(path,spec)),2)
            self.assertEqual(nga.parse(path,spec),[]);self.assertEqual(ourairports.parse(path,spec),[])
            with self.assertRaises(ValueError): gem.parse(path,spec)
            with self.assertRaises(ValueError): wri.parse(path,spec)
            self.assertEqual(len(wri.parse(path,{**spec,'as_of':'2021'})),3)

    def test_world_bank_physical_locations_require_individual_review(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'wb.json';path.write_text(json.dumps({'projects':{'P1':{'id':'P1','project_name':'Fixture finance operation','countryname':'United Kingdom','status':'Active'},'P2':{'id':'P2','project_name':'Fixture physical operation','countryname':'United Kingdom','status':'Pipeline','locations':[{'id':'L1','latitude':52,'longitude':1}]}}}))
            spec={'name':'World Bank fixture','url':'https://example.test/data','licence':'CC BY 4.0','checked_at':'2026-11-11'}
            records=world_bank.parse(path,spec);self.assertEqual(len(records),2)
            with self.assertRaisesRegex(ValueError,'no-coordinates'): self.normal(records[0])
            with self.assertRaisesRegex(ValueError,'physical-location-not-verified'): self.normal(records[1])
            records=world_bank.parse(path,{**spec,'record_reviews':{'world_bank:P2:L1':{'precise_physical_location_verified':True}}})
            self.assertEqual(self.normal(records[1])['t'],'Development finance')
            self.assertNotIn('s',self.normal(records[1]))

    def test_review_evidence_hash_required_not_licence_keyword(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);terms=d/'terms.txt';terms.write_text('Fixture licence review evidence, not real source permission')
            spec={'source':'gem','licence':'CC BY 4.0','checked_at':'2026-11-11','licence_review':{'commercial_use':True,'redistribution':True,'url':'https://example.test/terms','reviewer':'fixture','reviewed_at':'2026-11-11','evidence_file':'terms.txt','sha256':b.digest(terms)}}
            b.licence_gate(spec,d)
            terms.write_text('changed')
            with self.assertRaises(ValueError): b.licence_gate(spec,d)
            spec={'source':'wikidata','retained_snapshot':True,'file':'terms.txt','sha256':b.digest(terms)}
            with self.assertRaises(ValueError): b.licence_gate(spec,d)

    def test_featured_photo_hashes_and_no_claim_of_fifty(self):
        feats,rejected=b.featured(b.ROOT/'data/projects/curated',b.ROOT/'assets/globe')
        self.assertEqual(len(feats),4);self.assertEqual(rejected,[])
        self.assertTrue(all(p['review_status']=='inherited_preview' for p in feats))
