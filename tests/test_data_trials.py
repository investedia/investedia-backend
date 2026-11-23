"""Offline boundary checks using existing saved observations; no provider calls."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("trial_data", ROOT / "workers/news-trial/runner.py")
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)
stage_spec = importlib.util.spec_from_file_location("stage_frontend", ROOT / "tools/cloudflare/stage_frontend.py")
staging = importlib.util.module_from_spec(stage_spec)
stage_spec.loader.exec_module(staging)


class DataTrialTests(unittest.TestCase):
    def test_state_paths_and_job_names_fail_closed(self):
        for job in trial.DATA_JOBS:
            for name in ("../config.local.json", "/tmp/x.json", "US/../GB.json", "bad.json"):
                with self.subTest(job=job, name=name), self.assertRaises(ValueError):
                    trial.validate_data({"files": {name: {}}}, job)
        with self.assertRaises(ValueError):
            trial.validate_data({"files": {}}, "command")
        with self.assertRaises(ValueError):
            trial.validate_data({"files": {}}, "markets")

    def test_market_seed_rejects_duplicates_and_preserves_universe(self):
        seed = {"files": {"markets.json": json.loads((ROOT / "assets/globe/markets.json").read_text(encoding="utf-8"))}}
        original = copy.deepcopy(seed)
        self.assertIs(trial.validate_data(seed, "markets"), seed)
        with patch.object(trial, "DATA_SOURCES", {"markets": ()}), patch.object(trial.subprocess, "run") as call:
            with self.assertRaisesRegex(ValueError, "Stale"):
                trial.run_data(seed, "markets")
        self.assertEqual(seed, original)
        env = call.call_args.kwargs["env"]
        for secret in ("GEMINI_API_KEY", "FRED_API_KEY", "NEWS_INGEST_TOKEN", "WORKER_URL", "ANTHROPIC_API_KEY"):
            self.assertNotIn(secret, env)
        self.assertFalse(Path(call.call_args.kwargs["cwd"]).exists())
        seed["files"]["markets.json"]["assets"].append(seed["files"]["markets.json"]["assets"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            trial.validate_data(seed, "markets")

    def test_failed_generator_cannot_produce_or_mutate_state(self):
        for job in ("fx", "economy-history", "country-basics"):
            seed = {"files": {}}
            with self.subTest(job=job), patch.object(trial, "DATA_SOURCES", {job: ()}), patch.object(trial.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "fixed")) as call:
                with self.assertRaises(subprocess.CalledProcessError):
                    trial.run_data(seed, job)
                self.assertFalse(Path(call.call_args.kwargs["cwd"]).exists())
                self.assertNotIn("GEMINI_API_KEY", call.call_args.kwargs["env"])
                self.assertEqual(seed, {"files": {}})

    def test_country_output_stays_review_only_and_observations_unchanged(self):
        saved = json.loads((ROOT / "data/country-basics.json").read_text(encoding="utf-8"))
        # Simulate only the refresh status; retain every real saved observation and date.
        saved["refresh"]["failed_fields"] = []
        def output(command, **kwargs):
            path = Path(kwargs["cwd"]) / "out/country-basics.json"
            path.parent.mkdir()
            path.write_text(json.dumps(saved), encoding="utf-8")
            self.assertEqual(command[-3:], ["--fetch", "--output", "out/country-basics.json"])
        with patch.object(trial.subprocess, "run", side_effect=output):
            result = trial.run_data({"files": {}}, "country-basics")
        self.assertEqual(result["files"]["country-basics.json"], saved)
        self.assertTrue(result["summary"]["review_only"])
        self.assertEqual(result["summary"]["gemini_calls"], 0)

    def test_staging_reads_only_four_pinned_git_blobs(self):
        calls = []
        def git(command, **kwargs):
            calls.append(command)
            body = b"100644 blob id file" if "ls-tree" in command else b"{}"
            return subprocess.CompletedProcess(command, 0, stdout=body)
        with tempfile.TemporaryDirectory() as tmp, patch.object(staging.subprocess, "run", side_effect=git):
            target = Path(tmp) / "staged"
            staging.stage(Path(tmp), target)
            self.assertEqual({p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}, set(staging.FILES))
        for call in calls:
            self.assertTrue(any(staging.COMMIT in part for part in call))
        with tempfile.TemporaryDirectory() as tmp, patch.object(staging.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout=b"120000 blob id file")):
            with self.assertRaisesRegex(ValueError, "regular"):
                staging.stage(Path(tmp), Path(tmp) / "staged")
