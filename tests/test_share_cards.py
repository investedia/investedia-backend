import json, os, sys, tempfile, unittest
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import update_share_cards as sc

NOW = datetime(2026, 10, 26, 18, 0, tzinfo=timezone.utc)
PUB = NOW - timedelta(hours=3)
STORY = {'id': 'nabc', 'headline': 'Oil slips as <b>Asian</b> shares open "cautiously"', 'summary': 'Short & sweet.', 'category': 'commodities',
         'published_at': PUB.strftime('%Y-%m-%dT%H:%M:%SZ'), 'location': {'place': 'Singapore', 'country': 'Singapore', 'lat': 1.35, 'lon': 103.8},
         'impacts': [{'name': 'Brent crude oil', 'ticker': 'BZ=F', 'direction': 'down'}, {'name': 'Utilities', 'ticker': None, 'direction': 'up'}]}
pm = lambda dt: int(dt.timestamp() // 60)


class ShareCards(unittest.TestCase):
    def test_move_since_uses_first_price_after_article(self):
        s = [[pm(PUB + timedelta(minutes=5)), 100], [pm(NOW), 90]]
        self.assertAlmostEqual(sc.move_since(PUB.timestamp(), s), -10.0)

    def test_move_since_needs_a_second_point_and_a_timely_first_one(self):
        self.assertIsNone(sc.move_since(PUB.timestamp(), [[pm(NOW), 90]]))
        late = [[pm(PUB + timedelta(hours=2)), 100], [pm(NOW), 90]]
        self.assertIsNone(sc.move_since(PUB.timestamp(), late))

    def test_pills_prefer_since_then_today_then_implied(self):
        by = {'BZ=F': {'n': 'Brent crude oil', 'd': -1.2}}
        track = {'s': {'BZ=F': [[pm(PUB + timedelta(minutes=5)), 100], [pm(NOW), 95]]}}
        self.assertEqual(sc.pills(STORY, by, track)[0][2], 'since')
        self.assertEqual(sc.pills(STORY, by, {})[0][2], 'today')
        p = sc.pills(STORY, {}, {})
        self.assertEqual(p[0][2], 'implied')
        self.assertEqual(sc.caption(p), 'Direction the article implies')

    def test_page_has_escaped_open_graph_tags_and_redirect(self):
        h = sc.page(STORY)
        self.assertIn('property="og:image" content="https://investedia.com/assets/share/nabc.png"', h)
        self.assertIn('twitter:card" content="summary_large_image"', h)
        self.assertIn('noindex', h)
        self.assertIn('story.html?id=nabc', h)
        self.assertNotIn('<b>Asian</b>', h)
        self.assertIn('&lt;b&gt;Asian', h)

    def test_render_is_1200_by_630(self):
        im = sc.render(STORY, sc.pills(STORY, {}, {}), NOW)
        self.assertEqual(im.size, (1200, 630))

    def test_run_writes_pages_prunes_old_and_lists_ids(self):
        with tempfile.TemporaryDirectory() as t:
            g = os.path.join(t, 'g'); os.makedirs(g)
            json.dump({'stories': [STORY]}, open(os.path.join(g, 'news-live.json'), 'w'))
            out = os.path.join(t, 'o'); os.makedirs(out); open(os.path.join(out, 'nold.png'), 'w').write('x')
            sc.G, sc.OUTS = g, [out]
            made, removed, n = sc.run(NOW)
            self.assertEqual((made, n), (1, 1)); self.assertEqual(removed, 1)
            self.assertTrue(os.path.exists(os.path.join(out, 'nabc.png')) and os.path.exists(os.path.join(out, 'nabc.html')))
            self.assertEqual(json.load(open(os.path.join(out, 'index.json'))), ['nabc'])
            self.assertEqual(sc.run(NOW)[0], 0)  # unchanged articles are not redrawn


if __name__ == '__main__':
    unittest.main()
