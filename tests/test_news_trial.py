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

    def test_library_export_preserves_real_records_and_bounds_pages(self):
        rows = self.seed["files"]["news-live.json"]["stories"][:12]
        original = json.dumps(rows)
        first = trial.library_page(rows, 0)
        self.assertEqual(first["articles"], rows[:10])
        self.assertEqual(first["next"], 10)
        last = trial.library_page(rows, 10)
        self.assertEqual(last["articles"], rows[10:])
        self.assertEqual(last["next"], len(rows))
        self.assertEqual(json.dumps(rows), original)
        for cursor in (-1, len(rows) + 1, "0"):
            with self.assertRaises(ValueError):
                trial.library_page(rows, cursor)
        with self.assertRaises(ValueError):
            trial.library_page([{**rows[0], "id": "../key"}], 0)

    def test_container_library_endpoint_exports_only_bounded_article_pages(self):
        import http.client
        import threading
        server = trial.HTTPServer(("127.0.0.1", 0), trial.Handler)
        server.library = self.seed["files"]["news-live.json"]["stories"][:12]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        try:
            client.request("GET", "/library?cursor=0")
            response = client.getresponse()
            self.assertEqual(response.status, 200)
            page = json.loads(response.read())
            self.assertEqual(page["articles"], server.library[:10])
            for path in ("/library?cursor=-1", "/library?cursor=0&cursor=1", "/library?cursor=0&path=../key"):
                client.request("GET", path)
                response = client.getresponse()
                self.assertEqual(response.status, 400)
                response.read()
        finally:
            client.close(); server.shutdown(); server.server_close(); thread.join(timeout=5)

    def test_saved_library_copy_never_generates_and_preserves_every_article_field(self):
        original = json.dumps(self.seed, sort_keys=True)
        with patch.object(trial.subprocess, "run", side_effect=AssertionError("No process or AI calls permitted")):
            result = trial.run_library(self.seed)
        originals = {}
        for name in ("news-live.json", "news-48h.json", "news-archive.json"):
            for row in self.seed["files"].get(name, {}).get("stories", []):
                originals.setdefault(row["id"], row)
        articles = {name[8:-5]: row for name, row in result["files"].items() if name.startswith("library/")}
        self.assertGreater(len(articles), 0)
        self.assertEqual(articles, {sid: originals[sid] for sid in articles})
        self.assertEqual(result["summary"]["gemini_calls"], 0)
        self.assertEqual(json.dumps(self.seed, sort_keys=True), original)

    def test_live_outputs_use_disposable_state_and_original_priority_broad_limits(self):
        import importlib.util
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); g = root / 'assets/globe'; g.mkdir(parents=True)
            for name in ('tools/push-news-to-worker.py', 'tools/push-connections-to-worker.py'):
                target = root / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes((ROOT / name).read_bytes())
            for name, data in self.seed['files'].items():
                target = g / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(json.dumps(data), encoding='utf-8')
            (g / 'connections.json').write_bytes((ROOT / 'assets/globe/connections.json').read_bytes())
            original = json.loads((g / 'news-live.json').read_text(encoding='utf-8'))
            spec = importlib.util.spec_from_file_location('original_push_fixture', ROOT / 'tools/push-news-to-worker.py')
            helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
            for tier, limit in (('priority', 40), ('broad', 80)):
                out = trial.live_outputs(root, tier)
                self.assertEqual(out['news'], helper.payload(root=root, limit=limit))
                spec2 = importlib.util.spec_from_file_location('original_connections_fixture', root / 'tools/push-connections-to-worker.py')
                connections = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(connections)
                self.assertEqual(out['connections'], connections.payload(g / 'connections.json'))
                self.assertLessEqual(len(out['news']['stories']), limit)
                self.assertEqual(out.get('library', {}).get('days', {}), helper.library_days(root))
            self.assertEqual(json.loads((g / 'news-live.json').read_text(encoding='utf-8')), original)

    def test_container_live_exports_are_fixed_paths_and_do_not_return_arbitrary_state(self):
        import http.client, threading
        server = trial.HTTPServer(('127.0.0.1', 0), trial.Handler)
        body = json.dumps(self.seed['files']['news-live.json']).encode()
        server.live_outputs = {'news': body}
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        client = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
        try:
            for path, status in (('/output?kind=news', 200), ('/output?kind=library', 404),
                                 ('/output?kind=../state', 400), ('/output?kind=news&kind=calendar', 400),
                                 ('/output?kind=news&path=private', 400)):
                client.request('GET', path); response = client.getresponse()
                self.assertEqual(response.status, status)
                saved = response.read()
                if status == 200: self.assertEqual(saved, body)
            client.request('POST', '/run?job=news', body=b'{}')
            response = client.getresponse(); self.assertEqual(response.status, 422); response.read()
            client.request('GET', '/output?kind=news')
            response = client.getresponse(); self.assertEqual(response.status, 404); response.read()
        finally:
            client.close(); server.shutdown(); server.server_close(); thread.join(timeout=5)

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

    def test_compressed_bundle_preserves_all_saved_data(self):
        encoded = trial.encode_bundle(self.seed)
        self.assertTrue(encoded.startswith(b"\x1f\x8b"))
        self.assertEqual(trial.decode_bundle(encoded), self.seed)
        self.assertEqual(trial.decode_bundle(json.dumps(self.seed).encode()), self.seed)

    def test_bundle_larger_than_old_raw_limit_roundtrips(self):
        value = {**self.seed, "transport_test_padding": "x" * (32 * 1024 * 1024)}
        encoded = trial.encode_bundle(value)
        self.assertLess(len(encoded), trial.LIMIT)
        decoded = trial.decode_bundle(encoded)
        self.assertEqual(decoded["files"], self.seed["files"])
        self.assertEqual(len(decoded["transport_test_padding"]), 32 * 1024 * 1024)

    def test_compression_limits_and_corruption_fail_closed(self):
        import gzip
        with patch.object(trial, "EXPANDED_LIMIT", 128):
            with self.assertRaisesRegex(ValueError, "Expanded"):
                trial.decode_bundle(gzip.compress(b" " * 1024))
            with self.assertRaisesRegex(ValueError, "Expanded"):
                trial.encode_bundle(self.seed)
        with patch.object(trial, "LIMIT", 4):
            with self.assertRaisesRegex(ValueError, "transfer"):
                trial.decode_bundle(b"12345")
            with self.assertRaisesRegex(ValueError, "Compressed"):
                trial.encode_bundle(self.seed)
        with self.assertRaises((EOFError, OSError)):
            trial.decode_bundle(b"\x1f\x8bcorrupt")

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
        self.assertNotIn("LIVE_INGEST_TOKEN", kwargs["env"])
        self.assertNotIn("WORKER_URL", kwargs["env"])
        self.assertEqual(kwargs["env"]["PIXABAY_KEY"], "")
        self.assertEqual(kwargs["env"]["GEMINI_API_KEY"], "trial-proxy")
        self.assertFalse(Path(kwargs["cwd"]).exists())

    def test_broad_tier_uses_only_the_fixed_generator_and_broad_status(self):
        with patch.object(trial.subprocess, "run") as call:
            with self.assertRaisesRegex(ValueError, "fresh success"):
                trial.run(self.seed, tier="broad")
        self.assertEqual(call.call_args.kwargs["env"]["NEWS_TIER"], "broad")
        with patch.object(trial.subprocess, "run") as call:
            with self.assertRaisesRegex(ValueError, "Unknown news tier"):
                trial.run(self.seed, tier="../../other")
            call.assert_not_called()

    def test_allowlist_covers_all_declared_producer_feed_hosts(self):
        import ast, re
        from urllib.parse import urlsplit
        tree = ast.parse((ROOT / "update_globe_news.py").read_text(encoding="utf-8"))
        values = {}
        def value(node):
            return values[node.id] if isinstance(node, ast.Name) else ast.literal_eval(node)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        try:
                            values[target.id] = value(node.value)
                        except (ValueError, TypeError, KeyError):
                            pass
            elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and isinstance(node.op, ast.Add):
                try:
                    values[node.target.id] += value(node.value)
                except (ValueError, TypeError, KeyError):
                    pass
        expected = {urlsplit(row[0]).hostname for name in ("FEEDS", "NEWS_FEEDS", "REGION_FEEDS") for row in values[name]}
        policy = (ROOT / "workers/news-trial/policy.mjs").read_text(encoding="utf-8")
        allowed = set(json.loads(re.search(r"SOURCE_HOSTS = new Set\((\[.*?\])\)", policy, re.S).group(1)))
        self.assertFalse(expected - allowed, "Producer feed domains missing from the trial proxy")
        self.assertIn("api.gdeltproject.org", allowed)
        self.assertNotIn("api.investedia.com", allowed)

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
