"""Offline only: synthetic GDELT GKG/publisher fixtures (.invalid domains, "Test-only" headlines); nothing is ever ingested."""
import importlib.util, io, json, tempfile, unittest, urllib.error, zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gdelt_backfill', ROOT/'tools/gdelt-backfill.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
FIXTURE = ROOT/'tests/fixtures/gdelt-backfill'
GKG = (FIXTURE/'gkg-sample.csv').read_text()
PAGE = (FIXTURE/'publisher-page.html').read_text()
NOW = datetime(2026, 11, 11, 12, tzinfo=timezone.utc)
START, END = m.window('2026-08-01', '2026-10-15')
UTC = timezone.utc
FILE_TIME = datetime(2026, 9, 2, 12, tzinfo=UTC)


def gkg_zip(text=GKG, name='20260902120000.gkg.csv'):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z: z.writestr(name, text)
    return buf.getvalue()


class Clock:
    def __init__(self): self.t = 1000.0; self.sleeps = []
    def __call__(self): return self.t
    def sleep(self, s): self.sleeps.append(round(s, 3)); self.t += s


def http_error(url, code, location=None):
    headers = {'Location': location} if location else {}
    return urllib.error.HTTPError(url, code, 'test', headers, io.BytesIO(b''))


class WindowsAndRegions(unittest.TestCase):
    def test_window_is_inclusive_and_bounded_to_aug_oct(self):
        self.assertEqual((START, END), (datetime(2026, 8, 1, tzinfo=UTC), datetime(2026, 10, 16, tzinfo=UTC)))
        for a, b in [('2026-07-31', '2026-08-02'), ('2026-10-01', '2026-10-16'), ('2026-09-10', '2026-09-01'), ('2026-9-1', '2026-09-02')]:
            with self.assertRaises(ValueError): m.window(a, b)

    def test_file_plan_covers_every_day_first_then_adds_hours(self):
        days = (END - START).days
        self.assertEqual(days, 76)
        plan = m.gkg_plan(START, END, 160)
        self.assertEqual(len(plan), 160); self.assertEqual(len(set(plan)), 160)
        self.assertEqual(plan[0], datetime(2026, 8, 1, 12, tzinfo=UTC)); self.assertEqual(plan[days - 1], datetime(2026, 10, 15, 12, tzinfo=UTC))
        self.assertEqual(plan[days], datetime(2026, 8, 1, 0, tzinfo=UTC))  # second round: midnight files
        self.assertEqual({p.date() for p in plan[:days]}, {(START + timedelta(days=i)).date() for i in range(days)})
        self.assertTrue(all(START <= p < END for p in m.gkg_plan(START, END, 400)))
        self.assertEqual(m.gkg_url(plan[0]), 'https://data.gdeltproject.org/gdeltv2/20260801120000.gkg.csv.zip')
        for bad in (0, 401):
            with self.assertRaises(ValueError): m.gkg_plan(START, END, bad)

    def test_region_mapping(self):
        self.assertEqual(m.regions_from('all'), list(m.REGIONS)); self.assertEqual(m.regions_from(''), list(m.REGIONS))
        self.assertEqual(m.regions_from('oceania, caribbean'), ['oceania', 'caribbean'])
        with self.assertRaises(ValueError): m.regions_from('atlantis')
        for key in ['middle_east', 'oceania', 'asia', 'central_asia', 'east_africa', 'eastern_europe', 'southern_europe', 'caribbean']:
            self.assertIn(key, m.REGIONS)
        self.assertEqual(m.REGIONS['east_africa']['balance'], 'af'); self.assertEqual(m.REGIONS['caribbean']['balance'], 'latam')
        self.assertEqual(m.REGIONS['central_asia']['balance'], 'asia'); self.assertEqual(m.REGIONS['oceania']['balance'], 'oc')
        self.assertEqual(m.FIPS_REGION['KE'], 'east_africa'); self.assertEqual(m.FIPS_REGION['AS'], 'oceania')
        self.assertEqual(m.FIPS_REGION['JM'], 'caribbean'); self.assertNotIn('US', m.FIPS_REGION)
        codes = [c for r in m.REGIONS.values() for c in r['fips']]; self.assertEqual(len(codes), len(set(codes)))

    def test_model_choice_skips_non_gemini_placeholders(self):
        live = {'meta': {'model': 'github-ingest'}}
        self.assertEqual(m.selected_model(None, live, {'gemini_model': 'gemini-3.5-flash-lite', 'gemini_ok': True}), 'gemini-3.5-flash-lite')
        self.assertEqual(m.selected_model(None, {'meta': {'model': 'gemini-a'}}, {}), 'gemini-a')
        self.assertEqual(m.selected_model('gemini-b', live, {}), 'gemini-b')
        with self.assertRaises(ValueError): m.selected_model('github-ingest', live, {})
        with self.assertRaises(ValueError): m.selected_model(None, live, {'gemini_model': 'gemini-x', 'gemini_ok': False})


class GkgClientTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory(); self.cache = Path(self.dir.name); self.clock = Clock(); self.sent = []
    def tearDown(self): self.dir.cleanup()
    def client(self, responses, limit=10):
        def get(url, timeout=None):
            self.sent.append((url, self.clock.t)); r = responses.pop(0)
            if isinstance(r, Exception): raise r
            return r
        return m.GkgClient(get, self.cache, limit, clock=self.clock, sleep=self.clock.sleep)

    def test_downloads_are_spaced_and_parsed_results_cached_for_resume(self):
        c = self.client([gkg_zip()] * 3)
        for h in range(3): self.assertEqual(c.fetch(FILE_TIME + timedelta(hours=h))[1], 'fetched')
        gaps = [b - a for (_, a), (_, b) in zip(self.sent, self.sent[1:])]
        self.assertTrue(all(g >= 2.0 for g in gaps), gaps)
        self.assertEqual(c.downloads, 3); self.assertEqual(len(list(self.cache.glob('*.json'))), 3)
        self.assertTrue(self.sent[0][0].startswith('https://data.gdeltproject.org/gdeltv2/20260902120000'))
        again = self.client([])
        rows, status = again.fetch(FILE_TIME)
        self.assertEqual(status, 'cache'); self.assertEqual(len(rows), 4); self.assertEqual(again.downloads, 0)

    def test_missing_files_errors_and_budget(self):
        c = self.client([http_error('u', 404), b'not a zip', gkg_zip()], limit=3)
        self.assertEqual(c.fetch(FILE_TIME)[1], 'missing'); self.assertEqual(c.fetch(FILE_TIME + timedelta(hours=1))[1], 'error')
        self.assertEqual(c.fetch(FILE_TIME + timedelta(hours=2))[1], 'fetched')
        self.assertEqual(c.fetch(FILE_TIME + timedelta(hours=3))[1], 'gdelt_file_budget_reached')
        self.assertEqual(c.fetch(FILE_TIME)[1], 'cache')  # the missing file is remembered, not asked again
        stop = self.client([http_error('u', 503)] * 20, limit=50)
        outcomes = [stop.fetch(FILE_TIME + timedelta(days=1, hours=h))[1] for h in range(m.ERROR_STOP + 2)]
        self.assertEqual(outcomes[-1], 'gdelt_download_errors_stop'); self.assertEqual(len(self.sent), 3 + m.ERROR_STOP)
        with self.assertRaises(ValueError): m.GkgClient(lambda *a, **k: b'', self.cache, 401)

    def test_only_gdelt_file_host_is_downloaded(self):
        for url in ('http://data.gdeltproject.org/gdeltv2/x.zip', 'https://example.invalid/x.zip'):
            with self.assertRaises(ValueError): m.fetch_bytes(url)


class DiscoveryTests(unittest.TestCase):
    def rows(self): return m.parse_gkg(GKG, FILE_TIME)

    def test_parse_keeps_business_articles_in_backfill_regions_and_never_uses_file_time_as_publication(self):
        rows, rejected = self.rows()
        self.assertEqual([r['url'].rsplit('/', 1)[1] for r in rows], ['test-only-shilling', 'test-only-tea', 'test-only-shilling#amp', 'test-only-rba'])
        self.assertEqual(rejected, {'not_public_https_url': 1, 'not_business_theme': 1, 'outside_backfill_regions': 1,
                                    'missing_title': 1, 'not_web_article': 1})
        self.assertEqual(rows[0]['gdelt_seen'], '2026-09-02T12:00:00Z'); self.assertNotIn('published', rows[0])
        self.assertEqual(rows[0]['gdelt_country'], 'KE'); self.assertEqual(rows[0]['gdelt_region'], 'east_africa')
        self.assertEqual(rows[0]['feed_region'], 'af'); self.assertEqual(rows[3]['gdelt_region'], 'oceania')
        self.assertEqual(m.main_country('1#A#AS#x#0#0#1;1#B#KE#x#0#0#1;1#B#KE#x#0#0#1'), 'KE')

    def test_dedupe_against_ids_urls_headlines_events_and_earlier_runs(self):
        rows, _ = self.rows()
        fresh, dup = m.dedupe(rows, m.known_keys([], [], [], {}))
        self.assertEqual(len(fresh), 3); self.assertEqual(dup, {'duplicate_id_or_source_url': 1})  # '#amp' copy
        first = rows[0]
        cases = [m.known_keys([{'id': m.sid(first['url'])}], [], [], {}),
                 m.known_keys([{'id': 'x', 'source': {'url': first['url'].replace('https://', 'https://www.') + '/'}}], [], [], {}),
                 m.known_keys([], [{'id': 'e', 'url': first['url'], 'title': 'other'}], [], {}),
                 m.known_keys([], [], [m.sid(first['url'])], {}),
                 m.known_keys([], [], [], {m.core.canon(first['url']): '2026-11-01T00:00:00Z'}),
                 m.known_keys([{'id': 'y', 'headline': first['title'].upper()}], [], [], {})]
        for known in cases:
            fresh, _ = m.dedupe(rows, known)
            self.assertNotIn(first['title'], [r['title'] for r in fresh])
        noisy = [{**first, 'url': 'https://news.fixture.invalid/n', 'title': 'Test-only: three stocks to buy now'}]
        self.assertEqual(m.dedupe(noisy, m.known_keys([], [], [], {}))[1], {'existing_robot_noise_rule': 1})

    def test_order_alternates_regions_thin_first_and_spreads_days(self):
        def row(region, d, i): return {'gdelt_region': region, 'gdelt_seen': f'2026-09-0{d}T00:00:00Z', 'url': f'{region}{d}{i}'}
        rows = [row('asia', 1, i) for i in range(3)] + [row('asia', 2, 0), row('oceania', 3, 0)]
        got = [r['url'] for r in m.order(rows, ['oceania', 'asia'])]
        self.assertEqual(got, ['oceania30', 'asia10', 'asia20', 'asia11', 'asia12'])


