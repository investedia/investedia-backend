"""Offline only: saved real article replay; synthetic arithmetic/edge fixtures never ingested."""
import copy,hashlib,importlib.util,json,os,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('regional',ROOT/'tools/regional-backfill.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
FIXTURE=ROOT/'tests/fixtures/regional-backfill'
ARTICLE=json.loads((FIXTURE/'original-article.json').read_text())
NOW=m.stamp(ARTICLE['published_at'])+timedelta(days=4)
SOURCE={'name':ARTICLE['source']['name'],'url':'https://fixture.invalid/feed','hint':'','region':'af'}

class RegionalTests(unittest.TestCase):
 def test_original_date_filter_and_retention_metadata(self):
  rows,meta=m.parse_feed((FIXTURE/'saved-feed.xml').read_text(),SOURCE,NOW,7)
  self.assertEqual(rows[0]['title'],ARTICLE['headline']);self.assertEqual(rows[0]['url'],ARTICLE['source']['url']);self.assertEqual(rows[0]['published'],ARTICLE['published_at'])
  self.assertEqual(meta['oldest_original_date_reached'],ARTICLE['published_at']);self.assertFalse(meta['oldest_at_or_before_window_start'])
  self.assertEqual(m.parse_feed((FIXTURE/'saved-feed.xml').read_text(),SOURCE,NOW,1)[0],[])
  for days in [0,31]:
   with self.assertRaises(ValueError):m.parse_feed('<rss/>',SOURCE,NOW,days)
 def test_missing_naive_future_and_atom_updated_are_not_original_dates(self):
  for date in ['', '2026-11-01T10:00:00','2999-01-01T00:00:00Z']:
   xml=f'<rss><item><title>Test-only edge</title><link>https://fixture.invalid/a</link><pubDate>{date}</pubDate></item></rss>'
   rows,meta=m.parse_feed(xml,SOURCE,NOW,7);self.assertEqual(rows,[]);self.assertEqual(sum(meta['rejected'].values()),1)
  rows,_=m.parse_feed('<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Test-only edge</title><link href="https://fixture.invalid/a"/><updated>2026-11-01T00:00:00Z</updated></entry></feed>',SOURCE,NOW,30);self.assertEqual(rows,[])
 def test_id_url_and_seen_hash_dedupe_matches_robot(self):
  rows,_=m.parse_feed((FIXTURE/'saved-feed.xml').read_text(),SOURCE,NOW,7);c=rows[0]
  self.assertEqual(m.dedupe(rows,[ARTICLE],{})[0],[])
  known={'id':'different','source':{'url':c['url']+'#tracking'}};self.assertEqual(m.dedupe(rows,[known],{})[0],[])
  sid='n'+hashlib.md5(c['url'].encode()).hexdigest()[:10]
  self.assertEqual(m.dedupe(rows,[{'id':sid}],{})[0],[])
  self.assertEqual(m.dedupe(rows,[],{m.core.canon(c['url']):{'h':c['chash']}})[0],[])
  self.assertEqual(len(m.dedupe(rows,[],{m.core.canon(c['url']):{'h':'changed'}})[0]),1)
 def test_48h_boundary_is_current_clock_not_newest_article(self):
  rows=[{'id':'boundary','published_at':m.iso(NOW-timedelta(hours=48))},{'id':'old','published_at':m.iso(NOW-timedelta(hours=48,seconds=1))}]
  recent,old=m.split48(rows,NOW);self.assertEqual([x['id'] for x in recent],['boundary']);self.assertEqual([x['id'] for x in old],['old'])
  with self.assertRaises(ValueError):m.split48([{'published_at':m.iso(NOW+timedelta(seconds=1))}],NOW)
 def test_batches_and_capacity_are_bounded_without_silent_truncation(self):
  rows=[{'id':str(i),'published_at':m.iso(NOW-timedelta(days=3))} for i in range(150)]
  self.assertEqual([len(x) for x in m.batches(rows)],[80,70])
  _,accepted,deferred=m.plan(rows,{'history_count':230,'history_capacity':240},NOW,7)
  self.assertEqual(len(accepted),10);self.assertEqual(len(deferred),140)
  _,accepted,deferred=m.plan(rows,{},NOW,7);self.assertFalse(accepted);self.assertEqual(len(deferred),150)
 def test_flagged_robots_and_unavailable_feeds_never_fetched(self):
  sources=[('https://fixture.invalid/a','A','af'),('https://fixture.invalid/b','B','asia'),('https://fixture.invalid/c','C','me')]
  inventory={'feeds':[{'url':sources[0][0],'status':'robots_disallowed'},{'url':sources[1][0],'status':'unavailable_or_unreviewed_redirect'},{'url':sources[2][0],'status':'reachable_needs_licence_review'}]}
  with patch.object(m.robot,'FEEDS',[]),patch.object(m.robot,'NEWS_FEEDS',[]),patch.object(m.robot,'REGION_FEEDS',sources):enabled,skipped=m.feed_sources(inventory)
  self.assertEqual([s['name'] for s in enabled],['C']);self.assertEqual(len(skipped),2)
  def deny(url,**kw):
   self.assertTrue(url.endswith('/robots.txt'));return 'User-agent: *\nDisallow: /\n'
  rows,meta=m.FeedFetcher(deny).one(SOURCE,NOW,7);self.assertEqual(rows,[]);self.assertEqual(meta['status'],'robots_disallowed')
 def test_fixed_budget_counts_actual_http_attempts_and_bounds_tokens(self):
  sent=[]
  def transport(url,**kw):sent.append(kw);return '{}'
  budget=m.ModelBudget(transport);body=json.dumps({'contents':[{'parts':[{'text':'test-only'}]}],'generationConfig':{}}).encode()
  for _ in range(m.MAX_CALLS):budget.get('https://generativelanguage.googleapis.com/v1beta/models/test:generateContent',data=body,timeout=240)
  with self.assertRaises(m.BudgetExceeded):budget.get('https://generativelanguage.googleapis.com/v1beta/models/test:generateContent',data=body)
  self.assertEqual(len(sent),m.MAX_CALLS);self.assertEqual(sent[0]['timeout'],90);self.assertEqual(json.loads(sent[0]['data'])['generationConfig']['maxOutputTokens'],8192)
 def test_cap_cannot_be_exceeded_by_many_candidates(self):
  rows,_=m.parse_feed((FIXTURE/'saved-feed.xml').read_text(),SOURCE,NOW,7)
  candidates=[{**rows[0],'url':f'https://fixture.invalid/{i}','source':f'test-only-feed-{i%20}'} for i in range(501)]
  def pick(part,*args,**kw):
   m.robot.status['gemini_ok']=True
   return [{'id':'n'+hashlib.md5(c['url'].encode()).hexdigest()[:10],'headline':c['title'],'published_at':c['published'],'source':{'url':c['url']}} for c in part]
  with patch.object(m.robot,'pick_stories',side_effect=pick):new,processed=m.generate_new(candidates,NOW,{}, {},{})
  self.assertEqual(len(new),150);self.assertEqual(len(processed),150)
 def test_existing_robot_keeps_original_headline_single_source_and_no_pages(self):
  rows,_=m.parse_feed((FIXTURE/'saved-feed.xml').read_text(),SOURCE,NOW,7)
  box,by_iso,sym=m.robot.load_ref();loc=ARTICLE['location'];code=next(c for c,n in by_iso.items() if n==loc['country'])
  response={'members':[0],'headline':'Must never replace original','summary':ARTICLE.get('summary',''),'category':ARTICLE['category'],'importance':1,'country':code,'lat':loc['lat'],'lon':loc['lon'],'place':loc['place'],'impacts':[]}
  with patch.object(m.robot,'gemini',return_value=[response]),patch.object(m.robot,'describe',side_effect=AssertionError('article page fetch')),patch.object(m.robot,'photo',side_effect=AssertionError('photo fetch')):
   got=m.robot.pick_stories(rows,box,by_iso,sym,set(by_iso),1,preserve_source=True,feed_only=True,backfill=True)
  self.assertEqual(got[0]['headline'],ARTICLE['headline']);self.assertEqual(got[0]['published_at'],ARTICLE['published_at']);self.assertEqual(len(got[0]['sources']),1)
  response['members']=[0,0]
  with patch.object(m.robot,'gemini',return_value=[response]):self.assertEqual(m.robot.pick_stories(rows,box,by_iso,sym,set(by_iso),1,preserve_source=True,feed_only=True),[])
 def test_connection_repairs_keep_every_other_field_identical_and_are_idempotent(self):
  original=copy.deepcopy(ARTICLE);original['impacts']=[]
  def malicious(copies,*args,**kw):
   for row in copies:
    kw['completed_ids'].append(row['id']);row.update(headline='wrong',summary='wrong',published_at='wrong',location={})
    row['impacts']=[{'name':'test-only explicit impact'}];row['why_moved']='wrong'
  with patch.object(m.robot,'backfill_impacts',side_effect=malicious) as f:changed,checked=m.repair_existing([original],{}, {})
  self.assertEqual(json.dumps(m.protected(original)),json.dumps(m.protected(changed[0])));self.assertEqual(checked,[original['id']])
  with patch.object(m.robot,'backfill_impacts') as f:self.assertEqual(m.repair_existing(changed,{},{}),([],[]));f.assert_not_called()
  key=m.core.content_hash({'title':original.get('headline'),'desc':original.get('summary')})
  with patch.object(m.robot,'backfill_impacts') as f:self.assertEqual(m.repair_existing([original],{},{original['id']:key}),([],[]));f.assert_not_called()
 def test_no_link_without_named_evidence_or_real_price(self):
  reg=m.read(ROOT/'data/registry.json')['assets'];asset=next(a for a in reg.values() if a.get('class')=='equity' and a.get('px'))
  impact={'kind':'company','name':asset['name'],'country':asset['country'],'confidence':'high','why':'test-only','asset':{'id':asset['id']}}
  prices={asset['px']:{'p':100}} # mathematical unit fixture, not exported market data
  row={'id':'unit','headline':'Unrelated text','summary':asset['name'],'_feed_description':'No named company','impacts':[impact]}
  out,reasons=m.evidence([row],NOW,reg,prices,{});self.assertEqual(out[0]['impacts'],[]);self.assertEqual(reasons['unit'][0]['reason'],'no_named_asset_in_reporting')
  row['headline']=asset['name'];out,_=m.evidence([row],NOW,reg,{},{});self.assertEqual(out[0]['impacts'],[])
  out,_=m.evidence([row],NOW,reg,prices,{});self.assertEqual(len(out[0]['impacts']),1);self.assertFalse(out[0]['impacts'][0]['scorable'])
 def test_secret_values_never_written_to_artifacts(self):
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'GEMINI_API_KEY':'test-only-never-a-real-key','NEWS_INGEST_TOKEN':'test-only-private-token'}):
   p=Path(d)/'report.json'
   with self.assertRaisesRegex(ValueError,'secret_like_content'):m.write(p,{'error':'test-only-private-token'})
   self.assertFalse(p.exists());m.write(p,{'gemini_calls':0,'notice':'Not investment advice.'});self.assertNotIn('test-only-private-token',p.read_text())
 def test_events_archive_uses_original_day_and_preserves_article_identity(self):
  with tempfile.TemporaryDirectory() as d:
   base=Path(d)/'events';m.archive([copy.deepcopy(ARTICLE)],base,NOW)
   record=json.loads((base/(ARTICLE['published_at'][:10]+'.json')).read_text())['events'][0]
   self.assertEqual(record['id'],ARTICLE['id']);self.assertEqual(record['at'],ARTICLE['published_at']);self.assertEqual(record['title'],ARTICLE['headline']);self.assertEqual(record['url'],ARTICLE['source']['url'])


