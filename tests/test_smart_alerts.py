import importlib.util, json, unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('push_alerts', ROOT / 'tools/alerts/push_alerts.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
NOW = datetime(2026, 11, 11, 22, 0, tzinfo=timezone.utc)
def story(i, hours_ago, **kw):
    t = (NOW - timedelta(hours=hours_ago)).isoformat().replace('+00:00', 'Z')
    return {'id': i, 'headline': 'H ' + i, 'published_at': t, 'retrieved_at': t, 'location': {'country': 'Japan'}, 'category': 'Companies',
            'source': {'name': 'Src', 'url': 'https://x/' + i}, 'impacts': [{'ticker': '7201.t'}], 'entities': [{'ticker': 'NVDA'}, {'name': 'no ticker'}], **kw}
class SmartAlertsTests(unittest.TestCase):
    def test_payload_shape_window_and_dedupe(self):
        out = m.payload([story('a', 1), story('a', 1), story('old', 30), {'id': 'bad', 'published_at': 'x'}], {'Japan': 'JP'}, NOW)
        self.assertEqual([a['id'] for a in out], ['a'])
        a = out[0]
        self.assertEqual(a['country'], 'JP'); self.assertEqual(a['assets'], ['7201.T', 'NVDA']); self.assertEqual(a['topic'], 'companies')
        self.assertEqual(set(a), {'id', 'headline', 'source', 'url', 'published_at', 'country', 'assets', 'topic', 'importance'})
    def test_no_token_sends_nothing(self):
        with patch.dict('os.environ', {'ALERTS_INGEST_TOKEN': ''}), patch.object(m, 'send') as s:
            self.assertEqual(m.main(), 0); s.assert_not_called()
    def test_failure_never_breaks_the_news_run(self):
        with patch.dict('os.environ', {'ALERTS_INGEST_TOKEN': 't'}), patch.object(m, 'send', side_effect=OSError('down')):
            self.assertEqual(m.main(), 0)
    def test_token_is_never_printed(self):
        import io, contextlib
        buf = io.StringIO()
        with patch.dict('os.environ', {'ALERTS_INGEST_TOKEN': 'super-secret-token'}), patch.object(m, 'send', return_value={'inserted': 0}), contextlib.redirect_stdout(buf):
            m.main()
        self.assertNotIn('super-secret-token', buf.getvalue())
    def test_setup_sql_keeps_sending_off_and_free_limit_five(self):
        sql = (ROOT / 'emails/smart-alerts-setup.sql').read_text()
        self.assertIn('free_limit int not null default 5', sql); self.assertIn('update public.alert_config set sending = false', sql)
        self.assertIn('PASTE_A_LONG_RANDOM_TOKEN', sql); self.assertNotIn('sb_secret', sql)
if __name__ == '__main__': unittest.main()