class PublisherPageTests(unittest.TestCase):
    def row(self, seen='2026-09-02T08:15:00Z'):
        return {'title': 'Test-only: GDELT title', 'url': 'https://news.fixture.invalid/markets/test-only-shilling', 'domain': 'news.fixture.invalid',
                'gdelt_seen': seen, 'gdelt_country': 'Kenya', 'gdelt_region': 'east_africa', 'feed_region': 'af'}

    def test_publication_time_title_source_and_description_come_from_the_page(self):
        c, reason = m.enrich_page(self.row(), PAGE, START, END)
        self.assertIsNone(reason)
        self.assertEqual(c['published'], '2026-09-02T04:40:00Z')  # article:published_time, not modified_time or seendate
        self.assertEqual(c['title'], 'Test-only: Kenyan shilling edges up as central bank holds rate')
        self.assertEqual(c['source'], 'Fixture Daily'); self.assertTrue(c['desc'].startswith('Test-only description'))
        self.assertNotIn('body text', json.dumps(c)); self.assertEqual(c['hint'], ''); self.assertIn('chash', c)

    def test_missing_naive_outside_modified_and_paywalled_pages_are_rejected(self):
        cases = {
            'no_original_publication_time_on_page': PAGE.replace('article:published_time', 'x-none'),
            'original_date_outside_requested_window': PAGE.replace('2026-09-02T07:40:00+03:00', '2026-07-30T07:40:00+03:00'),
            'paywalled_page': PAGE.replace('</head>', '<script type="application/ld+json">{"isAccessibleForFree": "False"}</script></head>'),
            'no_source_description': PAGE.replace('og:description', 'x-none'),
        }
        for reason, page in cases.items():
            self.assertEqual(m.enrich_page(self.row(), page, START, END), (None, reason))
        naive = PAGE.replace('2026-09-02T07:40:00+03:00', '2026-09-02T07:40:00')
        self.assertEqual(m.enrich_page(self.row(), naive, START, END)[1], 'no_original_publication_time_on_page')
        self.assertEqual(m.enrich_page(self.row('2026-08-20T00:00:00Z'), PAGE, START, END)[1], 'page_date_after_discovery_likely_modified')
        ld = PAGE.replace('article:published_time', 'x-none').replace('</head>', '<script>{"datePublished":"2026-09-02T05:00:00Z"}</script></head>')
        self.assertEqual(m.enrich_page(self.row(), ld, START, END)[0]['published'], '2026-09-02T05:00:00Z')

    def test_robots_paywalled_hosts_and_redirects(self):
        calls = []
        def get(url, timeout=None):
            calls.append(url)
            if url.endswith('/robots.txt'): return 'User-agent: *\nDisallow: /markets/\n'
            raise AssertionError('disallowed page fetched')
        clock = Clock(); f = m.PageFetcher(get, clock=clock, sleep=clock.sleep)
        self.assertEqual(f.enrich(self.row(), START, END), (None, 'robots_disallowed'))
        self.assertEqual(calls, ['https://news.fixture.invalid/robots.txt'])
        paywalled = {**self.row(), 'url': 'https://www.ft.com/content/test-only'}
        self.assertEqual(f.enrich(paywalled, START, END), (None, 'paywalled_publisher')); self.assertEqual(len(calls), 1)

        def redirecting(target):
            def get(url, timeout=None):
                if url.endswith('/robots.txt'): raise http_error(url, 404)
                if url == self.row()['url']: raise http_error(url, 301, target)
                return PAGE
            return get
        f = m.PageFetcher(redirecting('/markets/test-only-shilling/'), clock=clock, sleep=clock.sleep)
        self.assertIsNone(f.enrich(self.row(), START, END)[1])
        f = m.PageFetcher(redirecting('https://elsewhere.fixture.invalid/x'), clock=clock, sleep=clock.sleep)
        self.assertEqual(f.enrich(self.row(), START, END), (None, 'redirect_to_other_site'))

    def test_a_page_cut_off_mid_download_is_skipped_not_fatal(self):
        import http.client
        def get(url, timeout=None):
            if url.endswith('/robots.txt'): return ''
            raise http.client.IncompleteRead(b'partial')
        clock = Clock(); f = m.PageFetcher(get, clock=clock, sleep=clock.sleep)
        self.assertEqual(f.enrich(self.row(), START, END), (None, 'page_unavailable'))
        def boom(url, timeout=None):
            if url.endswith('/robots.txt'): return ''
            raise RuntimeError('anything else')
        self.assertEqual(m.PageFetcher(boom, clock=clock, sleep=clock.sleep).enrich(self.row(), START, END), (None, 'page_unavailable'))

    def test_same_host_requests_are_spaced(self):
        clock = Clock(); times = []
        def get(url, timeout=None):
            if url.endswith('/robots.txt'): return 'User-agent: *\nCrawl-delay: 3\n'
            times.append(clock.t); return PAGE
        f = m.PageFetcher(get, clock=clock, sleep=clock.sleep)
        for i in range(3): f.page(f'https://news.fixture.invalid/{i}')
        self.assertTrue(all(b - a >= 3 for a, b in zip(times, times[1:])), times)


