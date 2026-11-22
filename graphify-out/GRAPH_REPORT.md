# Graph Report - investedia-trial-seed-export-tr6h2nwm  (2026-11-21)

## Corpus Check
- 254 files · ~157,684 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 5, .otf 3, .toml 2)

## Summary
- 3056 nodes · 5968 edges · 189 communities (137 shown, 52 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 137 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `acee2900`
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
- update_share_cards.py
- news-gap-backfill.py
- update_globe_news.py
- steps
- steps
- news.test.mjs
- test_projects_media.py
- NewsService.java
- markets_audit/run.py
- briefing.js
- SnapshotResponseHeaders.java
- fetch.py
- markets.js
- ref_node_test
- update_market.py
- FileMarketRepository.java
- handleNews
- events.py
- run
- alerts.js
- steps
- NewsImpacts
- gdelt-backfill.py
- NewsPhotos
- with
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
- engine/policy.py
- news-gap-backfill.yml
- steps
- news-pipeline.py
- country_basics.py
- regional-backfill.yml
- Policy
- StrictNewsTests
- math
- normal_id
- ref_node_assert
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
- sys
- MarketFocusTest
- package.json
- steps
- ExchangeCoordinatesTest
- env
- calendar_official.py
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
- reconcile
- Threads
- com.investedia:investedia-backend
- com.investedia:investedia-services
- with
- steps
- extract.py
- thin-recent.yml
- alert-email-preview.yml
- test_projects_scale.py
- env
- re
- RegionalTests
- test_projects_pipeline.py
- Clock
- ProjectsPipelineTests
- urllib_parse
- .run_once
- EndToEndTests
- connections.js
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
- argparse
- PageFetcher
- inputs
- enrich_page
- time
- DiscoveryTests
- .test_separate_ingest_step_rechecks_provenance_and_skips_articles_already_in_day_files
- live_v5.py
- writer
- sources
- writer
- WindowsAndRegions
- ClaudeWriterTests
- error_message
- engine/run.py
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
- outcome.py
- runner.py
- HoursTests
- waitlist.test.mjs
- fiscal_year
- TrialExportTests
- AuditTests
- RecentIngestTests
- CachedRepresentationTests
- LegacyRetryBudgetTests

## God Nodes (most connected - your core abstractions)
1. `run()` - 37 edges
2. `MarketsPilotTests` - 31 edges
3. `run()` - 29 edges
4. `fetch()` - 29 edges
5. `build()` - 22 edges
6. `ProjectsPipelineTests` - 21 edges
7. `env` - 20 edges
8. `reconcile()` - 20 edges
9. `main()` - 19 edges
10. `env` - 18 edges

## Surprising Connections (you probably didn't know these)
- `reg_place()` --calls--> `norm()`  [INFERRED]
  tools/globe-news/connections.py → news_core.py
- `server` --calls--> `fetch()`  [EXTRACTED]
  tests/news-ingest.integration.mjs → workers/live/index.js
- `MarketsPilotTests` --uses--> `Downloads`  [INFERRED]
  tests/test_markets_pilot.py → tools/markets_pilot/fetch.py
- `regional_candidates()` --indirect_call--> `c()`  [INFERRED]
  tools/regional-backfill.py → tests/test_news_regions.py
- `checked_fetch()` --calls--> `transport()`  [INFERRED]
  tools/coverage/source_licensing.py → tests/test_regional_backfill.py

## Import Cycles
- None detected.

## Communities (189 total, 52 thin omitted)

### Community 0 - "test_engine_v4_pipeline.py"
Cohesion: 0.14
Nodes (6): Context, Extraction, Outcome, Runner, session(), Shadow

### Community 1 - "calendar_fred.py"
Cohesion: 0.09
Nodes (18): _calc(), covered(), _day(), enrich(), fill_actuals(), _fmt(), FredError, _get() (+10 more)

### Community 2 - "pathlib"
Cohesion: 0.06
Nodes (8): CommandLineTests, CountryCapTests, RecentWindowTests, TitleJunkTests, HistoryConnections, EnglishHeadlineTests, ExtraFeedsTests, ThinCapTests

### Community 3 - "regional-backfill.py"
Cohesion: 0.10
Nodes (32): content_hash(), batches(), cached_patch(), contains_secret(), dedupe(), draw_connections(), english_headlines(), evidence() (+24 more)

### Community 4 - "json"
Cohesion: 0.08
Nodes (17): freeze(), judge(), load(), save(), main(), main(), payload(), push() (+9 more)

### Community 5 - "update_news_track.py"
Cohesion: 0.08
Nodes (18): Ledger, story(), Track, call(), OutcomeV2, bars(), bench_of(), call_start() (+10 more)

### Community 6 - "MarketsPilotTests"
Cohesion: 0.09
Nodes (13): MarketsPilotTests, runner(), build(), coverage(), digest(), ident(), provenance(), read() (+5 more)

### Community 7 - "SnapshotRepositoryTest.java"
Cohesion: 0.10
Nodes (6): RepositoryProperties, SnapshotUnavailableException, FileCallRepository, FileMarketRepository, FileNewsRepository, JsonSnapshotReader

### Community 8 - "ApiContractTest.java"
Cohesion: 0.06
Nodes (4): ApiContractTest, TimeConfiguration, LayeredArchitectureTest, LocalStartupTest

### Community 9 - "source_licensing.py"
Cohesion: 0.14
Nodes (10): active_sources(), collect(), checked_fetch(), contains_secret(), get(), LegalLinks, main(), cached_fetch() (+2 more)

### Community 10 - "live/index.js"
Cohesion: 0.12
Nodes (23): ALIAS, ALLOWED, cors(), fetch(), json(), scheduled(), snapshot(), withAliases() (+15 more)

### Community 11 - "prices.js"
Cohesion: 0.11
Nodes (35): fetchQuotes(), MAX_SYMBOLS, parseSpark(), PROVIDER, TIER_A, TIER_B, cold, env (+27 more)

### Community 12 - "registry.py"
Cohesion: 0.08
Nodes (15): ascii_lower(), get(), name_key(), norm_ticker(), Registry, same_company(), stamp(), words() (+7 more)

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
Cohesion: 0.07
Nodes (33): generate(), busy, env, NOW, quiet, stories, warmIx, FEEDS (+25 more)

### Community 22 - "worker-contracts.mjs"
Cohesion: 0.08
Nodes (17): env, expected, feed, now, p, quotes, snapshots, source (+9 more)

### Community 23 - "with"
Cohesion: 0.07
Nodes (27): concurrency, cancel-in-progress, group, runs-on, steps, timeout-minutes, jobs, deploy (+19 more)

### Community 24 - "steps"
Cohesion: 0.07
Nodes (27): concurrency, cancel-in-progress, group, GH_REPO, GH_TOKEN, jobs, notices, name (+19 more)

### Community 25 - "update_share_cards.py"
Cohesion: 0.14
Nodes (16): ShareCards, ago_text(), caption(), draw_logo(), load(), move_since(), page(), parse() (+8 more)

### Community 26 - "news-gap-backfill.py"
Cohesion: 0.05
Nodes (37): age_minutes(), authority_of(), canon(), dedupe(), entities(), freshness(), from_iso(), iso() (+29 more)

### Community 27 - "update_globe_news.py"
Cohesion: 0.12
Nodes (23): atomic_write(), backfill_impacts(), compact48(), dedupe(), describe(), err(), gdelt(), gemini() (+15 more)

### Community 28 - "steps"
Cohesion: 0.07
Nodes (26): concurrency, cancel-in-progress, group, description, required, NEWS_INGEST_TOKEN, WORKER_URL, if (+18 more)

### Community 29 - "steps"
Cohesion: 0.07
Nodes (26): concurrency, cancel-in-progress, group, description, required, NEWS_INGEST_TOKEN, WORKER_URL, confirm (+18 more)

### Community 30 - "news.test.mjs"
Cohesion: 0.14
Nodes (13): decode(), fetchFeed(), parseFeed(), parseTime(), tag(), env(), now, fakeKV() (+5 more)

### Community 31 - "test_projects_media.py"
Cohesion: 0.06
Nodes (22): DiscoveryTests, MediaTests, ScaleTransportTests, commons_candidate(), discover(), main(), query(), text() (+14 more)

### Community 32 - "NewsService.java"
Cohesion: 0.17
Nodes (5): NewsController, ApiEnvelope, NewsSnapshot, NewsRepository, NewsService

### Community 33 - "markets_audit/run.py"
Cohesion: 0.18
Nodes (11): AuditScopeTests, RunnerBoundaryTests, coverage(), fetch_audit(), licensing(), main(), read(), render_coverage() (+3 more)

### Community 34 - "briefing.js"
Cohesion: 0.60
Nodes (4): cleanName(), handleGreeting(), HI, xml()

### Community 35 - "SnapshotResponseHeaders.java"
Cohesion: 0.14
Nodes (3): SnapshotResponseHeaders, ApiExceptionHandler, UnknownGroupException

### Community 36 - "fetch.py"
Cohesion: 0.15
Nodes (14): ecb_xml(), collect(), companies_house(), confirmed_ogl(), gleif(), golden_urls(), walk(), local() (+6 more)

### Community 37 - "markets.js"
Cohesion: 0.25
Nodes (16): setup(), ApiError, CREDITS, error(), fail(), handleMarkets(), integer(), metadata() (+8 more)

### Community 38 - "ref_node_test"
Cohesion: 0.19
Nodes (16): NOW, V, authority(), canon(), dedupe(), EC, entities(), entitiesRaw() (+8 more)

### Community 39 - "update_market.py"
Cohesion: 0.21
Nodes (13): from_fred(), from_yahoo(), chg(), get(), history(), perf(), main(), one() (+5 more)

### Community 41 - "handleNews"
Cohesion: 0.11
Nodes (23): article(), gap(), now, req(), seed(), article(), backfilled(), body() (+15 more)

### Community 42 - "events.py"
Cohesion: 0.16
Nodes (9): family(), load_days(), record(), _t(), threads(), upsert(), _write(), write_threads() (+1 more)

### Community 43 - "run"
Cohesion: 0.15
Nodes (13): finalize(), gkg_plan(), main(), order(), regions_from(), rescue(), run(), save_checkpoint() (+5 more)

### Community 44 - "alerts.js"
Cohesion: 0.11
Nodes (39): RFC-8291, RFC-8292, te, about(), channelsFor(), country(), COUNTRY_ALIAS, deliver() (+31 more)

### Community 45 - "steps"
Cohesion: 0.11
Nodes (18): jobs, offline-trial, name, runs-on, steps, timeout-minutes, on, pull_request (+10 more)

### Community 47 - "gdelt-backfill.py"
Cohesion: 0.16
Nodes (11): day(), library_days(), library_row(), main_country(), model_list(), _module(), parse_gkg(), photo_topics() (+3 more)

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
Cohesion: 0.24
Nodes (6): configured(), dates(), get(), main(), NoRedirect, probe()

### Community 62 - "inputs"
Cohesion: 0.13
Nodes (15): description, required, default, description, required, default, description, confirm (+7 more)

### Community 63 - "update_track_backfill.py"
Cohesion: 0.22
Nodes (5): Daily, day(), judge_daily(), load(), run()

### Community 64 - "engine/policy.py"
Cohesion: 0.25
Nodes (6): decide(), horizon(), meaningful(), _pct(), strong_catalyst(), surprise_sign()

### Community 65 - "news-gap-backfill.yml"
Cohesion: 0.18
Nodes (10): concurrency, cancel-in-progress, group, jobs, name, on, workflow_dispatch, permissions (+2 more)

### Community 66 - "steps"
Cohesion: 0.17
Nodes (12): if, runs-on, steps, timeout-minutes, jobs, backfill, id, if (+4 more)

### Community 67 - "news-pipeline.py"
Cohesion: 0.15
Nodes (10): backfill(), store(), exclusive_run(), main(), preflight(), verify_generation(), main(), publish() (+2 more)

### Community 68 - "country_basics.py"
Cohesion: 0.33
Nodes (8): apply_indicator(), get(), main(), NoRedirect, numeric(), observation(), read(), saved()

### Community 69 - "regional-backfill.yml"
Cohesion: 0.20
Nodes (9): concurrency, cancel-in-progress, group, name, on, workflow_dispatch, permissions, actions (+1 more)

### Community 72 - "math"
Cohesion: 0.18
Nodes (6): FXTests, fx_audit(), pearson(), returns(), finite(), fx_relationships()

### Community 73 - "normal_id"
Cohesion: 0.39
Nodes (5): IdentifierTests, match(), normal_id(), valid_isin(), validate_model()

### Community 74 - "ref_node_assert"
Cohesion: 0.12
Nodes (8): target, feed, fixture, at, now, row, saved, snapshot

### Community 76 - "collections"
Cohesion: 0.18
Nodes (9): history(), km(), load(), main(), _rules(), reg_place(), parse(), parse() (+1 more)

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
Cohesion: 0.24
Nodes (3): BudgetExceeded, ClaudeWriter, ModelUnavailable

### Community 84 - "test_markets_pilot.py"
Cohesion: 0.46
Nodes (4): execute(), main(), plan(), write()

### Community 85 - "generate"
Cohesion: 0.17
Nodes (8): country_allowed(), dedupe(), generate(), headline_key(), known_keys(), provenance(), sid(), topic_photo()

### Community 86 - "steps"
Cohesion: 0.25
Nodes (8): recovery, runs-on, steps, timeout-minutes, if, name, run, uses

### Community 88 - "sys"
Cohesion: 0.17
Nodes (5): facts(), load(), main(), parse(), get()

### Community 90 - "package.json"
Cohesion: 0.25
Nodes (7): name, private, scripts, bench, bench:news, test, type

### Community 91 - "steps"
Cohesion: 0.06
Nodes (33): description, required, PER_TOPIC, PIXABAY_KEY, confirm, per_topic, jobs, photos (+25 more)

### Community 93 - "env"
Cohesion: 0.06
Nodes (32): concurrency, cancel-in-progress, group, GH_REPO, GH_TOKEN, MAX_TOTAL, QUEUE, SPENT (+24 more)

### Community 94 - "calendar_official.py"
Cohesion: 0.28
Nodes (8): all_official(), bea(), bls(), _event(), fomc(), _get(), _text(), OfficialCalendar

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
Nodes (8): records(), tabular(), parse(), parse(), parse(), parse(), parse(), normalize()

### Community 107 - "dry_run"
Cohesion: 0.50
Nodes (4): default, description, type, dry_run

### Community 108 - "gemini_calls"
Cohesion: 0.50
Nodes (4): default, description, required, gemini_calls

### Community 114 - "build_projects.py"
Cohesion: 0.18
Nodes (12): build(), covered(), digest(), distance(), featured(), finite(), licence_gate(), main() (+4 more)

### Community 115 - "reconcile"
Cohesion: 0.23
Nodes (7): row(), ScaleReconciliationTests, canonical(), merge_rows(), identity(), publishers(), reconcile()

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

### Community 126 - "test_projects_scale.py"
Cohesion: 0.13
Nodes (9): bind(), ScaleArtifactTests, ScalePolicyTests, TabularScaleTests, current(), header_hash(), parse(), records() (+1 more)

### Community 127 - "env"
Cohesion: 0.11
Nodes (19): ANTHROPIC_API_KEY, BATCH, CALLS, CONFIRM, COUNTRY_CAP, DRY_RUN, END_DATE, GDELT (+11 more)

### Community 128 - "re"
Cohesion: 0.33
Nodes (8): normalize_sector(), assets(), clean(), fetch(), for_asset(), google(), main(), parse()

### Community 130 - "test_projects_pipeline.py"
Cohesion: 0.21
Nodes (6): candidates(), connections(), fingerprint(), review_passes(), main(), parse()

### Community 131 - "Clock"
Cohesion: 0.19
Nodes (5): Clock, get(), PublisherPageTests, redirecting(), get()

### Community 132 - "ProjectsPipelineTests"
Cohesion: 0.32
Nodes (3): ProjectsPipelineTests, row(), company_links()

### Community 133 - "urllib_parse"
Cohesion: 0.11
Nodes (11): daily(), ok(), fetch(), main(), registry_listing(), ysym(), alias_known(), fetch() (+3 more)

### Community 134 - ".run_once"
Cohesion: 0.17
Nodes (3): ClaudeProviderTests, FakeClaude, boom()

### Community 135 - "EndToEndTests"
Cohesion: 0.21
Nodes (3): EndToEndTests, model(), http_error()

### Community 136 - "connections.js"
Cohesion: 0.20
Nodes (14): clean(), distance(), MAX_BODY, MAX_ROWS, MAX_STORED, point(), readBody(), RELATIONS (+6 more)

### Community 139 - "generate"
Cohesion: 0.17
Nodes (11): if, runs-on, timeout-minutes, jobs, generate, name, on, workflow_dispatch (+3 more)

### Community 140 - "backfill-photos.py"
Cohesion: 0.13
Nodes (9): jpeg(), PhotoPoolTests, main(), resize(), run(), save(), save_progress(), slug() (+1 more)

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

### Community 149 - "argparse"
Cohesion: 0.15
Nodes (11): active_time(), calendar_metadata(), enrich(), main(), choose(), country_map(), eligible(), main() (+3 more)

### Community 150 - "PageFetcher"
Cohesion: 0.32
Nodes (3): PageFetcher, paywalled_host(), same_site()

### Community 151 - "inputs"
Cohesion: 0.12
Nodes (16): default, description, required, description, required, default, description, batch_size (+8 more)

### Community 152 - "enrich_page"
Cohesion: 0.33
Nodes (5): clean_title(), enrich_page(), meta(), paywalled(), published_time()

### Community 153 - "time"
Cohesion: 0.19
Nodes (4): fetch(), NoRedirect, sparql(), get()

### Community 156 - "live_v5.py"
Cohesion: 0.27
Nodes (5): call_of(), main(), context_of(), series(), v5()

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

### Community 178 - "outcome.py"
Cohesion: 0.36
Nodes (4): exit_bar(), judge(), move_between(), _sessions()

### Community 179 - "runner.py"
Cohesion: 0.26
Nodes (5): allowed(), Handler, pack(), run(), validate()

### Community 181 - "waitlist.test.mjs"
Cohesion: 0.43
Nodes (4): CONSENT_V, hex(), joinWaitlist(), sha()

## Knowledge Gaps
- **4 isolated node(s):** `com.investedia:investedia-backend`, `com.investedia:investedia-services`, `RFC-8291`, `RFC-8292`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 1261 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **52 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `discover()` connect `test_projects_media.py` to `re`, `time`, `collections`, `json`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **What connects `com.investedia:investedia-backend`, `com.investedia:investedia-services`, `RFC-8291` to the rest of the system?**
  _4 weakly-connected nodes found - possible missing edges._
- **Should `test_engine_v4_pipeline.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13970588235294118 - nodes in this community are weakly interconnected._
- **Why does `SnapshotUnavailableException` connect `SnapshotRepositoryTest.java` to `FileMarketRepository.java`, `NewsService.java`, `SnapshotResponseHeaders.java`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **Should `calendar_fred.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08973172987974098 - nodes in this community are weakly interconnected._
- **Why does `LicensingEvidenceTests` connect `LicensingEvidenceTests` to `pathlib`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **Should `pathlib` be split into smaller, more focused modules?**
  _Cohesion score 0.06467661691542288 - nodes in this community are weakly interconnected._