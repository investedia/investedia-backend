"""The US route (route B) is reproducible offline from the committed audited chains.
Skipped when the raw EIA files are absent (they are git-ignored: data/projects/raw/eia)."""
import json, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/projects/raw/eia'
MONTHLY, ANNUAL = RAW / 'september_generator2026.xlsx', RAW / '860_2025'


class Replay(unittest.TestCase):
    @unittest.skipUnless(MONTHLY.exists() and ANNUAL.exists(), 'raw EIA files not present')
    def test_replay_finds_every_audited_b_plant_and_nothing_new(self):
        from tools.projects.invest.engine import route_b_replay
        records, ledger, stats = route_b_replay.run(MONTHLY, ANNUAL, '2026-11-13', 2025)
        layer = json.loads((ROOT / 'assets/globe/projects-invest.json').read_text())['projects']
        committed_b = {p['id'] for p in layer if p['id'].startswith('eia:') and any((e.get('verification') or {}).get('category') == 'B' for e in p['exposures'])}
        replay_b = {r['id'] for r in records if (r.get('route_b') or {}).get('category') == 'B'}
        self.assertEqual(replay_b, committed_b)            # the same audited plants, no new B
        self.assertEqual(stats['plants'], 1021)
        for r in records:                                  # a plant outside the audited chains can never become B
            if r['id'] not in committed_b:
                self.assertNotEqual((r.get('route_b') or {}).get('category'), 'B')

    def test_committed_layer_keeps_the_audited_us_projects(self):
        layer = json.loads((ROOT / 'assets/globe/projects-invest.json').read_text())['projects']
        self.assertGreaterEqual(len(layer), 142)
        self.assertEqual(sum(1 for p in layer if p['id'].startswith('eia:')), 102)
        self.assertFalse([p['id'] for p in layer for e in p['exposures'] if not (e.get('hq') or {}).get('lat')])


if __name__ == '__main__':
    unittest.main()
