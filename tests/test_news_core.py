"""Offline tests for news_core: normalisation, dedupe, dates, scoring, validation, atomic writes, retention, stale labels."""
import json, os, sys, tempfile, unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import news_core as c

NOW = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
def cand(title, url, kind='news', mins=10, **k):
    return {'title': title, 'url': url, 'source': k.pop('source', 'X'), 'kind': kind, 'published': c.iso(NOW - timedelta(minutes=mins)), **k}
def story(i, mins=10):
    return {'id': i, 'headline': 'h', 'category': 'markets', 'source': {'name': 'S'}, 'location': {'country': 'US'}, 'published_at': c.iso(NOW - timedelta(minutes=mins))}

class Core(unittest.TestCase):
    def test_canon_url(self):
        a = c.canon('https://www.Example.com/a/b/?utm_source=x&id=7#frag')
        self.assertEqual(a, 'example.com/a/b?id=7')
        self.assertEqual(c.canon('https://example.com/a/b/amp/'), 'example.com/a/b')

    def test_dates_utc_and_future_clamped(self):
        self.assertEqual(c.parse_time('Wed, 28 Oct 2026 10:00:00 +0200', NOW), datetime(2026, 10, 28, 8, 0, tzinfo=timezone.utc))
        self.assertEqual(c.parse_time('2026-10-28T11:00:00', NOW).hour, 11)  # naive = UTC
        self.assertEqual(c.parse_time('2027-01-01T00:00:00Z', NOW), NOW)     # future -> now
        for bad in ('', None, 'garbage', '32/13/2026'): self.assertIsNone(c.parse_time(bad, NOW))

    def test_dedupe_prefers_official_and_merges(self):
        items = [cand('ECB holds interest rates steady at 2%', 'https://a.com/1', source='Blog', mins=30),
                 cand('ECB holds interest rates steady at 2%', 'https://ecb.eu/p', kind='official', source='ECB', mins=5),
                 cand('Different story about copper mine strike in Chile', 'https://c.com/9')]
        kept, dropped = c.dedupe(items, [], NOW)
        self.assertEqual(dropped, 1); self.assertEqual(len(kept), 2)
        self.assertEqual([k for k in kept if 'ECB' in k['title']][0]['source'], 'ECB')

    def test_dedupe_same_url_known_titles_and_time_window(self):
        a = cand('Fed cuts rates by 25 basis points', 'https://x.com/a?utm_medium=1')
        b = cand('Fed cuts rates by 25 basis points', 'https://www.x.com/a')
        self.assertEqual(len(c.dedupe([a, b], [], NOW)[0]), 1)
        self.assertEqual(len(c.dedupe([a], [('Fed cuts rates by 25 basis points', c.iso(NOW))], NOW)[0]), 0)
        self.assertEqual(len(c.dedupe([cand('Oil prices jump as OPEC trims output', 'https://y.com/1')], [], NOW)[0]), 1)

    def test_entity_similarity(self):
        self.assertTrue(c.same_event('Nvidia shares jump 8% after record earnings', 'Nvidia stock surges 8% on record earnings beat', 2))
        self.assertFalse(c.same_event('Apple unveils new iPhone', 'Tesla recalls vehicles', 1))

    def test_scoring_orders_sensibly(self):
        official = cand('ECB raises interest rates in surprise decision', 'u1', kind='official', mins=3)
        old = cand('Local shop opens new branch', 'u2', mins=900)
        macro = cand('US inflation CPI surges, Treasury yields jump', 'u3', mins=20)
        so, sl, sm = c.score(official, NOW), c.score(old, NOW), c.score(macro, NOW)
        same = cand('ECB raises interest rates in surprise decision', 'u4', mins=3)
        self.assertGreater(so, c.score(same, NOW))  # official beats the same headline from a publisher
        self.assertGreater(sm, sl); self.assertGreater(so, sl)
        self.assertLess(c.score(macro, NOW, dup_count=3), sm)
        for v in (so, sl, sm): self.assertTrue(0 <= v <= 100)

    def test_content_hash_changes_only_with_text(self):
        a = cand('T', 'u', desc='d'); b = dict(a, url='other'); d = dict(a, desc='changed')
        self.assertEqual(c.content_hash(a), c.content_hash(b)); self.assertNotEqual(c.content_hash(a), c.content_hash(d))

    def test_validate_rejects_empty_malformed_duplicates(self):
        self.assertTrue(c.validate_feed({'stories': []}))
        self.assertTrue(c.validate_feed([]))
        self.assertTrue(c.validate_feed({'stories': [story('a'), story('a')]}))
        self.assertTrue(c.validate_feed({'stories': [{'id': 'x'}]}))
        bad = story('b'); bad['published_at'] = 'nope'
        self.assertTrue(c.validate_feed({'stories': [bad]}))
        self.assertEqual(c.validate_feed({'stories': [story('a'), story('b')]}), [])

    def test_atomic_write_keeps_previous_on_failure(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'f.json')
            c.atomic_write(p, {'stories': [story('a')]}, c.validate_feed)
            with self.assertRaises(ValueError): c.atomic_write(p, {'stories': []}, c.validate_feed)
            with self.assertRaises(TypeError): c.atomic_write(p, {'x': object()})
            self.assertEqual(json.load(open(p))['stories'][0]['id'], 'a')
            self.assertEqual([f for f in os.listdir(d) if f.startswith('.tmp')], [])

    def test_retention_unique_ids_and_limits(self):
        s = [story('a', 10), story('a', 20), story('old', 60 * 24 * 40), story('b', 30), story('c', 5)]
        out = c.retain(s, NOW, 30, 10)
        self.assertEqual([x['id'] for x in out], ['c', 'a', 'b'])
        self.assertEqual(len(c.retain(s, NOW, 30, 2)), 2)

    def test_freshness_labels_never_say_live(self):
        for m, want in ((0, 'just now'), (3, '3m ago'), (125, '2h ago'), (3000, '2d ago')):
            label = c.freshness(c.iso(NOW - timedelta(minutes=m)), NOW)
            self.assertIn(want, label); self.assertNotIn('LIVE', label.upper())

if __name__ == '__main__': unittest.main()
