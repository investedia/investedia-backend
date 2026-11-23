"""Offline calendar isolation checks using the existing saved calendar."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("calendar_trial_runner", ROOT / "workers/news-trial/runner.py")
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)

class CalendarTrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = json.loads((ROOT / "assets/calendar-live.json").read_text(encoding="utf-8"))
        cls.state = {"files": {"calendar-live.json": cls.saved}}

    def test_rejects_extra_paths_and_invalid_shapes(self):
        for value in ({"files": {}}, {"files": []}, {"files": {"calendar-live.json": self.saved, "../key.json": {}}},
                      {"files": {"calendar-live.json": {"events": {}, "earnings": []}}}):
            with self.subTest(value=type(value)), self.assertRaises(ValueError):
                trial.validate_calendar(value)
        self.assertEqual(trial.decode_bundle(trial.encode_bundle(self.state), trial.validate_calendar), self.state)

    def test_success_isolated_and_retains_event_dates_and_values(self):
        original = json.dumps(self.state, sort_keys=True)
        def process(args, **kwargs):
            root = Path(kwargs["cwd"])
            self.assertTrue(args[-1].endswith("calendar_job.py"))
            self.assertEqual(kwargs["env"]["CALENDAR_UNLICENSED"], "off")
            self.assertEqual(kwargs["env"]["FRED_API_KEY"], "trial-proxy")
            self.assertNotIn("NEWS_INGEST_TOKEN", kwargs["env"])
            self.assertNotIn("GEMINI_API_KEY", kwargs["env"])
            value = json.loads((root / "assets/calendar-live.json").read_text())
            value["updated_at"] = datetime.now(timezone.utc).isoformat()
            (root / "assets/calendar-live.json").write_text(json.dumps(value))
            (root / "calendar-trial-status.json").write_text(json.dumps({"official_events": 1, "failed_sources": [], "fred_configured": True, "fred_failures": 0}))
        with patch.object(trial.subprocess, "run", side_effect=process) as call:
            result = trial.run_calendar(self.state, fred_enabled=True)
        self.assertEqual(result["files"]["calendar-live.json"]["events"], self.saved["events"])
        self.assertEqual(json.dumps(self.state, sort_keys=True), original)
        self.assertFalse(Path(call.call_args.kwargs["cwd"]).exists())
        self.assertTrue(result["summary"]["fred_configured"])

    def test_wrapper_rejects_no_source_events_and_swallowed_event_errors(self):
        source = (ROOT / "workers/news-trial/calendar_job.py").read_text()
        for result, message in (({"official": []}, ""), ({"official": [self.saved["events"][0]]}, "events failed: private error")):
            with tempfile.TemporaryDirectory() as tmp:
                def run(*args, **kwargs):
                    if message: print(message)
                    return result
                with patch("runpy.run_path", side_effect=run), self.assertRaises(SystemExit):
                    exec(compile(source, "calendar_job.py", "exec"), {"__name__": "__main__", "__file__": str(Path(tmp) / "workers/news-trial/calendar_job.py")})
                self.assertFalse((Path(tmp) / "calendar-trial-status.json").exists())

    def test_diagnostics_never_contain_raw_error_messages(self):
        error = trial.GenerationFailed({"fetched": 12, "candidates": 4, "gemini_ok": False,
                "failed_sources": ["source"], "errors": ["HTTP 503 private-key-must-not-leak"]})
        self.assertEqual(error.diagnostic["http_statuses"], [503])
        self.assertNotIn("private-key", json.dumps(error.diagnostic))

if __name__ == '__main__':
    unittest.main()
