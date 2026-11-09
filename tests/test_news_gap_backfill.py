import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('gap',Path(__file__).resolve().parents[1]/'tools/news-gap-backfill.py')
gap=importlib.util.module_from_spec(spec);spec.loader.exec_module(gap)

class GapTests(unittest.TestCase):
    def test_window_is_half_open_and_bounded(self):
        a,b=gap.LIMIT_START,gap.LIMIT_END
        self.assertTrue(gap.in_window(a,a,b));self.assertFalse(gap.in_window(b,a,b))
        self.assertTrue(gap.in_window('2026-11-08T17:00:00+01:00',a,b))
        for x,y in [('2026-11-07T00:00:00Z',b),(b,a),(a,'2026-11-10T00:00:00Z')]:
            with self.assertRaises(ValueError):gap.window(x,y)
        with self.assertRaises(ValueError):gap.timestamp('2026-11-08T16:00:00')
    def test_dedupe_by_id_url_or_headline_and_within_batch(self):
        old={'id':'one','headline':'Bank Raises Rates!','source':{'url':'https://www.example.com/a?utm_source=x'}}
        candidates=[dict(old,id='two',headline='Other'),dict(old,id='three',source={'url':'https://different.com/b'}),dict(old,headline='Other',source={'url':'https://other.com/c'}),{'id':'new','headline':'Distinct','source':{'url':'https://example.com/new'}}]
        kept,count=gap.dedupe(candidates+[candidates[-1]],[old])
        self.assertEqual(count,4);self.assertEqual([x['id'] for x in kept],['new'])
        self.assertEqual(gap.dedupe([{'title':'Bank raises rates','url':'https://other.com','source':'Publisher'}],[old])[1],1)
    def test_provenance_does_not_redate_or_mutate(self):
        old={'published_at':gap.LIMIT_START}
        new=gap.provenance(old,gap.LIMIT_END,'https://example.com/rss')
        self.assertEqual(old,{'published_at':gap.LIMIT_START});self.assertTrue(new['backfilled'])
        self.assertEqual(new['published_at'],gap.LIMIT_START)
        self.assertEqual(new['backfill_provenance']['original_published_at'],gap.LIMIT_START)
    def test_feed_never_uses_updated_or_missing_date(self):
        rows,bad=gap.parse_feed('<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Title</title><link href="https://example.com"/><updated>2026-11-09T00:00:00Z</updated></entry></feed>','Source','https://example.com/feed')
        self.assertEqual(rows,[]);self.assertEqual(sum(bad.values()),1)
    def test_quality_requires_complete_bound_human_review(self):
        a={'stories':[{'id':'a'}]};r={'artifact_sha256':gap.digest(a),'reviewer':'Owner','articles':[{'id':'a','relevant':True,'correct_country':True}]}
        self.assertEqual(gap.quality(a,r),a['stories'])
        for field,val in [('artifact_sha256','wrong'),('reviewer',''),('articles',[])]:
            with self.assertRaises(ValueError):gap.quality(a,{**r,field:val})
        r['articles'][0]['correct_country']=False
        with self.assertRaises(ValueError):gap.quality(a,r)


class StageIntegrationTests(unittest.TestCase):
    def test_missing_feed_access_saves_incomplete_report_and_fails(self):
        import json, tempfile
        from unittest.mock import patch
        live={'data':{'stories':[{'id':'current','headline':'Current','source':{'url':'https://example.test/current'}}]},'meta':{}}
        def fetch(url):
            if url.endswith('/v1/news'):return json.dumps(live)
            raise OSError('blocked')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);archive=root/'archive.json';archive.write_text('{"stories":[]}')
            with patch.object(gap,'get',side_effect=fetch),patch.object(gap,'reference',return_value=({},{})),patch('builtins.print'):
                with self.assertRaisesRegex(ValueError,'source_scan_incomplete'):
                    gap.stage(gap.LIMIT_START,'2026-11-08T17:00:00Z','https://example.test',[archive],root/'output')
            report=json.loads((root/'output/staged.json').read_text())
            self.assertFalse(report['source_scan_complete']);self.assertEqual(report['counts']['accepted'],0)
            self.assertEqual(report['counts']['source_failures'],len(gap.SOURCES))
    def test_confirm_refuses_legacy_worker_before_any_upload(self):
        import json
        from unittest.mock import patch
        a={'schema':'investedia.news-gap/v1','source_scan_complete':True,'window':{'start':gap.LIMIT_START,'end':gap.LIMIT_END},'stories':[{'id':'a'}]}
        r={'artifact_sha256':gap.digest(a),'reviewer':'Owner','boundaries_verified':True,'boundary_evidence':'Reviewed source logs','articles':[{'id':'a','relevant':True,'correct_country':True}]}
        with patch.object(gap,'get',return_value=json.dumps({'meta':{},'data':{'stories':[]}})),patch.object(gap.uploader,'push') as push:
            with self.assertRaisesRegex(ValueError,'worker_history_capability_missing'):gap.confirm(a,r,'https://example.test')
            push.assert_not_called()

if __name__=='__main__':unittest.main()
