import importlib.util, json, os, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('push', ROOT / 'tools/push-news-to-worker.py'); push = importlib.util.module_from_spec(spec); spec.loader.exec_module(push)

class PushNews(unittest.TestCase):
    def test_payload_is_newest_first_and_bounded(self):
        st = [{'id': str(i), 'published_at': f'2026-10-28T{i % 24:02d}:00:00Z'} for i in range(60)]
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f: json.dump({'updated_at': 'x', 'stories': st}, f)
        p = push.payload(f.name, 40); os.unlink(f.name)
        self.assertEqual(len(p['stories']), 40); self.assertEqual(p['stories'], sorted(p['stories'], key=lambda s: s['published_at'], reverse=True))
    def test_empty_feed_is_never_sent(self):
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f: json.dump({'stories': []}, f)
        with self.assertRaises(ValueError): push.payload(f.name)
        os.unlink(f.name)
    def test_real_feed_payload_validates_like_the_worker(self):
        p = push.payload()
        for s in p['stories']:
            for k in ('id', 'headline', 'category', 'published_at', 'source', 'location'): self.assertTrue(s.get(k), k)
            self.assertIsInstance(s['location']['lat'], (int, float))
if __name__ == '__main__': unittest.main()