class LibraryTests(unittest.TestCase):
    def test_merge_with_worker_day_never_drops_rows_and_batches_three_days(self):
        days = {f'2026-09-0{d}': [{'id': f'n{d}', 'h': 'Test-only', 't': f'2026-09-0{d}T01:00:00Z'}] for d in range(1, 6)}
        existing = {'2026-09-01': [{'id': 'old', 'h': 'Test-only old', 't': '2026-09-01T05:00:00Z'}], '2026-09-02': [{'id': 'n2'}]}
        pushes, acked = [], []
        def push(url, token, group): pushes.append(group); return {'ok': True, 'written': len(group)}
        done, deferred = m.ingest_library('https://w.invalid', 't', days, lambda d: existing.get(d, []), push, acked.extend)
        self.assertEqual([len(p) for p in pushes], [3, 1]); self.assertIn('2026-09-02', done)  # already complete there: no push
        self.assertNotIn('2026-09-02', [d for p in pushes for d in p])
        self.assertEqual([r['id'] for r in pushes[0]['2026-09-01']], ['old', 'n1']); self.assertEqual(deferred, [])
        self.assertEqual(sorted(r['id'] for r in acked), ['n1', 'n2', 'n3', 'n4', 'n5'])
        full = {'2026-09-01': [{'id': str(i)} for i in range(m.LIBRARY_DAY_LIMIT)]}
        done, deferred = m.ingest_library('https://w.invalid', 't', {'2026-09-01': days['2026-09-01']}, lambda d: full[d], push, acked.extend)
        self.assertEqual(done, []); self.assertEqual(deferred[0]['reason'], 'library_day_limit_1500_no_truncation')
        with self.assertRaises(ValueError):
            m.ingest_library('https://w.invalid', 't', days, lambda d: [], lambda *a: {'ok': False}, acked.extend)

    def test_budget_cap_is_1_to_80(self):
        self.assertEqual(m.Budget(lambda *a, **k: '{}', 80).limit, 80)
        for bad in (0, 81):
            with self.assertRaises(ValueError): m.Budget(lambda *a, **k: '{}', bad)