class RecoveryIntegrationTests(unittest.TestCase):
 def test_upload_routing_batches_and_freshness_use_existing_timestamp(self):
  now=NOW;current={'meta':{'fetched_at':ARTICLE['published_at']},'data':{'stories':[ARTICLE]}}
  rows=[{**ARTICLE,'id':'unit-'+str(i),'published_at':m.iso(now-timedelta(hours=1))} for i in range(85)]
  rows += [{**ARTICLE,'id':'old-'+str(i),'published_at':m.iso(now-timedelta(days=4))} for i in range(2)]
  sent=[];ack=[]
  def send(url,token,body):sent.append(body);return {'ok':True}
  cap={'regional_backfill_version':1,'history_connections_version':1,'history_count':0,'history_capacity':240,'history_ids':[]}
  with patch.object(m,'request',return_value=json.dumps(current)),patch.object(m.uploader,'push',side_effect=send):
   self.assertEqual(m.publish(rows,'https://fixture.invalid',now,7,False,cap,ack.extend),[])
  self.assertEqual(len(ack),87);self.assertTrue(all(len(b['stories'])<=80 for b in sent))
  for body in sent:
   if body.get('mode')=='gap-history-v1':self.assertTrue(all(m.stamp(s['published_at'])<now-timedelta(hours=48) for s in body['stories']))
   else:self.assertEqual(body['generated_at'],ARTICLE['published_at'])
 def test_named_source_set_selects_only_those_feeds(self):
  sources=[('https://fixture.invalid/a','A','af'),('https://fixture.invalid/new','Central Bank of New','latam')]
  with patch.object(m.robot,'FEEDS',[]),patch.object(m.robot,'REGION_FEEDS',sources),patch.object(m.robot,'OFFICIAL_REGION_FEEDS_2026_11_11',[sources[1]]):
   enabled,skipped=m.feed_sources({},m.SOURCE_SETS['official-2026-11-11']())
  self.assertEqual([s['name'] for s in enabled],['Central Bank of New']);self.assertEqual(skipped,[])
  with self.assertRaises(ValueError):m.feed_sources({})
  self.assertTrue(all(any(u==r[0] for r in m.robot.REGION_FEEDS) for u in m.SOURCE_SETS['official-2026-11-11']()))
  self.assertIn('official-2026-11-11',(ROOT/'.github/workflows/regional-backfill.yml').read_text())
  wf=(ROOT/'.github/workflows/regional-backfill.yml').read_text();stage=wf[wf.index('Stage or ingest'):wf.index('Save acknowledged')]
  self.assertIn('BACKFILL_SOURCES_INPUT: ${{ inputs.sources }}',stage);self.assertIn('--sources "$BACKFILL_SOURCES_INPUT"',stage)
 def test_offline_dry_run_writes_only_review_artifacts(self):
  import shutil
  original=copy.deepcopy(ARTICLE);original['impacts']=[]
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);assets=root/'assets/globe';assets.mkdir(parents=True);(root/'data').mkdir()
   for name in ['registry.json']:shutil.copyfile(ROOT/'data'/name,root/'data'/name)
   for name in ['iso.json','markets.json','news-prices.json']:shutil.copyfile(ROOT/'assets/globe'/name,assets/name)
   for name in ['news-live.json','news-48h.json','news-archive.json']:(assets/name).write_text(json.dumps({'updated_at':ARTICLE['published_at'],'stories':[original]}))
   initial={p.name:p.read_bytes() for p in assets.iterdir() if p.is_file()}
   live={'meta':{'fetched_at':ARTICLE['published_at']},'data':{'stories':[original]}}
   def request(url,**kw):
    if '/v1/news?' in url:return json.dumps(live)
    if url.endswith('/capabilities'):return json.dumps({'regional_backfill_version':1,'history_connections_version':1,'history_count':0,'history_capacity':240,'history_ids':[]})
    raise AssertionError('unexpected HTTP request: '+url)
   with patch.object(m,'ROOT',root),patch.object(m,'request',side_effect=request),patch.object(m.robot,'gemini',return_value=[{'id':original['id'],'impacts':[]}]),patch.object(m.uploader,'push') as upload:
    with patch.object(m,'feed_sources',return_value=([],[])):
     result=m.run(7,True,False,{},root/'review','https://fixture.invalid',gemini_model='gemini-fixture')
    self.assertEqual(result['repair_sources']['news-48h.json']['articles'],1)
    self.assertEqual(result['repair_missing_impacts_scanned'],1)
    self.assertEqual(result['selected_model'],'gemini-fixture')
    self.assertIn('processed_by_region',result);self.assertIn('deferred_by_region',result)
   upload.assert_not_called();self.assertEqual(result['state'],'dry_run_complete');self.assertEqual(result['articles_checked'],1)
   self.assertTrue((root/'review/report.json').exists());self.assertTrue((root/'review/threads.json').exists())
   self.assertEqual(initial,{p.name:p.read_bytes() for p in assets.iterdir() if p.is_file()})
 def test_manual_workflow_has_shared_state_lock_and_keeps_robot_schedules(self):
  manual=(ROOT/'.github/workflows/regional-backfill.yml').read_text()
  self.assertIn('workflow_dispatch:',manual);self.assertNotIn('schedule:',manual);self.assertIn('group: news-production',manual)
  self.assertIn('dry_run:',manual);self.assertIn('default: true',manual);self.assertIn("inputs.confirm == 'BACKFILL'",manual)
  self.assertIn("!inputs.dry_run",manual)
  for name,cron in [('priority-news.yml',"17 * * * *"),('broad-news.yml',"47 */2 * * *")]:
   text=(ROOT/'.github/workflows'/name).read_text();self.assertIn(cron,text);self.assertIn('group: news-production',text)
   for path in ['news-seen.json','news-live.json','news-48h.json','news-archive.json','news-status.json','events','threads.json','news-gap-history-cache.json','regional-backfill-state.json']:
    self.assertIn('backend/assets/globe/'+path,text);self.assertIn('backend/assets/globe/'+path,manual)



