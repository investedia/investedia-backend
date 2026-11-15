import json, pathlib, sys, tempfile, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'tools'))
import publish_library as P

S = {'id': 'nabc12345', 'headline': 'H', 'published_at': '2026-11-15T10:00:00Z', 'location': {'country': 'France'}, 'source': {'name': 'X'}}

class PublishLibrary(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); r = pathlib.Path(self.t.name)
        self.be, self.fe = r / 'be', r / 'fe'
        (self.be / 'assets/globe').mkdir(parents=True); (self.fe / 'assets/globe/library').mkdir(parents=True); (self.fe / 'docs/assets/globe').mkdir(parents=True)
    def tearDown(self): self.t.cleanup()
    def feed(self, name, stories, **kw): (self.be / 'assets/globe' / name).write_text(json.dumps({'stories': stories, **kw}))

    def test_skips_demo_incomplete_and_unsafe_ids(self):
        self.feed('news-live.json', [S, dict(S, id='n2', demo=True), dict(S, id='n3', headline=''), dict(S, id='../x')])
        self.feed('news-48h.json', [dict(S, id='n4')], demo=True)
        self.assertEqual(list(P.robot_stories(self.be)), ['nabc12345'])

    def test_adds_only_new_articles_to_both_copies(self):
        old = self.fe / 'assets/globe/library/nold00001.json'; old.write_text('{"keep":1}')
        new = P.publish(self.fe, {'nold00001': dict(S, id='nold00001'), 'nabc12345': S})
        self.assertEqual(new, ['nabc12345'])
        self.assertEqual(old.read_text(), '{"keep":1}')  # existing articles are never rewritten
        for base in ('assets', 'docs/assets'): self.assertTrue((self.fe / base / 'globe/library/nabc12345.json').exists())

    def test_check_writes_nothing(self):
        self.assertEqual(P.publish(self.fe, {'nabc12345': S}, check=True), ['nabc12345'])
        self.assertFalse((self.fe / 'assets/globe/library/nabc12345.json').exists())

    def test_site_stats_keeps_projects(self):
        (self.fe / 'assets/globe/site-stats.json').write_text('{"articles":1,"sources":1,"projects":2797}')
        P.site_stats(self.fe, {'total': 7163, 'sources': 411})
        self.assertEqual(json.loads((self.fe / 'assets/globe/site-stats.json').read_text()), {'articles': 7163, 'sources': 411, 'projects': 2797})

if __name__ == '__main__': unittest.main()