class EndToEndTests(unittest.TestCase):
    """Whole run with fake transports: GDELT fixture -> publisher page -> existing robot prompt -> artifact."""
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory(); base = Path(self.dir.name)
        self.state, self.out, self.cache = base/'state', base/'out', base/'cache'
        (self.state/'events').mkdir(parents=True)
        self.worker_posts = []; self.library_pushes = []; self.model_prompts = []

    def tearDown(self): self.dir.cleanup()

    def worker(self, url, data=None, headers=None, timeout=15, raw=False):
        if data is not None: self.worker_posts.append(url); raise AssertionError('no POST through the read client')
        if '/v1/news?' in url:
            return json.dumps({'data': {'stories': [{'id': 'live1', 'headline': 'Test-only live article', 'published_at': '2026-11-11T10:00:00Z',
                                                     'source': {'name': 'Fixture', 'url': 'https://live.fixture.invalid/1'}}]},
                               'meta': {'fetched_at': '2026-11-11T11:00:00Z', 'model': 'gemini-test-only'}})
        if '/v1/library?day=' in url:
            if url.endswith('2026-09-02'): return json.dumps({'data': {'day': '2026-09-02', 'rows': [{'id': 'kept', 'h': 'Test-only kept', 't': '2026-09-02T01:00:00Z'}]}})
            raise http_error(url, 404)
        raise AssertionError('unexpected Worker read ' + url)

    def gdelt(self, url, timeout=None):
        return gkg_zip() if '20260902120000' in url else gkg_zip('')

    def page(self, url, timeout=None):
        if url.endswith('/robots.txt'): return 'User-agent: *\nAllow: /\n'
        if url.endswith('test-only-tea'): return PAGE.replace('og:description', 'x-none')  # no description -> rejected
        return PAGE

    def model(self, url, data=None, headers=None, timeout=None, raw=False):
        prompt = json.loads(data)['contents'][0]['parts'][0]['text']; self.model_prompts.append(prompt)
        self.assertIn('Test-only description', prompt); self.assertNotIn('body text', prompt)
        picked = [{'members': [0], 'headline': 'Must never replace the original', 'summary': 'Test-only summary written from the description.',
                   'why': 'Test-only', 'category': 'economy', 'importance': 1, 'country': 'KE', 'lat': -1.29, 'lon': 36.82, 'place': 'Nairobi', 'impacts': [], 'photo': 'bank building'}]
        return json.dumps({'candidates': [{'content': {'parts': [{'text': json.dumps(picked)}]}}]})

    def run_once(self, dry_run, calls=3, **extra):
        def library_push(url, token, group): self.library_pushes.append(group); return {'ok': True, 'written': len(group)}
        with patch.object(m.regional, 'request', side_effect=self.worker), patch.object(m.robot, 'GEMINI', 'test-only-key'), \
             patch.object(m.uploader, 'push', side_effect=AssertionError('live 48-hour feed ingestion')), \
             patch.object(m.robot, 'PIXABAY', 'test-only-key-never-used'), \
             patch.object(m.robot, 'get', side_effect=AssertionError('Pixabay download')), \
             patch.dict('os.environ', {'NEWS_INGEST_TOKEN': 'test-only-token'}):
            return m.run('2026-09-01', '2026-09-03', 'east_africa', dry_run, self.out, 'https://worker.fixture.invalid', self.cache,
                         gemini_calls=calls, batch_size=5, gdelt_files=5, now=NOW, gdelt_get=self.gdelt, page_get=self.page,
                         model_get=self.model, library_push=library_push, sleep=lambda s: None, state_root=self.state, **extra)

    def test_dry_run_builds_review_artifact_and_ingests_nothing(self):
        report = self.run_once(True)
        self.assertEqual(report['state'], 'dry_run_complete'); self.assertEqual(report['new_articles'], 1)
        self.assertEqual(report['gemini_calls'], 1); self.assertEqual(report['by_country'], {'Kenya': 1})
        self.assertEqual(report['by_day'], {'2026-09-02': 1}); self.assertEqual(report['rejections']['pages_and_rules'].get('no_source_description'), 1)
        self.assertEqual(self.library_pushes, []); self.assertEqual(self.worker_posts, [])
        self.assertEqual(sorted(p.name for p in self.state.iterdir()), ['events'])  # no producer state written
        self.assertEqual(list((self.state/'events').iterdir()), [])
        art = json.loads((self.out/'new-articles.json').read_text())[0]
        self.assertEqual(art['headline'], 'Test-only: Kenyan shilling edges up as central bank holds rate')
        self.assertEqual(art['published_at'], '2026-09-02T04:40:00Z'); self.assertTrue(art['backfilled'])
        self.assertEqual(art['backfill_provenance']['version'], 'gdelt-backfill-v1')
        index = json.loads((ROOT/'assets/globe/photos/index.json').read_text())
        self.assertEqual(art['image']['kind'], 'topic'); self.assertEqual(art['image']['source'], 'Pixabay')
        self.assertIn(art['image']['file'], [p['file'] for p in index['bank building']])  # existing published pool only
        self.assertEqual(report['with_topic_photo'], 1)
        self.assertEqual(art['location']['country'], 'Kenya'); self.assertEqual(len(art['sources']), 1)
        self.assertNotIn('_feed_description', art); self.assertEqual(report['sample_articles'][0]['id'], art['id'])
        self.assertTrue((self.out/'report.json').exists()); self.assertTrue((self.out/'events/2026-09-02.json').exists())
        # The second (resumed) run reads GDELT from the cache: no new GDELT request.
        report = self.run_once(True); self.assertEqual(report['gdelt']['downloads'], 0); self.assertGreater(report['gdelt']['cache_hits'], 0)

    def test_overloaded_model_is_retried_with_pauses_then_the_next_model_is_used(self):
        good, used = self.model, []
        def model(url, **kw):
            name = url.rsplit('/models/', 1)[1].split(':')[0]; used.append(name)
            if name == 'gemini-test-only':
                raise urllib.error.HTTPError(url, 503, 'x', {}, io.BytesIO(json.dumps({'error': {'message': 'The model is overloaded. Please try again later.'}}).encode()))
            return good(url, **kw)
        self.model = model
        report = self.run_once(True, calls=10)
        order = report['model_order']
        self.assertEqual(order[0], 'gemini-test-only'); self.assertEqual(order[-2:], ['gemini-flash-latest', 'gemini-flash-lite-latest'])
        self.assertEqual(used[:3], ['gemini-test-only'] * 3); self.assertEqual(report['model_retries'], {'gemini-test-only': 2})
        self.assertEqual(report['models_failed'], {'gemini-test-only': 'http_503: The model is overloaded. Please try again later.'})
        self.assertEqual(report['gemini_calls'], 4); self.assertEqual(report['new_articles'], 1)
        self.assertEqual(report['actual_model_used'], order[1])

    def test_all_models_failing_stops_and_says_why(self):
        def model(url, **kw): raise http_error(url, 400)
        self.model = model
        with self.assertRaises(ValueError): self.run_once(True, calls=10)
        report = json.loads((self.out/'report.json').read_text())
        self.assertEqual(report['gemini_calls'], len(report['model_order']))  # 400 is not retried
        self.assertEqual(set(report['models_failed'].values()), {'http_400'}); self.assertEqual(report['new_articles'], 0)

    def test_live_run_goes_to_library_and_day_files_never_the_live_feed(self):
        report = self.run_once(False)
        self.assertEqual(report['state'], 'ingestion_acknowledged'); self.assertEqual(len(self.library_pushes), 1)
        rows = self.library_pushes[0]['2026-09-02']; self.assertEqual([r['id'] for r in rows][0], 'kept')
        self.assertEqual(rows[1]['t'], '2026-09-02T04:40:00Z'); self.assertEqual(rows[1]['n'], 'Kenya')
        day = json.loads((self.state/'events/2026-09-02.json').read_text())['events']
        self.assertEqual([e['at'] for e in day], ['2026-09-02T04:40:00Z'])
        state = json.loads((self.state/'gdelt-backfill-state.json').read_text())['processed']
        self.assertEqual(sorted(state), ['news.fixture.invalid/markets/test-only-shilling', 'news.fixture.invalid/markets/test-only-tea'])  # tea: stable page rejection
        # Next run: the acknowledged article is a duplicate and no model call is spent on it.
        self.library_pushes.clear(); self.model_prompts.clear()
        report = self.run_once(False)
        self.assertEqual(report['new_articles'], 0); self.assertEqual(self.model_prompts, []); self.assertEqual(self.library_pushes, [])

    def test_separate_ingest_step_rechecks_provenance_and_skips_articles_already_in_day_files(self):
        self.run_once(True)  # artifact only
        art = json.loads((self.out/'new-articles.json').read_text())
        pushes = []
        def push(url, token, group): pushes.append(group); return {'ok': True}
        with patch.object(m.regional, 'request', side_effect=self.worker), patch.dict('os.environ', {'NEWS_INGEST_TOKEN': 'test-only-token'}):
            m.events.upsert(json.loads(json.dumps(art)), base=str(self.state/'events'))  # hourly robot already holds it
            result = m.ingest_artifact(self.out, 'https://worker.fixture.invalid', self.state, NOW, push)
            self.assertEqual(result['already_present'], 1); self.assertEqual(pushes, [])
            for bad in ({'backfilled': False}, {'published_at': '2026-11-10T00:00:00Z'}, {'impacts': [{'scorable': True}]}):
                (self.out/'new-articles.json').write_text(json.dumps([{**art[0], **bad}]))
                with self.assertRaises(ValueError): m.ingest_artifact(self.out, 'https://worker.fixture.invalid', self.state, NOW, push)
        self.assertEqual(pushes, [])


