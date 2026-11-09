"""Offline impact validation against the existing feed. Never calls Gemini or edits it."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('news_robot', ROOT / 'update_globe_news.py')
robot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(robot)
ISO = set(json.loads((ROOT / 'tools/globe-news/iso.json').read_text()).values())
FEED = json.loads((ROOT / 'assets/globe/news-live.json').read_text())
FIXTURE = json.loads((ROOT / 'tests/fixtures/impacts-response.json').read_text())

class NewsImpacts(unittest.TestCase):
    def test_typed_bounded_fields(self):
        robot.PROMPT.format(n=1, cats='markets', topics='oil', cands='[]', event_types='earnings', relations='subject')
        raw = copy.deepcopy(FIXTURE[0])
        raw['impacts'] = [None, {'kind': []}, {**raw['impacts'][0], 'country': 'ZZ'},
            {**raw['impacts'][0], 'direction': ['bad'], 'why': 'x' * 300, 'ticker': '<script>'}] + raw['impacts'] * 3
        result = robot.validate_analysis(raw, True, ISO)
        self.assertEqual(len(result['impacts']), robot.MAX_IMPACTS)
        self.assertEqual(result['impacts'][0]['direction'], 'unclear')
        self.assertEqual(len(result['impacts'][0]['why']), 200)
        self.assertIsNone(result['impacts'][0]['ticker'])
        self.assertTrue(all(i['country'] in ISO for i in result['impacts']))
        self.assertIsNone(robot.validate_analysis(raw, False, ISO)['why_moved'])

    def test_implications_are_stamped_once_and_backfill_is_not_scorable(self):
        raw = copy.deepcopy(FIXTURE[0]); raw['impacts'][0].update(direction='up', ticker='AAPL', confidence='high')
        live = robot.validate_analysis(raw, True, ISO, created_at='2026-10-29T12:00:00Z')['impacts'][0]
        for k in ('created_at', 'version', 'confidence', 'horizon', 'baseline_rule', 'scorable'): self.assertIn(k, live)
        self.assertEqual(live['confidence'], 'high')
        self.assertTrue(live['scorable'])
        late = robot.validate_analysis(raw, True, ISO, created_at='2026-10-29T12:00:00Z', backfill=True)['impacts'][0]
        self.assertFalse(late['scorable'])
        raw['impacts'][0]['confidence'] = 'certain'
        self.assertEqual(robot.validate_analysis(raw, True, ISO, created_at='x')['impacts'][0]['confidence'], 'low')

    def test_missing_or_malformed_analysis(self):
        for raw in (None, [], {}, {'impacts': 'bad'}, {'impacts': [7, {}]}):
            self.assertEqual(robot.validate_analysis(raw, False, ISO), {'impacts': [], 'why_moved': None})

    def test_backfill_existing_feed_max_40_and_known_ids_only(self):
        stories = copy.deepcopy(FEED['stories'])
        for s in stories: s.pop('impacts', None)
        calls = []
        def fake(prompt):
            calls.append(prompt)
            inputs = json.loads(prompt.split('Stories:\n', 1)[1])
            rows = []
            for s in inputs:
                row = copy.deepcopy(FIXTURE[0]); row['id'] = s['id']; rows.append(row)
            return [{'id': [], 'impacts': []}, {'id': 'unknown', 'impacts': []}] + rows
        n = robot.backfill_impacts(stories, ISO, fake)
        self.assertEqual(n, min(40, len(stories)))
        self.assertEqual(len(calls), 1)
        self.assertTrue(all('impacts' not in s for s in stories[40:]))
        for before, after in zip(FEED['stories'], stories):
            self.assertEqual(before['headline'], after['headline'])
            self.assertEqual(before['summary'], after['summary'])
            self.assertEqual(before['sources'], after['sources'])
            if not after.get('market_moving'): self.assertIsNone(after.get('why_moved'))

    def test_failure_does_not_mark_stories_complete(self):
        stories = copy.deepcopy(FEED['stories'][:2]); before = copy.deepcopy(stories)
        def fail(_): raise RuntimeError('offline fixture failure')
        self.assertEqual(robot.backfill_impacts(stories, ISO, fail), 0)
        self.assertEqual(stories, before)
        self.assertEqual(robot.backfill_impacts(stories, ISO, lambda _: {'bad': True}), 0)
        self.assertEqual(stories, before)

    def test_main_pipeline_uses_fake_response_and_memory_only(self):
        writes = {}
        def fake(prompt):
            inputs = json.loads(prompt.split('Stories:\n', 1)[1])
            return [{**copy.deepcopy(FIXTURE[0]), 'id': s['id']} for s in inputs]
        latest = max(robot.datetime.fromisoformat(s['published_at'].replace('Z', '+00:00')) for s in FEED['stories'])
        before = (ROOT / 'assets/globe/news-live.json').read_bytes()
        with patch.object(robot.EV, 'upsert', return_value=0), patch.object(robot.EV, 'write_threads', return_value=0), patch.object(robot, 'save_seen'), patch.object(robot, 'gdelt', return_value=[]), patch.object(robot, 'rss', return_value=[]), \
             patch.object(robot, 'gemini', side_effect=fake), patch.object(robot, 'save', side_effect=lambda n,v,feed=False:writes.update({n:v})), \
             patch.object(robot, 'NOW', latest):
            robot.main()
        self.assertIn('news-live.json', writes)
        had = {s['id'] for s in FEED['stories'] if 'impacts' in s}  # the live feed may already carry real analysis
        had |= {s['id'] for s in json.loads((ROOT / 'assets/globe/news-archive.json').read_text())['stories'] if 'impacts' in s}  # with the 360-story live file, archive stories (already analysed) move into it
        self.assertLessEqual(sum('impacts' in s and s['id'] not in had for s in writes['news-live.json']['stories']), 40)
        self.assertEqual((ROOT / 'assets/globe/news-live.json').read_bytes(), before)

    def _run(self, tier, raw, gemini):
        writes, seen = {}, {}
        latest = robot.datetime.fromisoformat(max(s['published_at'] for s in FEED['stories']).replace('Z', '+00:00'))
        with patch.object(robot.EV, 'upsert', return_value=0), patch.object(robot.EV, 'write_threads', return_value=0), patch.object(robot, 'TIER', tier), patch.object(robot, 'gdelt', return_value=[]), patch.object(robot, 'rss', return_value=raw), \
             patch.object(robot, 'gemini', side_effect=gemini), patch.object(robot, 'backfill_impacts', return_value=0), patch.object(robot, 'load_seen', return_value={}), \
             patch.object(robot, 'save_seen', side_effect=lambda x: seen.update(x)), patch.object(robot, 'NOW', latest), \
             patch.object(robot, 'save', side_effect=lambda n, v, feed=False: writes.update({n: v})):
            robot.status.update({'errors': [], 'failed_sources': []}); robot.status.pop('gemini_ok', None)
            robot.main()
        return writes, seen

    def _cand(self):
        return [{'title': 'Brand new central bank surprise decision on interest rates', 'url': 'https://example.org/zz1', 'source': 'Example', 'kind': 'news',
                 'published': max(s['published_at'] for s in FEED['stories']), 'desc': 'd'}]

    def test_priority_tier_never_rewrites_archive(self):
        ok = lambda prompt: [{**copy.deepcopy(FIXTURE[0]), 'members': [0], 'headline': 'Rates decision', 'category': 'economy', 'country': 'US', 'lat': 38.9, 'lon': -77, 'place': 'Washington'}]
        writes, seen = self._run('priority', self._cand(), ok)
        self.assertNotIn('news-archive.json', writes); self.assertIn('news-live.json', writes)
        self.assertEqual(writes['news-status.json']['tiers']['priority']['new_articles'], 1)
        self.assertTrue(seen)

    def test_failed_gemini_does_not_mark_candidates_judged_and_empty_feed_not_published(self):
        def boom(prompt): raise RuntimeError('quota')
        writes, seen = self._run('priority', self._cand(), boom)
        self.assertFalse(seen); self.assertNotEqual(writes['news-status.json']['tiers']['priority'].get('last_success'), robot.ISO_NOW)  # a failed run never counts as a success
        self.assertTrue(all(v for v in [writes['news-live.json']['stories']]) if 'news-live.json' in writes else True)

    def test_no_candidates_keeps_feed_untouched_in_priority(self):
        writes, _ = self._run('priority', [], lambda p: [])
        self.assertNotIn('news-live.json', writes); self.assertNotIn('news-archive.json', writes)
        self.assertIn('last_success', writes['news-status.json']['tiers']['priority'])

if __name__ == '__main__': unittest.main()
