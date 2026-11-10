import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location('source_licensing', ROOT/'tools/coverage/source_licensing.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
SOURCE = {'name':'Unit publisher','source_url':'https://publisher.invalid/rss.xml'}


class LicensingEvidenceTests(unittest.TestCase):
 def test_active_sources_include_regional_and_official_not_new_feeds(self):
  urls={x['source_url'] for x in m.active_sources()}
  self.assertTrue({u for u,_,_ in m.robot.REGION_FEEDS} <= urls)
  self.assertTrue({u for u,_,_ in m.robot.FEEDS} <= urls)
  self.assertEqual(len(urls),len(m.active_sources()))
 def test_inventory_blocks_all_fetches(self):
  for health in [{'robots_allowed':False},{'enabled':False},{'status':'unavailable'}]:
   row,raw=m.collect(SOURCE,lambda u:self.fail('inventory must skip'),health)
   self.assertEqual(row['collection_status'],'skipped_inventory_disallowed_or_unavailable');self.assertFalse(raw)
 def test_robots_disallowed_never_reads_home_feed_or_terms(self):
  urls=[]
  def fetch(u):urls.append(u);return 'User-agent: *\nDisallow: /'
  row,_=m.collect(SOURCE,fetch)
  self.assertEqual(row['collection_status'],'robots_disallowed');self.assertEqual(len(urls),1)
 def test_only_legal_links_on_same_host_and_no_feed_or_article_fetch(self):
  urls=[]
  def fetch(u):
   urls.append(u)
   if u.endswith('/robots.txt'):return 'User-agent: *\nAllow: /'
   if u.endswith('/terms'):return 'Non-commercial use only. All rights reserved.'
   return '<a href="/terms">Terms</a><a href="/article/1">Latest article</a><a href="https://other.invalid/legal">Other terms</a>'
  row,raw=m.collect(SOURCE,fetch)
  self.assertEqual(urls,['https://publisher.invalid/robots.txt','https://publisher.invalid/','https://publisher.invalid/terms'])
  self.assertIsNone(row['commercial_headlines_summaries_links']);self.assertTrue(row['notices'][0]['licensing_text_signals'])
  self.assertEqual(row['licence_review'],'pending_primary_notice_review')
 def test_crawl_delay_defers_instead_of_violating_policy(self):
  row,_=m.collect(SOURCE,lambda u:'User-agent: *\nCrawl-delay: 10\nAllow: /')
  self.assertEqual(row['collection_status'],'crawl_policy_requires_manual_spaced_review')
 def test_html_robots_response_is_not_permission(self):
  row,_=m.collect(SOURCE,lambda u:'<!doctype html><title>Unavailable</title>')
  self.assertEqual(row['collection_status'],'robots_unavailable')
 def test_secret_like_notice_is_not_saved(self):
  secret='unit-only-private-value'
  def fetch(u):
   if u.endswith('robots.txt'):return 'User-agent: *\nAllow: /'
   return secret
  with patch.dict(os.environ,{'GEMINI_API_KEY':secret}):row,raw=m.collect(SOURCE,fetch)
  self.assertNotIn(secret,str(row)+str(raw))
 def test_no_automatic_rights_grant_from_cc_or_public_domain_words(self):
  row,_=m.collect({**SOURCE,'terms_url':'https://publisher.invalid/terms'},lambda u:'User-agent: *\nAllow: /' if u.endswith('robots.txt') else 'Creative Commons public domain commercial use')
  self.assertIsNone(row['commercial_headlines_summaries_links'])
 def test_manual_workflow_has_no_secrets_schedule_or_writes(self):
  text=(ROOT/'.github/workflows/source-licensing.yml').read_text()
  self.assertIn('workflow_dispatch:',text);self.assertIn('contents: read',text)
  for prohibited in ('secrets.','schedule:','git push','wrangler','dispatches'):
   self.assertNotIn(prohibited,text)
