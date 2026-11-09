"""Offline photo-pool and allocation tests. No feed writes or Pixabay requests."""
import copy
import importlib.util
import json
from collections import Counter
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('news_photos_robot', ROOT / 'update_globe_news.py')
robot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(robot)
TOPIC = 'electric car charging'


def cached(i):
    return {'file': f'photos/electric-car-charging-{i}.jpg', 'credit': f'Photographer {i}',
            'source_url': f'https://pixabay.com/photos/test-{i}/', 'alt': TOPIC}


class NewsPhotos(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.globe, self.docs = Path(temp.name) / 'globe', Path(temp.name) / 'docs'
        for folder in (self.globe, self.docs): (folder / 'photos').mkdir(parents=True)
        for name, value in [('G', str(self.globe)), ('D', str(self.docs)), ('PIXABAY', 'offline-test-key'),
                            ('status', {'errors': []})]:
            p = patch.object(robot, name, value); p.start(); self.addCleanup(p.stop)
        p = patch.object(robot, 'log'); p.start(); self.addCleanup(p.stop)

    def index(self, photos=None):
        value = {} if photos is None else {TOPIC: photos}
        for folder in (self.globe, self.docs):
            (folder / 'photos/index.json').write_text(json.dumps(value))

    def read_index(self, folder=None):
        return json.loads(((folder or self.globe) / 'photos/index.json').read_text())

    def image_encoder(self):
        # The network/cache tests stay runnable without Pillow installed locally.
        image = Mock(); image.convert.return_value = image
        image.save.side_effect = lambda stream, *a, **kw: stream.write(b'encoded-jpeg')
        pil = types.SimpleNamespace(Image=types.SimpleNamespace(open=Mock(return_value=image)))
        return pil, image

    def pixabay(self, bad_download=None):
        def get(url, **kwargs):
            if url.startswith('https://pixabay.com/api/'):
                self.assertEqual(parse_qs(urlparse(url).query)['per_page'], ['20'])
                hits = [{'id': i, 'largeImageURL': f'https://images.test/{i}',
                         'user': f'Photographer {i}', 'pageURL': f'https://pixabay.com/photos/test-{i}/'}
                        for i in range(1, 21)]
                return json.dumps({'hits': [{}, hits[0], *hits]})
            if url == bad_download: raise OSError('image unavailable')
            return b'original-photo'
        return get

    def test_ten_photos_twelve_stories_use_every_photo_before_repeating(self):
        self.index([cached(i) for i in range(10)])
        stories = []
        with patch.object(robot, 'get', side_effect=AssertionError('no network for a full pool')):
            for i in range(12):
                # Even the same seed must never beat the least-used rule.
                stories.append({'id': f'story-{i}', 'image': robot.photo(TOPIC, 'same-seed', stories)})
        files = [s['image']['file'] for s in stories]
        self.assertEqual(len(set(files[:10])), 10)
        self.assertEqual(sorted(Counter(files).values()), [1] * 8 + [2] * 2)
        self.assertEqual(stories[0]['image']['license'], 'Pixabay Content License')
        self.assertEqual(stories[0]['image']['alt'], f'{TOPIC} (illustration)')

    def test_existing_online_usage_and_deterministic_seed_ties(self):
        self.index([cached(i) for i in range(10)])
        stories = [{'image': {'file': cached(i)['file']}} for i in range(9)]
        self.assertEqual(robot.photo(TOPIC, 'seed', stories)['file'], cached(9)['file'])
        stories.append({'image': {'file': cached(9)['file']}})
        self.assertEqual(robot.photo(TOPIC, 'seed', stories), robot.photo(TOPIC, 'seed', stories))
        self.assertGreater(len({robot.photo(TOPIC, str(i), stories)['file'] for i in range(20)}), 1)
        (self.globe / robot.OUT).write_text(json.dumps({'stories': stories[:-1]}))
        self.assertEqual(robot.photo(TOPIC, 'seed')['file'], cached(9)['file'])

    def test_first_fetch_keeps_first_ten_good_unique_photos_and_jpeg_settings(self):
        self.index(); pil, image = self.image_encoder()
        with patch.dict('sys.modules', {'PIL': pil}), patch.object(robot, 'get', side_effect=self.pixabay('https://images.test/2')) as get:
            result = robot.photo(TOPIC, 'seed', [])
        photos = self.read_index()[TOPIC]
        self.assertEqual([p['file'] for p in photos], [cached(i)['file'] for i in [1, *range(3, 12)]])
        self.assertEqual(sum('/api/' in call.args[0] for call in get.call_args_list), 1)
        image.convert.assert_called_with('RGB'); image.thumbnail.assert_called_with((1200, 800))
        self.assertEqual(image.save.call_args.args[1], 'JPEG')
        self.assertEqual(image.save.call_args.kwargs, {'quality': 78, 'optimize': True, 'progressive': True})
        self.assertEqual(self.read_index(), self.read_index(self.docs))
        for p in photos:
            self.assertEqual((self.globe / p['file']).read_bytes(), b'encoded-jpeg')
            self.assertEqual((self.docs / p['file']).read_bytes(), b'encoded-jpeg')
        selected = next(p for p in photos if p['file'] == result['file'])
        self.assertEqual(result['credit'], selected['credit']); self.assertEqual(result['source_url'], selected['source_url'])
        self.assertEqual(result['source'], 'Pixabay')
        self.assertEqual(result['license_url'], 'https://pixabay.com/service/license-summary/')

    def test_legacy_pool_top_up_happens_once_and_preserves_existing_entries(self):
        before = [cached(i) for i in range(1, 4)]; self.index(before); pil, _ = self.image_encoder()
        with patch.dict('sys.modules', {'PIL': pil}), patch.object(robot, 'get', side_effect=self.pixabay()) as get:
            robot.photo(TOPIC, 'one', []); robot.photo(TOPIC, 'two', [])
        self.assertEqual(sum('/api/' in call.args[0] for call in get.call_args_list), 1)
        index = self.read_index(); self.assertEqual(index[TOPIC][:3], before)
        self.assertEqual(len(index[TOPIC]), 10); self.assertIn(TOPIC, index['_topup_attempted'])
        self.assertEqual(robot.status['photos_downloaded'], 7)

    def test_failed_or_short_top_up_is_not_retried_and_cached_photos_survive(self):
        for response in [OSError('Pixabay unavailable'), json.dumps({'hits': []})]:
            with self.subTest(response=response):
                self.index([cached(1)])
                kwargs = {'side_effect': response} if isinstance(response, Exception) else {'return_value': response}
                with patch.object(robot, 'get', **kwargs) as get:
                    self.assertEqual(robot.photo(TOPIC, 'one', [])['file'], cached(1)['file'])
                    self.assertEqual(robot.photo(TOPIC, 'two', [])['file'], cached(1)['file'])
                self.assertEqual(get.call_count, 1)
                self.assertIn(TOPIC, self.read_index()['_topup_attempted'])
                self.assertEqual(self.read_index(), self.read_index(self.docs))

    def test_missing_pool_pixabay_failure_does_not_raise(self):
        self.index()
        with patch.object(robot, 'get', side_effect=OSError('offline')) as get:
            for i in range(4): self.assertIsNone(robot.photo(TOPIC, str(i), []))
        self.assertEqual(get.call_count, 2)  # initial request, then at most one top-up

    def test_editor_counts_retained_old_stories_and_new_batch(self):
        self.index([cached(i) for i in range(10)])
        cands = [{'title': f'Real candidate {i}', 'source': 'Source', 'url': f'https://example.com/{i}',
                  'published': '2026-10-21T12:00:00Z', 'kind': 'news'} for i in range(12)]
        picked = [{'members': [i], 'headline': c['title'], 'country': 'US', 'category': 'companies',
                   'lat': 30, 'lon': -97, 'importance': 2, 'photo': TOPIC} for i, c in enumerate(cands)]
        old = [{'id': 'old', 'published_at': '2026-10-20T12:00:00Z', 'image': {'file': cached(0)['file']}}]
        with patch.object(robot, 'describe', side_effect=lambda c: c), patch.object(robot, 'gemini', return_value=picked), \
             patch.object(robot, 'get', side_effect=AssertionError('no real network')):
            new = robot.pick_stories(copy.deepcopy(cands), {}, {'US': 'United States of America'}, {}, {'US'}, 12, old)
        files = [old[0]['image']['file']] + [s['image']['file'] for s in new]
        self.assertEqual(len(set(files[:10])), 10)
        self.assertEqual(max(Counter(files).values()), 2)
        # If the old story is trimmed from the feed, its photo becomes available.
        picked = picked[:10]; cands = cands[:10]
        with patch.object(robot, 'MAX_STORIES', 10), patch.object(robot, 'describe', side_effect=lambda c: c), \
             patch.object(robot, 'gemini', return_value=picked):
            new = robot.pick_stories(cands, {}, {'US': 'United States of America'}, {}, {'US'}, 10, old)
        self.assertEqual(len({s['image']['file'] for s in new}), 10)


if __name__ == '__main__': unittest.main()
