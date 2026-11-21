# Graph Report - investedia-news-trial-2h9e4efa  (2026-11-21)

## Corpus Check
- 252 files · ~157,297 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 5, .otf 3, .toml 2)

## Summary
- 3018 nodes · 5925 edges · 181 communities (132 shown, 49 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 137 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `024f10b9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- os
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
- update_share_cards.py
- news-gap-backfill.py
- hashlib
- steps
- steps
- news.test.mjs
- discover_media.py
- NewsService.java
- markets_audit/run.py
- briefing.js
- SnapshotResponseHeaders.java
- fetch.py
- ref_node_assert
- ref_node_test
- update_market.py
- FileMarketRepository.java
- regional-backfill.test.mjs
- events.py
- run
- alerts.js
- steps
- NewsImpacts
- gdelt-backfill.py
- NewsPhotos
- test_projects_media.py
- .missingAndMalformedSnapshotsFailClosedWithoutLeakingPaths
- context.py
- env
- market_data.py
- policy.test.mjs
- audit.py
- with
- Identity
- with
- LicensingEvidenceTests
- server
- feed_inventory.py
- inputs
- update_track_backfill.py
- math
- news-gap-backfill.yml
- steps
- runner.py
- country_basics.py
- regional-backfill.yml
- Policy
- StrictNewsTests
- fx_audit
- methods.py
- test_projects_scale.py
- ApiConfiguration.java
- collections
- inputs
- with
- with
- update_asset_analysis.py
- balance
- Downloads
- BudgetExceeded
- test_markets_pilot.py
- generate
- steps
- LiveConnectionsTests
- Outcome
- MarketFocusTest
- package.json
- steps
- ExchangeCoordinatesTest
- env
- Client
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
- gen-companies.py
- Threads
- com.investedia:investedia-backend
- com.investedia:investedia-services
- with
- steps
- extract.py
- thin-recent.yml
- alert-email-preview.yml
- reconcile
- env
- re
- RegionalTests
- test_projects_pipeline.py
- Clock
- ProjectsPipelineTests
- time
- .run_once
- EndToEndTests
- MediaTests
- org.springframework.web.bind.annotation.GetMapping
- ClaudeEditor
- generate
- backfill-photos.py
- GkgClient
- ingest_artifact
- gkg_zip
- ingest
- with
- steps
- AuditInputTests
- PublishLibrary
- resolve_impacts.py
- PageFetcher
- inputs
- enrich_page
- PhotoPoolTests
- DiscoveryTests
- .test_separate_ingest_step_rechecks_provenance_and_skips_articles_already_in_day_files
- sources
- writer
- sources
- writer
- WindowsAndRegions
- ClaudeWriterTests
- error_message
- batch_size
- country_cap
- dry_run
- end_date
- gdelt_files
- gemini_calls
- max_usd
- regions
- start_date
- connections_only
- ConnectionTests
- Budget
- NewsTrialTests
- LegalLinks
- Handler
- HoursTests

## God Nodes (most connected - your core abstractions)
1. `run()` - 37 edges
2. `MarketsPilotTests` - 31 edges
3. `fetch()` - 29 edges
4. `run()` - 29 edges
5. `build()` - 22 edges
6. `ProjectsPipelineTests` - 21 edges
7. `reconcile()` - 20 edges
8. `env` - 20 edges
9. `main()` - 19 edges
10. `env` - 18 edges

## Surprising Connections (you probably didn't know these)
- `ScaleTransportTests` --uses--> `Deferred`  [INFERRED]
  tests/test_projects_scale.py → tools/projects/scale/transport.py
- `MarketsPilotTests` --uses--> `Downloads`  [INFERRED]
  tests/test_markets_pilot.py → tools/markets_pilot/fetch.py
- `ScaleTransportTests` --uses--> `BudgetExceeded`  [INFERRED]
  tests/test_projects_scale.py → tools/projects/scale/transport.py
- `server` --calls--> `fetch()`  [EXTRACTED]
  tests/news-ingest.integration.mjs → workers/live/index.js
- `checked_fetch()` --calls--> `transport()`  [INFERRED]
  tools/coverage/source_licensing.py → tests/test_regional_backfill.py

## Import Cycles
- None detected.

## Communities (181 total, 49 thin omitted)

### Community 0 - "os"
Cohesion: 0.06
Nodes (12): exit_bar(), judge(), move_between(), _sessions(), daily(), freeze(), judge(), save() (+4 more)

### Community 1 - "calendar_fred.py"
Cohesion: 0.09
Nodes (18): _calc(), covered(), _day(), enrich(), fill_actuals(), _fmt(), FredError, _get() (+10 more)

### Community 2 - "pathlib"
Cohesion: 0.05
Nodes (12): AuditTests, CommandLineTests, CountryCapTests, RecentIngestTests, RecentWindowTests, TitleJunkTests, HistoryConnections, CachedRepresentationTests (+4 more)

### Community 3 - "regional-backfill.py"
Cohesion: 0.11
Nodes (29): batches(), cached_patch(), contains_secret(), dedupe(), draw_connections(), english_headlines(), evidence(), feed_sources() (+21 more)

### Community 4 - "json"
Cohesion: 0.07
Nodes (26): load(), facts(), load(), main(), parse(), get(), active_time(), calendar_metadata() (+18 more)

### Community 5 - "update_news_track.py"
Cohesion: 0.08
Nodes (18): Ledger, story(), Track, call(), OutcomeV2, bars(), bench_of(), call_start() (+10 more)

### Community 6 - "MarketsPilotTests"
Cohesion: 0.08
Nodes (16): MarketsPilotTests, build(), coverage(), digest(), finite(), fiscal_year(), fx_relationships(), ident() (+8 more)

### Community 7 - "SnapshotRepositoryTest.java"
Cohesion: 0.10
Nodes (6): RepositoryProperties, SnapshotUnavailableException, FileCallRepository, FileMarketRepository, FileNewsRepository, JsonSnapshotReader

### Community 8 - "ApiContractTest.java"
Cohesion: 0.06
Nodes (4): ApiContractTest, TimeConfiguration, LayeredArchitectureTest, LocalStartupTest

### Community 9 - "source_licensing.py"
Cohesion: 0.23
Nodes (9): active_sources(), collect(), checked_fetch(), contains_secret(), get(), main(), cached_fetch(), NoRedirect (+1 more)

### Community 10 - "live/index.js"
Cohesion: 0.07
Nodes (39): ALIAS, ALLOWED, cors(), fetch(), json(), scheduled(), snapshot(), withAliases() (+31 more)

### Community 11 - "prices.js"
Cohesion: 0.11
Nodes (34): fetchQuotes(), MAX_SYMBOLS, parseSpark(), PROVIDER, TIER_A, TIER_B, cold, env (+26 more)

### Community 12 - "registry.py"
Cohesion: 0.07
Nodes (16): call_of(), main(), context_of(), series(), v5(), ascii_lower(), get(), name_key() (+8 more)

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
Cohesion: 0.06
Nodes (39): generate(), feed, article(), gap(), now, req(), seed(), feed (+31 more)

### Community 22 - "worker-contracts.mjs"
Cohesion: 0.06
Nodes (23): target, env, expected, feed, now, p, quotes, snapshots (+15 more)

### Community 23 - "with"
Cohesion: 0.07
Nodes (27): concurrency, cancel-in-progress, group, runs-on, steps, timeout-minutes, jobs, deploy (+19 more)

### Community 24 - "steps"
Cohesion: 0.07
Nodes (27): concurrency, cancel-in-progress, group, GH_REPO, GH_TOKEN, jobs, notices, name (+19 more)

### Community 25 - "update_share_cards.py"
Cohesion: 0.09
Nodes (24): all_official(), bea(), bls(), _event(), fomc(), _get(), _text(), OfficialCalendar (+16 more)

### Community 26 - "news-gap-backfill.py"
Cohesion: 0.05
Nodes (38): age_minutes(), authority_of(), canon(), dedupe(), entities(), freshness(), from_iso(), iso() (+30 more)

### Community 27 - "hashlib"
Cohesion: 0.10
Nodes (27): records(), atomic_write(), content_hash(), generate_new(), repair_existing(), backfill_impacts(), compact48(), dedupe() (+19 more)

### Community 28 - "steps"
Cohesion: 0.07
Nodes (26): concurrency, cancel-in-progress, group, description, required, NEWS_INGEST_TOKEN, WORKER_URL, if (+18 more)

### Community 29 - "steps"
Cohesion: 0.07
Nodes (26): concurrency, cancel-in-progress, group, description, required, NEWS_INGEST_TOKEN, WORKER_URL, confirm (+18 more)

### Community 30 - "news.test.mjs"
Cohesion: 0.08
Nodes (22): decode(), fetchFeed(), parseFeed(), parseTime(), tag(), busy, env, NOW (+14 more)

### Community 31 - "discover_media.py"
Cohesion: 0.18
Nodes (7): DiscoveryTests, commons_candidate(), discover(), main(), query(), text(), Deferred

### Community 32 - "NewsService.java"
Cohesion: 0.17
Nodes (5): NewsController, ApiEnvelope, NewsSnapshot, NewsRepository, NewsService

### Community 33 - "markets_audit/run.py"
Cohesion: 0.17
Nodes (11): AuditScopeTests, RunnerBoundaryTests, coverage(), fetch_audit(), licensing(), main(), read(), render_coverage() (+3 more)

### Community 34 - "briefing.js"
Cohesion: 0.60
Nodes (4): cleanName(), handleGreeting(), HI, xml()

### Community 35 - "SnapshotResponseHeaders.java"
Cohesion: 0.14
Nodes (3): SnapshotResponseHeaders, ApiExceptionHandler, UnknownGroupException

### Community 36 - "fetch.py"
Cohesion: 0.17
Nodes (13): ecb_xml(), collect(), companies_house(), confirmed_ogl(), gleif(), golden_urls(), walk(), local() (+5 more)

### Community 37 - "ref_node_assert"
Cohesion: 0.21
Nodes (17): fixture, setup(), ApiError, CREDITS, error(), fail(), handleMarkets(), integer() (+9 more)

### Community 38 - "ref_node_test"
Cohesion: 0.16
Nodes (20): NOW, V, emptyNewsStats(), fnv(), refreshNews(), authority(), canon(), contentHash() (+12 more)

### Community 39 - "update_market.py"
Cohesion: 0.21
Nodes (13): from_fred(), from_yahoo(), chg(), get(), history(), perf(), main(), one() (+5 more)

### Community 41 - "regional-backfill.test.mjs"
Cohesion: 0.36
Nodes (8): article(), backfilled(), body(), impact, iso(), NOW, post(), seed()

### Community 42 - "events.py"
Cohesion: 0.18
Nodes (9): family(), load_days(), record(), _t(), threads(), upsert(), _write(), write_threads() (+1 more)

### Community 43 - "run"
Cohesion: 0.15
Nodes (12): finalize(), gkg_plan(), main(), order(), regions_from(), rescue(), run(), save_checkpoint() (+4 more)

### Community 44 - "alerts.js"
Cohesion: 0.12
Nodes (39): RFC-8291, RFC-8292, te, about(), alertsReady(), channelsFor(), country(), COUNTRY_ALIAS (+31 more)

### Community 45 - "steps"
Cohesion: 0.11
Nodes (18): jobs, offline-trial, name, runs-on, steps, timeout-minutes, on, pull_request (+10 more)

### Community 47 - "gdelt-backfill.py"
Cohesion: 0.16
Nodes (11): day(), library_days(), library_row(), main_country(), model_list(), _module(), parse_gkg(), photo_topics() (+3 more)

### Community 49 - "test_projects_media.py"
Cohesion: 0.23
Nodes (7): attach(), contained(), date(), https(), sha(), site_hash(), validate()

### Community 50 - ".missingAndMalformedSnapshotsFailClosedWithoutLeakingPaths"
Cohesion: 0.16
Nodes (5): CallController, LedgerDocument, CallRepository, CallService, SnapshotRepositoryTest

### Community 51 - "context.py"
Cohesion: 0.24
Nodes (4): features(), _last(), session_start(), sigma_daily()

### Community 52 - "env"
Cohesion: 0.11
Nodes (18): ANTHROPIC_API_KEY, BACKFILL_BATCH_INPUT, BACKFILL_CALLS_INPUT, BACKFILL_CONFIRM_INPUT, BACKFILL_CONNECTIONS_INPUT, BACKFILL_DAYS_INPUT, BACKFILL_DRY_RUN_INPUT, BACKFILL_SOURCES_INPUT (+10 more)

### Community 53 - "market_data.py"
Cohesion: 0.25
Nodes (8): correlation(), dated(), ecb_rates(), exchange_connections(), fetch(), main(), NoRedirect, valid()

### Community 54 - "policy.test.mjs"
Cohesion: 0.22
Nodes (7): NewsTrial, TrialEgress, destination(), egress(), route(), SOURCE_HOSTS, source

### Community 55 - "audit.py"
Cohesion: 0.30
Nodes (11): assets_for(), date(), fetch_api(), finite(), generate(), main(), markdown(), NoRedirect (+3 more)

### Community 56 - "with"
Cohesion: 0.05
Nodes (40): default, description, concurrency, cancel-in-progress, group, GH_TOKEN, backfill_run, jobs (+32 more)

### Community 58 - "with"
Cohesion: 0.05
Nodes (37): runs-on, steps, timeout-minutes, default, description, type, concurrency, cancel-in-progress (+29 more)

### Community 60 - "server"
Cohesion: 0.17
Nodes (11): name, include-message, include-stacktrace, investedia, repository-root, server, address, error (+3 more)

### Community 61 - "feed_inventory.py"
Cohesion: 0.22
Nodes (6): configured(), dates(), get(), main(), NoRedirect, probe()

### Community 62 - "inputs"
Cohesion: 0.13
Nodes (15): description, required, default, description, required, default, description, confirm (+7 more)

### Community 63 - "update_track_backfill.py"
Cohesion: 0.22
Nodes (5): Daily, day(), judge_daily(), load(), run()

### Community 64 - "math"
Cohesion: 0.20
Nodes (7): expected(), decide(), horizon(), meaningful(), _pct(), strong_catalyst(), surprise_sign()

### Community 65 - "news-gap-backfill.yml"
Cohesion: 0.18
Nodes (10): concurrency, cancel-in-progress, group, jobs, name, on, workflow_dispatch, permissions (+2 more)

### Community 66 - "steps"
Cohesion: 0.17
Nodes (12): if, runs-on, steps, timeout-minutes, jobs, backfill, id, if (+4 more)

### Community 67 - "runner.py"
Cohesion: 0.18
Nodes (10): backfill(), store(), exclusive_run(), main(), preflight(), verify_generation(), allowed(), pack() (+2 more)

### Community 68 - "country_basics.py"
Cohesion: 0.33
Nodes (8): apply_indicator(), get(), main(), NoRedirect, numeric(), observation(), read(), saved()

### Community 69 - "regional-backfill.yml"
Cohesion: 0.20
Nodes (9): concurrency, cancel-in-progress, group, name, on, workflow_dispatch, permissions, actions (+1 more)

### Community 72 - "fx_audit"
Cohesion: 0.44
Nodes (3): FXTests, fx_audit(), pearson()

### Community 73 - "methods.py"
Cohesion: 0.33
Nodes (5): IdentifierTests, match(), normal_id(), returns(), valid_isin()

### Community 74 - "test_projects_scale.py"
Cohesion: 0.21
Nodes (6): ScaleArtifactTests, run(), details(), ids(), BudgetExceeded, slim()

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
Cohesion: 0.36
Nodes (3): Balance, c(), balance()

### Community 82 - "Downloads"
Cohesion: 0.25
Nodes (3): Client, NoRedirect, Downloads

### Community 83 - "BudgetExceeded"
Cohesion: 0.19
Nodes (4): BudgetExceeded, ClaudeWriter, ModelBudget, ModelUnavailable

### Community 84 - "test_markets_pilot.py"
Cohesion: 0.27
Nodes (5): runner(), execute(), main(), plan(), write()

### Community 85 - "generate"
Cohesion: 0.17
Nodes (8): country_allowed(), dedupe(), generate(), headline_key(), known_keys(), provenance(), sid(), topic_photo()

### Community 86 - "steps"
Cohesion: 0.25
Nodes (8): recovery, runs-on, steps, timeout-minutes, if, name, run, uses

### Community 88 - "Outcome"
Cohesion: 0.29
Nodes (3): Context, Outcome, session()

### Community 90 - "package.json"
Cohesion: 0.25
Nodes (7): name, private, scripts, bench, bench:news, test, type

### Community 91 - "steps"
Cohesion: 0.06
Nodes (33): description, required, PER_TOPIC, PIXABAY_KEY, confirm, per_topic, jobs, photos (+25 more)

### Community 93 - "env"
Cohesion: 0.06
Nodes (32): concurrency, cancel-in-progress, group, GH_REPO, GH_TOKEN, MAX_TOTAL, QUEUE, SPENT (+24 more)

### Community 94 - "Client"
Cohesion: 0.29
Nodes (3): ScaleTransportTests, Client, NoRedirect

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
Cohesion: 0.12
Nodes (11): TabularScaleTests, header_hash(), parse(), records(), records(), tabular(), parse(), parse() (+3 more)

### Community 107 - "dry_run"
Cohesion: 0.50
Nodes (4): default, description, type, dry_run

### Community 108 - "gemini_calls"
Cohesion: 0.50
Nodes (4): default, description, required, gemini_calls

### Community 114 - "build_projects.py"
Cohesion: 0.16
Nodes (14): build(), canonical(), company_links(), covered(), digest(), distance(), finite(), licence_gate() (+6 more)

### Community 115 - "gen-companies.py"
Cohesion: 0.31
Nodes (5): clean(), display(), exchange(), main(), slugify()

### Community 121 - "with"
Cohesion: 0.07
Nodes (27): concurrency, cancel-in-progress, group, jobs, refresh, name, on, schedule (+19 more)

### Community 122 - "steps"
Cohesion: 0.08
Nodes (25): ANTHROPIC_API_KEY, MAX_USD, runs-on, steps, timeout-minutes, max_usd, jobs, fill (+17 more)

### Community 123 - "extract.py"
Cohesion: 0.31
Nodes (5): build_prompt(), calendar_expectations(), _num(), story_block(), validate()

### Community 124 - "thin-recent.yml"
Cohesion: 0.09
Nodes (21): concurrency, cancel-in-progress, group, GH_REPO, GH_TOKEN, jobs, start, name (+13 more)

### Community 125 - "alert-email-preview.yml"
Cohesion: 0.10
Nodes (20): TO, TOKEN, WORKER_URL, to, jobs, send, name, on (+12 more)

### Community 126 - "reconcile"
Cohesion: 0.18
Nodes (8): bind(), row(), ScalePolicyTests, ScaleReconciliationTests, current(), identity(), publishers(), reconcile()

### Community 127 - "env"
Cohesion: 0.11
Nodes (19): ANTHROPIC_API_KEY, BATCH, CALLS, CONFIRM, COUNTRY_CAP, DRY_RUN, END_DATE, GDELT (+11 more)

### Community 128 - "re"
Cohesion: 0.16
Nodes (6): featured(), parse(), validate(), parse(), query(), normalize_sector()

### Community 130 - "test_projects_pipeline.py"
Cohesion: 0.21
Nodes (6): candidates(), connections(), fingerprint(), review_passes(), main(), parse()

### Community 131 - "Clock"
Cohesion: 0.19
Nodes (5): Clock, get(), PublisherPageTests, redirecting(), get()

### Community 133 - "time"
Cohesion: 0.07
Nodes (22): ok(), fetch(), NoRedirect, sparql(), get(), get(), fetch(), main() (+14 more)

### Community 134 - ".run_once"
Cohesion: 0.17
Nodes (3): ClaudeProviderTests, FakeClaude, boom()

### Community 135 - "EndToEndTests"
Cohesion: 0.21
Nodes (3): EndToEndTests, model(), http_error()

### Community 139 - "generate"
Cohesion: 0.17
Nodes (11): if, runs-on, timeout-minutes, jobs, generate, name, on, workflow_dispatch (+3 more)

### Community 140 - "backfill-photos.py"
Cohesion: 0.26
Nodes (7): main(), resize(), run(), save(), save_progress(), slug(), top_up()

### Community 142 - "ingest_artifact"
Cohesion: 0.28
Nodes (7): ingest_artifact(), acknowledged(), ingest_library(), local_events(), worker_day_reader(), read_day(), group()

### Community 144 - "ingest"
Cohesion: 0.25
Nodes (9): cancel-in-progress, group, concurrency, concurrency, if, needs, runs-on, timeout-minutes (+1 more)

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
Cohesion: 0.29
Nodes (7): description, required, default, description, confirm, gemini_model, inputs

### Community 152 - "enrich_page"
Cohesion: 0.33
Nodes (5): clean_title(), enrich_page(), meta(), paywalled(), published_time()

### Community 156 - "sources"
Cohesion: 0.40
Nodes (5): sources, default, description, options, type

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

### Community 163 - "batch_size"
Cohesion: 0.50
Nodes (4): default, description, required, batch_size

### Community 164 - "country_cap"
Cohesion: 0.50
Nodes (4): default, description, required, country_cap

### Community 165 - "dry_run"
Cohesion: 0.50
Nodes (4): default, description, type, dry_run

### Community 166 - "end_date"
Cohesion: 0.50
Nodes (4): default, description, required, end_date

### Community 167 - "gdelt_files"
Cohesion: 0.50
Nodes (4): default, description, required, gdelt_files

### Community 168 - "gemini_calls"
Cohesion: 0.50
Nodes (4): default, description, required, gemini_calls

### Community 169 - "max_usd"
Cohesion: 0.50
Nodes (4): max_usd, default, description, required

### Community 170 - "regions"
Cohesion: 0.50
Nodes (4): regions, default, description, required

### Community 171 - "start_date"
Cohesion: 0.50
Nodes (4): start_date, default, description, required

### Community 172 - "connections_only"
Cohesion: 0.50
Nodes (4): default, description, type, connections_only

## Knowledge Gaps
- **4 isolated node(s):** `com.investedia:investedia-backend`, `com.investedia:investedia-services`, `RFC-8291`, `RFC-8292`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1236 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **49 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RegionalTests` connect `RegionalTests` to `error_message`, `pathlib`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **What connects `com.investedia:investedia-backend`, `com.investedia:investedia-services`, `RFC-8291` to the rest of the system?**
  _4 weakly-connected nodes found - possible missing edges._
- **Should `os` be split into smaller, more focused modules?**
  _Cohesion score 0.05656565656565657 - nodes in this community are weakly interconnected._
- **Why does `SnapshotUnavailableException` connect `SnapshotRepositoryTest.java` to `FileMarketRepository.java`, `NewsService.java`, `SnapshotResponseHeaders.java`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **Should `calendar_fred.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08973172987974098 - nodes in this community are weakly interconnected._
- **Why does `EndToEndTests` connect `EndToEndTests` to `pathlib`, `.run_once`, `.setUp`, `gkg_zip`, `.test_separate_ingest_step_rechecks_provenance_and_skips_articles_already_in_day_files`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **Should `pathlib` be split into smaller, more focused modules?**
  _Cohesion score 0.04936936936936937 - nodes in this community are weakly interconnected._