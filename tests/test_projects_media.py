"""Offline fixtures only; synthetic raster bytes do not represent real projects."""
import copy
import base64
import datetime as dt
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools.projects.scale.media import attach, validate, site_hash
from tools.projects.scale.discover_media import commons_candidate, discover, query
from tools.projects.scale.transport import Deferred


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = {'k':'Q123','n':'Fixture plant','cc':'GB','lo':1.2345,'la':52.1234,
                        't':'Wind energy','validation_status':'verified','src':[]}
        evidence = self.root/'data/projects/media-evidence.txt'
        evidence.parent.mkdir(parents=True)
        evidence.write_text('Synthetic rights + exact-site review fixture. Not actual source evidence.')
        image = self.root/'assets/img/projects/scale/fixture.png'
        image.parent.mkdir(parents=True)
        image.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAC0lEQVR4nGNgQAYAAA4AAamRc7EAAAAASUVORK5CYII='))
        self.entry = {'project':'Q123','kind':'photo','site_sha256':site_hash(self.project),
                      'file':str(image.relative_to(self.root)), 'sha256':hashlib.sha256(image.read_bytes()).hexdigest(),
                      'author':'Fixture author','licence':'CC BY-SA 4.0',
                      'licence_url':'https://creativecommons.org/licenses/by-sa/4.0/',
                      'source_url':'https://commons.wikimedia.org/wiki/File:Fixture.png',
                      'review':{'reviewer':'Offline fixture','checked_at':'2026-11-11',
                                'exact_site':True,'commercial_use':True,'redistribution':True,
                                'evidence_file':str(evidence.relative_to(self.root)),
                                'evidence_sha256':hashlib.sha256(evidence.read_bytes()).hexdigest()}}

    def satellite(self):
        e = copy.deepcopy(self.entry)
        e.update(kind='satellite',provider='USGS Landsat',licence='Public domain',
                 licence_url='https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits',
                 source_url='https://landsatlook.usgs.gov/scene/fixture',
                 acquired_at='2026-10-01',bbox=[1.22,52.11,1.25,52.14])
        return e

    def attach(self, entries):
        return attach([self.project], {'schema':'investedia.projects.media-reviewed.v1','media':entries},self.root,'2026-11-11')

    def test_photo_credit_and_no_mutation(self):
        before = copy.deepcopy(self.project)
        result, report = self.attach([self.entry])
        self.assertEqual(self.project,before)
        self.assertEqual(report['missing'],[])
        self.assertIn('CC BY-SA 4.0', result[0]['photo']['label'])
        self.assertNotIn('review',result[0]['photo'])
        self.assertEqual(result[0]['src'][0]['field_list'],['photo'])

    def test_photo_wins_over_satellite_regardless_of_input_order(self):
        for entries in ([self.satellite(),self.entry],[self.entry,self.satellite()]):
            result, _ = self.attach(entries)
            self.assertIn('photo',result[0]);self.assertNotIn('satellite',result[0])

    def test_satellite_requires_site_crop_source_date_and_rights(self):
        sat = self.satellite()
        self.assertEqual(validate(sat,self.project,self.root,'2026-11-11')['label'],
                         'Satellite view · USGS Landsat · 2026-10-01')
        for change in ({'bbox':[-180,-90,180,90]}, {'bbox':[2,53,2.01,53.01]},
                       {'acquired_at':'2027-01-01'}, {'source_url':'https://maps.google.com/site'},
                       {'licence':'Unknown'}, {'provider':'Copernicus Sentinel-2'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate({**sat,**change},self.project,self.root,'2026-11-11')

    def test_no_generic_placeholder_or_unreviewed_rights(self):
        for change in ({'licence':'CC BY-NC 4.0'}, {'review':{}}, {'author':''},
                       {'author':'<script>bad</script>'}, {'source_url':'https://example.test/placeholder'},
                       {'sha256':'bad'}, {'site_sha256':'wrong'}):
            rows, report = self.attach([{**self.entry,**change}])
            self.assertNotIn('photo',rows[0]);self.assertEqual(len(report['rejected']),1)

    def test_hash_change_and_relocation_invalidate_review(self):
        e = copy.deepcopy(self.entry)
        (self.root/e['review']['evidence_file']).write_text('Changed terms')
        with self.assertRaisesRegex(ValueError,'evidence-hash'):validate(e,self.project,self.root,'2026-11-11')
        with self.assertRaisesRegex(ValueError,'site-review'):validate(e,{**self.project,'lo':1.235},self.root,'2026-11-11')

    def test_path_traversal_and_symlink_blocked(self):
        with self.assertRaises(ValueError):validate({**self.entry,'file':'../../../etc/passwd'},self.project,self.root,'2026-11-11')
        external = self.root/'outside.png';external.write_bytes(b'not an asset')
        link = self.root/'assets/img/projects/scale/link.png';link.symlink_to(external)
        with self.assertRaises(ValueError):validate({**self.entry,'file':str(link.relative_to(self.root))},self.project,self.root,'2026-11-11')

    def test_ambiguous_photos_held_and_valid_satellite_used(self):
        rows, report = self.attach([self.entry,self.entry,self.satellite()])
        self.assertNotIn('photo',rows[0]);self.assertIn('satellite',rows[0])
        self.assertEqual(report['rejected'][0]['reason'],'ambiguous-photo')

    def test_missing_media_does_not_create_placeholder_or_remove_point(self):
        rows, report = self.attach([])
        self.assertEqual(rows,[self.project]);self.assertEqual(report['missing'],['Q123'])

    def test_idempotent_review_and_revocation(self):
        manifest={'schema':'investedia.projects.media-reviewed.v1','media':[self.entry]}
        first,_=self.attach([self.entry])
        second,_=attach(first,manifest,self.root,'2026-11-11')
        self.assertEqual(first,second)
        revoked,_=attach(first,{**manifest,'media':[]},self.root,'2026-11-11')
        self.assertEqual(revoked,[self.project])

    def test_truncated_raster_rejected_despite_matching_hash(self):
        p=self.root/self.entry['file'];p.write_bytes(b'\x89PNG\r\n\x1a\nfixture')
        e={**self.entry,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        with self.assertRaisesRegex(ValueError,'raster-invalid'):validate(e,self.project,self.root,'2026-11-11')


class DiscoveryTests(unittest.TestCase):
    def test_bounded_exact_id_query(self):
        self.assertIn('wd:Q123',query(['Q123']))
        for ids in ([],['Q1']*81,['Q1 } UNION { ?x ?y ?z']):
            with self.assertRaises(ValueError):query(ids)

    def test_commons_strips_html_and_rejects_nc_and_restrictions(self):
        payload={'query':{'pages':{'1':{'title':'File:Fixture.png','imageinfo':[{'mime':'image/png','extmetadata':{
            'Artist':{'value':'<a>Fixture author</a>'}, 'LicenseShortName':{'value':'CC BY-NC 4.0'},
            'LicenseUrl':{'value':'https://example.test/terms'}, 'Restrictions':{'value':'trademark'}}}]}}}}
        candidate=commons_candidate(payload)
        self.assertEqual(candidate['author'],'Fixture author')
        self.assertIn('licence-not-approved',candidate['rejected_reasons'])
        self.assertIn('rights-restrictions-need-review',candidate['rejected_reasons'])
        self.assertTrue(candidate['needs_exact_site_review'])

    @patch('tools.projects.scale.discover_media.time.sleep')
    def test_discovery_never_inherits_cc0_or_changes_project(self, _):
        p={'k':'Q123','n':'Fixture','cc':'GB','lo':1.2345,'la':52.1234,'t':'Wind energy','validation_status':'verified'}
        client=Mock(requests=1,bytes=300,hits=0)
        client.sparql.return_value=({'results':{'bindings':[{
            'item':{'value':'http://www.wikidata.org/entity/Q123'},
            'image':{'value':'http://commons.wikimedia.org/wiki/Special:FilePath/Fixture.png'}}]}},
            {'checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),'sha256':'fixture'})
        result=discover({'projects':[p]},client)
        self.assertEqual(result['counts']['projects_with_candidates'],1)
        self.assertFalse(result['projects'][0]['images'][0]['licence_inherited_from_wikidata'])
        self.assertNotIn('photo',p);client.get.assert_not_called()
        again=discover({'projects':[p]},client,result)
        self.assertEqual(again['counts']['pending'],0)
        self.assertEqual(client.sparql.call_count,1)

    def test_cooldown_preserves_previous_candidates(self):
        p={'k':'Q123','n':'Fixture','cc':'GB','lo':1.2345,'la':52.1234,'t':'Wind energy','validation_status':'verified'}
        client=Mock(requests=0,bytes=0,hits=0);client.sparql.side_effect=Deferred('Source cooldown')
        previous={'projects':[{'project':'Q123','site_sha256':site_hash(p),'images':[{'title':'File:X'}]}]}
        result=discover({'projects':[p]},client,previous,commons=True)
        self.assertEqual(result['counts']['projects_with_candidates'],1)
        self.assertEqual(result['counts']['pending'],1)
        self.assertEqual(result['deferred'],'Source cooldown')

    def test_cap_is_enforced_before_network(self):
        client=Mock()
        for limit in (0,5001):
            with self.assertRaises(ValueError):discover({'projects':[]},client,limit=limit)
        client.sparql.assert_not_called()