class CachedRepresentationTests(unittest.TestCase):
 def test_cached_fields_and_existing_good_impacts_are_never_replaced(self):
  old=copy.deepcopy(ARTICLE);old['impacts']=[]
  proposed={**old,'headline':'Must not replace cache text','summary':'Must not replace summary','impacts':[{'name':'No such named asset'}]}
  patched=m.cached_patch(old,proposed)
  self.assertEqual(json.dumps(m.protected(patched)),json.dumps(m.protected(old)));self.assertEqual(patched['impacts'],[])
  old['impacts']=[{'name':'Existing reviewed impact'}]
  self.assertEqual(m.cached_patch(old,proposed)['impacts'],old['impacts'])
 def test_event_asset_repair_preserves_all_other_archived_metadata(self):
  with tempfile.TemporaryDirectory() as d:
   base=Path(d)/'events';m.archive([copy.deepcopy(ARTICLE)],base,NOW)
   path=base/(ARTICLE['published_at'][:10]+'.json');before=json.loads(path.read_text())['events'][0]
   changed=copy.deepcopy(ARTICLE);changed['headline']='Must not replace event title';changed['impacts']=[{'name':'Test-only asset','kind':'asset'}]
   m.archive([changed],base,NOW);after=json.loads(path.read_text())['events'][0]
   self.assertEqual({k:v for k,v in before.items() if k not in {'assets','cos'}},{k:v for k,v in after.items() if k not in {'assets','cos'}})



