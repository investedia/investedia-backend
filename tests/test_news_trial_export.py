"""Check the real export workflow's age gate without GitHub or provider calls."""
import json
from pathlib import Path
import textwrap
import unittest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/export-news-trial-seed.yml'
SOURCE = WORKFLOW.read_text(encoding='utf-8')
GATE = textwrap.dedent(SOURCE.split("python - <<'PY'\n", 1)[1].split('\n          PY', 1)[0])

class TrialExportTests(unittest.TestCase):
    def check_gate(self, stamp):
        status = {'tiers': {'priority': {'last_success': stamp}}} if stamp else {}
        with patch.object(Path, 'read_text', return_value=json.dumps(status)), patch('builtins.print'):
            exec(compile(GATE, str(WORKFLOW), 'exec'), {})

    def test_accepts_recent_success(self):
        self.check_gate((datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat())

    def test_rejects_missing_stale_and_future_state(self):
        now = datetime.now(timezone.utc)
        for stamp in (None, (now - timedelta(hours=7)).isoformat(), (now + timedelta(hours=1)).isoformat()):
            with self.subTest(stamp=stamp), self.assertRaises(SystemExit):
                self.check_gate(stamp)

if __name__ == '__main__':
    unittest.main()
