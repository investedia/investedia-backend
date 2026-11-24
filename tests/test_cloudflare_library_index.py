"""Offline index transaction checks using real saved articles; no provider or storage calls."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cloudflare_library_index", ROOT / "workers/news-trial/index_job.py")
index = importlib.util.module_from_spec(spec); spec.loader.exec_module(index)


class LibraryIndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.baseline = Path(self.tmp.name)
        self.articles = json.loads((ROOT / "assets/globe/news-live.json").read_text(encoding="utf-8"))["stories"][:28]
        self.rows = {a["id"]: {"id": a["id"], "h": a["headline"], "c": a.get("category") or "news", "t": a["published_at"],
                                "s": a["source"].get("name"), "n": a["location"].get("country"), "g": a["location"].get("region"), "k": len(a.get("sources") or []) or 1} for a in self.articles}
        self.static = list(self.rows.values())[:25]
        raw = index.dump(self.static); (self.baseline / "all.json").write_bytes(raw)
        (self.baseline / "baseline.json").write_text(json.dumps({"catalog_sha256": hashlib.sha256(raw).hexdigest(), "shards": []}))
        self.previous = None; self.requests = []
        self.project = Mock(side_effect=lambda a: self.rows[a["id"]])
        module = SimpleNamespace(row=self.project)
        self.loader = patch.object(index.importlib.util, "spec_from_file_location", return_value=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda _: None)))
        self.modules = patch.object(index.importlib.util, "module_from_spec", return_value=module)
        self.loader.start(); self.modules.start(); self.addCleanup(self.loader.stop); self.addCleanup(self.modules.stop)

    def fetch(self, name, limit):
        self.requests.append(name)
        if name == "index-state.json.gz": return self.previous
        sid = Path(name).stem
        return index.dump(next(a for a in self.articles if a["id"] == sid))

    def build(self):
        return index.build_index({"ids": [a["id"] for a in self.articles]}, self.baseline, self.fetch)

    def test_original_rows_win_and_every_page_range_reconstructs_exact_utf8_rows(self):
        before = index.dump(self.articles)
        files, summary = self.build(); rows = json.loads(files["all.json"])
        self.assertEqual(summary["articles"], len(self.articles)); self.assertEqual(summary["gemini_calls"], 0)
        by = {r["id"]: r for r in rows}
        for row in self.static: self.assertEqual(by[row["id"]], row)
        self.assertEqual(self.project.call_count, 3)
        for a in self.articles[25:]: self.project.assert_any_call(a)
        manifest = json.loads(files["manifest.json"])
        reconstructed = []
        for offset, length in manifest["pages"]:
            reconstructed += json.loads(b"[" + files["all.json"][offset:offset + length] + b"]")
        self.assertEqual(reconstructed, rows)
        self.assertEqual(index.dump(self.articles), before)
        self.assertEqual(json.loads(files["meta.json"])["pages"], 2)

    def test_repeat_reuses_only_canonical_rows_and_has_identical_output(self):
        first, _ = self.build(); self.previous = first["state.json.gz"]; self.requests.clear(); self.project.reset_mock()
        second, _ = self.build()
        self.assertEqual(first, second); self.assertEqual(self.requests, ["index-state.json.gz"]); self.project.assert_not_called()

    def test_bad_ids_baseline_and_published_articles_abort_without_partial_output(self):
        for seed in ({"ids": ["../private"]}, {"ids": [self.articles[0]["id"]] * 2}, {"ids": "not a list"}):
            with self.assertRaises(ValueError): index.build_index(seed, self.baseline, self.fetch)
        (self.baseline / "all.json").write_bytes(b"[]")
        with self.assertRaises(ValueError): self.build()
        self.assertEqual(self.requests, [])

    def test_canonical_id_mismatch_cannot_create_a_listing(self):
        def fetch(name, limit):
            if name == "index-state.json.gz": return None
            return index.dump(self.articles[0])
        with self.assertRaises(ValueError): index.build_index({"ids": [a["id"] for a in self.articles]}, self.baseline, fetch)

    def test_gzip_state_is_bounded_and_corrupt_state_is_not_silently_discarded(self):
        self.previous = gzip.compress(b"invalid")
        with self.assertRaises(ValueError): self.build()

    def test_empty_additions_still_preserve_the_whole_archive(self):
        files, summary = index.build_index({"ids": []}, self.baseline, self.fetch)
        self.assertEqual(summary["articles"], len(self.static)); self.assertEqual(summary["added"], 0)
        self.assertEqual({r["id"] for r in json.loads(files["all.json"])}, {r["id"] for r in self.static})


if __name__ == "__main__": unittest.main()