class LegacyRetryBudgetTests(unittest.TestCase):
 def test_legacy_model_fallbacks_cannot_exceed_actual_request_budget(self):
  calls=[]
  def unavailable(url,**kwargs):calls.append(url);raise OSError('offline unit failure')
  budget=m.ModelBudget(unavailable)
  with patch.object(m.robot,'get',side_effect=budget.get),patch.object(m.robot,'GEMINI','unit-only-not-a-real-key'),patch.object(m.robot,'gemini_models',return_value=['unit-model-'+str(i) for i in range(6)]),patch.object(m.robot.time,'sleep'):
   with self.assertRaises(m.ModelUnavailable):m.robot.gemini('offline unit prompt')
  self.assertEqual(len(calls),1);self.assertEqual(budget.calls,1)

if __name__=='__main__':unittest.main()

class RegionalFixTests(unittest.TestCase):
 def test_pins_live_hourly_or_explicit_model_without_guessing_names(self):
  self.assertEqual(m.selected_model(None,{'meta':{'model':'gemini-live'}},{'gemini_model':'gemini-old','gemini_ok':True}),'gemini-live')
  self.assertEqual(m.selected_model('gemini-owner',{'meta':{'model':'gemini-live'}},{}),'gemini-owner')
  with self.assertRaises(ValueError):m.selected_model(None,{}, {})
  with self.assertRaises(ValueError):m.selected_model('https://not-a-model',{}, {})
 def test_discovery_is_at_most_one_actual_request(self):
  calls=[];budget=m.ModelBudget(lambda *args,**kw:calls.append(args) or '{}')
  budget.get('https://generativelanguage.googleapis.com/v1beta/models')
  with self.assertRaises(m.BudgetExceeded):budget.get('https://generativelanguage.googleapis.com/v1beta/models')
  self.assertEqual(len(calls),1);self.assertEqual(budget.discovery,1)
 def test_call_budget_inputs_are_bounded_and_context_is_logged(self):
  for value in [0,41]:
   with self.assertRaises(ValueError):m.ModelBudget(lambda:None,limit=value)
  budget=m.ModelBudget(lambda *args,**kw:'{}',limit=1)
  budget.context={'purpose':'new_articles','input_candidates':25}
  body=json.dumps({'contents':[{'parts':[{'text':'offline unit prompt'}]}]}).encode()
  budget.get('https://generativelanguage.googleapis.com/v1beta/models/gemini-fixture:generateContent',data=body)
  with self.assertRaises(m.BudgetExceeded):budget.get('https://generativelanguage.googleapis.com/v1beta/models/gemini-fixture:generateContent',data=body)
  self.assertEqual(budget.call_log[0]['input_candidates'],25);self.assertEqual(budget.calls,1)
 def test_regions_get_balanced_reserves_before_global_publishers(self):
  rows,_=m.parse_feed((FIXTURE/'saved-feed.xml').read_text(),SOURCE,NOW,7)
  candidates=[{**rows[0],'url':f'https://fixture.invalid/{region}/{i}','feed_region':region,'region':region} for region in m.REGIONAL_ORDER for i in range(100)]
  candidates += [{**rows[0],'url':f'https://fixture.invalid/global/{i}','feed_region':None,'region':'global'} for i in range(1000)]
  selected=m.regional_candidates(candidates,NOW)
  counts=m.Counter(c['feed_region'] for c in selected)
  self.assertEqual(len(selected),150);self.assertEqual(set(counts.values()),{25});self.assertNotIn(None,counts)
 def test_sparse_regional_feeds_do_not_give_their_reserve_to_global(self):
  rows,_=m.parse_feed((FIXTURE/'saved-feed.xml').read_text(),SOURCE,NOW,7)
  candidates=[{**rows[0],'url':f'https://fixture.invalid/{i}','feed_region':'af' if i<8 else None} for i in range(500)]
  selected=m.regional_candidates(candidates,NOW)
  self.assertEqual(sum(c['feed_region']=='af' for c in selected),8);self.assertLessEqual(len(selected),10)
 def test_deadline_stops_model_requests_before_transport(self):
  budget=m.ModelBudget(lambda *args,**kw:self.fail('deadline must stop before request'),deadline=0)
  with self.assertRaises(m.BudgetExceeded):budget.get('https://generativelanguage.googleapis.com/v1beta/models')
  self.assertEqual(budget.discovery,0)


