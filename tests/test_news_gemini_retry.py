"""Offline retry contract; no provider requests or financial content."""
import importlib.util
import io
import json
from pathlib import Path
import unittest
import urllib.error
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("news_retry_robot", Path(__file__).resolve().parents[1] / "update_globe_news.py")
robot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(robot)


def failure(code):
    return urllib.error.HTTPError("https://unit.invalid", code, "offline test", {}, io.BytesIO(b"{}"))


class GeminiRetryTests(unittest.TestCase):
    def error(self, code):
        error = failure(code)
        self.addCleanup(error.close)
        return error

    def check(self, codes, models):
        with patch.object(robot, "GEMINI", "offline-placeholder"), patch.object(robot, "gemini_models", return_value=models), patch.object(robot, "get", side_effect=[self.error(c) for c in codes]) as request, patch.object(robot.time, "sleep") as sleep, patch.object(robot, "azure", side_effect=RuntimeError("offline backup")):
            with self.assertRaises(RuntimeError): robot.gemini("offline protocol test")
        return request, sleep

    def test_unavailable_retries_same_model_after_delay(self):
        success = b'{"candidates":[{"content":{"parts":[{"text":"[]"}]}}]}'
        with patch.object(robot, "GEMINI", "offline-placeholder"), patch.object(robot, "gemini_models", return_value=["unit-a"]), patch.object(robot, "get", side_effect=[self.error(503), success]) as request, patch.object(robot.time, "sleep") as sleep, patch.object(robot, "azure", side_effect=RuntimeError("offline backup")):
            self.assertEqual(robot.gemini("offline protocol test"), [])
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args_list[0].args, request.call_args_list[1].args)
        sleep.assert_called_once_with(20)

    def test_persistent_unavailability_is_bounded_per_model(self):
        request, sleep = self.check([503]*4, ["unit-a", "unit-b"])
        self.assertEqual(request.call_count, 4)
        self.assertEqual(sleep.call_count, 2)

    def test_retired_model_is_not_retried(self):
        request, sleep = self.check([404]*2, ["unit-a", "unit-b"])
        self.assertEqual(request.call_count, 2)
        sleep.assert_not_called()

    def test_quota_moves_to_next_model_without_sleep_or_duplicate_request(self):
        success = b'{"candidates":[{"content":{"parts":[{"text":"[]"}]}}]}'
        with patch.object(robot, "GEMINI", "offline-placeholder"), patch.object(robot, "gemini_models", return_value=["unit-a", "unit-b"]), patch.object(robot, "get", side_effect=[self.error(429), success]) as request, patch.object(robot.time, "sleep") as sleep, patch.object(robot, "azure") as backup:
            self.assertEqual(robot.gemini("offline protocol test"), [])
        self.assertEqual(request.call_count, 2)
        self.assertIn("unit-a:", request.call_args_list[0].args[0])
        self.assertIn("unit-b:", request.call_args_list[1].args[0])
        sleep.assert_not_called(); backup.assert_not_called()

    def test_all_quota_limited_models_are_attempted_only_once(self):
        request, sleep = self.check([429, 429], ["unit-a", "unit-b"])
        self.assertEqual(request.call_count, 2); sleep.assert_not_called()

    def test_discovery_prefers_lite_and_filters_non_text_models(self):
        names = ["gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.8-flash-tts", "gemini-3.8-flash-image"]
        models = {"models": [{"name": "models/" + n, "supportedGenerationMethods": ["generateContent"]} for n in names]}
        with patch.object(robot, "get", return_value=json.dumps(models)):
            self.assertEqual(robot.gemini_models(), ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash"])

    def test_discovery_failure_keeps_lite_first(self):
        with patch.object(robot, "get", side_effect=OSError("offline")), patch.object(robot, "err"):
            self.assertEqual(robot.gemini_models(), ["gemini-flash-lite-latest", "gemini-flash-latest"])

    def test_client_errors_stop_without_retry_or_fallback(self):
        for code in (400, 401, 403):
            with self.subTest(code=code):
                request, sleep = self.check([code], ["unit-a", "unit-b"])
                request.assert_called_once()
                sleep.assert_not_called()


if __name__ == "__main__": unittest.main()
