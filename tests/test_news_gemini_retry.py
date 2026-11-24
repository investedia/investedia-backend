"""Offline retry contract; no provider requests or financial content."""
import importlib.util
import io
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
        with patch.object(robot, "GEMINI", "offline-placeholder"), patch.object(robot, "gemini_models", return_value=models), patch.object(robot, "get", side_effect=[self.error(c) for c in codes]) as request, patch.object(robot.time, "sleep") as sleep:
            with self.assertRaises(RuntimeError): robot.gemini("offline protocol test")
        return request, sleep

    def test_unavailable_retries_same_model_after_delay(self):
        success = b'{"candidates":[{"content":{"parts":[{"text":"[]"}]}}]}'
        with patch.object(robot, "GEMINI", "offline-placeholder"), patch.object(robot, "gemini_models", return_value=["unit-a"]), patch.object(robot, "get", side_effect=[self.error(503), success]) as request, patch.object(robot.time, "sleep") as sleep:
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

    def test_client_errors_stop_without_retry_or_fallback(self):
        for code in (400, 401, 403):
            with self.subTest(code=code):
                request, sleep = self.check([code], ["unit-a", "unit-b"])
                request.assert_called_once()
                sleep.assert_not_called()


if __name__ == "__main__": unittest.main()