class ClaudeWriterTests(unittest.TestCase):
    """Offline: a fake client; no network, no key."""
    def test_claude_writer_counts_budget_cost_and_caps(self):
        from types import SimpleNamespace as NS
        class Fake:
            def __init__(s): s.messages=s; s.calls=0
            def create(s, **kw):
                s.calls+=1; assert kw['model']=='claude-haiku-5-5'
                return NS(stop_reason='end_turn', usage=NS(input_tokens=1000, output_tokens=200), content=[NS(type='text', text='[{"id":"a"}]')])
        b=m.ModelBudget(lambda *a,**k:'',2); w=m.ClaudeWriter(Fake(),'claude-haiku-5-5',b,1.0)
        self.assertEqual(w('prompt'),[{'id':'a'}]); self.assertEqual(b.calls,1); self.assertAlmostEqual(w.spent,0.0002)
        w('p'); 
        with self.assertRaises(m.BudgetExceeded): w('p')
        tight=m.ClaudeWriter(Fake(),'claude-haiku-5-5',m.ModelBudget(lambda *a,**k:'',5),0.001)
        with self.assertRaises(m.BudgetExceeded): tight('p')
        with self.assertRaises(ValueError): m.ClaudeWriter(Fake(),'gpt',b,1)


class EnglishHeadlineTests(unittest.TestCase):
    def test_only_foreign_headlines_are_replaced_and_marked(self):
        stories=[{'headline':'Nvidia shares fall'},{'headline':'Paradoja exportadora en Argentina'}]
        n=m.english_headlines(lambda p:[{'i':1,'english':'Export paradox in Argentina'},{'i':9,'english':'out of range item'}],stories)
        self.assertEqual(n,1);self.assertEqual(stories[0],{'headline':'Nvidia shares fall'})
        self.assertEqual(stories[1],{'headline':'Export paradox in Argentina','original_headline':'Paradoja exportadora en Argentina','headline_translated':True})
