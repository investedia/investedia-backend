"""Exercise real local HTTP boundaries with saved snapshots; no provider calls."""
import importlib.util
import json
from pathlib import Path
from http.server import HTTPServer
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("data_export_runner", ROOT / "workers/news-trial/runner.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class DataExportTests(unittest.TestCase):
    def test_only_explicit_successful_market_and_fx_exports_are_available(self):
        for job, file, path in [("markets", "markets.json", ROOT / "assets/globe/markets.json"), ("fx", "fx-ecb.json", ROOT / "tests/fixtures/cloudflare-fx-ecb.json")]:
            saved = json.loads(path.read_text(encoding="utf-8"))
            seed = {"files": {file: saved}} if job == "markets" else {"files": {}}
            result = {"files": {file: saved}, "summary": {"trial": True, "job": job}}
            with self.subTest(job=job), HTTPServer(("127.0.0.1", 0), runner.Handler) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
                url = "http://127.0.0.1:" + str(server.server_port)
                try:
                    for enabled in (False, True):
                        headers = {"X-Data-Export": "1"} if enabled else {}
                        with patch.object(runner, "run_data", return_value=result):
                            with urllib.request.urlopen(urllib.request.Request(url + "/run?job=" + job, data=runner.encode_bundle(seed), headers=headers), timeout=5) as response:
                                self.assertEqual(response.status, 200)
                        if enabled:
                            with urllib.request.urlopen(url + "/output?kind=" + job, timeout=5) as response:
                                self.assertEqual(json.load(response), saved)
                        else:
                            with self.assertRaises(urllib.error.HTTPError) as error: urllib.request.urlopen(url + "/output?kind=" + job, timeout=5)
                            self.assertEqual(error.exception.code, 404); error.exception.close()
                    with patch.object(runner, "run_data", side_effect=ValueError("offline failure")):
                        with self.assertRaises(urllib.error.HTTPError) as error: urllib.request.urlopen(urllib.request.Request(url + "/run?job=" + job, data=runner.encode_bundle(seed), headers={"X-Data-Export": "1"}), timeout=5)
                        error.exception.close()
                    self.assertEqual(server.live_outputs, {})
                finally:
                    server.shutdown(); thread.join(timeout=5)


if __name__ == "__main__": unittest.main()
