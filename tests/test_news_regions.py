import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import update_globe_news as u


def c(i, region=None):
    return {'title': f't{i}', 'url': f'https://x/{i}', 'source': f's{i % 40}', 'published': '2026-10-26T00:00:00Z', 'kind': 'news', **({'region': region} if region else {})}


class Balance(unittest.TestCase):
    def test_reserved_slots_mix_regions_and_keep_the_limit(self):
        cands = [c(i) for i in range(200)] + [c(1000 + i, 'af') for i in range(30)] + [c(2000 + i, 'latam') for i in range(30)] + [c(3000 + i, 'me') for i in range(30)]
        out = u.balance(cands, 200)
        self.assertEqual(len(out), 200)
        regs = [x.get('region') for x in out]
        self.assertGreaterEqual(regs.count(None), u.CORE_FIRST)  # core (non-regional) candidates go in first
        for r in ('af', 'latam', 'me'):
            self.assertGreaterEqual(regs.count(r), u.REGION_EACH)

    def test_a_thin_region_does_not_block_the_others(self):
        cands = [c(i) for i in range(50)] + [c(900, 'af')] + [c(910 + i, 'latam') for i in range(40)]
        out = u.balance(cands, 80)
        regs = [x.get('region') for x in out]
        self.assertEqual(regs.count('af'), 1)
        self.assertEqual(regs.count('latam'), 80 - 50 - 1)  # all 50 core first, then the regions share what is left
        self.assertEqual(len(out), 80)

    def test_without_regional_candidates_nothing_changes(self):
        cands = [c(i) for i in range(30)]
        self.assertEqual(u.balance(cands, 20), cands[:20])

    def test_every_regional_feed_names_a_known_region(self):
        known = ('af', 'latam', 'me', 'asia', 'eu', 'oc', 'na')
        self.assertTrue(all(r in known for _, _, r in u.REGION_FEEDS))
        self.assertTrue(all(r in known for _, r in u.REGION_GDELT))

    def test_weak_regional_items_are_not_reserved(self):
        cands = [{**c(i), 'score': 80 - i * .1} for i in range(100)] + [{**c(500 + i, 'asia'), 'score': 5} for i in range(30)]
        out = u.balance(cands, 90)
        self.assertEqual(sum(1 for x in out if x.get('region')), 0)  # below the median score: balance never promotes them


if __name__ == '__main__':
    unittest.main()
