"""Validate the preview projection against its real sources, not UI markup."""
import importlib.util
import json
import hashlib
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('market_focus', ROOT / 'tools/globe-news/build_market_focus.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class MarketFocusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read = lambda p: json.loads((ROOT / p).read_text())
        cls.focus = read('assets/globe/market-focus.json')
        cls.news = {a['id']: a for a in read('assets/globe/news-48h.json')['stories']}
        cls.registry = read('data/registry.json')['assets']
        cls.links = {l['id']: l for l in read('assets/globe/connections.json')['connections']}
        cls.iso = read('assets/globe/iso.json')
        cls.snapshot = read('assets/globe/' + cls.focus['source_file'])

    def test_versioned_snapshot_matches_the_reported_source_fields(self):
        filename = self.focus['source_file']
        digest = hashlib.sha256((ROOT / 'assets/globe' / filename).read_bytes()).hexdigest()[:12]
        self.assertEqual(filename, 'market-focus-source-' + digest + '.json')
        self.assertEqual(self.snapshot['updated_at'], self.focus['updated_at'])
        self.assertEqual({a['id'] for a in self.snapshot['articles']}, set(self.news))
        for a in self.snapshot['articles']:
            original = self.news[a['id']]
            for field in ['headline', 'source', 'published_at', 'importance']:
                self.assertEqual(a[field], original[field])
            for impact in a['impacts']:
                self.assertTrue(any(all(i.get(k) == v for k, v in impact.items()) for i in original['impacts']))
        self.assertNotIn('registry', self.snapshot)
        for code, c in self.snapshot['globe_focus']['countries'].items():
            for key, value in c.items(): self.assertEqual(value, self.focus['countries'][code][key])

    def test_bounded_and_source_faithful_developments(self):
        self.assertLess((ROOT / 'assets/globe/market-focus.json').stat().st_size, 300000)
        for code, country in self.focus['countries'].items():
            self.assertLessEqual(len(country['developments']), 60)
            expected = [a for a in self.news.values() if self.iso.get(a['location']['country']) == code]
            self.assertEqual(country['counts']['articles_48h'], len(expected))
            for a in country['developments']:
                source = self.news[a['id']]
                for field in ['headline', 'published_at', 'source']:
                    self.assertEqual(a[field], source[field])
                self.assertEqual(a['category'], self.focus['article_categories'][a['id']])

    def test_labels_have_two_important_articles_in_the_same_group(self):
        for code, country in self.focus['countries'].items():
            for label in country['labels']:
                group = 'International impact' if label == 'International' else label
                count = sum(a.get('importance', 1) >= 2 and self.focus['article_categories'][a['id']] == group
                            for a in self.news.values() if self.iso.get(a['location']['country']) == code)
                self.assertGreaterEqual(count, 2)

    def test_research_has_source_impacts_and_verified_listing_ids(self):
        for code, country in self.focus['countries'].items():
            expected = {i['name'].casefold() for a in self.news.values()
                        if self.iso.get(a['location']['country']) == code for i in a['impacts']
                        if i.get('kind') in ('company', 'etf') and i.get('name')}
            self.assertEqual({i['name'].casefold() for i in country['investments']}, expected)
            for item in country['investments']:
                self.assertIn(item['evidence_article_id'], item['article_ids'])
                self.assertEqual(item['count'], len(set(item['article_ids'])))
                for aid in item['article_ids']:
                    self.assertTrue(any(i.get('name') == item['name'] and i.get('kind') in ('company', 'etf') for i in self.news[aid]['impacts']))
                if item['registry_id']:
                    self.assertIn(item['registry_id'], self.registry)
                    self.assertEqual(item['mic'], self.registry[item['registry_id']]['mic'])
                else:
                    self.assertIsNone(item['ticker'])
                    self.assertIsNone(item['mic'])

    def test_connections_are_cross_border_reported_events_in_the_window(self):
        verified_events = {l['event'] for l in self.links.values() if l.get('cross_border')}
        for aid, category in self.focus['article_categories'].items():
            if category == 'International impact': self.assertIn(aid, verified_events)
        for code, country in self.focus['countries'].items():
            for lid in country['connections']:
                link = self.links[lid]
                self.assertIn(link['event'], self.news)
                self.assertTrue(link['cross_border'])
                self.assertIn(code, [link['origin']['country'], link['dest']['country']])
                self.assertEqual(link['evidence']['headline'], self.news[link['event']]['headline'])

    def test_missing_data_and_policy_ranking(self):
        ng, my, tz = [self.focus['countries'][c] for c in ['NG', 'MY', 'TZ']]
        self.assertIn('Central Bank of Nigeria', ng['developments'][0]['headline'])
        self.assertEqual(my['exchange'], 'XKLS')
        self.assertIsNone(tz['exchange'])
        self.assertEqual(tz['counts']['articles_48h'], 1)
        self.assertEqual(tz['currency_facts']['currency'], 'TZS')
        self.assertEqual(tz['currency_facts']['currency_name'], 'Shilling')
        for c in self.focus['countries'].values(): self.assertNotIn('price_rights', c)


if __name__ == '__main__': unittest.main()
