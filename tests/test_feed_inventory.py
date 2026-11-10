import importlib.util,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('feeds',Path(__file__).resolve().parents[1]/'tools/coverage/feed_inventory.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class FeedsTests(unittest.TestCase):
 def test_feed_success_never_implies_licensed(self):
  self.assertFalse(m.eligible({'status':'reachable_needs_licence_review','dated_items':10}))
  self.assertFalse(m.eligible({'status':'not_probed','licence_verified':True,'dated_items':10}))
 def test_dated_original_entries_only(self):
  rows,missing=m.dates('<rss><channel><item><link>https://example.test/a</link><pubDate>Mon, 09 Nov 2026 12:00:00 +0000</pubDate></item><item><link>https://example.test/b</link></item></channel></rss>')
  self.assertEqual(len(rows),1);self.assertEqual(missing,1)
 def test_existing_sources_are_unique_and_no_new_source_enabled(self):
  rows=m.configured();self.assertGreater(len(rows),60);self.assertEqual(len(rows),len({x['url'] for x in rows}));self.assertFalse(any(x['newly_enabled'] for x in rows))
if __name__=='__main__':unittest.main()
