# Graph Report - investedia-coordinated-migration-k_8uwaks  (2026-11-23)

## Corpus Check
- 255 files · ~159,064 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 5, .otf 3, .toml 2)

## Summary
- 3087 nodes · 6020 edges · 179 communities (126 shown, 53 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 139 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `397415da`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_engine_v4_pipeline.py
- calendar_fred.py
- pathlib
- regional-backfill.py
- json
- update_news_track.py
- MarketsPilotTests
- SnapshotRepositoryTest.java
- ApiContractTest.java
- source_licensing.py
- live/index.js
- prices.js
- registry.py
- with
- steps
- steps
- steps
- MarketService
- steps
- with
- steps
- news.js
- worker-contracts.mjs
- with
- steps
- math
- news-gap-backfill.py
- update_globe_news.py
- steps
- steps
- MediaTests
- hashlib
- NewsService.java
- markets_audit/run.py
- news_core.py
- SnapshotResponseHeaders.java
- argparse
- markets.js
- copy
- update_market.py
- FileMarketRepository.java
- handleNews
- events.py
- gdelt-backfill.py
- alerts.js
- steps
- NewsImpacts
- calendar_official.py
- NewsPhotos
- with
- .missingAndMalformedSnapshotsFailClosedWithoutLeakingPaths
- context.py
- env
- AzureEditorTests
- policy.test.mjs
- feed_inventory.py
- with
- live_v5.py
- with
- LicensingEvidenceTests
- server
- enrich_page
- inputs
- judge_daily
- engine/policy.py
- news-gap-backfill.yml
- steps
- runner.py
- gen-companies.py
- regional-backfill.yml
- Policy
- StrictNewsTests
- fx_audit
- methods.py
- ref_node_assert
- ApiConfiguration.java
- collections
- inputs
- with
- with
- update_asset_analysis.py
- balance
- Downloads
- ClaudeEditor
- .test_activation_is_last
- PhotoPoolTests
- steps
- LiveConnectionsTests
- LegalLinks
- MarketFocusTest
- package.json
- steps
- ExchangeCoordinatesTest
- env
- RegionalFixTests
- InvestediaApplication.java
- env
- MarketTests
- GapTests
- RecoveryIntegrationTests
- SectorTests
- with
- confirm
- start
- batch_size
- tabular
- dry_run
- gemini_calls
- SavedFeeds
- BasicsTests
- FeedsTests
- StageIntegrationTests
- PushNews
- build_projects.py
- generate
- sources
- com.investedia:investedia-backend
- com.investedia:investedia-services
- with
- steps
- extract.py
- thin-recent.yml
- alert-email-preview.yml
- current
- env
- re
- RegionalTests
- test_projects_pipeline.py
- Clock
- ProjectsPipelineTests
- time
- .run_once
- EndToEndTests
- batch_size
- org.springframework.web.bind.annotation.GetMapping
- shadow.py
- ingest
- backfill-photos.py
- GkgClient
- Budget
- gkg_zip
- generate
- with
- steps
- AuditInputTests
- PublishLibrary
- resolve_impacts.py
- PageFetcher
- inputs
- RecentIngestTests
- DiscoveryTests
- .test_separate_ingest_step_rechecks_provenance_and_skips_articles_already_in_day_files
- writer
- sources
- writer
- WindowsAndRegions
- ClaudeWriterTests
- error_message
- country_cap
- end_date
- gdelt_files
- regions
- start_date
- connections_only
- ConnectionTests
- NewsTrialTests
- outcome.py
- HoursTests
- news.test.mjs
- fiscal_year
- TrialExportTests
- AuditTests
- CachedRepresentationTests
- LegacyRetryBudgetTests

## God Nodes (most connected - your core abstractions)
1. `run()` - 37 edges
2. `MarketsPilotTests` - 31 edges
3. `run()` - 30 edges
4. `fetch()` - 29 edges
5. `env` - 23 edges
6. `build()` - 22 edges
7. `ProjectsPipelineTests` - 21 edges
8. `reconcile()` - 20 edges
9. `main()` - 19 edges
10. `env` - 18 edges

## Surprising Connections (you probably didn't know these)
- `server` --calls--> `fetch()`  [EXTRACTED]
  tests/news-ingest.integration.mjs → workers/live/index.js
- `MarketsPilotTests` --uses--> `Downloads`  [INFERRED]
  tests/test_markets_pilot.py → tools/markets_pilot/fetch.py
- `regional_candidates()` --indirect_call--> `c()`  [INFERRED]
  tools/regional-backfill.py → tests/test_news_regions.py
- `DiscoveryTests` --uses--> `Deferred`  [INFERRED]
  tests/test_projects_media.py → tools/projects/scale/transport.py
- `checked_fetch()` --calls--> `transport()`  [INFERRED]
  tools/coverage/source_licensing.py → tests/test_regional_backfill.py

## Import Cycles
- None detected.

## Communities (179 total, 53 thin omitted)

### Community 0 - "test_engine_v4_pipeline.py"
Cohesion: 0.14
Nodes (6): Context, Extraction, Outcome, Runner, session(), Shadow

### Community 1 - "calendar_fred.py"
Cohesion: 0.09
Nodes (18): _calc(), covered(), _day(), enrich(), fill_actuals(), _fmt(), FredError, _get() (+10 more)

### Community 2 - "pathlib"
Cohesion: 0.06
Nodes (9): AzureProviderAccepted, CommandLineTests, CountryCapTests, RecentWindowTests, TitleJunkTests, HistoryConnections, EnglishHeadlineTests, ExtraFeedsTests (+1 more)

### Community 3 - "regional-backfill.py"
Cohesion: 0.10
Nodes (31): content_hash(), archive(), batches(), cached_patch(), contains_secret(), dedupe(), draw_connections(), english_headlines() (+23 more)

### Community 4 - "json"
Cohesion: 0.07
Nodes (24): save(), facts(), load(), main(), parse(), get(), main(), publish() (+16 more)

### Community 5 - "update_news_track.py"
Cohesion: 0.09
Nodes (17): Ledger, story(), Track, call(), OutcomeV2, bench_of(), call_start(), freeze() (+9 more)

### Community 6 - "MarketsPilotTests"
Cohesion: 0.12
Nodes (4): MarketsPilotTests, build(), reconcile(), validate_model()

### Community 7 - "SnapshotRepositoryTest.java"
Cohesion: 0.10
Nodes (6): RepositoryProperties, SnapshotUnavailableException, FileCallRepository, FileMarketRepository, FileNewsRepository, JsonSnapshotReader

### Community 8 - "ApiContractTest.java"
Cohesion: 0.06
Nodes (4): ApiContractTest, TimeConfiguration, LayeredArchitectureTest, LocalStartupTest

### Community 9 - "source_licensing.py"
Cohesion: 0.26
Nodes (9): active_sources(), collect(), checked_fetch(), contains_secret(), get(), main(), cached_fetch(), NoRedirect (+1 more)

### Community 10 - "live/index.js"
Cohesion: 0.08
Nodes (37): ALIAS, ALLOWED, cors(), fetch(), json(), scheduled(), snapshot(), withAliases() (+29 more)

### Community 11 - "prices.js"
Cohesion: 0.13
Nodes (31): fetchQuotes(), MAX_SYMBOLS, parseSpark(), PROVIDER, TIER_A, TIER_B, NOW, day() (+23 more)

### Community 12 - "registry.py"
Cohesion: 0.10
Nodes (11): ascii_lower(), get(), name_key(), norm_ticker(), Registry, same_company(), stamp(), words() (+3 more)

### Community 13 - "with"
Cohesion: 0.06
Nodes (34): runs-on, steps, timeout-minutes, concurrency, cancel-in-progress, group, DOWNLOAD_MB, max_download_mb (+26 more)

### Community 14 - "steps"
Cohesion: 0.06
Nodes (33): if, runs-on, steps, timeout-minutes, concurrency, cancel-in-progress, group, GEMINI_API_KEY (+25 more)

### Community 15 - "steps"
Cohesion: 0.06
Nodes (33): concurrency, cancel-in-progress, group, GEMINI_API_KEY, NEWS_INGEST_TOKEN, PIXABAY_KEY, WORKER_URL, jobs (+25 more)

### Community 16 - "steps"
Cohesion: 0.06
Nodes (31): runs-on, steps, timeout-minutes, concurrency, cancel-in-progress, group, SAMPLE_LIMIT, sample_limit (+23 more)

### Community 17 - "MarketService"
Cohesion: 0.19
Nodes (4): MarketController, MarketRepository, MarketService, SnapshotMetadata

### Community 18 - "steps"
Cohesion: 0.06
Nodes (30): if, runs-on, steps, timeout-minutes, concurrency, cancel-in-progress, group, CALENDAR_UNLICENSED (+22 more)

### Community 19 - "with"
Cohesion: 0.08
Nodes (29): concurrency, cancel-in-progress, group, runs-on, steps, timeout-minutes, jobs, java (+21 more)

### Community 20 - "steps"
Cohesion: 0.07
Nodes (28): concurrency, cancel-in-progress, group, default, description, runs-on, steps, timeout-minutes (+20 more)

### Community 21 - "news.js"
Cohesion: 0.05
Nodes (49): generate(), busy, env, NOW, quiet, stories, warmIx, NOW (+41 more)

### Community 22 - "worker-contracts.mjs"
Cohesion: 0.08
Nodes (17): env, expected, feed, now, p, quotes, snapshots, source (+9 more)

### Community 23 - "with"
Cohesion: 0.07
Nodes (27): concurrency, cancel-in-progress, group, runs-on, steps, timeout-minutes, jobs, deploy (+19 more)

### Community 24 - "steps"
Cohesion: 0.07
Nodes (27): concurrency, cancel-in-progress, group, GH_REPO, GH_TOKEN, jobs, notices, name (+19 more)

### Community 25 - "math"
Cohesion: 0.06
Nodes (43): ShareCards, assets_for(), date(), fetch_api(), finite(), generate(), main(), markdown() (+35 more)

### Community 26 - "news-gap-backfill.py"
Cohesion: 0.13
Nodes (19): articles(), ArticleText, confirm(), dedupe(), digest(), get(), in_window(), keys() (+11 more)

### Community 27 - "update_globe_news.py"
Cohesion: 0.13
Nodes (22): backfill_impacts(), compact48(), dedupe(), describe(), err(), gdelt(), gemini(), gemini_models() (+14 more)

### Community 28 - "steps"
Cohesion: 0.07
Nodes (26): concurrency, cancel-in-progress, group, description, required, NEWS_INGEST_TOKEN, WORKER_URL, if (+18 more)

### Community 29 - "steps"
Cohesion: 0.07
Nodes (26): concurrency, cancel-in-progress, group, description, required, NEWS_INGEST_TOKEN, WORKER_URL, confirm (+18 more)

### Community 31 - "hashlib"
Cohesion: 0.11
Nodes (10): ScaleTransportTests, run(), details(), ids(), header_hash(), records(), BudgetExceeded, Client (+2 more)

### Community 32 - "NewsService.java"
Cohesion: 0.17
Nodes (5): NewsController, ApiEnvelope, NewsSnapshot, NewsRepository, NewsService

### Community 33 - "markets_audit/run.py"
Cohesion: 0.18
Nodes (12): AuditScopeTests, RunnerBoundaryTests, coverage(), ecb_xml(), fetch_audit(), licensing(), main(), read() (+4 more)

### Community 34 - "news_core.py"
Cohesion: 0.08
Nodes (20): age_minutes(), atomic_write(), authority_of(), canon(), dedupe(), entities(), freshness(), from_iso() (+12 more)

### Community 35 - "SnapshotResponseHeaders.java"
Cohesion: 0.14
Nodes (3): SnapshotResponseHeaders, ApiExceptionHandler, UnknownGroupException

### Community 36 - "argparse"
Cohesion: 0.08
Nodes (26): active_time(), calendar_metadata(), enrich(), main(), collect(), companies_house(), confirmed_ogl(), gleif() (+18 more)

### Community 37 - "markets.js"
Cohesion: 0.25
Nodes (16): setup(), ApiError, CREDITS, error(), fail(), handleMarkets(), integer(), metadata() (+8 more)

### Community 38 - "copy"
Cohesion: 0.13
Nodes (12): DiscoveryTests, commons_candidate(), discover(), main(), query(), attach(), contained(), date() (+4 more)

### Community 39 - "update_market.py"
Cohesion: 0.21
Nodes (13): from_fred(), from_yahoo(), chg(), get(), history(), perf(), main(), one() (+5 more)

### Community 41 - "handleNews"
Cohesion: 0.14
Nodes (18): article(), backfilled(), body(), impact, iso(), NOW, post(), seed() (+10 more)

### Community 42 - "events.py"
Cohesion: 0.08
Nodes (11): family(), load_days(), record(), _t(), threads(), upsert(), _write(), write_threads() (+3 more)

### Community 43 - "gdelt-backfill.py"
Cohesion: 0.08
Nodes (34): day(), dedupe(), gkg_plan(), headline_key(), ingest_artifact(), acknowledged(), ingest_library(), known_keys() (+26 more)

### Community 44 - "alerts.js"
Cohesion: 0.11
Nodes (39): RFC-8291, RFC-8292, te, about(), channelsFor(), country(), COUNTRY_ALIAS, deliver() (+31 more)

### Community 45 - "steps"
Cohesion: 0.11
Nodes (18): jobs, offline-trial, name, runs-on, steps, timeout-minutes, on, pull_request (+10 more)

### Community 47 - "calendar_official.py"
Cohesion: 0.25
Nodes (9): all_official(), bea(), bls(), _event(), fomc(), _get(), _text(), OfficialCalendar (+1 more)

### Community 49 - "with"
Cohesion: 0.06
Nodes (30): concurrency, cancel-in-progress, group, if, runs-on, steps, timeout-minutes, jobs (+22 more)

### Community 50 - ".missingAndMalformedSnapshotsFailClosedWithoutLeakingPaths"
Cohesion: 0.16
Nodes (5): CallController, LedgerDocument, CallRepository, CallService, SnapshotRepositoryTest

### Community 51 - "context.py"
Cohesion: 0.24
Nodes (4): features(), _last(), session_start(), sigma_daily()

### Community 52 - "env"
Cohesion: 0.11
Nodes (18): ANTHROPIC_API_KEY, BACKFILL_BATCH_INPUT, BACKFILL_CALLS_INPUT, BACKFILL_CONFIRM_INPUT, BACKFILL_CONNECTIONS_INPUT, BACKFILL_DAYS_INPUT, BACKFILL_DRY_RUN_INPUT, BACKFILL_SOURCES_INPUT (+10 more)

### Community 54 - "policy.test.mjs"
Cohesion: 0.20
Nodes (7): NewsTrial, TrialEgress, destination(), egress(), route(), SOURCE_HOSTS, source

### Community 55 - "feed_inventory.py"
Cohesion: 0.27
Nodes (6): configured(), dates(), get(), main(), NoRedirect, probe()

### Community 56 - "with"
Cohesion: 0.05
Nodes (40): default, description, concurrency, cancel-in-progress, group, GH_TOKEN, backfill_run, jobs (+32 more)

### Community 57 - "live_v5.py"
Cohesion: 0.27
Nodes (5): call_of(), main(), context_of(), series(), v5()

### Community 58 - "with"
Cohesion: 0.05
Nodes (37): runs-on, steps, timeout-minutes, default, description, type, concurrency, cancel-in-progress (+29 more)

### Community 60 - "server"
Cohesion: 0.17
Nodes (11): name, include-message, include-stacktrace, investedia, repository-root, server, address, error (+3 more)

### Community 61 - "enrich_page"
Cohesion: 0.24
Nodes (7): clean_title(), enrich_page(), finalize(), meta(), paywalled(), published_time(), stamp()

### Community 62 - "inputs"
Cohesion: 0.13
Nodes (15): description, required, default, description, required, default, description, confirm (+7 more)

### Community 63 - "judge_daily"
Cohesion: 0.31
Nodes (3): Daily, day(), judge_daily()

### Community 64 - "engine/policy.py"
Cohesion: 0.25
Nodes (6): decide(), horizon(), meaningful(), _pct(), strong_catalyst(), surprise_sign()

### Community 65 - "news-gap-backfill.yml"
Cohesion: 0.18
Nodes (10): concurrency, cancel-in-progress, group, jobs, name, on, workflow_dispatch, permissions (+2 more)

### Community 66 - "steps"
Cohesion: 0.17
Nodes (12): if, runs-on, steps, timeout-minutes, jobs, backfill, id, if (+4 more)

### Community 67 - "runner.py"
Cohesion: 0.13
Nodes (13): backfill(), store(), exclusive_run(), main(), preflight(), verify_generation(), allowed(), decode_bundle() (+5 more)

### Community 68 - "gen-companies.py"
Cohesion: 0.31
Nodes (5): clean(), display(), exchange(), main(), slugify()

### Community 69 - "regional-backfill.yml"
Cohesion: 0.20
Nodes (9): concurrency, cancel-in-progress, group, name, on, workflow_dispatch, permissions, actions (+1 more)

### Community 72 - "fx_audit"
Cohesion: 0.38
Nodes (4): FXTests, fx_audit(), pearson(), returns()

### Community 73 - "methods.py"
Cohesion: 0.39
Nodes (4): IdentifierTests, match(), normal_id(), valid_isin()

### Community 74 - "ref_node_assert"
Cohesion: 0.08
Nodes (20): target, feed, fixture, article(), gap(), now, req(), seed() (+12 more)

### Community 76 - "collections"
Cohesion: 0.50
Nodes (5): history(), km(), load(), main(), _rules()

### Community 77 - "inputs"
Cohesion: 0.22
Nodes (9): default, description, required, end, review_json, staging_run_id, description, description (+1 more)

### Community 78 - "with"
Cohesion: 0.22
Nodes (9): with, github-token, if-no-files-found, name, path, persist-credentials, python-version, retention-days (+1 more)

### Community 79 - "with"
Cohesion: 0.22
Nodes (9): with, if-no-files-found, key, name, path, persist-credentials, python-version, restore-keys (+1 more)

### Community 80 - "update_asset_analysis.py"
Cohesion: 0.39
Nodes (6): ai(), load(), main(), related(), template(), vol()

### Community 81 - "balance"
Cohesion: 0.39
Nodes (3): Balance, c(), balance()

### Community 82 - "Downloads"
Cohesion: 0.25
Nodes (3): Client, NoRedirect, Downloads

### Community 83 - "ClaudeEditor"
Cohesion: 0.11
Nodes (6): AzureEditor, ClaudeEditor, BudgetExceeded, ClaudeWriter, ModelBudget, ModelUnavailable

### Community 86 - "steps"
Cohesion: 0.25
Nodes (8): recovery, runs-on, steps, timeout-minutes, if, name, run, uses

### Community 90 - "package.json"
Cohesion: 0.25
Nodes (7): name, private, scripts, bench, bench:news, test, type

### Community 91 - "steps"
Cohesion: 0.06
Nodes (33): description, required, PER_TOPIC, PIXABAY_KEY, confirm, per_topic, jobs, photos (+25 more)

### Community 93 - "env"
Cohesion: 0.06
Nodes (32): concurrency, cancel-in-progress, group, GH_REPO, GH_TOKEN, MAX_TOTAL, QUEUE, SPENT (+24 more)

### Community 97 - "env"
Cohesion: 0.33
Nodes (6): GAP_END, GAP_START, NEWS_INGEST_TOKEN, REVIEW_JSON, WORKER_URL, env

### Community 102 - "with"
Cohesion: 0.06
Nodes (30): runs-on, steps, timeout-minutes, concurrency, cancel-in-progress, group, default, description (+22 more)

### Community 103 - "confirm"
Cohesion: 0.50
Nodes (4): default, description, type, confirm

### Community 104 - "start"
Cohesion: 0.50
Nodes (4): start, default, description, required

### Community 105 - "batch_size"
Cohesion: 0.50
Nodes (4): default, description, required, batch_size

### Community 106 - "tabular"
Cohesion: 0.15
Nodes (9): parse(), records(), tabular(), parse(), parse(), parse(), parse(), parse() (+1 more)

### Community 107 - "dry_run"
Cohesion: 0.50
Nodes (4): default, description, type, dry_run

### Community 108 - "gemini_calls"
Cohesion: 0.50
Nodes (4): default, description, required, gemini_calls

### Community 114 - "build_projects.py"
Cohesion: 0.12
Nodes (19): ScaleArtifactTests, build(), canonical(), company_links(), covered(), digest(), distance(), featured() (+11 more)

### Community 115 - "generate"
Cohesion: 0.29
Nodes (4): country_allowed(), generate(), provenance(), topic_photo()

### Community 116 - "sources"
Cohesion: 0.40
Nodes (5): sources, default, description, options, type

### Community 121 - "with"
Cohesion: 0.07
Nodes (27): concurrency, cancel-in-progress, group, jobs, refresh, name, on, schedule (+19 more)

### Community 122 - "steps"
Cohesion: 0.08
Nodes (25): ANTHROPIC_API_KEY, MAX_USD, runs-on, steps, timeout-minutes, max_usd, jobs, fill (+17 more)

### Community 123 - "extract.py"
Cohesion: 0.17
Nodes (6): build_prompt(), calendar_expectations(), _num(), story_block(), validate(), records()

### Community 124 - "thin-recent.yml"
Cohesion: 0.09
Nodes (21): concurrency, cancel-in-progress, group, GH_REPO, GH_TOKEN, jobs, start, name (+13 more)

### Community 125 - "alert-email-preview.yml"
Cohesion: 0.10
Nodes (20): TO, TOKEN, WORKER_URL, to, jobs, send, name, on (+12 more)

### Community 126 - "current"
Cohesion: 0.18
Nodes (6): bind(), row(), ScalePolicyTests, ScaleReconciliationTests, TabularScaleTests, current()

### Community 127 - "env"
Cohesion: 0.09
Nodes (22): ANTHROPIC_API_KEY, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_ENDPOINT, BATCH, CALLS, CONFIRM, COUNTRY_CAP (+14 more)

### Community 128 - "re"
Cohesion: 0.18
Nodes (11): parse(), parse(), query(), normalize_sector(), assets(), clean(), fetch(), for_asset() (+3 more)

### Community 130 - "test_projects_pipeline.py"
Cohesion: 0.21
Nodes (6): candidates(), connections(), fingerprint(), review_passes(), main(), parse()

### Community 131 - "Clock"
Cohesion: 0.19
Nodes (5): Clock, get(), PublisherPageTests, redirecting(), get()

### Community 133 - "time"
Cohesion: 0.08
Nodes (16): ok(), fetch(), NoRedirect, sparql(), get(), get(), fetch(), main() (+8 more)

### Community 134 - ".run_once"
Cohesion: 0.17
Nodes (3): ClaudeProviderTests, FakeClaude, boom()

### Community 135 - "EndToEndTests"
Cohesion: 0.21
Nodes (3): EndToEndTests, model(), http_error()

### Community 136 - "batch_size"
Cohesion: 0.50
Nodes (4): default, description, required, batch_size

### Community 138 - "shadow.py"
Cohesion: 0.17
Nodes (4): daily(), freeze(), judge(), load()

### Community 139 - "ingest"
Cohesion: 0.15
Nodes (12): if, needs, runs-on, timeout-minutes, jobs, ingest, name, on (+4 more)

### Community 140 - "backfill-photos.py"
Cohesion: 0.18
Nodes (8): jpeg(), main(), resize(), run(), save(), save_progress(), slug(), top_up()

### Community 144 - "generate"
Cohesion: 0.29
Nodes (8): cancel-in-progress, group, concurrency, if, runs-on, timeout-minutes, concurrency, generate

### Community 145 - "with"
Cohesion: 0.22
Nodes (9): with, if-no-files-found, key, name, path, persist-credentials, python-version, restore-keys (+1 more)

### Community 146 - "steps"
Cohesion: 0.39
Nodes (8): steps, steps, id, if, name, run, uses, working-directory

### Community 149 - "resolve_impacts.py"
Cohesion: 0.43
Nodes (6): choose(), country_map(), eligible(), main(), read(), resolve()

### Community 150 - "PageFetcher"
Cohesion: 0.32
Nodes (3): PageFetcher, paywalled_host(), same_site()

### Community 151 - "inputs"
Cohesion: 0.11
Nodes (19): description, required, default, description, type, default, description, required (+11 more)

### Community 157 - "writer"
Cohesion: 0.40
Nodes (5): writer, default, description, options, type

### Community 158 - "sources"
Cohesion: 0.40
Nodes (5): sources, default, description, options, type

### Community 159 - "writer"
Cohesion: 0.40
Nodes (5): writer, default, description, options, type

### Community 162 - "error_message"
Cohesion: 0.29
Nodes (4): transport(), error_message(), recording(), call()

### Community 164 - "country_cap"
Cohesion: 0.50
Nodes (4): default, description, required, country_cap

### Community 166 - "end_date"
Cohesion: 0.50
Nodes (4): default, description, required, end_date

### Community 167 - "gdelt_files"
Cohesion: 0.50
Nodes (4): default, description, required, gdelt_files

### Community 170 - "regions"
Cohesion: 0.50
Nodes (4): regions, default, description, required

### Community 171 - "start_date"
Cohesion: 0.50
Nodes (4): start_date, default, description, required

### Community 172 - "connections_only"
Cohesion: 0.50
Nodes (4): default, description, type, connections_only

### Community 178 - "outcome.py"
Cohesion: 0.21
Nodes (5): expected(), exit_bar(), judge(), move_between(), _sessions()

### Community 181 - "news.test.mjs"
Cohesion: 0.09
Nodes (21): decode(), fetchFeed(), parseFeed(), parseTime(), tag(), cold, env, NOW (+13 more)

### Community 182 - "fiscal_year"
Cohesion: 0.19
Nodes (8): finite(), fiscal_year(), ident(), provenance(), entity(), find(), listing(), union()

## Knowledge Gaps
- **4 isolated node(s):** `com.investedia:investedia-backend`, `com.investedia:investedia-services`, `RFC-8291`, `RFC-8292`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1279 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **53 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SnapshotUnavailableException` connect `SnapshotRepositoryTest.java` to `FileMarketRepository.java`, `NewsService.java`, `SnapshotResponseHeaders.java`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **What connects `com.investedia:investedia-backend`, `com.investedia:investedia-services`, `RFC-8291` to the rest of the system?**
  _4 weakly-connected nodes found - possible missing edges._
- **Should `test_engine_v4_pipeline.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13970588235294118 - nodes in this community are weakly interconnected._
- **Why does `EndToEndTests` connect `EndToEndTests` to `pathlib`, `.run_once`, `.setUp`, `gkg_zip`, `.test_separate_ingest_step_rechecks_provenance_and_skips_articles_already_in_day_files`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **Should `calendar_fred.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08502415458937199 - nodes in this community are weakly interconnected._
- **Why does `LicensingEvidenceTests` connect `LicensingEvidenceTests` to `pathlib`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **Should `pathlib` be split into smaller, more focused modules?**
  _Cohesion score 0.05765765765765766 - nodes in this community are weakly interconnected._