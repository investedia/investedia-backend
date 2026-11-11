"""Offline only: fake Pixabay answers (test-only ids and .invalid pages); no network, no real photos."""
import importlib.util, io, json, tempfile, unittest
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('backfill_photos', ROOT/'tools/backfill-photos.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
gspec = importlib.util.spec_from_file_location('gdelt_backfill_photos', ROOT/'tools/gdelt-backfill.py')
g = importlib.util.module_from_spec(gspec); gspec.loader.exec_module(g)


def jpeg(w=2400, h=1600):
    b = io.BytesIO(); Image.new('RGB', (w, h), (30, 60, 90)).save(b, 'JPEG'); return b.getvalue()


class PhotoPoolTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory(); d = Path(self.dir.name)
        self.index, self.blocked, self.out = d/'index.json', d/'blocked.json', d/'out'
        self.index.write_text(json.dumps({'bank building': [{'file': 'photos/bank-building-1.jpg', 'credit': 'a', 'source_url': 'https://pixabay.com/x', 'alt': 'bank building'}]}))
        self.blocked.write_text(json.dumps({'ids': ['3']}))
        self.urls = []
    def tearDown(self): self.dir.cleanup()

    def fetch(self, url, **kw):
        self.urls.append(url)
        if url.startswith(m.API):
            hits = [{'id': 1, 'largeImageURL': 'https://cdn.pixabay.com/1.jpg', 'tags': 'bank', 'user': 'u1', 'pageURL': 'https://pixabay.com/p1'},
                    {'id': 2, 'largeImageURL': 'https://cdn.pixabay.com/2.jpg', 'tags': 'bank, building', 'user': 'u2', 'pageURL': 'https://pixabay.com/p2'},
                    {'id': 3, 'largeImageURL': 'https://cdn.pixabay.com/3.jpg', 'tags': 'bank', 'user': 'u3', 'pageURL': 'https://pixabay.com/p3'},
                    {'id': 4, 'largeImageURL': 'https://cdn.pixabay.com/4.jpg', 'tags': 'bank, illustration', 'user': 'u4', 'pageURL': 'https://pixabay.com/p4'}]
            return json.dumps({'hits': hits}).encode()
        return jpeg()

    def test_top_up_follows_the_live_robot_rules_and_never_writes_the_key(self):
        report = m.run('test-only-key', self.index, self.blocked, self.out, per_topic=10, fetch=self.fetch, sleep=lambda s: None)
        idx = json.loads((self.out/'index.json').read_text())
        bank = idx['bank building']
        self.assertEqual([e['file'] for e in bank], ['photos/bank-building-1.jpg', 'photos/bank-building-2.jpg'])  # old kept, dup/blocked/illustration skipped
        self.assertEqual(bank[1], {'file': 'photos/bank-building-2.jpg', 'credit': 'u2', 'source_url': 'https://pixabay.com/p2', 'alt': 'bank building'})
        self.assertEqual(report['topics']['bank building']['skipped'], {'already_in_pool': 1, 'blocked_id': 1, 'not_a_photograph': 1})
        with Image.open(self.out/'photos/bank-building-2.jpg') as im: self.assertLessEqual(im.size, (1200, 800))
        self.assertIn('middle east city skyline', idx); self.assertEqual(len(m.TOPICS), 70)
        for f in self.out.rglob('*.json'): self.assertNotIn('test-only-key', f.read_text())
        self.assertTrue(all(u.startswith(('https://pixabay.com/', 'https://cdn.pixabay.com/')) for u in self.urls))
        with self.assertRaises(ValueError): m.get('https://example.invalid/x.jpg')
        with self.assertRaises(ValueError): m.run('', self.index, self.blocked, self.out)

    def test_backfill_uses_only_published_extra_topics_and_spreads_reuse_across_runs(self):
        topics = g.photo_topics({'african market': [{'file': 'photos/x.jpg'}]})
        self.assertIn('african market', topics); self.assertNotIn('tea plantation', topics)
        self.assertEqual(topics[:len(g.robot.PHOTO_TOPICS)], g.robot.PHOTO_TOPICS)
        index = json.loads((ROOT/'assets/globe/photos/index.json').read_text())
        files = [p['file'] for p in index['bank building']]
        prior = g.usage_stories({files[0]: 5, files[1]: 5})
        img = g.topic_photo('bank building', 'seed', prior)
        self.assertNotIn(img['file'], files[:2])  # least-used photo wins, counting earlier runs


if __name__ == '__main__': unittest.main()
