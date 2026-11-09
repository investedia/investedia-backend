"""Read-only checks on restored P0b artifacts. Never regenerate/backfill historical inputs."""
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]

class HistoryConnections(unittest.TestCase):
    def test_original_bytes_event_identity_and_structural_guards(self):
        manifest=json.loads((ROOT/'data/connections-history-provenance.json').read_text())
        files=sorted((ROOT/'assets/globe/connections-history').glob('*.json'))
        self.assertEqual({f.name for f in files},set(manifest['sha256']))
        total=0
        for path in files:
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),manifest['sha256'][path.name])
            data=json.loads(path.read_text());self.assertEqual(data['day'],path.stem)
            ids={e['id'] for e in json.loads((ROOT/'assets/globe/events'/path.name).read_text())['events']}
            for conn in data['connections']:
                total+=1
                self.assertIn(conn['event'],ids)
                self.assertGreaterEqual(conn['km'],100)
                self.assertGreaterEqual(conn['confidence'],.25)
                self.assertNotEqual(conn['type'],'sector')
                self.assertTrue(conn['evidence']['source']);self.assertTrue(conn['explanation'])
        self.assertEqual(total,1498)
