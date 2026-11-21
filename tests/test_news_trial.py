"""Offline isolation checks; no provider calls and no repository snapshot writes."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("news_trial", ROOT / "workers/news-trial/runner.py")
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)

class NewsTrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed = trial.pack(ROOT, include_library=False)

    def test_seed_preserves_real_data_and_excludes_historical_library(self):
        self.assertEqual(self.seed["files"]["news-live.json"], json.loads((ROOT / "assets/globe/news-live.json").read_text(encoding="utf-8")))
        self.assertFalse(any(n.startswith("library/") for n in self.seed["files"]))
        self.assertLess(len(json.dumps(self.seed).encode()), trial.LIMIT)

    def test_rejects_paths_and_missing_state(self):
        for name in ("../config.local.json", "/tmp/a.json", "events/../../key.json", "library/x/../a.json", "photos/x.jpg", "connections.json"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                trial.validate({"files": {**self.seed["files"], name: {}}})
        with self.assertRaises(ValueError):
            trial.validate({"files": {}})

    def test_stale_status_is_failure_even_when_producer_exits_zero(self):
        original = json.dumps(self.seed, sort_keys=True)
        with patch.object(trial.subprocess, "run") as call:
            with self.assertRaisesRegex(ValueError, "fresh success"):
                trial.run(self.seed)
        self.assertEqual(call.call_count, 1)
        self.assertEqual(json.dumps(self.seed, sort_keys=True), original)
        args, kwargs = call.call_args
        self.assertTrue(args[0][-1].endswith("update_globe_news.py"))
        self.assertNotIn("NEWS_INGEST_TOKEN", kwargs["env"])
        self.assertNotIn("WORKER_URL", kwargs["env"])
        self.assertEqual(kwargs["env"]["PIXABAY_KEY"], "")
        self.assertEqual(kwargs["env"]["GEMINI_API_KEY"], "trial-proxy")
        self.assertFalse(Path(kwargs["cwd"]).exists())

    def test_offline_connections_on_real_seed(self):
        import subprocess, sys
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in trial.SOURCES:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                trial.shutil.copyfile(ROOT / name, target)
            for name, value in self.seed["files"].items():
                target = root / "assets/globe" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(value), encoding="utf-8")
            subprocess.run([sys.executable, str(root / "tools/globe-news/connections.py")], cwd=root,
                           check=True, stdout=subprocess.DEVNULL, timeout=60)
            result = json.loads((root / "assets/globe/connections.json").read_text())
            self.assertEqual(result["schema"], "investedia.connections.v1")
            self.assertFalse(result["rules"]["sector_lines"])
            self.assertGreater(result["diag"]["articles"], 0)

if __name__ == "__main__":
    unittest.main()
