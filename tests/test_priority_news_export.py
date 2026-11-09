import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('news_export', ROOT/'tools/export-priority-news.py')
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class NewsExport(unittest.TestCase):
    def test_news_and_photo_bytes_preserved_financial_data_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            backend, frontend = Path(directory)/'backend', Path(directory)/'frontend'
            source = backend/'assets/globe'
            (source/'photos').mkdir(parents=True)
            (frontend/'scripts').mkdir(parents=True)
            (frontend/'scripts/sync-snapshots.py').touch()
            for name in exporter.NEWS: (source/name).write_text('{}')
            (source/'photos/photo.jpg').write_bytes(b'photo-test-bytes')
            (source/'v5-ledger.json').write_bytes(b'frozen')
            self.assertEqual(exporter.export(frontend, backend), len(exporter.NEWS)+1)
            target = frontend/'assets/globe/photos/photo.jpg'
            self.assertEqual(target.read_bytes(), b'photo-test-bytes')
            self.assertEqual(target.stat().st_mtime_ns, (source/'photos/photo.jpg').stat().st_mtime_ns)
            self.assertFalse((frontend/'assets/globe/v5-ledger.json').exists())
            target.unlink()
            (source/'photos/photo.jpg').unlink()
            (source/'photos/photo.jpg').symlink_to(source/'v5-ledger.json')
            with self.assertRaises(ValueError): exporter.export(frontend, backend)