class FakeClaude:
    """Test-only stand-in for anthropic.Anthropic(): records requests, returns a Messages-API-shaped reply."""
    def __init__(self, reply_text, stop='end_turn', usage=(1000, 500)):
        self.requests = []; self.reply_text, self.stop, self.usage = reply_text, stop, usage
        self.messages = SimpleNamespace(create=self.create)
    def create(self, **kw):
        self.requests.append(kw)
        return SimpleNamespace(stop_reason=self.stop, content=[SimpleNamespace(type='thinking', thinking=''), SimpleNamespace(type='text', text=self.reply_text)],
                               usage=SimpleNamespace(input_tokens=self.usage[0], output_tokens=self.usage[1]))


class ClaudeProviderTests(EndToEndTests):
    PICKED = [{'members': [0], 'headline': 'Must never replace the original', 'summary': 'Test-only summary written from the description.',
               'why': 'Test-only', 'category': 'economy', 'importance': 1, 'country': 'KE', 'lat': -1.29, 'lon': 36.82, 'place': 'Nairobi', 'impacts': [], 'photo': 'bank building'}]

    def setUp(self):
        super().setUp()
        def no_gemini(url, **kw): raise AssertionError('Gemini must not be called with provider=claude')
        self.model = no_gemini

    def test_haiku_writes_through_the_same_robot_rules_and_reports_cost(self):
        fake = FakeClaude('```json\n' + json.dumps(self.PICKED) + '\n```')
        report = self.run_once(True, calls=5, provider='claude', claude_client=fake)
        self.assertEqual(report['new_articles'], 1); self.assertEqual(report['provider'], 'claude')
        self.assertEqual(report['actual_model_used'], 'claude-haiku-5-5'); self.assertEqual(report['gemini_calls'], 1)
        self.assertAlmostEqual(report['cost_usd'], 0.00035)
        req = fake.requests[0]
        self.assertEqual(req['model'], 'claude-haiku-5-5'); self.assertEqual(req['output_config'], {'effort': 'low'})
        self.assertIn('Test-only description', req['messages'][0]['content']); self.assertNotIn('body text', req['messages'][0]['content'])
        art = json.loads((self.out/'new-articles.json').read_text())[0]
        self.assertEqual(art['headline'], 'Test-only: Kenyan shilling edges up as central bank holds rate')
        self.assertEqual(art['published_at'], '2026-09-02T04:40:00Z'); self.assertTrue(art['backfilled'])
        self.assertEqual(self.library_pushes, [])

    def test_dollar_cap_stops_before_any_call_that_could_pass_it(self):
        fake = FakeClaude(json.dumps(self.PICKED))
        report = self.run_once(True, calls=5, provider='claude', claude_client=fake, max_usd=0.001)
        self.assertEqual(fake.requests, []); self.assertEqual(report['model_budget_stop'], 'dollar_cap_reached')
        self.assertEqual(report['new_articles'], 0); self.assertEqual(report['cost_usd'], 0)
        with self.assertRaises(ValueError): m.ClaudeEditor(fake, 'claude-unknown', None, 1)

    def test_refused_or_cut_off_batch_adds_nothing_and_is_counted(self):
        for stop in ('refusal', 'max_tokens'):
            fake = FakeClaude(json.dumps(self.PICKED), stop=stop)
            report = self.run_once(True, calls=5, provider='claude', claude_client=fake)
            self.assertEqual(report['new_articles'], 0); self.assertEqual(report['claude_unusable_batches'], {'stop_' + stop: 1})

    def test_rejected_request_keeps_claudes_reason(self):
        class Rejected(Exception):
            status_code = 400; body = {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low.'}}
        fake = FakeClaude('[]')
        def boom(**kw): raise Rejected()
        fake.messages = SimpleNamespace(create=boom)
        with self.assertRaises(ValueError): self.run_once(True, calls=5, provider='claude', claude_client=fake)
        report = json.loads((self.out/'report.json').read_text())
        self.assertEqual(report['models_failed'], {'claude-haiku-5-5': 'http_400: Your credit balance is too low.'})

    def test_local_language_articles_get_a_marked_english_headline(self):
        tr_row = GKG.splitlines()[0].split('\t')
        tr_row[4] = 'https://news.fixture.invalid/markets/test-only-shilling-sw'
        tr_row[25] = 'srclc:swa;eng:GT-SWA 1.0'
        tr_row[26] = '<PAGE_TITLE>Test-only: Shilingi yaimarika benki kuu ikishikilia riba</PAGE_TITLE>'
        tr_text = '\t'.join(tr_row)
        self.gdelt = lambda url, timeout=None: gkg_zip(tr_text) if ('translation' in url and '20260902120000' in url) else gkg_zip('')
        page_sw = PAGE.replace('Test-only: Kenyan shilling edges up as central bank holds rate | Fixture Daily', 'Test-only: Shilingi yaimarika benki kuu ikishikilia riba')
        self.page = lambda url, timeout=None: 'User-agent: *\nAllow: /\n' if url.endswith('/robots.txt') else page_sw
        replies = [json.dumps([{'i': 0, 'title': 'Test-only: Shilling strengthens as central bank holds rate',
                                'description': 'Test-only description: the shilling firmed after the central bank in Nairobi kept its rate.'}]),
                   json.dumps(self.PICKED)]
        class Seq(FakeClaude):
            def create(self, **kw):
                self.reply_text = replies[len(self.requests)]; return super().create(**kw)
        fake = Seq('')
        report = self.run_once(True, calls=5, provider='claude', claude_client=fake, sources='translated')
        self.assertIn('Translate each news headline', fake.requests[0]['messages'][0]['content'])
        self.assertIn('Shilingi', fake.requests[0]['messages'][0]['content'])
        self.assertIn('Shilling strengthens', fake.requests[1]['messages'][0]['content'])
        art = json.loads((self.out/'new-articles.json').read_text())[0]
        self.assertEqual(art['headline'], 'Test-only: Shilling strengthens as central bank holds rate')
        self.assertTrue(art['headline_translated']); self.assertEqual(art['source_language'], 'swa')
        self.assertEqual(art['original_headline'], 'Test-only: Shilingi yaimarika benki kuu ikishikilia riba')
        self.assertEqual(art['published_at'], '2026-09-02T04:40:00Z')
        self.assertEqual(report['translated_articles'], 1); self.assertEqual(report['translated_samples'][0]['language'], 'swa')
        with self.assertRaises(ValueError): self.run_once(True, sources='translated')  # Gemini cannot translate here
        # Fix C: a translated article placed in a large Western economy, or politics without market impact, is dropped.
        for change, reason in (({'country': 'DE', 'lat': 52.5, 'lon': 13.4, 'place': 'Berlin'}, 'translated_outside_thin_regions'),
                               ({'category': 'geopolitics', 'market_moving': False}, 'translated_not_business')):
            self.PICKED = [{**ClaudeProviderTests.PICKED[0], **change}]
            replies[1] = json.dumps(self.PICKED)
            report = self.run_once(True, calls=5, provider='claude', claude_client=Seq(''), sources='translated')
            self.assertEqual(report['new_articles'], 0); self.assertEqual(report['rejections']['pages_and_rules'].get(reason), 1)
        weak = tr_text.split('\t'); weak[7] = 'ECON_UNIONS;ECON_TAXATION_X;ECON_WORKINGCLASS;'
        self.assertEqual(m.parse_gkg('\t'.join(weak), FILE_TIME, True)[1], {'translated_needs_strong_business_theme': 1})
        self.assertEqual(len(m.parse_gkg('\t'.join(weak), FILE_TIME, False)[0]), 1)  # English rule unchanged

    # The Gemini-specific scenarios of the parent class do not apply here.
    test_overloaded_model_is_retried_with_pauses_then_the_next_model_is_used = None
    test_all_models_failing_stops_and_says_why = None
    test_dry_run_builds_review_artifact_and_ingests_nothing = None
    test_live_run_goes_to_library_and_day_files_never_the_live_feed = None
    test_separate_ingest_step_rechecks_provenance_and_skips_articles_already_in_day_files = None


class CommandLineTests(unittest.TestCase):
    def test_confirm_word_bounds_and_settings_are_checked_before_any_request(self):
        with patch.object(m, 'run', side_effect=AssertionError('run started')), patch.dict('os.environ', {}, clear=True):
            for argv in (['--confirm', 'yes'], ['--confirm', 'BACKFILL', '--gemini-calls', '81'], ['--confirm', 'BACKFILL', '--start', '2026-07-01'],
                         ['--confirm', 'BACKFILL', '--regions', 'atlantis'], ['--confirm', 'BACKFILL'],
                         ['--confirm', 'BACKFILL', '--phase', 'ingest', '--dry-run', 'true'],
                         ['--confirm', 'BACKFILL', '--provider', 'claude', '--max-usd', '0'],
                         ['--confirm', 'BACKFILL', '--provider', 'claude', '--claude-model', 'claude-unknown']):
                with self.assertRaises(SystemExit), patch('sys.stderr', io.StringIO()): m.main(argv)
        # Claude needs its own key, not the Gemini one.
        with patch.object(m, 'run', side_effect=AssertionError('run started')), patch.dict('os.environ', {'GEMINI_API_KEY': 'x', 'WORKER_URL': 'https://w.invalid'}, clear=True):
            err = io.StringIO()
            with self.assertRaises(SystemExit), patch('sys.stderr', err): m.main(['--confirm', 'BACKFILL', '--provider', 'claude'])
            self.assertIn('ANTHROPIC_API_KEY', err.getvalue())


if __name__ == '__main__': unittest.main()
